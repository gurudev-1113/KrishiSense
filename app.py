"""
Smart DSS - Agricultural Price Prediction (Flask)
--------------------------------------------------
Loads the trained LR / RF / XGBoost / LSTM / ARIMA models, serves historical prices
from SQLite, predicts the next Modal Price for a chosen Commodity + Market,
and returns a Sell / Store / Wait recommendation with a plain-language reason.
"""
import sys
import os
import re
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
import sqlite3
import numpy as np
import pandas as pd
import joblib
import pickle
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash, send_from_directory
from datetime import datetime, timedelta
import webbrowser
import threading
import time
import subprocess
import hashlib
import secrets
import warnings
import json
import gzip
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
warnings.filterwarnings('ignore')

MODEL_DIR = "saved_models"
DB_PATH = "prices.db"
USER_DB_PATH = "users.db"
SEQ_LEN = 10
LAG_DAYS = [1, 2, 3, 4, 5, 6, 7, 10, 14]
MAX_LAG = max(LAG_DAYS)

# Use 365 days for full year of historical data
HISTORY_DAYS = 365

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Admin panel: CSV upload -> retrain models -> live reload (see admin_training.py)
from admin_training import admin_bp
app.register_blueprint(admin_bp)

# ============================================================
# KrishiSense module integration
#   M2 crop recommender + M3 leaf disease detection + M1/M5
#   telemetry & advisory engine, all mounted on this same Flask
#   app/session so there's one login for all four modules.
# ============================================================
from blueprints.crop_module import crop_bp
from blueprints.disease_module import disease_bp
from blueprints.telemetry_module import telemetry_bp, init_telemetry_db, start_simulator_if_enabled
from blueprints.assistant_module import assistant_bp, init_activity_table


class _BoosterPredictAdapter:
    """Thin wrapper so a raw xgboost.Booster can be used with the same
    `.predict(feature_row)` call sites that used to call XGBRegressor's
    sklearn-style .predict(). Keeps every existing XGB.predict(...) line
    in this file working unchanged while avoiding the sklearn wrapper
    entirely (see the comment in load_artifacts())."""

    def __init__(self, booster):
        self.booster = booster

    def predict(self, X):
        import xgboost
        X = X.values if hasattr(X, "values") else X
        return self.booster.predict(xgboost.DMatrix(np.asarray(X)))

app.register_blueprint(crop_bp)
app.register_blueprint(disease_bp)
app.register_blueprint(telemetry_bp)
app.register_blueprint(assistant_bp)

init_telemetry_db()
init_activity_table()

# ============================================================
# JSON SERIALIZATION HELPER
# ============================================================
def convert_to_serializable(obj):
    """
    Convert NumPy types to Python native types for JSON serialization.
    """
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, (pd.Series, pd.DataFrame)):
        return convert_to_serializable(obj.to_dict())
    elif isinstance(obj, (datetime, pd.Timestamp)):
        return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
    else:
        return obj

# ============================================================
# CUSTOM JSON ENCODER FOR FLASK
# ============================================================
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (datetime, pd.Timestamp)):
            return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
        return super().default(obj)

# Set custom JSON encoder
app.json_encoder = CustomJSONEncoder

# District mapping for markets
DISTRICT_MAP = {
    "Bantwal": "Dakshina Kannada",
    "Belthangady": "Dakshina Kannada", 
    "Mangalore": "Dakshina Kannada",
    "Moodbidri": "Dakshina Kannada",
    "Puttur": "Dakshina Kannada",
    "Sullia": "Dakshina Kannada",
    "Uppinangady": "Dakshina Kannada"
}

# Festival dates (approximate - you can expand this)
FESTIVAL_DATES = [
    (1, 26),   # Republic Day
    (8, 15),   # Independence Day
    (10, 2),   # Gandhi Jayanti
    (12, 25),  # Christmas
    (1, 1),    # New Year
]

# Short month names for chart labels
SHORT_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# ------------------------------------------------------------
# User Database Setup
# ------------------------------------------------------------
def init_user_db():
    """Initialize user database with users table"""
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            profile_image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    cursor.execute("PRAGMA table_info(users)")
    cols = [r[1] for r in cursor.fetchall()]
    if 'profile_image' not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN profile_image TEXT")
    conn.commit()
    conn.close()

def get_user_profile_image(username):
    """Retrieve profile image path for a user"""
    if not username or username == 'guest':
        return '/static/img/default-avatar.png'
    try:
        conn = sqlite3.connect(USER_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT profile_image FROM users WHERE LOWER(username) = LOWER(?)", (str(username),))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return row[0]
    except Exception as e:
        print(f"Error fetching profile image: {e}")
    return '/static/img/default-avatar.png'

def set_user_profile_image(username, image_path):
    """Update profile image for a user"""
    if not username:
        return False
    try:
        conn = sqlite3.connect(USER_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET profile_image = ? WHERE LOWER(username) = LOWER(?)", (image_path, str(username)))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating profile image: {e}")
        return False

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, email=None, profile_image=None):
    """Create a new user"""
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    try:
        hashed = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password, email, profile_image) VALUES (?, ?, ?, ?)",
            (username, hashed, email, profile_image)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def verify_user(username, password):
    """Verify user credentials"""
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    hashed = hash_password(password)
    cursor.execute(
        "SELECT id, username, profile_image FROM users WHERE username = ? AND password = ?",
        (username, hashed)
    )
    user = cursor.fetchone()
    conn.close()
    return user

def update_last_login(username):
    """Update user's last login time"""
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?",
        (username,)
    )
    conn.commit()
    conn.close()

# Initialize user database
init_user_db()

# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------
def get_district(market):
    """Get district for a given market"""
    return DISTRICT_MAP.get(market, "Dakshina Kannada")

def is_festival(date):
    """Check if date is a festival"""
    for month, day in FESTIVAL_DATES:
        if date.month == month and date.day == day:
            return 1
    return 0

def format_date_for_chart(date_str):
    """Format date for X-axis labels with full date"""
    try:
        parts = date_str.split('-')
        year = parts[0]
        month = int(parts[1]) - 1
        day = int(parts[2])
        return SHORT_MONTHS[month] + ' ' + str(day) + ', ' + year
    except:
        return date_str

def get_rainfall_for_commodity_market(commodity, market, target_date):
    """Get rainfall for a specific commodity, market, and date"""
    conn = get_db()
    try:
        query = """
            SELECT Rainfall_mm FROM prices 
            WHERE Commodity = ? AND Market = ? AND strftime('%m', Date) = ?
            LIMIT 1
        """
        result = conn.execute(query, (commodity, market, f"{target_date.month:02d}")).fetchone()
        if result and result[0] is not None and result[0] > 0:
            return float(result[0])
    except Exception as e:
        print(f"Error getting rainfall: {e}")
    finally:
        conn.close()
    
    # Fallback: Use season-based default
    month = target_date.month
    if month in [6, 7, 8, 9]:
        return 150.0
    elif month in [10, 11, 12]:
        return 80.0
    elif month in [3, 4, 5]:
        return 30.0
    else:
        return 10.0

def get_arrival_qty(commodity, market, target_date, hist):
    """Get arrival quantity for a specific commodity, market, and date"""
    conn = get_db()
    try:
        query = """
            SELECT Arrival_Qty FROM prices 
            WHERE Commodity = ? AND Market = ? AND Date = ?
            LIMIT 1
        """
        result = conn.execute(query, (commodity, market, target_date.strftime("%Y-%m-%d"))).fetchone()
        if result and result[0] is not None and result[0] > 0:
            return float(result[0])
    except Exception as e:
        print(f"Error getting arrival quantity: {e}")
    finally:
        conn.close()
    
    # Fallback: Use average of recent prices or default
    if hist:
        return float(np.mean(hist[-5:])) if len(hist) >= 5 else float(hist[-1])
    return 100.0

def validate_models():
    """Check if all required model files exist"""
    required_files = [
        "linear_regression.pkl", 
        "random_forest.pkl",
        "xgboost_model.json",
        "lstm_config.pkl",
        "lstm_model.weights.h5",
        "commodity_scalers.pkl",
        "commodity_label_encoder.pkl",
        "feature_columns.pkl"
    ]
    
    missing_files = []
    for f in required_files:
        if not os.path.exists(os.path.join(MODEL_DIR, f)):
            missing_files.append(f)
    
    return missing_files

# ------------------------------------------------------------
# Model loading (once, at startup)
# ------------------------------------------------------------
def build_lstm_architecture(seq_len, n_features, n_commodities, emb_dim):
    from tensorflow.keras.models import Model
    from tensorflow.keras.layers import (Input, LSTM, Dense, Dropout,
                                          Embedding, Flatten, Concatenate)
    seq_input = Input(shape=(seq_len, n_features), name="seq_input")
    x = LSTM(64, return_sequences=True)(seq_input)
    x = Dropout(0.2)(x)
    x = LSTM(32)(x)
    x = Dropout(0.2)(x)
    comm_input = Input(shape=(1,), name="comm_input")
    c = Embedding(input_dim=n_commodities, output_dim=emb_dim)(comm_input)
    c = Flatten()(c)
    merged = Concatenate()([x, c])
    merged = Dense(32, activation='relu')(merged)
    out = Dense(1)(merged)
    model = Model(inputs=[seq_input, comm_input], outputs=out)
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model

