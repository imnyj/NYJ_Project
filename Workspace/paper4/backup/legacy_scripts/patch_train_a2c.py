import re

with open("train_actor_critic.py", "r") as f:
    content = f.read()

# Replace the multiple update logic with a single call
# For objective()
content = re.sub(
    r'        num_updates = len\(agent\.memory\) // agent\.batch_size.*?mean_reward \+= hook\.episode_reward',
    '        agent.train_step()\n        mean_reward += hook.episode_reward',
    content,
    flags=re.DOTALL
)

# For train_best_model()
content = re.sub(
    r'        # Train agent\n        actor_losses = \[\]\n        critic_losses = \[\]\n        num_updates = len\(agent\.memory\) // agent\.batch_size\n        if num_updates < 1:\n            num_updates = 1\n            \n        for _ in range\(num_updates\):\n            aloss, closs = agent\.train_step\(\)\n            if aloss != 0\.0 or closs != 0\.0:\n                actor_losses\.append\(aloss\)\n                critic_losses\.append\(closs\)\n            if hasattr\(agent, \'update_epsilon\'\):\n                agent\.update_epsilon\(\)\n                \n        ep_reward = hook\.episode_reward\n        \n        avg_aloss = sum\(actor_losses\)/len\(actor_losses\) if actor_losses else 0\.0\n        avg_closs = sum\(critic_losses\)/len\(critic_losses\) if critic_losses else 0\.0',
    '        # Train agent\n        avg_aloss, avg_closs = agent.train_step()\n        if hasattr(agent, "update_epsilon"):\n            agent.update_epsilon()\n            \n        ep_reward = hook.episode_reward',
    content
)

with open("train_actor_critic.py", "w") as f:
    f.write(content)
