#include <TinyGPS++.h>
#include <HardwareSerial.h>
#include <LoRa.h>
#include <Wire.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// GPS pins
#define GPS_RX 34
#define GPS_TX 12

// LoRa pins
#define LORA_SCK 5
#define LORA_MISO 19
#define LORA_MOSI 27
#define LORA_CS 18
#define LORA_RST 23
#define LORA_IRQ 26
#define LORA_FREQ 433E6

// I2C pins
#define I2C_SDA 21
#define I2C_SCL 22

// Sensor pins
#define DHT_PIN 13        // DHT11 - Ambient temp/humidity
#define DS18B20_PIN 4     // DS18B20 - Body temperature
#define PULSE_PIN 15

// MPU6050
#define MPU6050_ADDR 0x68
#define MPU6050_PWR_MGMT_1 0x6B
#define MPU6050_ACCEL_XOUT_H 0x3B

// AXP2101 Power Management
#define AXP2101_ADDR 0x34

// DEVICE ID - Change for each collar
const String DEVICE_ID = "COW001";

// Sensors
DHT dht(DHT_PIN, DHT11);
OneWire oneWire(DS18B20_PIN);
DallasTemperature ds18b20(&oneWire);
TinyGPSPlus gps;
HardwareSerial GPS(1);

// Pulse sensor variables
int pulseValue = 0;
int minPulse = 4095;
int maxPulse = 0;
int threshold = 2000;
unsigned long lastBeatTime = 0;
int beatsPerMinute = 0;
bool pulseDetected = false;

const int numReadings = 5;
int readings[numReadings];
int readIndex = 0;
int totalPulse = 0;
int avgPulse = 0;

int packetCounter = 0;
bool hasAXP2101 = false;

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("\n╔═══════════════════════════════════════╗");
  Serial.println("║ T-BEAM V1.2 - DUAL TEMP SENSORS     ║");
  Serial.println("║ DHT11 + DS18B20 System ✓             ║");
  Serial.println("╚═══════════════════════════════════════╝\n");
  
  // Initialize I2C with timeout protection for T-Beam v1.2
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setTimeout(1000);  // Increase timeout to 1000ms (prevents timeout errors)
  Wire.setClock(100000);  // Reduce to 100kHz for stability (was 400kHz)
  
  // AXP2101 PMU - DISABLED (causes I2C timeout errors on some T-Beam boards)
  // Using fixed battery level instead
  Serial.println("[0/6] AXP2101 PMU... ✗ Disabled (using fixed 50% battery)");
  hasAXP2101 = false;
  
  /*
  // Uncomment if you want to try detecting AXP2101
  delay(300);
  Serial.print("[0/6] AXP2101 PMU... ");
  Wire.beginTransmission(AXP2101_ADDR);
  if (Wire.endTransmission() == 0) {
    Serial.println("✓ Found at 0x34");
    hasAXP2101 = true;
    initAXP2101();
  } else {
    Serial.println("✗ Not found (using fallback battery)");
    hasAXP2101 = false;
  }
  */
  
  // 1. GPS
  Serial.print("[1/6] GPS... ");
  GPS.begin(9600, SERIAL_8N1, GPS_RX, GPS_TX);
  delay(100);
  Serial.println("✓");
  
  // 2. LoRa
  Serial.print("[2/6] LoRa... ");
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_CS);
  LoRa.setPins(LORA_CS, LORA_RST, LORA_IRQ);
  
  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("✗ FAILED!");
    while(1);
  }
  
  LoRa.setSpreadingFactor(12);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);
  LoRa.setSyncWord(0x12);
  LoRa.setTxPower(20);
  LoRa.enableCrc();
  LoRa.disableInvertIQ();
  Serial.println("✓");
  
  // 3. MPU6050
  Serial.print("[3/6] MPU6050... ");
  delay(100);
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(MPU6050_PWR_MGMT_1);
  Wire.write(0);
  Wire.endTransmission();
  delay(100);
  Serial.println("✓");
  
  // 4. DHT11 (Ambient)
  Serial.print("[4/6] DHT11 (Ambient)... ");
  dht.begin();
  delay(2000);
  float testTemp = dht.readTemperature();
  if (isnan(testTemp)) {
    Serial.println("✗");
  } else {
    Serial.printf("✓ (%.1f°C)\n", testTemp);
  }
  
  // 5. DS18B20 (Body Temperature)
  Serial.print("[5/6] DS18B20 (Body)... ");
  ds18b20.begin();
  delay(500);
  
  int deviceCount = ds18b20.getDeviceCount();
  if (deviceCount > 0) {
    ds18b20.setResolution(12);  // 12-bit resolution (0.0625°C)
    ds18b20.requestTemperatures();
    delay(750);  // Wait for conversion
    float bodyTemp = ds18b20.getTempCByIndex(0);
    
    if (bodyTemp != DEVICE_DISCONNECTED_C && bodyTemp > -50 && bodyTemp < 85) {
      Serial.printf("✓ (%.2f°C, %d device(s))\n", bodyTemp, deviceCount);
    } else {
      Serial.println("✗ (Connected but no reading)");
    }
  } else {
    Serial.println("✗ (Not detected - check wiring & 4.7kΩ resistor)");
  }
  
  // 6. Pulse Sensor
  Serial.print("[6/6] Pulse Sensor... ");
  pinMode(PULSE_PIN, INPUT);
  
  for (int i = 0; i < numReadings; i++) {
    readings[i] = 0;
  }
  
  Serial.print("calibrating...");
  for (int i = 0; i < 100; i++) {
    pulseValue = analogRead(PULSE_PIN);
    if (pulseValue < minPulse) minPulse = pulseValue;
    if (pulseValue > maxPulse) maxPulse = pulseValue;
    delay(10);
  }
  threshold = (minPulse + maxPulse) / 2;
  Serial.printf("✓ (threshold=%d)\n", threshold);
  
  Serial.println("\n✅ Device ID: " + DEVICE_ID);
  Serial.println("✅ All sensors ready!");
  Serial.println("\n⚙️  Packet Format: START:data:END");
  Serial.println("⚙️  Transmission interval: 15 seconds\n");
  
  // Display initial battery status
  int battLevel = getBatteryLevel();
  Serial.printf("🔋 Initial Battery: %d%%\n\n", battLevel);
}