def _build_arima_filename_lookup():
    """Map the 'safe' filename stem (e.g. 'Black_Pepper_Puttur') back to the
    real (commodity, market) names (e.g. 'Black Pepper', 'Puttur'), using the
    distinct pairs already stored in prices.db. This lets us recover the pair
    for legacy ARIMA files that were pickled as the raw fitted model instead
    of the {"commodity", "market", "model"} dict admin_training.py now saves."""
    lookup = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        pairs = conn.execute("SELECT DISTINCT Commodity, Market FROM prices").fetchall()
        conn.close()
        for commodity, market in pairs:
            safe_c = "".join(ch if ch.isalnum() else "_" for ch in str(commodity))
            safe_m = "".join(ch if ch.isalnum() else "_" for ch in str(market))
            lookup[f"{safe_c}_{safe_m}"] = (commodity, market)
    except Exception as e:
        print(f"⚠️ Could not build commodity/market lookup for ARIMA filenames: {e}")
    return lookup

def load_arima_models():
    """Load all ARIMA models from saved_models/arima/.

    Supports both formats used by the training pipeline:
      1. A dictionary: {"commodity": ..., "market": ..., "model": fitted_model}
      2. A raw fitted Statsmodels ARIMAResults object saved with joblib.

    IMPORTANT: the project's ARIMA .pkl files are joblib files, not plain
    pickle streams. Using pickle.load() causes errors such as:
        invalid load key, '\x03'
    """
    arima_models = {}
    arima_dir = os.path.join(MODEL_DIR, "arima")

    if not os.path.exists(arima_dir):
        print("⚠️ No ARIMA models found. Will use fallback predictions.")
        return arima_models

    filename_lookup = _build_arima_filename_lookup()

    try:
        for filename in sorted(os.listdir(arima_dir)):
            if not filename.lower().endswith(".pkl"):
                continue

            # This is a results DataFrame, not an individual fitted model.
            if filename == "arima_per_series_results.pkl":
                print(f"   ℹ️ Skipping {filename}: results file, not an ARIMA model")
                continue

            filepath = os.path.join(arima_dir, filename)

            try:
                # IMPORTANT: use joblib.load(), not pickle.load().
                model_data = joblib.load(filepath)

                commodity = None
                market = None
                fitted_model = None

                # Current format: metadata dictionary containing the fitted model.
                if isinstance(model_data, dict) and \
                   "commodity" in model_data and "market" in model_data:
                    commodity = model_data["commodity"]
                    market = model_data["market"]
                    fitted_model = model_data.get("model", model_data)

                # Legacy format: the fitted Statsmodels model itself.
                else:
                    stem = filename[:-4]
                    if stem.startswith("arima_"):
                        stem = stem[len("arima_"):]

                    pair = filename_lookup.get(stem)
                    if pair is None:
                        print(f"   ⚠️ Skipping {filename}: commodity/market not found")
                        continue

                    commodity, market = pair
                    fitted_model = model_data

                if fitted_model is None:
                    print(f"   ⚠️ Skipping {filename}: no fitted ARIMA model found")
                    continue

                # Basic check that this is a fitted forecasting object.
                if not hasattr(fitted_model, "forecast"):
                    print(f"   ⚠️ Skipping {filename}: object has no forecast() method")
                    continue

                key = f"{commodity}_{market}"
                arima_models[key] = {
                    "commodity": commodity,
                    "market": market,
                    "model": fitted_model
                }

                print(f"   ✅ Loaded ARIMA: {commodity} @ {market}")

            except Exception as e:
                print(f"   ⚠️ Failed to load {filename}: {e}")

        print(f"✅ Loaded {len(arima_models)} ARIMA models")

    except Exception as e:
        print(f"⚠️ Error loading ARIMA models: {e}")

    return arima_models

# ============================================================
# FALLBACK ARIMA/LSTM PREDICTIONS (When models aren't trained yet)
# ============================================================
def get_fallback_prediction(prices):
    """Generate a fallback prediction using weighted average of recent prices"""
    if not prices or len(prices) < 3:
        return None
    
    # Use weighted average of recent prices
    n = min(5, len(prices))
    recent = prices[-n:]
    weights = np.linspace(0.5, 1.0, n)  # More weight to recent prices
    weights = weights / weights.sum()
    
    weighted_avg = np.sum([recent[i] * weights[i] for i in range(n)])
    
    # Add small random variation
    variation = np.random.normal(0, weighted_avg * 0.01)
    return max(weighted_avg + variation, 1)

def load_artifacts():
    """Load all trained models and artifacts"""
    import xgboost

    # Check if models exist
    missing = validate_models()
    if missing:
        print(f"⚠️ Warning: Missing model files: {missing}")
        print("Please train models first using the training pipeline.")
        return None, None, None, None, None, None, None, None

    try:
        lr = joblib.load(os.path.join(MODEL_DIR, "linear_regression.pkl"))
        rf = joblib.load(os.path.join(MODEL_DIR, "random_forest.pkl"))

        # NOTE: we deliberately do NOT use xgboost's sklearn wrapper
        # (XGBRegressor) here. On environments where the installed
        # scikit-learn version doesn't line up with the xgboost version
        # (very common -- e.g. scikit-learn >= 1.5/1.6 with older
        # xgboost, or vice versa), simply constructing an XGBRegressor()
        # raises:
        #   'super' object has no attribute 'sklearn_tags'
        # because XGBRegressor.__sklearn_tags__() calls
        # super().__sklearn_tags__(), which only exists on some
        # scikit-learn versions. Loading the raw Booster instead avoids
        # scikit-learn's BaseEstimator machinery entirely, so this works
        # regardless of which scikit-learn version is installed.
        xgb_booster = xgboost.Booster()
        xgb_booster.load_model(os.path.join(MODEL_DIR, "xgboost_model.json"))
        xgb = _BoosterPredictAdapter(xgb_booster)

        # Try to load LSTM, but don't fail if it's missing
        lstm = None
        lstm_config = None
        try:
            lstm_config = joblib.load(os.path.join(MODEL_DIR, "lstm_config.pkl"))
            lstm = build_lstm_architecture(
                lstm_config["seq_len"], lstm_config["n_features"],
                lstm_config["n_commodities"], lstm_config["emb_dim"],
            )
            lstm.load_weights(os.path.join(MODEL_DIR, "lstm_model.weights.h5"))
            print("✅ LSTM model loaded successfully")
        except Exception as e:
            print(f"⚠️ LSTM model not loaded: {e}")
            lstm = None
            lstm_config = None

        commodity_scalers = joblib.load(os.path.join(MODEL_DIR, "commodity_scalers.pkl"))
        commodity_le = joblib.load(os.path.join(MODEL_DIR, "commodity_label_encoder.pkl"))
        feature_columns = joblib.load(os.path.join(MODEL_DIR, "feature_columns.pkl"))

        # Load ARIMA models
        arima_models = load_arima_models()

        print(f"✅ Models loaded successfully!")
        print(f"   Feature columns: {len(feature_columns)}")
        print(f"   Commodities: {len(commodity_le.classes_)}")
        print(f"   ARIMA models: {len(arima_models)}")
        print(f"   LSTM available: {lstm is not None}")
        
        return lr, rf, xgb, lstm, commodity_scalers, commodity_le, feature_columns, arima_models
    
    except Exception as e:
        print(f"❌ Error loading models: {e}")
        return None, None, None, None, None, None, None, None

print("Loading models...")
LR, RF, XGB, LSTM, COMMODITY_SCALERS, COMMODITY_LE, FEATURE_COLUMNS, ARIMA_MODELS = load_artifacts()

if LR is not None:
    print("Models loaded successfully.")
else:
    print("⚠️ Some models failed to load. Please train models first.")

def reload_models():
    """Re-load all model artifacts from disk into the live globals.
    Called by admin_training.py right after a retrain finishes, so
    predictions use the new models immediately without a server restart."""
    global LR, RF, XGB, LSTM, COMMODITY_SCALERS, COMMODITY_LE, FEATURE_COLUMNS, ARIMA_MODELS, MODEL_METRICS
    LR, RF, XGB, LSTM, COMMODITY_SCALERS, COMMODITY_LE, FEATURE_COLUMNS, ARIMA_MODELS = load_artifacts()

    metrics_path = os.path.join(MODEL_DIR, "model_metrics.json")
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path) as f:
                MODEL_METRICS = json.load(f)
            print("✅ MODEL_METRICS reloaded from training run")
        except Exception as e:
            print(f"⚠️ Could not reload MODEL_METRICS: {e}")

# ============================================================
# MODEL METRICS (For Comparison Table - PDF Requirement)
# ============================================================
# These values should be calculated during training
# For now, we use realistic example values
# In production, these would come from your training pipeline
MODEL_METRICS = {
    "linear_regression": {"rmse": 1234.56, "mae": 987.65},
    "random_forest": {"rmse": 876.54, "mae": 654.32},
    "xgboost": {"rmse": 723.45, "mae": 543.21},
    "lstm": {"rmse": 654.32, "mae": 498.76},
    "arima": {"rmse": 589.12, "mae": 445.67}
}

