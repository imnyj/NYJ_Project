import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

class PPO(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(PPO, self).__init__()
        self.actor = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim),
            nn.Softmax(dim=-1)
        )
        self.critic = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
        
    def forward(self, state):
        policy_dist = self.actor(state)
        value = self.critic(state)
        return policy_dist, value

class PPOAgent:
    def __init__(self, state_dim, action_dim, lr=3e-4, gamma=0.99, eps_clip=0.2, k_epochs=4, batch_size=64, buffer_size=100000):
        self.gamma = gamma
        self.eps_clip = eps_clip
        self.k_epochs = k_epochs
        self.batch_size = batch_size
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.policy = PPO(state_dim, action_dim).to(self.device)
        self.policy_old = PPO(state_dim, action_dim).to(self.device)
        self.policy_old.load_state_dict(self.policy.state_dict())
        
        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()
        
        self.memory = []
        
    def act(self, state, evaluate=False):
        state = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            policy_dist, _ = self.policy_old(state)
        
        if evaluate:
            return torch.argmax(policy_dist).item()
            
        dist = torch.distributions.Categorical(policy_dist)
        action = dist.sample()
        return action.item()
        
    def store_transition(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
        
    def train_step(self):
        if len(self.memory) < self.batch_size:
            return 0.0, 0.0
            
        # Batch generation logic can be improved for large memories, 
        # but for simple PPO we can train on all gathered transitions.
        states = torch.FloatTensor(np.array([m[0] for m in self.memory])).to(self.device)
        actions = torch.LongTensor([m[1] for m in self.memory]).to(self.device)
        rewards = torch.FloatTensor([m[2] for m in self.memory]).to(self.device)
        next_states = torch.FloatTensor(np.array([m[3] for m in self.memory])).to(self.device)
        dones = torch.FloatTensor([m[4] for m in self.memory]).to(self.device)
        
        with torch.no_grad():
            _, next_values = self.policy_old(next_states)
            target_values = rewards.unsqueeze(1) + self.gamma * next_values * (1 - dones.unsqueeze(1))
            _, values = self.policy_old(states)
            advantages = target_values - values
            # Normalize advantages
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
            
            dist_old, _ = self.policy_old(states)
            dist_old = torch.distributions.Categorical(dist_old)
            old_logprobs = dist_old.log_prob(actions)
            
        actor_loss_sum = 0
        critic_loss_sum = 0
            
        for _ in range(self.k_epochs):
            dist, state_values = self.policy(states)
            dist = torch.distributions.Categorical(dist)
            logprobs = dist.log_prob(actions)
            dist_entropy = dist.entropy()
            
            ratios = torch.exp(logprobs - old_logprobs.detach())
            surr1 = ratios * advantages.squeeze()
            surr2 = torch.clamp(ratios, 1 - self.eps_clip, 1 + self.eps_clip) * advantages.squeeze()
            
            actor_loss = -torch.min(surr1, surr2).mean()
            critic_loss = self.loss_fn(state_values, target_values.detach())
            
            loss = actor_loss + 0.5 * critic_loss - 0.01 * dist_entropy.mean()
            
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            actor_loss_sum += actor_loss.item()
            critic_loss_sum += critic_loss.item()
            
        self.policy_old.load_state_dict(self.policy.state_dict())
        self.memory.clear()
        
        return actor_loss_sum / self.k_epochs, critic_loss_sum / self.k_epochs
        
    def save(self, filepath):
        torch.save(self.policy.state_dict(), filepath)
        
    def load(self, filepath):
        self.policy.load_state_dict(torch.load(filepath, map_location=self.device))
        self.policy_old.load_state_dict(self.policy.state_dict())
