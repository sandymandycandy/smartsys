# 🐄 Smart Pastoralism - Advanced AI Livestock Monitoring System

![System Status](https://img.shields.io/badge/System-Production%20Ready-success)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green)
![LoRa](https://img.shields.io/badge/LoRa-433MHz-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

**Smart Pastoralism** is a comprehensive, enterprise-grade IoT solution designed for modern livestock management. It combines low-power long-range (LoRa) hardware with a powerful AI-driven backend to provide real-time health monitoring, disease prediction, and geolocation tracking for cattle.

---

## 🌟 Key Features

### 📡 Data Acquisition (IoT)
*   **Multi-Sensor Data Collection**: 
    *   **Body Temperature**: DS18B20 (accuracy ±0.5°C)
    *   **Heart Rate**: Pulse Sensor (BPM)
    *   **Motion**: MPU6050 6-Axis IMU (Accelerometer + Gyroscope) for activity & posture analysis.
    *   **Environment**: DHT11 (Ambient Temp & Humidity)
    *   **Location**: U-blox NEO-6M GPS (Latitude, Longitude)
    *   **Power**: AXP192/AXP2101 PMU for detailed battery monitoring.
*   **Long-Range Communication**: Uses LoRa (SX1278) at 433MHz for transmissions up to 10km in rural areas.
*   **Robust Custom Packet Protocol**: `START:data:END` format with error checking.

### 🧠 AI & Analytics Core
*   **Disease Prediction Engine**: Uses Machine Learning (Random Forest/XGBoost) to predict:
    *   Fever / Hyperthermia
    *   Heat Stress
    *   Respiratory Distress
    *   Lameness / Injury
    *   Digestive Issues
*   **Anomaly Detection**: Real-time outlier detection using Isolation Forest algorithms.
*   **Activity Classification**: Distinguishes between Grazing, Resting, Walking, and Running based on IMU data.
*   **Health Forecasting**: predicts health trends for the next 24-72 hours.

### 💻 Web Dashboard & Interface
*   **FastAPI Backend**: High-performance, async Python web server.
*   **Interactive Dashboard**:
    *   Live Map with Geofencing boundaries.
    *   Real-time charts (Heart Rate, Temperature).
    *   Individual animal profiles.
*   **Alert System**:
    *   **Visual**: Dashboard popups and color-coded status.
    *   **SMS**: Integration with Twilio for critical alerts (e.g., "Cow 001 Fever Detected!").
    *   **Email**: Automated daily reports and warnings via SMTP.

---

## 🛠️ Hardware Stack

### **Transmitter Node (Collar)**
| Component | Function | Pins Used |
|-----------|----------|-----------|
| **TTGO T-Beam v1.1/V1.2** | MCU + LoRa + GPS | - |
| **MPU6050** | 6-Axis Motion Sensor | SDA: 13, SCL: 14 |
| **DS18B20** | Body Temperature | GPIO 4 |
| **DHT11** | Ambient Temp/Hum | GPIO 25 |
| **Pulse Sensor** | Heart Rate | GPIO 15 |
| **Proprietary Antenna** | LoRa 433MHz | - |

### **Gateway (Receiver)**
*   **Raspberry Pi 5** (Recommended) or Pi 4/3.
*   **LoRa Module**: SX1278 (SPI Interface).
*   **Pinout**:
    *   NSS/CS: GPIO 8 (CE0)
    *   DIO0: GPIO 25 (or polling)
    *   RST: GPIO 25
    *   MOSI/MISO/SCK: Standard SPI pins.

---

## 📂 Project Structure

```bash
smart_pastoralism/
├── app/                        # FastAPI Backend Application
│   ├── routes/                 # API Endpoints (api.py, ml_api.py, etc.)
│   ├── services/               # Logic Layer (LoRa, ML, Notifications)
│   ├── templates/              # Jinja2 HTML Templates
│   ├── static/                 # CSS, JS Assets
│   └── websocket/              # Real-time WebSocket handlers
├── esp32code_sketch/           # Arduino Firmware
│   └── esp32code_sketch.ino    # Main Transmitter Code
├── ml_models/                  # Saved ML Models (.pkl)
├── deployment/                 # Docker/Systemd configs
├── reciver_rpi5.py             # Main Gateway Script (Python)
├── requirements.txt            # Python Dependencies
└── README.md                   # This file
```

---

## 🚀 Setup & Installation

### 1. Hardware Firmware (ESP32)
1.  Open `esp32code_sketch/esp32code_sketch.ino` in Arduino IDE or VS Code with PlatformIO.
2.  Install required libraries:
    *   `TinyGPS++`
    *   `LoRa`
    *   `Adafruit MPU6050` & `Adafruit Unified Sensor`
    *   `DHT sensor library`
    *   `DallasTemperature` & `OneWire`
3.  Select Board: **TTGO T-Beam**.
4.  Upload to the device.

### 2. Gateway Setup (Raspberry Pi)
1.  Enable SPI on Raspberry Pi: `sudo raspi-config` -> Interface Options -> SPI.
2.  Install system dependencies:
    ```bash
    sudo apt update
    sudo apt install python3-pip libatlas-base-dev
    ```
3.  Install Python libraries:
    ```bash
    pip3 install -r requirements.txt
    pip3 install spidev RPi.GPIO gpiozero
    ```

### 3. Web Dashboard
1.  Configure environment:
    ```bash
    cp .env.example .env
    # Edit .env with your settings (SMS keys, Email credentials, Database URL)
    ```
2.  Run the application:
    ```bash
    python3 run.py
    ```
3.  Access the dashboard at `http://localhost:8000`.

---

## 📊 API Documentation

The system exposes a full REST API for data access and integration.

*   **Swagger UI**: `http://localhost:8000/docs`
*   **ReDoc**: `http://localhost:8000/redoc`

**Key Endpoints:**
*   `GET /api/ingest/reading`: Receive data from Gateway.
*   `GET /api/animals`: List all monitored animals.
*   `GET /api/ml/predict/disease/{id}`: Trigger manual disease analysis.
*   `GET /api/map/locations`: Get GeoJSON data for map.

---

## 🤝 Contributing

Contributions are welcome! Please read the `CONTRIBUTING.md` (if available) or submit a Pull Request.

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Developed by Smart Patrolism Team**  
*Integrated System for Sustainable Livestock Management*
