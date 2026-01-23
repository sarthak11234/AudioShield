import torch
import torch.nn.functional as F
from transformers import HubertModel, Wav2Vec2FeatureExtractor

# Global model cache
_hubert_model = None
_feature_extractor = None

def load_hubert(device: str = "cuda"):
    """Load HuBERT model for adversarial attack."""
    global _hubert_model, _feature_extractor
    
    if _hubert_model is None:
        _feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained("facebook/hubert-base-ls960")
        _hubert_model = HubertModel.from_pretrained("facebook/hubert-base-ls960")
        _hubert_model = _hubert_model.to(device)
        _hubert_model.eval()
        
        # Freeze model parameters
        for param in _hubert_model.parameters():
            param.requires_grad = False
    
    return _hubert_model, _feature_extractor


def pgd_attack(
    waveform: torch.Tensor,
    sample_rate: int = 16000,
    epsilon: float = 0.02,
    alpha: float = 0.001,
    num_steps: int = 50,
    device: str = "cuda"
) -> torch.Tensor:
    """
    Projected Gradient Descent attack against HuBERT.
    
    Args:
        waveform: Audio tensor of shape (samples,) or (1, samples)
        sample_rate: Audio sample rate (HuBERT expects 16kHz)
        epsilon: Maximum perturbation magnitude
        alpha: Step size per iteration
        num_steps: Number of PGD iterations
        device: cuda or cpu
    
    Returns:
        Adversarially perturbed audio tensor
    """
    model, extractor = load_hubert(device)
    
    # Prepare input
    if waveform.dim() == 2:
        waveform = waveform.squeeze(0)
    
    waveform = waveform.to(device)
    original_waveform = waveform.clone()
    
    # Initialize perturbation
    delta = torch.zeros_like(waveform, requires_grad=True)
    
    # Get original features
    with torch.no_grad():
        inputs = extractor(
            original_waveform.cpu().numpy(),
            sampling_rate=sample_rate,
            return_tensors="pt"
        )
        original_features = model(inputs.input_values.to(device)).last_hidden_state
    
    # PGD loop
    for step in range(num_steps):
        delta.requires_grad_(True)
        
        perturbed = original_waveform + delta
        
        # Get perturbed features
        inputs = extractor(
            perturbed.detach().cpu().numpy(),
            sampling_rate=sample_rate,
            return_tensors="pt"
        )
        perturbed_features = model(inputs.input_values.to(device)).last_hidden_state
        
        # Loss: maximize feature distance (untargeted attack)
        loss = -F.mse_loss(perturbed_features, original_features)
        loss.backward()
        
        # Update perturbation
        with torch.no_grad():
            delta = delta + alpha * delta.grad.sign()
            delta = torch.clamp(delta, -epsilon, epsilon)
            delta = delta.detach()
        
        # Clear GPU memory periodically
        if step % 10 == 0:
            torch.cuda.empty_cache()
    
    # Apply final perturbation
    protected_audio = original_waveform + delta
    protected_audio = torch.clamp(protected_audio, -1.0, 1.0)
    
    return protected_audio.cpu()
