# 🌱 KrishiSense: Next-Gen AI & IoT Precision Agriculture Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![ESP32](https://img.shields.io/badge/Hardware-ESP32%20DevKit%20V1-red.svg?logo=espressif&logoColor=white)](https://www.espressif.com/)
[![Machine Learning](https://img.shields.io/badge/ML-Scikit--Learn%20%7C%20TensorFlow-orange.svg?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Gemini AI](https://img.shields.io/badge/AI-Google%20Gemini%201.5%20Flash-8E75B2.svg?logo=google&logoColor=white)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**KrishiSense** is an end-to-end smart agriculture ecosystem combining **real-time field IoT telemetry**, **machine learning price forecasting**, **computer vision crop disease diagnosis**, and **generative AI advisory** to empower farmers with data-driven decision-making.

---

## 📌 Table of Contents
- [Architecture & System Workflow](#-architecture--system-workflow)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [IoT Hardware & Pinout](#-iot-hardware--pinout)
- [Quick Start Guide](#-quick-start-guide)
  - [Prerequisites](#prerequisites)
  - [Local Installation](#local-installation)
  - [Environment Configuration](#environment-configuration)
  - [Running the Application](#running-the-application)
- [Deploying IoT Sensor Nodes](#-deploying-iot-sensor-nodes)
- [Core API Endpoints](#-core-api-endpoints)
- [Project Directory Structure](#-project-directory-structure)
- [Contributing & License](#-contributing--license)

---

## 🏛 Architecture & System Workflow

```
                        [ In-Field IoT Node (ESP32) ]
              [ Soil Moisture | pH | DHT22 Air | DS18B20 Soil ]
                                     │
                                     │ (HTTPS POST + Token)
                                     ▼
                        ┌────────────────────────┐
                        │    KrishiSense Core    │
                        │     (Flask Backend)    │
                        └────────────┬───────────┘
                                     │
     ┌───────────────────┬───────────┴───────────┬───────────────────┐
     ▼                   ▼                       ▼                   ▼
[APMC Price Models]  [Vision Disease Scan]  [Crop Recommendation] [Multilingual Bot]
 (LSTM / Prophet /     (MobileNetV2 CNN &      (XGBoost / Random    (Google Gemini 1.5
  Random Forest)         Gemini 1.5 Flash)       Forest Classifier)   Live Tool Use)
     │                   │                       │                   │
     └───────────────────┴───────────┬───────────┴───────────────────┘
                                     ▼
                     [ Farmer Web App & Admin MLOps ]
                    (Live Gauges, Forecasts, Charts)
```

---

## 🚀 Key Features

### 1. 📈 Mandi Market Price Forecasting
- Analyzes historical APMC mandi trading transaction data across multiple Indian markets and commodities.
- Provides day-ahead market forecasting using ensemble models (LSTM, Prophet, Random Forest, Linear Regression).
- Distinguishes between the **last market trading session** (weekdays) and the **forecast target date**.

### 2. 🧪 Real-Time IoT Soil & Environment Telemetry
- Real-time ingestion of soil moisture, soil temperature, air temperature, relative humidity, and soil pH.
- In-memory event stream with automated threshold alert engine (low moisture, high temperature, irregular pH).
- Offline fault-tolerant ring buffer on ESP32 nodes to prevent data loss during farm network outages.

### 3. 🔬 Computer Vision Plant Disease Diagnosis
- Dual-engine diagnostic pipeline:
  - **Edge CNN (MobileNetV2):** Instant offline classification across plant disease categories.
  - **Gemini 1.5 Vision:** Detailed generative biological assessment providing cause, severity, organic cures, and chemical remedies.

### 4. 🌾 Precision Crop Recommendation
- Recommends the most suitable and profitable crops based on live or manual N-P-K levels, soil pH, moisture, and microclimate temperature.

### 5. 🤖 Multilingual Agri-Advisory Chatbot
- Voice-enabled, multilingual AI assistant powered by Google Gemini with tool calling capabilities:
  - Fetches real-time field telemetry directly from the database.
  - Queries live commodity price trends on demand.

### 6. 🛡️ Admin MLOps Console
- Role-gated dashboard for administrators to monitor telemetry statistics, review active sensor nodes, audit actual model performance metrics (RMSE, MAE, R²), and trigger automated dataset re-training.

---

## 💻 Tech Stack

- **Backend:** Python 3.10+, Flask, Jinja2, SQLite3
- **Machine Learning & AI:** TensorFlow / Keras, Scikit-learn, XGBoost, Prophet, Google Gemini API
- **Frontend:** HTML5, Modern CSS / Tailwind, JavaScript (Vanilla ES6+), ApexCharts / Chart.js, Leaflet.js
- **IoT & Hardware:** ESP32 DevKit V1, C++ (Arduino Core), HTTPClient, ArduinoJson, OneWire

---

## 🔌 IoT Hardware & Pinout

The physical node measures in-field microclimate metrics and communicates with the backend via Wi-Fi (or USB serial gateway).

| Component | Pin / Interface | Description |
| :--- | :--- | :--- |
| **ESP32 DevKit V1** | Core Controller | 30-pin Dual Core Wi-Fi/BLE MCU |
| **Capacitive Moisture Sensor v2.0** | `GPIO 34` (ADC1_CH6) | Corrosion-resistant analog soil moisture |
| **pH Probe / PH4502C** | `GPIO 35` (ADC1_CH7) | Soil pH monitoring (via 10k divider) |
| **DHT22** | `GPIO 4` (Digital) | Ambient Air Temperature & Relative Humidity |
| **DS18B20 (Waterproof)** | `GPIO 5` (OneWire) | Sub-surface Soil Temperature |
| **SSD1306 OLED (128x64)** | `GPIO 21` (SDA), `GPIO 22` (SCL) | On-field diagnostics display |
| **Relay Module (Optional)** | `GPIO 27` (Digital Output) | Automated irrigation pump control |

Firmware source code: [`firmware/krishisense_node/krishisense_node.ino`](firmware/krishisense_node/krishisense_node.ino)

---

## 🏁 Quick Start Guide

### Prerequisites
- Python 3.10, 3.11, or 3.12 (or 3.14) installed on your system.
- Git and Git LFS installed (`git lfs install`).
- *(Optional for hardware)* Arduino IDE with ESP32 board support.

### Local Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/gurudev-1113/KrishiSense.git
   cd KrishiSense
   ```

2. **Pull Large Files (Models & Datasets):**
   ```bash
   git lfs pull
   ```

3. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

4. **Install required packages:**
   ```bash
   pip install -r requirements.txt
   ```

### Environment Configuration

Create a `.env` file in the root directory (or use default development fallbacks):

```ini
# Flask Secret Key
SECRET_KEY=your_secure_random_key

# IoT Ingestion Security Token (Must match the token in the ESP32 firmware)
KRISHISENSE_DEVICE_TOKEN=demo-node-token

# Google Gemini API Key (Required for AI Chatbot and Vision Diagnostics)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
```

### Running the Application

- **On Windows (Direct Launcher):**
  Double click [`run.bat`](run.bat) or execute:
  ```cmd
  run.bat
  ```

- **Standard CLI:**
  ```bash
  python app.py
  ```

Once running, navigate to:
- **Public Farmer Portal:** `http://localhost:5000`
- **IoT Telemetry Dashboard:** `http://localhost:5000/telemetry`
- **Crop Disease Scanner:** `http://localhost:5000/disease`
- **Crop Recommendation:** `http://localhost:5000/crop`
- **Admin Dashboard:** `http://localhost:5000/admin-dashboard` *(Sign in with admin credentials)*

---

## 📡 Deploying IoT Sensor Nodes

### Cloud Wi-Fi Mode (HTTP REST)
When deploying KrishiSense to a public cloud or VPS:
1. Open [`firmware/krishisense_node/krishisense_node.ino`](firmware/krishisense_node/krishisense_node.ino) in Arduino IDE.
2. Update the credentials and server domain:
   ```cpp
   const char* WIFI_SSID     = "YOUR_WIFI_OR_HOTSPOT_SSID";
   const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
   const char* SERVER_HOST   = "https://your-krishisense-domain.com";
   const char* DEVICE_TOKEN  = "your-device-token"; // Matches KRISHISENSE_DEVICE_TOKEN
   ```
3. Flash the code to your ESP32. The node will now stream telemetry every 10 seconds to your live server.

### Local USB Gateway Mode
If you prefer running a direct USB connection to a farm gateway (e.g., Raspberry Pi or local PC):
```bash
python -m blueprints.hardware_serial
```
The script auto-detects connected serial ports, parses sensor streams, and pushes data to `/api/telemetry`.

---

## 🔌 Core API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/telemetry` | Ingests sensor readings from ESP32 (`X-Device-Token` header required) |
| `GET` | `/api/telemetry/latest` | Returns the most recent readings for connected sensor nodes |
| `POST` | `/api/predict` | Computes commodity price forecast for target commodity & market |
| `POST` | `/api/crop/recommend` | Evaluates NPK, pH, and climate data to recommend suitable crops |
| `POST` | `/api/disease/diagnose` | Classifies leaf disease from an uploaded image |
| `POST` | `/api/assistant/chat` | Multilingual generative advisory conversation |

---

## 📁 Project Directory Structure

```text
KrishiSense/
├── app.py                      # Main Flask application & routing hub
├── run.bat                     # Windows one-click environment launcher
├── admin_dashboard.py          # Admin monitoring & MLOps routes
├── admin_training.py           # Automated model retraining engine
├── blueprints/
│   ├── assistant_module.py     # Gemini AI advisory chatbot
│   ├── crop_module.py          # Crop recommendation service
│   ├── disease_module.py       # Plant pathology vision diagnosis
│   ├── hardware_serial.py      # USB Serial hardware gateway
│   └── telemetry_module.py     # IoT ingestion, alerts & streaming
├── firmware/
│   └── krishisense_node/
│       └── krishisense_node.ino# ESP32 C++ firmware with ring buffer
├── models/                     # Trained ML models (Prophet, LSTM, XGBoost)
├── saved_models/               # Model weights & evaluation metrics
├── static/                     # CSS, JavaScript UI scripts, icons, audio
├── templates/                  # Responsive Jinja2 HTML templates
├── prices.db                   # Mandi trade transactions database
├── telemetry.db                # Real-time sensor logs and alerts
└── users.db                    # User accounts & activity logs
```

---

## 📜 Contributing & License

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/gurudev-1113/KrishiSense/issues).

Distributed under the **MIT License**. See `LICENSE` for more information.
