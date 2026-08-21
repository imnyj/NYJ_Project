import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import random
from collections import deque

try:
    from etsi_cam_layer import ACTION_DIM
except ImportError:
    ACTION_DIM = 24

class DoubleDQN(nn.Module):
    def __init__(self, state_dim=5, action_dim=ACTION_DIM):
        super(DoubleDQN, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim)
        )

    def forward(self, state):
        return self.network(state)

QNetwork = DoubleDQN

class DDQNAgent:
    def __init__(self, state_dim=5, action_dim=ACTION_DIM, lr=1e-3, gamma=0.99, tau=0.005, batch_size=64, target_update_freq=1, buffer_size=100000, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.995):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.tau = tau
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.q_network = DoubleDQN(state_dim, action_dim).to(self.device)
        self.target_network = DoubleDQN(state_dim, action_dim).to(self.device)
        self.q_net = self.q_network
        self.q_target = self.target_network
        self.update_target_network()
        
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=lr)
        self.criterion = nn.MSELoss()
        
        self.memory = deque(maxlen=buffer_size)
        
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        
    def update_target_network(self):
        self.target_network.load_state_dict(self.q_network.state_dict())
        
    def act(self, state, evaluate=False):
        if not evaluate and random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
            
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        self.q_network.eval()
        with torch.no_grad():
            q_values = self.q_network(state_tensor)
        self.q_network.train()
        return torch.argmax(q_values).item()
        
    def select_action(self, state, evaluate=False):
        return self.act(state, evaluate=evaluate)
        
    def store_transition(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
        
    def train_step(self):
        if len(self.memory) < self.batch_size:
            return 0.0
            
        batch = random.sample(self.memory, self.batch_size)
        states = torch.FloatTensor(np.array([m[0] for m in batch])).to(self.device)
        actions = torch.LongTensor(np.array([m[1] for m in batch])).unsqueeze(1).to(self.device)
        rewards = torch.FloatTensor(np.array([m[2] for m in batch])).unsqueeze(1).to(self.device)
        next_states = torch.FloatTensor(np.array([m[3] for m in batch])).to(self.device)
        dones = torch.FloatTensor(np.array([m[4] for m in batch])).unsqueeze(1).to(self.device)
        
        with torch.no_grad():
            # DDQN target logic: online network selects action, target network evaluates it
            next_actions = self.q_network(next_states).argmax(dim=1, keepdim=True)
            next_q_vals = self.target_network(next_states).gather(1, next_actions)
            target_q = rewards + (1 - dones) * self.gamma * next_q_vals
            
        current_q = self.q_network(states).gather(1, actions)
        
        loss = self.criterion(current_q, target_q)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # Soft update target network if tau > 0
        if self.tau > 0:
            for target_param, param in zip(self.target_network.parameters(), self.q_network.parameters()):
                target_param.data.copy_(target_param.data * (1.0 - self.tau) + param.data * self.tau)
            
        return loss.item()
        
    def update_epsilon(self):
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        
    def save(self, filepath):
        torch.save(self.q_network.state_dict(), filepath)
        
    def load(self, filepath):
        checkpoint = torch.load(filepath, map_location=self.device)
        if isinstance(checkpoint, dict) and "q_net" in checkpoint and not any(k.startswith("network.") for k in checkpoint.keys()):
            self.q_network.load_state_dict(checkpoint["q_net"])
        else:
            self.q_network.load_state_dict(checkpoint)
        self.update_target_network()

