"""
Real Arduino / ESP32 sensor-node reader over USB serial.
------------------------------------------------------------------------
Reads the physical node (pH probe + DHT11 + HW-080 soil moisture + LCD)
over USB serial, prints every step to the terminal, stores each reading
in the backend, and once WINDOW_SIZE (10) readings are collected it
averages them and runs the plant-health RandomForest over the average.

What this module does, in order:
  1. Lists every serial device actually connected right now and asks you
     to CONFIRM which port to use (skippable -- see env vars below).
  2. Opens the port. If nothing parsable arrives it automatically retries
     the other common baud rates instead of sitting there silently.
  3. Parses each reading. Two wire formats are understood:
       a) block format (soilmoisture.ino):
              pH: 6.54
              Temperature: 27.30 C
              Humidity: 61.00 %
              Soil Raw: 742
              Soil: WATER NEEDED
              --------------------------------
       b) single-line key=value format (krishisense_node.ino):
              moisture=41.2% air=27.3C rh=61% soil=24.1C pH=6.54 link=ok
  4. Prints each reading to the terminal as [ n/10] and POSTs it to
     /api/telemetry, so the dashboard / history / alert engine all work
     unchanged.
  5. Keeps the last 10 readings in a rolling buffer. Once 10 are in, it
     prints the full 10-reading comparison table, averages them, scores
     the average with saved_models/plant_health_random_forest.pkl, and
     exposes the verdict on GET /api/plant-health.

Environment variables (all optional):
    KRISHISENSE_HARDWARE_MODE=serial   force serial mode
                              =simulate  demo random-walk data
                              =off       never read hardware
                              (unset)    AUTO: use serial if a port is found
    KRISHISENSE_SERIAL_PORT=COM9        skip the picker and use this port
    KRISHISENSE_SERIAL_BAUD=9600       preferred baud (others auto-tried)
    KRISHISENSE_SERIAL_CONFIRM=0       never prompt, just auto-pick
    KRISHISENSE_SERIAL_PROMPT_TIMEOUT=15   seconds before the prompt
                                           falls back to the auto-pick

Standalone port test (no Flask, no models -- just proves the wiring):
    python -m blueprints.hardware_serial
"""
import os
import re
import sys
import time
import queue
import threading
from collections import deque
from datetime import datetime

import numpy as np
import requests

DEVICE_TOKEN = os.environ.get("KRISHISENSE_DEVICE_TOKEN", "demo-node-token")
SERIAL_PORT_ENV = os.environ.get("KRISHISENSE_SERIAL_PORT")  # None => ask
SERIAL_BAUD = int(os.environ.get("KRISHISENSE_SERIAL_BAUD", "9600"))
TELEMETRY_URL = os.environ.get("KRISHISENSE_TELEMETRY_URL", "http://127.0.0.1:5000/api/telemetry")
DEVICE_ID = os.environ.get("KRISHISENSE_DEVICE_ID", "pot-node-1")
CONFIRM_PORT = os.environ.get("KRISHISENSE_SERIAL_CONFIRM", "1") != "0"
PROMPT_TIMEOUT = float(os.environ.get("KRISHISENSE_SERIAL_PROMPT_TIMEOUT", "15"))

PLANT_HEALTH_MODEL_PATH = os.path.join("saved_models", "plant_health_random_forest.pkl")
MODEL_FEATURES = ["PHvalues", "temperature", "humidity", "water needed or not"]
WINDOW_SIZE = 10  # readings to average before scoring plant health

# Baud rates tried in order if the preferred one yields nothing parsable.
CANDIDATE_BAUDS = [SERIAL_BAUD, 9600, 115200, 57600, 38400]
# Seconds of silence/garbage on a baud before trying the next one.
BAUD_PROBE_SECONDS = 12
# A block is also flushed after this many seconds of inactivity, so a
# sketch that never prints a "----" separator still produces readings.
BLOCK_IDLE_FLUSH_SEC = 3.0

