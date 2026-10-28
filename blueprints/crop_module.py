"""
Module M2 -- Crop Recommender (blueprint), v2
Serves all 5 algorithms from KrishiSense_Crop_Models.zip (Random Forest,
Decision Tree, Logistic Regression, Polynomial Logistic, XGBoost) against
the same 7 inputs, with a fallback to a self-trained RandomForest.

Also serves the Regional Crop Advisor: a RandomForest trained on real
Karnataka-region agricultural data (Location, Soil type, Irrigation,
Rainfall, Temperature, Humidity -> Crop), with observed yield/price
context per crop. See train_regional_advisor.py.
"""
import os
import json
import joblib
import numpy as np
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for

crop_bp = Blueprint("crop_bp", __name__)

CLIENT_MODEL_DIR = "saved_models/crop"
FALLBACK_MODEL_DIR = "saved_models"
REGIONAL_MODEL_DIR = "saved_models/regional_advisor"

MODEL_FILES = {
    "random_forest": "random_forest_crop_model.pkl",
    "decision_tree": "decision_tree_crop_model.pkl",
    "logistic_regression": "logistic_crop_model.pkl",
    "polynomial_logistic": "polynomial_logistic_crop_model.pkl",
    "xgboost": "xgboost_crop_model.pkl",
}
MODEL_LABELS = {
    "random_forest": "Random Forest",
    "decision_tree": "Decision Tree",
    "logistic_regression": "Logistic Regression",
    "polynomial_logistic": "Polynomial Logistic",
    "xgboost": "XGBoost",
}
PRIMARY_MODEL = "random_forest"

_models = {}
_features = None
_label_encoder = None
_metrics = None
_loaded = False


def _load():
    global _models, _features, _label_encoder, _metrics, _loaded
    if _loaded:
        return
    _loaded = True

    feat_path = os.path.join(CLIENT_MODEL_DIR, "crop_features.pkl")
    if os.path.exists(feat_path):
        _features = joblib.load(feat_path)
        le_path = os.path.join(CLIENT_MODEL_DIR, "crop_label_encoder.pkl")
        if os.path.exists(le_path):
            _label_encoder = joblib.load(le_path)

        for key, fname in MODEL_FILES.items():
            path = os.path.join(CLIENT_MODEL_DIR, fname)
            if not os.path.exists(path):
                continue
            try:
                _models[key] = joblib.load(path)
            except ModuleNotFoundError as e:
                print(f"[crop_module] {key} not loaded: {e}")

        metrics_path = os.path.join(CLIENT_MODEL_DIR, "crop_model_metrics.json")
        if os.path.exists(metrics_path):
            with open(metrics_path) as f:
                _metrics = json.load(f)

    if not _models:
        rf_path = os.path.join(FALLBACK_MODEL_DIR, "crop_recommender_rf.pkl")
        feat_fallback = os.path.join(FALLBACK_MODEL_DIR, "crop_recommender_features.pkl")
        if os.path.exists(rf_path) and os.path.exists(feat_fallback):
            _models["random_forest"] = joblib.load(rf_path)
            _features = joblib.load(feat_fallback)


# ------------------------------------------------------------
# Regional Crop Advisor (real Karnataka-region dataset)
# ------------------------------------------------------------
_regional_model = None
_regional_le = None
_regional_features = None
_regional_categories = None
_regional_crop_stats = None
_regional_metrics = None
_regional_loaded = False


def _load_regional():
    global _regional_model, _regional_le, _regional_features
    global _regional_categories, _regional_crop_stats, _regional_metrics, _regional_loaded
    if _regional_loaded:
        return
    _regional_loaded = True

    model_path = os.path.join(REGIONAL_MODEL_DIR, "regional_rf_model.pkl")
    if not os.path.exists(model_path):
        return

    try:
        _regional_model = joblib.load(model_path)
        _regional_le = joblib.load(os.path.join(REGIONAL_MODEL_DIR, "regional_label_encoder.pkl"))
        _regional_features = joblib.load(os.path.join(REGIONAL_MODEL_DIR, "regional_feature_columns.pkl"))
        with open(os.path.join(REGIONAL_MODEL_DIR, "regional_categories.json")) as f:
            _regional_categories = json.load(f)
        with open(os.path.join(REGIONAL_MODEL_DIR, "regional_crop_stats.json")) as f:
            _regional_crop_stats = json.load(f)
        with open(os.path.join(REGIONAL_MODEL_DIR, "regional_metrics.json")) as f:
            _regional_metrics = json.load(f)
    except Exception as e:
        print(f"[crop_module] Regional advisor not loaded: {e}")
        _regional_model = None


