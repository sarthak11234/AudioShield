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
        print("[AudioShield] Loading HuBERT model...")
        _feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained("facebook/hubert-base-ls960")
        _hubert_model = HubertModel.from_pretrained("facebook/hubert-base-ls960")
        _hubert_model = _hubert_model.to(device)
        _hubert_model.eval()
        print("[AudioShield] HuBERT model loaded!")
    
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
    """
    model, extractor = load_hubert(device)
    
    # Prepare input
    if waveform.dim() == 2:
        waveform = waveform.squeeze(0)
    
    waveform = waveform.to(device).float()
    original_waveform = waveform.clone()
    
    # Get normalization params from extractor
    mean = extractor.mean if hasattr(extractor, 'mean') else 0.0
    std = extractor.std if hasattr(extractor, 'std') else 1.0
    
    # Initialize perturbation
    delta = torch.zeros_like(waveform, device=device)
    
    # Get original features (no grad needed)
    with torch.no_grad():
        inputs = extractor(
            original_waveform.cpu().numpy(),
            sampling_rate=sample_rate,
            return_tensors="pt",
            padding=True
        )
        original_features = model(inputs.input_values.to(device)).last_hidden_state
    
    print(f"[AudioShield] Running PGD attack ({num_steps} steps)...")
    
    # PGD loop - use finite differences for gradient estimation
    for step in range(num_steps):
        perturbed = original_waveform + delta
        
        # Get perturbed features
        with torch.no_grad():
            inputs = extractor(
                perturbed.cpu().numpy(),
                sampling_rate=sample_rate,
                return_tensors="pt",
                padding=True
            )
            perturbed_features = model(inputs.input_values.to(device)).last_hidden_state
        
        # Compute loss (maximize distance = minimize negative distance)
        loss = F.mse_loss(perturbed_features, original_features)
        
        # Estimate gradient using finite differences (SPSA-style)
        grad = torch.zeros_like(delta)
        h = 0.001  # Small step for gradient estimation
        
        for _ in range(2):  # Average over a few random directions
            direction = torch.sign(torch.randn_like(delta))
            
            # Forward difference
            delta_plus = delta + h * direction
            perturbed_plus = original_waveform + delta_plus
            with torch.no_grad():
                inputs_plus = extractor(
                    perturbed_plus.cpu().numpy(),
                    sampling_rate=sample_rate,
                    return_tensors="pt",
                    padding=True
                )
                features_plus = model(inputs_plus.input_values.to(device)).last_hidden_state
                loss_plus = F.mse_loss(features_plus, original_features)
            
            grad += (loss_plus - loss) / h * direction
        
        grad = grad / 2  # Average
        
        # Update perturbation (maximize loss = add positive gradient)
        delta = delta + alpha * torch.sign(grad)
        delta = torch.clamp(delta, -epsilon, epsilon)
        
        if step % 10 == 0:
            print(f"[AudioShield] Step {step + 1}/{num_steps}, loss: {loss.item():.6f}")
            torch.cuda.empty_cache()
    
    # Apply final perturbation
    protected_audio = original_waveform + delta
    protected_audio = torch.clamp(protected_audio, -1.0, 1.0)
    
    print("[AudioShield] PGD attack complete!")
    return protected_audio.cpu()

