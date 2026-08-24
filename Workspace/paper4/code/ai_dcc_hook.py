import os
import pickle
import numpy as np

from etsi_cam_layer import PTX_GRID_DBM, T_GRID_S, ACTION_DIM

# Calibrated CBR Target and Staleness threshold for C-3 reward formulation
# Calibrated via measure_cbr_target.py (empirical CBR knee-point under sim_engine channel model)
CBR_TARGET = 0.075
T_STALE = 0.5  # Staleness threshold in seconds


class TinyMLPHook:
    def __init__(self, model_path="tinymlp_model.pkl"):
        # Resolve path relative to this script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, model_path)
        
        self.t_grid = list(T_GRID_S)
        self.p_tx_grid = list(PTX_GRID_DBM)
        self.action_dim = ACTION_DIM
        
        if os.path.exists(full_path):
            with open(full_path, "rb") as f:
                model_dict = pickle.load(f)
            self.weights = model_dict.get("weights", {})
            self.W1 = self.weights.get("W1")
            self.b1 = self.weights.get("b1")
            self.W2 = self.weights.get("W2")
            self.b2 = self.weights.get("b2")
            self.W3 = self.weights.get("W3")
            self.b3 = self.weights.get("b3")
        else:
            self.weights = {}
            self.W1 = self.b1 = self.W2 = self.b2 = self.W3 = self.b3 = None
            
    def predict(self, cbr_global: float, n_neighbors: float, v_norm: float, 
                dt_since_last_cam: float, cbr_smoothed: float, vid: str = None):
        if self.W1 is not None and self.W2 is not None and self.W3 is not None:
            x = np.array([cbr_global, n_neighbors, v_norm, dt_since_last_cam, cbr_smoothed], dtype=np.float32)
            h1 = np.maximum(0, np.dot(self.W1, x) + self.b1)
            h2 = np.maximum(0, np.dot(self.W2, h1) + self.b2)
            logits = np.dot(self.W3, h2) + self.b3
            action_idx = int(np.argmax(logits))
        else:
            action_idx = 0
            
        n_p = len(self.p_tx_grid)
        t_act = self.t_grid[action_idx // n_p]
        p_act = self.p_tx_grid[action_idx % n_p]
        return t_act, p_act

    def wants_vid(self):
        return False

    def reset_episode(self):
        pass

    def set_agent(self, agent):
        pass

    def terminate_vehicle(self, vid: str = None):
        pass


class SklearnHook:
    def __init__(self, model_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, model_path)
        self.model = None
        if os.path.exists(full_path):
            with open(full_path, "rb") as f:
                self.model = pickle.load(f)
        self.t_grid = list(T_GRID_S)
        self.p_tx_grid = list(PTX_GRID_DBM)
        self.action_dim = ACTION_DIM

    def predict(self, cbr_global: float, n_neighbors: float, v_norm: float, 
                dt_since_last_cam: float, cbr_smoothed: float, vid: str = None):
        if self.model is not None:
            x = np.array([[cbr_global, n_neighbors, v_norm, dt_since_last_cam, cbr_smoothed]], dtype=np.float32)
            action_idx = int(self.model.predict(x)[0])
        else:
            action_idx = 0
        n_p = len(self.p_tx_grid)
        t_act = self.t_grid[action_idx // n_p]
        p_act = self.p_tx_grid[action_idx % n_p]
        return t_act, p_act

    def wants_vid(self):
        return False

    def reset_episode(self):
        pass

    def set_agent(self, agent):
        pass

    def terminate_vehicle(self, vid: str = None):
        pass


class AIDCCHookBase:
    """
    Base DRL Hook for AI-driven Decentralized Congestion Control.
    Implements full vehicle lifecycle, C-3 reward formulation,
    and terminal transition (done=True) storage on vehicle exit.
    """
    def __init__(self, agent=None, is_training=False, reward_variant="Base"):
        self.agent = agent
        self.is_training = is_training
        self.reward_variant = reward_variant
        self.t_grid = list(T_GRID_S)
        self.p_tx_grid = list(PTX_GRID_DBM)
        self.action_dim = ACTION_DIM
        
        # for training/tracking: store previous state, action, cbr, t_gencam per vehicle
        self.prev_states = {}
        self.prev_actions = {}
        self.prev_cbr = {}
        self.prev_t_gencam = {}
        self.episode_reward = 0.0

    @property
    def prev_state(self):
        return self.prev_states

    @property
    def prev_action(self):
        return self.prev_actions
        
    def set_agent(self, agent):
        self.agent = agent

    def wants_vid(self):
        return True
        
    def reset_episode(self):
        self.prev_states.clear()
        self.prev_actions.clear()
        self.prev_cbr.clear()
        self.prev_t_gencam.clear()
        self.episode_reward = 0.0

    def compute_reward(self, cbr_smoothed: float, dt_since_last_cam: float, vid: str = None, t_gencam: float = 0.1, reward_variant: str = None) -> float:
        var = reward_variant if reward_variant is not None else getattr(self, "reward_variant", "Base")
        over = max(0.0, cbr_smoothed - CBR_TARGET)
        osc = abs(cbr_smoothed - self.prev_cbr.get(vid, cbr_smoothed)) if vid is not None else 0.0
        stale = max(0.0, dt_since_last_cam - T_STALE)
        cost = 0.1 / max(t_gencam, 1e-3)
        
        r_cbr = -1.0 * over - 0.5 * osc
        r_aoi = -0.3 * stale
        r_cost = -0.05 * cost
        
        if var in ["wo_R1", "w/o R1", "wo_AoI"]:
            reward = r_cbr + r_cost
        elif var in ["wo_R2", "w/o R2", "wo_CBR"]:
            reward = r_aoi + r_cost
        elif var in ["wo_R3", "w/o R3", "wo_PDR", "wo_Cost"]:
            reward = r_cbr + r_aoi
        else: # "Base", "REMO-DQN", Full Reward
            reward = r_cbr + r_aoi + r_cost
            
        return float(reward)

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
                prev_t = self.prev_t_gencam.get(vid, t_act)
                reward = self.compute_reward(cbr_smoothed, dt_since_last_cam, vid=vid, t_gencam=prev_t)
                self.episode_reward += reward
                if self.is_training and self.agent is not None:
                    done = False
                    self.agent.store_transition(self.prev_states[vid], self.prev_actions[vid], reward, state, done)
            
            self.prev_states[vid] = state
            self.prev_actions[vid] = action_idx
            self.prev_cbr[vid] = cbr_smoothed
            self.prev_t_gencam[vid] = t_act
            
        return t_act, p_act

    def terminate_vehicle(self, vid: str):
        if vid is None:
            return
        if self.is_training and self.agent is not None and vid in self.prev_states:
            state = self.prev_states[vid]
            action = self.prev_actions[vid]
            reward = 0.0
            done = True
            try:
                self.agent.store_transition(state, action, reward, state, done)
            except Exception:
                pass
        self.prev_states.pop(vid, None)
        self.prev_actions.pop(vid, None)
        self.prev_cbr.pop(vid, None)
        self.prev_t_gencam.pop(vid, None)


class DuelingDQNHook(AIDCCHookBase):
    pass


class MoEDQNHook(AIDCCHookBase):
    pass


class ResNetMoEDQNHook(AIDCCHookBase):
    pass


class QLearningHook(AIDCCHookBase):
    pass


class SARSAHook(AIDCCHookBase):
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
                prev_t = self.prev_t_gencam.get(vid, t_act)
                reward = self.compute_reward(cbr_smoothed, dt_since_last_cam, vid=vid, t_gencam=prev_t)
                self.episode_reward += reward
                if self.is_training and self.agent is not None:
                    done = False
                    self.agent.store_transition(self.prev_states[vid], self.prev_actions[vid], reward, state, done, next_action=action_idx)
            
            self.prev_states[vid] = state
            self.prev_actions[vid] = action_idx
            self.prev_cbr[vid] = cbr_smoothed
            self.prev_t_gencam[vid] = t_act
            
        return t_act, p_act

    def terminate_vehicle(self, vid: str):
        if vid is None:
            return
        if self.is_training and self.agent is not None and vid in self.prev_states:
            state = self.prev_states[vid]
            action = self.prev_actions[vid]
            reward = 0.0
            done = True
            try:
                self.agent.store_transition(state, action, reward, state, done, next_action=None)
            except Exception:
                pass
        self.prev_states.pop(vid, None)
        self.prev_actions.pop(vid, None)
        self.prev_cbr.pop(vid, None)
        self.prev_t_gencam.pop(vid, None)


class ActorCriticHook(AIDCCHookBase):
    pass


class PPOHook(AIDCCHookBase):
    pass


class DDPGHook(AIDCCHookBase):
    pass


class DecisionTransformerHook(AIDCCHookBase):
    def __init__(self, agent=None, is_training=False, reward_variant="Base"):
        super().__init__(agent, is_training, reward_variant=reward_variant)
        self.trajectories = {}
        
    def reset_episode(self):
        if self.is_training and self.agent is not None:
            for vid, traj in self.trajectories.items():
                rtg = 0
                for i in reversed(range(len(traj))):
                    s, a, r, next_s = traj[i]
                    rtg = r + 0.99 * rtg
                    done = (i == len(traj) - 1)
                    try:
                        self.agent.store_transition(s, a, rtg, next_s, done)
                    except Exception:
                        pass
        self.trajectories.clear()
        super().reset_episode()
        
    def predict(self, cbr_global: float, n_neighbors: float, v_norm: float, 
                dt_since_last_cam: float, cbr_smoothed: float, vid: str = None):
        state = np.array([cbr_global, n_neighbors, v_norm, dt_since_last_cam, cbr_smoothed], dtype=np.float32)
        
        if self.agent is not None:
            action_idx = self.agent.act(state, evaluate=not self.is_training)
        else:
            action_idx = 0
            
        n_p = len(self.p_tx_grid)
        t_act = self.t_grid[action_idx // n_p]
        p_act = self.p_tx_grid[action_idx % n_p]
        
        if vid is not None:
            if vid in self.prev_states:
                prev_t = self.prev_t_gencam.get(vid, t_act)
                reward = self.compute_reward(cbr_smoothed, dt_since_last_cam, vid=vid, t_gencam=prev_t)
                self.episode_reward += reward
                if self.is_training:
                    if vid not in self.trajectories:
                        self.trajectories[vid] = []
                    self.trajectories[vid].append((self.prev_states[vid], self.prev_actions[vid], reward, state))
            
            self.prev_states[vid] = state
            self.prev_actions[vid] = action_idx
            self.prev_cbr[vid] = cbr_smoothed
            self.prev_t_gencam[vid] = t_act
            
        return t_act, p_act

    def terminate_vehicle(self, vid: str):
        if vid is None:
            return
        if self.is_training and self.agent is not None and vid in self.prev_states:
            traj = self.trajectories.pop(vid, [])
            traj.append((self.prev_states[vid], self.prev_actions[vid], 0.0, self.prev_states[vid]))
            rtg = 0.0
            for i in reversed(range(len(traj))):
                s, a, r, next_s = traj[i]
                rtg = r + 0.99 * rtg
                done = (i == len(traj) - 1)
                try:
                    self.agent.store_transition(s, a, rtg, next_s, done)
                except Exception:
                    pass
        self.trajectories.pop(vid, None)
        self.prev_states.pop(vid, None)
        self.prev_actions.pop(vid, None)
        self.prev_cbr.pop(vid, None)
        self.prev_t_gencam.pop(vid, None)


class VanillaDQNHook(AIDCCHookBase):
    pass


class SACHook(AIDCCHookBase):
    pass


class MAPPOHook(AIDCCHookBase):
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
                prev_t = self.prev_t_gencam.get(vid, t_act)
                reward = self.compute_reward(cbr_smoothed, dt_since_last_cam, vid=vid, t_gencam=prev_t)
                self.episode_reward += reward
                if self.is_training and self.agent is not None:
                    done = False
                    self.agent.store_transition(self.prev_states[vid], self.prev_states[vid], self.prev_actions[vid], reward, state, state, done)
            
            self.prev_states[vid] = state
            self.prev_actions[vid] = action_idx
            self.prev_cbr[vid] = cbr_smoothed
            self.prev_t_gencam[vid] = t_act
            
        return t_act, p_act

    def terminate_vehicle(self, vid: str):
        if vid is None:
            return
        if self.is_training and self.agent is not None and vid in self.prev_states:
            state = self.prev_states[vid]
            action = self.prev_actions[vid]
            reward = 0.0
            done = True
            try:
                self.agent.store_transition(state, state, action, reward, state, state, done)
            except Exception:
                pass
        self.prev_states.pop(vid, None)
        self.prev_actions.pop(vid, None)
        self.prev_cbr.pop(vid, None)
        self.prev_t_gencam.pop(vid, None)


class DDQNHook(AIDCCHookBase):
    pass


# DoubleDQNHook alias for seamless compatibility
DoubleDQNHook = DDQNHook


class TD3Hook(AIDCCHookBase):
    pass


_hooks = {}

def get_hook(method="ResNetMoEDQN"):
    global _hooks
    if method not in _hooks:
        if method in ["Proposed", "ResNetMoEDQN", "REMO-DQN"]:
            _hooks[method] = ResNetMoEDQNHook()
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
        elif method in ["DoubleDQN", "DDQN"]:
            _hooks[method] = DDQNHook()
        elif method == "TD3":
            _hooks[method] = TD3Hook()
        elif method in ["wo_R1", "w/o R1", "wo_R2", "w/o R2", "wo_R3", "w/o R3"]:
            _hooks[method] = ResNetMoEDQNHook(reward_variant=method)
        elif method in ["wo_ResNet", "wo_MoE", "wo_Dueling", "Base",
                        "StateAblation_Base", "StateAblation_wo_Density", "StateAblation_wo_CBR", "StateAblation_wo_Kinematics"]:
            _hooks[method] = ResNetMoEDQNHook()
        else:
            _hooks[method] = ResNetMoEDQNHook()
    return _hooks[method]
