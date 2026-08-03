import os

filepath = "/home/imnyj/papers/paper4/sim/tinymlp_train.py"
with open(filepath, "r") as f:
    content = f.read()

# Change hidden_dim default to 4
content = content.replace('p.add_argument("--hidden_dim", type=int,   default=32)', 
                          'p.add_argument("--hidden_dim", type=int,   default=4)')

# Ensure the architecture is 3 layers (it should already be if I messed it up, I'll rewrite it clearly)
old_net = """        if HAS_TORCH:
            self.net = nn.Sequential(
                nn.Linear(in_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, n_classes),
            )"""
new_net = """        if HAS_TORCH:
            self.net = nn.Sequential(
                nn.Linear(in_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, n_classes),
            )"""
content = content.replace(old_net, new_net)

with open(filepath, "w") as f:
    f.write(content)
print("tinymlp_train.py patched.")