# Soil ADC calibration -- the sketch gives a raw 0-1023 value plus a
# WATER NEEDED/WET flag at SOIL_THRESHOLD=600. Adjust these two if your
# HW-080 reads differently in a dry pot vs freshly watered soil.
SOIL_RAW_DRY = 900
SOIL_RAW_WET = 300

_last_raw_readings = deque(maxlen=WINDOW_SIZE)
_health_state = {
    "status": "warming_up",
    "message": f"Collecting the first {WINDOW_SIZE} hardware readings...",
    "readings_collected": 0,
    "port": None,
    "baud": None,
    "connected": False,
    "updated_at": None,
}
_health_lock = threading.Lock()
_plant_health_model = None
_reader_started = False
_total_readings = 0

# Telemetry POSTs go through this queue so a slow/unreachable HTTP call
# can never stall the serial read loop (which was silently dropping
# readings while requests.post blocked for its full timeout).
_post_queue = queue.Queue(maxsize=200)


# ------------------------------------------------------------------
# Port discovery + confirmation
# ------------------------------------------------------------------
def list_available_ports():
    """Every serial device currently attached. Returns a list of
    (device, description, hwid) tuples -- empty if pyserial is missing."""
    try:
        from serial.tools import list_ports
    except Exception as e:
        print(f"[hardware] pyserial not installed ({e}). Run: pip install pyserial")
        return []
    ports = []
    for p in sorted(list_ports.comports(), key=lambda x: x.device):
        ports.append((p.device, p.description or "", p.hwid or ""))
    return ports


def _looks_like_board(description, hwid):
    text = f"{description} {hwid}".lower()
    keywords = ("arduino", "ch340", "ch9102", "cp210", "ftdi", "usb serial",
                "wchusbserial", "silicon labs", "esp32", "usb-serial")
    return any(k in text for k in keywords)


def _auto_pick(ports):
    """Prefer something that actually looks like an Arduino/ESP32 board."""
    for device, desc, hwid in ports:
        if _looks_like_board(desc, hwid):
            return device
    return ports[0][0] if ports else None


def _input_with_timeout(prompt, timeout):
    """input() that gives up after `timeout` seconds, so an unattended
    server start never hangs forever on the confirmation prompt."""
    result = {}

    def _read():
        try:
            result["value"] = input(prompt)
        except Exception:
            result["value"] = ""

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        print(f"\n[hardware] no answer in {int(timeout)}s -- using the auto-pick.")
        return None
    return result.get("value")


def choose_port(interactive=None):
    """Print the connected devices and confirm which port to read.
    Returns a port name, or None if nothing is connected."""
    ports = list_available_ports()

    print("\n" + "=" * 62)
    print(" KrishiSense sensor node -- serial port check")
    print("=" * 62)

    if not ports:
        print(" No serial devices detected.")
        print(" Plug the Arduino/ESP32 in via USB, close the Arduino IDE")
        print(" Serial Monitor (it locks the port), then restart the server.")
        print("=" * 62 + "\n")
        return None

    print(f" Connected devices ({len(ports)} found):")
    for i, (device, desc, hwid) in enumerate(ports, start=1):
        tag = "  <-- looks like your board" if _looks_like_board(desc, hwid) else ""
        print(f"   [{i}] {device:<12} {desc}{tag}")

    # An explicit env var wins and skips the prompt entirely.
    if SERIAL_PORT_ENV:
        print(f"\n Using KRISHISENSE_SERIAL_PORT={SERIAL_PORT_ENV} (prompt skipped).")
        if SERIAL_PORT_ENV not in [p[0] for p in ports]:
            print(f" WARNING: {SERIAL_PORT_ENV} is not in the list above.")
        print("=" * 62 + "\n")
        return SERIAL_PORT_ENV

    default = _auto_pick(ports)

    if interactive is None:
        interactive = CONFIRM_PORT and sys.stdin is not None and sys.stdin.isatty()

    if not interactive:
        print(f"\n Auto-selected {default} (no terminal to prompt on).")
        print("=" * 62 + "\n")
        return default

    answer = _input_with_timeout(
        f"\n Confirm port [Enter = {default}, or type a number / port name]: ",
        PROMPT_TIMEOUT,
    )
    print("=" * 62 + "\n")

    if answer is None:
        return default
    answer = answer.strip()
    if not answer:
        return default
    if answer.isdigit():
        idx = int(answer) - 1
        if 0 <= idx < len(ports):
            return ports[idx][0]
        print(f"[hardware] {answer} is out of range -- using {default}.")
        return default
    return answer


