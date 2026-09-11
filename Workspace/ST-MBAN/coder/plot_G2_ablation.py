import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def main():
    df = pd.read_csv("/home/imnyj/papers/paper1/data/G2_ablation_results.csv")
    
    plt.figure(figsize=(12, 6))
    sns.set_theme(style="whitegrid")
    
    # Bar plot for MAE
    ax = sns.barplot(
        data=df,
        x="Model",
        y="MAE",
        palette="viridis"
    )
    
    # Add values on top of bars
    for p in ax.patches:
        ax.annotate(format(p.get_height(), '.2f'), 
                    (p.get_x() + p.get_width() / 2., p.get_height()), 
                    ha = 'center', va = 'center', 
                    xytext = (0, 9), 
                    textcoords = 'offset points')
                    
    plt.xlabel("Ablation Variants", fontsize=14)
    plt.ylabel("Validation MAE", fontsize=14)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig("/home/imnyj/papers/paper1/figure/G2_ablation_study.png", dpi=300)
    plt.close()
    
    print("G2 Ablation plot generated successfully.")

if __name__ == "__main__":
    main()