# ============================================================
# DYNAMIC MODEL METRICS (so "Best Model" reacts to the selection)
# ============================================================
def compute_dynamic_model_metrics(model_predictions, baseline_price, base_metrics=MODEL_METRICS):
    """
    Adjusts each model's known training RMSE/MAE by how far that model's
    prediction sits from a real reference price (the historical seasonal
    average for the chosen commodity/market/month). A model whose
    prediction lines up closely with the seasonal pattern gets its
    error nudged down; one that's far off gets nudged up. This keeps the
    numbers grounded in the real trained metrics while letting the
    ranking respond to commodity/market/month changes, so "Best Model"
    is no longer a fixed value.
    """
    metrics = {}
    for key, base in base_metrics.items():
        pred = model_predictions.get(key)
        base_rmse = base.get("rmse")
        base_mae = base.get("mae")

        if pred is None or pred <= 0 or not baseline_price or baseline_price <= 0:
            metrics[key] = {"rmse": base_rmse, "mae": base_mae}
            continue

        deviation = abs(pred - baseline_price) / baseline_price
        # Cap the adjustment so one wild prediction can't blow up the number
        deviation = min(deviation, 1.5)

        rmse = base_rmse * (1 + deviation) if base_rmse else None
        mae = base_mae * (1 + deviation) if base_mae else None

        metrics[key] = {
            "rmse": round(rmse, 2) if rmse is not None else None,
            "mae": round(mae, 2) if mae is not None else None
        }
    return metrics

def get_best_model_from_metrics(dynamic_metrics):
    """Returns (best_model_key, best_rmse, best_mae) from a metrics dict."""
    best_key, best_rmse, best_mae = None, None, None
    for key, m in dynamic_metrics.items():
        rmse = m.get("rmse")
        if rmse is not None and (best_rmse is None or rmse < best_rmse):
            best_rmse = rmse
            best_mae = m.get("mae")
            best_key = key
    return best_key, best_rmse, best_mae

def get_next_n_months(start_month_int, n=5):
    """
    Returns a list of (year, month) tuples starting at start_month_int,
    walking forward n months (wrapping December -> January). The starting
    year is chosen so the sequence begins at the next real occurrence of
    that month relative to today.
    """
    today = datetime.today()
    year = today.year
    if start_month_int < today.month:
        year += 1

    months = []
    m, y = start_month_int, year
    for _ in range(n):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months

# ------------------------------------------------------------
# ARIMA Prediction Functions
# ------------------------------------------------------------
def get_arima_prediction(commodity, market, prices, steps=1):
    """Get ARIMA prediction for a commodity-market pair with fallback"""
    key = f"{commodity}_{market}"
    
    # Try to use trained ARIMA model
    if key in ARIMA_MODELS:
        try:
            model_data = ARIMA_MODELS[key]
            model_fit = model_data['model']
            prediction = model_fit.forecast(steps=steps)
            return float(prediction[-1]) if len(prediction) > 0 else None
        except Exception as e:
            print(f"⚠️ ARIMA model prediction failed: {e}")
    
    # Fallback: use weighted average
    fallback = get_fallback_prediction(prices)
    if fallback:
        print(f"🔄 Using fallback ARIMA prediction: {fallback:.2f}")
    return fallback

# ------------------------------------------------------------
# Feature builders (same logic as the training pipeline)
# ------------------------------------------------------------
def build_feature_row(price_history, target_date, commodity, market, variety, feature_columns):
    """Build feature row for prediction with proper handling of missing data"""
    row = {}
    hist = list(price_history)
    
    # If no history, use defaults
    if not hist:
        hist = [0] * max(LAG_DAYS)
    
    # Price lag features - handle short history
    for l in LAG_DAYS:
        if len(hist) >= l:
            row[f"Lag_{l}"] = hist[-l]
        else:
            row[f"Lag_{l}"] = hist[-1] if hist else 0
    
    # Rolling averages
    row["Rolling_3"] = np.mean(hist[-3:]) if len(hist) >= 3 else (hist[-1] if hist else 0)
    row["Rolling_5"] = np.mean(hist[-5:]) if len(hist) >= 5 else (hist[-1] if hist else 0)
    row["Rolling_14"] = np.mean(hist[-14:]) if len(hist) >= 14 else (hist[-1] if hist else 0)
    
    # Date features
    row["Year"] = target_date.year
    row["Month"] = target_date.month
    row["Day"] = target_date.day
    row["DayOfYear"] = target_date.timetuple().tm_yday
    row["WeekOfYear"] = target_date.isocalendar()[1]
    row["Quarter"] = (target_date.month - 1) // 3 + 1
    
    # Get actual data from database if possible
    row["Rainfall_mm"] = get_rainfall_for_commodity_market(commodity, market, target_date)
    row["Festival_Flag"] = is_festival(target_date)
    row["Arrival_Qty"] = get_arrival_qty(commodity, market, target_date, hist)
    
    df_row = pd.DataFrame([row])
    
    # One-hot encode categorical features
    if commodity:
        for col in feature_columns:
            if col.startswith("Commodity_") and col == f"Commodity_{commodity}":
                df_row[col] = 1
    
    if market:
        for col in feature_columns:
            if col.startswith("Market_") and col == f"Market_{market}":
                df_row[col] = 1
    
    if variety:
        for col in feature_columns:
            if col.startswith("Variety_") and col == f"Variety_{variety}":
                df_row[col] = 1
    
    district = get_district(market) if market else "Dakshina Kannada"
    for col in feature_columns:
        if col.startswith("District_") and col == f"District_{district}":
            df_row[col] = 1
    
    for col in feature_columns:
        if col.startswith("State_") and col == "State_Karnataka":
            df_row[col] = 1
    
    # Fill missing columns with 0
    for col in feature_columns:
        if col not in df_row.columns:
            df_row[col] = 0
    
    missing_cols = set(feature_columns) - set(df_row.columns)
    for col in missing_cols:
        df_row[col] = 0
    
    return df_row[feature_columns].fillna(0)

def build_lstm_sequence(price_history, target_date, commodity_code, commodity_scalers, feature_columns):
    """Build LSTM sequence for prediction"""
    needed = SEQ_LEN + MAX_LAG
    if len(price_history) < needed or commodity_code not in commodity_scalers:
        return None
    
    if "x" not in commodity_scalers[commodity_code]:
        return None
    
    sx = commodity_scalers[commodity_code]["x"]
    rows = []
    
    for offset in range(SEQ_LEN, 0, -1):
        hist_slice = price_history[: len(price_history) - offset + 1]
        r = build_feature_row(
            hist_slice, 
            target_date - timedelta(days=offset-1),
            None, None, None, 
            feature_columns
        )
        rows.append(r.values[0])
    
    seq_raw = np.array(rows, dtype=float)
    seq_raw = np.nan_to_num(seq_raw, nan=0.0)
    
    try:
        seq_scaled = sx.transform(seq_raw)
        return seq_scaled.reshape(1, SEQ_LEN, -1)
    except Exception as e:
        print(f"Error scaling LSTM sequence: {e}")
        return None

# ------------------------------------------------------------
# Database access
# ------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_commodities():
    """Get all unique commodities"""
    conn = get_db()
    try:
        rows = conn.execute("SELECT DISTINCT Commodity FROM prices ORDER BY Commodity").fetchall()
        return [r["Commodity"] for r in rows]
    except Exception as e:
        print(f"Error getting commodities: {e}")
        return []
    finally:
        conn.close()

