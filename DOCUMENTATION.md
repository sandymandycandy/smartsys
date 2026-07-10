# 🐄 Smart Pastoralism - Complete Project Documentation

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Hardware Components](#hardware-components)
4. [Software Stack](#software-stack)
5. [Installation Guide](#installation-guide)
6. [Usage Instructions](#usage-instructions)
7. [API Documentation](#api-documentation)
8. [Troubleshooting](#troubleshooting)

---

## 📊 Project Overview

**Smart Pastoralism** is an IoT-based livestock monitoring system that uses LoRa communication to track animal health in real-time. The system monitors:

- 🌡️ **Body Temperature** (DS18B20 sensor)
- 🌡️ **Ambient Temperature & Humidity** (DHT11 sensor)
- ❤️ **Heart Rate** (Pulse sensor)
- 📍 **GPS Location** (NEO-6M GPS module)
- 🏃 **Motion & Activity** (MPU6050 6-axis IMU)
- 🔋 **Battery Status** (AXP192/2101 PMU)

**Key Features:**
- ✅ Long-range communication (up to 10km with LoRa)
- ✅ Real-time web dashboard
- ✅ AI-powered disease prediction
- ✅ Geofencing with alerts
- ✅ Email & SMS notifications
- ✅ Historical data analytics

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ESP32 Collar (Transmitter)               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ DS18B20  │  │  DHT11   │  │  Pulse   │  │ MPU6050  │   │
│  │ (Body T) │  │ (Ambient)│  │  Sensor  │  │ (Motion) │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │              │             │          │
│       └─────────────┴──────────────┴─────────────┘          │
│                         │                                    │
│                    ┌────▼────┐                              │
│                    │ ESP32   │                              │
│                    │ T-Beam  │                              │
│                    └────┬────┘                              │
│                         │                                    │
│                    ┌────▼────┐                              │
│                    │  LoRa   │ 433MHz                       │
│                    │ SX1278  │                              │
│                    └─────────┘                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ LoRa Radio
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Raspberry Pi 5 (Gateway/Server)                │
│  ┌──────────┐                                               │
│  │  LoRa    │  ──► reciver_rpi5.py ──► SQLite Database     │
│  │ SX1278   │                              │                │
│  └──────────┘                              │                │
│                                             ▼                │
│                                    ┌────────────────┐       │
│                                    │  FastAPI       │       │
│                                    │  Dashboard     │       │
│                                    │  (run.py)      │       │
│                                    └────────┬───────┘       │
│                                             │                │
│                                             ▼                │
│                                    ┌────────────────┐       │
│                                    │  WebSocket     │       │
│                                    │  Real-time UI  │       │
│                                    └────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ HTTP/WebSocket
                           ▼
                    ┌──────────────┐
                    │   Browser    │
                    │  Dashboard   │
                    └──────────────┘
```

---

## 🔧 Hardware Components

### ESP32 Transmitter (Collar)

| Component | Model | Pin | Function |
|-----------|-------|-----|----------|
| **Microcontroller** | TTGO T-Beam v1.1/1.2 | - | Main processor + LoRa + GPS |
| **Body Temp Sensor** | DS18B20 | GPIO 4 | Measures animal body temperature |
| **Ambient Sensor** | DHT11 | GPIO 25 | Ambient temp & humidity |
| **Heart Rate** | Pulse Sensor | GPIO 15 | Detects heartbeat |
| **Motion Sensor** | MPU6050 | SDA:13, SCL:14 | 6-axis accelerometer + gyroscope |
| **GPS** | NEO-6M | RX:34, TX:12 | Location tracking |
| **LoRa Radio** | SX1278 | Built-in | 433MHz long-range communication |
| **Power Management** | AXP192/2101 | SDA:21, SCL:22 | Battery monitoring |

**LoRa Configuration:**
- Frequency: 433 MHz
- Spreading Factor: 12
- Bandwidth: 125 kHz
- Coding Rate: 4/5
- Sync Word: 0x12
- TX Power: 20 dBm

### Raspberry Pi Gateway

| Component | Model | Connection |
|-----------|-------|------------|
| **Computer** | Raspberry Pi 5 (4GB+) | - |
| **LoRa Module** | SX1278 433MHz | SPI (GPIO 8, 25) |
| **Storage** | MicroSD 32GB+ | - |
| **Network** | Ethernet/WiFi | - |

---

## 💻 Software Stack

### ESP32 Firmware
- **Language**: C++ (Arduino)
- **Libraries**:
  - `TinyGPS++` - GPS parsing
  - `LoRa` - LoRa communication
  - `DHT sensor library` - DHT11
  - `DallasTemperature` + `OneWire` - DS18B20
  - `Adafruit MPU6050` - Motion sensor
  - `XPowersLib` - Power management

### Raspberry Pi Backend
- **Language**: Python 3.9+
- **Framework**: FastAPI
- **Database**: SQLite
- **Key Libraries**:
  - `spidev` - SPI communication for LoRa
  - `gpiozero` - GPIO control
  - `scikit-learn` - Machine learning
  - `requests` - HTTP communication
  - `python-socketio` - WebSocket

### Web Dashboard
- **Frontend**: Alpine.js + Tailwind CSS
- **Charts**: Chart.js
- **Maps**: Leaflet.js
- **Templates**: Jinja2

---

## 📥 Installation Guide

### 1. ESP32 Setup

**Install Arduino IDE:**
1. Download from [arduino.cc](https://www.arduino.cc/en/software)
2. Add ESP32 board support:
   - File → Preferences → Additional Board Manager URLs
   - Add: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3. Tools → Board → Boards Manager → Search "ESP32" → Install

**Install Libraries:**
```
Tools → Manage Libraries → Install:
- TinyGPS++
- LoRa by Sandeep Mistry
- DHT sensor library
- DallasTemperature
- OneWire
- Adafruit MPU6050
- Adafruit Unified Sensor
```

**Upload Firmware:**
1. Open `esp32code_sketch/esp32code_sketch.ino`
2. Select Board: "TTGO T-Beam"
3. Select Port: (your ESP32 port)
4. Click Upload

### 2. Raspberry Pi Setup

**Install OS:**
```bash
# Use Raspberry Pi Imager to install Raspberry Pi OS (64-bit)
# Enable SSH during setup
```

**Install Dependencies:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and tools
sudo apt install python3-pip python3-venv git -y

# Install system libraries
sudo apt install libatlas-base-dev -y

# Enable SPI
sudo raspi-config
# Interface Options → SPI → Enable
```

**Setup Project:**
```bash
# Clone or copy project files
cd ~
# (Copy smart_pastoralism folder to ~/smart_pastoralism)

# Create virtual environment
cd ~/smart_pastoralism
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

**Configure Environment:**
```bash
# Copy example config
cp .env.example .env

# Edit configuration
nano .env
# Set your SMTP, Twilio, and other settings
```

---

## 🚀 Usage Instructions

### Starting the System

**Method 1: Manual (Two Terminals)**

Terminal 1 - Dashboard:
```bash
cd ~/smart_pastoralism
source venv/bin/activate
python3 run.py
```

Terminal 2 - LoRa Receiver:
```bash
cd ~/smart_pastoralism
source venv/bin/activate
sudo python3 reciver_rpi5.py
```

**Method 2: One-Click Script**
```bash
cd ~/smart_pastoralism
chmod +x start_system.sh
./start_system.sh
```

### Accessing the Dashboard

1. Open browser: `http://192.168.1.12:8000/dashboard`
2. Login:
   - Username: `admin`
   - Password: `admin123`

### Stopping the System

**If using manual method:**
- Press `Ctrl+C` in each terminal

**If using script:**
- Press `Ctrl+C` once (stops everything)

**Force kill:**
```bash
sudo lsof -ti:8000 | xargs sudo kill -9
sudo pkill -9 python3
```

---

## 📡 API Documentation

### Base URL
```
http://192.168.1.12:8000
```

### Authentication
Session-based (login required for dashboard pages)

### Key Endpoints

#### Data Ingestion
```http
POST /api/ingest/reading
Content-Type: application/json

{
  "device_id": "COW001",
  "timestamp": 1702800000000,
  "temperature": 38.5,
  "body_temperature": 38.5,
  "ambient_temperature": 25.0,
  "humidity": 65.0,
  "heart_rate": 72,
  "battery": 85,
  "latitude": 13.0827,
  "longitude": 80.2707,
  "accel_x": 0.1,
  "accel_y": 0.2,
  "accel_z": 0.98,
  "gyro_x": 1.2,
  "gyro_y": -0.5,
  "gyro_z": 0.3,
  "motion_magnitude": 1.0,
  "rotation_speed": 1.5,
  "rssi": -75
}
```

#### Get Readings
```http
GET /api/readings?device_id=COW001&limit=100
```

#### Get Animal Summary
```http
GET /api/animals/summary
```

#### Get Active Alerts
```http
GET /api/alerts/active
```

#### Get Map Locations
```http
GET /api/map/locations
```

**Full API Docs:** `http://192.168.1.12:8000/docs`

---

## 🔍 Troubleshooting

### ESP32 Issues

**Problem: Upload fails**
```
Solution:
1. Hold BOOT button while uploading
2. Check USB cable (use data cable, not charge-only)
3. Try different USB port
4. Install CH340 drivers if needed
```

**Problem: LoRa not transmitting**
```
Solution:
1. Check antenna is connected
2. Verify LoRa frequency matches (433MHz)
3. Check power supply (needs 3.3V stable)
```

**Problem: GPS no fix**
```
Solution:
1. Move outdoors with clear sky view
2. Wait 2-5 minutes for cold start
3. Check antenna connection
```

**Problem: Sensors reading 0**
```
Solution:
- DS18B20: Check 4.7kΩ pull-up resistor
- DHT11: Wait 2 seconds after power-on
- Pulse: Ensure good skin contact
- MPU6050: Check I2C wiring (SDA/SCL)
```

### Raspberry Pi Issues

**Problem: Dashboard not accessible**
```bash
# Check if service is running
sudo lsof -i:8000

# Check logs
tail -f ~/smart_pastoralism/logs/dashboard.log

# Restart
sudo pkill python3
cd ~/smart_pastoralism && source venv/bin/activate && python3 run.py
```

**Problem: LoRa receiver not getting packets**
```bash
# Check SPI is enabled
ls /dev/spidev*
# Should show: /dev/spidev0.0

# Check LoRa module connection
sudo python3 -c "import spidev; spi=spidev.SpiDev(); spi.open(0,0); print('SPI OK')"

# Check receiver logs
tail -f ~/smart_pastoralism/logs/receiver.log
```

**Problem: Database errors**
```bash
# Check database
sqlite3 ~/smart_pastoralism/livestock_data.db "SELECT COUNT(*) FROM livestock_readings;"

# Repair database
cd ~/smart_pastoralism
python3 setup_db_force.py
```

**Problem: WebSocket not updating**
```
Solution:
1. Hard refresh browser (Ctrl+Shift+R)
2. Check browser console for errors (F12)
3. Restart dashboard service
```

### Network Issues

**Problem: Can't access from Windows**
```bash
# On Raspberry Pi, check IP
hostname -I

# On Windows, ping the Pi
ping 192.168.1.12

# Check firewall
sudo ufw status
# If active, allow port 8000:
sudo ufw allow 8000
```

---

## 📊 Data Format

### LoRa Packet Format
```
START:COW001,13.082680,80.270718,8,28.5,65.0,38.7,72,0.012,-0.034,0.982,1.23,-0.45,0.89,87,1702800000:END
```

**Fields:**
1. Device ID
2. Latitude
3. Longitude
4. Satellites
5. Ambient Temperature (°C)
6. Humidity (%)
7. Body Temperature (°C)
8. Heart Rate (BPM)
9-11. Accelerometer X,Y,Z (g)
12-14. Gyroscope X,Y,Z (°/s)
15. Battery (%)
16. Timestamp (ms)

---

## 🔐 Security Notes

1. **Change default password** after first login
2. **Use HTTPS** in production (setup reverse proxy with nginx)
3. **Restrict network access** (firewall rules)
4. **Regular backups** of database
5. **Update system** regularly: `sudo apt update && sudo apt upgrade`

---

## 📞 Support

For issues or questions:
1. Check this documentation
2. Review API docs: `http://192.168.1.12:8000/docs`
3. Check logs in `~/smart_pastoralism/logs/`

---

## 📄 License

MIT License - See LICENSE file

---

**Built with ❤️ for Smart Agriculture**