def _build_regional_row(location, soil_type, irrigation, rainfall, temperature, humidity):
    """One-hot encode categorical inputs to match the training feature columns."""
    row = {col: 0 for col in _regional_features}
    row["Rainfall"] = float(rainfall)
    row["Temperature"] = float(temperature)
    row["Humidity"] = float(humidity)

    soil_clean = " ".join(str(soil_type).strip().split())
    for col, value in (("Location", location), ("Soil type", soil_clean), ("Irrigation", irrigation)):
        key = f"{col}_{value}"
        if key in row:
            row[key] = 1
        # else: unseen category at inference -- leave as all-zero for that
        # group, which is the natural "unknown category" fallback for a
        # one-hot encoded RandomForest.

    return pd.DataFrame([row])[_regional_features]


def _predict_one(key, model, X):
    pred = model.predict(X)[0]
    proba_row = model.predict_proba(X)[0] if hasattr(model, "predict_proba") else None

    if isinstance(pred, (int, np.integer)) or (hasattr(pred, "dtype") and pred.dtype.kind in "iu"):
        label = _label_encoder.inverse_transform([pred])[0] if _label_encoder is not None else str(pred)
    else:
        label = pred

    confidence = float(np.max(proba_row)) if proba_row is not None else None
    return label, confidence


def _top3_from_model(key, model, X):
    proba_row = model.predict_proba(X)[0] if hasattr(model, "predict_proba") else None
    if proba_row is None:
        label, conf = _predict_one(key, model, X)
        return [{"crop": label, "confidence": round((conf or 0) * 100, 1)}]

    classes = model.classes_
    top_idx = np.argsort(proba_row)[::-1][:3]
    results = []
    for i in top_idx:
        c = classes[i]
        if isinstance(c, (int, np.integer)):
            c = _label_encoder.inverse_transform([c])[0] if _label_encoder is not None else str(c)
        results.append({"crop": c, "confidence": round(float(proba_row[i]) * 100, 1)})
    return results


@crop_bp.route("/crop", methods=["GET"])
def crop_form():
    if "user_id" not in session:
        return redirect(url_for("login"))
    _load()
    _load_regional()
    username = session.get("username", "User")
    return render_template(
        "crop_recommend.html",
        username=username,
        available_models=[MODEL_LABELS[k] for k in _models.keys()],
        regional_available=_regional_model is not None,
        regional_categories=_regional_categories or {"locations": [], "soil_types": [], "irrigation": []},
    )


@crop_bp.route("/api/predict-crop", methods=["POST"])
def api_predict_crop():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    _load()
    if not _models or _features is None:
        return jsonify({
            "error": "No crop model files found."
        }), 503

    data = request.get_json(silent=True) or request.form
    try:
        row = [float(data.get(f, 0)) for f in _features]
    except (TypeError, ValueError):
        return jsonify({"error": "All seven inputs (N, P, K, temperature, humidity, ph, rainfall) must be numeric."}), 400

    X = np.array([row])

    model_predictions = {}
    for key, model in _models.items():
        try:
            label, conf = _predict_one(key, model, X)
            model_predictions[key] = {
                "crop": label,
                "confidence": round((conf or 0) * 100, 1) if conf is not None else None,
            }
        except Exception as e:
            model_predictions[key] = {"error": str(e)}

    primary_key = PRIMARY_MODEL if PRIMARY_MODEL in _models else next(iter(_models))
    top3 = _top3_from_model(primary_key, _models[primary_key], X)

    limiting = None
    primary_model = _models[primary_key]
    if hasattr(primary_model, "feature_importances_"):
        limiting = _features[int(np.argmax(primary_model.feature_importances_))]

    best_model_key, best_acc = None, -1
    if _metrics:
        for key, m in _metrics.items():
            if m.get("available") and m.get("accuracy", -1) > best_acc:
                best_acc = m["accuracy"]
                best_model_key = key

    return jsonify({
        "top3": top3,
        "primary_model": MODEL_LABELS.get(primary_key, primary_key),
        "inputs": dict(zip(_features, row)),
        "limiting_parameter": limiting,
        "note": f"'{limiting}' most strongly separated this recommendation from the alternatives." if limiting else None,
        "model_predictions": model_predictions,
        "model_labels": MODEL_LABELS,
        "model_metrics": _metrics,
        "best_model": best_model_key,
    })