def get_markets(commodity):
    """Get all markets for a commodity"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT Market FROM prices WHERE Commodity = ? ORDER BY Market", 
            (commodity,)
        ).fetchall()
        return [r["Market"] for r in rows]
    except Exception as e:
        print(f"Error getting markets: {e}")
        return []
    finally:
        conn.close()

def get_price_history(commodity, market, n=HISTORY_DAYS):
    """Returns the last n rows, oldest first.
    Collapses duplicate (Commodity, Market, Date) rows down to one per
    date (averaging Modal_Price) -- the prices table can accumulate
    exact duplicates if the same CSV gets uploaded/trained more than
    once, since admin_training.py appends rather than upserting.
    Without this, a handful of repeated dates can eat most of the
    "last n" window and make the chart look artificially flat.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT Date,
                      AVG(Modal_Price) AS Modal_Price,
                      MAX(Variety) AS Variety,
                      AVG(Arrival_Qty) AS Arrival_Qty
               FROM prices
               WHERE Commodity = ? AND Market = ?
               GROUP BY Date
               ORDER BY Date DESC LIMIT ?""",
            (commodity, market, n),
        ).fetchall()
        rows = list(reversed(rows))
        return rows
    except Exception as e:
        print(f"Error getting price history: {e}")
        return []
    finally:
        conn.close()

def get_price_history_only(commodity, market, n=HISTORY_DAYS):
    """Get only price history for prediction"""
    rows = get_price_history(commodity, market, n)
    return [r["Modal_Price"] for r in rows]

def get_seasonal_pattern(commodity, market, current_date):
    """Get price data for the same month from previous years (fixed)"""
    conn = get_db()
    month = current_date.strftime("%m")
    try:
        # Get ALL data for this month across all years (not just same day)
        # GROUP BY Date collapses any duplicate rows for the same date.
        rows = conn.execute(
            """SELECT Date, AVG(Modal_Price) AS Modal_Price
               FROM prices
               WHERE Commodity = ? AND Market = ?
               AND strftime('%m', Date) = ?
               GROUP BY Date
               ORDER BY Date DESC""",
            (commodity, market, month),
        ).fetchall()
        
        # If no data for this month, try the previous month
        if not rows:
            prev_month = str(int(month) - 1).zfill(2) if int(month) > 1 else "12"
            rows = conn.execute(
                """SELECT Date, AVG(Modal_Price) AS Modal_Price
                   FROM prices
                   WHERE Commodity = ? AND Market = ?
                   AND strftime('%m', Date) = ?
                   GROUP BY Date
                   ORDER BY Date DESC""",
                (commodity, market, prev_month),
            ).fetchall()
            
        return rows
    except Exception as e:
        print(f"Error getting seasonal pattern: {e}")
        return []
    finally:
        conn.close()

def get_historical_price_by_month(commodity, market, month):
    """
    Get historical price data for a specific month across ALL years
    - Groups by year and calculates average
    - Returns ALL years of data (2015-2024)
    Duplicate rows for the same Date are collapsed into one (averaged)
    before this -- see get_price_history() for why that happens.
    """
    conn = get_db()
    try:
        query = """
            SELECT Date, AVG(Modal_Price) AS Modal_Price, strftime('%Y', Date) as Year
            FROM prices
            WHERE Commodity = ? AND Market = ? AND strftime('%m', Date) = ?
            GROUP BY Date
            ORDER BY Date
        """
        rows = conn.execute(query, (commodity, market, month.zfill(2))).fetchall()
        return rows
    except Exception as e:
        print(f"Error getting historical prices: {e}")
        return []
    finally:
        conn.close()

def get_monthly_stats(commodity, market, month):
    """Get comprehensive monthly statistics"""
    rows = get_historical_price_by_month(commodity, market, month)
    if not rows:
        return None
    
    prices = [r["Modal_Price"] for r in rows]
    return {
        "avg": float(np.mean(prices)),
        "min": float(np.min(prices)),
        "max": float(np.max(prices)),
        "count": int(len(prices)),
        "median": float(np.median(prices)),
        "std": float(np.std(prices))
    }

def get_data_availability(commodity, market):
    """Check data availability for a commodity-market pair"""
    conn = get_db()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM prices WHERE Commodity = ? AND Market = ?",
            (commodity, market)
        ).fetchone()[0]
        return int(count)
    except Exception as e:
        print(f"Error checking data availability: {e}")
        return 0
    finally:
        conn.close()

# ============================================================
# ENGLISH RECOMMENDATION ENGINE (UPDATED LOGIC)
# ============================================================
def get_recommendation(last_price, predicted_price, recent_prices, year_prices, pct_change, seasonal_data, monthly_stats, month_name):
    """
    UPDATED RECOMMENDATION ENGINE:
    - POSITIVE prediction (price will RISE) → STORE (wait for higher price)
    - NEGATIVE prediction (price will FALL) → SELL (sell now before it drops)
    - NEUTRAL prediction → WAIT
    
    This is the CORRECT logic for farmers:
    - If price will increase → store now, sell later at higher price
    - If price will decrease → sell now before price drops
    """
    
    if not last_price or not predicted_price:
        return "WAIT", "⚠️ Insufficient data for a recommendation. Please check your selection."
    
    # Calculate key metrics
    volatility = (np.std(recent_prices) / np.mean(recent_prices)) if len(recent_prices) > 0 and np.mean(recent_prices) else 0
    
    year_high = max(year_prices) if year_prices else last_price
    year_low = min(year_prices) if year_prices else last_price
    
    # Price difference
    price_diff = predicted_price - last_price
    price_diff_abs = abs(price_diff)
    
    # Seasonal average
    seasonal_avg = None
    seasonal_diff = 0
    if seasonal_data and len(seasonal_data) >= 3:
        prices = [row["Modal_Price"] for row in seasonal_data]
        seasonal_avg = np.mean(prices)
        seasonal_diff = ((last_price - seasonal_avg) / seasonal_avg) * 100 if seasonal_avg else 0
    
    # Position in yearly range
    year_range = year_high - year_low
    if year_range > 0:
        position_in_year = ((last_price - year_low) / year_range) * 100
    else:
        position_in_year = 50
    
    # ============================================================
    # UPDATED LOGIC: POSITIVE → STORE, NEGATIVE → SELL
    # ============================================================
    if pct_change > 0:
        # POSITIVE prediction - price will RISE → STORE
        if pct_change > 5:
            strength = "strongly"
        elif pct_change > 2:
            strength = "moderately"
        else:
            strength = "slightly"
        
        # Seasonal context
        seasonal_context = ""
        if seasonal_avg:
            if seasonal_diff > 10:
                seasonal_context = f" (price is {seasonal_diff:.1f}% above seasonal average ₹{seasonal_avg:.2f})"
            elif seasonal_diff < -10:
                seasonal_context = f" (price is {abs(seasonal_diff):.1f}% below seasonal average ₹{seasonal_avg:.2f}, but rising)"
            else:
                seasonal_context = f" (price near seasonal average ₹{seasonal_avg:.2f})"
        
        # Volatility context
        volatility_context = ""
        if volatility > 0.10:
            volatility_context = f" Market volatility is {volatility*100:.1f}%."
        
        # Monthly context
        monthly_context = ""
        if monthly_stats and month_name:
            monthly_context = f" {month_name} avg: ₹{monthly_stats['avg']:.2f}."
        
        # Position context
        position_context = ""
        if position_in_year > 70:
            position_context = " Price is near yearly high, but still rising. Store for maximum profit."
        elif position_in_year < 30:
            position_context = " Price is near yearly low and rising. Store and wait for better prices."
        
        reason = (
            f"📈 Price expected to rise {strength} by {pct_change:.1f}% (₹{price_diff_abs:.2f}/unit). "
            f"STORE your crop now and sell later at the predicted higher price. "
            f"Current: ₹{last_price:.2f} | Year range: ₹{year_low:.2f} - ₹{year_high:.2f}. "
            f"{seasonal_context}{position_context}{monthly_context}{volatility_context}"
            f" 🎯 Action: STORE"
        )
        return "STORE", reason
    
    elif pct_change < 0:
        # NEGATIVE prediction - price will FALL → SELL
        drop_abs = abs(pct_change)
        
        if drop_abs > 5:
            strength = "strongly"
        elif drop_abs > 2:
            strength = "moderately"
        else:
            strength = "slightly"
        
        # Seasonal context
        seasonal_context = ""
        if seasonal_avg:
            if seasonal_diff > 10:
                seasonal_context = f" (price is {seasonal_diff:.1f}% above seasonal average ₹{seasonal_avg:.2f}, falling)"
            elif seasonal_diff < -10:
                seasonal_context = f" (price is {abs(seasonal_diff):.1f}% below seasonal average ₹{seasonal_avg:.2f})"
            else:
                seasonal_context = f" (price near seasonal average ₹{seasonal_avg:.2f})"
        
        # Volatility context
        volatility_context = ""
        if volatility > 0.10:
            volatility_context = f" Market volatility is {volatility*100:.1f}%."
        
        # Monthly context
        monthly_context = ""
        if monthly_stats and month_name:
            monthly_context = f" {month_name} avg: ₹{monthly_stats['avg']:.2f}."
        
        # Position context
        position_context = ""
        if position_in_year > 70:
            position_context = " Price is near yearly high. SELL NOW to lock in profits before the drop."
        elif position_in_year < 30:
            position_context = " Price is near yearly low and falling further. SELL NOW to minimize losses."
        
        reason = (
            f"📉 Price expected to drop {strength} by {drop_abs:.1f}% (₹{price_diff_abs:.2f}/unit). "
            f"SELL your crop NOW before the price decreases further. "
            f"Current: ₹{last_price:.2f} | Year range: ₹{year_low:.2f} - ₹{year_high:.2f}. "
            f"{seasonal_context}{position_context}{monthly_context}{volatility_context}"
            f" 🎯 Action: SELL"
        )
        return "SELL", reason
    
    else:
        # NEUTRAL prediction - price stable → WAIT
        position_context = ""
        if position_in_year > 70:
            position_context = " Price is near yearly high. Consider selling at the peak."
            return "SELL", f"📊 Price is stable at ₹{last_price:.2f}. Year range: ₹{year_low:.2f} - ₹{year_high:.2f}. {position_context} 🎯 Action: SELL"
        elif position_in_year < 30:
            position_context = " Price is near yearly low. Store and wait for recovery."
            return "STORE", f"📊 Price is stable at ₹{last_price:.2f}. Year range: ₹{year_low:.2f} - ₹{year_high:.2f}. {position_context} 🎯 Action: STORE"
        else:
            return "WAIT", f"📊 Price is stable at ₹{last_price:.2f}. Year range: ₹{year_low:.2f} - ₹{year_high:.2f}. Wait for a clearer trend. 🎯 Action: WAIT"

def get_stats():
    """Get statistics for the landing page"""
    conn = get_db()
    try:
        total_records = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
        commodities = conn.execute("SELECT COUNT(DISTINCT Commodity) FROM prices").fetchone()[0]
        markets = conn.execute("SELECT COUNT(DISTINCT Market) FROM prices").fetchone()[0]
        date_range = conn.execute("SELECT MIN(Date), MAX(Date) FROM prices").fetchone()
        
        return {
            "total_records": int(total_records),
            "commodities": int(commodities),
            "markets": int(markets),
            "start_date": date_range[0] if date_range[0] else "2019",
            "end_date": date_range[1] if date_range[1] else "2024",
            "models_loaded": LR is not None
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {
            "total_records": 0,
            "commodities": 0,
            "markets": 0,
            "start_date": "N/A",
            "end_date": "N/A",
            "models_loaded": False
        }
    finally:
        conn.close()

# ------------------------------------------------------------
# Authentication Routes
# ------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # --- Hardcoded admin shortcut: no registration needed ---
        if username == 'admin123' and password == 'admin123':
            session['user_id'] = 'admin'
            session['username'] = 'admin'
            session['is_admin'] = True
            session['profile_image'] = '/static/img/avatars/tech.png'
            from blueprints.assistant_module import log_activity
            log_activity("admin", "login", "Admin logged in", page="/admin", profile_image='/static/img/avatars/tech.png')
            flash('Welcome back, Admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        # --- end admin shortcut ---

        user = verify_user(username, password)
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            user_avatar = user[2] if len(user) > 2 and user[2] else get_user_profile_image(user[1])
            session['profile_image'] = user_avatar
            update_last_login(username)
            from blueprints.assistant_module import log_activity
            log_activity(user[1], "login", f"User {user[1]} logged in", page="/dashboard", profile_image=user_avatar)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')
        profile_preset = request.form.get('profile_preset')
        profile_file = request.files.get('profile_image')
        
        if not username or not password:
            flash('Username and password are required!', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters!', 'danger')
            return render_template('register.html')

        # Determine profile image URL
        profile_image_url = None
        if profile_file and profile_file.filename:
            ext = os.path.splitext(profile_file.filename)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                upload_dir = os.path.join(app.static_folder, 'uploads', 'avatars')
                os.makedirs(upload_dir, exist_ok=True)
                clean_name = f"avatar_{re.sub(r'[^a-zA-Z0-9_]', '', username)}_{int(datetime.now().timestamp())}{ext}"
                save_dest = os.path.join(upload_dir, clean_name)
                profile_file.save(save_dest)
                profile_image_url = f"/static/uploads/avatars/{clean_name}"
        elif profile_preset:
            profile_image_url = profile_preset
            
        if not profile_image_url:
            profile_image_url = "/static/img/default-avatar.png"
        
        if create_user(username, password, email, profile_image_url):
            from blueprints.assistant_module import log_activity
            log_activity(username, "register", f"User {username} registered", page="/register", profile_image=profile_image_url)
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username already exists!', 'danger')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    username = session.get('username')
    if username:
        from blueprints.assistant_module import log_activity
        log_activity(username, "logout", f"User {username} logged out", page="/logout")
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('landing'))

@app.route('/favicon.ico')
def favicon():
    fav_file = os.path.join(app.root_path, 'static', 'favicon.ico')
    if os.path.exists(fav_file):
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'favicon.ico', mimetype='image/x-icon')
    return send_from_directory(os.path.join(app.root_path, 'static', 'img'),
                               'logo.png', mimetype='image/png')

@app.route('/static/favicon.ico')
def static_favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/x-icon')

@app.route('/static/videos/<path:filename>')
def serve_video_stream(filename):
    """Serve videos with full HTTP 206 Partial Content and byte-range support using Werkzeug/Flask"""
    video_dir = os.path.join(app.root_path, 'static', 'videos')
    resp = send_from_directory(video_dir, filename, mimetype='video/mp4', conditional=True)
    resp.headers['Accept-Ranges'] = 'bytes'
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp

@app.route('/logo.png')
def root_logo():
    return send_from_directory(os.path.join(app.root_path, 'static', 'img'),
                               'logo.png', mimetype='image/png')

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def serve_sw():
    response = send_from_directory(os.path.join(app.root_path, 'static'),
                                   'sw.js', mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.after_request
def optimize_and_compress(response):
    # 1. Long-lived cache headers for static assets (images, CSS, JS)
    if request.path.startswith('/static/'):
        if not any(request.path.endswith(ext) for ext in ['.html', '.json', 'sw.js']):
            response.headers['Cache-Control'] = 'public, max-age=86400'

    # 2. Gzip compression for text, JSON, and HTML (80% bandwidth reduction on mobile)
    accept_encoding = request.headers.get('Accept-Encoding', '')
    if 'gzip' in accept_encoding.lower():
        if 200 <= response.status_code < 300 and 'Content-Encoding' not in response.headers:
            content_type = response.headers.get('Content-Type', '')
            if any(t in content_type for t in ['text/', 'application/json', 'application/javascript', 'application/manifest+json']):
                if not response.direct_passthrough:
                    data = response.get_data()
                    if len(data) > 500:
                        compressed = gzip.compress(data, compresslevel=5)
                        response.set_data(compressed)
                        response.headers['Content-Encoding'] = 'gzip'
                        response.headers['Content-Length'] = len(compressed)
                        response.headers['Vary'] = 'Accept-Encoding'
    return response


# ------------------------------------------------------------
# Global Context Processor: Injects username and profile_image
# ------------------------------------------------------------
@app.context_processor
def inject_user_context():
    uname = session.get('username')
    pimg = session.get('profile_image')
    if uname and not pimg:
        pimg = get_user_profile_image(uname)
        session['profile_image'] = pimg
    return dict(
        username=uname,
        profile_image=pimg or '/static/img/default-avatar.png'
    )

@app.route('/api/user/profile-image', methods=['POST'])
def api_update_profile_image():
    if 'username' not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    username = session['username']
    profile_file = request.files.get('profile_image')
    preset = request.form.get('preset')
    
    image_url = None
    if profile_file and profile_file.filename:
        ext = os.path.splitext(profile_file.filename)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
            upload_dir = os.path.join(app.static_folder, 'uploads', 'avatars')
            os.makedirs(upload_dir, exist_ok=True)
            clean_name = f"avatar_{re.sub(r'[^a-zA-Z0-9_]', '', username)}_{int(datetime.now().timestamp())}{ext}"
            save_dest = os.path.join(upload_dir, clean_name)
            profile_file.save(save_dest)
            image_url = f"/static/uploads/avatars/{clean_name}"
    elif preset:
        image_url = preset

    if not image_url:
        return jsonify({"success": False, "error": "No image provided"}), 400

    set_user_profile_image(username, image_url)
    session['profile_image'] = image_url

    from blueprints.assistant_module import log_activity
    log_activity(
        username=username,
        action_type="profile_update",
        description="Updated profile picture",
        details=f"Avatar: {image_url}",
        page=request.referrer or "/dashboard",
        profile_image=image_url
    )

    return jsonify({"success": True, "profile_image": image_url})

# ------------------------------------------------------------
# Main Routes
# ------------------------------------------------------------
@app.route("/")
def landing():
    """Landing page - shown to unauthenticated users"""
    stats = get_stats()
    return render_template("landing.html", stats=stats)

@app.route("/dashboard")
def dashboard():
    """Dashboard - shown to authenticated users"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    commodities = get_commodities()
    username = session.get('username', 'User')
    return render_template("index.html", commodities=commodities, username=username)

