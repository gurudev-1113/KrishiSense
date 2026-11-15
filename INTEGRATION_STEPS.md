# 🔗 KrishiSense IoT Integration - Step by Step

Complete guide to integrate Arduino sensors with Flask backend and mobile app.

---

## **Phase 1: Setup & Testing (30 minutes)**

### **Step 1.1: Verify Flask App is Running**

```bash
# Terminal:
cd C:\Users\GURUDEV\Desktop\KrishiSense
python app.py

# Expected output:
# ✓ Models loaded successfully
# ✓ Running on http://127.0.0.1:5000
```

✅ **Check Point:** Visit `http://localhost:5000` and see dashboard

---

### **Step 1.2: Test with Simulation Mode (No Hardware)**

```bash
# Terminal 1 (Stop previous Flask if running):
# Press Ctrl+C

# Terminal 1 (Run with simulation):
set KRISHISENSE_HARDWARE_MODE=simulate
python app.py

# Expected:
# [telemetry] Simulator running - sending demo data every 10 seconds
# [telemetry] Reading 1: moisture=45.3% temp=27.2C ...
```

✅ **Check Point:** Visit `http://localhost:5000/telemetry` and see **fake sensor data updating live**

---

### **Step 1.3: Verify Telemetry Database**

```bash
# Terminal 2 (new window):
sqlite3 telemetry.db

# Inside sqlite3:
sqlite> SELECT COUNT(*) FROM readings;
# Should show > 0 if simulator is running

sqlite> SELECT * FROM readings ORDER BY id DESC LIMIT 1;
# Should show latest reading with moisture, temp, humidity, pH

sqlite> .quit
```

✅ **Check Point:** Data being stored in SQLite

---

## **Phase 2: Hardware Setup (45 minutes)**

### **Step 2.1: Install Arduino IDE**

```
1. Download: https://www.arduino.cc/en/software
2. Install on your Windows PC
3. Launch Arduino IDE
4. Tools → Manage Libraries
5. Search "DHT11" → Install by Adafruit
```

✅ **Check Point:** Arduino IDE opens without errors

---

### **Step 2.2: Connect & Identify Arduino**

```bash
# Plug Arduino into USB port on PC

# Find COM port:
# Arduino IDE → Tools → Port
# Should see: COM3, COM4, COM5, etc.

# OR from PowerShell:
python -c "import serial.tools.list_ports; print([p.device for p in serial.tools.list_ports.comports()])"
# Output: ['COM3', 'COM4']

# Remember your COM port (e.g., COM3)
```

✅ **Check Point:** Arduino appears in port list

---

### **Step 2.3: Wire Sensors to Arduino**

```
┌────────────────────────────────────────┐
│         Arduino Uno Pins               │
│  5V   GND   D5   A0   A1   D6   ...   │
│  │     │     │    │    │    │         │
└──┼─────┼─────┼────┼────┼────┼─────────┘
   │     │     │    │    │    │
   │     │  ┌──┘    │    │    └─ Pump Relay
   │     │  │       │    └────── pH Sensor
   │     │  │       └─────────── Moisture
   │     │  └──────────────────── DHT11
   │     └───────────────────────── GND
   └──────────────────────────────── 5V
```

**Detailed Connections:**

```
DHT11 (Temperature/Humidity):
  Pin 1 (VCC)  → 5V
  Pin 2 (DATA) → Pin 5 (with 10kΩ pullup)
  Pin 3 (NC)   → Not connected
  Pin 4 (GND)  → GND

HW-080 Soil Moisture:
  VCC  → 5V
  GND  → GND
  A0   → A0 (Analog)
  D0   → Not used

pH Probe (Analog):
  VCC  → 5V
  GND  → GND
  OUT  → A1 (Analog)

Pump Relay (Optional):
  VCC  → 5V
  GND  → GND
  IN   → Pin 6 (Digital)
```

✅ **Check Point:** All sensors wired, no loose connections

---

### **Step 2.4: Upload Arduino Code**

```
1. Open Arduino IDE
2. File → New → Sketch
3. Copy code from krishisense_arduino.ino (in KrishiSense folder)
4. Paste into Arduino IDE
5. Tools → Board → Arduino Uno
6. Tools → Port → COM3 (your port)
7. Click: Sketch → Upload

Expected output:
  Compiling...
  Uploading...
  ✓ Upload complete
```

✅ **Check Point:** Code uploads without errors

---

### **Step 2.5: Test Arduino in Serial Monitor**

```
1. Arduino IDE → Tools → Serial Monitor
2. Set baud rate to 9600 (bottom right)
3. Watch output:
   ✓ Should see sensor readings every 10 seconds:
     Soil: 45.3%
     Temperature: 27.30 C
     Humidity: 61.00 %
     Soil_Temp: 27.30 C
     pH: 6.54
     Soil Raw: 742
     --------------------------------
```

✅ **Check Point:** Real sensor data appearing in serial monitor

---

