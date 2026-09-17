"""
AudioShield XTTS-v2 cloning driver (runs in the ISOLATED xtts venv).

Model: Coqui XTTS-v2 (tts_models/multilingual/multi-dataset/xtts_v2)
  via coqui-TTS 0.22.0 `TTS.api`. License: CPML (Coqui Public Model License).
  Weights auto-downloaded by the TTS model manager at runtime (~1.9 GB),
  NOT committed to Git.

This script ONLY synthesizes. All evaluation (ECAPA/WER) runs in the main
.venv via evaluation/xtts_evaluate.py against the manifest written here.

Phase 4 (baseline gate): original reference -> XTTS -> clone, one reference
  (deterministically: longest utterance per speaker) x fixed prompts.
Phase 5 adds protected references with identical settings (see --conditions).

Determinism: torch manual seed set; sampling kwargs pinned in XTTS_KWARGS
  (verified against installed TTS 0.22.0 API before the recorded run).
CPU inference (gpu=False).

Usage (isolated env):
  ~/.venvs/audioshield-xtts/bin/python evaluation/xtts_synthesize.py \
      --dataset-dir evaluation/datasets/librispeech_benchmark \
      --protected-dir evaluation/results/protected_audio \
      --out-dir evaluation/results/xtts_clones \
      --conditions original[,protected,unrelated] [--seed 0]
"""

import argparse
import json
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent

MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
MODEL_LICENSE = "CPML (Coqui Public Model License)"
TTS_PKG_VERSION = "0.22.0"

# Fixed synthesis prompts (identical across conditions).
PROMPTS = [
    "The quick brown fox jumps over the lazy dog.",
    "AudioShield provides adversarial voice protection for human speech.",
]

# Sampling/behaviour kwargs - pinned after API inspection (see run notes).
XTTS_KWARGS = {
    "language": "en",
    "temperature": 0.65,
    "top_k": 50,
    "top_p": 0.85,
    "length_penalty": 1.0,
    "repetition_penalty": 2.0,
    "speed": 1.0,
}


def _allowlist_tts_configs():
    """Allowlist TTS config classes for torch>=2.6 weights_only-safe load.

    torch 2.6+ defaults torch.load to weights_only=True; TTS 0.22.0 checkpoints
    reference Coqpit config classes, so every config subclass in the TTS
    package is allowlisted (weights are the official Coqui release, trusted).
    """
    import pkgutil
    import importlib
    import inspect
    import torch.serialization
    import TTS.tts.configs
    import TTS.config
    from coqpit import Coqpit
    classes = set()
    for pkg in (TTS.tts.configs, TTS.config):
        for m in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
            try:
                mod = importlib.import_module(m.name)
            except Exception:
                continue
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                try:
                    if issubclass(obj, Coqpit) and obj is not Coqpit:
                        classes.add(obj)
                except Exception:
                    pass
    torch.serialization.add_safe_globals(list(classes))


def pick_reference(dataset_dir: Path, speaker_id: str) -> Path:
    """Deterministically pick the longest utterance file for a speaker."""
    import soundfile as sf
    cands = sorted(dataset_dir.glob(f"{speaker_id}_*.wav"))
    cands = [c for c in cands if "protected" not in c.name]
    assert cands, f"no references for {speaker_id}"
    best, best_dur = cands[0], -1.0
    for c in cands:
        with sf.SoundFile(str(c)) as f:
            dur = len(f) / f.samplerate
        if dur > best_dur:
            best, best_dur = c, dur
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-dir", default="evaluation/datasets/librispeech_benchmark")
    ap.add_argument("--protected-dir", default="evaluation/results/protected_audio")
    ap.add_argument("--out-dir", default="evaluation/results/xtts_clones")
    ap.add_argument("--conditions", default="original",
                    help="comma list of original,protected,unrelated")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    torch.manual_seed(args.seed)

    dataset_dir = ROOT / args.dataset_dir
    protected_dir = ROOT / args.protected_dir
    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    conditions = [c.strip() for c in args.conditions.split(",")]

    from TTS.api import TTS
    _allowlist_tts_configs()
    t0 = time.time()
    tts = TTS(MODEL_NAME, gpu=False)
    print(f"[xtts] model loaded in {time.time()-t0:.1f}s", flush=True)

    speakers = sorted({p.name.split("_utt_")[0]
                       for p in dataset_dir.glob("*.wav")
                       if "protected" not in p.name})
    print(f"[xtts] speakers: {speakers}", flush=True)

    manifest = {"model": MODEL_NAME, "license": MODEL_LICENSE,
                "tts_package": TTS_PKG_VERSION, "seed": args.seed,
                "sampling": XTTS_KWARGS, "trials": []}
    for spk in speakers:
        ref = pick_reference(dataset_dir, spk)
        prot = protected_dir / f"{ref.stem}_protected.wav"
        others = [s for s in speakers if s != spk]
        unrel = pick_reference(dataset_dir, others[0])
        cond_map = {"original": ref,
                    "protected": prot,
                    "unrelated": unrel}
        for cond in conditions:
            src = cond_map[cond]
            if not src.exists():
                print(f"[xtts] SKIP missing {cond} ref {src}", flush=True)
                manifest["trials"].append(
                    {"speaker": spk, "condition": cond, "status": "FAILED",
                     "reason": f"missing reference {src.name}",
                     "ref": str(src), "out": None})
                continue
            for pi, text in enumerate(PROMPTS, 1):
                out = out_dir / f"{spk}_{ref.stem}_p{pi}_{cond}.wav"
                try:
                    tts.tts_to_file(text=text, speaker_wav=str(src),
                                    file_path=str(out), **XTTS_KWARGS)
                    manifest["trials"].append(
                        {"speaker": spk, "condition": cond, "status": "OK",
                         "prompt_index": pi, "prompt": text,
                         "ref": str(src), "out": str(out)})
                    print(f"[xtts] OK {out.name}", flush=True)
                except Exception as e:  # noqa: BLE001 - record all failures
                    manifest["trials"].append(
                        {"speaker": spk, "condition": cond, "status": "FAILED",
                         "reason": str(e)[:300], "prompt_index": pi,
                         "prompt": text, "ref": str(src),
                         "out": str(out)})
                    print(f"[xtts] FAIL {spk} {cond} p{pi}: {e}", flush=True)

    # Merge with previous runs (re-run of a condition replaces its trials).
    man_path = out_dir / "xtts_manifest.json"
    prev = []
    if man_path.exists():
        try:
            prev = json.load(open(man_path)).get("trials", [])
        except Exception:
            prev = []
    prev = [t for t in prev if t.get("condition") not in conditions]
    manifest["trials"] = prev + manifest["trials"]
    with open(man_path, "w") as f:
        json.dump(manifest, f, indent=1)
    ok = sum(1 for t in manifest["trials"] if t["status"] == "OK")
    print(f"[xtts] done: {ok}/{len(manifest['trials'])} OK", flush=True)


if __name__ == "__main__":
    main()
