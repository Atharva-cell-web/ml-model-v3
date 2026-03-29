# Manufacturing Scrap Prediction System (ML v3/v4)

This repository contains the source code and machine learning scripts for predicting manufacturing scrap events.

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9+
- [Git](https://git-scm.com/)

### 2. Setup Environment
Clone the repository and set up a virtual environment:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r "te connectivity 3/requirements.txt"
```

---

## 📂 Project Structure

- `te connectivity 3/`: Primary development folder
  - `scripts/`: Python scripts for data processing and model training
  - `backend/`: API and server-side logic
  - `frontend/`: Dashboard and UI components
- `processed/`: (Ignored) Processed sensor and parameter data
- `new_processed_data/`: (Ignored) v4/v4.5 updated datasets

---

## 📦 Heavy Files (Google Drive Required)

To keep the repository lightweight, large datasets and trained models (>50MB) are **not** included in this Git repository. Please download these from the provided Google Drive link and place them in their respective directories:

| File Name | Destination Directory | Description |
|-----------|-----------------------|-------------|
| `te connectivity 3.zip` | Root `./` | Full project backup including all data |
| `rolling_features.parquet` | `te connectivity 3/new_processed_data/` | Pre-engineered rolling features for training |
| `M607-30_Jan_sensor_features.parquet` | `te connectivity 3/processed/sensor/` | Large sensor feature dataset |
| `M231Jan_sensor_features.parquet` | `te connectivity 3/processed/sensor/` | Sensor feature dataset (Machine 231) |

---

## 🛠️ Running the Model

### To retrain the base models:
```bash
python "te connectivity 3/scripts/retrain_base_model_v3.py"
python "te connectivity 3/scripts/per_machine_models_v3.py"
```

### To generate predictions/results:
```bash
python "te connectivity 3/scripts/regenerate_feb_results_v3.py"
```

### To build the latest v4.5f dataset:
```bash
python "te connectivity 3/scripts/build_future_dataset_v4.5f.py"
```

---

## 📊 Version Information
- **Current Stable Version**: v3.0 (February baseline)
- **Latest Work-in-Progress**: v4.5f (Multi-horizon forecasting)

---

## 📧 Support
If you have any questions or need access to the data, please contact the repository owner.
