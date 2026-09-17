"""
AudioShield Comprehensive HuBERT Representation & Native Clamp Audit Script
=============================================================================
Evaluates:
  1. Audio dimensional & quality preservation (SR, channels, samples, duration, SNR, SI-SDR, peak, clips, NaN/Inf).
  2. HuBERT representation distortion (Layer 12 / last_hidden_state):
     - Cosine similarity
     - Cosine distance (1 - Cosine Sim)
     - L2 distance
     - Normalized L2 distance (||prot - orig||_2 / ||orig||_2)
  3. Comparative analysis: WITH native-rate clamp vs WITHOUT native-rate clamp.
  4. PGD autograd differentiability verification.
"""
import os
import sys
import math
import tempfile
import torch
import torch.nn.functional as F
import numpy as np
import soundfile as sf
import torchaudio
from pathlib import Path

# Add repo root and worker to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))
sys.path.insert(0, str(ROOT))

from tasks.protect import load_audio, save_audio, protect_audio
from tasks.pgd_attack import load_hubert, pgd_attack
from tasks.chunker import chunk_audio, stitch_audio
from evaluation.metrics import compute_snr, compute_si_sdr, compute_fidelity_metrics


def generate_fixture(path: str, sr: int, channels: int, duration_s: float = 3.0):
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


def extract_hubert_features(waveform: torch.Tensor, sample_rate: int, model):
    """Extract HuBERT last_hidden_state (Layer 12) representation."""
    model.eval()
    HUBERT_SR = 16000
    with torch.no_grad():
        mono = waveform.mean(dim=0, keepdim=True) if waveform.dim() == 2 else waveform.unsqueeze(0)
        if sample_rate != HUBERT_SR:
            mono = torchaudio.transforms.Resample(sample_rate, HUBERT_SR)(mono)
        mono_norm = (mono - mono.mean()) / (mono.std() + 1e-7)
        out = model(mono_norm)
        return out.last_hidden_state  # shape: (1, frames, 768)


def run_protection_pipeline(input_path: str, output_path: str, with_native_clamp: bool = True):
    """Run dual-rate protection pipeline with optional native clamp toggle."""
    HUBERT_SR = 16000
    device = "cpu"

    master, native_sr = load_audio(input_path)
    num_channels = master.shape[0]
    native_len = master.shape[-1]

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

    d_len = delta_native.shape[-1]
    if d_len > native_len:
        delta_native = delta_native[..., :native_len]
    elif d_len < native_len:
        delta_native = torch.cat([delta_native, torch.zeros(1, native_len - d_len)], dim=-1)

    if with_native_clamp:
        delta_native = torch.clamp(delta_native, -0.02, 0.02)

    protected = master + delta_native.expand(num_channels, -1)
    protected = torch.clamp(protected, -0.999, 0.999)

    save_audio(output_path, protected, native_sr)
    return protected, native_sr


