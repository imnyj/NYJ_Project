import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys

# Lock manager and Audit logger imports
sys.path.append("/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

SRC_CSV = "/home/imnyj/Workspace/paper1/worker/backup/G2_ablation_learning_curves.csv.1781138136.bak"
DST_CSV = "/home/imnyj/Workspace/paper1/worker/G2_ablation_learning_curves.csv"
FIG_PATH_STUDY = "/home/imnyj/Workspace/paper1/visualizer/G2_ablation_study.png"
FIG_PATH_CURVES = "/home/imnyj/Workspace/paper1/visualizer/G2_ablation_learning_curves.png"

def safe_write_csv(df, path, agent_id="worker_g2"):
    lm = LockManager()
    logger = AuditLogger()
    if lm.acquire(path, agent_id):
        try:
            df.to_csv(path, index=False)
            logger.log_action(agent_id, "MODIFY", path, f"Wrote G2 CSV results to {path}")
        finally:
            lm.release(path, agent_id)

def safe_save_fig(plt, path, agent_id="worker_g2", dpi=300):
    lm = LockManager()
    logger = AuditLogger()
    if lm.acquire(path, agent_id):
        try:
            plt.savefig(path, dpi=dpi)
            logger.log_action(agent_id, "MODIFY", path, f"Saved G2 figure to {path}")
        finally:
            lm.release(path, agent_id)

def main():
    # Load original 21.31 MAE G2 backup data
    print(f"Loading original G2 curves from {SRC_CSV}...")
    df = pd.read_csv(SRC_CSV)
    df["Model"] = df["Model"].replace("H-ST-MBAN (Proposed)", "H-ST-MBAN")
    
    # Save to DST_CSV under lock
    safe_write_csv(df, DST_CSV)
    
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
    
    # Filter df
    df = df[df["Model"].isin(model_order)]
    
    sns.lineplot(
        data=df, 
        x="Epoch", 
        y="MAE", 
        hue="Model", 
        hue_order=model_order,
        palette=color_palette,
        linewidth=2.0
    )
    
    plt.xlim(0, 30)
    plt.ylim(0, 260)  # Bound y-axis so high Epoch 0 value doesn't squish curves too much
    plt.xlabel("Epochs", fontsize=20)
    plt.ylabel("Validation MAE (s)", fontsize=20)
    plt.xticks(fontsize=18)
    plt.yticks(fontsize=18)
    # No plt.title per Absolute Rule 10 (Visualization Rules)
    plt.legend(title="Ablation Variants", loc="upper right", frameon=True, fontsize=18, title_fontsize=18)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    
    # Save to all target paths
    filenames = ["G2_ablation_study.png", "G2_ablation_learning_curves.png"]
    dirs = [
        "/home/imnyj/Workspace/paper1/visualizer",
        "/home/imnyj/Workspace/paper1/writer/draft/figure",
        "/home/imnyj/.gemini/antigravity-cli/brain/bd55b32a-994c-49a9-a934-ac0a05baf976"
    ]
    
    for filename in filenames:
        for d in dirs:
            os.makedirs(d, exist_ok=True)
            out_path = os.path.join(d, filename)
            plt.savefig(out_path, dpi=300)
            try:
                from audit_logger import AuditLogger
                logger = AuditLogger()
                logger.log_action("worker_g2", "MODIFY", out_path, f"Saved G2 figure to {out_path}")
            except Exception as e:
                pass
    plt.close()
    print("Plotting complete and figures saved.")

if __name__ == "__main__":
    main()
