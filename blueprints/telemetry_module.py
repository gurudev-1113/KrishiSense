"""
Modules M1 (real-time monitoring) + M5 (advisory rule engine)
------------------------------------------------------------------
No physical ESP32 node was in scope for this integration pass, so this
module implements the FULL server side exactly as specced in the
synopsis (ingest endpoint, SQLite schema, threshold engine with
persistence + severity grading + de-duplication) and adds a background
simulator thread standing in for the field node, so the dashboard is
demoable without hardware. Swapping in the real ESP32 later requires
zero changes here -- it just needs to POST the same JSON shape to
/api/telemetry with the shared device token.
"""
import json
import os
import sqlite3
import threading
import time
import random
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, session, render_template

telemetry_bp = Blueprint("telemetry_bp", __name__)

TELEMETRY_DB = "telemetry.db"
DEVICE_TOKEN = os.environ.get("KRISHISENSE_DEVICE_TOKEN", "demo-node-token")
# Default is now OFF: no fake numbers are shown unless you explicitly ask
# for the demo. Set KRISHISENSE_HARDWARE_MODE=serial once your Arduino
# node is plugged in, or KRISHISENSE_HARDWARE_MODE=simulate if you
# specifically want the random-walk demo data back.
SIMULATE = os.environ.get("KRISHISENSE_SIMULATE", "0") == "1"
SIMULATE_INTERVAL_SEC = 10

