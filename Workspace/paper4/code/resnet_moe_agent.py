import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np
from collections import deque

try:
    from etsi_cam_layer import ACTION_DIM
except ImportError:
    ACTION_DIM = 24

class ResidualBlock(nn.Module):
    def __init__(self, hidden_dim=128):
        super(ResidualBlock, self).__init__()
        self.fc1 = nn.Linear(hidden_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)

    def forward(self, x):
        identity = x
        out = self.fc1(x)
        out = self.relu(out)
        out = self.fc2(out)
        out += identity
        out = self.relu(out)
        return out

class ResNetFeatureExtractor(nn.Module):
    def __init__(self, state_dim=5, hidden_dim=128, num_blocks=2):
        super(ResNetFeatureExtractor, self).__init__()
        self.input_layer = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU()
        )
        self.res_blocks = nn.Sequential(*[ResidualBlock(hidden_dim) for _ in range(num_blocks)])
        
    def forward(self, x):
        x = self.input_layer(x)
        x = self.res_blocks(x)
        return x

class DuelingExpert(nn.Module):
    def __init__(self, hidden_dim=128, action_dim=ACTION_DIM):
        super(DuelingExpert, self).__init__()
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim)
        )
        
    def forward(self, x):
        value = self.value_stream(x)
        advantage = self.advantage_stream(x)
        q_vals = value + (advantage - advantage.mean(dim=1, keepdim=True))
        return q_vals

class ResNetMoEDQN(nn.Module):
    def __init__(self, state_dim=5, action_dim=ACTION_DIM, num_experts=3, hidden_dim=128):
        super(ResNetMoEDQN, self).__init__()
        self.feature_extractor = ResNetFeatureExtractor(state_dim, hidden_dim, num_blocks=2)
        
        self.gating_network = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, num_experts),
            nn.Softmax(dim=-1)
        )
        
        self.experts = nn.ModuleList([DuelingExpert(hidden_dim, action_dim) for _ in range(num_experts)])
        
    def forward(self, state, return_gate_weights=False):
        features = self.feature_extractor(state)
        # Detach features for gating network to prevent representation instability
        gate_weights = self.gating_network(features.detach())
        
        expert_outputs = []
        for expert in self.experts:
            expert_outputs.append(expert(features))
            
        expert_outputs = torch.stack(expert_outputs, dim=1)
        weighted_q_vals = expert_outputs * gate_weights.unsqueeze(-1)
        q_vals = weighted_q_vals.sum(dim=1)
        
        if return_gate_weights:
            return q_vals, gate_weights
        return q_vals

class ResNetMoEAgent:
    def __init__(self, state_dim=5, action_dim=ACTION_DIM, num_experts=3, hidden_dim=128, lr=1e-3, gamma=0.99, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.995, buffer_size=100000, batch_size=64, target_update_freq=1):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.q_network = ResNetMoEDQN(state_dim, action_dim, num_experts, hidden_dim).to(self.device)
        self.target_network = ResNetMoEDQN(state_dim, action_dim, num_experts, hidden_dim).to(self.device)
        self.q_net = self.q_network
        self.q_target = self.target_network
        self.update_target_network()
        
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=lr)
        self.criterion = nn.MSELoss()
        
        self.memory = deque(maxlen=buffer_size)
        
    def update_target_network(self):
        self.target_network.load_state_dict(self.q_network.state_dict())
        
    def act(self, state, evaluate=False):
        if not evaluate and random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
            
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        self.q_network.eval()
        with torch.no_grad():
            q_vals = self.q_network(state_tensor)
        self.q_network.train()
        
        return torch.argmax(q_vals).item()
        
    def select_action(self, state, evaluate=False):
        return self.act(state, evaluate=evaluate)
        
    def store_transition(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
        
    def train_step(self):
        if len(self.memory) < self.batch_size:
            return 0.0
            
        batch = random.sample(self.memory, self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        
        states = torch.FloatTensor(np.array(states)).to(self.device)
        actions = torch.LongTensor(actions).unsqueeze(1).to(self.device)
        rewards = torch.FloatTensor(rewards).unsqueeze(1).to(self.device)
        next_states = torch.FloatTensor(np.array(next_states)).to(self.device)
        dones = torch.FloatTensor(dones).unsqueeze(1).to(self.device)
        
        q_vals_all, gate_weights = self.q_network(states, return_gate_weights=True)
        q_vals = q_vals_all.gather(1, actions)
        
        with torch.no_grad():
            next_actions = self.q_network(next_states).argmax(dim=1, keepdim=True)
            next_q_vals = self.target_network(next_states).gather(1, next_actions)
            target_q_vals = rewards + self.gamma * next_q_vals * (1 - dones)
            
        loss = self.criterion(q_vals, target_q_vals)
        
        # Load balancing loss (coefficient of variation of gate weights across batch)
        # gate_weights shape: (batch_size, num_experts)
        importance = gate_weights.mean(dim=0) # mean probability per expert
        cv_squared = torch.var(importance) / (torch.mean(importance)**2 + 1e-8)
        lb_loss = 0.01 * cv_squared
        
        total_loss = loss + lb_loss
        
        self.optimizer.zero_grad()
        total_loss.backward()
        self.optimizer.step()
        
        return total_loss.item()
        
    def update_epsilon(self):
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

    def get_latent_and_gate(self, state):
        """
        Extract 128-dimensional ResNet latent feature vector and 3-dimensional
        Softmax Gating weights for the given state.

        Parameters:
            state (np.ndarray or list or torch.Tensor): state vector of shape (5,) or (batch_size, 5).

        Returns:
            Tuple[np.ndarray, np.ndarray]:
                - latent_features: shape (128,) for single state, or (batch_size, 128)
                - gating_weights: shape (3,) for single state, or (batch_size, 3)
        """
        is_single = False
        if isinstance(state, (list, tuple)):
            state = np.array(state, dtype=np.float32)

        if isinstance(state, np.ndarray):
            if state.ndim == 1:
                is_single = True
                state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            else:
                state_tensor = torch.FloatTensor(state).to(self.device)
        elif isinstance(state, torch.Tensor):
            if state.ndim == 1:
                is_single = True
                state_tensor = state.unsqueeze(0).to(self.device)
            else:
                state_tensor = state.to(self.device)
        else:
            state_tensor = torch.FloatTensor(np.array(state)).unsqueeze(0).to(self.device)
            is_single = True

        was_training = self.q_network.training
        self.q_network.eval()
        with torch.no_grad():
            features = self.q_network.feature_extractor(state_tensor)
            gate_weights = self.q_network.gating_network(features)

        if was_training:
            self.q_network.train()

        feat_np = features.cpu().numpy()
        gate_np = gate_weights.cpu().numpy()

        if is_single:
            return feat_np.squeeze(0), gate_np.squeeze(0)
        return feat_np, gate_np
        
    def save(self, filepath):
        torch.save(self.q_network.state_dict(), filepath)
        
    def load(self, filepath):
        checkpoint = torch.load(filepath, map_location=self.device)
        if isinstance(checkpoint, dict) and "q_net" in checkpoint and not any(k.startswith("feature_extractor.") or k.startswith("gating_network.") for k in checkpoint.keys()):
            self.q_network.load_state_dict(checkpoint["q_net"])
        else:
            self.q_network.load_state_dict(checkpoint)
        self.update_target_network()
