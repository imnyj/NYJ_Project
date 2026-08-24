#!/usr/bin/env python3
"""
train.py
========
CLI entry point for Paper4 model retraining pipeline.
Dispatches to train_all.py.
"""

import sys
import os

_code_dir = os.path.dirname(os.path.abspath(__file__))
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from train_all import main

if __name__ == "__main__":
    main()
