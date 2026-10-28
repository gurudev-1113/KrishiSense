"""
admin_training.py
==================
Drop-in Flask Blueprint for the Smart DSS admin panel.

This version is matched EXACTLY to your real app.py:
- MODEL_DIR = "saved_models"          (same constant as app.py)
- DB_PATH   = "prices.db"             (same SQLite file app.py reads from)
- LSTM weights file: "lstm_model.weights.h5"   (matches validate_models())
- lstm_config.pkl carries seq_len / n_features / n_commodities / emb_dim
  (app.py's build_lstm_architecture needs all four)
- ARIMA models are saved ONE PER (Commodity, Market) PAIR as a pickled
  dict {"commodity":, "market":, "model":} inside saved_models/arima/,
  exactly what load_arima_models() in app.py expects.
- New CSV data is appended into the "prices" table in prices.db -- the
  SAME table app.py already reads for history/predictions -- so newly
  uploaded data shows up everywhere immediately, not just in training.
- After training, it calls app.reload_models() so the running server
  picks up the new models WITHOUT a restart (you add that one function
  to app.py -- see ADMIN_INTEGRATION.md).
- Metrics (R^2 as an accuracy score, MAE, RMSE) are written to
  saved_models/model_metrics.json in the same shape as app.py's
  MODEL_METRICS dict, so app.py can load real numbers instead of the
  hardcoded placeholder values it currently ships with.

HOW TO WIRE THIS IN -- see ADMIN_INTEGRATION.md
"""

import os
import json
import pickle
import sqlite3
import numpy as np
import pandas as pd
import joblib
from functools import wraps
import time

from flask import Blueprint, request, jsonify, session, stream_with_context, Response

from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# ------------------------------------------------------------------
# CONFIG -- these three MUST match the constants at the top of app.py
# ------------------------------------------------------------------
MODEL_DIR = "saved_models"
DB_PATH = "prices.db"
ARIMA_DIR = os.path.join(MODEL_DIR, "arima")
METRICS_PATH = os.path.join(MODEL_DIR, "model_metrics.json")

REQUIRED_COLUMNS = ["Date", "Commodity", "Market", "Variety", "Modal_Price"]

LAG_DAYS = [1, 2, 3, 4, 5, 6, 7, 10, 14]
SEQ_LEN = 10
LSTM_EPOCHS = int(os.environ.get("SMART_DSS_LSTM_EPOCHS", 60))

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(ARIMA_DIR, exist_ok=True)

admin_bp = Blueprint("admin_training", __name__)


# ------------------------------------------------------------------
# ADMIN GATE
# ------------------------------------------------------------------
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper


# ------------------------------------------------------------------
# 1. APPEND NEW CSV ROWS INTO prices.db -- the SAME table app.py reads
# ------------------------------------------------------------------
def append_to_prices_db(new_df: pd.DataFrame) -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(prices)")]
        if not existing_cols:
            raise RuntimeError("The 'prices' table doesn't exist in prices.db yet.")

        df = new_df.copy()
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

        # Only keep columns the prices table actually has, in its order
        keep_cols = [c for c in existing_cols if c in df.columns]
        df = df[keep_cols]

        df.to_sql("prices", conn, if_exists="append", index=False)
        conn.commit()
        return len(df)
    finally:
        conn.close()


def load_full_dataset() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql("SELECT * FROM prices", conn)
    finally:
        conn.close()
    df["Date"] = pd.to_datetime(df["Date"])
    return df


# ------------------------------------------------------------------
# 2. FEATURE ENGINEERING -- identical to your Colab training script
# ------------------------------------------------------------------
def engineer_features(df: pd.DataFrame):
    df = df.sort_values(["Commodity", "Date"]).reset_index(drop=True)

    for l in LAG_DAYS:
        df[f"Lag_{l}"] = df.groupby("Commodity")["Modal_Price"].shift(l)

    df["Rolling_3"] = df.groupby("Commodity")["Modal_Price"].shift(1).rolling(3, min_periods=1).mean()
    df["Rolling_5"] = df.groupby("Commodity")["Modal_Price"].shift(1).rolling(5, min_periods=1).mean()
    df["Rolling_14"] = df.groupby("Commodity")["Modal_Price"].shift(1).rolling(14, min_periods=1).mean()

    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    df["Day"] = df["Date"].dt.day

    lag_cols = [f"Lag_{l}" for l in LAG_DAYS]
    df = df.dropna(subset=lag_cols + ["Rolling_3", "Rolling_5", "Rolling_14"]).reset_index(drop=True)

    commodity_le = LabelEncoder()
    df["Commodity_Code"] = commodity_le.fit_transform(df["Commodity"])

    df_model = pd.get_dummies(df, columns=["Commodity", "Market", "Variety"], drop_first=True)

    drop_cols = ["Date", "Modal_Price", "Min_Price", "Max_Price", "State", "District",
                 "Month_Name", "Source"]
    X = df_model.drop(columns=[c for c in drop_cols if c in df_model.columns])
    y = df_model["Modal_Price"]

    return df, X, y, commodity_le