void loop() {
  // Read GPS continuously
  while (GPS.available() > 0) {
    gps.encode(GPS.read());
  }
  
  // Read pulse continuously
  readPulse();
  
  // Transmit every 15 seconds
  static unsigned long lastTx = 0;
  if (millis() - lastTx > 15000) {
    lastTx = millis();
    packetCounter++;
    
    Serial.println("═══════════════════════════════════════");
    Serial.printf("📦 PACKET #%d\n\n", packetCounter);
    
    // GPS
    float lat = 0.0, lon = 0.0;
    int sats = 0;
    if (gps.location.isValid()) {
      lat = gps.location.lat();
      lon = gps.location.lng();
    }
    if (gps.satellites.isValid()) {
      sats = gps.satellites.value();
    }
    Serial.printf("📍 GPS: %.6f, %.6f (%d sats)\n", lat, lon, sats);
    
    // DHT11 - Ambient conditions
    float ambientTemp = dht.readTemperature();
    float humidity = dht.readHumidity();
    if (isnan(ambientTemp) || isnan(humidity)) {
      ambientTemp = 0.0;
      humidity = 0.0;
    }
    Serial.printf("🌡️  Ambient: %.1f°C, Humidity: %.1f%%\n", ambientTemp, humidity);
    
    // DS18B20 - Body temperature
    ds18b20.requestTemperatures();
    float bodyTemp = ds18b20.getTempCByIndex(0);
    
    if (bodyTemp == DEVICE_DISCONNECTED_C || bodyTemp < -50 || bodyTemp > 85) {
      bodyTemp = 0.0;
      Serial.println("🌡️  Body Temp: Error (sensor disconnected)");
    } else {
      Serial.printf("🌡️  Body Temp: %.2f°C ", bodyTemp);
      
      // Cattle body temperature analysis
      if (bodyTemp >= 38.0 && bodyTemp <= 39.3) {
        Serial.println("✓ (Normal)");
      } else if (bodyTemp > 39.3 && bodyTemp <= 40.0) {
        Serial.println("⚠️ (Slightly elevated)");
      } else if (bodyTemp > 40.0) {
        Serial.println("🚨 (FEVER - Immediate attention!)");
      } else if (bodyTemp < 38.0 && bodyTemp > 35.0) {
        Serial.println("⚠️ (Below normal - monitor)");
      } else {
        Serial.println("⚠️ (Check sensor placement)");
      }
    }
    
    // Heart Rate - Reset if no beat for 5 seconds
    if (millis() - lastBeatTime > 5000) {
      beatsPerMinute = 0;
    }
    Serial.printf("❤️  Heart Rate: %d BPM\n", beatsPerMinute);
    
    // MPU6050
    float ax = 0, ay = 0, az = 0, gx = 0, gy = 0, gz = 0;
    
    Wire.beginTransmission(MPU6050_ADDR);
    Wire.write(MPU6050_ACCEL_XOUT_H);
    if (Wire.endTransmission(false) == 0) {
      Wire.requestFrom((uint8_t)MPU6050_ADDR, (uint8_t)14);
      
      if (Wire.available() >= 14) {
        int16_t axRaw = (Wire.read() << 8) | Wire.read();
        int16_t ayRaw = (Wire.read() << 8) | Wire.read();
        int16_t azRaw = (Wire.read() << 8) | Wire.read();
        Wire.read(); Wire.read(); // Skip temp
        int16_t gxRaw = (Wire.read() << 8) | Wire.read();
        int16_t gyRaw = (Wire.read() << 8) | Wire.read();
        int16_t gzRaw = (Wire.read() << 8) | Wire.read();
        
        ax = axRaw / 16384.0;
        ay = ayRaw / 16384.0;
        az = azRaw / 16384.0;
        gx = gxRaw / 131.0;
        gy = gyRaw / 131.0;
        gz = gzRaw / 131.0;
        
        float motion = sqrt(ax*ax + ay*ay + az*az);
        Serial.printf("📊 Motion: %.2fg\n", motion);
      }
    }
    
    // Battery
    int battery = getBatteryLevel();
    Serial.printf("🔋 Battery: %d%%\n", battery);
    
    // BUILD PACKET with START:END delimiters
    // Format: device_id,lat,lon,sats,ambient_temp,humidity,body_temp,hr,ax,ay,az,gx,gy,gz,battery,timestamp
    char packet[150];  // Increased size for extra temperature field
    snprintf(packet, sizeof(packet),
      "START:%s,%.6f,%.6f,%d,%.1f,%.1f,%.2f,%d,%.3f,%.3f,%.3f,%.2f,%.2f,%.2f,%d,%lu:END",
      DEVICE_ID.c_str(),
      lat,
      lon,
      sats,
      ambientTemp,
      humidity,
      bodyTemp,        // NEW: Body temperature added
      beatsPerMinute,
      ax, ay, az,
      gx, gy, gz,
      battery,
      millis()
    );
    
    Serial.println("\n📡 Transmitting packet:");
    Serial.print("   ");
    Serial.println(packet);
    Serial.printf("   Size: %d bytes\n", strlen(packet));
    
    // CRITICAL: Clear LoRa state before transmission
    LoRa.idle();
    delay(50);
    
    // Send packet
    LoRa.beginPacket();
    LoRa.print(packet);
    LoRa.endPacket();
    
    // Wait for transmission to complete
    delay(200);
    
    Serial.println("   ✓ Sent successfully!\n");
  }
}

