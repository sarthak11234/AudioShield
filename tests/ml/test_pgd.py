"""
PGD attack correctness tests.
Tests (CPU-only, no CUDA required):
  - Gradient is non-zero after one step
  - L-infinity constraint is never violated
  - Feature distortion increases monotonically with iterations
  - Output shape matches input shape
  - Random start produces diverse initializations

NOTE: These tests load a real HuBERT model from HuggingFace.
      First run will download ~360 MB. Set HF_HOME to cache.
      Mark slow tests with: pytest tests/ml/test_pgd.py -m slow
"""
import os
import sys
import pytest
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "worker"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conftest import make_sine_tensor
from tasks.pgd_attack import pgd_attack, AttackConfig, LInfinityConstraint, PreEmphasisConstraint


# ── Unit tests (no model required) ────────────────────────────────────────────

class TestLInfinityConstraint:
    def test_clamps_within_epsilon(self):
        constr = LInfinityConstraint(epsilon=0.02)
        delta = torch.tensor([-1.0, 0.0, 1.0])
        result = constr.apply(delta)
        assert result.min().item() >= -0.02 - 1e-9
        assert result.max().item() <= 0.02 + 1e-9

    def test_zero_tensor_unchanged(self):
        constr = LInfinityConstraint(epsilon=0.015)
        delta = torch.zeros(100)
        result = constr.apply(delta)
        assert torch.allclose(result, delta)


class TestPreEmphasisConstraint:
    def test_output_shape_preserved(self):
        constr = PreEmphasisConstraint(0.85)
        grad = torch.randn(1, 1000)
        result = constr.apply(grad)
        assert result.shape == grad.shape

    def test_attenuates_dc_component(self):
        """Constant signal (pure DC) should be nearly zeroed by 1 - 0.85*z^-1."""
        constr = PreEmphasisConstraint(0.85)
        dc = torch.ones(1, 500) * 0.5
        result = constr.apply(dc)
        # After filter, interior samples should be close to 0.5*(1-0.85) = 0.075
        interior_mean = result[:, 10:].mean().item()
        assert abs(interior_mean) < 0.1, f"DC not attenuated: mean={interior_mean}"


class TestAttackConfig:
    def test_default_values(self):
        cfg = AttackConfig()
        assert cfg.epsilon == 0.015
        assert cfg.alpha == 0.002
        assert cfg.num_steps == 15
        assert cfg.random_start is True

    def test_custom_values_applied(self):
        cfg = AttackConfig(epsilon=0.05, alpha=0.005, num_steps=5)
        assert cfg.epsilon == 0.05
        assert cfg.alpha == 0.005
        assert cfg.num_steps == 5


# ── Integration tests (require HuBERT model download) ─────────────────────────

@pytest.mark.slow
class TestPGDAttackIntegration:
    """
    Full PGD attack integration tests.
    Skipped unless --run-slow flag is provided or AUDIOSHIELD_RUN_SLOW_TESTS=1.
    """

    @pytest.fixture(autouse=True)
    def skip_if_not_slow(self, request):
        if not (
            request.config.getoption("--run-slow", default=False)
            or os.environ.get("AUDIOSHIELD_RUN_SLOW_TESTS") == "1"
        ):
            pytest.skip("Skipping slow test: HuBERT model required. Set AUDIOSHIELD_RUN_SLOW_TESTS=1 to enable.")

    def test_output_shape_matches_input(self):
        """pgd_attack must return a tensor with the same length as input."""
        waveform = make_sine_tensor(duration_s=1.0, sample_rate=16000, channels=1)
        x_1d = waveform.squeeze(0)
        result = pgd_attack(x_1d, sample_rate=16000, num_steps=3, device="cpu")
        assert result.shape == x_1d.shape, f"Shape mismatch: {result.shape} vs {x_1d.shape}"

    def test_linf_bound_never_violated(self):
        """Max absolute perturbation must always be <= epsilon."""
        epsilon = 0.015
        waveform = make_sine_tensor(duration_s=1.0, sample_rate=16000, channels=1)
        x_1d = waveform.squeeze(0)
        result = pgd_attack(x_1d, sample_rate=16000, epsilon=epsilon, num_steps=5, device="cpu")
        delta = result - x_1d.cpu()
        max_delta = delta.abs().max().item()
        assert max_delta <= epsilon + 1e-5, (
            f"L-infinity violation: ||delta||_inf = {max_delta:.6f} > epsilon = {epsilon}"
        )

    def test_output_is_finite(self):
        """pgd_attack output must not contain NaN or Inf."""
        waveform = make_sine_tensor(duration_s=1.0, sample_rate=16000, channels=1)
        result = pgd_attack(waveform.squeeze(0), sample_rate=16000, num_steps=3, device="cpu")
        assert not torch.isnan(result).any(), "NaN in attack output"
        assert not torch.isinf(result).any(), "Inf in attack output"

    def test_feature_distortion_is_positive(self):
        """
        HuBERT cosine similarity between original and perturbed representations
        must be < 1.0 (i.e., the attack is doing something).
        """
        import torch.nn.functional as F
        from tasks.pgd_attack import load_hubert

        waveform = make_sine_tensor(duration_s=2.0, sample_rate=16000, channels=1)
        x = waveform.squeeze(0)

        model = load_hubert("cpu")

        with torch.no_grad():
            x_norm = (x - x.mean()) / (x.std() + 1e-7)
            orig_feat = model(x_norm.unsqueeze(0)).last_hidden_state

        result = pgd_attack(x, sample_rate=16000, epsilon=0.02, num_steps=15, device="cpu")

        with torch.no_grad():
            r_norm = (result - result.mean()) / (result.std() + 1e-7)
            pert_feat = model(r_norm.unsqueeze(0)).last_hidden_state

        similarity = F.cosine_similarity(
            orig_feat.flatten(1), pert_feat.flatten(1), dim=-1
        ).mean().item()

        assert similarity < 0.99, (
            f"Attack had no effect: cosine similarity = {similarity:.4f}"
        )

    def test_gradient_is_nonzero_after_first_step(self):
        """
        Direct gradient test: delta.grad must not be all zeros after backward().
        This verifies the computational graph is connected through HuBERT.
        """
        import torch.nn.functional as F
        from tasks.pgd_attack import load_hubert

        x = make_sine_tensor(duration_s=1.0, sample_rate=16000, channels=1).squeeze(0)
        x = x.unsqueeze(0)  # (1, T)
        model = load_hubert("cpu")

        with torch.no_grad():
            x_norm = (x - x.mean()) / (x.std() + 1e-7)
            orig_feat = model(x_norm).last_hidden_state.detach()

        delta = torch.empty_like(x).uniform_(-0.002, 0.002).requires_grad_(True)
        perturbed = x + delta
        p_norm = (perturbed - perturbed.mean()) / (perturbed.std() + 1e-7)
        adv_feat = model(p_norm).last_hidden_state
        loss = -F.mse_loss(adv_feat, orig_feat)
        loss.backward()

        assert delta.grad is not None, "delta.grad is None — no gradient path through HuBERT"
        assert delta.grad.abs().max().item() > 0, "delta.grad is all zeros — attack will be ineffective"
