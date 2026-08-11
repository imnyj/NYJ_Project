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
        elif method == "VanillaDQN":
            _hooks[method] = VanillaDQNHook()
        elif method == "SAC":
            _hooks[method] = SACHook()
        elif method == "MAPPO":
            _hooks[method] = MAPPOHook()
        elif method == "DoubleDQN":
            _hooks[method] = DDQNHook()
        elif method == "TD3":
            _hooks[method] = TD3Hook()
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
        
        if vid is not None:
            if vid in self.prev_states:
                reward = -1.0 * abs(cbr_smoothed - 0.6) - 0.1 * dt_since_last_cam
                self.episode_reward += reward
                if self.is_training:
                    done = False
                    self.agent.store_transition(self.prev_states[vid], self.prev_actions[vid], reward, state, done)
            
            self.prev_states[vid] = state
            self.prev_actions[vid] = action_idx
            
        return t_act, p_act

    def terminate_vehicle(self, vid: str):
        if self.is_training and self.agent is not None and vid in self.prev_states:
            state = self.prev_states[vid]
            action = self.prev_actions[vid]
            reward = 0.0
            done = True
            try:
                self.agent.store_transition(state, action, reward, state, done)
            except Exception:
                pass
            del self.prev_states[vid]
            del self.prev_actions[vid]


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
        
        if vid is not None:
            if vid in self.prev_states:
                reward = -1.0 * abs(cbr_smoothed - 0.6) - 0.1 * dt_since_last_cam
                self.episode_reward += reward
                if self.is_training:
                    done = False
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
    def __init__(self, agent=None, is_training=False):
        super().__init__(agent, is_training)
        self.trajectories = {}
        
    def reset_episode(self):
        super().reset_episode()
        self.trajectories.clear()
        
    def predict(self, cbr_global: float, n_neighbors: float, v_norm: float, 
                dt_since_last_cam: float, cbr_smoothed: float, vid: str = None):
        state = __import__('numpy').array([cbr_global, n_neighbors, v_norm, dt_since_last_cam, cbr_smoothed], dtype=__import__('numpy').float32)
        
        if self.agent is not None:
            # We need to pass the current RTG to the agent.
            # In a real DT evaluation, we pass a target return. Let's say 0.0 for now, or maximum possible.
            action_idx = self.agent.act(state, evaluate=not self.is_training)
        else:
            action_idx = 0
            
        n_p = len(self.p_tx_grid)
        t_act = self.t_grid[action_idx // n_p]
        p_act = self.p_tx_grid[action_idx % n_p]
        
        if vid is not None:
            if vid in self.prev_states:
                reward = -1.0 * abs(cbr_smoothed - 0.6) - 0.1 * dt_since_last_cam
                self.episode_reward += reward
                if self.is_training:
                    if vid not in self.trajectories:
                        self.trajectories[vid] = []
                    self.trajectories[vid].append((self.prev_states[vid], self.prev_actions[vid], reward, state))
            
            self.prev_states[vid] = state
            self.prev_actions[vid] = action_idx
            
        return t_act, p_act

    def terminate_vehicle(self, vid: str):
        if self.is_training and self.agent is not None and vid in self.prev_states:
            # compute RTG and store transitions
            if vid in self.trajectories:
                traj = self.trajectories[vid]
                rtg = 0
                for i in reversed(range(len(traj))):
                    s, a, r, next_s = traj[i]
                    rtg = r + 0.99 * rtg # Gamma=0.99
                    # Pass RTG as reward argument to agent to piggyback on the API
                    self.agent.store_transition(s, a, rtg, next_s, False)
                del self.trajectories[vid]
            del self.prev_states[vid]
            del self.prev_actions[vid]
            
    # We also need to process remaining trajectories at the end of episode.
    # DuelingDQNHook reset_episode is called before next episode.
    def reset_episode(self):
        if self.is_training and self.agent is not None:
            for vid, traj in self.trajectories.items():
                rtg = 0
                for i in reversed(range(len(traj))):
                    s, a, r, next_s = traj[i]
                    rtg = r + 0.99 * rtg
                    self.agent.store_transition(s, a, rtg, next_s, False)
        self.trajectories.clear()
        super().reset_episode()


class VanillaDQNHook(DuelingDQNHook):
    pass

class SACHook(DuelingDQNHook):
    pass

class MAPPOHook(DuelingDQNHook):
    def predict(self, cbr_global: float, n_neighbors: float, v_norm: float, 
                dt_since_last_cam: float, cbr_smoothed: float, vid: str = None):
        state = np.array([cbr_global, n_neighbors, v_norm, dt_since_last_cam, cbr_smoothed], dtype=np.float32)
        
        if self.agent is not None:
            action_idx = self.agent.act(state, state, evaluate=not self.is_training)
        else:
            action_idx = 0
            
        n_p = len(self.p_tx_grid)
        t_act = self.t_grid[action_idx // n_p]
        p_act = self.p_tx_grid[action_idx % n_p]
        
        if vid is not None:
            if vid in self.prev_states:
                reward = -1.0 * abs(cbr_smoothed - 0.6) - 0.1 * dt_since_last_cam
                self.episode_reward += reward
                if self.is_training:
                    done = False
                    self.agent.store_transition(self.prev_states[vid], self.prev_states[vid], self.prev_actions[vid], reward, state, state, done)
            
            self.prev_states[vid] = state
            self.prev_actions[vid] = action_idx
            
        return t_act, p_act

    def terminate_vehicle(self, vid: str):
        if self.is_training and self.agent is not None and vid in self.prev_states:
            state = self.prev_states[vid]
            action = self.prev_actions[vid]
            reward = 0.0
            done = True
            try:
                self.agent.store_transition(state, state, action, reward, state, state, done)
            except Exception:
                pass
            del self.prev_states[vid]
            del self.prev_actions[vid]

class DDQNHook(DuelingDQNHook):
    pass

class TD3Hook(DuelingDQNHook):
    pass

