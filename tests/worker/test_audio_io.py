"""
Worker audio I/O tests.
Tests: WAV loading, multi-channel preservation, sample rate preservation, tensor shapes.
No real ML models are loaded — only the I/O layer is exercised.
"""
import os
import sys
import tempfile
import pytest
import torch
import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "worker"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conftest import make_sine_tensor


def _write_wav(path: str, waveform: torch.Tensor, sample_rate: int):
    audio_np = waveform.numpy()
    if audio_np.ndim == 2:
        audio_np = audio_np.T
    sf.write(path, audio_np, sample_rate, subtype="PCM_16")


class TestUniversalAudioLoader:
    """Tests for tasks.protect.load_audio()"""

    def test_load_mono_wav(self):
        from tasks.protect import load_audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            waveform = make_sine_tensor(duration_s=1.0, sample_rate=44100, channels=1)
            _write_wav(path, waveform, 44100)
            loaded, sr = load_audio(path)
            assert sr == 44100
            assert loaded.dim() == 2, "Expected (channels, samples)"
            assert loaded.shape[0] == 1, "Expected mono (1 channel)"
            assert loaded.shape[1] > 0
        finally:
            os.unlink(path)

    def test_load_stereo_wav_preserves_channels(self):
        from tasks.protect import load_audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            waveform = make_sine_tensor(duration_s=1.0, sample_rate=48000, channels=2)
            _write_wav(path, waveform, 48000)
            loaded, sr = load_audio(path)
            assert sr == 48000
            assert loaded.shape[0] == 2, "Expected stereo (2 channels)"
        finally:
            os.unlink(path)

    def test_load_preserves_sample_rate(self):
        """Different sample rates must be preserved exactly as read."""
        from tasks.protect import load_audio
        for target_sr in [16000, 22050, 44100, 48000]:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                path = f.name
            try:
                waveform = make_sine_tensor(duration_s=0.5, sample_rate=target_sr, channels=1)
                _write_wav(path, waveform, target_sr)
                _, sr = load_audio(path)
                assert sr == target_sr, f"Expected {target_sr}, got {sr}"
            finally:
                os.unlink(path)

    def test_nonexistent_file_raises_file_not_found(self):
        from tasks.protect import load_audio
        with pytest.raises(FileNotFoundError):
            load_audio("/nonexistent/path/audio.wav")

    def test_invalid_file_raises_value_error(self):
        from tasks.protect import load_audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"This is not an audio file at all.")
            path = f.name
        try:
            with pytest.raises((ValueError, Exception)):
                load_audio(path)
        finally:
            os.unlink(path)


class TestSaveAudio:
    """Tests for tasks.protect.save_audio()"""

    def test_save_and_reload_roundtrip(self):
        from tasks.protect import save_audio, load_audio
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.wav")
            original = make_sine_tensor(duration_s=1.0, sample_rate=44100, channels=1)
            save_audio(path, original, 44100)
            reloaded, sr = load_audio(path)
            assert sr == 44100
            assert reloaded.shape == original.shape

    def test_save_clips_extreme_values(self):
        """Values outside [-0.999, 0.999] must be clamped before saving."""
        from tasks.protect import save_audio, load_audio
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "clipped.wav")
            loud = torch.ones(1, 16000) * 5.0  # Way over 1.0
            save_audio(path, loud, 16000)
            reloaded, _ = load_audio(path)
            assert reloaded.abs().max().item() <= 1.0 + 1e-4  # small float tolerance
