import os
import glob
import pandas as pd
import random

dirs = [
    "/home/imnyj/Workspace/paper1/writer/data(Desk01)",
    "/home/imnyj/Workspace/paper1/writer/data(Desk02)",
    "/home/imnyj/SumoNetSim1.1.5/data"
]

output_file = "/home/imnyj/Workspace/paper1/github_repo/dataset_sample.csv"

all_files = []
for d in dirs:
    all_files.extend(glob.glob(os.path.join(d, "rsu_*.csv")))

print(f"Found {len(all_files)} CSV files.")

df_list = []
for f in all_files:
    df = pd.read_csv(f)
    df_list.append(df)

if df_list:
    combined_df = pd.concat(df_list, ignore_index=True)
    initial_len = len(combined_df)
    
    # Filter outliers (dwell_cur <= 400 and dwell_nxt <= 400)
    cleaned_df = combined_df[(combined_df['dwell_cur'] <= 400) & (combined_df['dwell_nxt'] <= 400)]
    cleaned_len = len(cleaned_df)
    
    # Sample to around 50MB. 
    # 111,230 rows was 32MB -> ~287 bytes/row.
    # 50MB = 50 * 1024 * 1024 / 287 ~ 182,600 rows.
    # 50MB was ~175k rows. For <25MB limit, we sample 85,000 rows.
    sample_size = 85000
    if cleaned_len > sample_size:
        final_df = cleaned_df.sample(n=sample_size, random_state=42)
    else:
        final_df = cleaned_df
        
    final_df.to_csv(output_file, index=False)
    
    actual_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    print(f"Processed: Initial={initial_len}, Cleaned={cleaned_len}, Final={len(final_df)}")
    print(f"Output saved to {output_file} (Size: {actual_size_mb:.2f} MB)")
else:
    print("No files found!")
