import pickle
import sys

traj_path = r"g:\내 드라이브\개인 자료\YoungjuNam\paper-ai.v1\papers\paper3\paper\data\trajectories\traj_seed42_dur1800.pkl"
try:
    with open(traj_path, 'rb') as f:
        traj = pickle.load(f)
    print('Total steps:', len(traj))
    print('Vehicles at step 0:', len(traj[0]))
    print('First 5 vehicles at step 0:')
    for v in traj[0][:5]:
        print(v)
except Exception as e:
    print(f"Error: {e}")
