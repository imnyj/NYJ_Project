import time
import os
import csv
import numpy as np
import optuna
from stable_baselines3 import SAC, TD3, PPO
from stable_baselines3.common.callbacks import BaseCallback
import logging

from v2v_env import V2V_Env

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

SUMO_CFG = os.path.abspath("../src/sumo/generated.sumocfg")
MODELS = {"SAC": SAC, "TD3": TD3, "Proposed_PPO": PPO}
TOTAL_TIMESTEPS = 300000

class CSVLoggerCallback(BaseCallback):
    def __init__(self, log_path, verbose=0):
        super().__init__(verbose)
        self.log_path = log_path
        self.episode_success = []
        
    def _on_step(self):
        if self.locals.get("done", False):
            info = self.locals.get("info", {})
            self.episode_success.append(1 if info.get("success", False) else 0)
            
        if self.n_calls % 10000 == 0:
            sr = np.mean(self.episode_success[-100:]) if len(self.episode_success) > 0 else 0
            with open(self.log_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([self.n_calls, sr])
        return True

def evaluate_metrics(model, env, num_episodes=20):
    total_waste, total_delay = 0.0, 0.0
    for _ in range(num_episodes):
        obs, _ = env.reset()
        done = False
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, _, info = env.step(action)
            if done:
                total_waste += info.get("W_curr", 0.0)
                total_delay += info.get("access_delay", 0.0)
    return total_waste / num_episodes, total_delay / num_episodes

def run_hpo(model_name, n_trials=5):
    logger.info(f"=== HPO for {model_name} ===")
    def objective(trial):
        alpha = trial.suggest_float('alpha', 1.0, 30.0)
        beta = trial.suggest_float('beta', 1.0, 30.0)
        gamma = trial.suggest_float('gamma', 1.0, 30.0)
        delta = trial.suggest_float('delta', 1.0, 30.0)
        lr = trial.suggest_float('lr', 1e-4, 5e-3, log=True)
        
        env = V2V_Env(sumo_cfg_file=SUMO_CFG)
        env.alpha, env.beta, env.gamma, env.delta = alpha, beta, gamma, delta
        
        ModelClass = MODELS[model_name]
        if model_name == "Proposed_PPO":
            model = ModelClass("MlpPolicy", env, learning_rate=lr, verbose=0, device="cpu")
        else:
            model = ModelClass("MlpPolicy", env, learning_rate=lr, learning_starts=100, verbose=0, device="cpu")
            
        try:
            model.learn(total_timesteps=3000)
            avg_waste, avg_delay = evaluate_metrics(model, env, num_episodes=10)
        except Exception:
            env.close()
            raise optuna.exceptions.TrialPruned()
        env.close()
        return avg_waste + (avg_delay * 0.5)

    study = optuna.create_study(direction="minimize", study_name=f"hpo_v2v_{model_name}")
    study.optimize(objective, n_trials=n_trials)
    
    with open(f"data/hpo_{model_name}.csv", "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Param", "Value"])
        for k, v in study.best_params.items():
            writer.writerow([k, v])
            
    return study.best_params

def train_model(model_name, best_params, ablation=False):
    suffix = "_ablation" if ablation else ""
    logger.info(f"=== Training {model_name}{suffix} for {TOTAL_TIMESTEPS} steps ===")
    
    env = V2V_Env(sumo_cfg_file=SUMO_CFG, ablation_mode=ablation)
    env.alpha = best_params.get('alpha', 10.0)
    env.beta = best_params.get('beta', 10.0)
    env.gamma = best_params.get('gamma', 10.0)
    env.delta = best_params.get('delta', 10.0)
    
    ModelClass = MODELS[model_name]
    model = ModelClass("MlpPolicy", env, learning_rate=best_params.get('lr', 3e-4), verbose=0)
    
    csv_path = f"data/learning_curve_{model_name}{suffix}.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestep", "Success_Rate"])
        
    callback = CSVLoggerCallback(csv_path)
    start_time = time.time()
    model.learn(total_timesteps=TOTAL_TIMESTEPS, callback=callback)
    end_time = time.time()
    with open(f"data/training_time_{model_name}{suffix}.txt", "w") as f:
        f.write(str(end_time - start_time))
    
    model.save(f"models/{model_name}{suffix}.zip")
    env.close()

def evaluate_density():
    logger.info("=== Evaluating Access Delay vs Density ===")
    densities = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
    
    with open("data/access_delay_vs_density.csv", "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Density", "Model", "Avg_Access_Delay"])
        
        for scale in densities:
            for model_name in MODELS.keys():
                model_path = f"models/{model_name}.zip"
                if not os.path.exists(model_path):
                    continue
                
                env = V2V_Env(sumo_cfg_file=SUMO_CFG, density_scale=scale)
                model = MODELS[model_name].load(model_path, env=env)
                
                _, avg_delay = evaluate_metrics(model, env, num_episodes=15)
                writer.writerow([scale, model_name, avg_delay])
                env.close()

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    
    for name in MODELS.keys():
        best_hps = run_hpo(name, n_trials=5)
        train_model(name, best_hps, ablation=False)
        
    train_model("Proposed_PPO", best_hps, ablation=True)
    evaluate_density()
    
    logger.info("=== All V2V experiments completed. Data saved in data/ directory. ===")
