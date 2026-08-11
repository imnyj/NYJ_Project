import re

with open("ai_dcc_hook.py", "r") as f:
    content = f.read()

# We want to add reward_variant to DuelingDQNHook init
content = content.replace("def __init__(self, agent=None, is_training=False):", "def __init__(self, agent=None, is_training=False, reward_variant=\"Base\"):\n        self.reward_variant = reward_variant")

# Add compute_reward method to DuelingDQNHook
compute_reward_method = """
    def compute_reward(self, cbr_smoothed, dt_since_last_cam, n_neighbors):
        R1 = 0.01 * n_neighbors
        R2 = -1.0 * abs(cbr_smoothed - 0.6)
        R3 = -0.1 * dt_since_last_cam
        if getattr(self, "reward_variant", "Base") == "Base":
            return R1 + R2 + R3
        elif self.reward_variant == "wo_R1":
            return R2 + R3
        elif self.reward_variant == "wo_R2":
            return R1 + R3
        elif self.reward_variant == "wo_R3":
            return R1 + R2
        else:
            return R1 + R2 + R3
"""

content = content.replace("def set_agent(self, agent):", compute_reward_method + "\n    def set_agent(self, agent):")

# Replace reward calculation in DuelingDQNHook, SARSAHook, DecisionTransformerHook, MAPPOHook
content = content.replace("reward = -1.0 * abs(cbr_smoothed - 0.6) - 0.1 * dt_since_last_cam", "reward = self.compute_reward(cbr_smoothed, dt_since_last_cam, n_neighbors)")

with open("ai_dcc_hook.py", "w") as f:
    f.write(content)