# ------------------------------------------------------------------
# 3. TRAIN LR / RF / XGBOOST -- each one is now fully independent
# ------------------------------------------------------------------
def _metrics_for(y_true, y_pred, rows_trained, collect_regression_data=False):
    """
    Calculate metrics and optionally collect regression data for chart.
    """
    # y_true comes straight out of train_test_split, so it's a pandas
    # Series that kept its ORIGINAL (scrambled) DataFrame index -- not
    # a clean 0..n-1 range. Indexing it with a positional integer
    # (y_true[i]) below would raise a KeyError almost every time.
    # Converting to plain numpy arrays makes positional indexing safe.
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    r2 = r2_score(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    
    metrics = {
        "accuracy_score": round(max(0.0, r2) * 100, 2),
        "r2_score": round(float(r2), 4),
        "mae": round(float(mae), 2),
        "rmse": round(float(rmse), 2),
        "rows_trained": rows_trained,
    }
    
    # Collect regression data for chart (max 100 points)
    if collect_regression_data and len(y_true) > 0 and len(y_pred) > 0:
        sample_size = min(100, len(y_true))
        indices = np.random.choice(len(y_true), sample_size, replace=False) if len(y_true) > 100 else range(len(y_true))
        
        metrics["regression_data"] = {
            "actual": [float(y_true[i]) for i in indices],
            "predicted": [float(y_pred[i]) for i in indices]
        }
    
    return metrics


def split_train_test(X, y):
    return train_test_split(X, y, test_size=0.20, random_state=42)


def train_linear_regression_only(X_train, X_test, y_train, y_test, collect_regression_data=False):
    lr = LinearRegression().fit(X_train, y_train)
    pred = lr.predict(X_test)
    joblib.dump(lr, os.path.join(MODEL_DIR, "linear_regression.pkl"))
    return _metrics_for(y_test, pred, len(X_train), collect_regression_data)


def train_random_forest_only(X_train, X_test, y_train, y_test, collect_regression_data=False):
    rf = RandomForestRegressor(n_estimators=500, max_depth=16, min_samples_leaf=1,
                                random_state=42, n_jobs=-1).fit(X_train, y_train)
    pred = rf.predict(X_test)
    joblib.dump(rf, os.path.join(MODEL_DIR, "random_forest.pkl"))
    return _metrics_for(y_test, pred, len(X_train), collect_regression_data)


def train_xgboost_only(X_train, X_test, y_train, y_test, collect_regression_data=False):
    from xgboost import XGBRegressor
    xgb = XGBRegressor(n_estimators=400, learning_rate=0.04, max_depth=4,
                        subsample=0.8, colsample_bytree=0.8, random_state=42)
    xgb.fit(X_train, y_train)
    pred = xgb.predict(X_test)
    xgb.save_model(os.path.join(MODEL_DIR, "xgboost_model.json"))
    return _metrics_for(y_test, pred, len(X_train), collect_regression_data)


# ------------------------------------------------------------------
# 4. TRAIN LSTM
# ------------------------------------------------------------------
def train_lstm(df, X, y, collect_regression_data=False, progress_callback=None):
    from tensorflow.keras.models import Model
    from tensorflow.keras.layers import Input, LSTM, Dense, Dropout, Embedding, Flatten, Concatenate
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, Callback

    commodity_dummy_cols = [c for c in X.columns if c.startswith("Commodity_")]
    exclude_from_numeric = set(commodity_dummy_cols) | {"Commodity_Code"}
    numeric_cols = [c for c in X.columns if c not in exclude_from_numeric]

    n_commodities = df["Commodity_Code"].nunique()

    X_train_list, X_test_list = [], []
    comm_train_list, comm_test_list = [], []
    y_train_list, y_test_list = [], []
    commodity_scalers = {}

    if progress_callback:
        progress_callback(35, "Preparing LSTM data...")

    for code in df["Commodity_Code"].unique():
        idx = df.index[df["Commodity_Code"] == code].tolist()
        if len(idx) < SEQ_LEN + 5:
            continue

        Xc_raw = X.loc[idx, numeric_cols].values.astype(float)
        yc_raw = y.loc[idx].values.reshape(-1, 1).astype(float)

        sx, sy = MinMaxScaler(), MinMaxScaler()
        Xc = sx.fit_transform(Xc_raw)
        yc = sy.fit_transform(yc_raw)
        commodity_scalers[code] = {"x": sx, "y": sy}

        Xs, ys, cs = [], [], []
        for i in range(SEQ_LEN, len(Xc)):
            Xs.append(Xc[i - SEQ_LEN:i])
            ys.append(yc[i])
            cs.append(code)
        if len(Xs) < 5:
            continue
        Xs, ys, cs = np.array(Xs), np.array(ys), np.array(cs)

        split = int(len(Xs) * 0.8)
        X_train_list.append(Xs[:split]); X_test_list.append(Xs[split:])
        comm_train_list.append(cs[:split]); comm_test_list.append(cs[split:])
        y_train_list.append(ys[:split]); y_test_list.append(ys[split:])

    if not X_train_list:
        return {
            "accuracy_score": 0.0, 
            "r2_score": 0.0, 
            "mae": None, 
            "rmse": None,
            "rows_trained": 0, 
            "note": "Not enough rows per commodity to train LSTM"
        }

    X_train_lstm = np.concatenate(X_train_list)
    X_test_lstm = np.concatenate(X_test_list)
    comm_train_lstm = np.concatenate(comm_train_list)
    comm_test_lstm = np.concatenate(comm_test_list)
    y_train_lstm = np.concatenate(y_train_list)
    y_test_lstm = np.concatenate(y_test_list)

    n_features = X_train_lstm.shape[2]
    emb_dim = min(8, n_commodities)

    seq_input = Input(shape=(X_train_lstm.shape[1], n_features), name="seq_input")
    x = LSTM(64, return_sequences=True)(seq_input)
    x = Dropout(0.2)(x)
    x = LSTM(32)(x)
    x = Dropout(0.2)(x)

    comm_input = Input(shape=(1,), name="comm_input")
    c = Embedding(input_dim=n_commodities, output_dim=emb_dim)(comm_input)
    c = Flatten()(c)

    merged = Concatenate()([x, c])
    merged = Dense(32, activation="relu")(merged)
    out = Dense(1)(merged)

    model = Model(inputs=[seq_input, comm_input], outputs=out)
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])

    if progress_callback:
        progress_callback(45, "Training LSTM neural network...")

    # Custom callback to update progress during training
    class ProgressCallback(Callback):
        def __init__(self, callback, total_epochs):
            super().__init__()
            self.callback = callback
            self.total_epochs = total_epochs
            self.current_epoch = 0

        def on_epoch_end(self, epoch, logs=None):
            self.current_epoch = epoch + 1
            if self.callback:
                progress = 45 + (self.current_epoch / self.total_epochs) * 30
                self.callback(min(75, progress), f"Training LSTM... ({self.current_epoch}/{self.total_epochs} epochs)")

    early_stop = EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True)
    reduce_lr = ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=5, min_lr=1e-5)
    progress_cb = ProgressCallback(progress_callback, LSTM_EPOCHS)

    model.fit(
        [X_train_lstm, comm_train_lstm], y_train_lstm,
        epochs=LSTM_EPOCHS, batch_size=16, validation_split=0.2,
        callbacks=[early_stop, reduce_lr, progress_cb], 
        verbose=0,
    )

    if progress_callback:
        progress_callback(75, "Evaluating LSTM model...")

    pred_scaled = model.predict([X_test_lstm, comm_test_lstm], verbose=0)

    lstm_pred_list, actual_list = [], []
    pos = 0
    codes_in_order = [c for c in df["Commodity_Code"].unique() if c in commodity_scalers]
    for code, y_test_c in zip(codes_in_order, y_test_list):
        n = len(y_test_c)
        sy = commodity_scalers[code]["y"]
        lstm_pred_list.append(sy.inverse_transform(pred_scaled[pos:pos + n]))
        actual_list.append(sy.inverse_transform(y_test_c))
        pos += n

    lstm_pred = np.concatenate(lstm_pred_list)
    actual = np.concatenate(actual_list)
    r2 = r2_score(actual, lstm_pred)
    mae = mean_absolute_error(actual, lstm_pred)
    rmse = np.sqrt(mean_squared_error(actual, lstm_pred))

    metrics = {
        "accuracy_score": round(max(0.0, r2) * 100, 2),
        "r2_score": round(float(r2), 4),
        "mae": round(float(mae), 2),
        "rmse": round(float(rmse), 2),
        "rows_trained": int(len(X_train_lstm)),
    }
    
    if collect_regression_data and len(actual) > 0 and len(lstm_pred) > 0:
        sample_size = min(100, len(actual))
        indices = np.random.choice(len(actual), sample_size, replace=False) if len(actual) > 100 else range(len(actual))
        metrics["regression_data"] = {
            "actual": [float(actual[i]) for i in indices],
            "predicted": [float(lstm_pred[i]) for i in indices]
        }

    model.save_weights(os.path.join(MODEL_DIR, "lstm_model.weights.h5"))
    joblib.dump(
        {"seq_len": SEQ_LEN, "n_features": n_features, "n_commodities": n_commodities, "emb_dim": emb_dim},
        os.path.join(MODEL_DIR, "lstm_config.pkl"),
    )
    joblib.dump(commodity_scalers, os.path.join(MODEL_DIR, "commodity_scalers.pkl"))

    if progress_callback:
        progress_callback(80, "LSTM training complete")

    return metrics


