import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np
from collections import deque

class MoEFeature(nn.Module):
    def __init__(self, state_dim, num_experts=2):
        super(MoEFeature, self).__init__()
        self.num_experts = num_experts
        
        self.experts = nn.ModuleList([
            nn.Sequential(
                nn.Linear(state_dim, 128),
                nn.ReLU(),
                nn.Linear(128, 128),
                nn.ReLU()
            ) for _ in range(num_experts)
        ])
        
        self.gating_network = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, num_experts),
            nn.Softmax(dim=-1)
        )
        
    def forward(self, state, return_gate_weights=False):
        # Detach state for gating network to prevent representation instability
        gate_weights = self.gating_network(state.detach())
        
        expert_outputs = []
        for i, expert in enumerate(self.experts):
            expert_outputs.append(expert(state))
            
        expert_outputs = torch.stack(expert_outputs, dim=1)
        weighted_features = expert_outputs * gate_weights.unsqueeze(-1)
        features = weighted_features.sum(dim=1)
        
        if return_gate_weights:
            return features, gate_weights
        return features


class MoEDQN(nn.Module):
    def __init__(self, state_dim, action_dim, num_experts=2):
        super(MoEDQN, self).__init__()
        
        self.feature_layer = MoEFeature(state_dim, num_experts)
        
        self.value_stream = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
        
        self.advantage_stream = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim)
        )
        
    def forward(self, state, return_gate_weights=False):
        if return_gate_weights:
            features, gate_weights = self.feature_layer(state, return_gate_weights=True)
        else:
            features = self.feature_layer(state)
            
        value = self.value_stream(features)
        advantage = self.advantage_stream(features)
        
        q_vals = value + (advantage - advantage.mean(dim=1, keepdim=True))
        
        if return_gate_weights:
            return q_vals, gate_weights
        return q_vals


class MoEAgent:
    def __init__(self, state_dim, action_dim, num_experts=2, lr=1e-3, gamma=0.99, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.995, buffer_size=100000, batch_size=64):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.q_network = MoEDQN(state_dim, action_dim, num_experts).to(self.device)
        self.target_network = MoEDQN(state_dim, action_dim, num_experts).to(self.device)
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
        
    def save(self, filepath):
        torch.save(self.q_network.state_dict(), filepath)
        
    def load(self, filepath):
        self.q_network.load_state_dict(torch.load(filepath, map_location=self.device))
        self.update_target_network()