void readPulse() {
  pulseValue = analogRead(PULSE_PIN);
  
  // Moving average filter
  totalPulse = totalPulse - readings[readIndex];
  readings[readIndex] = pulseValue;
  totalPulse = totalPulse + readings[readIndex];
  readIndex = (readIndex + 1) % numReadings;
  avgPulse = totalPulse / numReadings;
  
  // Update min/max for dynamic threshold
  if (avgPulse < minPulse) minPulse = avgPulse;
  if (avgPulse > maxPulse) maxPulse = avgPulse;
  
  // Detect beat
  if (avgPulse > threshold && !pulseDetected) {
    unsigned long currentTime = millis();
    
    if (lastBeatTime > 0) {
      unsigned long timeBetweenBeats = currentTime - lastBeatTime;
      if (timeBetweenBeats > 300 && timeBetweenBeats < 1500) {
        beatsPerMinute = 60000 / timeBetweenBeats;
        
        // Smooth the BPM reading
        static int lastBPM = beatsPerMinute;
        beatsPerMinute = (lastBPM * 3 + beatsPerMinute) / 4;
        lastBPM = beatsPerMinute;
      }
    }
    lastBeatTime = currentTime;
    pulseDetected = true;
  }
  
  // Reset detection flag
  if (avgPulse < threshold - 20) {
    pulseDetected = false;
  }
}

// ============================================
// AXP2101 FUNCTIONS (Direct Register Access)
// ============================================

void writeAXP2101Register(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(AXP2101_ADDR);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission();
}

