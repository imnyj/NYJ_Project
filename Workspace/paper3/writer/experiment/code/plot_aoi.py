import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# IEEE style configuration
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 12,
    'axes.labelsize': 14,
    'axes.titlesize': 14,
    'legend.fontsize': 10,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'figure.figsize': (7, 5),
    'lines.linewidth': 2,
    'lines.markersize': 8,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight'
})

def main():
    data_dir = r"g:\내 드라이브\개인 자료\YoungjuNam\paper-ai.v1\papers\paper3\paper\data"
    csv_files = glob.glob(os.path.join(data_dir, "*_full.csv"))
    
    if not csv_files:
        print("No CSV files found.")
        return

    df_list = []
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            df_list.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")
            
    if not df_list:
        return
        
    full_df = pd.concat(df_list, ignore_index=True)
    
    # Filter out columns of interest: algorithm, density, AoI_violation_rate
    # We will average over other parameters (like seed, gamma, pred_error, tau_max)
    # Alternatively, you can filter for specific baseline parameters, e.g. gamma=2.0, tau_max=5
    
    # We plot mean with confidence intervals using seaborn lineplot
    
    plt.figure()
    
    # Define custom markers for distinction
    markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']
    
    # Generate the plot
    ax = sns.lineplot(
        data=full_df, 
        x='density', 
        y='AoI_violation_rate', 
        hue='algorithm', 
        style='algorithm',
        markers=markers[:full_df['algorithm'].nunique()],
        dashes=False,
        err_style="bars", 
        errorbar=('ci', 95)
    )
    
    # Formatting the axes
    plt.xlabel('Vehicle Density (Vehicles / RSU)')
    plt.ylabel('AoI Violation Rate')
    plt.title('AoI Violation Rate vs Vehicle Density')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Customize legend
    plt.legend(title='Algorithm', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Save the figures
    pdf_path = os.path.join(data_dir, "AoI_Violation_vs_Density.pdf")
    png_path = os.path.join(data_dir, "AoI_Violation_vs_Density.png")
    
    plt.savefig(pdf_path)
    plt.savefig(png_path)
    print(f"Plots saved to {pdf_path} and {png_path}")

if __name__ == "__main__":
    main()
