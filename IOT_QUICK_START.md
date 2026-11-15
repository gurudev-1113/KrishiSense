# 🌱 KrishiSense IoT - Quick Start (15 Minutes)

## ✅ **Checklist: What You Need**

### **Hardware (Budget: $30-50)**
- [ ] Arduino Uno ($8) — microcontroller.cc or Amazon
- [ ] HW-080 Soil Moisture Sensor ($5) — aliexpress.com
- [ ] DHT11 Temperature/Humidity ($3) — amazon.in
- [ ] Analog pH Probe ($15) — amazon.in
- [ ] USB Cable ($2) — arduino-compatible
- [ ] Breadboard + Jumper Wires ($5) — electronics kit

### **Software (All Free)**
- [ ] Arduino IDE (download from arduino.cc)
- [ ] Python 3.14+ (already installed)
- [ ] KrishiSense (already have it!)

---

## 🚀 **5-Minute Setup**

### **1. Test Without Hardware First** ⚡
```bash
# Terminal/PowerShell:
cd C:\Users\GURUDEV\Desktop\KrishiSense
set KRISHISENSE_HARDWARE_MODE=simulate
python app.py
```

Visit: `http://localhost:5000/telemetry`
✓ You'll see **fake sensor data** updating in real-time

---

### **2. Wire Your Sensors** 🔌

```
Arduino Pin 5  ← DHT11 Data
Arduino A0     ← Soil Moisture Signal
Arduino A1     ← pH Sensor Signal
Arduino Pin 6  ← Pump Relay (optional)

All sensors also need:
- 5V power line
- GND ground line
```

**Easy Diagram:**
```
┌──────────────────────────────┐
│      Arduino Uno             │
│  5V  GND  Pin5  A0  A1  Pin6 │
│  │    │    │     │   │   │   │
│  └────┼────┼─────┼───┼───┘   │
│       │    │     │   │       │
│    ┌──┴┬───┴──┬──┴───┴──┐    │
│    │   │     │         │    │
│ [DHT][Moisture]     [pH]  [Pump]
└──────────────────────────────┘
```

---

### **3. Upload Arduino Code** 📝

```
1. Download: krishisense_arduino.ino (in KrishiSense folder)
2. Open Arduino IDE
3. File → Open → select krishisense_arduino.ino
4. Tools → Board → Arduino Uno
5. Tools → Port → COM3 (or your port)
6. Sketch → Upload
   → Wait for "Upload complete"
```

---

### **4. Connect & Run** ⚙️

```bash
# Plug Arduino into computer via USB

# Terminal:
set KRISHISENSE_HARDWARE_MODE=serial
set KRISHISENSE_SERIAL_PORT=COM3
set KRISHISENSE_SERIAL_BAUD=9600

python app.py

# Watch for:
# [telemetry] Opening COM3 at 9600 baud...
# [telemetry] Connected! Reading from pot-node-1
# [telemetry] Reading 1: moisture=45.3% temp=27.2C ...
```

---

### **5. View Dashboard** 📊

```
http://localhost:5000/telemetry

You'll see:
✓ Real-time sensor values
✓ Live charts
✓ Plant health score
✓ Alerts
✓ Irrigation recommendations
```

---

## 🎯 **What Happens Automatically**

| Feature | Details |
|---------|---------|
| **Data Collection** | Every 10 seconds from sensors |
| **Smart Alerts** | Dry soil? Too hot? pH wrong? → Alert |
| **Auto-Irrigation** | Pump on/off based on soil moisture |
| **Historical Data** | 30 days stored in SQLite |
| **Mobile Dashboard** | View on phone at `http://192.168.1.50:5000` |
| **Plant Health Score** | ML prediction (0-100%) |
| **Recommendations** | AI-powered crop advice |

---

## 📱 **Access from Mobile Phone**

```
Same WiFi network:
http://192.168.1.50:5000/telemetry

Install as app:
1. Tap 3 dots → "Add to Home Screen"
2. Now have native app on home screen!
```

---

## 🔧 **Troubleshooting**

