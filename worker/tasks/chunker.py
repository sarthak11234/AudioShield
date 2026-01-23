import torch
import torchaudio

def chunk_audio(waveform: torch.Tensor, sample_rate: int, max_duration: float = 10.0):
    """
    Split audio into chunks of max_duration seconds.
    Uses zero-crossing detection to avoid clicks.
    
    Args:
        waveform: Audio tensor of shape (channels, samples)
        sample_rate: Sample rate in Hz
        max_duration: Maximum chunk duration in seconds
    
    Returns:
        List of (chunk_tensor, start_sample, end_sample) tuples
    """
    max_samples = int(max_duration * sample_rate)
    total_samples = waveform.shape[-1]
    
    if total_samples <= max_samples:
        return [(waveform, 0, total_samples)]
    
    chunks = []
    start = 0
    
    while start < total_samples:
        end = min(start + max_samples, total_samples)
        
        # Find zero-crossing near the end for smooth cut
        if end < total_samples:
            search_start = max(end - int(0.01 * sample_rate), start)  # Search last 10ms
            segment = waveform[0, search_start:end] if waveform.dim() > 1 else waveform[search_start:end]
            
            # Find zero crossings
            zero_crossings = torch.where(torch.diff(torch.sign(segment)) != 0)[0]
            if len(zero_crossings) > 0:
                end = search_start + zero_crossings[-1].item() + 1
        
        chunk = waveform[..., start:end]
        chunks.append((chunk, start, end))
        start = end
    
    return chunks


def stitch_audio(chunks: list, total_samples: int, channels: int = 1) -> torch.Tensor:
    """
    Stitch audio chunks back together with crossfade.
    
    Args:
        chunks: List of (chunk_tensor, start_sample, end_sample) tuples
        total_samples: Total expected samples in output
        channels: Number of audio channels
    
    Returns:
        Stitched audio tensor
    """
    output = torch.zeros(channels, total_samples)
    
    for chunk, start, end in chunks:
        if chunk.dim() == 1:
            chunk = chunk.unsqueeze(0)
        output[..., start:end] = chunk
    
    return output
