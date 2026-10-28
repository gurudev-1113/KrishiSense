"""
Regional Crop Advisor -- trains a crop recommender on real Karnataka-region
agricultural data (data/karnataka_crop_data.csv), instead of the generic
7-feature N/P/K dataset used by the existing crop_bp models.

Inputs used for the recommendation:
    Location, Soil type, Irrigation (categorical)
    Rainfall, Temperature, Humidity (numeric)
Target:
    Crops (13 classes)

Also computes, per crop, the observed yield and price distribution from the
same dataset, so the UI can show "what to expect" alongside the
recommendation (e.g. typical yield, typical mandi price range) without
needing a second model.

Run this script from the project root:
    python train_regional_advisor.py

Outputs (into saved_models/regional_advisor/):
    regional_rf_model.pkl        -- trained RandomForestClassifier
    regional_label_encoder.pkl   -- LabelEncoder for the Crops target
    regional_feature_columns.pkl -- ordered list of one-hot + numeric feature columns
    regional_categories.json     -- valid Location / Soil type / Irrigation values (for dropdowns)
    regional_crop_stats.json     -- per-crop avg/min/max yield and price
    regional_metrics.json        -- train/test accuracy, confusion summary
"""
import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score

DATA_PATH = "data/karnataka_crop_data.csv"
OUT_DIR = "saved_models/regional_advisor"
os.makedirs(OUT_DIR, exist_ok=True)


def clean_soil(s):
    if pd.isna(s):
        return "Unknown"
    return " ".join(str(s).strip().split())  # collapse internal/edge whitespace


def main():
    df = pd.read_csv(DATA_PATH)
    df["Soil type"] = df["Soil type"].apply(clean_soil)
    df["Location"] = df["Location"].astype(str).str.strip()
    df["Irrigation"] = df["Irrigation"].astype(str).str.strip()
    df["Crops"] = df["Crops"].astype(str).str.strip()

    categorical_cols = ["Location", "Soil type", "Irrigation"]
    numeric_cols = ["Rainfall", "Temperature", "Humidity"]

    X_cat = pd.get_dummies(df[categorical_cols], prefix=categorical_cols)
    X_num = df[numeric_cols].astype(float)
    X = pd.concat([X_num, X_cat], axis=1)
    feature_columns = X.columns.tolist()

    le = LabelEncoder()
    y = le.fit_transform(df["Crops"])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    train_acc = accuracy_score(y_train, model.predict(X_train))
    test_acc = accuracy_score(y_test, model.predict(X_test))
    test_f1 = f1_score(y_test, model.predict(X_test), average="macro")

    print(f"Train accuracy: {train_acc:.4f}")
    print(f"Test accuracy:  {test_acc:.4f}")
    print(f"Test macro-F1:  {test_f1:.4f}")

    # Refit on ALL data for the deployed model (small dataset; more signal beats a
    # held-out slice once we've already reported honest test-set metrics above).
    model.fit(X, y)

    joblib.dump(model, os.path.join(OUT_DIR, "regional_rf_model.pkl"))
    joblib.dump(le, os.path.join(OUT_DIR, "regional_label_encoder.pkl"))
    joblib.dump(feature_columns, os.path.join(OUT_DIR, "regional_feature_columns.pkl"))

    categories = {
        "locations": sorted(df["Location"].unique().tolist()),
        "soil_types": sorted(df["Soil type"].unique().tolist()),
        "irrigation": sorted(df["Irrigation"].unique().tolist()),
    }
    with open(os.path.join(OUT_DIR, "regional_categories.json"), "w") as f:
        json.dump(categories, f, indent=2)

    crop_stats = {}
    for crop, g in df.groupby("Crops"):
        crop_stats[crop] = {
            "avg_yield": round(float(g["yeilds"].mean()), 1),
            "min_yield": round(float(g["yeilds"].min()), 1),
            "max_yield": round(float(g["yeilds"].max()), 1),
            "avg_price": round(float(g["price"].mean()), 2),
            "min_price": round(float(g["price"].min()), 2),
            "max_price": round(float(g["price"].max()), 2),
            "sample_count": int(len(g)),
            "common_locations": g["Location"].value_counts().head(3).index.tolist(),
            "common_soil": g["Soil type"].value_counts().head(3).index.tolist(),
        }
    with open(os.path.join(OUT_DIR, "regional_crop_stats.json"), "w") as f:
        json.dump(crop_stats, f, indent=2)

    metrics = {
        "train_accuracy": round(train_acc, 4),
        "test_accuracy": round(test_acc, 4),
        "test_macro_f1": round(test_f1, 4),
        "n_samples": int(len(df)),
        "n_features": len(feature_columns),
        "n_classes": len(le.classes_),
        "classes": le.classes_.tolist(),
    }
    with open(os.path.join(OUT_DIR, "regional_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nSaved regional advisor artifacts to {OUT_DIR}/")


if __name__ == "__main__":
    main()
