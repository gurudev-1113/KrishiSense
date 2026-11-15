# KrishiSense IoT Setup Guide

## 🌱 **IoT System Overview**

KrishiSense collects real-time sensor data from your farm through Arduino/ESP32 microcontrollers and displays it on a live dashboard with intelligent alerts.

### **System Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    KrishiSense Backend                      │
│  (Flask Server on PC/Laptop/RPi) - http://192.168.1.50:5000│
└─────────────────────────────────────────────────────────────┘
              ↑              ↑              ↑
        USB Serial    WiFi/4G API    Cloud (Optional)
              │              │              │
    ┌─────────┴──────┬──────┴─────────┬────┴───────┐
    │                │                │            │
┌───▼────┐  ┌────────▼────┐  ┌───────▼──┐  ┌─────▼──┐
│Arduino │  │   ESP32     │  │  4G/WiFi │  │ Raspberry
│  Uno   │  │   Node      │  │  Modem   │  │   Pi
└────────┘  └─────────────┘  └──────────┘  └────────┘
    │            │                │             │
    └────┬───────┴─────┬──────────┴─────────────┘
         │
    ┌────▼──────────────────────────────┐
    │    Field Sensors (IoT Devices)    │
    │  • Soil Moisture (HW-080)         │
    │  • Temperature (DHT11/DHT22)      │
    │  • Humidity (DHT11/DHT22)         │
    │  • pH Probe (Analog)              │
    │  • Rain Sensor (Optional)         │
    │  • UV Light (Optional)            │
    └───────────────────────────────────┘
```

---

## 🔧 **Hardware Requirements**

### **Essential Components:**

| Component | Model | Purpose | Cost |
|-----------|-------|---------|------|
| **Microcontroller** | Arduino Uno / ESP32 | Data collection & processing | $5-15 |
| **Soil Moisture** | HW-080 / Capacitive | Soil water content | $3-8 |
| **Temperature/Humidity** | DHT11 / DHT22 | Air conditions | $2-10 |
| **pH Probe** | Analog pH sensor | Soil pH level | $10-30 |
| **Power Supply** | 5V USB / Solar | Continuous operation | $5-50 |
| **USB Cable** | USB-A to Micro-B | Arduino connection | $2 |

### **Optional Sensors:**

- **Rain Sensor** (YL-83) — $2-5
- **UV Sensor** (ML8511) — $5-10
- **Light Intensity** (LDR) — $1-3
- **Wind Speed** (Anemometer) — $20-50
- **GPS Module** (Neo-6M) — $10-15

### **Total IoT Setup Cost:**
- **Basic**: $25-50 (moisture + temperature + pH)
- **Standard**: $50-100 (+ rain, light sensors)
- **Advanced**: $100-200 (WiFi, SD card, multiple nodes)

---

## 📋 **Step 1: Arduino Setup**

### **Install Arduino IDE**

```bash
1. Download: https://www.arduino.cc/en/software
2. Install on Windows/Mac/Linux
3. Connect Arduino to PC via USB
4. Tools → Board → Arduino Uno
5. Tools → Port → COM3 (or your port)
```

### **Arduino Code (Soil Moisture + Temperature + pH)**

```cpp
// KrishiSense_IoT_Node.ino
// Reads sensors and sends to Flask backend

#include <DHT.h>

// Pin definitions
#define DHT_PIN 5
#define DHT_TYPE DHT11
#define MOISTURE_PIN A0
#define pH_PIN A1
#define PUMP_PIN 6

DHT dht(DHT_PIN, DHT_TYPE);

// Calibration values
#define DRY_VALUE 800
#define WET_VALUE 400
#define pH_MIN 0
#define pH_MAX 14

void setup() {
  Serial.begin(9600);
  dht.begin();
  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, LOW);
}

