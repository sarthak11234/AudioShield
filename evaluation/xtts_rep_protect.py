"""
AudioShield XTTS replication: multi-seed protection generation (MAIN .venv).

Generates AudioShield-protected variants of the replication reference set
using the UNMODIFIED protection pipeline (evaluation.benchmark.
run_protection_pipeline: PGD eps=0.02, alpha=0.002, 15 steps, random_start).

"Multiple PGD seeds" = controlling torch CPU RNG state before each call:
  torch.manual_seed(pgd_seed) + single-threaded execution.
The algorithm itself is untouched; only the RNG state varies, which changes
the uniform random-start draw (worker/tasks/pgd_attack.py: uniform_).

Design:
  - 10 canonical speakers x 3 longest references each (deterministic) = 30 refs
  - PGD seeds {0, 1, 2} -> 90 protected files under
    evaluation/results/xtts_rep_protected/seed{S}/{stem}_protected.wav

Outputs:
  evaluation/results/xtts_rep_protected/seed{S}/*.wav
  evaluation/results/xtts_rep_protect_manifest.json (paths + sha256)

Usage:
  .venv/bin/python evaluation/xtts_rep_protect.py
"""

import hashlib
import json
import sys
import time
from pathlib import Path

import soundfile as sf
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))
sys.path.insert(0, str(ROOT))

from evaluation.benchmark import run_protection_pipeline  # noqa: E402 (unmodified pipeline)

DATASET_DIR = ROOT / "evaluation/datasets/librispeech_benchmark"
OUT_BASE = ROOT / "evaluation/results/xtts_rep_protected"
PGD_SEEDS = [0, 1, 2]
REFS_PER_SPEAKER = 3


def longest_refs(dataset_dir: Path, speaker_id: str, k: int):
    cands = sorted([c for c in dataset_dir.glob(f"{speaker_id}_*.wav")
                    if "protected" not in c.name])
    ranked = sorted(cands,
                    key=lambda c: sf.SoundFile(str(c)).frames / sf.SoundFile(str(c)).samplerate,
                    reverse=True)[:k]
    return ranked


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def main():
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT_BASE.mkdir(parents=True, exist_ok=True)

    speakers = sorted({p.name.split("_utt_")[0]
                       for p in DATASET_DIR.glob("*.wav")
                       if "protected" not in p.name})
    print(f"[rep-protect] speakers={speakers}", flush=True)

    entries = []
    t0 = time.time()
    total = len(speakers) * REFS_PER_SPEAKER * len(PGD_SEEDS)
    done = 0
    for spk in speakers:
        for ref in longest_refs(DATASET_DIR, spk, REFS_PER_SPEAKER):
            for seed in PGD_SEEDS:
                out = OUT_BASE / f"seed{seed}" / f"{ref.stem}_protected.wav"
                out.parent.mkdir(parents=True, exist_ok=True)
                torch.manual_seed(seed)  # ONLY RNG control; algorithm untouched
                run_protection_pipeline(str(ref), str(out), device="cpu")
                done += 1
                entries.append({"speaker": spk, "ref": str(ref),
                                "ref_stem": ref.stem, "pgd_seed": seed,
                                "protected": str(out),
                                "sha256": sha256_of(out)})
                print(f"[rep-protect] {done}/{total} {out.name}", flush=True)

    man = {"pgd_seeds": PGD_SEEDS, "refs_per_speaker": REFS_PER_SPEAKER,
           "pipeline": "evaluation.benchmark.run_protection_pipeline (unmodified)",
           "protection": {"epsilon": 0.02, "alpha": 0.002, "num_steps": 15,
                          "random_start": True},
           "elapsed_s": round(time.time() - t0, 1), "files": entries}
    with open(ROOT / "evaluation/results/xtts_rep_protect_manifest.json", "w") as f:
        json.dump(man, f, indent=1)
    print(f"[rep-protect] done: {len(entries)} files in {man['elapsed_s']}s", flush=True)


if __name__ == "__main__":
    main()