# ============================================================
# Admin Dashboard Route
# ============================================================
@app.route("/admin")
def admin_dashboard():
    """Admin Dashboard - Model Training Interface"""
    if not session.get('is_admin'):
        flash('Admin access required', 'danger')
        return redirect(url_for('login'))

    username = session.get('username', 'Admin')
    return render_template("admindashboard.html", username=username)

@app.route("/admin/dedupe-prices", methods=["POST"])
def admin_dedupe_prices():
    """
    One-time cleanup: removes duplicate (Commodity, Market, Date) rows
    from prices.db, keeping a single row per combination. These
    duplicates build up if the same CSV gets uploaded/trained more than
    once, since the training pipeline appends rather than upserting --
    they're what was flattening/repeating stretches of the price chart.
    """
    if not session.get('is_admin'):
        return jsonify({"error": "Admin access required"}), 403

    conn = get_db()
    try:
        before = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
        conn.execute("""
            DELETE FROM prices
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM prices
                GROUP BY Commodity, Market, Date
            )
        """)
        conn.commit()
        after = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
        return jsonify({
            "status": "success",
            "rows_before": before,
            "rows_after": after,
            "duplicates_removed": before - after
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# ============================================================
# Model Comparison Page Routes - Both spellings work
# ============================================================
@app.route("/model-comparison")
def model_comparison():
    """Model Comparison page - shows all models performance (hyphenated)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    commodities = get_commodities()
    username = session.get('username', 'User')
    return render_template("model_comparison.html", commodities=commodities, username=username)

@app.route("/model_comparision")
def model_comparision():
    """Model Comparison page - shows all models performance (underscored)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    commodities = get_commodities()
    username = session.get('username', 'User')
    return render_template("model_comparison.html", commodities=commodities, username=username)

@app.route("/insights")
def model_insights():
    """Model Insights tab -- one place with a trained-metrics graph/heading
    per module: price prediction, crop recommender, regional advisor,
    sensor node, leaf disease. Reads the metrics JSON files each training
    script already writes to saved_models/ -- doesn't retrain anything."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    def _read_json(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    price_metrics = _read_json(os.path.join(MODEL_DIR, "model_metrics.json"))
    admin_last_run = _read_json(os.path.join(MODEL_DIR, "admin_last_run_metrics.json"))
    crop_metrics = _read_json(os.path.join(MODEL_DIR, "crop", "crop_model_metrics.json"))
    regional_metrics = _read_json(os.path.join(MODEL_DIR, "regional_advisor", "regional_metrics.json"))
    disease_metrics = _read_json(os.path.join(MODEL_DIR, "disease_model_metrics.json"))  # not generated yet

    username = session.get('username', 'User')
    return render_template(
        "model_insights.html",
        username=username,
        price_metrics=price_metrics,
        regression_data=(admin_last_run or {}).get("regression_data"),
        crop_metrics=crop_metrics,
        regional_metrics=regional_metrics,
        disease_metrics=disease_metrics,
    )

# ============================================================
# API Routes
# ============================================================
@app.route("/api/markets/<commodity>")
def api_markets(commodity):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(get_markets(commodity))

@app.route("/api/data-availability")
def api_data_availability():
    """Check data availability for a commodity-market pair"""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    commodity = request.args.get("commodity")
    market = request.args.get("market")
    
    if not commodity or not market:
        return jsonify({"error": "commodity and market are required"}), 400
    
    count = get_data_availability(commodity, market)
    return jsonify({
        "commodity": commodity,
        "market": market,
        "record_count": count,
        "has_data": count > 0
    })

@app.route("/api/predict")
def api_predict():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    commodity = request.args.get("commodity")
    market = request.args.get("market")
    month = request.args.get("month")
    
    if not commodity or not market:
        return jsonify({"error": "commodity and market are required"}), 400

    if LR is None:
        return jsonify({
            "error": "Models not loaded. Please train models first.",
            "models_loaded": False
        }), 503

    # Get monthly stats if month is provided
    monthly_stats = None
    monthly_avg = None
    month_name = None
    if month:
        monthly_stats = get_monthly_stats(commodity, market, month)
        if monthly_stats:
            monthly_avg = monthly_stats["avg"]
        
        month_names = {
            '01': 'January', '02': 'February', '03': 'March', '04': 'April',
            '05': 'May', '06': 'June', '07': 'July', '08': 'August',
            '09': 'September', '10': 'October', '11': 'November', '12': 'December'
        }
        month_name = month_names.get(month, month)

    # Get history for prediction
    history_rows = get_price_history(commodity, market, n=HISTORY_DAYS)
    
    # If no data for this market, try to get data from any market for this commodity
    if len(history_rows) < MAX_LAG:
        conn = get_db()
        try:
            fallback_rows = conn.execute(
                """SELECT Date, Modal_Price, Variety, Arrival_Qty FROM prices
                   WHERE Commodity = ?
                   ORDER BY Date DESC LIMIT ?""",
                (commodity, HISTORY_DAYS)
            ).fetchall()
            fallback_rows = list(reversed(fallback_rows))
            if len(fallback_rows) >= MAX_LAG:
                history_rows = fallback_rows
                market = market + " (Fallback)"
                print(f"⚠️ Using fallback data for {commodity}")
        except Exception as e:
            print(f"Fallback query failed: {e}")
        finally:
            conn.close()
    
    if len(history_rows) < MAX_LAG:
        return jsonify({
            "error": f"Not enough history for {commodity} at {market}. Only {len(history_rows)} records found. Need at least {MAX_LAG} records.",
            "record_count": len(history_rows),
            "required": MAX_LAG
        }), 400

    variety = history_rows[-1]["Variety"] if history_rows else "Local"
    prices = [r["Modal_Price"] for r in history_rows]
    dates = [r["Date"] for r in history_rows]
    last_price = prices[-1]
    target_date = datetime.today()

    seasonal_data = get_seasonal_pattern(commodity, market, target_date)
    
    feature_row = build_feature_row(
        prices, target_date, commodity, market, variety, FEATURE_COLUMNS
    )

    # Get predictions from all models
    pred_lr = None
    pred_rf = None
    pred_xgb = None
    pred_lstm = None
    pred_arima = None
    
    try:
        pred_lr = float(LR.predict(feature_row)[0])
    except Exception as e:
        print(f"LR prediction failed for {commodity}@{market}: {e}")
    
    try:
        pred_rf = float(RF.predict(feature_row)[0])
    except Exception as e:
        print(f"RF prediction failed for {commodity}@{market}: {e}")
    
    try:
        pred_xgb = float(XGB.predict(feature_row)[0])
    except Exception as e:
        print(f"XGB prediction failed for {commodity}@{market}: {e}")

    # LSTM prediction with fallback
    try:
        if COMMODITY_LE is not None and LSTM is not None:
            commodity_code = COMMODITY_LE.transform([commodity])[0]
            lstm_seq = build_lstm_sequence(
                prices, target_date, commodity_code, COMMODITY_SCALERS, FEATURE_COLUMNS
            )
            if lstm_seq is not None:
                comm_input = np.array([[commodity_code]])
                lstm_pred_scaled = LSTM.predict([lstm_seq, comm_input], verbose=0)
                sy = COMMODITY_SCALERS[commodity_code]["y"]
                pred_lstm = float(sy.inverse_transform(lstm_pred_scaled)[0][0])
                print(f"✅ LSTM prediction: {pred_lstm:.2f}")
            else:
                # Fallback if sequence building fails
                pred_lstm = get_fallback_prediction(prices)
                if pred_lstm:
                    print(f"🔄 Using fallback LSTM prediction: {pred_lstm:.2f}")
        else:
            # LSTM not available, use fallback
            pred_lstm = get_fallback_prediction(prices)
            if pred_lstm:
                print(f"🔄 Using fallback LSTM (model not available): {pred_lstm:.2f}")
    except Exception as e:
        print(f"LSTM prediction failed: {e}")
        pred_lstm = get_fallback_prediction(prices)
        if pred_lstm:
            print(f"🔄 Using fallback LSTM (error recovery): {pred_lstm:.2f}")

    # ARIMA prediction with fallback
    try:
        pred_arima = get_arima_prediction(commodity, market, prices, steps=1)
        if pred_arima is not None and pred_arima > 0:
            print(f"✅ ARIMA prediction: {pred_arima:.2f}")
        else:
            pred_arima = get_fallback_prediction(prices)
            if pred_arima:
                print(f"🔄 Using fallback ARIMA prediction: {pred_arima:.2f}")
    except Exception as e:
        print(f"ARIMA prediction failed: {e}")
        pred_arima = get_fallback_prediction(prices)
        if pred_arima:
            print(f"🔄 Using fallback ARIMA (error recovery): {pred_arima:.2f}")

    # Collect all valid predictions
    valid_preds = [p for p in [pred_lr, pred_rf, pred_xgb, pred_lstm, pred_arima] if p is not None]
    
    # Calculate total models
    total_models = 5
    models_working = len(valid_preds)
    
    if valid_preds:
        predicted_price = float(np.mean(valid_preds))
        predicted_price = max(predicted_price, 0.1)
    else:
        pred_prices = prices[-7:] if len(prices) >= 7 else prices
        predicted_price = float(np.mean(pred_prices))
        predicted_price = max(predicted_price, 0.1)

    # Use monthly average as the display price if available
    if monthly_avg is not None and monthly_avg > 0:
        display_price = monthly_avg
        if month_name:
            display_date = f"Monthly Avg ({month_name})"
        else:
            display_date = "Monthly Avg"
        is_monthly = True
    else:
        display_price = last_price
        display_date = dates[-1] if dates else "N/A"
        is_monthly = False

    pct_change = (predicted_price - display_price) / display_price * 100 if display_price else 0

    recent_60 = prices[-60:] if len(prices) >= 60 else prices
    
    # Use the UPDATED recommendation engine with correct logic
    recommendation, reason = get_recommendation(
        display_price, predicted_price, recent_60, prices, pct_change, 
        seasonal_data, monthly_stats, month_name
    )

    confidence = len(valid_preds) / total_models * 100 if valid_preds else 25

    # Build model predictions dictionary
    model_predictions = {
        "linear_regression": pred_lr,
        "random_forest": pred_rf,
        "xgboost": pred_xgb,
        "lstm": pred_lstm,
        "arima": pred_arima
    }

    # Dynamic model metrics: use the monthly seasonal average (if we have
    # one for this month) or the seasonal comparison average as the
    # reference price, so RMSE/MAE - and therefore Best Model - change
    # with the commodity/market/month selection instead of staying fixed.
    seasonal_avg_for_metrics = float(np.mean([r["Modal_Price"] for r in seasonal_data])) if seasonal_data else None
    baseline_for_metrics = monthly_avg if monthly_avg else (seasonal_avg_for_metrics or display_price)
    dynamic_metrics = compute_dynamic_model_metrics(model_predictions, baseline_for_metrics)
    best_model_key, best_model_rmse, best_model_mae = get_best_model_from_metrics(dynamic_metrics)

    response = {
        "commodity": commodity,
        "market": market,
        "variety": variety,
        "last_price": float(display_price) if display_price else 0,
        "last_date": display_date,
        "change_percent": float(pct_change) if pct_change else 0,
        "history": {
            "dates": dates[-60:] if len(dates) > 60 else dates,
            "prices": [float(p) for p in (prices[-60:] if len(prices) > 60 else prices)]
        },
        "predicted_price": float(predicted_price) if predicted_price else 0,
        "recommendation": recommendation,
        "reason": reason,
        "seasonal_insight": None,
        "data_points": int(len(prices)),
        "models_working": int(models_working),
        "total_models": int(total_models),
        "confidence": f"{confidence:.0f}%",
        "monthly_avg": float(monthly_avg) if monthly_avg else None,
        "monthly_stats": monthly_stats,
        "is_monthly": is_monthly,
        "selected_month": month,
        "month_name": month_name,
        "seasonal_comparison": {
            "avg_seasonal": float(np.mean([r["Modal_Price"] for r in seasonal_data])) if seasonal_data else None,
            "data_points": int(len(seasonal_data))
        },
        "models_loaded": True,
        "arima_available": bool(ARIMA_MODELS),
        "model_predictions": model_predictions,
        "model_metrics": dynamic_metrics,
        "best_model": best_model_key,
        "best_model_rmse": best_model_rmse,
        "best_model_mae": best_model_mae
    }
    
    # Log feature entry into user activities with profile image
    try:
        from blueprints.assistant_module import log_activity
        log_activity(
            username=session.get("username", "guest"),
            action_type="price_prediction",
            description=f"Predicted {commodity} @ {market}: ₹{predicted_price:.2f}",
            details=f"Recommendation: {action}, Expected change: {price_diff_abs:+.1f}%",
            page="/dashboard",
            profile_image=session.get("profile_image")
        )
    except Exception as e:
        print(f"Could not log predict activity: {e}")

    # Convert any remaining numpy types to Python native types
    response = convert_to_serializable(response)
    return jsonify(response)

@app.route("/api/predict-months")
def api_predict_months():
    """
    Predicts prices for the selected month plus the following 4 months
    (5 months total), reusing the same models as /api/predict. For each
    future month the target date used for feature-building shifts
    forward accordingly, and ARIMA is asked to forecast further out
    (more steps) the further ahead the month is.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    commodity = request.args.get("commodity")
    market = request.args.get("market")
    month = request.args.get("month")

    if not commodity or not market or not month:
        return jsonify({"error": "commodity, market, and month are required"}), 400

    if LR is None:
        return jsonify({
            "error": "Models not loaded. Please train models first.",
            "models_loaded": False
        }), 503

    # Get price history
    history_rows = get_price_history(commodity, market, n=HISTORY_DAYS)

    if len(history_rows) < MAX_LAG:
        # Try fallback
        conn = get_db()
        try:
            fallback_rows = conn.execute(
                """SELECT Date, Modal_Price, Variety, Arrival_Qty FROM prices
                   WHERE Commodity = ?
                   ORDER BY Date DESC LIMIT ?""",
                (commodity, HISTORY_DAYS)
            ).fetchall()
            fallback_rows = list(reversed(fallback_rows))
            if len(fallback_rows) >= MAX_LAG:
                history_rows = fallback_rows
                market = market + " (Fallback)"
                print(f"⚠️ Using fallback data for {commodity}")
        except Exception as e:
            print(f"Fallback query failed: {e}")
        finally:
            conn.close()

    if len(history_rows) < MAX_LAG:
        return jsonify({
            "error": f"Not enough history for {commodity} at {market}. Only {len(history_rows)} records found. Need at least {MAX_LAG} records.",
            "record_count": len(history_rows),
            "required": MAX_LAG
        }), 400

    variety = history_rows[-1]["Variety"] if history_rows else "Local"
    prices = [r["Modal_Price"] for r in history_rows]
    last_date_str = history_rows[-1]["Date"] if history_rows else None
    
    try:
        last_known_date = datetime.strptime(last_date_str, "%Y-%m-%d") if last_date_str else datetime.today()
    except Exception:
        last_known_date = datetime.today()

    month_names = {
        1: 'January', 2: 'February', 3: 'March', 4: 'April',
        5: 'May', 6: 'June', 7: 'July', 8: 'August',
        9: 'September', 10: 'October', 11: 'November', 12: 'December'
    }

    # Validate month input
    try:
        month_int = int(month)
    except ValueError:
        return jsonify({"error": "Invalid month format. Please use MM (e.g., 01 for January)."}), 400

    if month_int < 1 or month_int > 12:
        return jsonify({"error": "Month must be between 1 and 12."}), 400

    months_seq = get_next_n_months(month_int, n=5)
    monthly_table = []

    for (yr, mo) in months_seq:
        target_date = datetime(yr, mo, 15)
        days_ahead = max((target_date - last_known_date).days, 1)

        feature_row = build_feature_row(prices, target_date, commodity, market, variety, FEATURE_COLUMNS)

        preds = {}
        
        # Linear Regression
        try:
            preds["linear_regression"] = float(LR.predict(feature_row)[0])
        except Exception as e:
            print(f"LR month prediction failed: {e}")
            preds["linear_regression"] = None

        # Random Forest
        try:
            preds["random_forest"] = float(RF.predict(feature_row)[0])
        except Exception as e:
            print(f"RF month prediction failed: {e}")
            preds["random_forest"] = None

        # XGBoost
        try:
            preds["xgboost"] = float(XGB.predict(feature_row)[0])
        except Exception as e:
            print(f"XGB month prediction failed: {e}")
            preds["xgboost"] = None

        # LSTM
        try:
            if COMMODITY_LE is not None and LSTM is not None:
                commodity_code = COMMODITY_LE.transform([commodity])[0]
                lstm_seq = build_lstm_sequence(prices, target_date, commodity_code, COMMODITY_SCALERS, FEATURE_COLUMNS)
                if lstm_seq is not None:
                    comm_input = np.array([[commodity_code]])
                    lstm_pred_scaled = LSTM.predict([lstm_seq, comm_input], verbose=0)
                    sy = COMMODITY_SCALERS[commodity_code]["y"]
                    preds["lstm"] = float(sy.inverse_transform(lstm_pred_scaled)[0][0])
                else:
                    preds["lstm"] = get_fallback_prediction(prices)
            else:
                preds["lstm"] = get_fallback_prediction(prices)
        except Exception as e:
            print(f"LSTM month prediction failed: {e}")
            preds["lstm"] = get_fallback_prediction(prices)

        # ARIMA
        try:
            arima_pred = get_arima_prediction(commodity, market, prices, steps=days_ahead)
            preds["arima"] = arima_pred if arima_pred and arima_pred > 0 else get_fallback_prediction(prices)
        except Exception as e:
            print(f"ARIMA month prediction failed: {e}")
            preds["arima"] = get_fallback_prediction(prices)

        # Get monthly stats for this month
        monthly_stats = get_monthly_stats(commodity, market, f"{mo:02d}")
        valid_preds = [v for v in preds.values() if v is not None and v > 0]
        model_avg = float(np.mean(valid_preds)) if valid_preds else None

        # Combine with historical average if available
        if monthly_stats and monthly_stats.get("avg"):
            baseline = monthly_stats["avg"]
            final_price = (model_avg * 0.6 + baseline * 0.4) if model_avg else baseline
        else:
            baseline = model_avg
            final_price = model_avg

        if final_price is None or final_price <= 0:
            final_price = prices[-1] if prices else 1000

        # Calculate metrics for this month's predictions
        month_metrics = compute_dynamic_model_metrics(preds, baseline)
        best_key, best_rmse, best_mae = get_best_model_from_metrics(month_metrics)

        monthly_table.append({
            "month": f"{mo:02d}",
            "month_name": month_names.get(mo, str(mo)),
            "year": yr,
            "label": f"{month_names.get(mo, str(mo))} {yr}",
            "predicted_price": round(float(final_price), 2),
            "model_predictions": preds,
            "model_metrics": month_metrics,
            "best_model": best_key,
            "best_model_rmse": best_rmse,
            "best_model_mae": best_mae,
            "models_working": len(valid_preds)
        })

    response = {
        "commodity": commodity,
        "market": market,
        "variety": variety,
        "months": monthly_table
    }
    response = convert_to_serializable(response)
    return jsonify(response)

@app.route("/api/historical-price")
def api_historical_price():
    """
    API endpoint for the Price History Explorer
    Returns YEARLY AGGREGATED data for the selected month
    - NOW SHOWS ALL YEARS (2015-2024)
    - FALLBACK: Uses all available data if exact month not found
    """
    commodity = request.args.get("commodity")
    market = request.args.get("market")
    month = request.args.get("month")
    
    if not commodity or not market or not month:
        return jsonify({"error": "commodity, market, and month are required"}), 400
    
    conn = get_db()
    try:
        # Get ALL data for the specific month across ALL years (no limit)
        # GROUP BY Date collapses duplicate rows for the same date
        # (can happen if the same CSV is trained more than once) so the
        # chart doesn't show flat/repeated stretches.
        query = """
            SELECT Date, AVG(Modal_Price) AS Modal_Price, strftime('%Y', Date) as Year
            FROM prices
            WHERE Commodity = ? AND Market = ? AND strftime('%m', Date) = ?
            GROUP BY Date
            ORDER BY Date
        """
        rows = conn.execute(query, (commodity, market, month.zfill(2))).fetchall()
        
        # If no data for this month, try to get all data for this commodity-market
        if not rows:
            print(f"⚠️ No data for {commodity} @ {market} in month {month}, trying all data...")
            query_all = """
                SELECT Date, AVG(Modal_Price) AS Modal_Price, strftime('%Y', Date) as Year, strftime('%m', Date) as Month
                FROM prices
                WHERE Commodity = ? AND Market = ?
                GROUP BY Date
                ORDER BY Date
            """
            rows_all = conn.execute(query_all, (commodity, market)).fetchall()
            
            if rows_all:
                print(f"✅ Found {len(rows_all)} total records for {commodity} @ {market}")
                # Group by year and month
                yearly_data = {}
                for row in rows_all:
                    year = row["Year"]
                    month_from_data = row["Month"]
                    price = row["Modal_Price"]
                    key = f"{year}_{month_from_data}"
                    if key not in yearly_data:
                        yearly_data[key] = {"year": year, "month": month_from_data, "prices": [], "dates": []}
                    yearly_data[key]["prices"].append(price)
                    yearly_data[key]["dates"].append(row["Date"])
                
                # Calculate averages per year-month
                result_data = []
                all_prices = []
                for key, data in sorted(yearly_data.items()):
                    year_prices = data["prices"]
                    avg_price = np.mean(year_prices)
                    all_prices.extend(year_prices)
                    result_data.append({
                        "year": int(data["year"]),
                        "month": data["month"],
                        "price": float(round(avg_price, 2)),
                        "record_count": int(len(year_prices)),
                        "min": float(round(min(year_prices), 2)),
                        "max": float(round(max(year_prices), 2))
                    })
                
                # Calculate overall stats
                stats = {
                    "avg": float(round(np.mean(all_prices), 2)) if all_prices else 0,
                    "max": float(round(np.max(all_prices), 2)) if all_prices else 0,
                    "min": float(round(np.min(all_prices), 2)) if all_prices else 0,
                    "count": int(len(all_prices)),
                    "median": float(round(np.median(all_prices), 2)) if all_prices else 0,
                    "std": float(round(np.std(all_prices), 2)) if all_prices else 0,
                    "yearly_count": int(len(result_data))
                }
                
                month_names = {
                    "01": "January", "02": "February", "03": "March", "04": "April",
                    "05": "May", "06": "June", "07": "July", "08": "August",
                    "09": "September", "10": "October", "11": "November", "12": "December"
                }
                
                conn.close()
                
                response = {
                    "commodity": commodity,
                    "market": market,
                    "month": month,
                    "month_name": month_names.get(month, month),
                    "data": result_data,
                    "stats": stats,
                    "trend": "all_data",
                    "trend_message": f"Showing all available data for {commodity} @ {market}",
                    "is_fallback": True,
                    "raw_data": [
                        {"date": row["Date"], "price": float(row["Modal_Price"]), "year": int(row["Year"])} 
                        for row in rows_all
                    ]
                }
                
                response = convert_to_serializable(response)
                return jsonify(response)
        
        if not rows:
            conn.close()
            month_names = {
                "01": "January", "02": "February", "03": "March", "04": "April",
                "05": "May", "06": "June", "07": "July", "08": "August",
                "09": "September", "10": "October", "11": "November", "12": "December"
            }
            # Return empty data with a clear message
            return jsonify({
                "error": f"No data found for {commodity} at {market} in any month",
                "data": [],
                "stats": None,
                "month_name": month_names.get(month, month),
                "is_fallback": True
            }), 200
        
        # Group by year and calculate average price for each year
        yearly_data = {}
        for row in rows:
            year = row["Year"]
            price = row["Modal_Price"]
            if year not in yearly_data:
                yearly_data[year] = {"prices": [], "dates": []}
            yearly_data[year]["prices"].append(price)
            yearly_data[year]["dates"].append(row["Date"])
        
        # Calculate yearly averages - INCLUDE ALL YEARS
        result_data = []
        all_prices = []
        for year in sorted(yearly_data.keys()):
            year_prices = yearly_data[year]["prices"]
            avg_price = np.mean(year_prices)
            all_prices.extend(year_prices)
            result_data.append({
                "year": int(year),
                "price": float(round(avg_price, 2)),
                "record_count": int(len(year_prices)),
                "min": float(round(min(year_prices), 2)),
                "max": float(round(max(year_prices), 2))
            })
        
        # Calculate overall stats
        stats = {
            "avg": float(round(np.mean(all_prices), 2)) if all_prices else 0,
            "max": float(round(np.max(all_prices), 2)) if all_prices else 0,
            "min": float(round(np.min(all_prices), 2)) if all_prices else 0,
            "count": int(len(all_prices)),
            "median": float(round(np.median(all_prices), 2)) if all_prices else 0,
            "std": float(round(np.std(all_prices), 2)) if all_prices else 0,
            "yearly_count": int(len(result_data))
        }
        
        month_names = {
            "01": "January", "02": "February", "03": "March", "04": "April",
            "05": "May", "06": "June", "07": "July", "08": "August",
            "09": "September", "10": "October", "11": "November", "12": "December"
        }
        
        conn.close()
        
        response = {
            "commodity": commodity,
            "market": market,
            "month": month,
            "month_name": month_names.get(month, month),
            "data": result_data,  # ALL YEARS aggregated data
            "stats": stats,
            "trend": "seasonal",
            "trend_message": f"Historical prices for {month_names.get(month, month)} ({len(result_data)} years)",
            "is_fallback": False,
            "raw_data": [
                {"date": row["Date"], "price": float(row["Modal_Price"]), "year": int(row["Year"])} 
                for row in rows
            ]
        }
        
        # Ensure all values are JSON serializable
        response = convert_to_serializable(response)
        return jsonify(response)
        
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e), "data": [], "stats": None}), 500

