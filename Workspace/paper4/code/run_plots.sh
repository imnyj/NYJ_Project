#!/bin/bash
python3 plot_complexity.py
python3 plot_convergence.py
python3 plot_line_density.py
python3 plot_pdr_distance.py
python3 plot_cbr_cdf.py
python3 plot_results.py
cp /home/imnyj/papers/paper4/paper/data/plots/*.png /home/imnyj/.gemini/antigravity-cli/brain/8130db3b-367f-452c-bbe0-02bd3f253a09/
echo "Done generating and copying plots."
