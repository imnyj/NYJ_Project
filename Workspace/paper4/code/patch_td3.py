import re

with open("td3_agent.py", "r") as f:
    content = f.read()

content = content.replace(
    "next_actions = F.softmax(next_logits, dim=-1)",
    "next_actions = F.gumbel_softmax(next_logits, tau=1.0, hard=True)"
)

with open("td3_agent.py", "w") as f:
    f.write(content)
