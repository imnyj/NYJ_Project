import re

with open("actor_critic_agent.py", "r") as f:
    content = f.read()

# Replace memory with a simple list, and train_step to use all collected transitions in order
new_code = """
class ActorCriticAgent:
    def __init__(self, state_dim, action_dim, lr=1e-3, gamma=0.99, buffer_size=100000, batch_size=64):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.batch_size = batch_size
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.network = ActorCritic(state_dim, action_dim).to(self.device)
        self.optimizer = optim.Adam(self.network.parameters(), lr=lr)
        
        self.memory = []
        
    def act(self, state, evaluate=False):
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        self.network.eval()
        with torch.no_grad():
            policy_dist, _ = self.network(state_tensor)
        self.network.train()
        
        if evaluate:
            return torch.argmax(policy_dist).item()
        
        m = torch.distributions.Categorical(policy_dist)
        action = m.sample().item()
        return action
        
    def store_transition(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
        
    def train_step(self):
        if len(self.memory) == 0:
            return 0.0, 0.0
            
        states = torch.FloatTensor(np.array([m[0] for m in self.memory])).to(self.device)
        actions = torch.LongTensor([m[1] for m in self.memory]).to(self.device)
        rewards = torch.FloatTensor([m[2] for m in self.memory]).unsqueeze(1).to(self.device)
        next_states = torch.FloatTensor(np.array([m[3] for m in self.memory])).to(self.device)
        dones = torch.FloatTensor([m[4] for m in self.memory]).unsqueeze(1).to(self.device)
        
        # Forward pass
        policy_dist, values = self.network(states)
        with torch.no_grad():
            _, next_values = self.network(next_states)
        
        # Compute advantage
        target_values = rewards + self.gamma * next_values * (1 - dones)
        advantages = target_values - values
        
        # Critic loss
        critic_loss = advantages.pow(2).mean()
        
        # Actor loss
        m = torch.distributions.Categorical(policy_dist)
        log_probs = m.log_prob(actions).unsqueeze(1)
        actor_loss = -(log_probs * advantages.detach()).mean()
        
        loss = actor_loss + critic_loss
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # Clear memory since A2C is on-policy
        self.memory.clear()
        
        return actor_loss.item(), critic_loss.item()
"""

# replace the ActorCriticAgent class
content = re.sub(r'class ActorCriticAgent:.*?(?=    def save)', new_code, content, flags=re.DOTALL)

with open("actor_critic_agent.py", "w") as f:
    f.write(content)
