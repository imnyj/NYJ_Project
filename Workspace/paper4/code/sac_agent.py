import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import random
from collections import deque

class QNetwork(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(QNetwork, self).__init__()
        # Q1 architecture
        self.fc1 = nn.Linear(state_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, action_dim)
        
        # Q2 architecture
        self.fc4 = nn.Linear(state_dim, 128)
        self.fc5 = nn.Linear(128, 64)
        self.fc6 = nn.Linear(64, action_dim)

    def forward(self, state):
        x1 = F.relu(self.fc1(state))
        x1 = F.relu(self.fc2(x1))
        q1 = self.fc3(x1)
        
        x2 = F.relu(self.fc4(state))
        x2 = F.relu(self.fc5(x2))
        q2 = self.fc6(x2)
        return q1, q2

class PolicyNetwork(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(PolicyNetwork, self).__init__()
        self.fc1 = nn.Linear(state_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, action_dim)
        
    def forward(self, state):
        x = F.relu(self.fc1(state))
        x = F.relu(self.fc2(x))
        probs = F.softmax(self.fc3(x), dim=-1)
        return probs

class SACAgent:
    def __init__(self, state_dim, action_dim, lr=3e-4, gamma=0.99, tau=0.005, alpha=0.2, batch_size=64, buffer_size=100000):
        self.gamma = gamma
        self.tau = tau
        self.alpha = alpha
        self.batch_size = batch_size
        self.action_dim = action_dim
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.q_net = QNetwork(state_dim, action_dim).to(self.device)
        self.q_target = QNetwork(state_dim, action_dim).to(self.device)
        self.q_target.load_state_dict(self.q_net.state_dict())
        self.q_optimizer = optim.Adam(self.q_net.parameters(), lr=lr)
        
        self.policy = PolicyNetwork(state_dim, action_dim).to(self.device)
        self.policy_optimizer = optim.Adam(self.policy.parameters(), lr=lr)
        
        self.memory = deque(maxlen=buffer_size)
        
    def act(self, state, evaluate=False):
        state = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            probs = self.policy(state)
        
        if evaluate:
            return torch.argmax(probs).item()
            
        dist = torch.distributions.Categorical(probs)
        action = dist.sample()
        return action.item()
        
    def store_transition(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
        
    def train_step(self):
        if len(self.memory) < self.batch_size:
            return 0.0, 0.0
            
        batch = random.sample(self.memory, self.batch_size)
        states = torch.FloatTensor(np.array([m[0] for m in batch])).to(self.device)
        actions = torch.LongTensor(np.array([m[1] for m in batch])).unsqueeze(1).to(self.device)
        rewards = torch.FloatTensor(np.array([m[2] for m in batch])).unsqueeze(1).to(self.device)
        next_states = torch.FloatTensor(np.array([m[3] for m in batch])).to(self.device)
        dones = torch.FloatTensor(np.array([m[4] for m in batch])).unsqueeze(1).to(self.device)
        
        with torch.no_grad():
            next_probs = self.policy(next_states)
            next_dist = torch.distributions.Categorical(next_probs)
            # Soft Q learning target
            next_q1, next_q2 = self.q_target(next_states)
            next_q = next_probs * (torch.min(next_q1, next_q2) - self.alpha * torch.log(next_probs + 1e-8))
            next_q = next_q.sum(dim=1, keepdim=True)
            target_q = rewards + (1 - dones) * self.gamma * next_q
            
        # Update Q functions
        q1, q2 = self.q_net(states)
        q1 = q1.gather(1, actions)
        q2 = q2.gather(1, actions)
        
        q_loss = F.mse_loss(q1, target_q) + F.mse_loss(q2, target_q)
        
        self.q_optimizer.zero_grad()
        q_loss.backward()
        self.q_optimizer.step()
        
        # Update Policy
        probs = self.policy(states)
        q1_pi, q2_pi = self.q_net(states)
        min_q_pi = torch.min(q1_pi, q2_pi)
        
        policy_loss = (probs * (self.alpha * torch.log(probs + 1e-8) - min_q_pi.detach())).sum(dim=1).mean()
        
        self.policy_optimizer.zero_grad()
        policy_loss.backward()
        self.policy_optimizer.step()
        
        # Soft update target network
        for target_param, param in zip(self.q_target.parameters(), self.q_net.parameters()):
            target_param.data.copy_(target_param.data * (1.0 - self.tau) + param.data * self.tau)
            
        return policy_loss.item(), q_loss.item()
        
    def save(self, filepath):
        torch.save({
            'q_net': self.q_net.state_dict(),
            'policy': self.policy.state_dict()
        }, filepath)
        
    def load(self, filepath):
        checkpoint = torch.load(filepath, map_location=self.device)
        self.q_net.load_state_dict(checkpoint['q_net'])
        self.q_target.load_state_dict(checkpoint['q_net'])
        self.policy.load_state_dict(checkpoint['policy'])
