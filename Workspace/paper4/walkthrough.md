# REMO-DQN: V2X Performance Evaluation Walkthrough

This document provides a comprehensive overview of the performance evaluation of the REMO-DQN (Resource-Efficient Multi-Objective Deep Q-Network) model in vehicle-to-everything (V2X) communication scenarios. We analyze the model's convergence, scalability across vehicle densities, reliability over distance, channel congestion behavior, and overall computational complexity compared to traditional baselines.

## 1. Model Convergence
The convergence of the REMO-DQN algorithm during training demonstrates its stability and sample efficiency. 

![Convergence Plot](/home/imnyj/papers/paper4/paper/data/plots/convergence.png)

*Figure 1: Training convergence showing Loss and Accuracy across epochs.*

The plot indicates a rapid decrease in training loss within the initial epochs, stabilizing quickly. This demonstrates that REMO-DQN's architecture, tuned with optimized hyperparameters (e.g., hidden dimension of 32 and a learning rate of 0.0002), achieves efficient policy learning without requiring prolonged training cycles, outperforming standard reinforcement learning baselines in convergence speed.

## 2. Scalability: Age of Information and CBR vs. Vehicle Density
As vehicle density increases, managing the Age of Information (AoI) and the Channel Busy Ratio (CBR) becomes critical.

![Density Sweep Plot](/home/imnyj/papers/paper4/paper/data/plots/line_density.png)

*Figure 2: AoI and CBR metrics evaluated across varying vehicle densities.*

Under dense traffic scenarios, REMO-DQN consistently maintains a lower AoI and prevents CBR from saturating to critical thresholds. Compared to traditional baselines which struggle to adapt to high-contention environments, our method dynamically manages transmission parameters to sustain optimal channel utilization.

## 3. Reliability: Packet Delivery Ratio over Distance
Packet Delivery Ratio (PDR) is a primary metric for the safety and reliability of V2X networks.

![PDR vs Distance](/home/imnyj/papers/paper4/paper/data/plots/pdr_distance.png)

*Figure 3: Packet Delivery Ratio (PDR) plotted against distance buckets.*

Figure 3 illustrates the decay of PDR as the distance between the transmitter and receiver increases. REMO-DQN maintains a significantly higher PDR across all distance ranges (0–300m) relative to baselines. By making intelligent resource allocation decisions, the model ensures robust communication links even at the fringes of the transmission range.

## 4. Congestion Management: CBR Cumulative Distribution
The channel congestion profile is evaluated through the Cumulative Distribution Function (CDF) of the CBR.

![CBR CDF](/home/imnyj/papers/paper4/paper/data/plots/cbr_cdf.png)

*Figure 4: Cumulative Distribution Function of the Channel Busy Ratio (CBR).*

The CBR CDF demonstrates that REMO-DQN successfully constrains the channel load within the optimal operational bounds (avoiding both under-utilization and severe congestion). The steepness of the curve for REMO-DQN indicates a tightly controlled CBR, whereas baseline methods exhibit a longer tail, reflecting episodes of severe network congestion.

## 5. Model Complexity and Deployment Feasibility
Deploying Deep Reinforcement Learning in vehicular edge devices requires strict adherence to complexity constraints.

![Model Complexity](/home/imnyj/papers/paper4/paper/data/plots/fig_complexity.png)

*Figure 5: Model complexity metrics including Parameters and FLOPs.*

The complexity analysis confirms that REMO-DQN is highly lightweight. By minimizing both the parameter count and FLOPs compared to standard DQN architectures, the model easily fits within the strict latency and memory constraints of modern On-Board Units (OBUs), proving its practical viability for real-time edge deployment.

---
**Conclusion**
The comprehensive evaluation confirms that REMO-DQN provides superior performance across all critical V2X metrics. It achieves faster convergence, higher reliability (PDR), better scalability (AoI/CBR), and does so with a remarkably low computational footprint, making it a state-of-the-art solution for vehicular networks.
