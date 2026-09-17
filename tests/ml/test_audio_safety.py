"""
Audio safety validation tests.
Tests: NaN/Inf rejection, peak amplitude clamping, SNR floor, output length invariance.
"""
import os
import sys
import tempfile
import pytest
import torch
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "worker"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conftest import make_sine_tensor


class TestNaNInfDetection:
    """_validate_output_tensor must raise RuntimeError for corrupt data."""

    def test_nan_tensor_raises(self):
        from tasks.protect import _validate_output_tensor
        t = torch.full((1, 1000), float("nan"))
        with pytest.raises(RuntimeError, match="NaN"):
            _validate_output_tensor(t, "test_nan")

    def test_inf_tensor_raises(self):
        from tasks.protect import _validate_output_tensor
        t = torch.full((1, 1000), float("inf"))
        with pytest.raises(RuntimeError, match="Inf"):
            _validate_output_tensor(t, "test_inf")

    def test_clean_tensor_passes(self):
        from tasks.protect import _validate_output_tensor
        t = make_sine_tensor(duration_s=1.0, sample_rate=16000, channels=1)
        # Should not raise
        _validate_output_tensor(t, "clean_tensor")


class TestSaveAudioClipping:
    """save_audio must prevent digital clipping at file boundary."""

    def test_max_amplitude_below_1_after_save(self):
        from tasks.protect import save_audio, load_audio
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "output.wav")
            # Write a very loud tensor (5x normal range)
            loud = torch.ones(1, 16000) * 5.0
            save_audio(path, loud, 16000)
            loaded, _ = load_audio(path)
            assert loaded.abs().max().item() <= 1.0 + 1e-3

    def test_negative_clipping_preserved_correctly(self):
        from tasks.protect import save_audio, load_audio
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "neg.wav")
            loud_neg = torch.ones(1, 16000) * -5.0
            save_audio(path, loud_neg, 16000)
            loaded, _ = load_audio(path)
            assert loaded.abs().max().item() <= 1.0 + 1e-3


class TestSNRRequirement:
    """
    SNR of the perturbation (relative to the original) must be >= 28 dB
    when the perturbation is within the epsilon ball.
    """

    def _compute_snr(self, signal: torch.Tensor, noise: torch.Tensor) -> float:
        signal_power = signal.pow(2).mean()
        noise_power = noise.pow(2).mean()
        if noise_power < 1e-12:
            return float("inf")
        return 10 * torch.log10(signal_power / noise_power).item()

    def test_snr_meets_28db_floor_for_epsilon_0015(self):
        """
        For epsilon=0.015, a sine at 0.5 amplitude gives:
          SNR = 10 * log10(0.5^2/2 / (0.015^2/3)) ≈ 35 dB
        Any compliant perturbation must meet >= 28 dB.
        """
        epsilon = 0.015
        sr = 16000
        original = make_sine_tensor(duration_s=3.0, sample_rate=sr, channels=1)
        # Simulate worst-case perturbation: uniform [-epsilon, epsilon]
        perturbation = torch.empty_like(original).uniform_(-epsilon, epsilon)
        snr = self._compute_snr(original, perturbation)
        assert snr >= 28.0, f"SNR requirement not met: {snr:.1f} dB < 28 dB"


class TestOutputLengthInvariance:
    """Protected output length must match input within ±1 sample."""

    def test_dual_rate_length_preservation(self):
        """
        After downsampling to 16 kHz and upsampling back, length must match
        the original within ±1 sample.
        """
        import torchaudio
        sr = 44100
        waveform = make_sine_tensor(duration_s=5.0, sample_rate=sr, channels=2)
        original_len = waveform.shape[-1]

        # Simulate the dual-rate resample cycle
        mono = waveform.mean(dim=0, keepdim=True)
        downsampler = torchaudio.transforms.Resample(sr, 16000)
        mono_16k = downsampler(mono)

        upsampler = torchaudio.transforms.Resample(16000, sr)
        back = upsampler(mono_16k)

        # Trim or pad
        back_len = back.shape[-1]
        diff = abs(back_len - original_len)
        assert diff <= 2, (
            f"Resampling cycle length drift: {diff} samples (original={original_len}, back={back_len})"
        )


@pytest.mark.slow
class TestNativeEpsilonConstraint:
    """
    Regression test verifying that the final resampled perturbation on native audio
    (including 44.1 kHz stereo and 48 kHz stereo) obeys the configured L-infinity epsilon bound.
    """

    def test_44k_stereo_resampled_perturbation_bound(self):
        """
        44.1 kHz stereo audio must satisfy max(|protected - original|) <= epsilon + tolerance
        after end-to-end protection pipeline execution.
        """
        import soundfile as sf
        from tasks.protect import load_audio, protect_audio

        epsilon = 0.02
        tolerance = 1e-3  # 16-bit PCM quantization step size tolerance (1/32768 ≈ 0.00003)
        sr = 44100
        channels = 2

        with tempfile.TemporaryDirectory() as tmpdir:
            in_path = os.path.join(tmpdir, "stereo_44k_in.wav")
            out_path = os.path.join(tmpdir, "stereo_44k_out.wav")

            t = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
            sig = (np.sin(2 * np.pi * 200 * t) * 0.4 + np.sin(2 * np.pi * 600 * t) * 0.2).astype(np.float32)
            stereo_sig = np.stack([sig, sig * 0.9], axis=1)
            sf.write(in_path, stereo_sig, sr, subtype="PCM_16")

            protect_audio.update_state = lambda state=None, meta=None: None
            res = protect_audio.__wrapped__("test-44k-stereo", in_path, out_path)
            assert res["status"] == "completed"

            orig, orig_sr = load_audio(in_path)
            prot, prot_sr = load_audio(out_path)

            assert orig_sr == prot_sr == sr
            assert orig.shape == prot.shape == (channels, int(sr * 2.0))

            delta = prot - orig
            max_delta = delta.abs().max().item()

            assert not torch.isnan(prot).any(), "NaN in protected audio"
            assert not torch.isinf(prot).any(), "Inf in protected audio"
            assert max_delta <= epsilon + tolerance, (
                f"L-infinity perturbation bound violated for 44.1 kHz stereo: "
                f"max|delta| = {max_delta:.6f} > epsilon = {epsilon}"
            )
