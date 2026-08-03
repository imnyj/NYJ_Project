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
        # Q1
        self.fc1 = nn.Linear(state_dim + action_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 1)
        # Q2
        self.fc4 = nn.Linear(state_dim + action_dim, 128)
        self.fc5 = nn.Linear(128, 64)
        self.fc6 = nn.Linear(64, 1)

    def forward(self, state, action):
        sa = torch.cat([state, action], 1)
        
        q1 = F.relu(self.fc1(sa))
        q1 = F.relu(self.fc2(q1))
        q1 = self.fc3(q1)
        
        q2 = F.relu(self.fc4(sa))
        q2 = F.relu(self.fc5(q2))
        q2 = self.fc6(q2)
        return q1, q2

    def Q1(self, state, action):
        sa = torch.cat([state, action], 1)
        q1 = F.relu(self.fc1(sa))
        q1 = F.relu(self.fc2(q1))
        return self.fc3(q1)

class Actor(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(Actor, self).__init__()
        self.fc1 = nn.Linear(state_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, action_dim)

    def forward(self, state):
        a = F.relu(self.fc1(state))
        a = F.relu(self.fc2(a))
        return self.fc3(a) # logits

class TD3Agent:
    def __init__(self, state_dim, action_dim, lr=1e-3, gamma=0.99, tau=0.005, batch_size=64, buffer_size=100000, policy_delay=2, target_noise=0.2, noise_clip=0.5):
        self.gamma = gamma
        self.tau = tau
        self.batch_size = batch_size
        self.action_dim = action_dim
        self.policy_delay = policy_delay
        self.target_noise = target_noise
        self.noise_clip = noise_clip
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.actor = Actor(state_dim, action_dim).to(self.device)
        self.actor_target = Actor(state_dim, action_dim).to(self.device)
        self.actor_target.load_state_dict(self.actor.state_dict())
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)
        
        self.critic = QNetwork(state_dim, action_dim).to(self.device)
        self.critic_target = QNetwork(state_dim, action_dim).to(self.device)
        self.critic_target.load_state_dict(self.critic.state_dict())
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)
        
        self.memory = deque(maxlen=buffer_size)
        self.it = 0
        
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995

    def act(self, state, evaluate=False):
        if not evaluate and random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
            
        state = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.actor(state)
        return torch.argmax(logits).item()
        
    def store_transition(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
        
    def train_step(self):
        if len(self.memory) < self.batch_size:
            return 0.0, 0.0
            
        self.it += 1
        
        batch = random.sample(self.memory, self.batch_size)
        states = torch.FloatTensor(np.array([m[0] for m in batch])).to(self.device)
        actions = torch.LongTensor(np.array([m[1] for m in batch])).to(self.device)
        rewards = torch.FloatTensor(np.array([m[2] for m in batch])).unsqueeze(1).to(self.device)
        next_states = torch.FloatTensor(np.array([m[3] for m in batch])).to(self.device)
        dones = torch.FloatTensor(np.array([m[4] for m in batch])).unsqueeze(1).to(self.device)
        
        actions_onehot = F.one_hot(actions, num_classes=self.action_dim).float()
        
        with torch.no_grad():
            next_logits = self.actor_target(next_states)
            noise = torch.randn_like(next_logits) * self.target_noise
            noise = noise.clamp(-self.noise_clip, self.noise_clip)
            next_logits = next_logits + noise
            next_actions = F.softmax(next_logits, dim=-1)
            
            target_Q1, target_Q2 = self.critic_target(next_states, next_actions)
            target_Q = rewards + (1 - dones) * self.gamma * torch.min(target_Q1, target_Q2)
            
        current_Q1, current_Q2 = self.critic(states, actions_onehot)
        critic_loss = F.mse_loss(current_Q1, target_Q) + F.mse_loss(current_Q2, target_Q)
        
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()
        
        actor_loss_val = 0.0
        
        if self.it % self.policy_delay == 0:
            logits = self.actor(states)
            soft_actions = F.gumbel_softmax(logits, tau=1.0, hard=True)
            actor_loss = -self.critic.Q1(states, soft_actions).mean()
            
            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            self.actor_optimizer.step()
            
            actor_loss_val = actor_loss.item()
            
            for param, target_param in zip(self.critic.parameters(), self.critic_target.parameters()):
                target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)
                
            for param, target_param in zip(self.actor.parameters(), self.actor_target.parameters()):
                target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        return critic_loss.item(), actor_loss_val

    def save(self, filepath):
        torch.save({
            'actor': self.actor.state_dict(),
            'critic': self.critic.state_dict()
        }, filepath)
        
    def load(self, filepath):
        checkpoint = torch.load(filepath, map_location=self.device)
        self.actor.load_state_dict(checkpoint['actor'])
        self.critic.load_state_dict(checkpoint['critic'])
        self.actor_target.load_state_dict(checkpoint['actor'])
        self.critic_target.load_state_dict(checkpoint['critic'])
