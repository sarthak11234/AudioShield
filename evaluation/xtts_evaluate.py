"""
AudioShield XTTS-v2 clone evaluation (runs in the MAIN .venv).

Reads evaluation/results/xtts_clones/xtts_manifest.json (written by
evaluation/xtts_synthesize.py in the isolated xtts venv) and evaluates every
generated clone with the project's existing evaluators:

  - Speaker identity: SpeechBrain ECAPA-TDNN (spkrec-ecapa-voxceleb) cosine
    similarity between the SOURCE speaker's own reference embedding and the
    clone embedding. Ground truth is always the test speaker's own longest
    reference (even for the unrelated condition).
  - Intelligibility: local openai/whisper-tiny WER vs. the known prompt.
  - Quality: duration, clipping count (|x|>0.999), NaN/Inf count.
    Source-vs-clone SNR/STOI deliberately omitted (different waveforms).

Baseline gate (Phase 4): distributions are compared against the canonical
benchmark's same-speaker orig-orig and cross-speaker orig-other ECAPA
statistics (read from evaluation/results/evaluation_results.json). No
universal threshold is invented; the verdict inspects the distributions.

Outputs (main venv):
  evaluation/results/xtts_baseline_results.json
  evaluation/results/xtts_baseline_results.csv
  evaluation/results/xtts_baseline_summary.md

Usage:
  .venv/bin/python evaluation/xtts_evaluate.py \
      --clones-dir evaluation/results/xtts_clones \
      --results-dir evaluation/results [--tag baseline]
"""

import argparse
import csv
import dataclasses
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))
sys.path.insert(0, str(ROOT))

from tasks.protect import load_audio  # noqa: E402
from evaluation.metrics import extract_speaker_embedding  # noqa: E402
from evaluation.voice_cloning_eval import compute_wer  # noqa: E402 reuse WER

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("audioshield.xtts_eval")


