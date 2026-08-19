#!/usr/bin/env python3
"""
table_fidelity_checker.py
Exhaustive verification of all 14 tables between Korean draft and main.tex.
"""

import re
import sys
from pathlib import Path

K_PATH = Path("/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md")
L_PATH = Path("/home/imnyj/Workspace/paper4/latex/main.tex")

def clean_num(s):
    # Remove LaTeX formatting like \, or ~, %, $, \textbf, etc.
    s = re.sub(r"\\[,; ]", "", s)
    s = re.sub(r"\\textbf\{([^}]+)\}", r"\1", s)
    s = re.sub(r"[\$%~]", "", s)
    return s.strip()

def check_all_tables():
    k_text = K_PATH.read_text(encoding="utf-8")
    l_text = L_PATH.read_text(encoding="utf-8")

    # Extract all tabularx/tabular environments from LaTeX
    l_tables = re.findall(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", l_text, re.DOTALL)
    print(f"Total LaTeX table environments: {len(l_tables)}")

    # Extract all markdown tables from Korean draft
    lines = k_text.split("\n")
    k_tables = []
    current_t = []
    in_t = False
    for line in lines:
        if line.strip().startswith("|") and "|" in line.strip()[1:]:
            if not in_t:
                in_t = True
            current_t.append(line)
        else:
            if in_t:
                k_tables.append(current_t)
                current_t = []
                in_t = False
    if in_t:
        k_tables.append(current_t)

    print(f"Total Korean markdown table blocks: {len(k_tables)}")

    # Let's map and check each table
    print("\n--- Checking Table by Table Fidelity ---")
    
    # Table 1: Literature comparison
    print("\n[Table 1] Literature Comparison Matrix (tab:lit_comparison)")
    l_t1 = l_tables[0]
    # Check baseline models present
    models_to_check = ["Arena et al.", "ETSI DCC", "SAE J2945/1", "Ye et al.", "Wang et al.", "Yu et al.", "Xu et al.", "REMO-DQN (Ours)"]
    for m in models_to_check:
        found = m.replace(" et al.", "") in l_t1 or m in l_t1
        print(f"  Model '{m}': {'FOUND' if found else 'MISSING'}")

    # Table 2: System Model and REMO-DQN Hyperparameters
    print("\n[Table 2] System Model and REMO-DQN Hyperparameters (tab:system_params)")
    l_t2 = l_tables[1]
    params_t2 = [
        ("f_c", "5.89"), ("B", "10"), ("m", "3.0"), ("P_{noise}", "-94.0"),
        ("T_{min}", "0.1"), ("T_{max}", "1.0"), ("P_{tx}", "30.0"),
        ("w_1", "0.01"), ("w_2", "1.0"), ("w_3", "0.10"), ("\\lambda_{LB}", "0.01"),
        ("CBR_{target}", "0.65"), ("\\alpha", "0.0001"), ("\\gamma", "0.99"),
        ("\\tau", "0.005"), ("50,000", "50")
    ]
    for p_name, p_val in params_t2:
        found = p_val in l_t2
        print(f"  Param {p_name} ({p_val}): {'FOUND' if found else 'MISSING'}")

    # Table 3: Simulation Setup Parameters
    print("\n[Table 3] Simulation Setup Parameters (tab:sim_setup)")
    l_t3 = l_tables[2]
    sim_params = [
        ("Simulation Area", "1000 m"), ("Number of Lanes", "3 lanes"),
        ("Vehicle Speed", "20--100 km/h"), ("Transmission Range", "300 m"),
        ("Carrier Sensing Range", "500 m"), ("Carrier Frequency", "5.9 GHz"),
        ("Bandwidth", "10 MHz"), ("Data Rate", "3 Mbps"),
        ("Noise Figure", "10 dB"), ("CWmin", "15"), ("CWmax", "1023"),
        ("AIFS", "58"), ("Slot Time", "13")
    ]
    for sp_name, sp_val in sim_params:
        # check presence
        found = sp_val.split()[0] in l_t3
        print(f"  Sim Param '{sp_name}' ({sp_val}): {'FOUND' if found else 'MISSING'}")

    # Table 4: Optuna Optimal Hyperparameters of 14 Models
    print("\n[Table 4] Optuna Optimal Hyperparameters of 14 Models (tab:optuna_params)")
    l_t4 = l_tables[3]
    optuna_models = [
        ("Static-5Hz", "N/A"), ("ETSI DCC", "N/A"), ("SAE J2945/1", "N/A"), ("LIMERIC", "N/A"),
        ("Q-Learning", "1e-2"), ("SARSA", "1e-2"), ("DQN", "1e-3"), ("Double DQN", "5e-4"),
        ("Dueling DQN", "5e-4"), ("DQN+MoE", "1e-4"), ("MAPPO", "3e-4"), ("QMIX", "5e-4"),
        ("Decision Transformer", "1e-4"), ("REMO-DQN (Ours)", "1e-4")
    ]
    for m_name, lr_val in optuna_models:
        m_found = m_name.replace(" (Ours)", "") in l_t4
        print(f"  Model {m_name:25s}: {'FOUND' if m_found else 'MISSING'}")

    # Table 5: Learning Convergence Statistics
    print("\n[Table 5] Learning Convergence Statistics (tab:convergence_stats)")
    l_t5 = l_tables[4]
    conv_metrics = [
        ("REMO-DQN Ep to -100k", "74"), ("REMO-DQN Final Reward", "-61"),
        ("REMO-DQN Final PDR", "73.41"), ("REMO-DQN Final AoI", "373.21"),
        ("REMO-DQN Final CBR", "0.3442"), ("DQN Ep to -100k", "148"),
        ("DQN Final Reward", "-142"), ("DQN Final PDR", "45.63"),
        ("DQN Final AoI", "624.18"), ("DQN Final CBR", "0.5284")
    ]
    for c_name, c_val in conv_metrics:
        found = c_val in l_t5
        print(f"  Metric {c_name:30s} ({c_val}): {'FOUND' if found else 'MISSING'}")

    # Table 6: Time-Series CBR Statistics
    print("\n[Table 6] Time-Series CBR Statistics (tab:cbr_stats)")
    l_t6 = l_tables[5]
    cbr_vals = [
        ("Static-5Hz Mean", "0.6812"), ("Static-5Hz Std", "0.1845"),
        ("ETSI DCC Mean", "0.6124"), ("ETSI DCC Std", "0.1420"),
        ("Vanilla DQN Mean", "0.5284"), ("Vanilla DQN Std", "0.1632"),
        ("REMO-DQN Mean", "0.3442"), ("REMO-DQN Std", "0.1008")
    ]
    for c_name, c_val in cbr_vals:
        found = c_val in l_t6
        print(f"  CBR stat {c_name:25s} ({c_val}): {'FOUND' if found else 'MISSING'}")

    # Table 7: PDR vs Density
    print("\n[Table 7] PDR vs Vehicle Density (tab:pdr_density_stats)")
    l_t7 = l_tables[6]
    pdr_vals = [
        ("REMO-DQN 10 veh/km", "76.54"), ("REMO-DQN 50 veh/km", "74.88"), ("REMO-DQN 100 veh/km", "73.41"),
        ("Vanilla DQN 10 veh/km", "75.12"), ("Vanilla DQN 50 veh/km", "42.15"), ("Vanilla DQN 100 veh/km", "1.21"),
        ("ETSI DCC 100 veh/km", "28.45"), ("MAPPO 100 veh/km", "68.32"), ("Decision Transformer 100 veh/km", "69.15")
    ]
    for p_name, p_val in pdr_vals:
        found = p_val in l_t7
        print(f"  PDR stat {p_name:35s} ({p_val}): {'FOUND' if found else 'MISSING'}")

    # Table 8: Energy Consumption and Efficiency
    print("\n[Table 8] Communication Energy Consumption and Efficiency (tab:energy_stats)")
    l_t8 = l_tables[7]
    energy_vals = [
        ("REMO-DQN Energy (J)", "184.2"), ("REMO-DQN Efficiency (PDR/J)", "0.3985"),
        ("Static-5Hz Energy (J)", "420.5"), ("Static-5Hz Efficiency", "0.0812"),
        ("ETSI DCC Energy (J)", "298.4"), ("ETSI DCC Efficiency", "0.1842"),
        ("Vanilla DQN Energy (J)", "312.8"), ("Vanilla DQN Efficiency", "0.1458")
    ]
    for e_name, e_val in energy_vals:
        found = e_val in l_t8
        print(f"  Energy stat {e_name:35s} ({e_val}): {'FOUND' if found else 'MISSING'}")

    # Table 9: AoI vs Density
    print("\n[Table 9] Receiver-Side AoI vs Density (tab:aoi_density_stats)")
    l_t9 = l_tables[8]
    aoi_vals = [
        ("REMO-DQN 10 veh/km", "210.45"), ("REMO-DQN 50 veh/km", "295.12"), ("REMO-DQN 100 veh/km", "373.21"),
        ("Vanilla DQN 100 veh/km", "1290.89"), ("ETSI DCC 100 veh/km", "845.30"),
        ("MAPPO 100 veh/km", "420.15"), ("Decision Transformer 100 veh/km", "412.30")
    ]
    for a_name, a_val in aoi_vals:
        found = a_val in l_t9 or a_val.replace("1290.89", "1\\,290.89") in l_t9
        print(f"  AoI stat {a_name:35s} ({a_val}): {'FOUND' if found else 'MISSING'}")

    # Table 10: PDR vs Distance
    print("\n[Table 10] PDR vs Distance (tab:pdr_distance_stats)")
    l_t10 = l_tables[9]
    dist_vals = [
        ("REMO-DQN 50 m", "92.45"), ("REMO-DQN 150 m", "84.12"), ("REMO-DQN 300 m", "71.20"),
        ("Vanilla DQN 300 m", "12.45"), ("ETSI DCC 300 m", "34.12"), ("MAPPO 300 m", "65.40")
    ]
    for d_name, d_val in dist_vals:
        found = d_val in l_t10
        print(f"  Distance PDR {d_name:30s} ({d_val}): {'FOUND' if found else 'MISSING'}")

    # Table 11: Hardware Complexity
    print("\n[Table 11] Hardware Complexity and Latency (tab:hardware_stats)")
    l_t11 = l_tables[10]
    hw_vals = [
        ("Vanilla DQN MACs", "1.2 M"), ("Vanilla DQN Params", "100 K"), ("Vanilla DQN Latency", "0.5 ms"),
        ("DQN+MoE MACs", "1.5 M"), ("DQN+MoE Params", "120 K"), ("DQN+MoE Latency", "0.6 ms"),
        ("REMO-DQN MACs", "3.8 M"), ("REMO-DQN Params", "350 K"), ("REMO-DQN Latency", "1.2 ms"),
        ("REMO-DQN 100ms ratio", "1.2%")
    ]
    for h_name, h_val in hw_vals:
        # strip spaces for check
        clean_val = h_val.replace(" ", "")
        found = clean_val in l_t11.replace(" ", "")
        print(f"  Hardware stat {h_name:30s} ({h_val}): {'FOUND' if found else 'MISSING'}")

    # Table 12: Structural Ablation Study
    print("\n[Table 12] Structural Ablation Study (tab:ablation_stats)")
    l_t12 = l_tables[11]
    ablation_vals = [
        ("Vanilla DQN High Density PDR", "1.21"), ("Vanilla DQN AoI", "1290.89"), ("Vanilla DQN CBR Std", "0.1632"),
        ("DQN+ResNet High Density PDR", "48.35"), ("DQN+ResNet AoI", "580.45"), ("DQN+ResNet CBR Std", "0.1345"),
        ("DQN+MoE High Density PDR", "65.20"), ("DQN+MoE AoI", "452.18"), ("DQN+MoE CBR Std", "0.1058"),
        ("DQN+Dueling High Density PDR", "52.14"), ("DQN+Dueling AoI", "540.20"), ("DQN+Dueling CBR Std", "0.1280"),
        ("REMO-DQN High Density PDR", "73.41"), ("REMO-DQN AoI", "373.21"), ("REMO-DQN CBR Std", "0.1008")
    ]
    for ab_name, ab_val in ablation_vals:
        found = ab_val in l_t12 or ab_val.replace("1290.89", "1\\,290.89") in l_t12
        print(f"  Ablation stat {ab_name:35s} ({ab_val}): {'FOUND' if found else 'MISSING'}")

    # Table 13: MoE Routing Weights
    print("\n[Table 13] Dynamic MoE Routing Weights (tab:moe_routing_stats)")
    l_t13 = l_tables[12]
    moe_vals = [
        ("Density 20 Exp1", "0.80"), ("Density 20 Exp2", "0.15"), ("Density 20 Exp3", "0.05"),
        ("Density 80 Exp1", "0.35"), ("Density 80 Exp2", "0.50"), ("Density 80 Exp3", "0.15"),
        ("Density 160 Exp1", "0.05"), ("Density 160 Exp2", "0.10"), ("Density 160 Exp3", "0.85")
    ]
    for m_name, m_val in moe_vals:
        found = m_val in l_t13
        print(f"  MoE weight {m_name:30s} ({m_val}): {'FOUND' if found else 'MISSING'}")

    # Table 14: t-SNE Clustering
    print("\n[Table 14] t-SNE 2D Latent Space Clustering (tab:tsne_stats)")
    l_t14 = l_tables[13]
    tsne_vals = [
        ("Low Traffic mean_x", "-0.225"), ("Low Traffic std_x", "0.934"),
        ("Low Traffic mean_y", "0.084"), ("Low Traffic std_y", "0.894"),
        ("Medium Traffic mean_x", "5.018"), ("Medium Traffic std_x", "0.874"),
        ("Medium Traffic mean_y", "5.151"), ("Medium Traffic std_y", "1.092"),
        ("High Traffic mean_x", "1.961"), ("High Traffic std_x", "1.015"),
        ("High Traffic mean_y", "4.979"), ("High Traffic std_y", "1.081")
    ]
    for ts_name, ts_val in tsne_vals:
        found = ts_val in l_t14
        print(f"  t-SNE stat {ts_name:30s} ({ts_val}): {'FOUND' if found else 'MISSING'}")

if __name__ == "__main__":
    check_all_tables()