# ------------------------------------------------------------------
# Model + parsing
# ------------------------------------------------------------------
def _load_plant_health_model():
    global _plant_health_model
    try:
        import joblib
        _plant_health_model = joblib.load(PLANT_HEALTH_MODEL_PATH)
        print(f"[hardware] plant health model loaded ({PLANT_HEALTH_MODEL_PATH})")
    except Exception as e:
        print(f"[hardware] could not load plant health model: {e}")
        _plant_health_model = None


def get_plant_health_state():
    with _health_lock:
        return dict(_health_state)


def _soil_raw_to_pct(raw):
    """Higher raw ADC = drier (per the sketch's comment). Map to 0-100%."""
    if raw is None:
        return None
    span = SOIL_RAW_WET - SOIL_RAW_DRY  # negative
    if span == 0:
        return None
    pct = (raw - SOIL_RAW_DRY) / span * 100.0
    return round(max(0.0, min(100.0, pct)), 1)


# Block format: "pH: 6.54", "Temperature: 27.3 C", ...
_LINE_PATTERNS = {
    "ph": re.compile(r"^p\s*h\s*[:=]\s*([-\d.]+)", re.I),
    "temperature": re.compile(r"^(?:temp|temperature|air)\s*[:=]\s*([-\d.]+)", re.I),
    "humidity": re.compile(r"^(?:humidity|hum|rh)\s*[:=]\s*([-\d.]+)", re.I),
    "soil_raw": re.compile(r"^soil\s*(?:raw|adc|value)\s*[:=]\s*([-\d.]+)", re.I),
    "moisture_pct": re.compile(r"^(?:moisture|soil\s*moisture)\s*[:=]\s*([-\d.]+)\s*%", re.I),
    "soil_state": re.compile(r"^soil\s*[:=]\s*([A-Za-z ]+)$", re.I),
}

# Single-line format: "moisture=41.2% air=27.3C rh=61% soil=24.1C pH=6.54"
_INLINE_PATTERNS = {
    "ph": re.compile(r"\bp\s*h\s*[:=]\s*([-\d.]+)", re.I),
    "temperature": re.compile(r"\b(?:air|temp|temperature)\s*[:=]\s*([-\d.]+)", re.I),
    "humidity": re.compile(r"\b(?:rh|humidity|hum)\s*[:=]\s*([-\d.]+)", re.I),
    "moisture_pct": re.compile(r"\bmoisture\s*[:=]\s*([-\d.]+)", re.I),
    "soil_raw": re.compile(r"\bsoil\s*(?:raw|adc)\s*[:=]\s*([-\d.]+)", re.I),
    "soil_temp": re.compile(r"\bsoil\s*[:=]\s*([-\d.]+)\s*C", re.I),
}


def _finalise(reading):
    """A reading needs pH to be usable. Derive whichever of
    moisture_pct / soil_raw / water_needed is missing."""
    if "ph" not in reading:
        return None
    if "moisture_pct" not in reading and "soil_raw" in reading:
        reading["moisture_pct"] = _soil_raw_to_pct(reading["soil_raw"])
    if "water_needed" not in reading:
        if "soil_raw" in reading:
            reading["water_needed"] = 1 if reading["soil_raw"] > 600 else 0
        elif reading.get("moisture_pct") is not None:
            reading["water_needed"] = 1 if reading["moisture_pct"] < 35 else 0
        else:
            reading["water_needed"] = 0
    return reading


