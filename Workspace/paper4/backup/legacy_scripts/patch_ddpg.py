import re

with open("ddpg_agent.py", "r") as f:
    content = f.read()

# Change Actor to return Gumbel-Softmax
actor_code = """    def forward(self, state):
        x = F.relu(self.fc1(state))
        x = F.relu(self.fc2(x))
        logits = self.fc3(x)
        # Always use gumbel_softmax during training, hard=True gives one-hot vectors
        # For evaluation, we can just use argmax, but gumbel_softmax handles it automatically if we set noise properly.
        # It's better to just use gumbel_softmax with hard=True
        return F.gumbel_softmax(logits, tau=1.0, hard=True)"""

content = re.sub(
    r'    def forward\(self, state\):\n        x = F\.relu\(self\.fc1\(state\)\)\n        x = F\.relu\(self\.fc2\(x\)\)\n        x = F\.softmax\(self\.fc3\(x\), dim=-1\)\n        return x',
    actor_code,
    content
)

# In act(), we need to handle Gumbel-Softmax output
# act uses: action_probs = self.actor(state_tensor).cpu().numpy()[0]
# But now self.actor returns a one-hot vector.
# Let's change act to:
act_code = """    def act(self, state, evaluate=False):
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        self.actor.eval()
        with torch.no_grad():
            x = F.relu(self.actor.fc1(state_tensor))
            x = F.relu(self.actor.fc2(x))
            logits = self.actor.fc3(x)
            action_probs = F.softmax(logits, dim=-1).cpu().numpy()[0]
        self.actor.train()
        
        if evaluate:
            return np.argmax(action_probs)
        
        # Add exploration noise
        noise = np.random.normal(0, 0.1, size=self.action_dim)
        action_probs = action_probs + noise
        action_probs = np.clip(action_probs, 0, 1)
        if action_probs.sum() == 0:
            action_probs = np.ones(self.action_dim)
        action_probs /= action_probs.sum()
        
        return np.random.choice(self.action_dim, p=action_probs)"""

content = re.sub(
    r'    def act\(self, state, evaluate=False\):.*?(?=    def store_transition)',
    act_code + '\n        \n',
    content,
    flags=re.DOTALL
)

with open("ddpg_agent.py", "w") as f:
    f.write(content)