# ------------------------------------------------------------------
# 5. TRAIN ARIMA
# ------------------------------------------------------------------
def train_arima_all(df: pd.DataFrame, collect_regression_data=False, progress_callback=None):
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.stattools import adfuller

    # Clear old ARIMA files
    for fname in os.listdir(ARIMA_DIR):
        if fname.endswith(".pkl"):
            os.remove(os.path.join(ARIMA_DIR, fname))

    per_pair_metrics = {}
    all_actual = []
    all_predicted = []
    
    pairs = list(df.groupby(["Commodity", "Market"]))
    total_pairs = len(pairs)

    if progress_callback:
        progress_callback(82, f"Training ARIMA models for {total_pairs} commodity-market pairs...")

    for idx, ((commodity, market), sub) in enumerate(pairs):
        sub = sub.sort_values("Date")
        prices = sub["Modal_Price"].values
        pair_key = f"{commodity} @ {market}"

        if progress_callback:
            progress = 82 + (idx / total_pairs) * 13
            progress_callback(progress, f"ARIMA: {pair_key} ({idx+1}/{total_pairs})")

        if len(prices) < 40:
            per_pair_metrics[pair_key] = {
                "commodity": commodity, 
                "market": market,
                "accuracy_score": None, 
                "r2_score": None,
                "mae": None, 
                "rmse": None,
                "rows_trained": len(prices), 
                "note": "Too few rows (need 40+)",
            }
            continue

        split = int(len(prices) * 0.8)
        train_prices, test_prices = prices[:split], prices[split:]

        try:
            result = adfuller(train_prices)
            order = (5, 1, 0) if result[1] > 0.05 else (5, 0, 0)
            fit = ARIMA(train_prices, order=order).fit()

            forecast = fit.forecast(steps=len(test_prices))
            mae = mean_absolute_error(test_prices, forecast)
            rmse = np.sqrt(mean_squared_error(test_prices, forecast))
            r2 = r2_score(test_prices, forecast)

            safe_c = "".join(ch if ch.isalnum() else "_" for ch in str(commodity))
            safe_m = "".join(ch if ch.isalnum() else "_" for ch in str(market))
            with open(os.path.join(ARIMA_DIR, f"{safe_c}_{safe_m}.pkl"), "wb") as f:
                pickle.dump({"commodity": commodity, "market": market, "model": fit}, f)

            per_pair_metrics[pair_key] = {
                "commodity": commodity, 
                "market": market,
                "accuracy_score": round(max(0.0, r2) * 100, 2),
                "r2_score": round(float(r2), 4),
                "mae": round(float(mae), 2),
                "rmse": round(float(rmse), 2),
                "rows_trained": len(train_prices),
            }
            
            if collect_regression_data:
                all_actual.extend(test_prices.tolist())
                all_predicted.extend(forecast.tolist())
                
        except Exception as e:
            per_pair_metrics[pair_key] = {
                "commodity": commodity, 
                "market": market,
                "accuracy_score": None, 
                "r2_score": None,
                "mae": None, 
                "rmse": None,
                "rows_trained": len(prices), 
                "note": f"Training failed: {e}",
            }

    if progress_callback:
        progress_callback(95, "Finalizing ARIMA models...")

    if collect_regression_data and len(all_actual) > 0 and len(all_predicted) > 0:
        sample_size = min(100, len(all_actual))
        indices = np.random.choice(len(all_actual), sample_size, replace=False) if len(all_actual) > 100 else range(len(all_actual))
        per_pair_metrics["_regression_data"] = {
            "actual": [float(all_actual[i]) for i in indices],
            "predicted": [float(all_predicted[i]) for i in indices]
        }

    return per_pair_metrics


