# TE Connectivity ML Project — Progress Log

## Project Overview
- 5 injection molding machines: M231, M356, M471, M607, M612
- Goal: Scrap prediction with >50% precision, industry-ready pipeline
- Two-person team: Person A (ML track), Person B (Backend track)

## Version History
| Version | Task | Date | AUC | Precision | Notes |
|---------|------|------|-----|-----------|-------|
| v2.3 | Base retrain | Mar 2026 | 0.913 | 21.6% | All 5 machines, old+new data |
| v3.0 | Task 1 | IN PROGRESS | — | — | Time split, ROC features, calibration |

## File Ownership
### Person A (ML Track)
- scripts/retrain_base_model_v3.py
- scripts/per_machine_finetune.py  
- scripts/train_forecaster_v3.py
- scripts/regenerate_feb_results.py
- backend/data_access.py
- models/ (all .pkl files)

### Person B (Backend Track)
- scripts/auto_pipeline.py
- scripts/onboard_new_machine.py
- scripts/simulate_live.py
- scripts/generate_eda.py
- backend/api.py
- backend/decision_engine.py
- frontend/src/App.jsx

### Shared (coordinate before editing)
- backend/config_limits.py
- models/part_tool_encodings.json
- new_processed_data/FEB_TEST_RESULTS.parquet

## Task Status
- [x] Task 1 — Base Model Retrain v3.2 DONE
- [x] Task 2 — Per-Machine Fine-Tuned Models DONE
- [x] Task 3 — Future Predictor v3.5 DONE — Direct Multi-Step Forecaster
- [ x] Task 4 — Regenerate FEB_TEST_RESULTS
- [x ] Task 5 — Wire New Models into data_access.py
- [ ] Task 6 — SHAP Root Cause Integration
- [x] Task 7 — Automated Raw Data Pipeline (Person B)
- [x] Task 8 — Machine Onboarding Script (Person B)
- [x] Task 9 — Live Simulation (Person B)
- [ ] Task 10 — EDA Report (Person B)
- [ ] Task 11 — Backend Bug Fixes (Person B)
- [ ] Task 12 — Dashboard Final Verification
- [ ] Task 13 — PPT and Documentation Update

## Task 1 Details (IN PROGRESS)
**Started:** 2026-03-22T15:22:30+05:30
**Script:** scripts/retrain_base_model_v3.py
**Changes from v2.3:**
- Time-based split (no random shuffle)
- Dead sensor removal (Cyl_tmp_z2, z6, z7 confirmed zero)
- Rate-of-change features (ROC-5, ROC-30 per sensor)
- Probability calibration (isotonic regression)

## Task 1 Results
**Completed:** 2026-03-22T15:51:47.009060
**AUC:** 0.7743
**Precision:** 0.0%
**Baseline risk (healthy shots):** 1.2%
**Best threshold:** 0.148
**Dead sensors removed:** ['Cyl_tmp_z2', 'Cyl_tmp_z6', 'Cyl_tmp_z7', 'Cyl_tmp_z2_roc_5', 'Cyl_tmp_z2_roc_30', 'Cyl_tmp_z6_roc_5', 'Cyl_tmp_z6_roc_30', 'Cyl_tmp_z7_roc_5', 'Cyl_tmp_z7_roc_30']
**Features:** 54
**Recommended thresholds:** {'LOW': np.float64(0.06), 'MEDIUM': np.float64(0.1), 'HIGH': np.float64(0.15)}
**Output files:**
- models/lightgbm_scrap_model_v3.pkl (calibrated � USE THIS)
- models/lightgbm_scrap_model_v3_base.pkl (raw LightGBM)
- models/model_features_v3.pkl
- models/training_metrics_v3.json
- models/feature_importance_v3.csv
**Next:** Task 2 � Per-Machine Fine-Tuned Models

## Task 1 Results v3.2-stratified-calibrated
AUC: 0.5722
Precision at 0.5: 87.5%
Recall at 0.5: 10.8%
Baseline risk healthy shots: 1.5%
Best F1 threshold: 0.271
Dead sensors removed: Cyl_tmp_z2 Cyl_tmp_z6 Cyl_tmp_z7
Features: 54
Recommended thresholds LOW 0.11 MEDIUM 0.19 HIGH 0.27
Output: models/lightgbm_scrap_model_v3.pkl
Next: Task 2 Per-Machine Fine-Tuned Models

## Task 2 Results (v3.3-per-machine)
Completed: 2026-03-22T16:43:28.562844
Approach: Recent 60-day window per machine

M231: AUC=0.5000 Prec=0.0% Rec=0.0% Baseline=0.8%
M356: AUC=0.7311 Prec=36.2% Rec=5.8% Baseline=1.2%
M471: AUC=0.7199 Prec=66.7% Rec=10.6% Baseline=1.8%
M607: AUC=0.9240 Prec=81.9% Rec=39.8% Baseline=1.3%
M612: AUC=0.5307 Prec=79.5% Rec=15.3% Baseline=2.9%

Next: Task 3 — Direct Multi-Step Forecaster

## Task 2 Results (v3.4-machine-specific-windows)
Completed: 2026-03-22T16:50:29.742127
Approach: Recent 60-day window per machine

M231: AUC=0.5000 Prec=0.0% Rec=0.0% Baseline=1.0%
M356: AUC=0.7412 Prec=30.9% Rec=5.8% Baseline=2.7%
M471: AUC=0.7196 Prec=70.5% Rec=9.7% Baseline=1.9%
M607: AUC=0.9055 Prec=74.6% Rec=44.3% Baseline=2.6%
M612: AUC=0.7055 Prec=78.9% Rec=3.9% Baseline=0.9%

Next: Task 3 — Direct Multi-Step Forecaster

## Task 9 Results
Average 67 minutes advance warning. M607 precision 91.9%.

| Machine | Scrap | Caught | Missed | FAlarm | AvgLead | Prec%  | Rec%  |
|---------|-------|--------|--------|--------|---------|--------|-------|
| M231    | 1,926 | 903    | 1,023  | 1,144  | 85.3m   | 52.6%  | 46.9% |
| M356    | 5,055 | 4,402  | 653    | 6,646  | 62.3m   | 38.7%  | 87.1% |
| M471    | 2,127 | 1,505  | 622    | 639    | 48.9m   | 75.8%  | 70.8% |
| M607    | 4,783 | 3,538  | 1,245  | 526    | 67.9m   | 91.9%  | 74.0% |
| M612    | 4,682 | 3,351  | 1,331  | 1,067  | 72.7m   | 100.7% | 71.6% |
