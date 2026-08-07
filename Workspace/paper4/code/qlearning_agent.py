import numpy as np
import pickle
import os

class QLearningAgent:
    def __init__(self, state_bins, action_dim=16, alpha=0.1, gamma=0.99, epsilon=1.0, epsilon_decay=0.995, epsilon_min=0.01):
        """
        state_bins: list of integers representing the number of bins for each state variable.
        """
        self.state_bins = state_bins
        self.action_dim = action_dim
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        
        # Initialize Q-table
        # Shape: (bins_s1, bins_s2, bins_s3, bins_s4, bins_s5, action_dim)
        table_shape = tuple(state_bins) + (action_dim,)
        self.q_table = np.zeros(table_shape, dtype=np.float32)
        
        # State space bounds (approximate, based on observation)
        # cbr_global (0 to 1), n_neighbors (0 to 200), v_norm (0 to 1), dt_since_last_cam (0 to 1), cbr_smoothed (0 to 1)
        self.state_bounds = [
            (0.0, 1.0),
            (0.0, 4.0),
            (0.0, 1.0),
            (0.0, 1.0),
            (0.0, 1.0)
        ]

    def _discretize_state(self, state):
        discretized = []
        for i, val in enumerate(state):
            low, high = self.state_bounds[i]
            # Clip value
            val = max(low, min(val, high))
            # Find bin
            bin_idx = int(np.floor((val - low) / (high - low) * self.state_bins[i]))
            # Handle edge case where val == high
            if bin_idx == self.state_bins[i]:
                bin_idx -= 1
            discretized.append(bin_idx)
        return tuple(discretized)

    def act(self, state, evaluate=False):
        d_state = self._discretize_state(state)
        
        if not evaluate and np.random.rand() < self.epsilon:
            return np.random.randint(self.action_dim)
        else:
            # Return action with max Q-value
            q_values = self.q_table[d_state]
            # Tie-breaking randomly among max values
            max_q = np.max(q_values)
            best_actions = np.where(q_values == max_q)[0]
            return np.random.choice(best_actions)

    def store_transition(self, state, action, reward, next_state, done):
        d_state = self._discretize_state(state)
        d_next_state = self._discretize_state(next_state)
        
        best_next_action = np.argmax(self.q_table[d_next_state])
        td_target = reward + (0 if done else self.gamma * self.q_table[d_next_state][best_next_action])
        td_error = td_target - self.q_table[d_state][action]
        self.q_table[d_state][action] += self.alpha * td_error

    def update_epsilon(self):
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            self.epsilon = max(self.epsilon_min, self.epsilon)

    def save(self, filepath):
        with open(filepath, 'wb') as f:
            pickle.dump({
                'q_table': self.q_table,
                'state_bins': self.state_bins,
                'state_bounds': self.state_bounds,
                'action_dim': self.action_dim,
                'alpha': self.alpha,
                'gamma': self.gamma,
                'epsilon': self.epsilon,
                'epsilon_decay': self.epsilon_decay,
                'epsilon_min': self.epsilon_min
            }, f)

    def load(self, filepath):
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.q_table = data['q_table']
            self.state_bins = data['state_bins']
            self.state_bounds = data['state_bounds']
            self.action_dim = data['action_dim']
            self.alpha = data['alpha']
            self.gamma = data['gamma']
            self.epsilon = data['epsilon']
            self.epsilon_decay = data['epsilon_decay']
            self.epsilon_min = data['epsilon_min']
