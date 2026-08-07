#!/bin/bash
mkdir -p logs
echo "Batch 1"
python train_qlearning.py > logs/qlearning.out 2>&1 &
python train_sarsa.py > logs/sarsa.out 2>&1 &
python train_actor_critic.py > logs/actor_critic.out 2>&1 &
python train_dqn.py > logs/dqn.out 2>&1 &
wait

echo "Batch 2"
python optuna_ppo.py > logs/ppo.out 2>&1 &
python optuna_ddpg.py > logs/ddpg.out 2>&1 &
python optuna_ddqn.py > logs/ddqn.out 2>&1 &
python optuna_td3.py > logs/td3.out 2>&1 &
wait

echo "Batch 3"
python optuna_dt.py > logs/dt.out 2>&1 &
python optuna_sac.py > logs/sac.out 2>&1 &
python optuna_mappo.py > logs/mappo.out 2>&1 &
python train_moe.py > logs/moe.out 2>&1 &
wait

echo "Batch 4"
python train_resnet.py > logs/resnet.out 2>&1
wait

echo "ALL TRAINING DONE"
python plot_all_convergence.py
