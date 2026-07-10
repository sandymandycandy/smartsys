# 🎯 Smart Pastoralism Demo - Quick Start Guide

## ✅ Current Status

### **Server Running**
- ✅ Main Application: `http://localhost:8000`
- ✅ Dashboard: `http://localhost:8000/dashboard`
- ✅ API Docs: `http://localhost:8000/docs`

### **Demo Data Generation**
- 🔄 Currently generating 24 hours of historical data
- 📊 5 Animals with different health profiles
- 📈 ~480 total readings (96 per animal)

---

## 🐄 Demo Animals

| Device ID | Name | Type | Health Status | Base Temp | Base HR |
|-----------|------|------|---------------|-----------|---------|
| **COW001** | Bessie | Cow | 🟢 Healthy | 38.5°C | 65 BPM |
| **COW002** | Daisy | Cow | 🔴 Fever | 40.2°C | 85 BPM |
| **COW003** | Molly | Cow | 🟢 Healthy | 38.8°C | 70 BPM |
| **SHEEP001** | Dolly | Sheep | 🟡 Heat Stress | 39.8°C | 90 BPM |
| **SHEEP002** | Shaun | Sheep | 🟢 Healthy | 39.0°C | 75 BPM |

---

## 🌐 Dashboard Features

### **Main Dashboard** (`/dashboard`)
- 📊 **Herd Overview**: Total animals, health status, alerts
- 🗺️ **Live Map**: Real-time GPS tracking of all animals
- 📈 **Recent Readings**: Latest sensor data
- 🚨 **Active Alerts**: Critical health warnings
- 🔋 **Battery Status**: Device battery levels

### **Analytics Page** (`/dashboard/analytics`)
- 📉 **Temperature Trends**: Historical temperature charts
- ❤️ **Heart Rate Distribution**: HR patterns
- 🚨 **Alerts by Type**: Alert categorization
- 📊 **Alert Trends**: Time-series alert analysis

### **ML Insights** (`/dashboard/ml-insights`)
- 🤖 **Anomaly Detection**: AI-powered health anomalies
- 🔮 **Disease Predictions**: ML-based disease classification
- 📈 **Health Forecasting**: 24-hour predictions
- 🎯 **Model Performance**: ML model statistics

### **Settings Pages**
- ⚙️ **Thresholds** (`/settings/thresholds`): Configure alert limits
- 📧 **Notifications** (`/settings/notifications`): Email/SMS setup
- 🗺️ **Geofences** (`/settings/geofences`): Create safe zones
- 🌤️ **Weather** (`/settings/weather`): Weather integration

---

## 🎮 Demo Data Generator Options

### **Quick Start**
```bash
python demo_data_generator.py
```

### **Menu Options**
1. **1 hour of data** - Quick demo (20 readings per animal)
2. **6 hours of data** - Medium dataset (120 readings per animal)
3. **24 hours of data** - Full demo (480 readings per animal) ⭐
4. **Live simulation** - Real-time continuous data
5. **Quick test** - 10 test readings
6. **Exit**

---

## 📊 What You'll See

### **Healthy Animals (Bessie, Molly, Shaun)**
- ✅ Normal temperature (38-39°C)
- ✅ Normal heart rate (60-75 BPM)
- ✅ Active motion (0.8-1.2g)
- 🟢 No alerts

### **Fever Animal (Daisy - COW002)**
- 🔴 High temperature (40.2°C)
- 🔴 Elevated heart rate (85 BPM)
- ⚠️ Low activity (0.3-0.6g)
- 🚨 Critical temperature alerts
- 🤖 ML will detect anomaly

### **Heat Stress Animal (Dolly - SHEEP001)**
- 🟡 Elevated temperature (39.8°C)
- 🟡 High heart rate (90 BPM)
- ⚠️ Moderate activity (0.5-0.9g)
- ⚠️ Warning alerts

---

## 🔍 Testing Scenarios

