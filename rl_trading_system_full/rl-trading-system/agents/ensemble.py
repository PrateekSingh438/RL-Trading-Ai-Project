"""
Ensemble Agent
==============
Combines PPO and SAC agents via weighted averaging or meta-policy.
Leverages PPO's stability and SAC's exploration.
"""
import numpy as np
from typing import Dict, Tuple, Optional
from agents.ppo_agent import PPOAgent
from agents.sac_agent import SACAgent
from agents.networks import MLP


class MetaPolicyNetwork:
    """
    Meta-policy that learns to weight PPO and SAC actions
    based on current market state.
    """

    def __init__(self, obs_dim: int, hidden_dim: int = 128):
        self.network = MLP([obs_dim, hidden_dim, 64, 2], activation="relu")

    def get_weights(self, observation: np.ndarray) -> np.ndarray:
        """Return softmax weights for [PPO, SAC]."""
        if observation.ndim > 1:
            observation = observation[-1]  # Use latest observation
        logits = self.network.forward(observation)
        exp_logits = np.exp(logits - np.max(logits))
        return exp_logits / (np.sum(exp_logits) + 1e-10)


class EnsembleAgent:
    """
    Ensemble of PPO + SAC agents.

    Combination strategies:
    1. Weighted average (fixed or adaptive)
    2. Meta-policy network that learns optimal weighting
    """

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        ppo_weight: float = 0.5,
        sac_weight: float = 0.5,
        use_meta_policy: bool = False,
        ppo_kwargs: dict = None,
        sac_kwargs: dict = None,
        meta_hidden_dim: int = 128
    ):
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.ppo_weight = ppo_weight
        self.sac_weight = sac_weight
        self.use_meta_policy = use_meta_policy

        # Initialize sub-agents
        ppo_kwargs = ppo_kwargs or {}
        sac_kwargs = sac_kwargs or {}
        self.ppo = PPOAgent(obs_dim=obs_dim, action_dim=action_dim, **ppo_kwargs)
        self.sac = SACAgent(obs_dim=obs_dim, action_dim=action_dim, **sac_kwargs)

        # Meta-policy (optional)
        if use_meta_policy:
            self.meta_policy = MetaPolicyNetwork(obs_dim, meta_hidden_dim)
        else:
            self.meta_policy = None

        # Performance tracking for adaptive weighting
        self.ppo_rewards = []
        self.sac_rewards = []
        self.weight_history = []

        # Decision explanation
        self.last_decision_info = {}

    def select_action(
        self, observation: np.ndarray, deterministic: bool = False
    ) -> Tuple[np.ndarray, Dict]:
        """
        Select action from ensemble.

        Returns:
            (action, decision_info)
        """
        # Get actions from both agents
        ppo_action, ppo_log_prob, ppo_value = self.ppo.select_action(observation, deterministic)
        sac_action = self.sac.select_action(observation, deterministic)

        # Determine weights
        if self.use_meta_policy and self.meta_policy is not None:
            weights = self.meta_policy.get_weights(observation)
            w_ppo, w_sac = weights[0], weights[1]
        else:
            w_ppo, w_sac = self.ppo_weight, self.sac_weight

        # Weighted combination
        action = w_ppo * ppo_action + w_sac * sac_action
        action = np.clip(action, -1, 1)

        # Store decision info for explainability
        self.last_decision_info = {
            "ppo_action": ppo_action.tolist(),
            "sac_action": sac_action.tolist(),
            "ensemble_action": action.tolist(),
            "ppo_weight": float(w_ppo),
            "sac_weight": float(w_sac),
            "ppo_value": float(ppo_value),
            "ppo_log_prob": float(ppo_log_prob),
            "agreement": float(1.0 - np.mean(np.abs(ppo_action - sac_action)))
        }

        self.weight_history.append((w_ppo, w_sac))
        return action, self.last_decision_info

    def store_transition(
        self, obs, action, reward, next_obs, done, value=None, log_prob=None
    ):
        """Store transition for both agents."""
        # PPO (on-policy)
        if value is not None and log_prob is not None:
            self.ppo.store_transition(obs, action, reward, value, log_prob, done)

        # SAC (off-policy)
        self.sac.store_transition(obs, action, reward, next_obs, done)

    def train(self) -> Dict[str, float]:
        """Train both agents and update weights."""
        ppo_stats = self.ppo.train()
        sac_stats = self.sac.train()

        # Adaptive weight update based on recent performance
        self._update_weights()

        combined_stats = {}
        for k, v in ppo_stats.items():
            combined_stats[f"ppo_{k}"] = v
        for k, v in sac_stats.items():
            combined_stats[f"sac_{k}"] = v
        combined_stats["ppo_weight"] = self.ppo_weight
        combined_stats["sac_weight"] = self.sac_weight

        return combined_stats

    def _update_weights(self):
        """
        Adaptively adjust weights based on recent performance.
        Agent with better recent returns gets higher weight.
        """
        window = 50
        if len(self.ppo_rewards) > window and len(self.sac_rewards) > window:
            ppo_perf = np.mean(self.ppo_rewards[-window:])
            sac_perf = np.mean(self.sac_rewards[-window:])

            total = abs(ppo_perf) + abs(sac_perf) + 1e-10
            self.ppo_weight = 0.3 + 0.4 * (abs(ppo_perf) / total)
            self.sac_weight = 1.0 - self.ppo_weight

    def get_explainability(self) -> Dict:
        """
        Generate explainability information for the last decision.
        """
        info = self.last_decision_info.copy()

        # Determine dominant agent
        if info.get("ppo_weight", 0.5) > info.get("sac_weight", 0.5):
            info["dominant_agent"] = "PPO (stable policy)"
        else:
            info["dominant_agent"] = "SAC (exploratory policy)"

        # Agreement analysis
        agreement = info.get("agreement", 0.5)
        if agreement > 0.8:
            info["consensus"] = "Strong agreement between agents"
        elif agreement > 0.5:
            info["consensus"] = "Moderate agreement"
        else:
            info["consensus"] = "Agents disagree - ensemble smoothing applied"

        return info

    def to_device(self, device_str: str):
        """Move PPO network to a new device. SAC is NumPy-only, no move needed."""
        if hasattr(self.ppo, "to_device"):
            self.ppo.to_device(device_str)

    def save(self, ppo_path: str, sac_path: str):
        self.ppo.save(ppo_path)
        self.sac.save(sac_path)

    def load(self, ppo_path: str, sac_path: str):
        self.ppo.load(ppo_path)
        self.sac.load(sac_path)
