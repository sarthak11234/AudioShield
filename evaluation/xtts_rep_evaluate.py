"""
AudioShield XTTS replication: paired statistical evaluation (MAIN .venv).

Reads evaluation/results/xtts_rep_clones/xtts_rep_manifest.json and evaluates
every clone with the project evaluators (ECAPA-TDNN similarity vs the test
speaker's own longest reference, whisper-tiny WER, duration/clipping/NaN-Inf;
source-vs-clone SNR/STOI omitted as not meaningful).

Paired analysis: pair = (speaker, ref_stem, prompt_index), shared across the
5 conditions by construction. Primary estimand per PGD seed s:
    Delta_s = sim(original clone) - sim(protected_seed-s clone)
Reported per seed (complete pairs only): n, mean, SD, 95% t-CI, median, IQR,
paired t (t, p), Wilcoxon signed-rank (W, p), Cohen's dz, sign consistency
(#pairs Delta>0 / n), per-speaker mean Deltas. Same for the unrelated control
(Delta_unrel) as a paired reference frame. Pooled-across-seeds figures are
supplementary (pairs share the original clone across seeds, hence not
independent). No success thresholds are invented.

Outputs:
  evaluation/results/xtts_rep_results.json
  evaluation/results/xtts_rep_results.csv
  evaluation/results/xtts_rep_summary.md

Usage:
  .venv/bin/python evaluation/xtts_rep_evaluate.py --device cpu
"""

import argparse
import csv
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))
sys.path.insert(0, str(ROOT))

from tasks.protect import load_audio  # noqa: E402
from evaluation.metrics import extract_speaker_embedding  # noqa: E402
from evaluation.voice_cloning_eval import compute_wer  # noqa: E402 reuse WER

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("audioshield.xtts_rep_eval")

PGD_SEEDS = [0, 1, 2]


def _dist(values):
    a = np.array(values, dtype=np.float64)
    return {"n": len(a), "mean": round(float(np.mean(a)), 4),
            "std": round(float(np.std(a, ddof=1)), 4) if len(a) > 1 else 0.0,
            "median": round(float(np.median(a)), 4),
            "q25": round(float(np.percentile(a, 25)), 4),
            "q75": round(float(np.percentile(a, 75)), 4),
            "min": round(float(np.min(a)), 4), "max": round(float(np.max(a)), 4)}


