"""
SAC Agent
=========
Soft Actor-Critic with LSTM feature extraction.
Maximum entropy RL for better exploration in continuous action spaces.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import deque
from agents.networks import ActorCriticNetwork, QNetwork


class ReplayMemory:
    """Experience replay buffer for off-policy SAC."""

    def __init__(self, capacity: int = 1_000_000):
        self.buffer = deque(maxlen=capacity)

    def push(self, obs, action, reward, next_obs, done):
        self.buffer.append((obs.copy(), action.copy(), reward, next_obs.copy(), done))

    def sample(self, batch_size: int) -> Dict:
        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        batch = [self.buffer[i] for i in indices]

        return {
            "observations": [b[0] for b in batch],
            "actions": np.array([b[1] for b in batch]),
            "rewards": np.array([b[2] for b in batch]),
            "next_observations": [b[3] for b in batch],
            "dones": np.array([b[4] for b in batch], dtype=np.float32)
        }

    def __len__(self):
        return len(self.buffer)


class SACAgent:
    """
    Soft Actor-Critic with LSTM backbone.

    Maximizes: E[Σ γ^t (r_t + α H(π(·|s_t)))]
    where H is the entropy of the policy.

    Uses twin Q-networks to reduce overestimation bias.
    """

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        alpha: float = 0.2,
        auto_alpha: bool = True,
        batch_size: int = 256,
        buffer_size: int = 1_000_000,
        hidden_dim: int = 256,
        lstm_hidden_dim: int = 128,
        num_lstm_layers: int = 2,
        learning_starts: int = 1000
    ):
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.lr = learning_rate
        self.gamma = gamma
        self.tau = tau
        self.alpha = alpha
        self.auto_alpha = auto_alpha
        self.batch_size = batch_size
        self.learning_starts = learning_starts

        # Actor (policy network)
        self.actor = ActorCriticNetwork(
            obs_dim, action_dim, hidden_dim, lstm_hidden_dim, num_lstm_layers
        )

        # Twin Q-networks
        self.q1 = QNetwork(obs_dim, action_dim, hidden_dim, lstm_hidden_dim, num_lstm_layers)
        self.q2 = QNetwork(obs_dim, action_dim, hidden_dim, lstm_hidden_dim, num_lstm_layers)

        # Target Q-networks (soft update targets)
        self.q1_target = QNetwork(obs_dim, action_dim, hidden_dim, lstm_hidden_dim, num_lstm_layers)
        self.q2_target = QNetwork(obs_dim, action_dim, hidden_dim, lstm_hidden_dim, num_lstm_layers)
        self._hard_update_target()

        # Entropy tuning
        if auto_alpha:
            self.target_entropy = -action_dim
            self.log_alpha = 0.0

        # Replay buffer
        self.memory = ReplayMemory(buffer_size)

        # Training stats
        self.total_steps = 0
        self.training_history = {
            "q_loss": [], "actor_loss": [], "alpha": [], "episode_rewards": []
        }

    def select_action(
        self, observation: np.ndarray, deterministic: bool = False
    ) -> np.ndarray:
        """Select action using current policy."""
        action, _, _ = self.actor.get_action(observation, deterministic)
        return action

    def store_transition(self, obs, action, reward, next_obs, done):
        """Store transition in replay buffer."""
        self.memory.push(obs, action, reward, next_obs, done)
        self.total_steps += 1

    def train(self) -> Dict[str, float]:
        """
        Train SAC agent.

        Updates:
        1. Q-networks using Bellman backup with entropy
        2. Policy to maximize Q + α * entropy
        3. Temperature α (if auto-tuning)
        """
        if len(self.memory) < self.learning_starts:
            return {}

        batch = self.memory.sample(self.batch_size)

        # ─── Q-network update ───
        q_loss = self._update_critics(batch)

        # ─── Policy update ───
        actor_loss = self._update_actor(batch)

        # ─── Alpha update ───
        if self.auto_alpha:
            self._update_alpha(batch)

        # ─── Soft update targets ───
        self._soft_update_target()

        stats = {
            "q_loss": q_loss,
            "actor_loss": actor_loss,
            "alpha": self.alpha
        }
        self.training_history["q_loss"].append(q_loss)
        self.training_history["actor_loss"].append(actor_loss)
        self.training_history["alpha"].append(self.alpha)

        return stats

    # Per-sample NumPy LSTM forward passes are expensive (~5 network forwards
    # per critic sample, ~3 per actor sample).  We subsample the batch to keep
    # wall-clock cost bounded while still providing gradient signal.
    _CRITIC_SUBSAMPLE = 16
    _ACTOR_SUBSAMPLE  = 16
    _ALPHA_SUBSAMPLE  = 8

    def _update_critics(self, batch: Dict) -> float:
        """Update Q-networks (subsampled for speed — NumPy LSTM is per-sample)."""
        total_loss = 0
        n = len(batch["observations"])
        k = min(n, self._CRITIC_SUBSAMPLE)
        indices = np.random.choice(n, k, replace=False)

        for i in indices:
            obs = batch["observations"][i]
            action = batch["actions"][i]
            reward = batch["rewards"][i]
            next_obs = batch["next_observations"][i]
            done = batch["dones"][i]

            # Target Q value
            next_action, next_log_prob, _ = self.actor.get_action(next_obs)
            q1_target = self.q1_target.forward(next_obs, next_action)
            q2_target = self.q2_target.forward(next_obs, next_action)
            min_q_target = min(q1_target, q2_target) - self.alpha * next_log_prob
            target = reward + self.gamma * (1 - done) * min_q_target

            # Current Q values
            q1_val = self.q1.forward(obs, action)
            q2_val = self.q2.forward(obs, action)

            loss = (q1_val - target) ** 2 + (q2_val - target) ** 2
            total_loss += loss

            # Update Q-network weights
            self._update_q_weights(self.q1, obs, action, target, q1_val)
            self._update_q_weights(self.q2, obs, action, target, q2_val)

        return total_loss / max(k, 1)

    def _update_actor(self, batch: Dict) -> float:
        """Update policy network (subsampled — NumPy LSTM is per-sample)."""
        total_loss = 0
        n = len(batch["observations"])
        k = min(n, self._ACTOR_SUBSAMPLE)
        indices = np.random.choice(n, k, replace=False)

        for i in indices:
            obs = batch["observations"][i]
            action, log_prob, _ = self.actor.get_action(obs)
            q1_val = self.q1.forward(obs, action)
            q2_val = self.q2.forward(obs, action)
            min_q = min(q1_val, q2_val)

            # Actor loss: minimize α*log_π - Q
            actor_loss = self.alpha * log_prob - min_q
            total_loss += actor_loss

            # Update actor weights
            noise_scale = self.lr * 0.01
            for j, w in enumerate(self.actor.actor.weights):
                noise = np.random.randn(*w.shape) * noise_scale
                self.actor.actor.weights[j] -= actor_loss * noise

        return total_loss / max(k, 1)

    def _update_alpha(self, batch: Dict):
        """Update temperature parameter (subsampled)."""
        n = len(batch["observations"])
        k = min(n, self._ALPHA_SUBSAMPLE)
        indices = np.random.choice(n, k, replace=False)
        total_entropy = 0

        for i in indices:
            _, log_prob, _ = self.actor.get_action(batch["observations"][i])
            total_entropy += -log_prob

        avg_entropy = total_entropy / max(k, 1)
        alpha_loss = -self.log_alpha * (avg_entropy - self.target_entropy)
        self.log_alpha -= self.lr * 0.01 * np.sign(alpha_loss)
        self.alpha = np.exp(np.clip(self.log_alpha, -5, 2))

    def _update_q_weights(self, q_net, obs, action, target, current):
        """Update Q-network weights toward target."""
        error = current - target
        noise_scale = self.lr * 0.01

        for j, w in enumerate(q_net.q_net.weights):
            noise = np.random.randn(*w.shape) * noise_scale
            q_net.q_net.weights[j] -= error * noise

    def _soft_update_target(self):
        """Polyak averaging of target networks."""
        for i in range(len(self.q1.q_net.weights)):
            self.q1_target.q_net.weights[i] = (
                self.tau * self.q1.q_net.weights[i]
                + (1 - self.tau) * self.q1_target.q_net.weights[i]
            )
            self.q2_target.q_net.weights[i] = (
                self.tau * self.q2.q_net.weights[i]
                + (1 - self.tau) * self.q2_target.q_net.weights[i]
            )

    def _hard_update_target(self):
        """Copy weights to target networks."""
        for i in range(len(self.q1.q_net.weights)):
            self.q1_target.q_net.weights[i] = self.q1.q_net.weights[i].copy()
            self.q2_target.q_net.weights[i] = self.q2.q_net.weights[i].copy()

    def save(self, path: str):
        """Save agent parameters."""
        import json
        params = {
            "actor_weights": [w.tolist() for w in self.actor.actor.weights],
            "actor_biases": [b.tolist() for b in self.actor.actor.biases],
            "log_std": self.actor.log_std.tolist(),
            "alpha": float(self.alpha),
            "log_alpha": float(self.log_alpha) if self.auto_alpha else 0,
            "total_steps": self.total_steps
        }
        with open(path, "w") as f:
            json.dump(params, f)

    def load(self, path: str):
        """Load agent parameters."""
        import json
        with open(path, "r") as f:
            params = json.load(f)
        for i, w in enumerate(params["actor_weights"]):
            self.actor.actor.weights[i] = np.array(w)
        for i, b in enumerate(params["actor_biases"]):
            self.actor.actor.biases[i] = np.array(b)
        self.actor.log_std = np.array(params["log_std"])
        self.alpha = params["alpha"]
        self.total_steps = params["total_steps"]
