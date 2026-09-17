"""Merge two XTTS replication worker outputs into the canonical replication dir.

Each worker dir (e.g. ``evaluation/results/xtts_rep_clones_a``) holds a subset
of the replication clones (disjoint speaker sets) plus its own
``xtts_rep_manifest.json``. This script merges both workers into the canonical
``evaluation/results/xtts_rep_clones/`` directory:

  * verifies the metadata blocks (model/license/sampling/pgd_seeds/prompts)
    are identical across workers, failing loudly otherwise;
  * copies every ``*.wav`` from both workers into ``--out`` (filenames are
    globally unique: ``{spk}_{refstem}_p{pi}_{cond}.wav``). A same-name
    collision with different bytes fails loudly, *unless* it is exactly the
    dedup case below (same logical trial in both manifests), where the LAST
    occurrence (``--b``) wins;
  * concatenates the trial lists, deduplicating by ``(pair_id, condition)``
    and keeping the LAST occurrence;
  * rewrites every trial's ``out`` path to point at ``--out``;
  * writes the merged ``xtts_rep_manifest.json`` and prints a verification
    report (expected 300 trials, counts by status/condition, missing combos).

Stdlib only (argparse, json, shutil, pathlib). CPU-light: audio is never
decoded; files are only byte-compared and copied.

Example (run from the repo root, after both workers finish)::

    python evaluation/xtts_rep_merge.py \
        --a evaluation/results/xtts_rep_clones_a \
        --b evaluation/results/xtts_rep_clones_b \
        --out evaluation/results/xtts_rep_clones
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

MANIFEST_NAME = "xtts_rep_manifest.json"
META_KEYS = ("model", "license", "sampling", "pgd_seeds", "prompts")
EXPECTED_TRIALS = 300
EXPECTED_DESIGN = "10 speakers x 3 refs x 2 prompts x 5 conditions"


def die(msg):
    print(f"[xtts-rep-merge] ERROR: {msg}", file=sys.stderr)
    raise SystemExit(2)


def load_manifest(worker_dir):
    man_path = worker_dir / MANIFEST_NAME
    if not man_path.is_file():
        die(f"missing manifest: {man_path}")
    try:
        manifest = json.loads(man_path.read_text())
    except json.JSONDecodeError as exc:
        die(f"invalid JSON in {man_path}: {exc}")
    if not isinstance(manifest.get("trials"), list):
        die(f"{man_path} has no 'trials' list")
    return manifest


def trial_key(trial):
    try:
        return (trial["pair_id"], trial["condition"])
    except (KeyError, TypeError) as exc:
        die(f"trial missing required key {exc}: {trial!r}")


def main():
    ap = argparse.ArgumentParser(
        description="Merge two XTTS replication worker dirs into the "
                    "canonical replication dir.")
    ap.add_argument("--a", default="evaluation/results/xtts_rep_clones_a")
    ap.add_argument("--b", default="evaluation/results/xtts_rep_clones_b")
    ap.add_argument("--out", default="evaluation/results/xtts_rep_clones")
    args = ap.parse_args()

    dir_a = Path(args.a)
    dir_b = Path(args.b)
    out_dir = Path(args.out)
    for label, cand in (("--a", dir_a), ("--b", dir_b)):
        if not cand.is_dir():
            die(f"{label} is not a directory: {cand}")
    if dir_a.resolve() == dir_b.resolve():
        die("--a and --b must be different directories")
    if out_dir.resolve() in (dir_a.resolve(), dir_b.resolve()):
        die("--out must differ from --a and --b")

    man_a = load_manifest(dir_a)
    man_b = load_manifest(dir_b)

    for key in META_KEYS:
        if man_a.get(key) != man_b.get(key):
            die(f"metadata mismatch on {key!r}: "
                f"--a={man_a.get(key)!r} --b={man_b.get(key)!r}")

    trials_a = man_a["trials"]
    trials_b = man_b["trials"]

    # Which logical trials reference each wav basename, per worker. Needed so
    # a same-filename/different-bytes collision can be attributed: it is only
    # acceptable when both workers hold the SAME logical trial under that
    # name (the dedup case, where --b as LAST wins).
    refs_a = {}
    for trial in trials_a:
        refs_a.setdefault(Path(trial.get("out") or "").name, set()).add(
            trial_key(trial))
    refs_b = {}
    for trial in trials_b:
        refs_b.setdefault(Path(trial.get("out") or "").name, set()).add(
            trial_key(trial))

    wavs_a = {p.name: p for p in sorted(dir_a.glob("*.wav"))}
    wavs_b = {p.name: p for p in sorted(dir_b.glob("*.wav"))}

    out_dir.mkdir(parents=True, exist_ok=True)
    n_copied = 0
    n_skipped_identical = 0
    n_dedup_overwrite = 0
    for name in sorted(set(wavs_a) | set(wavs_b)):
        src_a = wavs_a.get(name)
        src_b = wavs_b.get(name)
        if src_a is not None and src_b is not None:
            bytes_a = src_a.read_bytes()
            bytes_b = src_b.read_bytes()
            if bytes_a == bytes_b:
                src = src_a
            elif refs_a.get(name) and refs_a.get(name) == refs_b.get(name):
                # Same logical trial synthesized in both workers; dedup keeps
                # the LAST occurrence, i.e. --b wins.
                src = src_b
                n_dedup_overwrite += 1
                print(f"[xtts-rep-merge] dedup wav: {name} differs across "
                      f"workers, keeping --b (LAST)", flush=True)
            else:
                die(f"filename collision with different content: {name} "
                    f"(present in both --a and --b but not the same trial)")
        else:
            src = src_a if src_a is not None else src_b
        dst = out_dir / name
        if dst.is_file():
            if dst.read_bytes() != src.read_bytes():
                die(f"destination collision with different content: {dst} "
                    f"(stale --out; remove it or use a fresh dir)")
            n_skipped_identical += 1
            continue
        shutil.copy2(src, dst)
        n_copied += 1

    # Concatenate and deduplicate by (pair_id, condition), LAST occurrence
    # wins. Dict insertion order keeps --a's order, appending new --b keys.
    n_raw = len(trials_a) + len(trials_b)
    merged = {}
    for trial in trials_a + trials_b:
        merged[trial_key(trial)] = dict(trial)
    trials = list(merged.values())
    n_dedup = n_raw - len(trials)

    out_abs = out_dir.resolve()
    for trial in trials:
        if trial.get("status") == "OK":
            wav_name = Path(trial.get("out") or "").name
            if not wav_name or not (out_dir / wav_name).is_file():
                die(f"OK trial {trial_key(trial)} references missing clone "
                    f"{wav_name!r} (not found in --a, --b, or --out)")
        if trial.get("out"):
            trial["out"] = str(out_abs / Path(trial["out"]).name)

    merged_manifest = {k: v for k, v in man_a.items() if k != "trials"}
    merged_manifest["trials"] = trials
    with open(out_dir / MANIFEST_NAME, "w") as fh:
        json.dump(merged_manifest, fh, indent=1)

    # ---- verification report ----
    pair_ids = sorted({t["pair_id"] for t in trials_a + trials_b})
    conditions = sorted({t["condition"] for t in trials_a + trials_b})
    present = set(merged)
    missing = [(pid, cond) for pid in pair_ids for cond in conditions
               if (pid, cond) not in present]
    by_status = {}
    by_condition = {}
    for trial in trials:
        by_status[trial.get("status")] = by_status.get(trial.get("status"),
                                                       0) + 1
        by_condition[trial.get("condition")] = by_condition.get(
            trial.get("condition"), 0) + 1

    print(f"[xtts-rep-merge] workers: --a {len(trials_a)} trials / "
          f"{len(wavs_a)} wavs, --b {len(trials_b)} trials / "
          f"{len(wavs_b)} wavs")
    print(f"[xtts-rep-merge] wavs: {n_copied} copied, "
          f"{n_skipped_identical} skipped (identical), "
          f"{n_dedup_overwrite} dedup-overwrites (--b wins)")
    print(f"[xtts-rep-merge] trials: {n_raw} raw -> {len(trials)} merged "
          f"({n_dedup} duplicates dropped, LAST kept)")
    print(f"[xtts-rep-merge] trials: {len(trials)}/{EXPECTED_TRIALS} "
          f"expected ({EXPECTED_DESIGN})")
    print("[xtts-rep-merge] by status: "
          + ", ".join(f"{k}={v}" for k, v in sorted(by_status.items(),
                                                    key=str)))
    print("[xtts-rep-merge] by condition: "
          + ", ".join(f"{k}={v}" for k, v in sorted(by_condition.items(),
                                                    key=str)))
    print(f"[xtts-rep-merge] combos: {len(present)}/"
          f"{len(pair_ids) * len(conditions)} present "
          f"({len(pair_ids)} pair_ids x {len(conditions)} conditions)")
    if missing:
        print(f"[xtts-rep-merge] INCOMPLETE: missing {len(missing)} "
              f"(pair_id, condition) combos:")
        for pid, cond in missing:
            print(f"[xtts-rep-merge]   MISSING {pid} | {cond}")
    else:
        print("[xtts-rep-merge] COMPLETE: all (pair_id, condition) combos "
              "present")


if __name__ == "__main__":
    main()
