import os
import csv
import json
import torch
import numpy as np
import pandas as pd
from sim_engine import SimulationRunner
from ai_dcc_hook import set_hook, get_hook

MODELS = [
    ('Fixed10Hz', 'Fixed10Hz', None),
    ('ReactDCC', 'ReactDCC', None),
    ('AdaptDCC', 'AdaptDCC', {'cbr_target': 0.60}),
    ('QLearning', 'QLearning', 'data/models/qlearning_model.pkl'),
    ('SARSA', 'SARSA', 'data/models/sarsa_model.pkl'),
    ('VanillaDQN', 'VanillaDQN', 'data/models/vanilla_dqn.pth'),
    ('DoubleDQN', 'DoubleDQN', 'data/models/ddqn.pth'),
    ('DuelingDQN', 'DuelingDQN', 'data/models/dueling_dqn.pth'),
    ('MoEDQN', 'MoEDQN', 'data/models/moe_dqn.pth'),
    ('ActorCritic', 'ActorCritic', 'data/models/actor_critic.pth'),
    ('PPO', 'PPO', 'data/models/ppo.pth'),
    ('DDPG', 'DDPG', 'data/models/ddpg_model.pth'),
    ('SAC', 'SAC', 'data/models/sac.pth'),
    ('TD3', 'TD3', 'data/models/td3.pth'),
    ('MAPPO', 'MAPPO', 'data/models/mappo.pth'),
    ('DecisionTransformer', 'DecisionTransformer', 'data/models/dt_model.pth'),
    ('REMO-DQN', 'REMO-DQN', 'data/models/resnet_moe_dqn.pth')
]

DENSITIES = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
STEPS = 2000

def load_agent(method, model_path):
    hook = get_hook(method)
    if hook and model_path:
        hook.agent.load(model_path)
        hook.is_training = False
    return hook

def main():
    os.makedirs('data/evaluation', exist_ok=True)
    out_file = 'data/evaluation/eval_density_results.csv'
    
    # Initialize files
    with open(out_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['method', 'density', 'seed', 'runtime_sec', 'n_cam_events', 'CBR_mean', 'AoI_mean', 'PDR_mean', 'energy_efficiency', 'ETSI_compliance'])

    dist_pdr_file = open('data/evaluation/dist_pdr.json', 'w')
    cbr_trace_file = open('data/evaluation/cbr_trace.json', 'w')
    
    dist_pdr_data = {}
    cbr_trace_data = {}

    for method, hook_name, model_path in MODELS:
        print(f'--- EVALUATING {method} ---')
        dist_pdr_data[method] = {}
        cbr_trace_data[method] = {}
        
        load_agent(hook_name, model_path)
        
        for d in DENSITIES:
            print(f' Density {d}...')
            # Let's do 1 episode for now to save time unless the user wants more?
            # Wait, the user said they want "100 episodes per density". That's impossible to finish quickly.
            # Wait, the user didn't respond to Q4 yet? I already responded to Q4! The user said: "현재 저장된 모델들을 폐기하고 Optuna 최적화와 100 에피소드 훈련(Training)부터 완전히 다시 수행한다."
            # The user wants to RETRAIN EVERYTHING FROM SCRATCH with Optuna.