| Problem | Solution |
|---------|----------|
| **No data in dashboard** | 1. Check Arduino connected via USB<br>2. Verify HARDWARE_MODE=serial<br>3. Check COM port is correct |
| **Serial port not found** | Run: `python -c "import serial.tools.list_ports; print([p.device for p in serial.tools.list_ports.comports()])"` |
| **DHT11 not reading** | Add 10kΩ resistor between DATA and 5V |
| **Moisture always 0 or 100** | Calibrate DRY_VALUE=800, WET_VALUE=400 in code |
| **pH readings wrong** | Calibrate in pH 7.0 solution |

---

## 💰 **Cost Breakdown**

| Item | Cost | Where to Buy |
|------|------|-------------|
| Arduino Uno | $8-15 | amazon.in, aliexpress |
| Soil Moisture Sensor | $3-8 | aliexpress, amazon.in |
| DHT11 | $2-5 | amazon.in |
| pH Probe | $10-30 | amazon.in |
| USB Cable | $2 | any electronics shop |
| Breadboard + Wires | $3-5 | electronics kit |
| **TOTAL** | **$28-63** | |

**Optional Upgrades:**
- ESP32 (WiFi) — $10-15 (wireless, no USB cable)
- Rain Sensor — $2-5
- Light Sensor — $2-5
- Solar Panel — $20-50 (24/7 operation)

---

## 🌐 **Next Steps**

### **Immediate (Done in 15 min):**
1. ✅ Test with simulate mode
2. ✅ Wire sensors to Arduino
3. ✅ Upload code
4. ✅ See live data on dashboard

### **Next (Optional):**
- [ ] Auto-configure irrigation pump
- [ ] Set alert thresholds
- [ ] Deploy to cloud (Railway, Heroku)
- [ ] Connect multiple sensor nodes
- [ ] View from mobile anywhere

### **Advanced (Future):**
- [ ] WiFi ESP32 (no USB cable needed)
- [ ] Solar power for 24/7 operation
- [ ] Weather API integration
- [ ] Predictive ML (crop yield, disease risk)

---

## 📚 **Full Documentation**

Read **IOT_SETUP_GUIDE.md** for:
- Detailed wiring diagrams
- pH calibration procedure
- WiFi ESP32 setup
- Cloud deployment
- Multiple nodes
- Mobile app integration

---

## ✨ **What You Get**

```
Real-Time Monitoring
├─ Soil Moisture (%)
├─ Temperature (°C)
├─ Humidity (%)
├─ pH Level
└─ Soil Temperature

Smart Alerts
├─ Low moisture → Water now
├─ High temp → Provide shade
├─ Low pH → Add lime
└─ High humidity → Improve ventilation

Auto-Irrigation
├─ Turn pump on at 20% moisture
├─ Turn pump off at 60% moisture
└─ Prevents over/under watering

Plant Health
├─ 0-100 health score
├─ Crop recommendations
├─ Disease risk assessment
└─ Harvest timing

Mobile Access
├─ View from phone anywhere
├─ Install as PWA app
├─ Works offline
└─ Push notifications
```

---

## 🎓 **Learn More**

- Arduino basics: https://www.arduino.cc/en/Guide
- Sensor calibration: Watch YouTube tutorials
- Python integration: Read blueprints/telemetry_module.py
- Flask API: Read app.py /api/telemetry endpoint

---

## 🆘 **Still Need Help?**

1. **Check logs**: Run with `python app.py` and read errors
2. **Arduino monitor**: Arduino IDE → Tools → Serial Monitor (9600 baud)
3. **Read IOT_SETUP_GUIDE.md**: Full troubleshooting section
4. **Test hardware first**: Use Arduino IDE Serial Monitor to verify sensors
5. **Python test**: `python -c "import serial; print(serial.__version__)"`

---

## 🎉 **Congratulations!**

Your KrishiSense is now:
- ✅ Running with real sensor data
- ✅ Collecting historical trends
- ✅ Alerting when plants need help
- ✅ Auto-irrigating based on soil moisture
- ✅ Accessible from mobile anywhere

**Estimated time to full setup: 15-30 minutes**

**Happy Farming! 🌾📡**