def parse_inline(line):
    """Parse a single-line 'key=value key=value' reading. Returns None if
    the line isn't one."""
    reading = {}
    for key, pattern in _INLINE_PATTERNS.items():
        m = pattern.search(line)
        if m:
            try:
                reading[key] = float(m.group(1))
            except ValueError:
                pass
    # needs at least pH plus one other field to count as a real reading
    if "ph" not in reading or len(reading) < 2:
        return None
    return _finalise(reading)


def _parse_block(lines):
    """Turn the accumulated lines of one block into a reading dict."""
    reading = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        for key, pattern in _LINE_PATTERNS.items():
            m = pattern.match(line)
            if m:
                if key == "soil_state":
                    reading["water_needed"] = 1 if "WATER" in m.group(1).upper() else 0
                else:
                    try:
                        reading[key] = float(m.group(1))
                    except ValueError:
                        pass
                break
    return _finalise(reading)


# ------------------------------------------------------------------
# Scoring
# ------------------------------------------------------------------
def _score_plant_health(avg):
    if _plant_health_model is None:
        return {"status": "unavailable", "message": "Plant health model not loaded."}

    water_needed = 1 if avg.get("water_needed", 0) >= 0.5 else 0
    row = [avg.get("ph", 0.0), avg.get("temperature", 0.0),
           avg.get("humidity", 0.0), water_needed]
    try:
        # The model was fitted on a named DataFrame; passing one back
        # keeps sklearn from warning about missing feature names.
        try:
            import pandas as pd
            X = pd.DataFrame([row], columns=MODEL_FEATURES)
        except Exception:
            X = np.array([row])
        pred = _plant_health_model.predict(X)[0]
        proba = None
        if hasattr(_plant_health_model, "predict_proba"):
            proba = float(max(_plant_health_model.predict_proba(X)[0]))
    except Exception as e:
        return {"status": "error", "message": f"Prediction failed: {e}"}

    healthy = int(pred) == 1
    return {
        "status": "healthy" if healthy else "attention",
        "message": "Plant healthy" if healthy else "Plant not healthy -- check the alert feed",
        "confidence": proba,
        "averaged_over": len(_last_raw_readings),
        "inputs": {
            "ph": round(avg.get("ph", 0.0), 2),
            "temperature": round(avg.get("temperature", 0.0), 1),
            "humidity": round(avg.get("humidity", 0.0), 1),
            "water_needed": water_needed,
        },
    }


def _print_window_table():
    """Print the 10 buffered readings side by side, then the average."""
    print("\n" + "-" * 62)
    print(f" {WINDOW_SIZE}-reading window complete -- comparing:")
    print(f" {'#':>2}  {'pH':>6}  {'Temp C':>7}  {'Hum %':>7}  {'Soil':>6}  {'Water':>5}")
    for i, r in enumerate(_last_raw_readings, start=1):
        print(f" {i:>2}  {r.get('ph', 0):>6.2f}  {r.get('temperature', 0):>7.1f}  "
              f"{r.get('humidity', 0):>7.1f}  {str(r.get('soil_raw', '-')):>6}  "
              f"{r.get('water_needed', 0):>5}")
    print("-" * 62)


def _post_worker():
    """Drains the telemetry queue on its own thread."""
    while True:
        payload = _post_queue.get()
        try:
            requests.post(
                TELEMETRY_URL, json=payload,
                headers={"X-Device-Token": DEVICE_TOKEN}, timeout=5,
            )
        except Exception as e:
            print(f"[hardware] telemetry post failed (is the server up?): {e}")
        finally:
            _post_queue.task_done()