void loop() {
  // Read sensors
  float humidity = dht.readHumidity();
  float air_temp = dht.readTemperature();
  int moisture_raw = analogRead(MOISTURE_PIN);
  float ph_raw = analogRead(pH_PIN) * (5.0 / 1023.0);
  float soil_temp = air_temp; // Use air temp as approximation
  
  // Convert moisture to percentage
  float moisture_pct = map(moisture_raw, DRY_VALUE, WET_VALUE, 0, 100);
  moisture_pct = constrain(moisture_pct, 0, 100);
  
  // Convert pH (simple linear mapping)
  float ph = pH_MIN + (ph_raw / 5.0) * (pH_MAX - pH_MIN);
  
  // Auto-irrigation logic
  if (moisture_pct < 30) {
    digitalWrite(PUMP_PIN, HIGH);  // Turn on pump
  } else if (moisture_pct > 60) {
    digitalWrite(PUMP_PIN, LOW);   // Turn off pump
  }
  
  // Print data (block format for Python parser)
  Serial.println("Soil: " + String(moisture_pct, 1) + "%");
  Serial.println("Temperature: " + String(air_temp, 2) + " C");
  Serial.println("Humidity: " + String(humidity, 2) + "%");
  Serial.println("Soil_Temp: " + String(soil_temp, 2) + " C");
  Serial.println("pH: " + String(ph, 2));
  Serial.println("Moisture_Raw: " + String(moisture_raw));
  Serial.println("--------------------------------");
  
  // Send every 10 seconds
  delay(10000);
}
```

### **Alternative: Single-Line Format (for parsing simplicity)**

```cpp
// Simpler format - all data in one line
void send_data() {
  float humidity = dht.readHumidity();
  float air_temp = dht.readTemperature();
  int moisture_pct = get_moisture_percentage();
  float ph = get_ph_value();
  float soil_temp = air_temp;
  
  Serial.print("moisture=");
  Serial.print(moisture_pct);
  Serial.print("% air=");
  Serial.print(air_temp);
  Serial.print("C rh=");
  Serial.print(humidity);
  Serial.print("% soil=");
  Serial.print(soil_temp);
  Serial.print("C pH=");
  Serial.print(ph);
  Serial.println(" link=ok");
}
```

---

## 🔌 **Step 2: Wiring Diagram**

### **Arduino Uno Connections**

```
DHT11 (Temperature/Humidity):
  • VCC   → 5V
  • GND   → GND
  • DATA  → Pin 5

HW-080 Soil Moisture:
  • VCC   → 5V
  • GND   → GND
  • A0    → A0 (Analog)

pH Probe (Analog):
  • VCC   → 5V
  • GND   → GND
  • OUT   → A1 (Analog)

Pump Relay (Optional):
  • VCC   → 5V
  • GND   → GND
  • IN    → Pin 6 (Digital)
  • COM   → Pump Power +
  • NO    → Pump Power -
```

### **Visual Wiring (ASCII)**

```
┌─────────────────────────────────────┐
│         Arduino Uno                 │
│  [5V] [GND] [A0] [A1] [5] [6] ...  │
│   │    │     │    │    │   │        │
│   │    │     │    │    │   └─ Pump Relay
│   │    │     │    │    └──── DHT11
│   │    │     │    └───────── pH Sensor
│   │    │     └────────────── Soil Moisture
│   │    └──────────────────── Common Ground
│   └───────────────────────── Power
└─────────────────────────────────────┘
```

---

## 🖥️ **Step 3: Test Without Hardware**

### **Run Demo Mode (Simulated Sensor Data)**

```bash
# Terminal/PowerShell:
set KRISHISENSE_HARDWARE_MODE=simulate
python app.py

# Now visit: http://localhost:5000/telemetry
# You'll see fake sensor data updating in real-time
```

### **View Telemetry Dashboard**

```
http://localhost:5000/telemetry

