import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

class MAPPO(nn.Module):
    def __init__(self, local_state_dim, global_state_dim, action_dim):
        super(MAPPO, self).__init__()
        # Actor takes local state (decentralized execution)
        self.actor = nn.Sequential(
            nn.Linear(local_state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim),
            nn.Softmax(dim=-1)
        )
        # Critic takes both local and global state (centralized training)
        self.critic = nn.Sequential(
            nn.Linear(local_state_dim + global_state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
        
    def get_policy(self, local_state):
        return self.actor(local_state)
        
    def get_value(self, local_state, global_state):
        return self.critic(torch.cat([local_state, global_state], dim=-1))

class MAPPOAgent:
    def __init__(self, local_state_dim, global_state_dim, action_dim, lr=3e-4, gamma=0.99, eps_clip=0.2, k_epochs=4, batch_size=64, buffer_size=100000):
        self.gamma = gamma
        self.eps_clip = eps_clip
        self.k_epochs = k_epochs
        self.batch_size = batch_size
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.policy = MAPPO(local_state_dim, global_state_dim, action_dim).to(self.device)
        self.policy_old = MAPPO(local_state_dim, global_state_dim, action_dim).to(self.device)
        self.policy_old.load_state_dict(self.policy.state_dict())
        
        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()
        
        self.memory = []
        
    def act(self, local_state, global_state, evaluate=False):
        l_state = torch.FloatTensor(local_state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            policy_dist = self.policy_old.get_policy(l_state)
        
        if evaluate:
            return torch.argmax(policy_dist).item()
            
        dist = torch.distributions.Categorical(policy_dist)
        action = dist.sample()
        return action.item()
        
    def store_transition(self, l_state, g_state, action, reward, next_l_state, next_g_state, done):
        self.memory.append((l_state, g_state, action, reward, next_l_state, next_g_state, done))
        
    def train_step(self):
        if len(self.memory) < self.batch_size:
            return 0.0, 0.0
            
        l_states = torch.FloatTensor(np.array([m[0] for m in self.memory])).to(self.device)
        g_states = torch.FloatTensor(np.array([m[1] for m in self.memory])).to(self.device)
        actions = torch.LongTensor([m[2] for m in self.memory]).to(self.device)
        rewards = torch.FloatTensor([m[3] for m in self.memory]).to(self.device)
        next_l_states = torch.FloatTensor(np.array([m[4] for m in self.memory])).to(self.device)
        next_g_states = torch.FloatTensor(np.array([m[5] for m in self.memory])).to(self.device)
        dones = torch.FloatTensor([m[6] for m in self.memory]).to(self.device)
        
        with torch.no_grad():
            next_values = self.policy_old.get_value(next_l_states, next_g_states).squeeze(-1)
            target_values = rewards + self.gamma * next_values * (1 - dones)
            values = self.policy_old.get_value(l_states, g_states).squeeze(-1)
            advantages = target_values - values
            if advantages.std() > 0:
                advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
            else:
                advantages = advantages - advantages.mean()
            
            dist_old_probs = self.policy_old.get_policy(l_states)
            dist_old = torch.distributions.Categorical(dist_old_probs)
            old_logprobs = dist_old.log_prob(actions)
            
        actor_loss_sum = 0
        critic_loss_sum = 0
            
        for _ in range(self.k_epochs):
            dist_probs = self.policy.get_policy(l_states)
            state_values = self.policy.get_value(l_states, g_states).squeeze(-1)
            dist = torch.distributions.Categorical(dist_probs)
            logprobs = dist.log_prob(actions)
            dist_entropy = dist.entropy()
            
            ratios = torch.exp(logprobs - old_logprobs.detach())
            surr1 = ratios * advantages
            surr2 = torch.clamp(ratios, 1 - self.eps_clip, 1 + self.eps_clip) * advantages
            
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
