# Manufacturing Scrap Prediction System (ML v4)

This repository contains the source code, backend API, and frontend dashboard for predicting manufacturing scrap events in real-time.

## 📦 1. Required Files from Google Drive

To keep the repository lightweight, large datasets, trained machine learning models, and secret environment variables are **not** hosted on GitHub. 

Before running the project, please download the required files from the **[Insert Google Drive Link Here]** and place them exactly as shown below:

- `models/` ➔ Place inside the `te connectivity 3/` directory.
- `new_processed_data/` ➔ Place inside the `te connectivity 3/` directory.
- `processed/` ➔ Place inside the `te connectivity 3/` directory.
- `.env` files ➔ Place inside `te connectivity 3/frontend/` and `te connectivity 3/backend/` (if provided in the drive).

---

## 🚀 2. Getting Started

### Prerequisites
- [Python 3.9+](https://www.python.org/downloads/) (for the backend and ML models)
- [Node.js & npm](https://nodejs.org/) (for the frontend dashboard)

### Backend Setup (Python API)
1. Open a terminal and navigate to the project directory:
   ```bash
   cd "te connectivity 3"
   ```
2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv .venv
   .\.venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the backend server:
   ```bash
   python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend Setup (Dashboard)
1. Open a **new, separate terminal** and navigate to the frontend directory:
   ```bash
   cd "te connectivity 3/frontend"
   ```
2. Install the Node.js dependencies:
   ```bash
   npm install
   ```
3. Start the frontend development server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to `http://localhost:3000` (or whichever port is shown in the terminal).

---

## 📂 Project Structure

- `te connectivity 3/`
  - `backend/`: FastAPI server, data access layers, and real-time scrap checkers.
  - `frontend/`: React dashboard for data visualization and root cause analysis.
  - `scripts/`: Data preprocessing, feature engineering, and ML training pipelines.
  - `models/`: *(From Google Drive)* Saved LightGBM models, scalers, and SHAP explainers.
  - `new_processed_data/` & `processed/`: *(From Google Drive)* Multi-horizon future datasets and generated baseline data.