Shows:
✓ Live readings (moisture, temp, humidity, pH)
✓ Charts over time
✓ Alert history
✓ Plant health score
✓ Irrigation recommendations
```

---

## 📡 **Step 4: Connect Real Arduino**

### **1. Upload Code to Arduino**

```bash
1. Open Arduino IDE
2. File → New → Paste KrishiSense_IoT_Node.ino
3. Select Tools → Board → Arduino Uno
4. Select Tools → Port → COM3 (your port)
5. Click Upload ➔
6. Wait for "Upload complete"
```

### **2. Plug in Arduino to PC**

```bash
USB Arduino → PC USB Port
```

### **3. Start Flask with Serial Mode**

```bash
# Terminal:
set KRISHISENSE_HARDWARE_MODE=serial
set KRISHISENSE_SERIAL_PORT=COM3
set KRISHISENSE_SERIAL_BAUD=9600

python app.py

# Output:
# [telemetry] Opening COM3 at 9600 baud...
# [telemetry] Connected!
# [telemetry] Reading from pot-node-1
# [telemetry] Reading 1: moisture=45.3% temp=27.2C ...
```

### **4. Verify in Dashboard**

```
http://localhost:5000/telemetry
✓ Real sensor values appearing
✓ Charts updating live
✓ Alerts triggering
✓ Plant health calculated
```

---

## 🚨 **Alert System**

### **Built-In Alerts Trigger When:**

| Alert | Condition | Action |
|-------|-----------|--------|
| **Low Moisture** | < 20% | Water plant immediately |
| **High Moisture** | > 80% | Stop watering, improve drainage |
| **Temperature High** | > 35°C | Increase shade/ventilation |
| **Temperature Low** | < 10°C | Move indoors or use heater |
| **Low Humidity** | < 30% | Mist plant, increase moisture |
| **High Humidity** | > 85% | Improve air circulation |
| **pH Too Low** | < 6.0 | Add lime, adjust soil |
| **pH Too High** | > 8.0 | Add sulfur, acidify soil |

### **Configure Thresholds**

```python
# In blueprints/telemetry_module.py:

THRESHOLDS = {
    'moisture_min': 20,      # %
    'moisture_max': 80,      # %
    'temp_min': 10,          # °C
    'temp_max': 35,          # °C
    'humidity_min': 30,      # %
    'humidity_max': 85,      # %
    'ph_min': 6.0,
    'ph_max': 8.0,
}
```

---

## 📊 **Step 5: Data Viewing & Analysis**

### **Real-Time Dashboard**

```
GET /telemetry
```

Shows:
- 📈 Live graphs (last 24 hours)
- 📋 Readings table (last 100)
- 🚨 Active alerts
- 💚 Plant health score (0-100)
- 🌾 Crop stage & recommendations

### **API Access**

```bash
# Get latest reading:
curl http://localhost:5000/api/telemetry

# Get readings from last hour:
curl http://localhost:5000/api/telemetry?hours=1

# Get alerts:
curl http://localhost:5000/api/telemetry/alerts
```

### **Database Access**

```bash
# View raw data:
sqlite3 telemetry.db
sqlite> SELECT * FROM readings LIMIT 5;
sqlite> SELECT * FROM alerts;
sqlite> .quit
```

---

## 🌐 **Step 6: WiFi IoT Node (ESP32)**

### **For Wireless Without USB Cable:**

```cpp
// ESP32 WiFi Version (connects via WiFi)
#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

const char* ssid = "YourWiFiName";
const char* password = "YourWiFiPassword";
const char* serverUrl = "http://192.168.1.50:5000/api/telemetry";

void send_to_server(float moisture, float temp, float humidity, float ph) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    
    String json = "{\"device_id\":\"pot-node-1\",\"moisture_pct\":" 
                + String(moisture) + ",\"air_temp_c\":" 
                + String(temp) + ",\"humidity_pct\":" 
                + String(humidity) + ",\"ph\":" 
                + String(ph) + "}";
    
    int httpCode = http.POST(json);
    http.end();
  }
}
```

---

## ⚙️ **Configuration Options**

### **Environment Variables**

```bash
# Hardware mode (serial, simulate, or off)
set KRISHISENSE_HARDWARE_MODE=serial

# Serial port (COM3, /dev/ttyUSB0, etc.)
set KRISHISENSE_SERIAL_PORT=COM3

# Baud rate (9600, 115200, etc.)
set KRISHISENSE_SERIAL_BAUD=9600

