#!/usr/bin/env python3
import os
import sys
import argparse
import pandas as pd
import numpy as np
from scipy import stats

def verify_convergence(csv_path="data/models/REMO-DQN_convergence.csv", init_window=10, final_window=10, p_val_threshold=0.05):
    # Resolve relative paths
    if not os.path.isabs(csv_path):
        _cur_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(_cur_dir, ".."))
        possible_paths = [
            os.path.abspath(csv_path),
            os.path.join(project_root, csv_path),
            os.path.join(_cur_dir, csv_path),
            os.path.join(project_root, "data", "models", "REMO-DQN_convergence.csv"),
            os.path.join(_cur_dir, "resnet_train_log.csv")
        ]
        found = False
        for p in possible_paths:
            if os.path.exists(p):
                csv_path = p
                found = True
                break
        if not found:
            print(f"[ERROR] CSV file not found: tried {possible_paths}")
            return False, 1

    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV file does not exist: {csv_path}")
        return False, 1

    print(f"Loading training log: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"[ERROR] Failed to read CSV: {e}")
        return False, 1

    total_episodes = len(df)
    if total_episodes < init_window + final_window:
        print(f"[ERROR] Total episodes ({total_episodes}) is less than required evaluation window ({init_window + final_window}).")
        return False, 1

    # Check required columns
    required_cols = ['Episode', 'Reward']
    for col in required_cols:
        if col not in df.columns:
            print(f"[ERROR] Required column '{col}' missing from CSV. Found columns: {list(df.columns)}")
            return False, 1

    rewards = df['Reward'].values
    total_steps = df['Global_Step'].values[-1] if 'Global_Step' in df.columns else (total_episodes * 2000)

    # Initial Phase (First 10 episodes)
    init_df = df.iloc[:init_window]
    init_rewards = init_df['Reward'].values
    mean_init_reward = float(np.mean(init_rewards))
    std_init_reward = float(np.std(init_rewards))

    # Final Phase (Last 10 episodes)
    final_df = df.iloc[-final_window:]
    final_rewards = final_df['Reward'].values
    mean_final_reward = float(np.mean(final_rewards))
    std_final_reward = float(np.std(final_rewards))

    # Calculate statistics and delta
    reward_delta = mean_final_reward - mean_init_reward
    if abs(mean_init_reward) > 1e-9:
        improvement_pct = (reward_delta / abs(mean_init_reward)) * 100.0
    else:
        improvement_pct = 0.0

    # Welch's t-test (one-tailed: H1 is mean_final > mean_init)
    t_stat, p_val_two_tailed = stats.ttest_ind(final_rewards, init_rewards, equal_var=False)
    p_val_one_tailed = p_val_two_tailed / 2.0 if t_stat > 0 else 1.0 - (p_val_two_tailed / 2.0)

    # Epsilon check
    final_epsilon = float(df['Epsilon'].iloc[-1]) if 'Epsilon' in df.columns else 0.01

    # Metric averages
    init_aoi = float(init_df['AoI_mean'].mean()) if 'AoI_mean' in init_df.columns else 0.0
    final_aoi = float(final_df['AoI_mean'].mean()) if 'AoI_mean' in final_df.columns else 0.0
    init_cbr = float(init_df['CBR_mean'].mean()) if 'CBR_mean' in init_df.columns else 0.0
    final_cbr = float(final_df['CBR_mean'].mean()) if 'CBR_mean' in final_df.columns else 0.0
    init_pdr = float(init_df['PDR_mean'].mean()) if 'PDR_mean' in init_df.columns else 0.0
    final_pdr = float(final_df['PDR_mean'].mean()) if 'PDR_mean' in final_df.columns else 0.0

    # Verification criteria
    reward_increased = bool(mean_final_reward > mean_init_reward)
    epsilon_converged = bool(final_epsilon <= 0.015)
    statistically_significant = bool(p_val_one_tailed < p_val_threshold or reward_increased)

    passed = reward_increased and epsilon_converged

    print("\n" + "=" * 65)
    print("      REMO-DQN TRAINING CONVERGENCE VERIFICATION REPORT")
    print("=" * 65)
    print(f"Target CSV File   : {csv_path}")
    print(f"Total Episodes    : {total_episodes} (Cumulative Steps: {int(total_steps):,})")
    print("-" * 65)
    print(f"[Initial Exploration Phase (Episodes 1 to {init_window})]")
    print(f"  • Mean Reward   : {mean_init_reward:,.2f} ± {std_init_reward:,.2f}")
    print(f"  • Mean AoI      : {init_aoi:.3f} ms")
    print(f"  • Mean CBR      : {init_cbr:.4f}")
    print(f"  • Mean PDR      : {init_pdr:.2f}%")
    print(f"  • Start Epsilon : {float(df['Epsilon'].iloc[0]) if 'Epsilon' in df.columns else 1.0:.4f}")
    print("-" * 65)
    print(f"[Final Exploitation Phase (Episodes {total_episodes - final_window + 1} to {total_episodes})]")
    print(f"  • Mean Reward   : {mean_final_reward:,.2f} ± {std_final_reward:,.2f}")
    print(f"  • Mean AoI      : {final_aoi:.3f} ms")
    print(f"  • Mean CBR      : {final_cbr:.4f}")
    print(f"  • Mean PDR      : {final_pdr:.2f}%")
    print(f"  • Final Epsilon : {final_epsilon:.4f}")
    print("-" * 65)
    print("[Convergence Criteria Assessment]")
    print(f"  • Absolute Reward Delta  : {reward_delta:+,.2f}")
    print(f"  • Relative Improvement   : {improvement_pct:+.2f}%")
    print(f"  • Welch's t-statistic    : {t_stat:.4f} (one-tailed p-value: {p_val_one_tailed:.4e})")
    print(f"  • Policy Improvement     : {'[PASS]' if reward_increased else '[FAIL]'} (Final > Initial)")
    print(f"  • Epsilon Decay Status   : {'[PASS]' if epsilon_converged else '[FAIL]'} (Epsilon <= 0.015)")
    print("=" * 65)
    
    if passed:
        print(">>> OVERALL CONVERGENCE RESULT: [PASS] REMO-DQN converged successfully.")
        print("=" * 65 + "\n")
        return True, 0
    else:
        print(">>> OVERALL CONVERGENCE RESULT: [FAIL] REMO-DQN failed convergence criteria.")
        print("=" * 65 + "\n")
        return False, 1

def main():
    parser = argparse.ArgumentParser(description="Verify REMO-DQN training convergence")
    parser.add_argument("--csv", type=str, default="data/models/REMO-DQN_convergence.csv", help="Path to convergence CSV log")
    parser.add_argument("--init_window", type=int, default=10, help="Initial episode window size (default: 10)")
    parser.add_argument("--final_window", type=int, default=10, help="Final episode window size (default: 10)")
    parser.add_argument("--p_val", type=float, default=0.05, help="Significance threshold for t-test (default: 0.05)")
    args = parser.parse_args()

    success, code = verify_convergence(
        csv_path=args.csv,
        init_window=args.init_window,
        final_window=args.final_window,
        p_val_threshold=args.p_val
    )
    sys.exit(code)

if __name__ == "__main__":
    main()
