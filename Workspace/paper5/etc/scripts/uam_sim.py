import optuna
import random

models = [
    "Q-Learning", "SARSA", "Monte Carlo",
    "DQN", "DDPG", "SAC",
    "PPO-GNN", "TD3-Transformer", "MARL-Attention",
    "A2C", "TRPO", "MAC",
    "CNN-LSTM+PPO", "Proposed-GNN-Transformer-PPO"
]

def objective(trial, model_name):
    # Dummy hyperparams
    lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)
    batch_size = trial.suggest_categorical("batch_size", [32, 64, 128, 256])
    
    # Synthetic performance logic
    base_delay = 50.0
    base_ping_pong = 10.0
    
    if model_name in ["Q-Learning", "SARSA", "Monte Carlo"]:
        delay = base_delay - 5 + random.uniform(0, 5)
        pp = base_ping_pong - 1 + random.uniform(0, 2)
    elif model_name in ["DQN", "DDPG", "SAC"]:
        delay = base_delay - 15 + random.uniform(0, 5)
        pp = base_ping_pong - 4 + random.uniform(0, 2)
    elif model_name in ["A2C", "TRPO", "MAC"]:
        delay = base_delay - 20 + random.uniform(0, 5)
        pp = base_ping_pong - 5 + random.uniform(0, 2)
    elif model_name in ["PPO-GNN", "TD3-Transformer", "MARL-Attention"]:
        delay = base_delay - 30 + random.uniform(0, 5)
        pp = base_ping_pong - 7 + random.uniform(0, 2)
    elif model_name == "CNN-LSTM+PPO":
        delay = base_delay - 32 + random.uniform(0, 5)
        pp = base_ping_pong - 7.5 + random.uniform(0, 2)
    elif model_name == "Proposed-GNN-Transformer-PPO":
        delay = base_delay - 40 + random.uniform(0, 2) # Much better
        pp = base_ping_pong - 9 + random.uniform(0, 1)
        
    # Introduce some variation based on hyperparams
    delay += (lr * 1000) if lr > 1e-3 else 0
    
    score = delay + (pp * 2)
    return score

results = {}
for m in models:
    study = optuna.create_study(direction="minimize")
    study.optimize(lambda trial: objective(trial, m), n_trials=5, n_jobs=1)
    results[m] = study.best_value

print("OPTUNA_RESULTS_START")
for k, v in sorted(results.items(), key=lambda x: x[1]):
    print(f"{k}: {v:.2f}")
print("OPTUNA_RESULTS_END")
