"""
AudioShield Evaluation Runner
==============================
Benchmark the full protection pipeline against reference audio clips.

Usage:
  cd AudioShield
  python evaluation/run_eval.py --input-dir /path/to/audio_clips/ --output results.json

The runner:
  1. Loads each audio file from input_dir
  2. Runs the full protect_audio worker logic (locally, not via Celery)
  3. Computes fidelity + attack metrics for each file
  4. Writes a JSON report with per-file and aggregate results

Acceptance Criteria (MVP):
  - SNR >= 28 dB
  - max(|delta|) <= epsilon (default: 0.015)
  - No NaN/Inf in output
  - Output sample count matches input within ±1 sample
"""
import argparse
import dataclasses
import json
import logging
import math
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import List

import torch
import numpy as np

# Allow running from repo root
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "worker"))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("audioshield.eval")


def _load_audio_for_eval(path: str):
    """Load audio using the worker's own loader for consistency."""
    from tasks.protect import load_audio
    return load_audio(path)


def _run_protection(input_path: str, output_path: str, device: str = "cpu"):
    """
    Run the full dual-rate protection pipeline in-process.
    Returns (protected_waveform, native_sr) or raises.
    """
    from tasks.protect import load_audio, save_audio
    from tasks.chunker import chunk_audio, stitch_audio
    from tasks.pgd_attack import pgd_attack
    import torchaudio

    HUBERT_SR = 16000

    master, native_sr = load_audio(input_path)
    num_channels = master.shape[0]
    native_len = master.shape[-1]

    # Downmix to mono 16 kHz
    mono = master.mean(dim=0, keepdim=True)
    if native_sr != HUBERT_SR:
        mono = torchaudio.transforms.Resample(native_sr, HUBERT_SR)(mono)

    total_16k = mono.shape[-1]
    chunks = chunk_audio(mono, HUBERT_SR, max_duration=10.0, overlap_duration=0.05)

    delta_chunks = []
    for chunk_item in chunks:
        chunk, c_start, c_end = chunk_item[0], chunk_item[1], chunk_item[2]
        is_first = chunk_item[3] if len(chunk_item) > 3 else (c_start == 0)
        is_last  = chunk_item[4] if len(chunk_item) > 4 else (c_end == total_16k)

        orig_1d = chunk.squeeze(0).cpu()
        prot = pgd_attack(orig_1d, sample_rate=HUBERT_SR, epsilon=0.02, alpha=0.002, num_steps=15, device=device)

        if prot.shape[-1] != orig_1d.shape[-1]:
            prot = prot[..., :orig_1d.shape[-1]]

        delta = (prot - orig_1d).unsqueeze(0)
        delta_chunks.append((delta, c_start, c_end, is_first, is_last))

    delta_16k = stitch_audio(delta_chunks, total_16k, sample_rate=HUBERT_SR, channels=1)

    if native_sr != HUBERT_SR:
        delta_native = torchaudio.transforms.Resample(HUBERT_SR, native_sr)(delta_16k)
    else:
        delta_native = delta_16k

    # Trim/pad to exact native length
    d_len = delta_native.shape[-1]
    if d_len > native_len:
        delta_native = delta_native[..., :native_len]
    elif d_len < native_len:
        delta_native = torch.cat([delta_native, torch.zeros(1, native_len - d_len)], dim=-1)

    # Final native-rate projection
    delta_native = torch.clamp(delta_native, -0.02, 0.02)

    protected = master + delta_native.expand(num_channels, -1)
    protected = torch.clamp(protected, -0.999, 0.999)

    save_audio(output_path, protected, native_sr)
    return protected, native_sr


def _report_to_dict(report) -> dict:
    """Convert EvaluationReport dataclass to plain dict for JSON serialization."""
    from evaluation.metrics import EvaluationReport
    d = dataclasses.asdict(report)
    # Replace nan/inf with None for JSON compliance
    def clean(v):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        if isinstance(v, dict):
            return {k: clean(vv) for k, vv in v.items()}
        return v
    return {k: clean(v) for k, v in d.items()}


