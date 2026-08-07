import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np
from collections import deque

class ResidualBlock(nn.Module):
    def __init__(self, hidden_dim):
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
    def __init__(self, state_dim, hidden_dim=128, num_blocks=2):
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

class MLPFeatureExtractor(nn.Module):
    def __init__(self, state_dim, hidden_dim=128):
        super(MLPFeatureExtractor, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
    def forward(self, x):
        return self.net(x)

class DuelingExpert(nn.Module):
    def __init__(self, hidden_dim, action_dim):
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

class StandardExpert(nn.Module):
    def __init__(self, hidden_dim, action_dim):
        super(StandardExpert, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim)
        )
        
    def forward(self, x):
        return self.net(x)

# 1. REMO-DQN (ResNet + MoE + Dueling)
class Variant1_REMODQN(nn.Module):
    def __init__(self, state_dim, action_dim, num_experts=3, hidden_dim=128):
        super(Variant1_REMODQN, self).__init__()
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

# 2. w/o ResNet (MLP + MoE + Dueling)
class Variant2_NoResNet(nn.Module):
    def __init__(self, state_dim, action_dim, num_experts=3, hidden_dim=128):
        super(Variant2_NoResNet, self).__init__()
        self.feature_extractor = MLPFeatureExtractor(state_dim, hidden_dim)
        
        self.gating_network = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, num_experts),
            nn.Softmax(dim=-1)
        )
        
        self.experts = nn.ModuleList([DuelingExpert(hidden_dim, action_dim) for _ in range(num_experts)])
        
    def forward(self, state, return_gate_weights=False):
        features = self.feature_extractor(state)
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

# 3. w/o MoE (ResNet + Dueling, no MoE)
class Variant3_NoMoE(nn.Module):
    def __init__(self, state_dim, action_dim, hidden_dim=128):
        super(Variant3_NoMoE, self).__init__()
        self.feature_extractor = ResNetFeatureExtractor(state_dim, hidden_dim, num_blocks=2)
        self.expert = DuelingExpert(hidden_dim, action_dim)
        
    def forward(self, state, return_gate_weights=False):
        features = self.feature_extractor(state)
        q_vals = self.expert(features)
        
        if return_gate_weights:
            # Return dummy weights if requested, to keep API compatible
            batch_size = state.size(0)
            dummy_weights = torch.ones(batch_size, 1, device=state.device)
            return q_vals, dummy_weights
        return q_vals

# 4. w/o Dueling (ResNet + MoE + Standard DQN output)
class Variant4_NoDueling(nn.Module):
    def __init__(self, state_dim, action_dim, num_experts=3, hidden_dim=128):
        super(Variant4_NoDueling, self).__init__()
        self.feature_extractor = ResNetFeatureExtractor(state_dim, hidden_dim, num_blocks=2)
        
        self.gating_network = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, num_experts),
            nn.Softmax(dim=-1)
        )
        
        self.experts = nn.ModuleList([StandardExpert(hidden_dim, action_dim) for _ in range(num_experts)])
        
    def forward(self, state, return_gate_weights=False):
        features = self.feature_extractor(state)
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


class AblationAgent:
    def __init__(self, variant_type, state_dim, action_dim, num_experts=3, hidden_dim=128, lr=1e-3, gamma=0.99, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.995, buffer_size=100000, batch_size=64):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.variant_type = variant_type
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        if variant_type == 1:
            self.q_network = Variant1_REMODQN(state_dim, action_dim, num_experts, hidden_dim).to(self.device)
            self.target_network = Variant1_REMODQN(state_dim, action_dim, num_experts, hidden_dim).to(self.device)
        elif variant_type == 2:
            self.q_network = Variant2_NoResNet(state_dim, action_dim, num_experts, hidden_dim).to(self.device)
            self.target_network = Variant2_NoResNet(state_dim, action_dim, num_experts, hidden_dim).to(self.device)
        elif variant_type == 3:
            self.q_network = Variant3_NoMoE(state_dim, action_dim, hidden_dim).to(self.device)
            self.target_network = Variant3_NoMoE(state_dim, action_dim, hidden_dim).to(self.device)
        elif variant_type == 4:
            self.q_network = Variant4_NoDueling(state_dim, action_dim, num_experts, hidden_dim).to(self.device)
            self.target_network = Variant4_NoDueling(state_dim, action_dim, num_experts, hidden_dim).to(self.device)
        else:
            raise ValueError("variant_type must be 1, 2, 3, or 4")
            
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
            if isinstance(q_vals, tuple):
                q_vals = q_vals[0]
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
        
        out = self.q_network(states, return_gate_weights=True)
        if isinstance(out, tuple):
            q_vals_all, gate_weights = out
        else:
            q_vals_all = out
            gate_weights = None

        q_vals = q_vals_all.gather(1, actions)
        
        with torch.no_grad():
            next_out = self.q_network(next_states)
            if isinstance(next_out, tuple):
                next_out = next_out[0]
            next_actions = next_out.argmax(dim=1, keepdim=True)
            
            target_next_out = self.target_network(next_states)
            if isinstance(target_next_out, tuple):
                target_next_out = target_next_out[0]
            next_q_vals = target_next_out.gather(1, next_actions)
            
            target_q_vals = rewards + self.gamma * next_q_vals * (1 - dones)
            
        loss = self.criterion(q_vals, target_q_vals)
        
        lb_loss = 0.0
        if self.variant_type != 3 and gate_weights is not None:
            importance = gate_weights.mean(dim=0)
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