@crop_bp.route("/api/crop-model-metrics")
def api_crop_model_metrics():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    _load()
    return jsonify({
        "metrics": _metrics or {},
        "labels": MODEL_LABELS,
        "loaded": list(_models.keys()),
    })


@crop_bp.route("/api/predict-regional-crop", methods=["POST"])
def api_predict_regional_crop():
    """
    Regional Crop Advisor, trained on real Karnataka-region data
    (Location, Soil type, Irrigation, Rainfall, Temperature, Humidity).
    Sensor-fed fields (Rainfall/Temperature/Humidity) are designed to be
    pre-filled from a live telemetry reading once the hardware node is
    connected -- see Module M1/M5.
    """
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    _load_regional()
    if _regional_model is None:
        return jsonify({
            "error": "Regional advisor model not found. Run train_regional_advisor.py first."
        }), 503

    data = request.get_json(silent=True) or request.form
    required = ["location", "soil_type", "irrigation", "rainfall", "temperature", "humidity"]
    missing = [f for f in required if data.get(f) in (None, "")]
    if missing:
        return jsonify({"error": f"Missing required field(s): {', '.join(missing)}"}), 400

    try:
        rainfall = float(data.get("rainfall"))
        temperature = float(data.get("temperature"))
        humidity = float(data.get("humidity"))
    except (TypeError, ValueError):
        return jsonify({"error": "Rainfall, temperature, and humidity must be numeric."}), 400

    location = str(data.get("location"))
    soil_type = str(data.get("soil_type"))
    irrigation = str(data.get("irrigation"))

    X = _build_regional_row(location, soil_type, irrigation, rainfall, temperature, humidity)

    proba_row = _regional_model.predict_proba(X)[0]
    classes = _regional_model.classes_
    top_idx = np.argsort(proba_row)[::-1][:3]

    top3 = []
    for i in top_idx:
        crop_name = _regional_le.inverse_transform([classes[i]])[0]
        stats = (_regional_crop_stats or {}).get(crop_name, {})
        top3.append({
            "crop": crop_name,
            "confidence": round(float(proba_row[i]) * 100, 1),
            "avg_yield": stats.get("avg_yield"),
            "yield_range": [stats.get("min_yield"), stats.get("max_yield")],
            "avg_price": stats.get("avg_price"),
            "price_range": [stats.get("min_price"), stats.get("max_price")],
            "common_locations": stats.get("common_locations", []),
            "sample_count": stats.get("sample_count"),
        })

    limiting = None
    if hasattr(_regional_model, "feature_importances_"):
        idx = int(np.argmax(_regional_model.feature_importances_))
        limiting = _regional_features[idx]

    return jsonify({
        "top3": top3,
        "inputs": {
            "location": location, "soil_type": soil_type, "irrigation": irrigation,
            "rainfall": rainfall, "temperature": temperature, "humidity": humidity,
        },
        "limiting_parameter": limiting,
        "model_metrics": _regional_metrics,
        "trained_on": (_regional_metrics or {}).get("n_samples"),
    })


@crop_bp.route("/api/regional-categories")
def api_regional_categories():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    _load_regional()
    return jsonify(_regional_categories or {"locations": [], "soil_types": [], "irrigation": []})
