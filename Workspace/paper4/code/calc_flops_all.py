import sys
import torch
sys.path.append('.')
try:
    from thop import profile
except ImportError:
    print("thop not installed")
    sys.exit(0)

# Import models
from dqn_agent import VanillaDQN
from resnet_moe_agent import ResNetMoEDQN
from actor_critic_agent import ActorCritic
from ppo_agent import PPOAgent # wait PPO usually has actor and critic
from dt_agent import DecisionTransformer
from moe_agent import MoEDQN
from tinymlp_train import TinyMLP  # wait, tinymlp_train might not have TinyMLP class easily importable if it runs training on import

