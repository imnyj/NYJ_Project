import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def main():
    data_dir = r"g:\내 드라이브\개인 자료\YoungjuNam\paper-ai.v1\papers\paper3\paper\data"
    csv_path = os.path.join(data_dir, "A_full.csv")
    
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return
        
    df = pd.read_csv(csv_path)
    # Filter for Density = 5
    df_d5 = df[df['density'] == 5]
    
    plt.figure(figsize=(8, 6))
    sns.set_style("whitegrid")
    sns.lineplot(
        data=df_d5,
        x="pred_error_pct",
        y="AoI_violation_rate",
        hue="algorithm",
        style="algorithm",
        markers=True,
        dashes=False,
        linewidth=2.5,
        markersize=8,
        errorbar=('ci', 95)
    )
    
    plt.xlabel("Prediction Error Magnitude (%)", fontsize=14, fontweight='bold')
    plt.ylabel("AoI Violation Rate", fontsize=14, fontweight='bold')
    plt.title("AoI Violation Rate vs Prediction Error (Density=5)", fontsize=16, fontweight='bold')
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.legend(title="Algorithm", fontsize=10, title_fontsize=12, bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    out_pdf = os.path.join(data_dir, "AoI_Violation_vs_PredError.pdf")
    out_png = os.path.join(data_dir, "AoI_Violation_vs_PredError.png")
    plt.savefig(out_pdf, format='pdf', dpi=300)
    plt.savefig(out_png, format='png', dpi=300)
    print(f"Plots saved to {out_pdf} and {out_png}")

if __name__ == "__main__":
    main()