def _stats(values: List[float]) -> Dict:
    if not values:
        return {"n": 0, "mean": None, "median": None, "std": None, "min": None, "max": None}
    a = np.array(values, dtype=np.float64)
    return {"n": len(values), "mean": round(float(np.mean(a)), 4),
            "median": round(float(np.median(a)), 4), "std": round(float(np.std(a)), 4),
            "min": round(float(np.min(a)), 4), "max": round(float(np.max(a)), 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clones-dir", default="evaluation/results/xtts_clones")
    ap.add_argument("--results-dir", default="evaluation/results")
    ap.add_argument("--tag", default="baseline")
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    clones_dir = ROOT / args.clones_dir
    results_dir = ROOT / args.results_dir
    manifest = json.load(open(clones_dir / "xtts_manifest.json"))

    # Canonical benchmark reference distributions.
    bench = json.load(open(results_dir / "evaluation_results.json"))
    bench_dists = bench["speaker_embedding_distributions"]
    ref_orig_orig = bench_dists["orig_orig_stats"]
    ref_orig_other = bench_dists["orig_other_stats"]

    # Speaker encoder + ASR (main venv, cached).
    from speechbrain.inference.speaker import EncoderClassifier
    enc = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=str(ROOT / "evaluation" / "fixtures" / "ecapa_model"),
        run_opts={"device": args.device})
    from transformers import WhisperForConditionalGeneration, WhisperProcessor
    asr_proc = WhisperProcessor.from_pretrained("openai/whisper-tiny")
    asr_mod = WhisperForConditionalGeneration.from_pretrained(
        "openai/whisper-tiny").to(args.device)
    asr_mod.eval()

    def transcribe(wave: torch.Tensor, sr: int) -> Optional[str]:
        import torchaudio
        mono = wave.mean(dim=0, keepdim=True) if wave.dim() == 2 else wave
        if mono.dim() == 1:
            mono = mono.unsqueeze(0)
        if sr != 16000:
            mono = torchaudio.transforms.Resample(sr, 16000)(mono)
        feats = asr_proc(mono.squeeze(0).cpu().numpy().astype(np.float32),
                         sampling_rate=16000, return_tensors="pt")
        with torch.no_grad():
            ids = asr_mod.generate(feats.input_features.to(args.device))
        return asr_proc.batch_decode(ids, skip_special_tokens=True)[0].strip()

    # Ground-truth embedding per test speaker = ECAPA(longest own reference).
    gt: Dict[str, torch.Tensor] = {}
    trials = []
    failures: Dict[str, int] = defaultdict(int)
    for t in manifest["trials"]:
        if t["status"] != "OK":
            failures["synthesis_failure"] += 1
            trials.append({**t, "eval": "SKIPPED_SYNTHESIS_FAIL"})
            continue
        spk = t["speaker"]
        try:
            if spk not in gt:
                # Reconstruct speaker's own reference: longest dataset file.
                import soundfile as sf
                cands = sorted((ROOT / "evaluation/datasets/librispeech_benchmark").glob(f"{spk}_*.wav"))
                cands = [c for c in cands if "protected" not in c.name]
                ref0 = max(cands, key=lambda c: sf.SoundFile(str(c)).frames / sf.SoundFile(str(c)).samplerate)
                w0, s0 = load_audio(str(ref0))
                gt[spk] = extract_speaker_embedding(w0, s0, enc)
            w, s = load_audio(t["out"])
            emb = extract_speaker_embedding(w, s, enc)
            sim = round(float(torch.dot(gt[spk], emb).item()), 4)
            nan_inf = int(torch.isnan(w).sum() + torch.isinf(w).sum())
            clip = int((w.abs() > 0.999).sum())
            dur = round(w.shape[-1] / s, 3)
            hyp = transcribe(w, s)
            wer = round(compute_wer(t["prompt"], hyp), 4) if hyp else None
            trials.append({**t, "eval": "SUCCESS", "speaker_sim": sim,
                           "wer": wer, "transcript": hyp,
                           "duration_s": dur, "clipping": clip, "nan_inf": nan_inf})
        except Exception as e:  # noqa: BLE001 - classify, never silently drop
            failures["evaluation_failure"] += 1
            trials.append({**t, "eval": "FAILED", "error": str(e)[:300]})

    ok = [t for t in trials if t.get("eval") == "SUCCESS"]
    by_cond: Dict[str, List[float]] = defaultdict(list)
    by_cond_wer: Dict[str, List[float]] = defaultdict(list)
    for t in ok:
        by_cond[t["condition"]].append(t["speaker_sim"])
        if t["wer"] is not None:
            by_cond_wer[t["condition"]].append(t["wer"])

    stats = {c: _stats(v) for c, v in by_cond.items()}
    wer_stats = {c: _stats(v) for c, v in by_cond_wer.items()}

    # Baseline-gate verdict: compare original-condition distribution with
    # canonical same-speaker and cross-speaker references (no invented threshold).
    verdict = "INCONCLUSIVE"
    o = stats.get("original", {})
    if o.get("n"):
        same, other = ref_orig_orig["mean"], ref_orig_other["mean"]
        mid = (same + other) / 2
        if o["mean"] is not None and o["mean"] >= mid and o["median"] >= other:
            verdict = "BASELINE_SPEAKER_FAITHFUL"
        else:
            verdict = "BASELINE_NOT_SPEAKER_FAITHFUL"

    out = {"tag": args.tag, "n_trials": len(trials),
           "n_success": len(ok), "failures": dict(failures),
           "sampling": manifest.get("sampling"), "model": manifest.get("model"),
           "license": manifest.get("license"),
           "canonical_ref": {"orig_orig_mean": ref_orig_orig["mean"],
                             "orig_other_mean": ref_orig_other["mean"]},
           "speaker_sim_stats": stats, "wer_stats": wer_stats,
           "baseline_verdict": verdict, "trials": trials}
    with open(results_dir / f"xtts_{args.tag}_results.json", "w") as f:
        json.dump(out, f, indent=1)
    with open(results_dir / f"xtts_{args.tag}_results.csv", "w", newline="") as f:
        wri = csv.DictWriter(f, fieldnames=["speaker", "condition", "prompt_index",
                                            "eval", "speaker_sim", "wer", "duration_s",
                                            "clipping", "nan_inf", "out", "transcript"])
        wri.writeheader()
        for t in ok:
            wri.writerow({k: t.get(k) for k in
                          ["speaker", "condition", "prompt_index", "eval",
                           "speaker_sim", "wer", "duration_s", "clipping",
                           "nan_inf", "out", "transcript"]})
    L = [f"# XTTS-v2 cloning evaluation ({args.tag})", "",
         f"- Model: `{manifest.get('model')}` ({manifest.get('license')})",
         f"- Trials: {len(trials)}, evaluated OK: {len(ok)}, failures: {dict(failures)}",
         f"- Canonical ref: orig-orig mean {ref_orig_orig['mean']}, orig-other mean {ref_orig_other['mean']}",
         "", "## Speaker similarity (source speaker -> clone)",
         "| Condition | N | Mean | Median | Std | Min | Max |",
         "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"]
    for c, s in stats.items():
        L.append(f"| {c} | {s['n']} | {s['mean']} | {s['median']} | {s['std']} | {s['min']} | {s['max']} |")
    L += ["", "## WER (whisper-tiny vs prompt)",
          "| Condition | N | Mean | Median |", "| :--- | :--- | :--- | :--- |"]
    for c, s in wer_stats.items():
        L.append(f"| {c} | {s['n']} | {s['mean']} | {s['median']} |")
    L += ["", "## Per-speaker means",
          "| Speaker | " + " | ".join(f"{c}" for c in sorted(by_cond)) + " |",
          "| :--- | " + " | ".join("---:" for _ in by_cond) + " |"]
    spks = sorted({t["speaker"] for t in ok})
    for s in spks:
        row = []
        for c in sorted(by_cond):
            v = [t["speaker_sim"] for t in ok if t["speaker"] == s and t["condition"] == c]
            row.append(f"{round(float(np.mean(v)),4)} (n={len(v)})" if v else "n/a")
        L.append(f"| {s} | " + " | ".join(row) + " |")
    L += ["", f"## Baseline verdict: `{verdict}`",
          ("Original-condition clones sit with same-speaker similarity "
           "(at/above the midpoint between same-speaker and cross-speaker "
           "canonical means); valid for protection testing."
           if verdict == "BASELINE_SPEAKER_FAITHFUL" else
           "Original-condition clones do NOT reproduce speaker identity "
           "reliably under the current configuration; STOP - do not proceed "
           "to protection-effectiveness claims with this setup.")]
    with open(results_dir / f"xtts_{args.tag}_summary.md", "w") as f:
        f.write("\n".join(L) + "\n")
    logger.info(f"[{args.tag}] verdict={verdict} stats={stats}")


if __name__ == "__main__":
    main()
