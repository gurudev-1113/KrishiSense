/*
  KrishiSense -- ESP32 field node firmware (Module M1)
  ------------------------------------------------------
  Samples soil moisture, air temp/humidity, soil temperature and soil pH
  every 10 seconds and POSTs a JSON reading to the Flask server's
  /api/telemetry endpoint. Matches the pin map and process flow in the
  project synopsis (Lane A).

  Board: ESP32 DevKit V1 (30-pin)

  Pin map:
    GPIO34 (ADC1_CH6) - Capacitive soil moisture sensor v2.0 (AOUT)
    GPIO35 (ADC1_CH7) - pH probe / PH4502C board (Po), via 10k/10k divider
    GPIO4             - DHT22 DATA (air temp + humidity), 10k pull-up
    GPIO5              - DS18B20 DATA (soil temperature, OneWire), 4.7k pull-up
    GPIO21 / GPIO22    - I2C SDA/SCL, shared by SSD1306 OLED
    GPIO27             - Relay IN (optional pump/irrigation add-on)

  Libraries required (Arduino IDE > Library Manager):
    WiFi (bundled with ESP32 core), HTTPClient (bundled),
    DHT sensor library (Adafruit), OneWire, DallasTemperature,
    Adafruit_SSD1306 + Adafruit_GFX, ArduinoJson

  Fill in WIFI_SSID / WIFI_PASSWORD / SERVER_HOST / DEVICE_TOKEN below
  before flashing. DEVICE_TOKEN must match KRISHISENSE_DEVICE_TOKEN in
  the Flask app's environment (defaults to "demo-node-token").
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ---------------- Configuration ----------------
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_HOST   = "http://192.168.1.100:5000";  // IP of the machine running app.py
const char* DEVICE_TOKEN  = "demo-node-token";             // must match KRISHISENSE_DEVICE_TOKEN
const char* DEVICE_ID     = "pot-node-1";
const unsigned long SAMPLE_INTERVAL_MS = 10000;             // 10 s duty cycle

// ---------------- Pins ----------------
#define PIN_MOISTURE   34
#define PIN_PH         35
#define PIN_DHT        4
#define PIN_DS18B20    5
#define OLED_SDA       21
#define OLED_SCL       22

// ---------------- Calibration (fill in after the two-point calibration in §6) ----------------
// Moisture: raw ADC in dry air, raw ADC fully submerged in water
int MOISTURE_RAW_DRY = 3000;
int MOISTURE_RAW_WET = 1200;

// pH: raw ADC at pH 4.0 buffer, raw ADC at pH 6.86 buffer
int PH_RAW_AT_4  = 2032;
int PH_RAW_AT_6_86 = 1500;

// ---------------- Objects ----------------
DHT dht(PIN_DHT, DHT22);
OneWire oneWire(PIN_DS18B20);
DallasTemperature ds18b20(&oneWire);
Adafruit_SSD1306 display(128, 64, &Wire, -1);

unsigned long lastSample = 0;

// Ring buffer for offline retry (holds up to 60 readings)
#define BUFFER_SIZE 60
StaticJsonDocument<256> buffer[BUFFER_SIZE];
bool bufferSlotUsed[BUFFER_SIZE] = {false};
int bufferHead = 0;

float medianOf5(float (*sampleFn)()) {
  float samples[5];
  for (int i = 0; i < 5; i++) {
    samples[i] = sampleFn();
    delay(10);
  }
  // simple insertion sort
  for (int i = 1; i < 5; i++) {
    float key = samples[i];
    int j = i - 1;
    while (j >= 0 && samples[j] > key) {
      samples[j + 1] = samples[j];
      j--;
    }
    samples[j + 1] = key;
  }
  return samples[2];
}

float readMoistureRaw() { return analogRead(PIN_MOISTURE); }
float readPhRaw() { return analogRead(PIN_PH); }

float readMoisturePercent() {
  float raw = medianOf5(readMoistureRaw);
  float pct = (MOISTURE_RAW_DRY - raw) * 100.0 / (MOISTURE_RAW_DRY - MOISTURE_RAW_WET);
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  return pct;
}

float readPh() {
  float raw = medianOf5(readPhRaw);
  // two-point linear map between the 4.0 and 6.86 calibration buffers
  float slope = (6.86 - 4.0) / (float)(PH_RAW_AT_6_86 - PH_RAW_AT_4);
  float ph = 4.0 + slope * (raw - PH_RAW_AT_4);
  return ph;
}

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(400);
    Serial.print(".");
  }
  Serial.println(WiFi.status() == WL_CONNECTED ? " connected" : " FAILED (will retry)");
}

void updateDisplay(float moisture, float airTemp, float humidity, float soilTemp, float ph, bool linkOk) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("KrishiSense Node");
  display.print("Moist: "); display.print(moisture, 1); display.println(" %");
  display.print("Air:   "); display.print(airTemp, 1); display.print("C  "); display.print(humidity, 0); display.println("%RH");
  display.print("Soil T:"); display.print(soilTemp, 1); display.println(" C");
  display.print("pH:    "); display.println(ph, 2);
  display.print("Link:  "); display.println(linkOk ? "OK" : "OFFLINE");
  display.display();
}

bool postReading(JsonDocument &doc) {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  http.begin(String(SERVER_HOST) + "/api/telemetry");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", DEVICE_TOKEN);

  String body;
  serializeJson(doc, body);
  int code = http.POST(body);
  http.end();

  return code == 200;
}

void flushBuffer() {
  for (int i = 0; i < BUFFER_SIZE; i++) {
    if (bufferSlotUsed[i]) {
      if (postReading(buffer[i])) {
        bufferSlotUsed[i] = false;
      } else {
        break;  // still offline, stop trying the rest
      }
    }
  }
}

void bufferReading(JsonDocument &doc) {
  buffer[bufferHead] = doc;
  bufferSlotUsed[bufferHead] = true;
  bufferHead = (bufferHead + 1) % BUFFER_SIZE;
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  ds18b20.begin();
  Wire.begin(OLED_SDA, OLED_SCL);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("SSD1306 not found");
  }
  display.clearDisplay();
  display.display();

  analogReadResolution(12);  // ESP32 12-bit ADC, ADC1 only (Wi-Fi disables ADC2)

  connectWiFi();
}

void loop() {
  if (millis() - lastSample < SAMPLE_INTERVAL_MS) return;
  lastSample = millis();

  if (WiFi.status() != WL_CONNECTED) connectWiFi();

  float moisture = readMoisturePercent();
  float airTemp = dht.readTemperature();
  float humidity = dht.readHumidity();
  ds18b20.requestTemperatures();
  float soilTemp = ds18b20.getTempCByIndex(0);
  float ph = readPh();

  StaticJsonDocument<256> doc;
  doc["device_id"] = DEVICE_ID;
  doc["moisture_pct"] = moisture;
  doc["air_temp_c"] = isnan(airTemp) ? nullptr : airTemp;
  doc["humidity_pct"] = isnan(humidity) ? nullptr : humidity;
  doc["soil_temp_c"] = soilTemp;
  doc["ph"] = ph;

  bool ok = postReading(doc);
  if (!ok) {
    bufferReading(doc);
    Serial.println("POST failed, buffered reading");
  } else {
    flushBuffer();  // opportunistically drain anything queued from an earlier outage
  }

  updateDisplay(moisture, airTemp, humidity, soilTemp, ph, ok);

  Serial.printf("moisture=%.1f%% air=%.1fC rh=%.0f%% soil=%.1fC pH=%.2f link=%s\n",
                moisture, airTemp, humidity, soilTemp, ph, ok ? "OK" : "BUFFERED");
}
