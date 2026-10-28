"""
Module M2 -- Crop Recommender training script
------------------------------------------------
RandomForestClassifier over the standard 7-feature crop dataset:
N, P, K, temperature, humidity, ph, rainfall -> one of 22 crops.
(As specified in the KrishiSense synopsis, Module design / M2.)

Trains on Crop_recommendation.csv (2200 rows, 22 crops), reports a
stratified hold-out accuracy, and saves:
  saved_models/crop_recommender_rf.pkl
  saved_models/crop_recommender_features.pkl   (feature column order)
  saved_models/crop_recommender_metrics.json   (hold-out accuracy etc.)

Run once at build time: `python train_crop_recommender.py`
"""
import json
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

CSV_PATH = "Crop_recommendation.csv"
MODEL_DIR = "saved_models"
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]

df = pd.read_csv(CSV_PATH)
df.columns = [c.strip() for c in df.columns]

X = df[FEATURES]
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

clf = RandomForestClassifier(
    n_estimators=200,
    max_depth=None,
    random_state=42,
    n_jobs=-1,
)
clf.fit(X_train, y_train)

y_pred = clf.predict(X_test)
acc = accuracy_score(y_test, y_pred)
report = classification_report(y_test, y_pred, output_dict=True)

print(f"Hold-out accuracy: {acc*100:.2f}%  (synopsis target: >=95%)")

import os
os.makedirs(MODEL_DIR, exist_ok=True)
joblib.dump(clf, os.path.join(MODEL_DIR, "crop_recommender_rf.pkl"))
joblib.dump(FEATURES, os.path.join(MODEL_DIR, "crop_recommender_features.pkl"))

with open(os.path.join(MODEL_DIR, "crop_recommender_metrics.json"), "w") as f:
    json.dump({
        "holdout_accuracy": acc,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "n_classes": int(y.nunique()),
        "classes": sorted(y.unique().tolist()),
    }, f, indent=2)

print(f"Saved model with {len(clf.classes_)} crop classes to {MODEL_DIR}/")
