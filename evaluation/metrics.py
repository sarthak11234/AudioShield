"""
AudioShield Evaluation Metrics Module
======================================
Provides quantitative functions and data classes for evaluating:
1. Audio Preservation & Quality (SR, channels, sample count, duration, L-inf, RMS, SNR, SI-SDR, peak, clipping, NaN/Inf)
2. HuBERT Feature Distortion (Layer 12 / last_hidden_state: Cosine similarity, Cosine distance, L2 distance, Normalized L2)
3. Objective Perceptual Quality (STOI, with documented PESQ environment limitation)
4. Speaker Identity Embeddings (ECAPA-TDNN speaker encoder cosine similarity distributions)
"""

import math
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
import torch
import torch.nn.functional as F
import numpy as np

logger = logging.getLogger("audioshield.eval.metrics")


@dataclass
class AudioPreservationMetrics:
    """Audio preservation and numerical fidelity metrics."""
    sr_preserved: bool
    ch_preserved: bool
    samples_preserved: bool
    duration_preserved: bool
    linf_norm: float
    rms_perturbation: float
    rms_original: float
    snr_db: float
    si_sdr_db: float
    peak_amplitude: float
    clipping_count: int
    nan_inf_count: int


@dataclass
class HubertDistortionMetrics:
    """HuBERT representation distortion metrics (Layer 12 / last_hidden_state)."""
    cosine_similarity: float
    cosine_distance: float
    l2_distance: float
    normalized_l2_distance: float


@dataclass
class PerceptualQualityMetrics:
    """Objective perceptual quality metrics."""
    stoi_score: Optional[float]
    pesq_score: Optional[float]  # None if pesq library is not installed
    snr_db: float
    si_sdr_db: float
    pesq_limitation_note: str = "PESQ metric unavailable: 'pesq' package not installed in environment."


@dataclass
class SpeakerEmbeddingMetrics:
    """Speaker embedding similarity metrics (ECAPA-TDNN)."""
    orig_vs_protected_cosine_sim: float


