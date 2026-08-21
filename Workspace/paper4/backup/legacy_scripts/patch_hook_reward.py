with open("ai_dcc_hook.py", "r") as f:
    content = f.read()

# For DuelingDQNHook and others
# Original:
#         if self.is_training and vid is not None:
#             if vid in self.prev_states:
#                 reward = self.compute_reward(cbr_smoothed, dt_since_last_cam, n_neighbors)
#                 self.episode_reward += reward
#                 done = False
#                 self.agent.store_transition(self.prev_states[vid], self.prev_actions[vid], reward, state, done)
#             
#             self.prev_states[vid] = state
#             self.prev_actions[vid] = action_idx

# We will just remove "self.is_training and " in all those four occurrences
# and wrap store_transition inside an if self.is_training:

content = content.replace("if self.is_training and vid is not None:", "if vid is not None:")

# DuelingDQNHook (and VanillaDQN, SAC, etc.)
content = content.replace(
"""                self.episode_reward += reward
                done = False
                self.agent.store_transition(self.prev_states[vid], self.prev_actions[vid], reward, state, done)""",
"""                self.episode_reward += reward
                if self.is_training:
                    done = False
                    self.agent.store_transition(self.prev_states[vid], self.prev_actions[vid], reward, state, done)""")

# SARSAHook
content = content.replace(
"""                self.episode_reward += reward
                done = False
                # Passing next_action to store_transition for SARSA
                self.agent.store_transition(self.prev_states[vid], self.prev_actions[vid], reward, state, done, next_action=action_idx)""",
"""                self.episode_reward += reward
                if self.is_training:
                    done = False
                    self.agent.store_transition(self.prev_states[vid], self.prev_actions[vid], reward, state, done, next_action=action_idx)""")

# DecisionTransformerHook
content = content.replace(
"""                self.episode_reward += reward
                
                if vid not in self.trajectories:
                    self.trajectories[vid] = []
                self.trajectories[vid].append((self.prev_states[vid], self.prev_actions[vid], reward, state))""",
"""                self.episode_reward += reward
                if self.is_training:
                    if vid not in self.trajectories:
                        self.trajectories[vid] = []
                    self.trajectories[vid].append((self.prev_states[vid], self.prev_actions[vid], reward, state))""")

# MAPPOHook
content = content.replace(
"""                self.episode_reward += reward
                done = False
                self.agent.store_transition(self.prev_states[vid], self.prev_states[vid], self.prev_actions[vid], reward, state, state, done)""",
"""                self.episode_reward += reward
                if self.is_training:
                    done = False
                    self.agent.store_transition(self.prev_states[vid], self.prev_states[vid], self.prev_actions[vid], reward, state, state, done)""")

with open("ai_dcc_hook.py", "w") as f:
    f.write(content)
print("Patch applied.")
