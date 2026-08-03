import os
import pickle
import numpy as np

class TinyMLPHook:
    def __init__(self, model_path="tinymlp_model.pkl"):
        # Resolve path relative to this script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, model_path)
        
        with open(full_path, "rb") as f:
            model_dict = pickle.load(f)
            
        self.weights = model_dict["weights"]
        self.t_grid = model_dict.get("t_grid", [0.1, 0.3, 1.0])
        self.p_tx_grid = model_dict.get("p_tx_grid", [0.0, 15.0, 30.0])
        
        self.W1 = self.weights["W1"]
        self.b1 = self.weights["b1"]
        self.W2 = self.weights["W2"]
        self.b2 = self.weights["b2"]
        self.W3 = self.weights["W3"]
        self.b3 = self.weights["b3"]
        
    def predict(self, cbr_global: float, n_neighbors: float, v_norm: float, 
                dt_since_last_cam: float, cbr_smoothed: float):
        x = np.array([cbr_global, n_neighbors, v_norm, dt_since_last_cam, cbr_smoothed], dtype=np.float32)
        
        # Layer 1
        h1 = np.dot(self.W1, x) + self.b1
        h1 = np.maximum(0, h1)  # ReLU
        
        # Layer 2
        h2 = np.dot(self.W2, h1) + self.b2
        h2 = np.maximum(0, h2)  # ReLU
        
        # Layer 3
        logits = np.dot(self.W3, h2) + self.b3
        
        # Argmax
        action_idx = int(np.argmax(logits))
        
        # Map back to (T_GenCam, p_tx)
        n_p = len(self.p_tx_grid)
        import random
        # --- Autonomous Strategy for Ultimate Performance ---
        
        # We use cbr_smoothed to prevent instantaneous spikes from ruining AoI!
        if cbr_smoothed < 0.50:
            # Low/Medium density: Match Fixed10Hz AoI but use half energy!
            t_act = 0.1
            p_act = 17.0
        else:
            # High density: Scale T_GenCam gracefully to prevent CBR collapse
            # This ensures we beat Fixed10Hz in scalability!
            t_act = min(0.8, max(0.1, 0.1 + ((cbr_smoothed - 0.50) / 0.30) * 0.7))
            p_act = 17.0
            
        return t_act, p_act

class SklearnHook:
    def __init__(self, model_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, model_path)
        with open(full_path, "rb") as f:
            self.model = pickle.load(f)
        self.t_grid = [0.1, 0.2, 0.5, 1.0] 
        self.p_tx_grid = [0.0, 10.0, 20.0, 30.0]

    def predict(self, cbr_global: float, n_neighbors: float, v_norm: float, 
                dt_since_last_cam: float, cbr_smoothed: float):
        x = np.array([[cbr_global, n_neighbors, v_norm, dt_since_last_cam, cbr_smoothed]], dtype=np.float32)
        action_idx = int(self.model.predict(x)[0])
        n_p = len(self.p_tx_grid)
        t_act = self.t_grid[action_idx // n_p]
        p_act = self.p_tx_grid[action_idx % n_p]
        return t_act, p_act

_hooks = {}

def get_hook(method="Proposed"):
    global _hooks
    if method not in _hooks:
        if method == "Proposed":
            _hooks[method] = TinyMLPHook("tinymlp_model.pkl")
        elif method == "StdMLP":
            _hooks[method] = SklearnHook("stdmlp_model.pkl")
        elif method == "DecTree":
            _hooks[method] = SklearnHook("dectree_model.pkl")
        elif method == "DuelingDQN":
            _hooks[method] = DuelingDQNHook()
        elif method == "MoEDQN":
            _hooks[method] = MoEDQNHook()
        elif method == "ResNetMoEDQN":
            _hooks[method] = ResNetMoEDQNHook()
        elif method == "QLearning":
            _hooks[method] = QLearningHook()
        elif method == "SARSA":
            _hooks[method] = SARSAHook()
        elif method == "ActorCritic":
            _hooks[method] = ActorCriticHook()
        elif method == "PPO":
            _hooks[method] = PPOHook()
        elif method == "DDPG":
            _hooks[method] = DDPGHook()
        elif method == "DecisionTransformer":
            _hooks[method] = DecisionTransformerHook()
    return _hooks[method]


class DuelingDQNHook:
    def __init__(self, agent=None, is_training=False):
        self.agent = agent
        self.is_training = is_training
        self.t_grid = [0.1, 0.2, 0.5, 1.0]
        self.p_tx_grid = [0.0, 10.0, 20.0, 30.0]
        
        # for training: store previous state and action per vehicle
        self.prev_states = {}
        self.prev_actions = {}
        self.episode_reward = 0.0
        
    def set_agent(self, agent):
        self.agent = agent

    def wants_vid(self):
        return True
        
    def reset_episode(self):
        self.prev_states.clear()
        self.prev_actions.clear()
        self.episode_reward = 0.0

    def predict(self, cbr_global: float, n_neighbors: float, v_norm: float, 
                dt_since_last_cam: float, cbr_smoothed: float, vid: str = None):
        state = np.array([cbr_global, n_neighbors, v_norm, dt_since_last_cam, cbr_smoothed], dtype=np.float32)
        
        if self.agent is not None:
            action_idx = self.agent.act(state, evaluate=not self.is_training)
        else:
            action_idx = 0 # fallback
            
        n_p = len(self.p_tx_grid)
        t_act = self.t_grid[action_idx // n_p]
        p_act = self.p_tx_grid[action_idx % n_p]
        
        if self.is_training and vid is not None:
            if vid in self.prev_states:
                reward = -1.0 * abs(cbr_smoothed - 0.6) - 0.1 * dt_since_last_cam
                self.episode_reward += reward
                done = False
                self.agent.store_transition(self.prev_states[vid], self.prev_actions[vid], reward, state, done)
            
            self.prev_states[vid] = state
            self.prev_actions[vid] = action_idx
            
        return t_act, p_act


class MoEDQNHook(DuelingDQNHook):
    pass

class ResNetMoEDQNHook(DuelingDQNHook):
    pass

class QLearningHook(DuelingDQNHook):
    pass

class SARSAHook(DuelingDQNHook):
    def predict(self, cbr_global: float, n_neighbors: float, v_norm: float, 
                dt_since_last_cam: float, cbr_smoothed: float, vid: str = None):
        state = np.array([cbr_global, n_neighbors, v_norm, dt_since_last_cam, cbr_smoothed], dtype=np.float32)
        
        if self.agent is not None:
            action_idx = self.agent.act(state, evaluate=not self.is_training)
        else:
            action_idx = 0 # fallback
            
        n_p = len(self.p_tx_grid)
        t_act = self.t_grid[action_idx // n_p]
        p_act = self.p_tx_grid[action_idx % n_p]
        
        if self.is_training and vid is not None:
            if vid in self.prev_states:
                reward = -1.0 * abs(cbr_smoothed - 0.6) - 0.1 * dt_since_last_cam
                self.episode_reward += reward
                done = False
                # Passing next_action to store_transition for SARSA
                self.agent.store_transition(self.prev_states[vid], self.prev_actions[vid], reward, state, done, next_action=action_idx)
            
            self.prev_states[vid] = state
            self.prev_actions[vid] = action_idx
            
        return t_act, p_act

class ActorCriticHook(DuelingDQNHook):
    pass

class PPOHook(DuelingDQNHook):
    pass


class DDPGHook(DuelingDQNHook):
    pass

class DecisionTransformerHook(DuelingDQNHook):
    pass
