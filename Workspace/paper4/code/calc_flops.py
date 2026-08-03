import sys
sys.path.append('.')
from dqn_agent import VanillaDQN
from resnet_moe_agent import ResNetMoEDQN
import torch

try:
    from thop import profile
except ImportError:
    print("thop not installed")
    sys.exit(0)

dqn = VanillaDQN(state_dim=15, action_dim=5)
moe = ResNetMoEDQN(state_dim=15, action_dim=5)

dummy_input = torch.randn(1, 15)

macs_dqn, params_dqn = profile(dqn, inputs=(dummy_input, ), verbose=False)
macs_moe, params_moe = profile(moe, inputs=(dummy_input, ), verbose=False)

print(f"DQN - MACs: {macs_dqn}, Params: {params_dqn}")
print(f"MoE - MACs: {macs_moe}, Params: {params_moe}")

def count_active_params(model, input):
    # This is a bit tricky, but for MoE, we can just print the architecture.
    pass

