import os
import torch
import torchaudio
import numpy as np
from scipy.io import wavfile
from celery_app import app
from tasks.chunker import chunk_audio, stitch_audio
from tasks.pgd_attack import pgd_attack

def load_audio(path):
    """Load audio using scipy for WAV files (most reliable)."""
    sample_rate, data = wavfile.read(path)
    # Convert to float32 and normalize
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.uint8:
        data = (data.astype(np.float32) - 128) / 128.0
    # Convert to tensor (channels, samples)
    waveform = torch.from_numpy(data)
    if waveform.dim() == 1:
        waveform = waveform.unsqueeze(0)
    else:
        waveform = waveform.T  # scipy returns (samples, channels)
    return waveform, sample_rate

@app.task(bind=True, name="protect_audio")
def protect_audio(self, task_id: str, input_path: str, output_path: str):
    """
    Main protection task - applies PGD adversarial attack to audio.
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[AudioShield] Starting protection on {device}")
    
    try:
        # Step 1: Load audio using soundfile backend
        self.update_state(state="PROCESSING", meta={"step": "loading"})
        print(f"[AudioShield] Loading audio: {input_path}")
        waveform, sample_rate = load_audio(input_path)
        
        # Resample to 16kHz for HuBERT
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)
            sample_rate = 16000
        
        # Step 2: Chunk audio (<10s for VRAM)
        self.update_state(state="PROCESSING", meta={"step": "chunking"})
        chunks = chunk_audio(waveform, sample_rate, max_duration=10.0)
        
        # Step 3: Apply PGD attack to each chunk
        protected_chunks = []
        for i, (chunk, start, end) in enumerate(chunks):
            self.update_state(
                state="PROCESSING",
                meta={"step": f"protecting chunk {i+1}/{len(chunks)}"}
            )
            
            protected = pgd_attack(
                chunk.squeeze(0) if chunk.dim() > 1 else chunk,
                sample_rate=sample_rate,
                epsilon=0.02,
                alpha=0.002,  # Slightly larger step size for fewer steps
                num_steps=15,  # Reduced from 50 for faster processing
                device=device
            )
            protected_chunks.append((protected.unsqueeze(0), start, end))
            
            # Clear GPU memory
            torch.cuda.empty_cache()
        
        # Step 4: Stitch chunks
        self.update_state(state="PROCESSING", meta={"step": "stitching"})
        total_samples = waveform.shape[-1]
        protected_audio = stitch_audio(protected_chunks, total_samples, channels=1)
        
        # Step 5: Save output using scipy (more reliable)
        self.update_state(state="PROCESSING", meta={"step": "saving"})
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Convert to int16 for WAV file
        audio_np = protected_audio.squeeze(0).numpy()
        audio_int16 = (audio_np * 32767).astype(np.int16)
        wavfile.write(output_path, sample_rate, audio_int16)
        
        print(f"[AudioShield] Protection complete! Saved to {output_path}")
        return {"status": "completed", "output_path": output_path}
        
    except Exception as e:
        print(f"[AudioShield] Error: {str(e)}")
        return {"status": "failed", "error": str(e)}