# ------------------------------------------------------------------
# 6. WRITE model_metrics.json
# ------------------------------------------------------------------
def write_flat_metrics_json(metrics: dict):
    flat = {}
    for key in ("linear_regression", "random_forest", "xgboost", "lstm"):
        if key in metrics and metrics[key] is not None:
            flat[key] = {
                "rmse": metrics[key].get("rmse"),
                "mae": metrics[key].get("mae"),
                "r2": metrics[key].get("r2_score"),
                "accuracy_score": metrics[key].get("accuracy_score"),
            }

    if "arima_by_pair" in metrics and metrics["arima_by_pair"]:
        valid = [m for m in metrics["arima_by_pair"].values() if m.get("rmse") is not None and isinstance(m, dict)]
        if valid:
            flat["arima"] = {
                "rmse": round(float(np.mean([m["rmse"] for m in valid])), 2),
                "mae": round(float(np.mean([m["mae"] for m in valid])), 2),
                "r2": round(float(np.mean([m["r2_score"] for m in valid])), 4),
                "accuracy_score": round(float(np.mean([m["accuracy_score"] for m in valid])), 2),
            }

    with open(METRICS_PATH, "w") as f:
        json.dump(flat, f, indent=2, default=str)


# ------------------------------------------------------------------
# 7. PROGRESS TRACKING ROUTE (Server-Sent Events / Streaming)
# ------------------------------------------------------------------
@admin_bp.route("/admin/train-progress", methods=["GET"])
@admin_required
def train_progress():
    """Stream training progress using Server-Sent Events"""
    def generate():
        # This is a placeholder - actual progress is sent from the training route
        # The frontend will receive updates via the /admin/train endpoint
        yield f"data: {json.dumps({'progress': 0, 'status': 'Waiting to start...'})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype="text/event-stream")


