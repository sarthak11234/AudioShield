"""
AudioShield XTTS replication: synthesis driver (ISOLATED xtts venv).

Synthesizes clones for the replication design:
  10 speakers x 3 references x 2 prompts x 5 conditions
  (original, protected/seed0, protected/seed1, protected/seed2, unrelated)
  = 300 clones.

Pairing: every (speaker, ref_stem, prompt_index) quintuplet shares one
pair_id. RNG fairness across conditions: before EACH synthesis, torch+numpy+
python-random are reseeded from a stable hash of
  f"{speaker}|{ref_stem}|{prompt_index}"
(i.e. identical RNG setup for all conditions of a pair; trajectories diverge
only via the differing reference audio — no systematic RNG bias).

Protected inputs come from evaluation/results/xtts_rep_protected/seed{S}/
(written by evaluation/xtts_rep_protect.py in the main venv).

Model/settings identical to the prior XTTS run: XTTS-v2, coqui-TTS 0.22.0,
CPML non-commercial (COQUI_TOS_AGREED=1), CPU, same XTTS_KWARGS.

Usage (isolated env):
  COQUI_TOS_AGREED=1 ~/.venvs/audioshield-xtts/bin/python evaluation/xtts_rep_synthesize.py
"""

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent

MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
MODEL_LICENSE = "CPML (Coqui Public Model License)"

PROMPTS = [
    "The quick brown fox jumps over the lazy dog.",
    "AudioShield provides adversarial voice protection for human speech.",
]
PGD_SEEDS = [0, 1, 2]

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


def pair_seed(speaker: str, ref_stem: str, prompt_index: int) -> int:
    h = hashlib.sha256(f"{speaker}|{ref_stem}|{prompt_index}".encode()).hexdigest()
    return int(h[:8], 16)


def reseed(seed: int):
    torch.manual_seed(seed)
    np.random.seed(seed % (2 ** 32))
    random.seed(seed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-dir", default="evaluation/datasets/librispeech_benchmark")
    ap.add_argument("--protected-base", default="evaluation/results/xtts_rep_protected")
    ap.add_argument("--out-dir", default="evaluation/results/xtts_rep_clones")
    ap.add_argument("--speakers", default=None,
                    help="comma-separated subset to synthesize (unrelated refs still drawn from the full set)")
    args = ap.parse_args()

    dataset_dir = ROOT / args.dataset_dir
    prot_base = ROOT / args.protected_base
    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    from TTS.api import TTS
    _allowlist_tts_configs()
    tts = TTS(MODEL_NAME, gpu=False)
    print("[xtts-rep] model loaded", flush=True)

    import soundfile as sf

    def refs_of(spk: str):
        cands = sorted([c for c in dataset_dir.glob(f"{spk}_*.wav")
                        if "protected" not in c.name])
        ranked = sorted(
            cands,
            key=lambda c: sf.SoundFile(str(c)).frames / sf.SoundFile(str(c)).samplerate,
            reverse=True)[:3]
        return ranked

    speakers = sorted({p.name.split("_utt_")[0]
                       for p in dataset_dir.glob("*.wav")
                       if "protected" not in p.name})
    all_speakers = speakers
    if args.speakers:
        want = {s.strip() for s in args.speakers.split(",")}
        speakers = [s for s in all_speakers if s in want]
        assert speakers, f"no matching speakers for {want}"
    print(f"[xtts-rep] speakers: {speakers} (unrelated pool: full set)", flush=True)

    # Merge with any previous partial run (re-running overwrites same pair_ids).
    man_path = out_dir / "xtts_rep_manifest.json"
    prev = []
    if man_path.exists():
        try:
            prev = json.load(open(man_path)).get("trials", [])
        except Exception:
            prev = []
    done_ids = {t["pair_id"] + "|" + t["condition"] for t in prev if t.get("status") == "OK"}

    manifest = {"model": MODEL_NAME, "license": MODEL_LICENSE,
                "tts_package": "0.22.0", "sampling": XTTS_KWARGS,
                "pgd_seeds": PGD_SEEDS, "prompts": PROMPTS,
                "pair_rng": "torch+numpy+random reseeded per (speaker,ref,prompt) for all conditions",
                "trials": prev}
    n_new = 0
    for spk in speakers:
        refs = refs_of(spk)
        others = [s for s in all_speakers if s != spk]
        unrel_ref = refs_of(others[0])[0]
        for ref in refs:
            cond_src = {"original": ref,
                        "unrelated": unrel_ref}
            for seed in PGD_SEEDS:
                cond_src[f"protected_seed{seed}"] = (
                    prot_base / f"seed{seed}" / f"{ref.stem}_protected.wav")
            for pi, text in enumerate(PROMPTS, 1):
                pair_id = f"{spk}|{ref.stem}|p{pi}"
                for cond, src in cond_src.items():
                    if pair_id + "|" + cond in done_ids:
                        continue
                    out = out_dir / f"{spk}_{ref.stem}_p{pi}_{cond}.wav"
                    rec = {"pair_id": pair_id, "speaker": spk,
                           "ref_stem": ref.stem, "prompt_index": pi,
                           "prompt": text, "condition": cond,
                           "ref": str(src), "out": str(out)}
                    if not src.exists():
                        manifest["trials"].append(
                            {**rec, "status": "FAILED",
                             "reason": f"missing reference {src.name}"})
                        print(f"[xtts-rep] SKIP missing {src}", flush=True)
                        continue
                    try:
                        reseed(pair_seed(spk, ref.stem, pi))
                        tts.tts_to_file(text=text, speaker_wav=str(src),
                                        file_path=str(out), **XTTS_KWARGS)
                        manifest["trials"].append({**rec, "status": "OK"})
                        n_new += 1
                        print(f"[xtts-rep] OK {out.name}", flush=True)
                    except Exception as e:  # noqa: BLE001 - record, never drop
                        manifest["trials"].append(
                            {**rec, "status": "FAILED", "reason": str(e)[:300]})
                        print(f"[xtts-rep] FAIL {pair_id} {cond}: {e}", flush=True)
                    with open(man_path, "w") as f:
                        json.dump(manifest, f, indent=1)
    with open(man_path, "w") as f:
        json.dump(manifest, f, indent=1)
    ok = sum(1 for t in manifest["trials"] if t.get("status") == "OK")
    print(f"[xtts-rep] done: {ok}/{len(manifest['trials'])} OK ({n_new} new)", flush=True)


if __name__ == "__main__":
    main()
