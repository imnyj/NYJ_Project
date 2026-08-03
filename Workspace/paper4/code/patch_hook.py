import sys

filename = '/home/imnyj/Workspace/paper4/code/ai_dcc_hook.py'
with open(filename, 'r') as f:
    content = f.read()

content = content.replace('elif method == "PPO":\n            _hooks[method] = PPOHook()', 
                          'elif method == "PPO":\n            _hooks[method] = PPOHook()\n        elif method == "DDPG":\n            _hooks[method] = DDPGHook()')

content += "\nclass DDPGHook(DuelingDQNHook):\n    pass\n"

with open(filename, 'w') as f:
    f.write(content)
