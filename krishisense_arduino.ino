/*
 * KrishiSense IoT Node Firmware
 * ==============================
 *
 * Reads sensors and sends data to Flask backend
 * Sensors: DHT11 (temp/humidity), Soil Moisture (HW-080), pH Probe
 *
 * Upload Instructions:
 * 1. Open Arduino IDE
 * 2. Tools > Manage Libraries > Install DHT11 by Adafruit
 * 3. Connect Arduino via USB
 * 4. Select Board: Arduino Uno
 * 5. Select Port: COM3 (or your port)
 * 6. Click Upload
 */

#include <DHT.h>

// ====== PIN CONFIGURATION ======
#define DHT_PIN 5          // DHT11 data pin
#define DHT_TYPE DHT11     // DHT type
#define MOISTURE_PIN A0    // Soil moisture analog pin
#define pH_PIN A1          // pH sensor analog pin
#define PUMP_PIN 6         // Pump control pin (relay)

// ====== SENSOR CALIBRATION ======
#define DRY_VALUE 800      // Moisture ADC reading when completely dry
#define WET_VALUE 400      // Moisture ADC reading when completely wet
#define pH_CALIB_7 512     // ADC value at pH 7.0 (calibrate with pH 7 solution)

// ====== CONSTANTS ======
#define SENSOR_READ_INTERVAL 10000  // Read sensors every 10 seconds
#define PUMP_THRESHOLD_LOW 20       // Turn on pump when moisture < 20%
#define PUMP_THRESHOLD_HIGH 60      // Turn off pump when moisture > 60%

// ====== GLOBAL VARIABLES ======
DHT dht(DHT_PIN, DHT_TYPE);
unsigned long lastReadTime = 0;
int pump_state = 0;  // 0 = off, 1 = on

// ====== SETUP ======
void setup() {
  Serial.begin(9600);
  dht.begin();
  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, LOW);

  delay(2000);  // Wait for serial to initialize
  Serial.println("KrishiSense IoT Node Starting...");
  Serial.println("Sensors: DHT11, HW-080 Moisture, pH Probe");
  Serial.println("--------------------------------");
}

// ====== MAIN LOOP ======
void loop() {
  unsigned long currentTime = millis();

  // Read sensors every SENSOR_READ_INTERVAL milliseconds
  if (currentTime - lastReadTime >= SENSOR_READ_INTERVAL) {
    lastReadTime = currentTime;

    // Read all sensors
    float humidity = dht.readHumidity();
    float air_temp = dht.readTemperature();
    int moisture_raw = analogRead(MOISTURE_PIN);
    float pH = read_ph_sensor();

    // Skip if DHT read failed
    if (isnan(humidity) || isnan(air_temp)) {
      Serial.println("ERROR: DHT11 read failed!");
      return;
    }

    // Convert moisture to percentage (0-100%)
    float moisture_pct = map_moisture(moisture_raw);

    // Control pump based on moisture level (simple hysteresis)
    control_pump(moisture_pct);

    // Send data in block format (compatible with Python parser)
    send_block_format(moisture_pct, air_temp, humidity, moisture_raw, pH);
  }
}

// ====== FUNCTIONS ======

// Map moisture raw ADC value to percentage
float map_moisture(int raw_value) {
  // Constrain between dry and wet values
  int constrained = constrain(raw_value, WET_VALUE, DRY_VALUE);

  // Map to 0-100%
  float percentage = map(constrained, DRY_VALUE, WET_VALUE, 0, 100);

  return percentage;
}

// Read pH sensor and return pH value
// Simple linear mapping: 0V = pH0, 5V = pH14
float read_ph_sensor() {
  int ph_raw = analogRead(pH_PIN);

  // Convert ADC (0-1023) to voltage (0-5V)
  float voltage = ph_raw * (5.0 / 1023.0);

  // Linear mapping: 0V = pH 0, 5V = pH 14
  // pH = (voltage / 5.0) * 14.0
  float pH = (voltage / 5.0) * 14.0;

  // Better: use calibration point at pH 7.0
  // pH_7V = voltage at pH 7 (typically ~2.5V or 512 ADC)
  // slope = 59.16 mV per pH (Nernst equation)
  // This is simplified - for production, use proper pH meter calibration

  return constrain(pH, 0.0, 14.0);
}