# ------------------------------------------------------------
# Schema (synopsis §9 data model)
# ------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(TELEMETRY_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_telemetry_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            ts TEXT,
            moisture_pct REAL,
            air_temp_c REAL,
            humidity_pct REAL,
            soil_temp_c REAL,
            ph REAL,
            quarantined INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_raised TEXT,
            ts_cleared TEXT,
            rule_key TEXT,
            severity TEXT,
            message TEXT,
            acknowledged INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS disease_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            image_path TEXT,
            predicted_class TEXT,
            confidence REAL
        );
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            token_hash TEXT,
            last_seen TEXT
        );
    """)
    conn.commit()
    conn.execute(
        "INSERT OR IGNORE INTO devices (name, token_hash, last_seen) VALUES (?, ?, ?)",
        ("pot-node-1", DEVICE_TOKEN, None),
    )
    conn.commit()
    conn.close()


def log_disease_scan(image_path, predicted_class, confidence):
    conn = get_db()
    conn.execute(
        "INSERT INTO disease_scans (ts, image_path, predicted_class, confidence) VALUES (?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), image_path, predicted_class, confidence),
    )
    conn.commit()
    conn.close()


# ------------------------------------------------------------
# Advisory rule engine (synopsis §M5 rule table, verbatim)
# ------------------------------------------------------------
RULES = {
    "moisture_low":  {"severity": "warning",  "message": "Irrigate now -- root zone below the comfort band", "streak_needed": 3},
    "waterlogging":  {"severity": "warning",  "message": "Stop watering; check drainage before root rot sets in", "streak_needed": 3},
    "acidic_soil":   {"severity": "info",     "message": "Apply agricultural lime; most vegetables prefer 6.0-7.0", "streak_needed": 1},
    "alkaline_soil": {"severity": "info",     "message": "Add organic matter or gypsum; iron uptake will suffer", "streak_needed": 1},
    "heat_stress":   {"severity": "critical", "message": "Provide shade and irrigate in the evening", "streak_needed": 1},
    "fungal_risk":   {"severity": "warning",  "message": "Blight-favourable conditions -- run a leaf scan today", "streak_needed": 3},
    "node_offline":  {"severity": "critical", "message": "Sensor node unreachable -- check power and Wi-Fi", "streak_needed": 1},
}

_streaks = {k: 0 for k in RULES}
_lock = threading.Lock()


def _evaluate_conditions(reading):
    """Returns the set of rule_keys whose raw condition is true for this reading."""
    hit = set()
    if reading["moisture_pct"] is not None and reading["moisture_pct"] < 30:
        hit.add("moisture_low")
    if reading["moisture_pct"] is not None and reading["moisture_pct"] > 85:
        hit.add("waterlogging")
    if reading["ph"] is not None and reading["ph"] < 5.5:
        hit.add("acidic_soil")
    if reading["ph"] is not None and reading["ph"] > 7.5:
        hit.add("alkaline_soil")
    if reading["air_temp_c"] is not None and reading["air_temp_c"] > 38:
        hit.add("heat_stress")
    if (reading["humidity_pct"] is not None and reading["air_temp_c"] is not None
            and reading["humidity_pct"] > 85 and 18 <= reading["air_temp_c"] <= 28):
        hit.add("fungal_risk")
    return hit


def _active_alert(conn, rule_key):
    return conn.execute(
        "SELECT id FROM alerts WHERE rule_key=? AND ts_cleared IS NULL", (rule_key,)
    ).fetchone()


def _raise_alert(conn, rule_key):
    rule = RULES[rule_key]
    if _active_alert(conn, rule_key):
        return  # de-duplicated: already active
    conn.execute(
        "INSERT INTO alerts (ts_raised, ts_cleared, rule_key, severity, message, acknowledged) VALUES (?, NULL, ?, ?, ?, 0)",
        (datetime.utcnow().isoformat(), rule_key, rule["severity"], rule["message"]),
    )
    conn.commit()


def _clear_alert(conn, rule_key):
    active = _active_alert(conn, rule_key)
    if active:
        conn.execute(
            "UPDATE alerts SET ts_cleared=? WHERE id=?",
            (datetime.utcnow().isoformat(), active["id"]),
        )
        conn.commit()


def evaluate_rules(reading):
    """Threshold + persistence logic: a rule fires only after
    `streak_needed` consecutive breaches, and is re-armed only after
    the condition clears (synopsis M5)."""
    conditions_now = _evaluate_conditions(reading)
    conn = get_db()
    try:
        with _lock:
            for rule_key, rule in RULES.items():
                if rule_key == "node_offline":
                    continue  # handled separately, by absence of readings
                if rule_key in conditions_now:
                    _streaks[rule_key] += 1
                    if _streaks[rule_key] >= rule["streak_needed"]:
                        _raise_alert(conn, rule_key)
                else:
                    _streaks[rule_key] = 0
                    _clear_alert(conn, rule_key)
    finally:
        conn.close()


def check_node_offline():
    """No payload for 2 minutes -> Critical (checked by the simulator
    loop / could equally be a cron job in a real deployment)."""
    conn = get_db()
    try:
        last = conn.execute("SELECT ts FROM readings ORDER BY id DESC LIMIT 1").fetchone()
        if last:
            last_ts = datetime.fromisoformat(last["ts"])
            if datetime.utcnow() - last_ts > timedelta(minutes=2):
                _raise_alert(conn, "node_offline")
            else:
                _clear_alert(conn, "node_offline")
    finally:
        conn.close()


# ------------------------------------------------------------
# Ingest (Lane A) -- range/spike validation then insert
# ------------------------------------------------------------
RANGES = {
    "moisture_pct": (0, 100),
    "ph": (3, 10),
    "air_temp_c": (-5, 60),
    "soil_temp_c": (-5, 60),
    "humidity_pct": (0, 100),
}


def _in_range(field, value):
    if value is None:
        return True
    lo, hi = RANGES.get(field, (None, None))
    if lo is None:
        return True
    return lo <= value <= hi


@telemetry_bp.route("/api/telemetry", methods=["POST"])
def api_telemetry():
    """The only endpoint the field node ever calls."""
    token = request.headers.get("X-Device-Token")
    if token != DEVICE_TOKEN:
        return jsonify({"error": "invalid device token"}), 401

    payload = request.get_json(silent=True) or {}
    reading = {
        "device_id": payload.get("device_id", "pot-node-1"),
        "ts": payload.get("ts") or datetime.utcnow().isoformat(),
        "moisture_pct": payload.get("moisture_pct"),
        "air_temp_c": payload.get("air_temp_c"),
        "humidity_pct": payload.get("humidity_pct"),
        "soil_temp_c": payload.get("soil_temp_c"),
        "ph": payload.get("ph"),
    }

    quarantined = any(not _in_range(f, reading[f]) for f in RANGES)

    conn = get_db()
    conn.execute(
        """INSERT INTO readings (device_id, ts, moisture_pct, air_temp_c, humidity_pct, soil_temp_c, ph, quarantined)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (reading["device_id"], reading["ts"], reading["moisture_pct"], reading["air_temp_c"],
         reading["humidity_pct"], reading["soil_temp_c"], reading["ph"], int(quarantined)),
    )
    conn.execute("UPDATE devices SET last_seen=? WHERE name=?", (reading["ts"], reading["device_id"]))
    conn.commit()
    conn.close()

    if not quarantined:
        evaluate_rules(reading)

    return jsonify({"status": "ok", "quarantined": quarantined})