# Device ID
set KRISHISENSE_DEVICE_ID=pot-node-1

# Device token for security
set KRISHISENSE_DEVICE_TOKEN=your-secret-token

# Telemetry endpoint
set KRISHISENSE_TELEMETRY_URL=http://localhost:5000/api/telemetry

# Simulate mode (true/false)
set KRISHISENSE_SIMULATE=false
```

---

## 🧪 **Troubleshooting**

### **"No data appearing in dashboard"**

```bash
✓ Check Arduino is connected: python -c "import serial; print(serial.tools.list_ports.comports())"
✓ Verify baud rate: 9600 (or check Arduino code)
✓ Check device token: set KRISHISENSE_DEVICE_TOKEN=demo-node-token
✓ Check HARDWARE_MODE: set KRISHISENSE_HARDWARE_MODE=serial
✓ Open Arduino IDE Serial Monitor to see raw output
```

### **"Serial port not found"**

```bash
# On Windows:
set KRISHISENSE_SERIAL_PORT=COM3
python app.py

# On Linux/Mac:
set KRISHISENSE_SERIAL_PORT=/dev/ttyUSB0
python app.py

# Find your port:
python -c "import serial.tools.list_ports; [print(p) for p in serial.tools.list_ports.comports()]"
```

### **"Sensor readings are wrong"**

```
✓ Recalibrate moisture: DRY_VALUE=800, WET_VALUE=400 (adjust in code)
✓ Check pH calibration (7.0 in distilled water)
✓ Verify DHT sensor is working (test in Arduino IDE Serial Monitor)
✓ Check wiring (loose connections cause noise)
```

---

## 📱 **Mobile App Integration**

The IoT data is **automatically available on mobile**:

1. Open app: `http://192.168.1.50:5000`
2. Go to: **Telemetry** tab
3. See **live sensor data** from your field
4. Get **push notifications** for alerts
5. View **historical charts**

---

## 🚀 **Production Deployment**

### **For Farm Use (Continuous Monitoring):**

```bash
# Option 1: Raspberry Pi (always on, low power)
sudo apt-get install python3-pip
pip3 install -r requirements.txt
python3 app.py &  # Run in background

# Option 2: Docker Container
docker build -t krishisense:iot .
docker run -d --device=/dev/ttyUSB0 -p 5000:5000 krishisense:iot

# Option 3: Cloud Deployment (AWS/Google Cloud)
# Send data via 4G/WiFi to cloud server
# View dashboard from anywhere
```

---

## 📈 **Expected Performance**

| Metric | Value |
|--------|-------|
| **Data Update Interval** | 10 seconds |
| **Dashboard Refresh** | Real-time (WebSocket) |
| **Historical Data** | 30 days (SQLite) |
| **Alert Response** | < 1 second |
| **Power Consumption** | 100-500mA (Arduino) or 50-200mA (ESP32) |
| **Range** | USB: Direct / WiFi: 100m |

---

## ✨ **What You Get**

✅ **Real-Time Monitoring** — Live sensor readings  
✅ **Smart Alerts** — Notifications for dry soil, temperature extremes  
✅ **Auto-Irrigation** — Turn pump on/off based on moisture  
✅ **Historical Data** — 30 days of sensor history  
✅ **Plant Health Score** — ML-based plant wellness prediction  
✅ **Mobile Access** — View IoT data from phone anywhere  
✅ **Multi-Node Support** — Monitor multiple pots/fields  
✅ **Cloud Integration** — Connect to AWS/Google Cloud  

---

## 🎯 **Quick Start Checklist**

- [ ] Buy sensors (moisture, DHT11, pH, Arduino)
- [ ] Solder/wire connections
- [ ] Upload Arduino code
- [ ] Plug in Arduino to PC
- [ ] Run: `set KRISHISENSE_HARDWARE_MODE=serial && python app.py`
- [ ] Visit: `http://localhost:5000/telemetry`
- [ ] See live sensor data
- [ ] Configure alert thresholds
- [ ] Test on mobile phone

**That's it! Your farm IoT is ready!** 🌾📡