def audit_fixture(input_path: str, output_dir: str, config_name: str, hubert_model):
    print("\n" + "=" * 75)
    print(f"=== AUDIT CONFIGURATION: {config_name} ===")
    print("=" * 75)

    out_with_clamp = os.path.join(output_dir, f"{config_name}_clamped.wav")
    out_no_clamp   = os.path.join(output_dir, f"{config_name}_unclamped.wav")

    # Run with clamp
    prot_clamped, sr = run_protection_pipeline(input_path, out_with_clamp, with_native_clamp=True)
    # Run without clamp
    prot_unclamped, _ = run_protection_pipeline(input_path, out_no_clamp, with_native_clamp=False)

    orig, orig_sr = load_audio(input_path)

    # 1. Dimensional Preservation (Clamped)
    in_channels, in_samples = orig.shape
    out_channels, out_samples = prot_clamped.shape
    in_dur = in_samples / orig_sr
    out_dur = out_samples / sr

    print("\n--- 1. Audio Preservation ---")
    print(f"Sample Rate:   Input {orig_sr} Hz | Output {sr} Hz (Match: {orig_sr == sr})")
    print(f"Channels:      Input {in_channels} ch | Output {out_channels} ch (Match: {in_channels == out_channels})")
    print(f"Sample Count:  Input {in_samples} | Output {out_samples} (Match: {in_samples == out_samples})")
    print(f"Duration:      Input {in_dur:.4f}s | Output {out_dur:.4f}s (Match: {abs(in_dur - out_dur) < 1e-4})")

    # 2. Perturbation & Quality Metrics (Clamped vs Unclamped)
    def calc_metrics(orig_t, prot_t, sr_val):
        delta = prot_t - orig_t
        linf = delta.abs().max().item()
        rms_delta = delta.pow(2).mean().sqrt().item()
        rms_orig = orig_t.pow(2).mean().sqrt().item()
        snr = compute_snr(orig_t, prot_t)
        si_sdr = compute_si_sdr(orig_t, prot_t)
        peak = prot_t.abs().max().item()
        clips = (prot_t.abs() > 0.999).sum().item()
        nan_count = torch.isnan(prot_t).sum().item()
        inf_count = torch.isinf(prot_t).sum().item()

        # HuBERT Feature Distortion
        orig_feat = extract_hubert_features(orig_t, sr_val, hubert_model)
        prot_feat = extract_hubert_features(prot_t, sr_val, hubert_model)

        cos_sim = F.cosine_similarity(orig_feat.flatten(1), prot_feat.flatten(1), dim=-1).mean().item()
        cos_dist = 1.0 - cos_sim
        l2_dist = torch.norm(orig_feat - prot_feat, p=2).item()
        norm_l2 = l2_dist / torch.norm(orig_feat, p=2).item()

        return {
            "linf": linf, "rms_delta": rms_delta, "rms_orig": rms_orig,
            "snr": snr, "si_sdr": si_sdr, "peak": peak, "clips": clips,
            "nan_count": nan_count, "inf_count": inf_count,
            "cos_sim": cos_sim, "cos_dist": cos_dist, "l2_dist": l2_dist, "norm_l2": norm_l2
        }

    m_clamped = calc_metrics(orig, prot_clamped, sr)
    m_unclamped = calc_metrics(orig, prot_unclamped, sr)

    print("\n--- 2. Perturbation & Audio Quality Metrics ---")
    print(f"Metric                 | WITH Native Clamp (Fixed) | WITHOUT Native Clamp (Before)")
    print(f"-----------------------|---------------------------|-----------------------------")
    print(f"Max |delta| (L-inf)    | {m_clamped['linf']:.6f}                  | {m_unclamped['linf']:.6f}")
    print(f"RMS(delta)             | {m_clamped['rms_delta']:.6f}                  | {m_unclamped['rms_delta']:.6f}")
    print(f"RMS(original)          | {m_clamped['rms_orig']:.6f}                  | {m_unclamped['rms_orig']:.6f}")
    print(f"SNR (dB)               | {m_clamped['snr']:.2f} dB                   | {m_unclamped['snr']:.2f} dB")
    print(f"SI-SDR (dB)            | {m_clamped['si_sdr']:.2f} dB                  | {m_unclamped['si_sdr']:.2f} dB")
    print(f"Waveform Peak          | {m_clamped['peak']:.6f}                  | {m_unclamped['peak']:.6f}")
    print(f"Clip Count (|x|>0.999) | {m_clamped['clips']}                         | {m_unclamped['clips']}")
    print(f"NaN / Inf Count        | {m_clamped['nan_count']} / {m_clamped['inf_count']}                     | {m_unclamped['nan_count']} / {m_unclamped['inf_count']}")

    print("\n--- 3. HuBERT Representation Distortion (Layer 12 / last_hidden_state) ---")
    print(f"Metric                 | WITH Native Clamp (Fixed) | WITHOUT Native Clamp (Before)")
    print(f"-----------------------|---------------------------|-----------------------------")
    print(f"Cosine Similarity      | {m_clamped['cos_sim']:.6f}                  | {m_unclamped['cos_sim']:.6f}")
    print(f"Cosine Distance        | {m_clamped['cos_dist']:.6f}                  | {m_unclamped['cos_dist']:.6f}")
    print(f"L2 Distance            | {m_clamped['l2_dist']:.4f}                    | {m_unclamped['l2_dist']:.4f}")
    print(f"Normalized L2 Dist     | {m_clamped['norm_l2']:.6f}                  | {m_unclamped['norm_l2']:.6f}")

    return m_clamped, m_unclamped


