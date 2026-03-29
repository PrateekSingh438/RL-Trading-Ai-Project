"""
Neural Network Architectures
=============================
LSTM-based feature extractor with Actor-Critic networks
for PPO and SAC agents.
"""
import numpy as np
from typing import Tuple, List, Optional


class LSTMCell:
    """Minimal LSTM cell implementation (NumPy-based for portability)."""

    def __init__(self, input_dim: int, hidden_dim: int):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim

        # Xavier initialization
        scale_i = np.sqrt(2.0 / (input_dim + hidden_dim))
        scale_h = np.sqrt(2.0 / (hidden_dim + hidden_dim))

        # Gates: forget, input, candidate, output
        self.W_f = np.random.randn(input_dim, hidden_dim) * scale_i
        self.U_f = np.random.randn(hidden_dim, hidden_dim) * scale_h
        self.b_f = np.ones(hidden_dim)  # Bias forget gate to 1

        self.W_i = np.random.randn(input_dim, hidden_dim) * scale_i
        self.U_i = np.random.randn(hidden_dim, hidden_dim) * scale_h
        self.b_i = np.zeros(hidden_dim)

        self.W_c = np.random.randn(input_dim, hidden_dim) * scale_i
        self.U_c = np.random.randn(hidden_dim, hidden_dim) * scale_h
        self.b_c = np.zeros(hidden_dim)

        self.W_o = np.random.randn(input_dim, hidden_dim) * scale_i
        self.U_o = np.random.randn(hidden_dim, hidden_dim) * scale_h
        self.b_o = np.zeros(hidden_dim)

    def forward(
        self, x: np.ndarray, h_prev: np.ndarray, c_prev: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Forward pass through LSTM cell."""
        f = self._sigmoid(x @ self.W_f + h_prev @ self.U_f + self.b_f)
        i = self._sigmoid(x @ self.W_i + h_prev @ self.U_i + self.b_i)
        c_hat = np.tanh(x @ self.W_c + h_prev @ self.U_c + self.b_c)
        o = self._sigmoid(x @ self.W_o + h_prev @ self.U_o + self.b_o)

        c = f * c_prev + i * c_hat
        h = o * np.tanh(c)
        return h, c

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


class LSTMFeatureExtractor:
    """
    Multi-layer LSTM for time-series feature extraction.
    Processes sequential market data into a fixed-size representation.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.1
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout

        # Stack of LSTM cells
        self.cells = []
        for layer in range(num_layers):
            in_dim = input_dim if layer == 0 else hidden_dim
            self.cells.append(LSTMCell(in_dim, hidden_dim))

    def forward(self, sequence: np.ndarray) -> np.ndarray:
        """
        Process a sequence through the LSTM stack.

        Args:
            sequence: Shape (seq_len, input_dim) or (input_dim,) for single step

        Returns:
            Final hidden state of shape (hidden_dim,)
        """
        if sequence.ndim == 1:
            sequence = sequence.reshape(1, -1)

        # If input features don't match expected input_dim, use projection
        if sequence.shape[1] != self.input_dim:
            # Simple linear projection to match expected dim
            proj = np.zeros((sequence.shape[1], self.input_dim))
            min_dim = min(sequence.shape[1], self.input_dim)
            proj[:min_dim, :min_dim] = np.eye(min_dim)
            sequence = sequence @ proj

        seq_len = sequence.shape[0]
        batch_h = [np.zeros(self.hidden_dim) for _ in range(self.num_layers)]
        batch_c = [np.zeros(self.hidden_dim) for _ in range(self.num_layers)]

        for t in range(seq_len):
            x = sequence[t]
            for layer in range(self.num_layers):
                h, c = self.cells[layer].forward(x, batch_h[layer], batch_c[layer])
                batch_h[layer] = h
                batch_c[layer] = c
                x = h  # Output of this layer is input to next

        return batch_h[-1]  # Return final layer's hidden state


class MLP:
    """Simple multi-layer perceptron."""

    def __init__(self, layer_dims: List[int], activation: str = "relu"):
        self.weights = []
        self.biases = []
        self.activation = activation

        for i in range(len(layer_dims) - 1):
            scale = np.sqrt(2.0 / layer_dims[i])
            self.weights.append(np.random.randn(layer_dims[i], layer_dims[i + 1]) * scale)
            self.biases.append(np.zeros(layer_dims[i + 1]))

    def forward(self, x: np.ndarray) -> np.ndarray:
        for i, (w, b) in enumerate(zip(self.weights, self.biases)):
            x = x @ w + b
            if i < len(self.weights) - 1:  # No activation on output
                if self.activation == "relu":
                    x = np.maximum(0, x)
                elif self.activation == "tanh":
                    x = np.tanh(x)
        return x


class ActorCriticNetwork:
    """
    Actor-Critic architecture with LSTM feature extractor.

    Actor: outputs action means (and log_stds for SAC)
    Critic: outputs state value V(s) or Q(s,a)
    """

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_dim: int = 256,
        lstm_hidden_dim: int = 128,
        num_lstm_layers: int = 2
    ):
        self.obs_dim = obs_dim
        self.action_dim = action_dim

        # LSTM for sequential feature extraction
        self.lstm = LSTMFeatureExtractor(
            input_dim=obs_dim,
            hidden_dim=lstm_hidden_dim,
            num_layers=num_lstm_layers
        )

        # Actor network (policy)
        self.actor = MLP(
            [lstm_hidden_dim, hidden_dim, hidden_dim, action_dim],
            activation="relu"
        )
        self.log_std = np.zeros(action_dim)  # Learnable log standard deviation

        # Critic network (value)
        self.critic = MLP(
            [lstm_hidden_dim, hidden_dim, hidden_dim, 1],
            activation="relu"
        )

    def get_action(
        self, obs_sequence: np.ndarray, deterministic: bool = False
    ) -> Tuple[np.ndarray, float, float]:
        """
        Get action from policy.

        Args:
            obs_sequence: Observation sequence (seq_len, obs_dim)
            deterministic: If True, return mean action

        Returns:
            (action, log_prob, value)
        """
        # Extract features
        if obs_sequence.ndim == 1:
            obs_sequence = obs_sequence.reshape(1, -1)

        features = self.lstm.forward(obs_sequence)

        # Actor
        action_mean = np.tanh(self.actor.forward(features))
        std = np.exp(np.clip(self.log_std, -5, 2))

        if deterministic:
            action = action_mean
        else:
            action = action_mean + std * np.random.randn(self.action_dim)
            action = np.clip(action, -1, 1)

        # Log probability (Gaussian)
        log_prob = -0.5 * np.sum(
            ((action - action_mean) / (std + 1e-8)) ** 2
            + 2 * self.log_std
            + np.log(2 * np.pi)
        )

        # Critic
        value = self.critic.forward(features)[0]

        return action, log_prob, value

    def get_value(self, obs_sequence: np.ndarray) -> float:
        """Get state value estimate."""
        if obs_sequence.ndim == 1:
            obs_sequence = obs_sequence.reshape(1, -1)
        features = self.lstm.forward(obs_sequence)
        return self.critic.forward(features)[0]


class QNetwork:
    """Q-network for SAC: Q(s, a) -> scalar."""

    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int = 256,
                 lstm_hidden_dim: int = 128, num_lstm_layers: int = 2):
        self.lstm = LSTMFeatureExtractor(obs_dim, lstm_hidden_dim, num_lstm_layers)
        self.q_net = MLP(
            [lstm_hidden_dim + action_dim, hidden_dim, hidden_dim, 1],
            activation="relu"
        )

    def forward(self, obs_sequence: np.ndarray, action: np.ndarray) -> float:
        if obs_sequence.ndim == 1:
            obs_sequence = obs_sequence.reshape(1, -1)
        features = self.lstm.forward(obs_sequence)
        # Handle action dimension mismatch
        if len(action) != self.q_net.weights[0].shape[0] - len(features):
            # Pad or truncate action
            expected_action_dim = self.q_net.weights[0].shape[0] - len(features)
            if len(action) < expected_action_dim:
                action = np.concatenate([action, np.zeros(expected_action_dim - len(action))])
            else:
                action = action[:expected_action_dim]
        x = np.concatenate([features, action])
        return self.q_net.forward(x)[0]
