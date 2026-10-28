"""
Evaluates the 5 crop-recommendation models supplied in
KrishiSense_Crop_Models.zip (random_forest, decision_tree, logistic,
polynomial_logistic, xgboost) on the SAME stratified hold-out split of
Crop_recommendation.csv, so their accuracy numbers are comparable --
mirrors how the price module's model_metrics.json was produced.

Writes saved_models/crop/crop_model_metrics.json, read by the crop
comparison page.
"""
import json
import os
import warnings
warnings.filterwarnings("ignore")

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score

CSV_PATH = "Crop_recommendation.csv"
MODEL_DIR = "saved_models/crop"

FEATURES = joblib.load(os.path.join(MODEL_DIR, "crop_features.pkl"))

df = pd.read_csv(CSV_PATH)
df.columns = [c.strip() for c in df.columns]
X = df[FEATURES]
y = df["label"]

# Same split params as train_crop_recommender.py, so numbers are apples-to-apples
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

MODEL_FILES = {
    "random_forest": "random_forest_crop_model.pkl",
    "decision_tree": "decision_tree_crop_model.pkl",
    "logistic_regression": "logistic_crop_model.pkl",
    "polynomial_logistic": "polynomial_logistic_crop_model.pkl",
    "xgboost": "xgboost_crop_model.pkl",
}

label_encoder = joblib.load(os.path.join(MODEL_DIR, "crop_label_encoder.pkl"))

metrics = {}
for key, fname in MODEL_FILES.items():
    path = os.path.join(MODEL_DIR, fname)
    if not os.path.exists(path):
        metrics[key] = {"available": False, "reason": "file not found"}
        continue
    try:
        model = joblib.load(path)
    except ModuleNotFoundError as e:
        metrics[key] = {"available": False, "reason": f"missing dependency: {e}"}
        continue

    try:
        y_pred = model.predict(X_test)
        # XGBoost's classifier here was trained on label-encoded integers
        if y_pred.dtype.kind in "iu":
            y_pred_labels = label_encoder.inverse_transform(y_pred)
        else:
            y_pred_labels = y_pred

        acc = accuracy_score(y_test, y_pred_labels)
        f1 = f1_score(y_test, y_pred_labels, average="macro")
        metrics[key] = {
            "available": True,
            "accuracy": round(float(acc) * 100, 2),
            "f1_macro": round(float(f1) * 100, 2),
        }
        print(f"{key:22s} accuracy={acc*100:.2f}%  f1_macro={f1*100:.2f}%")
    except Exception as e:
        metrics[key] = {"available": False, "reason": str(e)}
        print(f"{key:22s} FAILED: {e}")

with open(os.path.join(MODEL_DIR, "crop_model_metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)

print(f"\nSaved metrics to {MODEL_DIR}/crop_model_metrics.json")
