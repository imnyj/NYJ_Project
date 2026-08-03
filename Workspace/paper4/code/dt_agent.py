import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import random
from collections import deque

class DecisionTransformer(nn.Module):
    def __init__(self, state_dim, action_dim, hidden_size=64, num_layers=2):
        super(DecisionTransformer, self).__init__()
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_size = hidden_size
        
        self.state_emb = nn.Linear(state_dim, hidden_size)
        self.action_emb = nn.Linear(action_dim, hidden_size)
        self.rtg_emb = nn.Linear(1, hidden_size)
        
        encoder_layer = nn.TransformerEncoderLayer(d_model=hidden_size, nhead=4, dim_feedforward=hidden_size*4, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.predict_action = nn.Linear(hidden_size, action_dim)
        
    def forward(self, states, actions, rtgs):
        # inputs are (batch_size, seq_len, dim)
        s_emb = self.state_emb(states)
        a_emb = self.action_emb(actions)
        r_emb = self.rtg_emb(rtgs)
        
        # simple sequence: rtg, state, action
        # we'll just sum them for a simple context since we might just use seq_len=1 for online
        seq = s_emb + a_emb + r_emb
        
        out = self.transformer(seq)
        action_preds = self.predict_action(out)
        return action_preds

class DTAgent:
    def __init__(self, state_dim, action_dim, lr=1e-4, gamma=0.99, buffer_size=10000, batch_size=64):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.batch_size = batch_size
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = DecisionTransformer(state_dim, action_dim).to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
        
        self.memory = deque(maxlen=buffer_size)
        
    def act(self, state, evaluate=False):
        # For online interaction, we just pass the current state, dummy action, dummy rtg
        self.model.eval()
        with torch.no_grad():
            s = torch.FloatTensor(state).unsqueeze(0).unsqueeze(0).to(self.device)
            a = torch.zeros(1, 1, self.action_dim).to(self.device)
            r = torch.ones(1, 1, 1).to(self.device)
            
            action_logits = self.model(s, a, r).squeeze(0).squeeze(0)
            action_probs = F.softmax(action_logits, dim=-1).cpu().numpy()
            
        self.model.train()
        if evaluate:
            return np.argmax(action_probs)
            
        # Add exploration
        noise = np.random.normal(0, 0.1, size=self.action_dim)
        action_probs = action_probs + noise
        action_probs = np.clip(action_probs, 0, 1)
        if action_probs.sum() == 0:
            action_probs = np.ones(self.action_dim)
        action_probs /= action_probs.sum()
        
        return np.random.choice(self.action_dim, p=action_probs)
        
    def store_transition(self, state, action, reward, next_state, done):
        action_onehot = np.zeros(self.action_dim)
        action_onehot[action] = 1.0
        self.memory.append((state, action_onehot, reward, next_state, done))
        
    def train_step(self):
        if len(self.memory) < self.batch_size:
            return 0.0
            
        batch = random.sample(self.memory, self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        
        states = torch.FloatTensor(np.array(states)).unsqueeze(1).to(self.device)
        actions = torch.FloatTensor(np.array(actions)).unsqueeze(1).to(self.device)
        rewards = torch.FloatTensor(rewards).unsqueeze(1).unsqueeze(1).to(self.device)
        
        # simple training: predict the action taken given state and reward
        action_preds = self.model(states, actions, rewards)
        
        # target is the actual actions taken
        target_actions = torch.argmax(actions.squeeze(1), dim=-1)
        
        loss = F.cross_entropy(action_preds.squeeze(1), target_actions)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
        
    def save(self, filepath):
        torch.save(self.model.state_dict(), filepath)
        
    def load(self, filepath):
        self.model.load_state_dict(torch.load(filepath, map_location=self.device))
