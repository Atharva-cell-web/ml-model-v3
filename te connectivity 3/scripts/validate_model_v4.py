import pandas as pd
import joblib
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score

print("Loading dataset...")

df = pd.read_parquet("new_processed_data/cleaned_dataset_v4.parquet")

print("Dataset shape:", df.shape)

scrap_ratio = df["future_scrap"].mean()
print("Scrap ratio:", scrap_ratio)

# ------------------------------
# TIME BASED SPLIT
# ------------------------------

print("\nRunning time-based validation...")

split_index = int(len(df) * 0.8)

train_df = df.iloc[:split_index]
val_df = df.iloc[split_index:]

X_train = train_df.drop(columns=["future_scrap"])
y_train = train_df["future_scrap"]

X_val = val_df.drop(columns=["future_scrap"])
y_val = val_df["future_scrap"]

print("Train rows:", len(X_train))
print("Validation rows:", len(X_val))

# ------------------------------
# LOAD MODEL
# ------------------------------

print("\nLoading trained model...")

model = joblib.load("models/scrap_risk_model_v4.pkl")

# ------------------------------
# PREDICTIONS
# ------------------------------

print("\nRunning predictions...")

preds = model.predict(X_val)

# ------------------------------
# METRICS
# ------------------------------

auc = roc_auc_score(y_val, preds)

threshold = 0.5
pred_labels = (preds > threshold).astype(int)

precision = precision_score(y_val, pred_labels)
recall = recall_score(y_val, pred_labels)
f1 = f1_score(y_val, pred_labels)

print("\nTime Split Metrics")
print("------------------")
print("AUC:", auc)
print("Precision:", precision)
print("Recall:", recall)
print("F1:", f1)

# ------------------------------
# CORRELATION CHECK
# ------------------------------

print("\nChecking top correlated features...")

corr = df.corr()["future_scrap"].abs().sort_values(ascending=False)

print(corr.head(20))

# ------------------------------
# FEATURE IMPORTANCE CHECK
# ------------------------------

print("\nChecking feature importance...")

fi = pd.read_csv("features/feature_importance_v4.csv")

print(fi.head(20))

print("\nValidation complete.")