def paired_stats(deltas):
    """Paired inference on difference scores (no thresholds)."""
    from scipy import stats as S
    d = np.array(deltas, dtype=np.float64)
    n = len(d)
    out = {"n": n, **_dist(d)}
    out["n_positive"] = int((d > 0).sum())
    out["n_negative"] = int((d < 0).sum())
    if n >= 2:
        t_res = S.ttest_1samp(d, 0.0)
        out["paired_t"] = round(float(t_res.statistic), 4)
        out["paired_t_p"] = float(t_res.pvalue)
        ci = S.t.interval(0.95, n - 1, loc=float(np.mean(d)),
                          scale=float(np.std(d, ddof=1) / np.sqrt(n)))
        out["mean_95ci"] = [round(float(ci[0]), 4), round(float(ci[1]), 4)]
        out["cohens_dz"] = round(float(np.mean(d) / (np.std(d, ddof=1) + 1e-12)), 4)
    if n >= 6:
        try:
            w = S.wilcoxon(d, zero_method="wilcox", alternative="two-sided")
            out["wilcoxon_W"] = float(w.statistic)
            out["wilcoxon_p"] = float(w.pvalue)
        except Exception as e:  # noqa: BLE001
            out["wilcoxon_error"] = str(e)[:200]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clones-dir", default="evaluation/results/xtts_rep_clones")
    ap.add_argument("--results-dir", default="evaluation/results")
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    clones_dir = ROOT / args.clones_dir
    results_dir = ROOT / args.results_dir
    manifest = json.load(open(clones_dir / "xtts_rep_manifest.json"))

    bench = json.load(open(results_dir / "evaluation_results.json"))
    bd = bench["speaker_embedding_distributions"]

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

    def transcribe(wave, sr):
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

    import soundfile as sf

    def own_longest(spk):
        cands = [c for c in (ROOT / "evaluation/datasets/librispeech_benchmark").glob(f"{spk}_*.wav")
                 if "protected" not in c.name]
        return max(cands, key=lambda c: sf.SoundFile(str(c)).frames / sf.SoundFile(str(c)).samplerate)

    gt = {}
    eval_trials = []
    failures = defaultdict(int)
    for t in manifest["trials"]:
        if t.get("status") != "OK":
            failures["synthesis_failure"] += 1
            eval_trials.append({**t, "eval": "SKIPPED_SYNTH_FAIL"})
            continue
        spk = t["speaker"]
        try:
            if spk not in gt:
                w0, s0 = load_audio(str(own_longest(spk)))
                gt[spk] = extract_speaker_embedding(w0, s0, enc)
            w, s = load_audio(t["out"])
            emb = extract_speaker_embedding(w, s, enc)
            sim = round(float(torch.dot(gt[spk], emb).item()), 4)
            hyp = transcribe(w, s)
            wer = round(compute_wer(t["prompt"], hyp), 4) if hyp else None
            eval_trials.append({**t, "eval": "SUCCESS", "speaker_sim": sim,
                                "wer": wer, "transcript": hyp,
                                "duration_s": round(w.shape[-1] / s, 3),
                                "clipping": int((w.abs() > 0.999).sum()),
                                "nan_inf": int(torch.isnan(w).sum() + torch.isinf(w).sum())})
        except Exception as e:  # noqa: BLE001 - classify, never drop
            failures["evaluation_failure"] += 1
            eval_trials.append({**t, "eval": "FAILED", "error": str(e)[:300]})

    ok = [t for t in eval_trials if t.get("eval") == "SUCCESS"]

    # --- condition distributions ---
    cond_sims = defaultdict(list)
    cond_wers = defaultdict(list)
    for t in ok:
        cond_sims[t["condition"]].append(t["speaker_sim"])
        if t["wer"] is not None:
            cond_wers[t["condition"]].append(t["wer"])
    cond_stats = {c: _dist(v) for c, v in sorted(cond_sims.items())}

    # --- paired deltas (complete pairs only) ---
    by_pair = defaultdict(dict)
    for t in ok:
        by_pair[t["pair_id"]][t["condition"]] = t["speaker_sim"]
    pair_results = {}
    for s in PGD_SEEDS:
        key = f"protected_seed{s}"
        ds = [v["original"] - v[key] for v in by_pair.values()
              if "original" in v and key in v]
        pair_results[f"delta_seed{s}"] = paired_stats(ds)
        # per-speaker mean deltas
        spk_d = defaultdict(list)
        for pid, v in by_pair.items():
            if "original" in v and key in v:
                spk_d[pid.split("|")[0]].append(v["original"] - v[key])
        pair_results[f"delta_seed{s}"]["per_speaker_mean"] = {
            sp: round(float(np.mean(v)), 4) for sp, v in sorted(spk_d.items())}
        pair_results[f"delta_seed{s}"]["speakers_positive"] = sum(
            1 for v in spk_d.values() if float(np.mean(v)) > 0)
    du = [v["original"] - v["unrelated"] for v in by_pair.values()
          if "original" in v and "unrelated" in v]
    pair_results["delta_unrelated"] = paired_stats(du)
    # supplementary pooled (non-independent: shared original clone across seeds)
    dall = []
    for v in by_pair.values():
        if "original" not in v:
            continue
        for s in PGD_SEEDS:
            key = f"protected_seed{s}"
            if key in v:
                dall.append(v["original"] - v[key])
    pair_results["delta_pooled_supplementary"] = paired_stats(dall)
    pair_results["delta_pooled_supplementary"]["note"] = (
        "non-independent: the same original clone is reused across seeds; "
        "per-seed analyses are primary.")

    n_pairs = sum(1 for v in by_pair.values()
                  if "original" in v and all(f"protected_seed{s}" in v for s in PGD_SEEDS))
    out = {"n_manifest_trials": len(manifest["trials"]), "n_success": len(ok),
           "failures": dict(failures), "model": manifest.get("model"),
           "license": manifest.get("license"), "sampling": manifest.get("sampling"),
           "pgd_seeds": PGD_SEEDS,
           "canonical_ref": {"orig_orig_mean": bd["orig_orig_stats"]["mean"],
                             "orig_other_mean": bd["orig_other_stats"]["mean"]},
           "condition_stats": cond_stats,
           "wer_means": {c: round(float(np.mean(v)), 4) for c, v in sorted(cond_wers.items()) if v},
           "complete_pairs_all_conditions": n_pairs,
           "paired": pair_results, "trials": eval_trials}
    with open(results_dir / "xtts_rep_results.json", "w") as f:
        json.dump(out, f, indent=1)
    with open(results_dir / "xtts_rep_results.csv", "w", newline="") as f:
        wri = csv.DictWriter(f, fieldnames=["pair_id", "speaker", "ref_stem", "condition",
                                            "prompt_index", "eval", "speaker_sim", "wer",
                                            "duration_s", "clipping", "nan_inf", "out", "transcript"])
        wri.writeheader()
        for t in ok:
            wri.writerow({k: t.get(k) for k in
                          ["pair_id", "speaker", "ref_stem", "condition", "prompt_index",
                           "eval", "speaker_sim", "wer", "duration_s", "clipping",
                           "nan_inf", "out", "transcript"]})

    def fmt_ci(ps):
        ci = ps.get("mean_95ci")
        return f"[{ci[0]:.4f}, {ci[1]:.4f}]" if ci else "n/a"

    def fmt_p(p):
        return f"{p:.4g}" if p is not None else "n/a"

    L = ["# XTTS-v2 replication: 3 references x 3 PGD seeds, paired analysis", "",
         f"- Model: `{manifest.get('model')}` ({manifest.get('license')}); sampling: {manifest.get('sampling')}",
         f"- Trials: {len(manifest['trials'])} manifest, {len(ok)} evaluated OK, failures: {dict(failures)}",
         f"- Complete pairs (original + 3 protected): {n_pairs}",
         f"- Canonical ref: orig-orig {bd['orig_orig_stats']['mean']}, orig-other {bd['orig_other_stats']['mean']}",
         "", "## Condition distributions (source speaker -> clone)",
         "| Condition | N | Mean | Median | Std | Min | Max |",
         "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"]
    for c, s in cond_stats.items():
        L.append(f"| {c} | {s['n']} | {s['mean']} | {s['median']} | {s['std']} | {s['min']} | {s['max']} |")
    L += ["", "## Paired deltas: Delta = sim(original clone) - sim(protected clone)",
          "(complete pairs only; positive Delta = protection reduced clone similarity)",
          "",
          "| Comparison | N pairs | Mean Delta | 95% CI | Median | dz | paired-t (p) | Wilcoxon (p) | Pairs Delta>0 | Speakers +/10 |",
          "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"]
    for s in PGD_SEEDS:
        ps = pair_results[f"delta_seed{s}"]
        L.append(f"| seed{s} | {ps['n']} | {ps['mean']:.4f} | {fmt_ci(ps)} | {ps['median']:.4f} | "
                 f"{ps.get('cohens_dz', 'n/a')} | {ps.get('paired_t', 'n/a')} ({fmt_p(ps.get('paired_t_p'))}) | "
                 f"{ps.get('wilcoxon_W', 'n/a')} ({fmt_p(ps.get('wilcoxon_p'))}) | "
                 f"{ps['n_positive']}/{ps['n']} | {ps['speakers_positive']}/10 |")
    pu = pair_results["delta_unrelated"]
    L.append(f"| unrelated (paired frame) | {pu['n']} | {pu['mean']:.4f} | {fmt_ci(pu)} | {pu['median']:.4f} | "
             f"{pu.get('cohens_dz', 'n/a')} | {pu.get('paired_t', 'n/a')} ({fmt_p(pu.get('paired_t_p'))}) | "
             f"{pu.get('wilcoxon_W', 'n/a')} ({fmt_p(pu.get('wilcoxon_p'))}) | {pu['n_positive']}/{pu['n']} | n/a |")
    pp = pair_results["delta_pooled_supplementary"]
    L.append(f"| pooled seeds (supplementary, non-independent) | {pp['n']} | {pp['mean']:.4f} | {fmt_ci(pp)} | "
             f"{pp['median']:.4f} | {pp.get('cohens_dz', 'n/a')} | {pp.get('paired_t', 'n/a')} ({fmt_p(pp.get('paired_t_p'))}) | "
             f"{pp.get('wilcoxon_W', 'n/a')} ({fmt_p(pp.get('wilcoxon_p'))}) | {pp['n_positive']}/{pp['n']} | n/a |")
    L += ["", "## Per-speaker mean Delta (original - protected)"]
    L.append("| Speaker | " + " | ".join(f"seed{s}" for s in PGD_SEEDS) + " |")
    L.append("| :--- | " + " | ".join("---:" for _ in PGD_SEEDS) + " |")
    for sp in sorted({t["speaker"] for t in ok}):
        L.append("| " + sp + " | " + " | ".join(
            f"{pair_results[f'delta_seed{s}']['per_speaker_mean'].get(sp, 'n/a'):.4f}" for s in PGD_SEEDS) + " |")
    L += ["", "## WER means (whisper-tiny; confounded by XTTS continuation rambling, see §8.2)"]
    for c, m in out["wer_means"].items():
        L.append(f"- {c}: {m}")
    L += ["", "## Interpretation",
          "- CIs and p-values are reported as evidence measures; no success thresholds are invented.",
          "- A consistent positive Delta across seeds/speakers with CIs excluding zero constitutes",
          "  preliminary paired evidence of reduced cloning effectiveness, not proof of prevention.",
          "- Protected clones are expected to sit between the original and unrelated conditions (partial reduction)."]
    with open(results_dir / "xtts_rep_summary.md", "w") as f:
        f.write("\n".join(L) + "\n")
    logger.info("[rep] paired summary written")


if __name__ == "__main__":
    main()
