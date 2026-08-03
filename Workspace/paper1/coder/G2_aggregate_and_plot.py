import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys

# Add Command/core to path for lock manager and audit logger
sys.path.append("/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

OUT_CSV_FINAL = "/home/imnyj/Workspace/paper1/worker/G2_ablation_learning_curves.csv"
FIG_PATH_STUDY = "/home/imnyj/Workspace/paper1/visualizer/G2_ablation_study.png"
FIG_PATH_CURVES = "/home/imnyj/Workspace/paper1/visualizer/G2_ablation_learning_curves.png"

def safe_write_csv(df, path, agent_id="worker_g2"):
    lm = LockManager()
    logger = AuditLogger()
    if lm.acquire(path, agent_id):
        try:
            df.to_csv(path, index=False)
            logger.log_action(agent_id, "MODIFY", path, f"Wrote CSV results to {path}")
        finally:
            lm.release(path, agent_id)

def safe_save_fig(plt, path, agent_id="worker_g2", dpi=300):
    lm = LockManager()
    logger = AuditLogger()
    if lm.acquire(path, agent_id):
        try:
            plt.savefig(path, dpi=dpi)
            logger.log_action(agent_id, "MODIFY", path, f"Saved figure to {path}")
        finally:
            lm.release(path, agent_id)

def main():
    # Load H-ST-MBAN from G1
    print("Loading H-ST-MBAN G1 curves...")
    g1_h_st_mban_path = "/home/imnyj/Workspace/paper1/worker/G1_learning_curves.csv"
    g1_all_df = pd.read_csv(g1_h_st_mban_path)
    g1_df = g1_all_df[g1_all_df["Model"] == "H-ST-MBAN"].copy()
    g1_df = g1_df.rename(columns={"Step": "Epoch"})
    g1_df["Model"] = "H-ST-MBAN"
    
    # Files of the 6 ablation variants
    temp_files = {
        "w/o XGB": "/home/imnyj/Workspace/paper1/worker/ablation_temp_w_o_Hybrid.csv",
        "w/o Attn": "/home/imnyj/Workspace/paper1/worker/ablation_temp_w_o_Attention.csv",
        "Early Fusion": "/home/imnyj/Workspace/paper1/worker/ablation_temp_Early_Fusion.csv",
        "w/o Social (S)": "/home/imnyj/Workspace/paper1/worker/ablation_temp_w_o_Social_S.csv",
        "w/o Traffic (T)": "/home/imnyj/Workspace/paper1/worker/ablation_temp_w_o_Traffic_T.csv",
        "w/o Kinematic (K)": "/home/imnyj/Workspace/paper1/worker/ablation_temp_w_o_Kinematic_K.csv"
    }
    
    dfs = [g1_df]
    for mapped_name, file_path in temp_files.items():
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df["Model"] = mapped_name
            dfs.append(df)
            print(f"Loaded {mapped_name} from {file_path}")
        else:
            print(f"Warning: File not found: {file_path}")
            
    final_df = pd.concat(dfs, ignore_index=True)
    safe_write_csv(final_df, OUT_CSV_FINAL)
    print(f"Saved final ablation learning curves to {OUT_CSV_FINAL}")
    
    # Plotting
    print("Plotting learning curves...")
    plt.figure(figsize=(10, 6))
    sns.set_theme(style="whitegrid")
    
    # Define exact colors
    color_palette = {
        "H-ST-MBAN": "#FF0000",   # Red
        "w/o XGB": "#ED7D31",                # Orange
        "w/o Attn": "#3399FF",               # Blue
        "Early Fusion": "#70AD47",           # Green
        "w/o Social (S)": "#800080",         # Purple
        "w/o Traffic (T)": "#FFD700",         # Gold/Yellow
        "w/o Kinematic (K)": "#008080"       # Teal
    }
    
    model_order = [
        "H-ST-MBAN",
        "w/o XGB",
        "w/o Attn",
        "Early Fusion",
        "w/o Social (S)",
        "w/o Traffic (T)",
        "w/o Kinematic (K)"
    ]
    
    final_df = final_df[final_df["Model"].isin(model_order)]
    
    sns.lineplot(
        data=final_df, 
        x="Epoch", 
        y="MAE", 
        hue="Model", 
        hue_order=model_order,
        palette=color_palette,
        linewidth=2.0
    )
    
    plt.xlim(0, 30)
    plt.ylim(0, 260)  # Bound y-axis so high Epoch 0 value doesn't squish curves too much
    plt.xlabel("Epochs", fontsize=12)
    plt.ylabel("Validation MAE (seconds)", fontsize=12)
    plt.legend(title="Ablation Variants", loc="upper right", frameon=True)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    
    safe_save_fig(plt, FIG_PATH_STUDY)
    safe_save_fig(plt, FIG_PATH_CURVES)
    plt.close()
    print("Plotting complete and figures saved.")

if __name__ == "__main__":
    main()