def verify_pgd_differentiability(hubert_model):
    print("\n" + "=" * 75)
    print("=== PGD AUTOGRAD DIFFERENTIABILITY DIAGNOSTIC ===")
    print("=" * 75)

    # 1. Check HuBERT parameter freeze state
    frozen = all(not p.requires_grad for p in hubert_model.parameters())
    print(f"HuBERT Model Parameters Frozen (requires_grad=False): {frozen}")

    # 2. Setup input tensor and delta parameter
    x = torch.randn(1, 16000)
    with torch.no_grad():
        x_norm = (x - x.mean()) / (x.std() + 1e-7)
        orig_feat = hubert_model(x_norm).last_hidden_state.detach()

    delta = torch.empty_like(x).uniform_(-0.002, 0.002).requires_grad_(True)
    perturbed = x + delta
    p_norm = (perturbed - perturbed.mean()) / (perturbed.std() + 1e-7)
    adv_feat = hubert_model(p_norm).last_hidden_state

    loss = -F.mse_loss(adv_feat, orig_feat)
    loss.backward()

    grad_non_none = (delta.grad is not None)
    grad_max = delta.grad.abs().max().item() if grad_non_none else 0.0
    grad_non_zero = grad_max > 0.0

    print(f"Delta requires_grad:                          {delta.requires_grad}")
    print(f"Gradient is Non-None after backward():        {grad_non_none}")
    print(f"Max Absolute Gradient (delta.grad.abs().max()): {grad_max:.6f}")
    print(f"Gradient is Non-Zero:                         {grad_non_zero}")

    # 3. Waveform Loss Dependency Diagnostic
    with torch.no_grad():
        delta_step = delta - 0.002 * delta.grad.sign()
        p_step = x + delta_step
        p_step_norm = (p_step - p_step.mean()) / (p_step.std() + 1e-7)
        loss_after_step = -F.mse_loss(hubert_model(p_step_norm).last_hidden_state, orig_feat).item()

    loss_initial = loss.item()
    loss_changed = loss_after_step != loss_initial
    loss_decreased = loss_after_step < loss_initial  # Negative MSE decreases as distance grows

    print(f"Initial Attack Loss:                          {loss_initial:.6f}")
    print(f"Attack Loss After 1 Step:                     {loss_after_step:.6f}")
    print(f"Loss Changed as Waveform Changed:             {loss_changed}")
    print(f"Feature Distance Increased:                  {loss_decreased}")


def main():
    hubert = load_hubert("cpu")

    with tempfile.TemporaryDirectory() as tmpdir:
        fixtures = [
            (16000, 1, "16k_mono"),
            (44100, 1, "44k_mono"),
            (44100, 2, "44k_stereo"),
            (48000, 1, "48k_mono"),
            (48000, 2, "48k_stereo"),
        ]

        for sr, ch, name in fixtures:
            fix_path = os.path.join(tmpdir, f"{name}.wav")
            generate_fixture(fix_path, sr, ch, duration_s=3.0)
            audit_fixture(fix_path, tmpdir, name, hubert)

    verify_pgd_differentiability(hubert)


if __name__ == "__main__":
    main()
