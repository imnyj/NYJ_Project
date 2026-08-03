import os
import pandas as pd
import glob

data_dir = "/home/imnyj/Workspace/paper1/writer/data(Desk02)"
output_file = "/home/imnyj/Workspace/paper1/writer/final/cleaned_dataset.csv"

all_files = glob.glob(os.path.join(data_dir, "*.csv"))
df_list = []

for file in all_files:
    df = pd.read_csv(file)
    df_list.append(df)

if df_list:
    combined_df = pd.concat(df_list, ignore_index=True)
    initial_len = len(combined_df)
    
    # Filter outliers (e.g. dwell times > 400s)
    # The paper says average is 100 to 300 seconds. Let's filter out anything > 500s just to be safe and remove extreme outliers.
    cleaned_df = combined_df[(combined_df['dwell_cur'] <= 400) & (combined_df['dwell_nxt'] <= 400)]
    
    cleaned_df.to_csv(output_file, index=False)
    print(f"Consolidated and cleaned dataset saved to {output_file}")
    print(f"Original size: {initial_len}, Cleaned size: {len(cleaned_df)}")
else:
    print("No CSV files found.")