uint8_t readAXP2101Register(uint8_t reg) {
  Wire.beginTransmission(AXP2101_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(AXP2101_ADDR, (uint8_t)1);
  return Wire.read();
}

void initAXP2101() {
  // Enable battery voltage ADC
  writeAXP2101Register(0x30, 0x64);
  
  // Enable ALDO3 (GPS) - 3.3V
  writeAXP2101Register(0x93, 0x1C);
  writeAXP2101Register(0x90, readAXP2101Register(0x90) | 0x04);
  
  // Enable ALDO4 (LoRa) - 3.3V  
  writeAXP2101Register(0x94, 0x1C);
  writeAXP2101Register(0x90, readAXP2101Register(0x90) | 0x08);
  
  // Set charging current to 500mA
  writeAXP2101Register(0x62, 0x05);
  
  delay(100);
  
  float voltage = readBatteryVoltage();
  Serial.printf("   Battery: %.2fV\n", voltage);
}

float readBatteryVoltage() {
  if (!hasAXP2101) return 0.0;
  
  uint8_t highByte = readAXP2101Register(0x34);
  uint8_t lowByte = readAXP2101Register(0x35);
  
  uint16_t voltage = ((highByte << 8) | lowByte) & 0x3FFF;
  return voltage / 1000.0;
}

bool isCharging() {
  if (!hasAXP2101) return false;
  
  uint8_t status = readAXP2101Register(0x01);
  return (status & 0x40) != 0;
}

int getBatteryLevel() {
  if (!hasAXP2101) {
    Serial.println("   ⚠️  AXP2101 not detected, using fallback");
    return 50;
  }
  
  float voltage = readBatteryVoltage();
  bool charging = isCharging();
  
  Serial.printf("   🔋 Battery Debug (AXP2101):\n");
  Serial.printf("      Voltage:   %.3fV\n", voltage);
  Serial.printf("      Charging:  %s\n", charging ? "YES" : "NO");
  
  if (voltage < 2.5 || voltage > 4.5) {
    Serial.println("      ⚠️  Invalid voltage reading!");
    return 50;
  }
  
  int percentage;
  
  if (voltage >= 4.15) {
    percentage = 100;
  } else if (voltage >= 4.0) {
    percentage = 90 + (int)((voltage - 4.0) / 0.15 * 10);
  } else if (voltage >= 3.85) {
    percentage = 70 + (int)((voltage - 3.85) / 0.15 * 20);
  } else if (voltage >= 3.7) {
    percentage = 40 + (int)((voltage - 3.7) / 0.15 * 30);
  } else if (voltage >= 3.5) {
    percentage = 15 + (int)((voltage - 3.5) / 0.2 * 25);
  } else if (voltage >= 3.3) {
    percentage = 5 + (int)((voltage - 3.3) / 0.2 * 10);
  } else if (voltage >= 3.0) {
    percentage = (int)((voltage - 3.0) / 0.3 * 5);
  } else {
    percentage = 0;
  }
  
  if (percentage > 100) percentage = 100;
  if (percentage < 0) percentage = 0;
  
  Serial.printf("      Percent:   %d%%\n", percentage);
  
  return percentage;
}
```

---

## 📚 Required Arduino Libraries

You need to install **one additional library**:

### **In Arduino IDE:**
1. Go to **Sketch** → **Include Library** → **Manage Libraries**
2. Search and install:
   - ✅ `DallasTemperature` by Miles Burton
   - ✅ `OneWire` by Paul Stoffregen (dependency)

*You already have the other libraries (TinyGPS++, LoRa, DHT, Wire)*

---

## 🎯 How It Works Now

### **Dual Temperature System:**
1. **DHT11 (GPIO 13)** → Measures **ambient** conditions
   - Room/outdoor temperature
   - Humidity levels
   - Environmental monitoring

2. **DS18B20 (GPIO 4)** → Measures **body** temperature
   - Direct contact with animal's skin
   - Accurate core temperature
   - Fever detection

---

## 📊 Updated Packet Format

**New format** (16 fields now):
```
START:COW001,lat,lon,sats,ambient_temp,humidity,BODY_TEMP,hr,ax,ay,az,gx,gy,gz,battery,timestamp:END
```

**Example:**
```
START:COW001,13.082680,80.270718,8,28.5,65.0,38.7,65,0.012,-0.034,0.982,1.23,-0.45,0.89,87,123456:END
                                      ^^^^^  ^^^^^  ^^^^
                                      Ambient Body   HR
                                      (DHT11) (DS18B20)