## **Phase 3: Integrate Arduino with Flask (30 minutes)**

### **Step 3.1: Configure Flask for Serial Mode**

```bash
# Terminal (Stop previous Flask):
# Press Ctrl+C

# Set environment variables:
set KRISHISENSE_HARDWARE_MODE=serial
set KRISHISENSE_SERIAL_PORT=COM3
set KRISHISENSE_SERIAL_BAUD=9600
set KRISHISENSE_DEVICE_ID=pot-node-1
set KRISHISENSE_DEVICE_TOKEN=demo-node-token

# Run Flask:
python app.py

# Expected output:
# [telemetry] Hardware mode: serial
# [telemetry] Opening COM3 at 9600 baud...
# [telemetry] Connected! Reading from pot-node-1
# [telemetry] Reading 1: moisture=45.3% temp=27.2C ...
```

✅ **Check Point:** Flask connects to Arduino and shows readings

---

### **Step 3.2: Verify Data in Telemetry Dashboard**

```
Open browser:
http://localhost:5000/telemetry

You should see:
✓ Real sensor values (not simulated)
✓ Live updating charts
✓ Plant health score
✓ Active alerts
✓ Pump status
✓ Readings history
```

✅ **Check Point:** Real sensor data showing on dashboard

---

### **Step 3.3: Check Telemetry Database**

```bash
# Terminal 2:
sqlite3 telemetry.db

sqlite> SELECT * FROM readings ORDER BY ts DESC LIMIT 3;
# Shows latest 3 readings with real values

sqlite> SELECT COUNT(*) FROM alerts;
# Shows any triggered alerts

sqlite> .quit
```

✅ **Check Point:** Real data stored in database

---

### **Step 3.4: Test Alert System**

```
Let soil moisture drop below 20% (or trigger manually):

Expected:
✓ Alert appears on dashboard
✓ Alert stored in alerts table
✓ Pump turns on (if relay connected)
✓ Notification/log entry created

Check alerts:
sqlite3 telemetry.db
sqlite> SELECT * FROM alerts ORDER BY ts_raised DESC LIMIT 3;
```

✅ **Check Point:** Alerts trigger correctly

---

## **Phase 4: Mobile App Integration (15 minutes)**

### **Step 4.1: Access from Mobile on Same WiFi**

```bash
# Find server IP:
PowerShell:
  ipconfig
  Look for: IPv4 Address (e.g., 192.168.1.50)

# On your mobile phone (same WiFi):
  http://192.168.1.50:5000/telemetry

Expected:
✓ Mobile dashboard loads
✓ Real sensor data visible
✓ Charts responsive to touch
✓ Alerts show as notifications
```

✅ **Check Point:** Mobile can see telemetry dashboard

---

### **Step 4.2: Install as PWA App**

```
On mobile phone:

1. Visit: http://192.168.1.50:5000
2. Wait 2 seconds for install banner
3. Tap "Install App" or:
   - Tap 3-dot menu (⋮)
   - Select "Add to Home Screen"
4. Tap "Add"

Result:
✓ KrishiSense icon appears on home screen
✓ Tap it to open in full-screen mode
✓ Works like native app!
✓ Still receives updates from server
```

✅ **Check Point:** App installed and working on phone

---

### **Step 4.3: Test Offline Mode**

```
On mobile:

1. Disconnect WiFi (airplane mode)
2. Tap KrishiSense app
3. Expected:
   ✓ Last cached dashboard visible
   ✓ "Offline" message may appear
   ✓ Can still view previous data
4. Reconnect WiFi
5. Data syncs automatically
```

✅ **Check Point:** Offline mode working

---

## **Phase 5: Advanced Configuration (Optional)**

### **Step 5.1: Configure Alert Thresholds**

Edit `blueprints/telemetry_module.py`:

```python
# Find THRESHOLDS section around line 50:
THRESHOLDS = {
    'moisture_min': 20,      # Alert if < 20%
    'moisture_max': 80,      # Alert if > 80%
    'temp_min': 10,          # Alert if < 10°C
    'temp_max': 35,          # Alert if > 35°C
    'humidity_min': 30,      # Alert if < 30%
    'humidity_max': 85,      # Alert if > 85%
    'ph_min': 6.0,
    'ph_max': 8.0,
}
```

Then restart Flask:
```bash
set KRISHISENSE_HARDWARE_MODE=serial
python app.py
```

✅ **Check Point:** Alerts trigger at custom thresholds

---

### **Step 5.2: Calibrate Sensors**

**Soil Moisture Calibration:**

```python
# In krishisense_arduino.ino, find:
#define DRY_VALUE 800      // Adjust these
#define WET_VALUE 400

# Steps:
1. Leave sensor in air (dry)
2. Check Serial Monitor for "Soil Raw" value
3. Update DRY_VALUE with that number

4. Put sensor in water (wet)
5. Check Serial Monitor for "Soil Raw" value
6. Update WET_VALUE with that number

7. Re-upload code
8. Check that moisture % goes 0-100 correctly
```