def _queue_telemetry(reading):
    payload = {
        "device_id": DEVICE_ID,
        "ts": datetime.utcnow().isoformat(),
        "moisture_pct": reading.get("moisture_pct"),
        "air_temp_c": reading.get("temperature"),
        "humidity_pct": reading.get("humidity"),
        "soil_temp_c": reading.get("soil_temp"),
        "ph": reading.get("ph"),
    }
    try:
        _post_queue.put_nowait(payload)
    except queue.Full:
        print("[hardware] telemetry backlog full -- dropping one reading.")


def _handle_reading(reading):
    global _total_readings
    _total_readings += 1

    _last_raw_readings.append(reading)
    n = len(_last_raw_readings)

    print(f"[hardware] [{n:>2}/{WINDOW_SIZE}] #{_total_readings}  "
          f"pH={reading.get('ph')}  Temp={reading.get('temperature')}C  "
          f"Humidity={reading.get('humidity')}%  Soil={reading.get('soil_raw')}  "
          f"Moisture={reading.get('moisture_pct')}%  "
          f"WaterNeeded={bool(reading.get('water_needed'))}")

    _queue_telemetry(reading)

    with _health_lock:
        _health_state["readings_collected"] = n
        _health_state["updated_at"] = datetime.utcnow().isoformat()
        if n < WINDOW_SIZE:
            _health_state["status"] = "warming_up"
            _health_state["message"] = f"Collected {n}/{WINDOW_SIZE} readings..."
            return

    _print_window_table()
    avg = {
        "ph": float(np.mean([r.get("ph", 0.0) for r in _last_raw_readings])),
        "temperature": float(np.mean([r.get("temperature", 0.0) for r in _last_raw_readings])),
        "humidity": float(np.mean([r.get("humidity", 0.0) for r in _last_raw_readings])),
        "water_needed": float(np.mean([r.get("water_needed", 0) for r in _last_raw_readings])),
    }
    result = _score_plant_health(avg)
    print(f" average -> pH={avg['ph']:.2f}  Temp={avg['temperature']:.1f}C  "
          f"Humidity={avg['humidity']:.1f}%  WaterNeeded={avg['water_needed']:.2f}")
    print(f" verdict -> {result.get('status','?').upper()}: {result.get('message','')}")
    print("-" * 62 + "\n")

    with _health_lock:
        _health_state.update(result)


# ------------------------------------------------------------------
# Serial loop
# ------------------------------------------------------------------
def _read_stream(ser, baud, probe_only=False):
    """Read the port until it dies. Returns True if at least one reading
    was parsed. With probe_only=True it gives up after BAUD_PROBE_SECONDS
    with no reading, so the caller can try the next baud rate."""
    import serial  # noqa: F401  (import here so a missing pyserial is caught by the caller)

    buffer_lines = []
    got_reading = False
    started = time.time()
    last_line_at = time.time()
    saw_bytes = False

    while True:
        raw_line = ser.readline()
        now = time.time()

        if not raw_line:
            # Idle: flush a pending block so sketches without a "----"
            # separator still emit readings.
            if buffer_lines and (now - last_line_at) > BLOCK_IDLE_FLUSH_SEC:
                reading = _parse_block(buffer_lines)
                buffer_lines = []
                if reading:
                    got_reading = True
                    _handle_reading(reading)
            if probe_only and not got_reading and (now - started) > BAUD_PROBE_SECONDS:
                return got_reading, saw_bytes
            continue

        saw_bytes = True
        last_line_at = now
        line = raw_line.decode(errors="ignore").strip()
        if not line:
            continue

        # Separator ends a block.
        if set(line) <= set("-=_*# ") and len(line) >= 4:
            if buffer_lines:
                reading = _parse_block(buffer_lines)
                buffer_lines = []
                if reading:
                    got_reading = True
                    _handle_reading(reading)
            continue

        # A complete single-line reading is handled immediately.
        inline = parse_inline(line)
        if inline:
            got_reading = True
            _handle_reading(inline)
            buffer_lines = []
            continue

        buffer_lines.append(line)
        # Safety valve: never let a runaway block grow forever.
        if len(buffer_lines) > 40:
            buffer_lines = buffer_lines[-20:]

        if probe_only and not got_reading and (now - started) > BAUD_PROBE_SECONDS:
            return got_reading, saw_bytes


