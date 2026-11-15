#include <string.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>

// =====================================================
// SMART PLANT MONITORING SYSTEM
// Arduino UNO + pH + DHT11 + HW-080 + LCD
// =====================================================

// LCD (Default I2C address 0x27, change to 0x3F if your module uses that)
LiquidCrystal_I2C lcd(0x27, 16, 2);

// pH Sensor
#define PH_PIN A0
const float PH7_VOLTAGE = 3.873;
const float VOLTAGE_PER_PH = 0.18;

// DHT Sensor (Change DHT11 to DHT22 if using a white sensor)
#define DHT_PIN 2
#define DHT_TYPE DHT11
DHT dht(DHT_PIN, DHT_TYPE);

// Soil Moisture Sensor
#define SOIL_PIN A1
#define SOIL_THRESHOLD 600

// =====================================================

void printLCDLine(byte row, const char *text) {
  lcd.setCursor(0, row);
  lcd.print(text);
  int len = strlen(text);

  while (len < 16) {
    lcd.print(" ");
    len++;
  }
}

// =====================================================

void setup() {
  Serial.begin(9600);

  lcd.init();
  lcd.backlight();

  dht.begin();

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Smart Plant");
  lcd.setCursor(0, 1);
  lcd.print("Initializing...");
  delay(2000);

  lcd.clear();
}

// =====================================================

void loop() {

  // ---------------- READ pH ----------------

  long totalPH = 0;

  for (int i = 0; i < 20; i++) {
    totalPH += analogRead(PH_PIN);
    delay(10);
  }

  float rawPH = totalPH / 20.0;
  float voltage = rawPH * 5.0 / 1023.0;

  float pH = 7.00 +
            ((PH7_VOLTAGE - voltage) / VOLTAGE_PER_PH);

  pH = constrain(pH, 0.0, 14.0);

  // ---------------- READ DHT ----------------

  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  // ---------------- READ SOIL ----------------

  int soilValue = analogRead(SOIL_PIN);

  bool soilDry = soilValue > SOIL_THRESHOLD;

  // ---------------- SERIAL MONITOR ----------------

  Serial.println("\n-----------------------------");

  Serial.print("pH: ");
  Serial.println(pH, 2);

  Serial.print("Raw pH: ");
  Serial.println(rawPH, 1);

  Serial.print("Voltage: ");
  Serial.println(voltage, 3);

  Serial.print("Temperature: ");

  if (isnan(temperature)) {
    Serial.println("DHT Error");
  } else {
    Serial.print(temperature, 1);
    Serial.println(" C");
  }

  Serial.print("Humidity: ");

  if (isnan(humidity)) {
    Serial.println("DHT Error");
  } else {
    Serial.print(humidity, 1);
    Serial.println(" %");
  }

  Serial.print("Soil Raw: ");
  Serial.println(soilValue);

  Serial.print("Soil Status: ");
  Serial.println(soilDry ? "WATER NEEDED" : "WET");

  // ---------------- LCD PAGE 1 ----------------

  lcd.clear();

  char line1[17];
  char line2[17];

  snprintf(line1, sizeof(line1), "pH: %.2f", pH);

  if (soilDry) {
    snprintf(line2, sizeof(line2), "Soil: DRY");
  } else {
    snprintf(line2, sizeof(line2), "Soil: WET");
  }

  printLCDLine(0, line1);
  printLCDLine(1, line2);

  delay(3000);

  // ---------------- LCD PAGE 2 ----------------

  lcd.clear();

  if (isnan(temperature)) {
    snprintf(line1, sizeof(line1), "Temp: Error");
  } else {
    snprintf(line1, sizeof(line1), "Temp: %.1f%cC",
            temperature, (char)223);
  }

  if (isnan(humidity)) {
    snprintf(line2, sizeof(line2), "Hum: Error");
  } else {
    snprintf(line2, sizeof(line2), "Hum: %.1f%%",
            humidity);
  }

  printLCDLine(0, line1);
  printLCDLine(1, line2);

  delay(3000);
}