**pH Calibration:**

```python
# Simple 2-point calibration:
1. Put pH probe in pH 7.0 solution (distilled water)
2. Adjust pH_PIN reading to output 7.0
3. Put probe in pH 4.0 solution
4. Verify it shows ~4.0

# Edit in krishisense_arduino.ino:
float pH = (voltage / 5.0) * 14.0;  // Adjust this formula
```

✅ **Check Point:** Sensor values accurate

---

### **Step 5.3: Enable Auto-Irrigation**

The Arduino code already has pump control:

```cpp
// In krishisense_arduino.ino:
#define PUMP_THRESHOLD_LOW 20   // Turn ON at 20%
#define PUMP_THRESHOLD_HIGH 60  // Turn OFF at 60%

// To enable:
1. Connect water pump to relay on Pin 6
2. Adjust thresholds to your needs
3. Re-upload code
4. Pump will now auto-irrigate!
```

To **disable** auto-irrigation temporarily:

```cpp
// Comment out pump control in loop():
// control_pump(moisture_pct);
```

✅ **Check Point:** Pump turns on/off based on moisture

---

## **Phase 6: Multi-Device & Cloud (Advanced)**

### **Step 6.1: Add Second Arduino/ESP32**

```
If you want to monitor multiple fields/pots:

1. Get second Arduino
2. Upload code with different DEVICE_ID:
   const char* DEVICE_ID = "pot-node-2";
3. Connect to different COM port
4. Add to Flask:
   set KRISHISENSE_SERIAL_PORT=COM3  (Arduino 1)
   set KRISHISENSE_SERIAL_PORT=COM4  (Arduino 2)
```

**Better: Use ESP32 WiFi**

```
ESP32 connects via WiFi (no USB cable):
1. Add WiFi code (see IOT_SETUP_GUIDE.md)
2. Configure WiFi SSID + password
3. All data POSTs to same /api/telemetry
4. Multiple nodes show separately on dashboard
```

---

### **Step 6.2: Deploy to Cloud (Optional)**

```bash
# Make app accessible from anywhere:

Option 1: Cloudflare Tunnel (Easiest)
  pip install cloudflare
  cloudflare tunnel --url http://localhost:5000
  # Get public URL instantly!

Option 2: Railway.app (Free tier)
  1. Connect GitHub repo
  2. Deploy automatically
  3. Get https://krishisense-yourname.railway.app

Option 3: AWS/Google Cloud
  1. Container Docker image
  2. Deploy to cloud
  3. Get public URL
```

---

## **Phase 7: Testing Checklist**

### **✅ Complete Integration Checklist**

- [ ] Flask app runs without errors
- [ ] Simulation mode works (fake data visible)
- [ ] Arduino code uploads successfully
- [ ] Arduino Serial Monitor shows sensor data
- [ ] Flask connects to Arduino (HARDWARE_MODE=serial)
- [ ] Telemetry dashboard shows real sensor data
- [ ] Data stored in SQLite database
- [ ] Mobile phone can access dashboard
- [ ] PWA app installs on phone
- [ ] Offline mode works on phone
- [ ] Alerts trigger when thresholds exceeded
- [ ] Pump relay turns on/off (if connected)
- [ ] Sensor values are calibrated correctly
- [ ] Plant health score calculates
- [ ] Historical data shows in charts

---

## **Troubleshooting Integration**

| Issue | Check | Solution |
|-------|-------|----------|
| **Flask can't find COM port** | `python -c "import serial.tools.list_ports; print([p.device for p in serial.tools.list_ports.comports()])"` | Update COM port number |
| **No data on dashboard** | Arduino IDE Serial Monitor | Verify sensor values are real |
| **Wrong sensor readings** | Calibration values | Adjust DRY_VALUE, WET_VALUE, pH formula |
| **Alerts not triggering** | Check thresholds | Update THRESHOLDS in telemetry_module.py |
| **Mobile can't access** | Ping server IP | Check WiFi, firewall, IP address |
| **Offline mode empty** | Clear cache, reconnect WiFi | Service Worker caches on first visit |

---

## **Summary: Full Integration (2 Hours Total)**

```
Time Breakdown:
├─ Phase 1: Setup & Test (30 min)     ← Simulation mode
├─ Phase 2: Hardware (45 min)         ← Arduino wiring & upload
├─ Phase 3: Arduino ↔ Flask (30 min)  ← Real data integration
├─ Phase 4: Mobile (15 min)           ← Phone access
└─ Phase 5+: Advanced (Optional)      ← Alerts, calibration, cloud

Total: ~2 hours for full working system
```

---

## **Next Steps**

1. **Start with Phase 1** → Test simulation
2. **Move to Phase 2** → Wire your Arduino
3. **Do Phase 3** → Integrate with Flask
4. **Test Phase 4** → Access from mobile
5. **Optional Phase 5+** → Advanced features

**You now have a production-ready IoT system!** 🌾📡✨

