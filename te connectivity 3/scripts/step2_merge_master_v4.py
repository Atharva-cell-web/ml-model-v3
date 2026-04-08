import pandas as pd
import os
import gc
import argparse
import re
from pathlib import Path

# Only merge sensors against scrap logged during production status
PRODUCTION_STATUS_CODES = [200]

def build_event_ts(df):
    """Combine date + seconds-of-day -> UTC timestamp."""
    base = pd.to_datetime(df['machine_event_create_date'])
    if base.dt.tz is not None:
        base = base.dt.tz_convert('UTC').dt.tz_localize(None)
    
    if 'machine_event_create_time' in df.columns:
        offset = pd.to_timedelta(
            pd.to_numeric(df['machine_event_create_time'], errors='coerce').fillna(0),
            unit='s'
        )
        return (base + offset).dt.tz_localize('UTC')
    return base.dt.tz_localize('UTC')

def main():
    parser = argparse.ArgumentParser(description="Step 2: Merge Machine Parquets with Hydra Labels")
    parser.add_argument("--processed-dir", type=str, default="./new_processed_data",
                        help="Folder containing the Step 1 converted .parquet files")
    parser.add_argument("--outdir", type=str, default="./new_processed_data",
                        help="Folder to save the FINAL_TRAINING_MASTER_V3.parquet")
    parser.add_argument("--master-name", type=str, default="FINAL_TRAINING_MASTER_V3.parquet",
                        help="Name of the final output file")
    
    args = parser.parse_args()
    
    proc_dir = Path(args.processed_dir)
    out_dir = Path(args.outdir)
    out_dir.mkdir(exist_ok=True)
    
    print("🚀 Starting Data Merger & Pivoter (Portable V4)")
    print("   Using Status 200 + 5-min point merge logic")

    # 1. Load Hydra Scrap Events
    hydra_files = list(proc_dir.glob("*HYDRA_TRAIN.parquet"))
    if not hydra_files:
        print(f"❌ Error: Could not find any *HYDRA_TRAIN.parquet files in '{proc_dir}'. Did you run Step 1?")
        return
        
    print(f"\n⏳ Loading {len(hydra_files)} Hydra Scrap Event files...")
    hydra_dfs = [pd.read_parquet(f) for f in hydra_files]
    hydra_df = pd.concat(hydra_dfs, ignore_index=True)
    
    hydra_df = hydra_df.drop_duplicates(subset=[
        'machine_id', 'machine_event_create_date', 
        'machine_event_create_time', 'scrap_quantity'
    ])
    scrap_source = hydra_df[hydra_df['scrap_quantity'] > 0].copy()

    if 'machine_status_code' in hydra_df.columns:
        scrap_source = scrap_source[scrap_source['machine_status_code'].isin(PRODUCTION_STATUS_CODES)]
    
    # Normalize Machine IDs for matching
    scrap_source['machine_id_clean'] = (
        scrap_source['machine_id'].astype(str)
        .str.replace('-', '').str.upper().str.strip()
    )
    
    # Build exact Scrap Timestamps
    scrap_source['merge_ts'] = build_event_ts(scrap_source)
    scrap_source = scrap_source.sort_values('merge_ts')
    
    print(f"   -> {len(scrap_source)} production scrap events prepared for merger.")
    
    master_train_dfs = []
    
    # 2. Process Machine Files
    train_files = [f for f in os.listdir(proc_dir) if f.endswith("_TRAIN.parquet") and "HYDRA" not in f and "MERGED" not in f and "FINAL" not in f]
    print(f"\n   -> Found {len(train_files)} Machine Parquet files.")

    for file in train_files:
        tokens = file.replace('.parquet', '').split('_')
        machine_id_raw = next((t for t in tokens if re.match(r'^M\d+$', t)), tokens[0])
        machine_id = machine_id_raw.upper().strip()

        print(f"\n⚙️  Processing {machine_id_raw} (as {machine_id})...")
        df = pd.read_parquet(proc_dir / file)
        
        # Robust Value Cleaning
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna(subset=['value'])

        print("   -> Pivoting to wide format...")
        pivot_df = df.pivot_table(
            index='timestamp',
            columns='variable_name',
            values='value',
            aggfunc='mean'
        ).reset_index()

        pivot_df['timestamp'] = pd.to_datetime(pivot_df['timestamp'], utc=True)
        pivot_df = pivot_df.sort_values('timestamp').reset_index(drop=True)

        # Retrieve machine-specific scrap records
        machine_scrap = scrap_source[scrap_source['machine_id_clean'] == machine_id][['merge_ts', 'scrap_quantity']].copy()
        machine_scrap = machine_scrap.rename(columns={'merge_ts': 'timestamp'})
        machine_scrap['is_scrap'] = 1
        # Save the original scrap timestamp to calculate time difference
        machine_scrap['scrap_timestamp'] = machine_scrap['timestamp']
        machine_scrap = machine_scrap.sort_values('timestamp')

        if not machine_scrap.empty:
            merged = pd.merge_asof(
                pivot_df,
                machine_scrap[['timestamp', 'is_scrap', 'scrap_quantity', 'scrap_timestamp']],
                on='timestamp',
                direction='forward',  # 'forward' is needed since scrap (right) is AFTER sensor (left)
                tolerance=pd.Timedelta('2 minutes')
            )
            merged['is_scrap'] = merged['is_scrap'].fillna(0).astype(int)
            merged['scrap_quantity'] = merged['scrap_quantity'].fillna(0)
            
            # direction='forward' means scrap_timestamp >= sensor timestamp
            time_diff = (merged['scrap_timestamp'] - merged['timestamp']).dt.total_seconds()
            
            merged['scrap_weight'] = 1.0
            
            high_conf_mask = (merged['is_scrap'] == 1) & (time_diff < 30)
            merged.loc[high_conf_mask, 'scrap_weight'] = 2.0
            
            matched_events = merged['scrap_timestamp'].dropna().nunique()
        else:
            pivot_df['is_scrap'] = 0
            pivot_df['scrap_quantity'] = 0
            pivot_df['scrap_weight'] = 1.0
            merged = pivot_df
            matched_events = 0

        merged['machine_id'] = machine_id
        
        # Calculate stats for the report
        total_sensor_rows = len(merged)
        scrap_rows = merged['is_scrap'].sum()
        scrap_pct = (scrap_rows / total_sensor_rows) * 100 if total_sensor_rows > 0 else 0
        
        high_conf_rows = (merged['scrap_weight'] == 2.0).sum()
        normal_conf_rows = scrap_rows - high_conf_rows
        
        total_hydra_events = len(machine_scrap)
        unmatched_events = total_hydra_events - matched_events
        
        print(f"   -> Final merged rows: {total_sensor_rows:,}")
        print(f"   -> Scrap rows (is_scrap=1): {scrap_rows:,} ({scrap_pct:.2f}%)")
        print(f"   -> Confidence split: {high_conf_rows:,} high | {normal_conf_rows:,} normal")
        print(f"   -> Hydra events match rate: {matched_events:,} matched | {unmatched_events:,} unmatched")
        
        if 'scrap_timestamp' in merged.columns:
            merged = merged.drop(columns=['scrap_timestamp'])
        
        master_train_dfs.append(merged)
        del df, pivot_df, merged
        gc.collect()

    # 3. Combine Masters
    if not master_train_dfs:
        print("\n❌ No data was merged. Pipeline failed.")
        return

    print("\n🔗 Combining all machines into FINAL_TRAINING_MASTER...")
    final_train_df = pd.concat(master_train_dfs, ignore_index=True)

    # Sort comprehensively for v4 script downstream
    final_train_df = final_train_df.sort_values(by=["machine_id", "timestamp"]).reset_index(drop=True)
    
    final_save_path = out_dir / args.master_name
    final_train_df.to_parquet(final_save_path, index=False)

    total_scrap = final_train_df['is_scrap'].sum()
    scrap_pct = (total_scrap / len(final_train_df)) * 100

    print(f"\n✅ DONE! Saved Master File: {final_save_path}")
    print(f"📊 Total Rows: {len(final_train_df):,}")
    print(f"🧨 Total Scrap: {total_scrap:,} ({scrap_pct:.2f}%)")
    
    print(f"\n🎉 Step 2 Complete. Your Master file is ready for the V4 Preprocessing Pipeline!")
    print(f"Next command: python scripts/data_preprocessing_v4.py --input '{final_save_path}' --outdir '{out_dir}'")

if __name__ == "__main__":
    main()
