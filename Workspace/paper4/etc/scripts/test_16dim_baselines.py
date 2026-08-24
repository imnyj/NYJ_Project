"""
Verify loading and inference of 16-action baseline models
"""
import os
import sys
import torch
import numpy as np

WORKSPACE = "/home/imnyj/Workspace/paper4"
sys.path.append(os.path.join(WORKSPACE, "code"))
MODELS_DIR = os.path.join(WORKSPACE, "data/models")

sample_state_5d = np.array([0.65, 0.4, 0.15, 0.5, 0.2], dtype=np.float32)

print("=" * 80)
print("TESTING 16-ACTION BASELINE MODELS WITH action_dim=16")
print("=" * 80)

# ActorCritic with action_dim=16
from actor_critic_agent import ActorCriticAgent
ac_agent = ActorCriticAgent(state_dim=5, action_dim=16)
ac_agent.load(os.path.join(MODELS_DIR, "ActorCritic.pth"))
ac_action = ac_agent.select_action(sample_state_5d)
print(f"[PASS] ActorCritic (16-act): Loaded successfully, action={ac_action}")

# MAPPO with action_dim=16
from mappo_agent import MAPPOAgent
mappo_agent = MAPPOAgent(local_state_dim=5, global_state_dim=5, action_dim=16)
mappo_agent.load(os.path.join(MODELS_DIR, "MAPPO.pth"))
mappo_action = mappo_agent.act(sample_state_5d, sample_state_5d, evaluate=True)
print(f"[PASS] MAPPO (16-act): Loaded successfully, action={mappo_action}")

# DecisionTransformer with action_dim=16
from dt_agent import DTAgent
dt_agent = DTAgent(state_dim=5, action_dim=16)
dt_agent.load(os.path.join(MODELS_DIR, "DecisionTransformer.pth"))
dt_action = dt_agent.act(sample_state_5d, evaluate=True)
print(f"[PASS] DecisionTransformer (16-act): Loaded successfully, action={dt_action}")

# TD3 with action_dim=16
from td3_agent import TD3Agent
td3_agent = TD3Agent(state_dim=5, action_dim=16)
td3_agent.load(os.path.join(MODELS_DIR, "TD3.pth"))
td3_action = td3_agent.act(sample_state_5d, evaluate=True)
print(f"[PASS] TD3 (16-act): Loaded successfully, action={td3_action}")

# QLearning with action_dim=16
from qlearning_agent import QLearningAgent
ql_agent = QLearningAgent(state_bins=[10,10,10,10,10], action_dim=16)
ql_agent.load(os.path.join(MODELS_DIR, "QLearning.pkl"))
ql_action = ql_agent.select_action(sample_state_5d, evaluate=True)
print(f"[PASS] QLearning (16-act): Loaded successfully, action={ql_action}")

# SARSA with action_dim=16
from sarsa_agent import SARSAAgent
sarsa_agent = SARSAAgent(state_bins=[10,10,10,10,10], action_dim=16)
sarsa_agent.load(os.path.join(MODELS_DIR, "SARSA.pkl"))
sarsa_action = sarsa_agent.select_action(sample_state_5d, evaluate=True)
print(f"[PASS] SARSA (16-act): Loaded successfully, action={sarsa_action}")

print("\n" + "=" * 80)
print("ALL 16-ACTION BASELINES LOAD AND INFER PERFECTLY!")
print("=" * 80)
