import os
import torch
import torchaudio
from celery_app import app
from tasks.chunker import chunk_audio, stitch_audio
from tasks.pgd_attack import pgd_attack

@app.task(bind=True, name="protect_audio")
def protect_audio(self, task_id: str, input_path: str, output_path: str):
    """
    Main protection task - applies PGD adversarial attack to audio.
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    try:
        # Step 1: Load audio
        self.update_state(state="PROCESSING", meta={"step": "loading"})
        waveform, sample_rate = torchaudio.load(input_path)
        
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
                alpha=0.001,
                num_steps=50,
                device=device
            )
            protected_chunks.append((protected.unsqueeze(0), start, end))
            
            # Clear GPU memory
            torch.cuda.empty_cache()
        
        # Step 4: Stitch chunks
        self.update_state(state="PROCESSING", meta={"step": "stitching"})
        total_samples = waveform.shape[-1]
        protected_audio = stitch_audio(protected_chunks, total_samples, channels=1)
        
        # Step 5: Save output
        self.update_state(state="PROCESSING", meta={"step": "saving"})
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        torchaudio.save(output_path, protected_audio, sample_rate)
        
        return {"status": "completed", "output_path": output_path}
        
    except Exception as e:
        return {"status": "failed", "error": str(e)}
