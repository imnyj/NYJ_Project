
class MAPPOHook(DuelingDQNHook):
    def __init__(self, agent=None, is_training=False):
        super().__init__(agent, is_training)
        self.current_global_state = np.zeros(5, dtype=np.float32)

    def predict(self, cbr_global: float, n_neighbors: float, v_norm: float, 
                dt_since_last_cam: float, cbr_smoothed: float, vid: str = None):
        local_state = np.array([cbr_global, n_neighbors, v_norm, dt_since_last_cam, cbr_smoothed], dtype=np.float32)
        
        self.current_global_state = 0.9 * self.current_global_state + 0.1 * local_state
        global_state = self.current_global_state.copy()
        
        if self.agent is not None:
            action_idx = self.agent.act(local_state, global_state, evaluate=not self.is_training)
        else:
            action_idx = 0
            
        n_p = len(self.p_tx_grid)
        t_act = self.t_grid[action_idx // n_p]
        p_act = self.p_tx_grid[action_idx % n_p]
        
        if self.is_training and vid is not None:
            if vid in self.prev_states:
                reward = -1.0 * abs(cbr_smoothed - 0.6) - 0.1 * dt_since_last_cam
                self.episode_reward += reward
                done = False
                self.agent.store_transition(
                    self.prev_states[vid]['local'], 
                    self.prev_states[vid]['global'], 
                    self.prev_actions[vid], 
                    reward, 
                    local_state, 
                    global_state, 
                    done
                )
            
            self.prev_states[vid] = {'local': local_state, 'global': global_state}
            self.prev_actions[vid] = action_idx
            
        return t_act, p_act