### **1. Real-time Monitoring**
1. Open dashboard: `http://localhost:8000/dashboard`
2. Watch live updates as data comes in
3. See animals move on the map
4. Monitor health metrics

### **2. Alert System**
1. Check alerts for COW002 (fever)
2. Verify critical temperature warnings
3. Test notification system (if configured)

### **3. ML Predictions**
1. Go to ML Insights page
2. See anomaly detection for COW002
3. Check disease predictions
4. View health forecasts

### **4. Analytics**
1. Open Analytics page
2. View temperature trends over 24 hours
3. Compare healthy vs. sick animals
4. Analyze alert patterns

### **5. Geofencing** (Optional)
1. Go to Settings > Geofences
2. Create a geofence around Chennai (13.0827, 80.2707)
3. Set radius to 500m
4. Watch for violations if animals move outside

---

## 🚀 Quick Commands

### **Start Server**
```bash
python run.py
```

### **Generate Demo Data**
```bash
# Option 1: Interactive menu
python demo_data_generator.py

# Option 2: Simple continuous data
python simulate_data.py
```

### **Check Database**
```bash
python check_db.py
```

---

## 📱 Access Points

| Page | URL | Description |
|------|-----|-------------|
| **Landing** | http://localhost:8000 | Home page |
| **Dashboard** | http://localhost:8000/dashboard | Main monitoring |
| **Analytics** | http://localhost:8000/dashboard/analytics | Charts & graphs |
| **ML Insights** | http://localhost:8000/dashboard/ml-insights | AI predictions |
| **Livestock** | http://localhost:8000/dashboard/livestock | Animal list |
| **Alerts** | http://localhost:8000/dashboard/alerts | Alert management |
| **Settings** | http://localhost:8000/settings/thresholds | Configuration |
| **API Docs** | http://localhost:8000/docs | Interactive API |

---

## 🎨 UI Features

- ✨ **Modern Design**: Clean, professional interface
- 🌙 **Dark Mode**: Eye-friendly dark theme
- 📱 **Responsive**: Works on mobile, tablet, desktop
- 🔄 **Real-time**: WebSocket-powered live updates
- 📊 **Interactive Charts**: Hover, zoom, pan
- 🗺️ **Live Maps**: Leaflet.js with markers
- 🎯 **Alpine.js**: Reactive UI components

---

## 🔧 Troubleshooting

### **No Data Showing?**
1. Check if server is running: `http://localhost:8000/health`
2. Verify data generator is sending data
3. Check browser console for errors (F12)
4. Refresh the page

### **WebSocket Not Connecting?**
1. Check server logs for WebSocket errors
2. Verify port 8000 is not blocked
3. Try refreshing the page

### **Charts Not Loading?**
1. Wait for data generation to complete
2. Check if Chart.js is loaded (browser console)
3. Try the Analytics page

---

## 📈 Expected Results

After 24 hours of data generation:
- ✅ **480 total readings** in database
- ✅ **5 animals** tracked on map
- ✅ **Multiple alerts** for COW002 (fever)
- ✅ **ML anomalies** detected
- ✅ **Charts populated** with trends
- ✅ **Health forecasts** available

---

## 🎯 Demo Presentation Tips

1. **Start with Dashboard** - Show live monitoring
2. **Highlight Sick Animal** - Focus on COW002 alerts
3. **Show ML Predictions** - Demonstrate AI capabilities
4. **Display Analytics** - Show trend charts
5. **Demo Geofencing** - Create and test geofences
6. **Show API Docs** - Demonstrate REST API

---

## 📞 Support

- 📚 Documentation: `DOCUMENTATION.md`
- 🚀 Deployment: `DEPLOYMENT_GUIDE.md`
- 🔧 Tech Stack: `TECH_STACK.md`
- 🐛 Bug Fixes: `BUG_FIXES_2025-12-19.md`

---

**Last Updated**: 2025-12-19  
**Status**: ✅ Demo Ready  
**Data**: 🔄 Generating...
