#!/bin/bash
echo "Starting Global Pre-training..."
/home/imnyj/venv/bin/python train_global.py | tee train_global.log

echo "Starting ML Baselines evaluation..."
/home/imnyj/venv/bin/python train_ml_baselines.py | tee train_ml_baselines.log

echo "Starting Local Ping-Pong Fine-tuning simulation..."
/home/imnyj/venv/bin/python train_local_pingpong.py | tee train_local_pingpong.log

echo "All tasks completed!"
