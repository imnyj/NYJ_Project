import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys

# Audit logger import
sys.path.append("/home/imnyj/Command/core")
try:
    from audit_logger import AuditLogger
    has_logger = True
except ImportError:
    has_logger = False

CSV_PATH = "/home/imnyj/Workspace/paper1/worker/goal_pred_vs_true_all.csv"

# Destination directories
DIR_VISUALIZER = "/home/imnyj/Workspace/paper1/visualizer"
DIR_DRAFT_FIG = "/home/imnyj/Workspace/paper1/writer/draft/figure"
DIR_ARTIFACTS = "/home/imnyj/.gemini/antigravity-cli/brain/bd55b32a-994c-49a9-a934-ac0a05baf976"

def log_modification(path, agent_id="worker_g3"):
    if has_logger:
        try:
            logger = AuditLogger()
            logger.log_action(agent_id, "MODIFY", path, f"Saved figure to {path}")
            print(f"Logged modification for {path}")
        except Exception as e:
            print(f"Failed to log modification: {e}")

def main():
    print(f"Loading G3 prediction vs true data from {CSV_PATH}...")
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {CSV_PATH}")
        sys.exit(1)
        
    df = pd.read_csv(CSV_PATH)
    
    # Check headers
    print("CSV columns:", list(df.columns))
    
    # 1. G3-1: Current RSU Dwell Time
    print("Plotting G3-1 (Current Target)...")
    fig, ax = plt.subplots(figsize=(7, 7))
    sns.set_theme(style="whitegrid")
    
    # Scatter plot
    ax.scatter(
        df["True_Dwell_Cur"], 
        df["ST-MBAN_Pred_Cur"], 
        color="#FF0000", 
        alpha=0.25, 
        s=6, 
        label="H-ST-MBAN",
        edgecolors="none"
    )
    
    # Ideal line
    ax.plot([0, 3000], [0, 3000], color="gray", linestyle="--", linewidth=2, label="Identity line")
    
    # Set aspect and limits
    ax.set_box_aspect(1)
    ax.set_xlim(0, 3000)
    ax.set_ylim(0, 3000)
    
    # Labels (20pt) and Ticks (18pt)
    ax.set_xlabel(r"True Dwell Time $\tau_{\mathrm{cur}}$ (s)", fontsize=20)
    ax.set_ylabel(r"Predicted Dwell Time $\hat{\tau}_{\mathrm{cur}}$ (s)", fontsize=20)
    ax.tick_params(axis='both', which='major', labelsize=18)
    
    # Legend (18pt)
    ax.legend(loc="upper left", fontsize=18)
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    
    # Save individual plot G3-1 to the three directories
    paths_g3_1 = [
        os.path.join(DIR_VISUALIZER, "G3-1_pred_vs_true_cur.png"),
        os.path.join(DIR_DRAFT_FIG, "G3-1_pred_vs_true_cur.png"),
        os.path.join(DIR_ARTIFACTS, "G3-1_pred_vs_true_cur.png")
    ]
    
    for path in paths_g3_1:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        plt.savefig(path, dpi=300, bbox_inches="tight")
        log_modification(path)
        
    plt.close()
    
    # 2. G3-2: Next RSU Dwell Time
    print("Plotting G3-2 (Next Target)...")
    fig, ax = plt.subplots(figsize=(7, 7))
    
    ax.scatter(
        df["True_Dwell_Nxt"], 
        df["ST-MBAN_Pred_Nxt"], 
        color="#FF0000", 
        alpha=0.25, 
        s=6, 
        label="H-ST-MBAN",
        edgecolors="none"
    )
    
    ax.plot([0, 3000], [0, 3000], color="gray", linestyle="--", linewidth=2, label="Identity line")
    
    ax.set_box_aspect(1)
    ax.set_xlim(0, 3000)
    ax.set_ylim(0, 3000)
    
    ax.set_xlabel(r"True Dwell Time $\tau_{\mathrm{nxt}}$ (s)", fontsize=20)
    ax.set_ylabel(r"Predicted Dwell Time $\hat{\tau}_{\mathrm{nxt}}$ (s)", fontsize=20)
    ax.tick_params(axis='both', which='major', labelsize=18)
    
    ax.legend(loc="upper left", fontsize=18)
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    
    paths_g3_2 = [
        os.path.join(DIR_VISUALIZER, "G3-2_pred_vs_true_nxt.png"),
        os.path.join(DIR_DRAFT_FIG, "G3-2_pred_vs_true_nxt.png"),
        os.path.join(DIR_ARTIFACTS, "G3-2_pred_vs_true_nxt.png")
    ]
    
    for path in paths_g3_2:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        plt.savefig(path, dpi=300, bbox_inches="tight")
        log_modification(path)
        
    plt.close()
    
    # 3. G3: Unified Side-by-Side Plot
    print("Plotting G3 Unified Subplots...")
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    
    # Subplot 1: Cur
    axes[0].scatter(
        df["True_Dwell_Cur"], 
        df["ST-MBAN_Pred_Cur"], 
        color="#FF0000", 
        alpha=0.25, 
        s=6, 
        label="H-ST-MBAN",
        edgecolors="none"
    )
    axes[0].plot([0, 3000], [0, 3000], color="gray", linestyle="--", linewidth=2, label="Identity line")
    axes[0].set_box_aspect(1)
    axes[0].set_xlim(0, 3000)
    axes[0].set_ylim(0, 3000)
    axes[0].set_xlabel(r"True Dwell Time $\tau_{\mathrm{cur}}$ (s)", fontsize=20)
    axes[0].set_ylabel(r"Predicted Dwell Time $\hat{\tau}_{\mathrm{cur}}$ (s)", fontsize=20)
    axes[0].tick_params(axis='both', which='major', labelsize=18)
    axes[0].legend(loc="upper left", fontsize=18)
    axes[0].grid(True, linestyle="--", alpha=0.6)
    
    # Subplot 2: Nxt
    axes[1].scatter(
        df["True_Dwell_Nxt"], 
        df["ST-MBAN_Pred_Nxt"], 
        color="#FF0000", 
        alpha=0.25, 
        s=6, 
        label="H-ST-MBAN",
        edgecolors="none"
    )
    axes[1].plot([0, 3000], [0, 3000], color="gray", linestyle="--", linewidth=2, label="Identity line")
    axes[1].set_box_aspect(1)
    axes[1].set_xlim(0, 3000)
    axes[1].set_ylim(0, 3000)
    axes[1].set_xlabel(r"True Dwell Time $\tau_{\mathrm{nxt}}$ (s)", fontsize=20)
    axes[1].set_ylabel(r"Predicted Dwell Time $\hat{\tau}_{\mathrm{nxt}}$ (s)", fontsize=20)
    axes[1].tick_params(axis='both', which='major', labelsize=18)
    axes[1].legend(loc="upper left", fontsize=18)
    axes[1].grid(True, linestyle="--", alpha=0.6)
    
    # No titles are added to axes[0] or axes[1] per Rule 10
    
    plt.tight_layout()
    
    paths_g3_unified = [
        os.path.join(DIR_VISUALIZER, "G3_pred_vs_true.png"),
        os.path.join(DIR_DRAFT_FIG, "G3_pred_vs_true.png"),
        os.path.join(DIR_ARTIFACTS, "G3_pred_vs_true.png")
    ]
    
    for path in paths_g3_unified:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        plt.savefig(path, dpi=300, bbox_inches="tight")
        log_modification(path)
        
    plt.close()
    print("All G3 plots generated successfully.")

if __name__ == "__main__":
    main()