def _serial_loop(port):
    try:
        import serial
    except Exception as e:
        print(f"[hardware] pyserial missing ({e}). Run: pip install pyserial")
        return

    _load_plant_health_model()

    # De-duplicated, preferred baud first.
    bauds = list(dict.fromkeys(CANDIDATE_BAUDS))
    baud_idx = 0
    confirmed_baud = None

    while True:
        baud = confirmed_baud or bauds[baud_idx % len(bauds)]
        ser = None
        try:
            print(f"[hardware] connecting to {port} @ {baud} baud...")
            ser = serial.Serial(port, baud, timeout=1)
            time.sleep(2)  # let the board finish its boot/reset
            ser.reset_input_buffer()
            print(f"[hardware] CONNECTED on {port} @ {baud} baud. Waiting for readings...")

            with _health_lock:
                _health_state["connected"] = True
                _health_state["port"] = port
                _health_state["baud"] = baud

            probing = confirmed_baud is None
            got, saw_bytes = _read_stream(ser, baud, probe_only=probing)

            if got:
                confirmed_baud = baud
            else:
                if saw_bytes:
                    print(f"[hardware] data arrived on {port} @ {baud} but nothing parsed "
                          f"(likely wrong baud) -- trying the next rate.")
                else:
                    print(f"[hardware] silence on {port} @ {baud} -- trying the next rate.")
                baud_idx += 1
                try:
                    ser.close()
                except Exception:
                    pass
                continue

        except Exception as e:
            with _health_lock:
                _health_state["connected"] = False
            print(f"[hardware] {port} not connected / read error: {e}")
            if "PermissionError" in str(type(e)) or "Access is denied" in str(e):
                print("[hardware] the port is held by something else -- close the "
                      "Arduino IDE Serial Monitor (and any other terminal) and retry.")
            print("[hardware] retrying in 5s...")
            time.sleep(5)
        finally:
            if ser is not None:
                try:
                    ser.close()
                except Exception:
                    pass


def start_hardware_reader(port=None):
    """Confirm the port on the main thread (so the prompt actually works),
    then read it on a background thread."""
    global _reader_started

    # Flask's debug reloader runs this file twice; the second process
    # would fight the first for exclusive access to the COM port.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "false":
        return None
    if _reader_started:
        print("[hardware] reader already running -- not starting a second one.")
        return None

    if port is None:
        port = choose_port()
    if not port:
        print("[hardware] no port selected -- sensor node is idle. "
              "Plug the board in and restart, or set KRISHISENSE_SERIAL_PORT.")
        return None

    _reader_started = True
    with _health_lock:
        _health_state["port"] = port

    threading.Thread(target=_post_worker, daemon=True).start()
    threading.Thread(target=_serial_loop, args=(port,), daemon=True).start()
    print(f"[hardware] serial reader thread started for {port} "
          f"({WINDOW_SIZE}-reading average -> plant health model)")
    return port


# ------------------------------------------------------------------
# Standalone test:  python -m blueprints.hardware_serial
# ------------------------------------------------------------------
if __name__ == "__main__":
    chosen = choose_port(interactive=True)
    if not chosen:
        sys.exit(1)
    print(f"[hardware] standalone mode -- reading {chosen}, Ctrl+C to stop.\n")
    threading.Thread(target=_post_worker, daemon=True).start()
    try:
        _serial_loop(chosen)
    except KeyboardInterrupt:
        print("\n[hardware] stopped.")
