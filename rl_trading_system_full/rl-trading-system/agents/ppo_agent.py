"""
PPO Agent v2 — PyTorch Implementation
======================================
Real gradient descent with Adam optimizer, proper GAE,
clipped surrogate objective, and LSTM feature extraction.

Falls back to NumPy if PyTorch is unavailable.

REPLACE: agents/ppo_agent.py
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
import json

# Try PyTorch, fall back to NumPy
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.distributions import Normal
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


if HAS_TORCH:

    class LSTMActorCritic(nn.Module):
        """LSTM-based Actor-Critic network in PyTorch."""

        def __init__(self, obs_dim: int, action_dim: int, hidden: int = 256, lstm_hidden: int = 128, lstm_layers: int = 2):
            super().__init__()
            self.lstm = nn.LSTM(obs_dim, lstm_hidden, lstm_layers, batch_first=True)
            self.actor_head = nn.Sequential(
                nn.Linear(lstm_hidden, hidden), nn.ReLU(),
                nn.Linear(hidden, hidden), nn.ReLU(),
                nn.Linear(hidden, action_dim), nn.Tanh(),
            )
            self.critic_head = nn.Sequential(
                nn.Linear(lstm_hidden, hidden), nn.ReLU(),
                nn.Linear(hidden, hidden), nn.ReLU(),
                nn.Linear(hidden, 1),
            )
            self.log_std = nn.Parameter(torch.zeros(action_dim))
            self._init_weights()

        def _init_weights(self):
            for m in self.modules():
                if isinstance(m, nn.Linear):
                    nn.init.orthogonal_(m.weight, gain=0.01)
                    nn.init.zeros_(m.bias)

        def forward(self, x):
            if x.dim() == 1:
                x = x.unsqueeze(0).unsqueeze(0)
            elif x.dim() == 2:
                x = x.unsqueeze(0)
            lstm_out, _ = self.lstm(x)
            features = lstm_out[:, -1, :]
            action_mean = self.actor_head(features)
            value = self.critic_head(features)
            return action_mean.squeeze(0), value.squeeze(0), features.squeeze(0)

        def get_action(self, obs, deterministic=False):
            with torch.no_grad():
                obs_t = torch.FloatTensor(obs).to(next(self.parameters()).device)
                mean, value, _ = self.forward(obs_t)
                std = torch.exp(self.log_std.clamp(-3, 1))
                if deterministic:
                    action = mean
                else:
                    dist = Normal(mean, std)
                    action = dist.sample()
                action = action.clamp(-1, 1)
                log_prob = Normal(mean, std).log_prob(action).sum()
                return action.cpu().numpy(), log_prob.item(), value.item()

        def evaluate_actions(self, obs_batch, actions_batch):
            """Used during PPO update to recompute log_probs and values.
            Batched: single LSTM forward pass instead of per-sample loop."""
            device = next(self.parameters()).device
            # Stack all observations into (batch, 1, obs_dim) for batched LSTM
            obs_t = torch.FloatTensor(np.array(obs_batch)).to(device)
            if obs_t.dim() == 2:
                obs_t = obs_t.unsqueeze(1)  # (batch, 1, obs_dim)
            lstm_out, _ = self.lstm(obs_t)
            features = lstm_out[:, -1, :]  # (batch, lstm_hidden)
            means = self.actor_head(features)  # (batch, action_dim)
            values = self.critic_head(features).squeeze(-1)  # (batch,)

            std = torch.exp(self.log_std.clamp(-3, 1))
            dist = Normal(means, std)
            actions_t = torch.FloatTensor(np.array(actions_batch)).to(device)
            log_probs = dist.log_prob(actions_t).sum(dim=-1)
            entropy = dist.entropy().sum(dim=-1).mean()
            return log_probs, values, entropy


class ReplayBuffer:
    def __init__(self):
        self.clear()

    def add(self, obs, action, reward, value, log_prob, done):
        self.observations.append(obs)
        self.actions.append(action)
        self.rewards.append(reward)
        self.values.append(value)
        self.log_probs.append(log_prob)
        self.dones.append(done)

    def clear(self):
        self.observations, self.actions, self.rewards = [], [], []
        self.values, self.log_probs, self.dones = [], [], []

    def compute_gae(self, gamma=0.99, lam=0.95, last_value=0.0):
        T = len(self.rewards)
        advs = np.zeros(T)
        rets = np.zeros(T)
        gae = 0.0
        for t in reversed(range(T)):
            nv = last_value if t == T - 1 else self.values[t + 1]
            nt = 1.0 - float(self.dones[t])
            delta = self.rewards[t] + gamma * nv * nt - self.values[t]
            gae = delta + gamma * lam * nt * gae
            advs[t] = gae
            rets[t] = advs[t] + self.values[t]
        advs = (advs - advs.mean()) / (advs.std() + 1e-8)
        return rets, advs


class PPOAgent:
    """PPO with PyTorch (falls back to NumPy)."""

    def __init__(self, obs_dim, action_dim, learning_rate=3e-4, gamma=0.99,
                 gae_lambda=0.95, clip_epsilon=0.2, entropy_coef=0.01,
                 value_coef=0.5, n_epochs=10, batch_size=64,
                 hidden_dim=256, lstm_hidden_dim=128, num_lstm_layers=2,
                 max_grad_norm=0.5, **kwargs):
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.entropy_coef = entropy_coef
        self.value_coef = value_coef
        self.n_epochs = n_epochs
        self.batch_size = batch_size
        self.max_grad_norm = max_grad_norm
        self.buffer = ReplayBuffer()
        self.total_steps = 0
        self.episodes = 0
        self.training_history = {"episode_rewards": [], "policy_loss": [], "value_loss": [], "entropy": []}

        if HAS_TORCH:
            # Resolve device from config
            from config.settings import CONFIG
            self.device = torch.device(CONFIG.training.device if torch.cuda.is_available() and CONFIG.training.device == "cuda" else "cpu")
            self.network = LSTMActorCritic(obs_dim, action_dim, hidden_dim, lstm_hidden_dim, num_lstm_layers).to(self.device)
            self.optimizer = optim.Adam(self.network.parameters(), lr=learning_rate, eps=1e-5)
        else:
            from agents.networks import ActorCriticNetwork
            self.network = ActorCriticNetwork(obs_dim, action_dim, hidden_dim, lstm_hidden_dim, num_lstm_layers)
            self.lr = learning_rate

    def to_device(self, device_str: str):
        """Move network + optimizer to a new device (cpu/cuda). Call after CONFIG change."""
        if not HAS_TORCH:
            return
        new_device = torch.device(device_str)
        if new_device == self.device:
            return
        self.device = new_device
        self.network.to(self.device)
        # Rebuild optimizer so its internal state tensors are on the correct device
        lr = self.optimizer.param_groups[0]["lr"]
        self.optimizer = optim.Adam(self.network.parameters(), lr=lr, eps=1e-5)

    def select_action(self, obs, deterministic=False):
        if HAS_TORCH:
            return self.network.get_action(obs, deterministic)
        else:
            return self.network.get_action(obs, deterministic)

    def store_transition(self, obs, action, reward, value, log_prob, done):
        self.buffer.add(obs, action, reward, value, log_prob, done)
        self.total_steps += 1

    def train(self):
        if len(self.buffer.observations) < self.batch_size:
            self.buffer.clear()
            return {}

        if HAS_TORCH:
            return self._train_torch()
        else:
            return self._train_numpy()

    def _train_torch(self):
        last_obs = self.buffer.observations[-1]
        _, _, last_val = self.network.get_action(last_obs)
        returns, advantages = self.buffer.compute_gae(self.gamma, self.gae_lambda, last_val)

        obs = self.buffer.observations
        actions = np.array(self.buffer.actions)
        old_log_probs = np.array(self.buffer.log_probs)
        returns_t = torch.FloatTensor(returns).to(self.device)
        advantages_t = torch.FloatTensor(advantages).to(self.device)
        old_lp_t = torch.FloatTensor(old_log_probs).to(self.device)

        total_pl, total_vl, total_ent, n = 0, 0, 0, 0

        for epoch in range(self.n_epochs):
            indices = np.random.permutation(len(obs))
            for start in range(0, len(obs), self.batch_size):
                end = min(start + self.batch_size, len(obs))
                idx = indices[start:end]

                batch_obs = [obs[i] for i in idx]
                batch_actions = actions[idx]
                batch_returns = returns_t[idx]
                batch_advs = advantages_t[idx]
                batch_old_lp = old_lp_t[idx]

                new_lp, new_values, entropy = self.network.evaluate_actions(batch_obs, batch_actions)

                ratio = torch.exp(new_lp - batch_old_lp)
                surr1 = ratio * batch_advs
                surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * batch_advs
                policy_loss = -torch.min(surr1, surr2).mean()
                value_loss = (new_values - batch_returns).pow(2).mean()
                loss = policy_loss + self.value_coef * value_loss - self.entropy_coef * entropy

                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.network.parameters(), self.max_grad_norm)
                self.optimizer.step()

                total_pl += policy_loss.item()
                total_vl += value_loss.item()
                total_ent += entropy.item()
                n += 1

        self.buffer.clear()
        self.episodes += 1
        stats = {"policy_loss": total_pl / max(n, 1), "value_loss": total_vl / max(n, 1), "entropy": total_ent / max(n, 1)}
        self.training_history["policy_loss"].append(stats["policy_loss"])
        self.training_history["value_loss"].append(stats["value_loss"])
        return stats

    def _train_numpy(self):
        """Fallback NumPy training (same as before)."""
        if len(self.buffer.observations) < self.batch_size:
            self.buffer.clear()
            return {}
        last_obs = self.buffer.observations[-1]
        _, _, last_val = self.network.get_action(last_obs)
        _returns, advantages = self.buffer.compute_gae(self.gamma, self.gae_lambda, last_val)

        noise_scale = self.lr * 0.1
        loss_approx = -np.mean(advantages)
        for i, w in enumerate(self.network.actor.weights):
            self.network.actor.weights[i] -= loss_approx * np.random.randn(*w.shape) * noise_scale
        for i, w in enumerate(self.network.critic.weights):
            self.network.critic.weights[i] -= loss_approx * np.random.randn(*w.shape) * noise_scale
        self.network.log_std -= self.lr * 0.01 * np.sign(loss_approx) * np.random.randn(self.action_dim)
        self.network.log_std = np.clip(self.network.log_std, -3, 1)

        self.buffer.clear()
        self.episodes += 1
        return {"policy_loss": float(loss_approx), "value_loss": 0.0, "entropy": 0.0}

    def save(self, path):
        if HAS_TORCH:
            torch.save({"model": self.network.state_dict(), "optimizer": self.optimizer.state_dict(),
                         "steps": self.total_steps, "episodes": self.episodes}, path)
        else:
            params = {"actor_weights": [w.tolist() for w in self.network.actor.weights],
                      "actor_biases": [b.tolist() for b in self.network.actor.biases],
                      "critic_weights": [w.tolist() for w in self.network.critic.weights],
                      "critic_biases": [b.tolist() for b in self.network.critic.biases],
                      "log_std": self.network.log_std.tolist(), "total_steps": self.total_steps, "episodes": self.episodes}
            with open(path, "w") as f:
                json.dump(params, f)

    def load(self, path):
        if HAS_TORCH:
            ckpt = torch.load(path, map_location=self.device)
            self.network.load_state_dict(ckpt["model"])
            self.network.to(self.device)
            self.optimizer.load_state_dict(ckpt["optimizer"])
            self.total_steps = ckpt["steps"]
            self.episodes = ckpt["episodes"]
        else:
            with open(path) as f:
                params = json.load(f)
            for i, w in enumerate(params["actor_weights"]):
                self.network.actor.weights[i] = np.array(w)
            for i, b in enumerate(params["actor_biases"]):
                self.network.actor.biases[i] = np.array(b)
            self.network.log_std = np.array(params["log_std"])
            self.total_steps = params["total_steps"]
            self.episodes = params["episodes"]