import re

with open("ai_dcc_hook.py", "r") as f:
    content = f.read()

# Replace DecisionTransformerHook definition
new_dt_hook = """class DecisionTransformerHook(DuelingDQNHook):
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
        
        if self.is_training and vid is not None:
            if vid in self.prev_states:
                reward = -1.0 * abs(cbr_smoothed - 0.6) - 0.1 * dt_since_last_cam
                self.episode_reward += reward
                
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
"""

content = re.sub(
    r'class DecisionTransformerHook\(DuelingDQNHook\):\n    pass',
    new_dt_hook,
    content
)

with open("ai_dcc_hook.py", "w") as f:
    f.write(content)
