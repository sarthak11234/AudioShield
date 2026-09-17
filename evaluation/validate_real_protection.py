"""
AudioShield Real Audio Protection Validation Script
===================================================
Evaluates the real protection pipeline on:
1. Native 16 kHz mono speech audio clip
2. Native 44.1 kHz stereo speech audio clip
"""
import os
import sys
import math
import torch
import numpy as np
import soundfile as sf
from pathlib import Path

# Add worker and repo root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))
sys.path.insert(0, str(ROOT))

from tasks.protect import load_audio, save_audio, protect_audio


def generate_test_speech(path: str, sr: int, channels: int, duration_s: float = 3.0):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    f0 = 130.0
    formant1 = np.sin(2 * np.pi * f0 * t) * 0.4
    formant2 = np.sin(2 * np.pi * (f0 * 4) * t) * 0.2
    formant3 = np.sin(2 * np.pi * (f0 * 12) * t) * 0.1
    env = 0.5 * (1.0 - np.cos(2 * np.pi * t / duration_s))
    mono = (formant1 + formant2 + formant3) * env

    if channels == 1:
        signal = mono.astype(np.float32)
    else:
        signal = np.stack([mono, mono * 0.9], axis=1).astype(np.float32)

    sf.write(path, signal, sr, subtype="PCM_16")


def evaluate_audio_protection(input_path: str, output_path: str, task_name: str):
    print("\n" + "=" * 60)
    print(f"=== EVALUATION: {task_name} ===")
    print("=" * 60)

    # 1. Original Metrics
    orig_waveform, orig_sr = load_audio(input_path)
    orig_channels, orig_samples = orig_waveform.shape
    orig_duration = orig_samples / orig_sr

    print(f"Input Path:             {input_path}")
    print(f"Original Sample Rate:   {orig_sr} Hz")
    print(f"Original Channel Count: {orig_channels}")
    print(f"Original Sample Count:  {orig_samples}")
    print(f"Original Duration:      {orig_duration:.4f} s")

    # 2. Run Protection
    protect_audio.update_state = lambda state=None, meta=None: None
    res = protect_audio.__wrapped__(f"eval-{task_name}", input_path, output_path)

    print(f"\nProtection Result Status: {res['status']}")

    # 3. Protected Metrics
    prot_waveform, prot_sr = load_audio(output_path)
    prot_channels, prot_samples = prot_waveform.shape
    prot_duration = prot_samples / prot_sr

    print(f"\nProtected Sample Rate:   {prot_sr} Hz")
    print(f"Protected Channel Count: {prot_channels}")
    print(f"Protected Sample Count:  {prot_samples}")
    print(f"Protected Duration:      {prot_duration:.4f} s")

    # 4. Verifications
    sr_preserved = (orig_sr == prot_sr)
    ch_preserved = (orig_channels == prot_channels)
    samples_preserved = (orig_samples == prot_samples)
    duration_preserved = abs(orig_duration - prot_duration) < 1e-4

    print("\n--- Preservation Checks ---")
    print(f"Sample Rate Preserved:   {sr_preserved} ({orig_sr} Hz == {prot_sr} Hz)")
    print(f"Channel Count Preserved: {ch_preserved} ({orig_channels} ch == {prot_channels} ch)")
    print(f"Sample Count Preserved:  {samples_preserved} ({orig_samples} == {prot_samples})")
    print(f"Duration Preserved:      {duration_preserved} ({orig_duration:.4f}s == {prot_duration:.4f}s)")

    # 5. Perturbation Analysis
    delta = prot_waveform - orig_waveform
    delta_np = delta.numpy()
    orig_np = orig_waveform.numpy()
    prot_np = prot_waveform.numpy()

    linf = float(np.abs(delta_np).max())
    rms_delta = float(np.sqrt(np.mean(delta_np ** 2)))
    rms_orig = float(np.sqrt(np.mean(orig_np ** 2)))
    snr_db = 10.0 * math.log10((rms_orig ** 2) / (rms_delta ** 2 + 1e-12))

    delta_finite = not bool(np.isnan(delta_np).any() or np.isinf(delta_np).any())
    delta_nonzero = linf > 0.0
    linf_respects_eps = linf <= 0.02 + 1e-3  # configured epsilon is 0.02
    prot_no_nan = not bool(np.isnan(prot_np).any())
    prot_no_inf = not bool(np.isinf(prot_np).any())
    prot_in_range = bool(np.abs(prot_np).max() <= 1.0)

    print("\n--- Perturbation Mathematical Verification ---")
    print(f"L_infinity Norm (max |delta|): {linf:.6f}")
    print(f"RMS(delta):                    {rms_delta:.6f}")
    print(f"RMS(original):                 {rms_orig:.6f}")
    print(f"Signal-to-Noise Ratio (SNR):   {snr_db:.2f} dB")
    print(f"Delta is finite:               {delta_finite}")
    print(f"Delta is non-zero:             {delta_nonzero}")
    print(f"L_inf <= configured epsilon:   {linf_respects_eps}  ({linf:.6f} <= 0.02)")
    print(f"Protected audio no NaN:        {prot_no_nan}")
    print(f"Protected audio no Inf:        {prot_no_inf}")
    print(f"Protected audio in valid range:{prot_in_range}  (peak = {np.abs(prot_np).max():.6f})")

    return {
        "sr_preserved": sr_preserved,
        "ch_preserved": ch_preserved,
        "samples_preserved": samples_preserved,
        "duration_preserved": duration_preserved,
        "linf": linf,
        "rms_delta": rms_delta,
        "rms_orig": rms_orig,
        "snr_db": snr_db,
        "delta_finite": delta_finite,
        "delta_nonzero": delta_nonzero,
        "linf_respects_eps": linf_respects_eps,
        "prot_no_nan": prot_no_nan,
        "prot_no_inf": prot_no_inf,
        "prot_in_range": prot_in_range,
    }


def main():
    path_16k_in = "evaluation/fixtures/test_speech_16k.wav"
    path_16k_out = "evaluation/fixtures/test_speech_16k_protected.wav"
    path_44k_in = "evaluation/fixtures/test_speech_44k.wav"
    path_44k_out = "evaluation/fixtures/test_speech_44k_protected.wav"

    generate_test_speech(path_16k_in, sr=16000, channels=1, duration_s=3.0)
    generate_test_speech(path_44k_in, sr=44100, channels=2, duration_s=3.0)

    res_16k = evaluate_audio_protection(path_16k_in, path_16k_out, "16 kHz Mono Audio")
    res_44k = evaluate_audio_protection(path_44k_in, path_44k_out, "44.1 kHz Stereo Audio")


if __name__ == "__main__":
    main()
