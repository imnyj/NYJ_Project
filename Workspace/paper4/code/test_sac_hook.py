import optuna
import csv
import torch
import numpy as np

from sim_engine import SimulationRunner
from sac_agent import SACAgent
from ai_dcc_hook import get_hook

agent = SACAgent(state_dim=5, action_dim=16, lr=1e-3, gamma=0.99, tau=0.005, alpha=0.2, batch_size=32, buffer_size=10000)
hook = get_hook("SAC")
hook.set_agent(agent)
hook.is_training = True
print("test_sac_hook.py hook id:", id(hook))

runner = SimulationRunner(scenario="urban_grid", n_vehicles=30, seed=42, method="SAC", method_params={}, duration_steps=500)
runner.run()
print("Memory len:", len(agent.memory))
print("Episode reward:", hook.episode_reward)
