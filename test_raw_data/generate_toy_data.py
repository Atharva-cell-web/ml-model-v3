import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

def generate_messy_raw_data(output_path):
    # Base configuration
    rows = 100
    machine_id = "M231-11"
    sensors = [
        "Cyl_tmp_z1", "Cyl_tmp_z2", "Injection_pressure", 
        "Cycle_time", "Switch_pressure", "Ejector_fix_d",
        "Peak_pressure", "Time_on_machine"
    ]
    
    data = []
    base_time = datetime(2026, 3, 30, 8, 0, 0)
    
    for i in range(rows):
        # Generate a timestamp (messy every now and then)
        if i % 10 == 0:
            ts = "2026-INVALID-DATE" # Malformed
        elif i % 15 == 0:
            ts = None # Missing
        else:
            ts = (base_time + timedelta(seconds=i*30)).strftime("%Y-%m-%d %H:%M:%S.000000")
            
        # Select a random sensor
        sensor = np.random.choice(sensors)
        
        # Generate a value (messy often)
        val = np.random.uniform(20.0, 450.0)
        final_val = str(round(val, 2))
        
        if i % 7 == 0:
            final_val = "N/A" # String instead of number
        elif i % 12 == 0:
            final_val = "" # Empty
        elif i % 20 == 0:
            final_val = "999.abc" # Corrupted number
            
        data.append({
            "device_name": "be714-em63-multi-client",
            "machine_definition": machine_id,
            "variable_name": sensor,
            "value": final_val,
            "timestamp": ts,
            "variable_attribute": "",
            "device": "be714-em63",
            "machine_def": machine_id,
            "year": "2026",
            "month": "03",
            "date": "2026-03-30"
        })

    df = pd.DataFrame(data)
    
    # Save as CSV (as requested "raw" often comes in CSV)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated messy raw data at: {output_path}")

if __name__ == "__main__":
    generate_messy_raw_data("d:/teit04/test_raw_data/messy_raw_M231.csv")
