import pandas as pd
import os
import gc
import argparse
from pathlib import Path

# Only merge sensors against scrap logged during production status
PRODUCTION_STATUS_CODES = [200]

def build_event_ts(df):
    """Build a UTC timestamp from the first usable Hydra timestamp column."""
    candidate_columns = [
        "production_order_login_timestamp",
        "plant_shift_timestamp",
        "production_order_logoff_timestamp",
        "last_load_timestamp",
        "machine_event_create_date",
    ]

    for column in candidate_columns:
        if column not in df.columns:
            continue

        base = pd.to_datetime(df[column], errors="coerce")
        if base.isna().all():
            continue

        if base.dt.tz is not None:
            base = base.dt.tz_convert("UTC").dt.tz_localize(None)

        if "machine_event_create_time" in df.columns:
            offset = pd.to_timedelta(
                pd.to_numeric(df["machine_event_create_time"], errors="coerce").fillna(0),
                unit="s",
            )
            return (base + offset).dt.tz_localize("UTC")

        return base.dt.tz_localize("UTC")

    raise KeyError(
        "No usable timestamp column found. Expected one of: "
        + ", ".join(candidate_columns)
    )

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
    hydra_path = proc_dir / "HYDRA_TRAIN.parquet"
    if not hydra_path.exists():
        print(f"❌ Error: Could not find '{hydra_path}'. Did you run Step 1?")
        return
        
    print("\n⏳ Loading Hydra Scrap Events...")
    hydra_df = pd.read_parquet(hydra_path)
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
    train_files = [f for f in os.listdir(proc_dir) if f.endswith("_TRAIN.parquet") and "HYDRA" not in f and "MERGED" not in f]
    print(f"\n   -> Found {len(train_files)} Machine Parquet files.")

    for file in train_files:
        machine_id_raw = file.split('_')[0]
        machine_id = machine_id_raw.replace('-', '').upper().strip()

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
        machine_scrap = machine_scrap.sort_values('timestamp')

        if not machine_scrap.empty:
            merged = pd.merge_asof(
                pivot_df,
                machine_scrap[['timestamp', 'is_scrap']],
                on='timestamp',
                direction='nearest',
                tolerance=pd.Timedelta('5 minutes')
            )
            merged['is_scrap'] = merged['is_scrap'].fillna(0).astype(int)
        else:
            pivot_df['is_scrap'] = 0
            merged = pivot_df

        merged['machine_id'] = machine_id
        scrap_pct = (merged['is_scrap'].sum() / len(merged)) * 100
        print(f"   -> Final merged rows: {len(merged):,}. Scrap rate: {scrap_pct:.2f}%")
        
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
