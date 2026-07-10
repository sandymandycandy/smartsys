# 🚀 Smart Pastoralism - Technology Stack

## 📋 Table of Contents
- [Hardware Components](#hardware-components)
- [Backend Stack](#backend-stack)
- [Frontend Stack](#frontend-stack)
- [IoT & Embedded Systems](#iot--embedded-systems)
- [Machine Learning & AI](#machine-learning--ai)
- [Database & Storage](#database--storage)
- [Communication Protocols](#communication-protocols)
- [Development & Deployment](#development--deployment)

---

## 🔧 Hardware Components

### **IoT Collar Device (ESP32-based)**
| Component | Model/Type | Purpose |
|-----------|------------|---------|
| **Microcontroller** | ESP32 (T-BEAM V1.2) | Main processing unit |
| **GPS Module** | NEO-6M/7M | Location tracking |
| **LoRa Transceiver** | SX1276 (433MHz) | Long-range wireless communication |
| **Temperature Sensors** | DHT11 + DS18B20 | Ambient & body temperature monitoring |
| **Motion Sensor** | MPU6050 (6-axis) | Accelerometer + Gyroscope for activity tracking |
| **Heart Rate Sensor** | Analog Pulse Sensor | Livestock heart rate monitoring |
| **Power Management** | AXP2101 PMU | Battery management & charging |
| **Battery** | 18650 Li-ion | Power source |

### **Gateway/Receiver**
| Component | Purpose |
|-----------|---------|
| **Raspberry Pi 5** | Central server & LoRa receiver |
| **LoRa Module** | SX1276 receiver for data collection |

---

## 🖥️ Backend Stack

### **Core Framework**
```python
FastAPI 0.104.1+          # Modern async web framework
Uvicorn 0.24.0+           # ASGI server
Python 3.8+               # Programming language
```

### **Key Features**
- ✅ **Asynchronous** - Non-blocking I/O for high performance
- ✅ **RESTful API** - Clean API design with automatic OpenAPI docs
- ✅ **WebSocket Support** - Real-time bidirectional communication
- ✅ **Type Hints** - Better code quality and IDE support
- ✅ **Dependency Injection** - Clean architecture

### **Backend Libraries**
| Library | Version | Purpose |
|---------|---------|---------|
| `python-multipart` | 0.0.6+ | Form data handling |
| `python-dotenv` | 1.0.0+ | Environment configuration |
| `jinja2` | 3.1.2+ | Server-side templating |
| `requests` | 2.31.0+ | HTTP client for external APIs |
| `python-dateutil` | 2.8.2+ | Date/time utilities |

---

## 🎨 Frontend Stack

### **Core Technologies**
```html
HTML5                     # Structure
CSS3                      # Styling with modern features
Vanilla JavaScript        # Client-side logic (ES6+)
```

### **UI Framework & Libraries**
| Technology | Purpose |
|------------|---------|
| **Alpine.js** | Lightweight reactive framework (Vue-like syntax) |
| **Tailwind CSS** | Utility-first CSS framework |
| **Chart.js** | Interactive data visualization |
| **Leaflet.js** | Interactive maps & geofencing |
| **Leaflet.draw** | Drawing tools for geofences |

### **Design Features**
- 🎨 **Responsive Design** - Mobile-first approach
- 🌙 **Dark Mode** - Eye-friendly interface
- 📊 **Real-time Updates** - WebSocket-powered live data
- 🗺️ **Interactive Maps** - GPS tracking & geofencing
- 📈 **Dynamic Charts** - Temperature, heart rate, analytics

---

## 📡 IoT & Embedded Systems

### **ESP32 Firmware**
```cpp
Arduino Framework         # Development platform
C/C++                    # Programming language
```

### **ESP32 Libraries**
| Library | Purpose |
|---------|---------|
| `TinyGPS++` | GPS data parsing |
| `LoRa.h` | LoRa communication |
| `DHT.h` | DHT11 temperature sensor |
| `OneWire.h` + `DallasTemperature.h` | DS18B20 body temperature |
| `Wire.h` | I2C communication (MPU6050, AXP2101) |
| `HardwareSerial` | GPS serial communication |

### **Sensor Configuration**
```cpp
LoRa Frequency: 433 MHz
Spreading Factor: 12 (maximum range)
Bandwidth: 125 kHz
Coding Rate: 4/5
TX Power: 20 dBm (maximum)
Transmission Interval: 15 seconds
```

---

## 🤖 Machine Learning & AI

### **ML Framework**
```python
scikit-learn 1.3.0+       # Primary ML library
numpy 1.24.3+             # Numerical computing
pandas 2.0.3+             # Data manipulation
```

### **ML Models Implemented**

#### **1. Anomaly Detection**
- **Algorithm**: Isolation Forest
- **Purpose**: Detect unusual health patterns
- **Features**: 8 engineered features
  - Temperature, Heart Rate, Motion Magnitude
  - Temperature change rate, HR change rate, Motion variability
  - Temperature std deviation, HR std deviation
- **Contamination**: 10% (expects 10% anomalies)

#### **2. Disease Classification**
- **Type**: Rule-based + ML hybrid
- **Diseases Detected**:
  - Fever (temp > 40°C)
  - Heat Stress (temp > 39.5°C + HR > 85)
  - Respiratory Issues (HR > 90 + low motion)
  - Lameness (low motion + low temp)

#### **3. Health Forecasting**
- **Method**: Moving average with trend analysis
- **Prediction**: 24-hour health metrics forecast
- **Risk Levels**: Low, Medium, High

### **ML Features**
- ✅ Automatic model training on historical data
- ✅ Real-time anomaly prediction
- ✅ Confidence scoring
- ✅ Human-readable explanations
- ✅ Model persistence (pickle)

---

## 💾 Database & Storage

### **Primary Database**
```
SQLite 3                  # Embedded relational database
```

### **Database Files**
| Database | Purpose |
|----------|---------|
| `livestock_data.db` | Main sensor readings & livestock data |
| `geofences.db` | Geofence definitions & violations |
| `notifications.db` | Email/SMS notification logs |
| `sessions.db` | User authentication sessions |
| `thresholds.db` | Alert threshold configurations |
| `weather.db` | Weather data cache |

### **Key Tables**
- `livestock_readings` - Sensor data (temp, HR, GPS, motion, battery)
- `alerts` - Health alerts with temperature, HR, battery context
- `geofences` - Polygon/circle geofence definitions
- `geofence_violations` - Violation logs
- `notification_settings` - Email/SMS configuration
- `users` - Authentication & authorization

---

## 📞 Communication Protocols

### **Wireless Communication**
| Protocol | Range | Use Case |
|----------|-------|----------|
| **LoRa** | 2-15 km | ESP32 → Raspberry Pi data transmission |
| **Wi-Fi** | 50-100m | Raspberry Pi → Internet connectivity |
| **WebSocket** | N/A | Real-time browser updates |
| **HTTP/REST** | N/A | API communication |

### **Data Format**
```
LoRa Packet Format (CSV):
START:device_id,lat,lon,sats,ambient_temp,humidity,body_temp,hr,
      ax,ay,az,gx,gy,gz,battery,timestamp:END

Example:
START:COW001,12.345678,77.654321,8,28.5,65.0,38.2,72,
      0.123,0.456,0.789,1.2,3.4,5.6,85,123456:END
```

---

## 🔔 Notification System

### **Email Notifications**
```python
SMTP (built-in)           # Email protocol
Gmail/Outlook support     # SMTP providers
```

### **SMS Notifications**
```python
Twilio 8.10.0+           # SMS API service
```

### **Notification Triggers**
- 🚨 Critical temperature alerts
- ❤️ Abnormal heart rate
- 🔋 Low battery warnings
- 📍 Geofence violations
- 🤖 ML-detected anomalies

---

## 🌐 External APIs & Services

### **Weather API**
```
OpenWeatherMap API        # Weather data integration
```

### **Geolocation**
```
Leaflet.js + OpenStreetMap # Map tiles & rendering
```

---

## 🛠️ Development & Deployment

### **Development Tools**
```bash
Git                       # Version control
VS Code / Arduino IDE     # Code editors
Python Virtual Env        # Dependency isolation
```

### **Production Server**
```python
Gunicorn 21.2.0+         # Production WSGI server
systemd                  # Linux service management
```

### **Deployment Platform**
- **Raspberry Pi 5** (Debian-based Linux)
- **IP**: `10.143.38.80:8000`
- **Auto-start**: systemd service

### **Service Files**
```bash
smart-pastoralism.service        # Main web app
smartpastoral-receiver.service   # LoRa receiver
```

---

## 📦 Package Management

### **Python Dependencies**
```bash
pip install -r requirements.txt
```

### **Arduino Libraries**
```bash
# Install via Arduino Library Manager:
- TinyGPS++
- LoRa
- DHT sensor library
- OneWire
- DallasTemperature
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    ESP32 IoT Collar                         │
│  GPS + LoRa + Temp + HR + Motion + Battery                  │
└────────────────────┬────────────────────────────────────────┘
                     │ LoRa (433MHz)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Raspberry Pi 5 Gateway                         │
│  LoRa Receiver → SQLite → FastAPI Server                    │
│  ML Models + WebSocket + REST API                           │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/WebSocket
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Web Dashboard                              │
│  HTML + CSS + JavaScript + Alpine.js + Chart.js + Leaflet   │
│  Real-time monitoring + Analytics + Geofencing              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 Security Features

- ✅ **Authentication**: Session-based user login
- ✅ **Environment Variables**: Sensitive data in `.env`
- ✅ **HTTPS Ready**: Can be deployed with reverse proxy (nginx)
- ✅ **Input Validation**: FastAPI automatic validation
- ✅ **SQL Injection Protection**: Parameterized queries

---

## 📊 Performance Characteristics

| Metric | Value |
|--------|-------|
| **LoRa Range** | 2-15 km (line of sight) |
| **Data Update Rate** | Every 15 seconds |
| **WebSocket Latency** | < 100ms |
| **ML Prediction Time** | < 50ms |
| **Battery Life** | 24-48 hours (depends on usage) |
| **Concurrent Users** | 50+ (with Uvicorn) |

---

## 🎯 Key Differentiators

1. **Real-time ML Predictions** - Anomaly detection on live data
2. **Long-range Communication** - LoRa for rural areas without internet
3. **Multi-sensor Fusion** - GPS + Temp + HR + Motion for comprehensive health
4. **Geofencing** - Automatic alerts when animals leave safe zones
5. **Scalable Architecture** - Can handle multiple collars simultaneously
6. **Low Power Design** - Optimized for battery-powered operation

---

## 📚 Documentation

- `DOCUMENTATION.md` - System overview
- `DEPLOYMENT_GUIDE.md` - Deployment instructions
- `FEATURES_OVERVIEW.md` - Feature details
- `ADVANCED_FEATURES.md` - ML & advanced features
- `QUICKSTART.md` - Quick setup guide
- `BUG_FIXES_2025-12-19.md` - Recent bug fixes

---

## 🔄 Version Control

```
Repository: Local Git
Branch Strategy: Main branch
Deployment: Manual deployment to Raspberry Pi
```

---

## 🌟 Future Enhancements (Potential)

- 🔮 **Deep Learning**: TensorFlow/PyTorch for advanced predictions
- 📱 **Mobile App**: React Native or Flutter
- ☁️ **Cloud Integration**: AWS IoT / Azure IoT Hub
- 🔊 **Voice Alerts**: Text-to-speech notifications
- 📸 **Camera Integration**: Visual health monitoring
- 🌐 **Multi-language Support**: i18n implementation

---

**Last Updated**: 2025-12-19  
**System Status**: ✅ Production Ready  
**Current IP**: `10.143.38.80:8000`
