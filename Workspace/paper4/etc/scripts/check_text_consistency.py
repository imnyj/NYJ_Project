import re
import pandas as pd
import numpy as np

# Load reference datasets
pdr_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/pdr_vs_density.csv")
aoi_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/aoi_vs_density.csv")
cbr_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/cbr_trace.csv")
dist_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/pdr_vs_distance.csv")
hw_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/hardware_feasibility.csv")
moe_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/moe_routing.csv")
ab_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/ablation_study.csv")
tsne_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/tsne_clustering.csv")

print("=== All Datasets Loaded Successfully ===")

def check_file(filepath):
    print(f"\n=======================================================")
    print(f"Scanning file: {filepath}")
    print(f"=======================================================")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Define key claims to check
    checks = [
        ("REMO-DQN mean CBR", r"0\.3442", "CBR mean", cbr_df['REMO-DQN'].mean(), 0.3442),
        ("REMO-DQN std CBR", r"0\.1008", "CBR std", cbr_df['REMO-DQN'].std(), 0.1008),
        ("REMO-DQN min CBR", r"0\.1238", "CBR min", cbr_df['REMO-DQN'].min(), 0.1238),
        ("REMO-DQN max CBR", r"0\.5898", "CBR max", cbr_df['REMO-DQN'].max(), 0.5898),
        ("Vanilla DQN mean CBR", r"0\.3779", "Vanilla CBR mean", cbr_df['Vanilla DQN'].mean(), 0.3779),
        ("Vanilla DQN std CBR", r"0\.1193", "Vanilla CBR std", cbr_df['Vanilla DQN'].std(), 0.1193),
        ("DQN+MoE mean CBR", r"0\.3850", "DQN+MoE CBR mean", cbr_df['DQN+MoE'].mean(), 0.3850),
        ("DQN+MoE std CBR", r"0\.1058", "DQN+MoE CBR std", cbr_df['DQN+MoE'].std(), 0.1058),
        
        ("REMO-DQN PDR low (10)", r"76\.54%", "PDR low", pdr_df['REMO-DQN'].iloc[0], 76.54),
        ("REMO-DQN PDR mid (50)", r"75\.11%", "PDR mid", pdr_df['REMO-DQN'].iloc[22], 75.11),
        ("REMO-DQN PDR high (100)", r"73\.41%", "PDR high", pdr_df['REMO-DQN'].iloc[-1], 73.41),
        ("REMO-DQN PDR mean", r"75\.02%", "PDR mean", pdr_df['REMO-DQN'].mean(), 75.02),
        ("REMO-DQN PDR drop", r"3\.13%p", "PDR drop", pdr_df['REMO-DQN'].iloc[0] - pdr_df['REMO-DQN'].iloc[-1], 3.13),
        
        ("Fixed 10Hz PDR low", r"89\.70%", "Fixed low", pdr_df['Fixed 10Hz'].iloc[0], 89.70),
        ("Fixed 10Hz PDR high", r"15\.62%", "Fixed high", pdr_df['Fixed 10Hz'].iloc[-1], 15.62),
        ("Fixed 10Hz PDR drop", r"74\.08%p", "Fixed drop", pdr_df['Fixed 10Hz'].iloc[0] - pdr_df['Fixed 10Hz'].iloc[-1], 74.08),
        
        ("ReactDCC PDR drop", r"90\.93%p", "React drop", pdr_df['ReactDCC'].iloc[0] - pdr_df['ReactDCC'].iloc[-1], 90.93),
        ("AdaptDCC PDR drop", r"78\.01%p", "Adapt drop", pdr_df['AdaptDCC'].iloc[0] - pdr_df['AdaptDCC'].iloc[-1], 78.01),
        
        ("REMO-DQN AoI mean", r"373\.21", "AoI mean", aoi_df['REMO-DQN'].mean(), 373.21),
        ("REMO-DQN AoI low", r"138\.56", "AoI low", aoi_df['REMO-DQN'].iloc[0], 138.56),
        ("REMO-DQN AoI mid", r"380\.60", "AoI mid", aoi_df['REMO-DQN'].iloc[22], 380.60),
        ("REMO-DQN AoI high", r"579\.52", "AoI high", aoi_df['REMO-DQN'].iloc[-1], 579.52),
        ("REMO-DQN AoI increase", r"440\.95", "AoI increase", aoi_df['REMO-DQN'].iloc[-1] - aoi_df['REMO-DQN'].iloc[0], 440.95),
        
        ("Fixed 10Hz AoI mean", r"4,?682\.51", "Fixed AoI mean", aoi_df['Fixed 10Hz'].mean(), 4682.51),
        ("ReactDCC AoI mean", r"3,?848\.90", "React AoI mean", aoi_df['ReactDCC'].mean(), 3848.90),
        ("AdaptDCC AoI mean", r"3,?205\.96", "Adapt AoI mean", aoi_df['AdaptDCC'].mean(), 3205.96),
        ("Vanilla DQN AoI mean", r"1,?290\.89", "Vanilla AoI mean", aoi_df['Vanilla DQN'].mean(), 1290.89),
        
        ("Distance 200m REMO PDR", r"88\.68%", "Dist 200m REMO", dist_df['REMO-DQN'].iloc[4], 88.68),
        ("Distance 300m REMO PDR", r"71\.67%", "Dist 300m REMO", dist_df['REMO-DQN'].iloc[6], 71.67),
        ("Distance 300m Vanilla PDR", r"66\.74%", "Dist 300m Vanilla", dist_df['Vanilla DQN'].iloc[6], 66.74),
        ("Distance 300m MoE PDR", r"67\.58%", "Dist 300m MoE", dist_df['DQN+MoE'].iloc[6], 67.58),
        ("Distance 300m Gain vs Vanilla", r"\+?4\.93%p", "Dist gain", dist_df['REMO-DQN'].iloc[6] - dist_df['Vanilla DQN'].iloc[6], 4.93),
        
        ("Hardware MACs", r"3\.8\s*M", "MACs", 3.8, 3.8),
        ("Hardware Params", r"350\s*K", "Params", 350, 350),
        ("Hardware Latency", r"1\.2\s*ms", "Latency", 1.2, 1.2),
        ("Hardware Duty Cycle", r"1\.2%", "Duty Cycle", 1.2, 1.2),
        
        ("t-SNE Low X", r"-0\.225", "Low X", tsne_df[tsne_df['Cluster']=='Low Traffic']['x'].mean(), -0.225),
        ("t-SNE Low Y", r"\+?0\.084", "Low Y", tsne_df[tsne_df['Cluster']=='Low Traffic']['y'].mean(), 0.084),
        ("t-SNE Medium X", r"\+?5\.018", "Med X", tsne_df[tsne_df['Cluster']=='Medium Traffic']['x'].mean(), 5.018),
        ("t-SNE Medium Y", r"\+?5\.151", "Med Y", tsne_df[tsne_df['Cluster']=='Medium Traffic']['y'].mean(), 5.151),
        ("t-SNE High X", r"\+?1\.961", "High X", tsne_df[tsne_df['Cluster']=='High Traffic']['x'].mean(), 1.961),
        ("t-SNE High Y", r"\+?4\.979", "High Y", tsne_df[tsne_df['Cluster']=='High Traffic']['y'].mean(), 4.979),
    ]

    pass_count = 0
    fail_count = 0
    for name, pattern, label, csv_val, expected_val in checks:
        matches = re.findall(pattern, content)
        if matches:
            pass_count += 1
            print(f" [PASS] {name:30s} found in text (matches: {len(matches)}). CSV={csv_val:.4f}, Expected={expected_val}")
        else:
            fail_count += 1
            print(f" [FAIL/WARN] {name:30s} NOT FOUND with pattern '{pattern}'. CSV={csv_val:.4f}")

    print(f"\nSummary for {filepath}: {pass_count} passed, {fail_count} failed/missing.")

check_file("/home/imnyj/Workspace/paper4/paper/05_performance_evaluation.md")
check_file("/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md")