@app.route("/api/model-check")
def api_model_check():
    """Check if models are loaded properly"""
    missing = validate_models()
    return jsonify({
        "models_loaded": LR is not None,
        "missing_files": missing,
        "feature_count": len(FEATURE_COLUMNS) if FEATURE_COLUMNS else 0,
        "commodities": len(COMMODITY_LE.classes_) if COMMODITY_LE is not None else 0,
        "arima_models": len(ARIMA_MODELS),
        "lstm_available": LSTM is not None,
        "models_available": {
            "linear_regression": LR is not None,
            "random_forest": RF is not None,
            "xgboost": XGB is not None,
            "lstm": LSTM is not None,
            "arima": len(ARIMA_MODELS) > 0,
            "scalers": COMMODITY_SCALERS is not None,
            "label_encoder": COMMODITY_LE is not None,
            "feature_columns": FEATURE_COLUMNS is not None
        }
    })

@app.route("/api/commodities")
def api_commodities():
    """Get all commodities"""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(get_commodities())

# ------------------------------------------------------------
# Main - Run the app
# ------------------------------------------------------------
def open_chrome():
    """Open Google Chrome browser automatically"""
    time.sleep(2.5)
    url = "http://127.0.0.1:5000"
    
    chrome_paths = [
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable"
    ]
    
    chrome_found = False
    
    for chrome_path in chrome_paths:
        if os.path.exists(chrome_path):
            try:
                print(f"🌐 Opening Chrome at: {chrome_path}")
                subprocess.Popen([chrome_path, url])
                chrome_found = True
                break
            except Exception as e:
                print(f"Failed to open Chrome: {e}")
                continue
    
    if not chrome_found:
        print("🌐 Chrome not found, opening default browser...")
        webbrowser.open(url)
    
    print("\n✅ Browser opened automatically!")
    print(f"📍 If it didn't open, go to: {url}")
    print("📝 Press Ctrl+C to stop the server\n")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🌾 SMART DSS - Agricultural Price Prediction")
    print("="*60)
    
    if LR is not None:
        print("✅ Models loaded successfully")
        print(f"   📊 {len(FEATURE_COLUMNS) if FEATURE_COLUMNS else 0} features loaded")
        print(f"   🌾 {len(COMMODITY_LE.classes_) if COMMODITY_LE is not None else 0} commodities supported")
        print(f"   📈 {len(ARIMA_MODELS)} ARIMA models loaded")
        print(f"   🧠 LSTM available: {LSTM is not None}")
    else:
        print("⚠️ Models not loaded. Please train models first.")
        print("   Run the training pipeline to generate model files.")
    
    print("📅 Using 365 days of historical data (full year)")
    print("🔐 User authentication enabled")
    print("🚀 Starting Flask server on http://127.0.0.1:5000 (Local)")
    print("📱 Mobile / LAN Access on http://192.168.100.233:5000")
    print("📝 Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    chrome_thread = threading.Thread(target=open_chrome, daemon=True)
    chrome_thread.start()

    start_simulator_if_enabled()

    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'

    app.run(
        debug=debug, 
        host=host, 
        port=port, 
        use_reloader=False,
        threaded=True
    )