@telemetry_bp.route("/api/latest")
def api_latest():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    row = conn.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 1").fetchone()
    device = conn.execute("SELECT last_seen FROM devices WHERE name='pot-node-1'").fetchone()
    conn.close()
    if not row:
        return jsonify({"status": "no data yet"}), 200
    online = False
    if device and device["last_seen"]:
        online = (datetime.utcnow() - datetime.fromisoformat(device["last_seen"])) < timedelta(minutes=2)
    return jsonify({**dict(row), "node_online": online})


@telemetry_bp.route("/api/history")
def api_history():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    hours = int(request.args.get("hours", 24))
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM readings WHERE ts >= ? ORDER BY ts ASC", (since,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@telemetry_bp.route("/api/alerts")
def api_alerts():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM alerts ORDER BY ts_raised DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@telemetry_bp.route("/telemetry")
def telemetry_dashboard():
    if "user_id" not in session:
        from flask import redirect, url_for
        return redirect(url_for("login"))
    username = session.get("username", "User")
    return render_template(
        "telemetry_dashboard.html",
        username=username,
        hardware_status=get_hardware_status(),
    )


# ------------------------------------------------------------
# Field-node simulator (stands in for the ESP32 until one is wired up)
# ------------------------------------------------------------
def _simulate_loop():
    import urllib.request
    state = {"moisture": 55.0, "ph": 6.5}
    while True:
        # Gentle random walk so trend charts look like real sensor drift,
        # occasionally wandering into alert territory so rules can be seen firing.
        state["moisture"] = max(5, min(98, state["moisture"] + random.uniform(-4, 3)))
        state["ph"] = max(4.0, min(8.5, state["ph"] + random.uniform(-0.1, 0.1)))
        payload = {
            "device_id": "pot-node-1",
            "moisture_pct": round(state["moisture"], 1),
            "air_temp_c": round(random.uniform(20, 34), 1),
            "humidity_pct": round(random.uniform(50, 92), 1),
            "soil_temp_c": round(random.uniform(18, 30), 1),
            "ph": round(state["ph"], 2),
        }
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:5000/api/telemetry",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "X-Device-Token": DEVICE_TOKEN},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            print(f"[simulator] telemetry post failed: {e}")
        time.sleep(SIMULATE_INTERVAL_SEC)


def get_hardware_status():
    """Single source of truth for which sensor-node source is active:
      - 'serial'   -> real Arduino Uno over USB serial (COM6 etc.)
      - 'simulate' -> demo random-walk data, only when explicitly asked for
      - 'waiting'  -> neither -- the default. No numbers are fabricated;
                      the dashboard shows blank gauges until real hardware
                      (serial or a real ESP32 POSTing to /api/telemetry)
                      actually sends a reading.
    """
    hardware_mode = os.environ.get("KRISHISENSE_HARDWARE_MODE", "auto").lower()
    if hardware_mode == "serial":
        return "serial"
    if hardware_mode == "simulate" or SIMULATE:
        return "simulate"
    if hardware_mode == "off":
        return "waiting"

    # 'auto' (the default): use the real node if a serial device is
    # actually plugged in right now, otherwise just wait. This is what
    # made the node look broken before -- the mode defaulted to 'off',
    # so the reader never started unless you set an env var by hand.
    try:
        from blueprints.hardware_serial import list_available_ports
        if list_available_ports():
            return "serial"
    except Exception as e:
        print(f"[telemetry] serial auto-detect unavailable: {e}")
    return "waiting"


def start_simulator_if_enabled():
    status = get_hardware_status()
    if status == "serial":
        from blueprints.hardware_serial import start_hardware_reader
        start_hardware_reader()
        print("[telemetry] real hardware mode: reading the Arduino node over serial "
              "(set KRISHISENSE_HARDWARE_MODE=simulate for the demo, or unset it to just wait)")
    elif status == "simulate":
        t = threading.Thread(target=_simulate_loop, daemon=True)
        t.start()
        print("[telemetry] demo simulator started on purpose (KRISHISENSE_HARDWARE_MODE=simulate) "
              "-- set it to 'serial' once the Arduino node is plugged in")
    else:
        print("[telemetry] no serial device detected -- waiting for real hardware, "
              "no demo data will be shown. Plug the Arduino in and restart, "
              "force it with KRISHISENSE_HARDWARE_MODE=serial, "
              "or use =simulate for the random-walk demo.")


@telemetry_bp.route("/api/plant-health")
def api_plant_health():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        from blueprints.hardware_serial import get_plant_health_state
        return jsonify(get_plant_health_state())
    except Exception as e:
        return jsonify({"status": "unavailable", "message": str(e)})
