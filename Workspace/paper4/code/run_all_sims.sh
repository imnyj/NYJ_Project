#!/bin/bash
cd /home/imnyj/Workspace/paper4/code

# Run training scripts
/home/imnyj/venv/bin/python3 train_dqn.py
/home/imnyj/venv/bin/python3 train_moe.py
/home/imnyj/venv/bin/python3 train_actor_critic.py
/home/imnyj/venv/bin/python3 train_resnet.py
/home/imnyj/venv/bin/python3 train_qlearning.py
/home/imnyj/venv/bin/python3 train_sarsa.py
/home/imnyj/venv/bin/python3 train_final.py

# Run simulations
/home/imnyj/venv/bin/python3 sweep_density.py

# Maybe aggregator.py?
/home/imnyj/venv/bin/python3 aggregator.py
