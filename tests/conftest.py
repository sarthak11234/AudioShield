"""
Shared pytest fixtures for AudioShield test suite.
Uses pytest-asyncio for async FastAPI endpoint testing.
"""
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests that require HuBERT model download (~360 MB).",
    )

import os
import sys
import io
import struct
import wave
import pytest
import pytest_asyncio
import torch
import numpy as np
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

# ── Backend path setup ─────────────────────────────────────────────────────────
# Allow importing backend modules without installing as a package
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, BACKEND_DIR)

WORKER_DIR = os.path.join(os.path.dirname(__file__), "..", "worker")
sys.path.insert(0, WORKER_DIR)


# ── Audio generation helpers ───────────────────────────────────────────────────

def make_wav_bytes(duration_s: float = 1.0, sample_rate: int = 44100, channels: int = 1) -> bytes:
    """Return a minimal valid WAV file as bytes."""
    num_samples = int(duration_s * sample_rate)
    # 440 Hz tone
    t = np.linspace(0, duration_s, num_samples, dtype=np.float32)
    data = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
    if channels == 2:
        data = np.stack([data, data], axis=-1)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        pcm = (data * 32767).astype(np.int16)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def make_sine_tensor(
    duration_s: float = 3.0,
    sample_rate: int = 16000,
    channels: int = 1,
    freq: float = 440.0,
) -> torch.Tensor:
    """Return a (channels, samples) float32 tensor of a sine wave."""
    num_samples = int(duration_s * sample_rate)
    t = torch.linspace(0, duration_s, num_samples)
    wave_1ch = (torch.sin(2 * torch.pi * freq * t) * 0.5).unsqueeze(0)
    return wave_1ch.expand(channels, -1).clone()
