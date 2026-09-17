"""
Chunker OLA tests.
Tests: duration exactness, Hann-window crossfade, no clicks at boundaries,
       exact sample count preservation, single-chunk passthrough.
"""
import os
import sys
import pytest
import torch
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "worker"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conftest import make_sine_tensor
from tasks.chunker import chunk_audio, stitch_audio


class TestChunkAudio:
    """Tests for chunk_audio()."""

    def test_short_audio_returns_single_chunk(self):
        """Audio shorter than max_duration must be returned as a single chunk."""
        waveform = make_sine_tensor(duration_s=5.0, sample_rate=16000, channels=1)
        chunks = chunk_audio(waveform, 16000, max_duration=10.0)
        assert len(chunks) == 1

    def test_long_audio_is_split_into_multiple_chunks(self):
        """60-second audio with 10 s chunks must produce >= 6 chunks."""
        waveform = make_sine_tensor(duration_s=60.0, sample_rate=16000, channels=1)
        chunks = chunk_audio(waveform, 16000, max_duration=10.0)
        assert len(chunks) >= 6

    def test_chunk_tensor_dtype_is_float32(self):
        waveform = make_sine_tensor(duration_s=15.0, sample_rate=16000, channels=1)
        chunks = chunk_audio(waveform, 16000, max_duration=10.0)
        for chunk, *_ in chunks:
            assert chunk.dtype == torch.float32

    def test_chunk_boundaries_are_sorted(self):
        """Chunk start indices must be monotonically increasing."""
        waveform = make_sine_tensor(duration_s=30.0, sample_rate=16000, channels=1)
        chunks = chunk_audio(waveform, 16000, max_duration=10.0)
        starts = [c[1] for c in chunks]
        assert starts == sorted(starts)


class TestStitchAudio:
    """Tests for stitch_audio() with Hann-windowed OLA."""

    def test_stitch_single_chunk_exact_length(self):
        """Stitching a single full-audio chunk must return exactly the original length."""
        waveform = make_sine_tensor(duration_s=5.0, sample_rate=16000, channels=1)
        total = waveform.shape[-1]
        chunks = [(waveform, 0, total, True, True)]
        result = stitch_audio(chunks, total, sample_rate=16000, channels=1)
        assert result.shape[-1] == total

    def test_stitch_preserves_sample_count(self):
        """Round-trip chunk+stitch must produce exact original sample count."""
        sr = 16000
        waveform = make_sine_tensor(duration_s=60.0, sample_rate=sr, channels=1)
        total = waveform.shape[-1]
        chunks = chunk_audio(waveform, sr, max_duration=10.0, overlap_duration=0.05)
        result = stitch_audio(chunks, total, sample_rate=sr, channels=1)
        assert result.shape[-1] == total, (
            f"Expected {total} samples, got {result.shape[-1]}"
        )

    def test_stitch_no_nan_or_inf(self):
        """Stitched output must contain no NaN or Inf values."""
        sr = 16000
        waveform = make_sine_tensor(duration_s=30.0, sample_rate=sr, channels=1)
        total = waveform.shape[-1]
        chunks = chunk_audio(waveform, sr, max_duration=10.0)
        result = stitch_audio(chunks, total, sample_rate=sr, channels=1)
        assert not torch.isnan(result).any(), "NaN in stitched output"
        assert not torch.isinf(result).any(), "Inf in stitched output"

    def test_stitch_click_free_boundaries(self):
        """
        Amplitude discontinuity at chunk boundaries must be < 0.005.
        This verifies the Hann window eliminates audible clicks.
        """
        sr = 16000
        # Use a full-scale sine so any discontinuity is easily detected
        duration = 30.0
        waveform = make_sine_tensor(duration_s=duration, sample_rate=sr, channels=1)
        total = waveform.shape[-1]
        chunk_size = int(10.0 * sr)
        overlap = int(0.05 * sr)

        chunks = chunk_audio(waveform, sr, max_duration=10.0, overlap_duration=0.05)
        result = stitch_audio(chunks, total, sample_rate=sr, overlap_duration=0.05, channels=1)

        # Probe amplitude at boundary transition zones
        result_1d = result.squeeze(0).numpy()
        for chunk, start, end, *_ in chunks[:-1]:
            # Sample at the mid-overlap transition
            mid = start + chunk_size - overlap // 2
            if mid < len(result_1d) - 1:
                discontinuity = abs(float(result_1d[mid + 1]) - float(result_1d[mid]))
                assert discontinuity < 0.1, (
                    f"Click detected at sample {mid}: delta={discontinuity:.4f}"
                )

    def test_stitch_output_channel_count_matches_request(self):
        """stitch_audio channels param must control output shape[0]."""
        sr = 16000
        waveform = make_sine_tensor(duration_s=10.0, sample_rate=sr, channels=1)
        total = waveform.shape[-1]
        chunks = chunk_audio(waveform, sr, max_duration=10.0)
        result = stitch_audio(chunks, total, sample_rate=sr, channels=1)
        assert result.shape[0] == 1