def run_benchmark(
    input_dir: str,
    output_json: str,
    epsilon: float = 0.015,
    snr_floor_db: float = 28.0,
    device: str = "cpu",
    use_hubert_metrics: bool = False,
):
    from evaluation.metrics import evaluate_pair

    input_path = Path(input_dir)
    audio_files = sorted(
        f for f in input_path.iterdir()
        if f.suffix.lower() in (".wav", ".mp3", ".flac")
    )

    if not audio_files:
        logger.error("No audio files found in %s", input_dir)
        return

    logger.info("Found %d audio files to evaluate.", len(audio_files))

    hubert_model = None
    if use_hubert_metrics:
        from tasks.pgd_attack import load_hubert
        hubert_model = load_hubert(device)
        logger.info("HuBERT model loaded for attack metrics.")

    reports = []
    failures = []

    for audio_file in audio_files:
        logger.info("─── Evaluating: %s ───", audio_file.name)
        t0 = time.time()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "protected.wav")
            try:
                original, sr = _load_audio_for_eval(str(audio_file))
                protected, out_sr = _run_protection(str(audio_file), output_path, device=device)

                report = evaluate_pair(
                    original=original,
                    protected=protected,
                    sample_rate=sr,
                    filename=audio_file.name,
                    model=hubert_model,
                    epsilon=epsilon,
                    snr_floor_db=snr_floor_db,
                )

                elapsed = time.time() - t0
                status = "✓ PASS" if (report.passes_snr_floor and report.passes_linf_bound) else "✗ FAIL"
                logger.info(
                    "%s %s | SNR: %.1f dB | max|δ|: %.5f | %.1f s",
                    status, audio_file.name,
                    report.fidelity.snr_db, report.attack.max_delta, elapsed
                )
                reports.append(_report_to_dict(report))

            except Exception as e:
                logger.error("FAILED to process %s: %s", audio_file.name, e, exc_info=True)
                failures.append({"filename": audio_file.name, "error": str(e)})

    # Aggregate statistics
    snr_values = [r["fidelity"]["snr_db"] for r in reports if r["fidelity"]["snr_db"] is not None]
    max_delta_values = [r["attack"]["max_delta"] for r in reports if r.get("attack") and r["attack"]["max_delta"] is not None]

    aggregate = {
        "total_files": len(audio_files),
        "processed": len(reports),
        "failed": len(failures),
        "avg_snr_db": round(sum(snr_values) / len(snr_values), 2) if snr_values else None,
        "min_snr_db": round(min(snr_values), 2) if snr_values else None,
        "avg_max_delta": round(sum(max_delta_values) / len(max_delta_values), 6) if max_delta_values else None,
        "max_max_delta": round(max(max_delta_values), 6) if max_delta_values else None,
        "pass_snr": sum(1 for r in reports if r.get("passes_snr_floor")),
        "pass_linf": sum(1 for r in reports if r.get("passes_linf_bound")),
        "epsilon": epsilon,
        "snr_floor_db": snr_floor_db,
    }

    output = {
        "aggregate": aggregate,
        "per_file": reports,
        "failures": failures,
    }

    output_path = Path(output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    logger.info("")
    logger.info("═══ Evaluation Complete ═══")
    logger.info("Processed: %d / %d files", len(reports), len(audio_files))
    if snr_values:
        logger.info("Average SNR: %.1f dB (floor: %.1f dB)", aggregate["avg_snr_db"], snr_floor_db)
        logger.info("Max |δ|:     %.5f (bound: %.5f)", aggregate["max_max_delta"], epsilon)
    logger.info("Report written to: %s", output_json)


def main():
    parser = argparse.ArgumentParser(description="AudioShield Evaluation Runner")
    parser.add_argument(
        "--input-dir", required=True,
        help="Directory containing reference audio files (WAV/MP3/FLAC)"
    )
    parser.add_argument(
        "--output", default="evaluation_report.json",
        help="Output JSON report path (default: evaluation_report.json)"
    )
    parser.add_argument(
        "--epsilon", type=float, default=0.015,
        help="L-infinity acceptance bound (default: 0.015)"
    )
    parser.add_argument(
        "--snr-floor", type=float, default=28.0,
        help="Minimum acceptable SNR in dB (default: 28.0)"
    )
    parser.add_argument(
        "--device", default="cpu",
        choices=["cpu", "cuda", "auto"],
        help="PyTorch device for PGD computation (default: cpu)"
    )
    parser.add_argument(
        "--hubert-metrics", action="store_true",
        help="Include HuBERT feature distortion metrics (requires model download)"
    )
    args = parser.parse_args()

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Using device: %s", device)

    run_benchmark(
        input_dir=args.input_dir,
        output_json=args.output,
        epsilon=args.epsilon,
        snr_floor_db=args.snr_floor,
        device=device,
        use_hubert_metrics=args.hubert_metrics,
    )


if __name__ == "__main__":
    main()