@dataclass
class SpeakerDistributionStats:
    """Statistical summary of a similarity distribution."""
    mean: float
    std: float
    min: float
    p25: float
    median: float
    p75: float
    max: float

    @classmethod
    def from_values(cls, values: List[float]) -> "SpeakerDistributionStats":
        if not values:
            return cls(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        arr = np.array(values, dtype=np.float64)
        return cls(
            mean=round(float(np.mean(arr)), 6),
            std=round(float(np.std(arr)), 6),
            min=round(float(np.min(arr)), 6),
            p25=round(float(np.percentile(arr, 25)), 6),
            median=round(float(np.median(arr)), 6),
            p75=round(float(np.percentile(arr, 75)), 6),
            max=round(float(np.max(arr)), 6),
        )


@dataclass
class SpeakerEvaluationReport:
    """Aggregate report of speaker embedding distributions."""
    orig_orig_stats: SpeakerDistributionStats
    orig_protected_stats: SpeakerDistributionStats
    orig_other_stats: SpeakerDistributionStats
    systematic_speaker_shift_observed: bool
    notes: str


@dataclass
class UtteranceEvaluationReport:
    """Combined report for a single audio utterance."""
    utterance_id: str
    speaker_id: str
    sample_rate: int
    num_channels: int
    sample_count: int
    duration_s: float
    audio_preservation: AudioPreservationMetrics
    hubert_distortion: Optional[HubertDistortionMetrics]
    perceptual_quality: PerceptualQualityMetrics
    speaker_embedding: Optional[SpeakerEmbeddingMetrics]


def compute_snr(original: torch.Tensor, protected: torch.Tensor) -> float:
    """
    Signal-to-Noise Ratio in dB.
    SNR = 10 * log10(E[signal^2] / E[noise^2])
    """
    if original.shape != protected.shape:
        raise ValueError(f"Shape mismatch: original={original.shape}, protected={protected.shape}")
    noise = protected - original
    signal_power = original.pow(2).mean().item()
    noise_power = noise.pow(2).mean().item()
    if noise_power < 1e-12:
        return float("inf")
    return 10.0 * math.log10(signal_power / noise_power)


def compute_si_sdr(original: torch.Tensor, protected: torch.Tensor) -> float:
    """
    Scale-Invariant Signal-to-Distortion Ratio (SI-SDR) in dB.
    Le Roux et al., 2019.
    """
    s = original.flatten().float()
    s_hat = protected.flatten().float()

    s = s - s.mean()
    s_hat = s_hat - s_hat.mean()

    dot = torch.dot(s_hat, s)
    s_sq = torch.dot(s, s) + 1e-8
    target = (dot / s_sq) * s
    noise = s_hat - target

    target_pow = target.pow(2).sum()
    noise_pow = noise.pow(2).sum() + 1e-8
    si_sdr = 10.0 * torch.log10(target_pow / noise_pow).item()
    return si_sdr


def compute_stoi(original: torch.Tensor, protected: torch.Tensor, sample_rate: int) -> Optional[float]:
    """
    Short-Time Objective Intelligibility (STOI) via pystoi.
    """
    try:
        import pystoi
        import torchaudio

        orig_mono = original.mean(dim=0, keepdim=True) if original.dim() == 2 else original.unsqueeze(0)
        prot_mono = protected.mean(dim=0, keepdim=True) if protected.dim() == 2 else protected.unsqueeze(0)

        if sample_rate != 16000:
            orig_mono = torchaudio.transforms.Resample(sample_rate, 16000)(orig_mono)
            prot_mono = torchaudio.transforms.Resample(sample_rate, 16000)(prot_mono)
            eval_sr = 16000
        else:
            eval_sr = sample_rate

        o_np = orig_mono.squeeze().cpu().numpy()
        p_np = prot_mono.squeeze().cpu().numpy()

        score = pystoi.stoi(o_np, p_np, eval_sr, extended=False)
        return round(float(score), 4)
    except Exception as e:
        logger.warning(f"Failed to compute STOI: {e}")
        return None


def compute_audio_preservation(
    original: torch.Tensor,
    protected: torch.Tensor,
    orig_sr: int,
    prot_sr: int,
) -> AudioPreservationMetrics:
    """Compute complete set of Phase 1 audio preservation metrics."""
    orig_channels, orig_samples = (original.shape[0], original.shape[-1]) if original.dim() == 2 else (1, original.shape[0])
    prot_channels, prot_samples = (protected.shape[0], protected.shape[-1]) if protected.dim() == 2 else (1, protected.shape[0])

    orig_dur = orig_samples / orig_sr
    prot_dur = prot_samples / prot_sr

    sr_preserved = (orig_sr == prot_sr)
    ch_preserved = (orig_channels == prot_channels)
    samples_preserved = (orig_samples == prot_samples)
    duration_preserved = abs(orig_dur - prot_dur) < 1e-4

    delta = protected - original
    linf_norm = delta.abs().max().item()
    rms_perturbation = delta.pow(2).mean().sqrt().item()
    rms_original = original.pow(2).mean().sqrt().item()

    snr_db = compute_snr(original, protected)
    si_sdr_db = compute_si_sdr(original, protected)
    peak_amplitude = protected.abs().max().item()

    # Clipping count: samples with |x| > 0.999
    clipping_count = int((protected.abs() > 0.999).sum().item())

    # NaN / Inf count
    nan_count = int(torch.isnan(protected).sum().item())
    inf_count = int(torch.isinf(protected).sum().item())
    nan_inf_count = nan_count + inf_count

    return AudioPreservationMetrics(
        sr_preserved=sr_preserved,
        ch_preserved=ch_preserved,
        samples_preserved=samples_preserved,
        duration_preserved=duration_preserved,
        linf_norm=round(linf_norm, 8),
        rms_perturbation=round(rms_perturbation, 8),
        rms_original=round(rms_original, 8),
        snr_db=round(snr_db, 4),
        si_sdr_db=round(si_sdr_db, 4),
        peak_amplitude=round(peak_amplitude, 6),
        clipping_count=clipping_count,
        nan_inf_count=nan_inf_count,
    )


def compute_hubert_distortion(
    original: torch.Tensor,
    protected: torch.Tensor,
    sample_rate: int,
    hubert_model,
) -> Optional[HubertDistortionMetrics]:
    """
    Compute HuBERT representation distortion metrics (Layer 12 / last_hidden_state).
    Uses corrected 16 kHz resampled path.
    """
    if hubert_model is None:
        return None

    import torchaudio

    HUBERT_SR = 16000
    hubert_model.eval()

    with torch.no_grad():
        def _extract(x: torch.Tensor):
            mono = x.mean(dim=0, keepdim=True) if x.dim() == 2 else x.unsqueeze(0)
            if sample_rate != HUBERT_SR:
                mono = torchaudio.transforms.Resample(sample_rate, HUBERT_SR)(mono)
            mono_norm = (mono - mono.mean()) / (mono.std() + 1e-7)
            out = hubert_model(mono_norm.to(next(hubert_model.parameters()).device))
            return out.last_hidden_state.flatten(1)

        orig_feat = _extract(original)
        prot_feat = _extract(protected)

        cos_sim = F.cosine_similarity(orig_feat, prot_feat, dim=-1).mean().item()
        cos_dist = 1.0 - cos_sim
        l2_dist = torch.norm(orig_feat - prot_feat, p=2).item()
        orig_norm = torch.norm(orig_feat, p=2).item()
        norm_l2 = l2_dist / (orig_norm + 1e-7)

    return HubertDistortionMetrics(
        cosine_similarity=round(cos_sim, 6),
        cosine_distance=round(cos_dist, 6),
        l2_distance=round(l2_dist, 6),
        normalized_l2_distance=round(norm_l2, 6),
    )


def extract_speaker_embedding(waveform: torch.Tensor, sample_rate: int, speaker_encoder) -> torch.Tensor:
    """
    Extract 192-dimensional ECAPA-TDNN speaker embedding using SpeechBrain.
    Waveform is resampled to 16 kHz if necessary.
    Returns 1D Tensor of shape (192,).
    """
    import torchaudio

    mono = waveform.mean(dim=0, keepdim=True) if waveform.dim() == 2 else waveform.unsqueeze(0)
    if sample_rate != 16000:
        mono = torchaudio.transforms.Resample(sample_rate, 16000)(mono)

    with torch.no_grad():
        # speechbrain encoder expects (batch, samples)
        emb = speaker_encoder.encode_batch(mono)  # shape (1, 1, 192)
        emb = emb.squeeze().cpu()
        emb = F.normalize(emb, p=2, dim=-1)
    return emb