# ------------------------------------------------------------------
# 8. MAIN TRAINING ROUTE WITH PROGRESS
# ------------------------------------------------------------------
@admin_bp.route("/admin/train", methods=["POST"])
@admin_required
def train_models():
    if "dataset" not in request.files:
        return jsonify({"error": "No file uploaded. Expected form field 'dataset'."}), 400

    file = request.files["dataset"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        new_df = pd.read_csv(file)
    except Exception as e:
        return jsonify({"error": f"Could not read CSV: {e}"}), 400

    missing = [c for c in REQUIRED_COLUMNS if c not in new_df.columns]
    if missing:
        return jsonify({"error": f"CSV is missing required columns: {missing}"}), 400

    selected = request.form.get("models", "lr,rf,xgb,lstm,arima").split(",")
    selected = [m.strip() for m in selected if m.strip()]

    # Progress tracking function
    progress_updates = []

    def update_progress(percent, status):
        progress_updates.append({"progress": percent, "status": status})
        print(f"📊 Progress: {percent}% - {status}")

    try:
        update_progress(5, "📊 Reading CSV file...")
        
        # Append data to database
        rows_added = append_to_prices_db(new_df)
        update_progress(10, f"✅ Appended {rows_added} rows to database")

        # Load full dataset
        combined = load_full_dataset()
        update_progress(15, "📊 Loading dataset...")

        # Feature engineering
        df_fe, X, y, commodity_le = engineer_features(combined)
        joblib.dump(commodity_le, os.path.join(MODEL_DIR, "commodity_label_encoder.pkl"))
        joblib.dump(list(X.columns), os.path.join(MODEL_DIR, "feature_columns.pkl"))
        update_progress(20, "⚙️ Feature engineering complete")

        metrics = {"trained_at_rows_total": len(combined), "new_rows_added": rows_added}
        collect_regression = True
        
        # Count total models to train
        total_models = len([m for m in selected if m in ("lr", "rf", "xgb", "lstm", "arima")])
        models_trained = 0

        # Split data for tabular models
        if any(m in selected for m in ("lr", "rf", "xgb")):
            X_train, X_test, y_train, y_test = split_train_test(X, y)
            update_progress(22, "📊 Data split for training")

            # Linear Regression
            if "lr" in selected:
                update_progress(25, "📊 Training Linear Regression...")
                metrics["linear_regression"] = train_linear_regression_only(
                    X_train, X_test, y_train, y_test, collect_regression
                )
                models_trained += 1
                progress = 25 + (models_trained / total_models) * 20
                update_progress(min(progress, 45), f"✅ Linear Regression trained ({models_trained}/{total_models})")

            # Random Forest
            if "rf" in selected:
                update_progress(30, "🌳 Training Random Forest...")
                metrics["random_forest"] = train_random_forest_only(
                    X_train, X_test, y_train, y_test, collect_regression
                )
                models_trained += 1
                progress = 25 + (models_trained / total_models) * 20
                update_progress(min(progress, 45), f"✅ Random Forest trained ({models_trained}/{total_models})")

            # XGBoost
            if "xgb" in selected:
                update_progress(35, "🚀 Training XGBoost...")
                metrics["xgboost"] = train_xgboost_only(
                    X_train, X_test, y_train, y_test, collect_regression
                )
                models_trained += 1
                progress = 25 + (models_trained / total_models) * 20
                update_progress(min(progress, 45), f"✅ XGBoost trained ({models_trained}/{total_models})")

        # LSTM
        if "lstm" in selected:
            update_progress(45, "🧠 Preparing LSTM training...")
            metrics["lstm"] = train_lstm(df_fe, X, y, collect_regression, update_progress)
            models_trained += 1
            progress = 45 + (models_trained / total_models) * 35
            update_progress(min(progress, 80), f"✅ LSTM trained ({models_trained}/{total_models})")

        # ARIMA
        if "arima" in selected:
            update_progress(82, "📈 Training ARIMA models...")
            metrics["arima_by_pair"] = train_arima_all(df_fe, collect_regression, update_progress)
            models_trained += 1
            update_progress(95, f"✅ ARIMA trained ({models_trained}/{total_models})")

        # Combine regression data
        regression_data = {}
        for model_key in ["linear_regression", "random_forest", "xgboost", "lstm"]:
            if model_key in metrics and metrics[model_key] and "regression_data" in metrics[model_key]:
                regression_data[model_key] = metrics[model_key].pop("regression_data")
        
        if "arima_by_pair" in metrics and metrics["arima_by_pair"]:
            if "_regression_data" in metrics["arima_by_pair"]:
                regression_data["arima"] = metrics["arima_by_pair"].pop("_regression_data")
        
        if regression_data:
            priority = ["lstm", "arima", "xgboost", "random_forest", "linear_regression"]
            for key in priority:
                if key in regression_data:
                    metrics["regression_data"] = regression_data[key]
                    break

        # Write metrics
        write_flat_metrics_json(metrics)
        update_progress(98, "💾 Saving metrics...")

        with open(os.path.join(MODEL_DIR, "admin_last_run_metrics.json"), "w") as f:
            json.dump(metrics, f, indent=2, default=str)

        # Reload models
        reload_note = "Restart the server to use the new models."
        try:
            import app as main_app
            if hasattr(main_app, "reload_models"):
                main_app.reload_models()
                reload_note = "Live models reloaded -- no restart needed."
        except Exception as e:
            reload_note = f"Could not hot-reload models automatically ({e}). Restart the server."

        metrics["reload_status"] = reload_note
        update_progress(100, "🎉 Training complete!")

        return jsonify({"status": "success", "metrics": metrics, "progress": progress_updates})

    except Exception as e:
        update_progress(0, f"❌ Error: {str(e)}")
        return jsonify({"error": f"Training failed: {str(e)}"}), 500


@admin_bp.route("/admin/model-metrics", methods=["GET"])
@admin_required
def get_last_metrics():
    path = os.path.join(MODEL_DIR, "admin_last_run_metrics.json")
    if not os.path.exists(path):
        return jsonify({"metrics": None})
    with open(path) as f:
        return jsonify({"metrics": json.load(f)})