// Auto irrigation pump control
// Hysteresis: turn on at LOW, turn off at HIGH to prevent oscillation
void control_pump(float moisture) {
  if (moisture < PUMP_THRESHOLD_LOW && pump_state == 0) {
    digitalWrite(PUMP_PIN, HIGH);
    pump_state = 1;
    Serial.println("[PUMP] ON - Moisture too low");
  }
  else if (moisture > PUMP_THRESHOLD_HIGH && pump_state == 1) {
    digitalWrite(PUMP_PIN, LOW);
    pump_state = 0;
    Serial.println("[PUMP] OFF - Moisture sufficient");
  }
}

// Send data in block format (compatible with hardware_serial.py parser)
void send_block_format(float moisture, float air_temp, float humidity, int raw, float pH) {
  Serial.print("Soil: ");
  Serial.print(moisture, 1);
  Serial.println("%");

  Serial.print("Temperature: ");
  Serial.print(air_temp, 2);
  Serial.println(" C");

  Serial.print("Humidity: ");
  Serial.print(humidity, 2);
  Serial.println(" %");

  Serial.print("Soil_Temp: ");
  Serial.print(air_temp, 2);  // Use air temp as approximation
  Serial.println(" C");

  Serial.print("pH: ");
  Serial.println(pH, 2);

  Serial.print("Soil Raw: ");
  Serial.println(raw);

  Serial.println("--------------------------------");
}

// ====== ALTERNATIVE: SINGLE-LINE FORMAT ======
// Uncomment send_single_line() below if you prefer single-line format
// Then replace send_block_format() call with send_single_line()

void send_single_line(float moisture, float air_temp, float humidity, int raw, float pH) {
  Serial.print("moisture=");
  Serial.print(moisture, 1);
  Serial.print("% air=");
  Serial.print(air_temp, 1);
  Serial.print("C rh=");
  Serial.print(humidity, 1);
  Serial.print("% soil=");
  Serial.print(air_temp, 1);  // Use air temp
  Serial.print("C pH=");
  Serial.print(pH, 2);
  Serial.println(" link=ok");
}

/*
 * ====== SENSOR WIRING ======
 *
 * DHT11 (Temperature/Humidity):
 *   GND  -> Arduino GND
 *   VCC  -> Arduino 5V
 *   DATA -> Arduino Pin 5
 *   (Optional: 10kΩ pullup between DATA and VCC)
 *
 * HW-080 Soil Moisture:
 *   GND  -> Arduino GND
 *   VCC  -> Arduino 5V
 *   A0   -> Arduino A0
 *   D0   -> (Not used - digital threshold)
 *
 * pH Probe (Analog):
 *   GND  -> Arduino GND
 *   VCC  -> Arduino 5V
 *   OUT  -> Arduino A1
 *
 * Water Pump Relay (Optional):
 *   GND  -> Arduino GND
 *   VCC  -> Arduino 5V
 *   IN   -> Arduino Pin 6
 *   Connect pump to relay's normally-open contacts
 *
 * USB Cable:
 *   Arduino USB -> Computer USB
 *
 * ====== TROUBLESHOOTING ======
 *
 * If DHT not working:
 *   - Check wiring (GND, VCC, DATA pin)
 *   - Try 10kΩ pullup resistor between DATA and VCC
 *   - Check DHT11 is not DHT22 (or update DHT_TYPE)
 *
 * If moisture readings are wrong:
 *   - Calibrate DRY_VALUE and WET_VALUE
 *   - Sensor should read ~800 in air, ~400 in water
 *
 * If pH readings are wrong:
 *   - Calibrate with known pH solutions (4.0, 7.0, 10.0)
 *   - Adjust pH linear mapping
 *
 * If pump not working:
 *   - Check relay wiring
 *   - Test relay with standalone 5V
 *   - Verify pump power source is external (not Arduino)
 */

