import pandas as pd
import os
import gc
import argparse
from pathlib import Path

def get_machine_id(filename):
    """Extract machine ID from filename (e.g., M231Jan.csv -> M231)."""
    return Path(filename).stem.split("-")[0].replace("Jan", "").replace("Feb", "").upper()

def process_hydra(raw_dir, out_dir, cutoff_date=None):
    """Convert raw Hydra Excel files into HYDRA_TRAIN.parquet."""
    print(f"\n{'='*60}\nSTEP 1A — Processing Hydra Quality Data\n{'='*60}")
    
    xlsx_files = list(Path(raw_dir).glob("*.xlsx"))
    if not xlsx_files:
        print(f"⚠️  No .xlsx Hydra files found in {raw_dir}. Make sure you include the Hydra Dataset!")
        return

    hydra_file = xlsx_files[0]
    print(f"⏳ Loading Hydra file: {hydra_file.name}...")
    
    df = pd.read_excel(str(hydra_file))
    
    # Ensure datetime conversion for the event timestamp
    date_col = "machine_event_create_date" if "machine_event_create_date" in df.columns else df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], utc=True, errors="coerce")
    
    # If a cutoff date is provided, split it. Otherwise, use everything.
    if cutoff_date:
        train_df = df[df[date_col] <= cutoff_date]
    else:
        train_df = df
        
    out_path = Path(out_dir) / "HYDRA_TRAIN.parquet"
    train_df.to_parquet(out_path, index=False)
    print(f"✅ HYDRA_TRAIN saved: {len(train_df):,} rows")

def process_sensor_files(raw_dir, out_dir, cutoff_date=None):
    """Convert raw Machine CSV files into [MACHINE]_TRAIN.parquet."""
    print(f"\n{'='*60}\nSTEP 1B — Processing Machine Sensor Data\n{'='*60}")
    
    csv_files = sorted(Path(raw_dir).glob("*.csv"))
    if not csv_files:
        print(f"⚠️  No .csv sensor files found in {raw_dir}.")
        return

    print(f"Found {len(csv_files)} CSV files")

    for csv_file in csv_files:
        machine_id = get_machine_id(csv_file.name)
        print(f"\n⏳ Loading {csv_file.name} ({csv_file.stat().st_size/1e6:.1f} MB)...")

        df = pd.read_csv(str(csv_file), low_memory=False, on_bad_lines="skip")
        
        # Ensure timestamp exists
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            print(f"   -> Range: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
            
            if cutoff_date:
                df = df[df["timestamp"] <= cutoff_date]
        
        out_path = Path(out_dir) / f"{machine_id}_TRAIN.parquet"
        df.to_parquet(out_path, index=False)
        print(f"✅ {machine_id}_TRAIN saved: {len(df):,} rows")
        
        del df
        gc.collect()

def main():
    parser = argparse.ArgumentParser(description="Step 1: Convert Company Raw Excel/CSV to Parquet")
    parser.add_argument("--raw-dir", type=str, default="./raw_data", 
                        help="Folder containing original .csv machine files and .xlsx Hydra file")
    parser.add_argument("--outdir", type=str, default="./new_processed_data",
                        help="Folder to save the converted .parquet files")
    parser.add_argument("--cutoff-date", type=str, default=None,
                        help="Optional split date (e.g. '2026-01-11'). Data after this is ignored.")
    
    args = parser.parse_args()
    
    os.makedirs(args.outdir, exist_ok=True)
    cutoff = pd.to_datetime(args.cutoff_date, utc=True) if args.cutoff_date else None
    
    print("🚀 Starting Portable Raw Data Converter (V4-Compatible)")
    print(f"   Input Dir:  {args.raw_dir}")
    print(f"   Output Dir: {args.outdir}")
    if cutoff: print(f"   Cutoff:     {cutoff.date()}")

    if not Path(args.raw_dir).exists():
        print(f"\n❌ Input directory '{args.raw_dir}' does not exist!")
        print(f"Please create the folder, put the CSV/Excel files inside, and run again.")
        return

    process_hydra(args.raw_dir, args.outdir, cutoff)
    process_sensor_files(args.raw_dir, args.outdir, cutoff)
    
    print("\n🎉 DONE! Step 1 Complete.")
    print("Next step: Run the `step2_merge_master_v4.py` script to align scrap events!")

if __name__ == "__main__":
    main()
