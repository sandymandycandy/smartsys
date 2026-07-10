# 🔥 Activity Heatmap - Detailed Explanation

## 📋 Overview

The **Activity Heatmap** is a powerful visualization tool that shows **where animals spend their time** and **what their health status is** across your pasture. It uses color intensity to represent different metrics, helping you identify patterns, hotspots, and potential issues.

---

## 🎯 What the Heatmap Shows

### **Visual Representation**
The heatmap uses a **color gradient** to show intensity:

```
Blue → Cyan → Lime → Yellow → Red
(Low)                        (High)
```

- **Blue/Cyan**: Low activity or normal values
- **Lime/Yellow**: Moderate activity or elevated values  
- **Red**: High activity or critical values

---

## 📊 Four Data Visualization Modes

### **1. Activity (Location Density)** 🐄
**What it shows**: Where animals spend most of their time

**How it works**:
- Each GPS reading creates a "heat point"
- More readings in one area = Hotter color (red)
- Fewer readings = Cooler color (blue)

**Use Cases**:
- **Identify favorite grazing spots**
- **Find water sources** (high activity zones)
- **Detect shade areas** (animals cluster during hot days)
- **Spot unusual patterns** (animals avoiding certain areas)

**Example**:
```
🔴 Red hotspot near water trough
   → Animals drinking frequently (normal)

🔴 Red hotspot in corner of field
   → Possible fence issue or predator concern

🔵 Blue area in center
   → Animals avoiding this zone (investigate why)
```

---

### **2. Body Temperature** 🌡️
**What it shows**: Geographic distribution of animal body temperatures

**How it works**:
- Each location is colored based on the animal's temperature at that spot
- Temperature range: 35-40°C mapped to color gradient
- Formula: `intensity = (temperature - 35) / 5`

**Color Meaning**:
- **Blue (35-36°C)**: Below normal (hypothermia risk)
- **Cyan/Lime (37-38.5°C)**: Normal range
- **Yellow (38.5-39.5°C)**: Slightly elevated
- **Red (39.5-40°C+)**: Fever/heat stress

**Use Cases**:
- **Identify heat stress zones** (red areas in open sun)
- **Find cooling spots** (blue areas near shade/water)
- **Detect sick animals** (red spots that don't match environment)
- **Monitor seasonal patterns** (temperature changes by location)

**Example**:
```
🔴 Red cluster in south pasture at 2 PM
   → Heat stress zone, need more shade

🔵 Blue area near pond
   → Good cooling spot, animals healthy there

🟡 Yellow scattered points
   → Borderline temperatures, monitor closely
```

---

### **3. Heart Rate** ❤️
**What it shows**: Geographic distribution of heart rate readings

**How it works**:
- Each location colored by animal's heart rate
- HR range: 50-100 BPM mapped to gradient
- Formula: `intensity = (heart_rate - 50) / 50`

**Color Meaning**:
- **Blue (50-60 BPM)**: Resting/calm
- **Cyan/Lime (60-75 BPM)**: Normal activity
- **Yellow (75-85 BPM)**: Elevated (exercise or stress)
- **Red (85-100+ BPM)**: High stress or illness

**Use Cases**:
- **Find stressful areas** (red zones = high HR)
- **Identify calm zones** (blue = resting areas)
- **Detect predator activity** (sudden red spikes in specific areas)
- **Monitor exercise patterns** (yellow during active grazing)

**Example**:
```
🔴 Red cluster near fence line
   → Animals stressed by dogs/predators

🔵 Blue area under trees
   → Resting zone, animals calm

🟡 Yellow trail across field
   → Normal grazing activity
```

---

### **4. Alert Locations** 🚨
**What it shows**: Where health alerts occurred

**How it works**:
- Shows GPS locations where alerts were triggered
- Intensity based on alert severity
- Critical alerts = Red, Warnings = Yellow

**Use Cases**:
- **Identify problem zones** (repeated alerts in same area)
- **Environmental hazards** (toxic plants, contaminated water)
- **Disease hotspots** (infections spreading in specific areas)
- **Equipment issues** (faulty feeders, broken waterers)

**Example**:
```
🔴 Multiple red points near old barn
   → Possible mold/contamination issue

🟡 Yellow cluster in wet area
   → Foot rot risk from muddy conditions

🔵 Most of pasture blue
   → Healthy zones
```

---

## 📈 Statistics Dashboard

### **Data Points** 📍
- **What**: Total number of GPS readings used
- **Typical**: 100-1000+ depending on time range
- **Example**: 480 readings over 24 hours (5 animals × 96 readings each)

### **Animals Tracked** 🐄
- **What**: Number of unique devices/animals
- **Calculation**: Distinct device IDs in dataset
- **Example**: 5 animals (COW001, COW002, COW003, SHEEP001, SHEEP002)

### **Hotspot Zones** 🔥
- **What**: Number of high-activity areas detected
- **Calculation**: Clusters where readings > 10% of total
- **Typical**: 3-7 hotspots per pasture
- **Example**: Water source, shade area, feeding zone

### **Coverage** 📊
- **What**: Percentage of pasture area covered by readings
- **Calculation**: Based on GPS spread and density
- **Good**: >70% coverage
- **Example**: 82% = animals using most of available space

---

## 🗺️ Zone Analysis

### **What It Shows**
Breaks down the pasture into geographic zones and counts activity in each.

### **How Zones Are Created**
```python
# Simplified algorithm
1. Divide GPS coordinates into grid squares
2. Count readings in each square
3. Name zones by coordinates (e.g., "Zone 28_77")
4. Assign colors for visual distinction
5. Show top 5 most active zones
```

### **Example Zones**
| Zone | Color | Readings | Interpretation |
|------|-------|----------|----------------|
| Water Source | 🔴 Red | 95 | High activity (normal) |
| Shade Area | 🟡 Yellow | 75 | Moderate (good) |
| North Pasture | 🟢 Green | 85 | Active grazing |
| South Grazing | 🔵 Blue | 65 | Less preferred |
| Central Area | 🟣 Purple | 80 | Mixed use |

---

## 📊 Activity Distribution Chart

### **What It Shows**
24-hour bar chart showing when animals are most active.

### **How to Read It**
- **X-axis**: Hours of the day (0:00 - 23:00)
- **Y-axis**: Number of GPS readings
- **Bar height**: Activity level at that hour

### **Typical Patterns**

#### **Healthy Herd**
```
High activity: 6-10 AM (morning grazing)
Moderate: 11 AM - 2 PM (resting in shade)
High activity: 4-7 PM (evening grazing)
Low: 8 PM - 5 AM (sleeping)
```

#### **Heat Stress**
```
Low activity: 11 AM - 4 PM (too hot)
High activity: 5-9 PM (grazing when cooler)
Unusual: High activity at night (avoiding heat)
```

#### **Illness**
```
Low activity all day (lethargy)
No morning peak (not grazing)
Scattered readings (restless)
```

---

## 🎛️ Interactive Controls

### **Data Type Selector**
```
Activity (Location Density)  ← Default
Body Temperature
Heart Rate
Alert Locations
```
**Purpose**: Switch between different metrics

### **Time Range**
```
Last Hour      ← Real-time monitoring
Last 24 Hours  ← Daily patterns
Last 7 Days    ← Weekly trends
Last 30 Days   ← Monthly analysis
```
**Purpose**: Adjust historical depth

### **Intensity Slider** (0.1 - 1.0)
- **Low (0.1-0.4)**: Subtle colors, see small variations
- **Medium (0.5-0.7)**: Balanced view
- **High (0.8-1.0)**: Dramatic contrast, highlight extremes

### **Radius Slider** (10-50 pixels)
- **Small (10-20)**: Precise, pinpoint locations
- **Medium (25-35)**: Balanced, shows patterns
- **Large (40-50)**: Broad view, general trends

### **Refresh Button** 🔄
- Reloads data from database
- Updates all visualizations
- Use after new data arrives

### **Demo Data Button** 🔥
- Generates sample heatmap
- Useful for testing
- Shows 5 hotspot zones with realistic patterns

---

## 🔍 Real-World Use Cases

### **1. Water Management** 💧
**Problem**: Are animals drinking enough?

**Solution**:
1. Select "Activity" mode
2. Set time range to "Last 24 Hours"
3. Look for red hotspot near water source

**Interpretation**:
- ✅ **Red hotspot at water**: Animals drinking regularly
- ⚠️ **No hotspot**: Water source issue (broken, contaminated)
- 🔴 **Excessive hotspot**: Possible water shortage

---

### **2. Heat Stress Detection** 🌡️
**Problem**: Are animals suffering from heat?

**Solution**:
1. Select "Body Temperature" mode
2. Set time range to "Last Hour"
3. Look for red zones during hot hours (12-4 PM)

**Interpretation**:
- ✅ **Blue/green near shade**: Animals cooling properly
- ⚠️ **Yellow in open areas**: Mild heat stress
- 🔴 **Red clusters**: Critical heat stress, add shade

---

### **3. Predator Activity** 🐺
**Problem**: Are predators stressing the herd?

**Solution**:
1. Select "Heart Rate" mode
2. Set time range to "Last 7 Days"
3. Look for red spikes at unusual times/locations

**Interpretation**:
- ✅ **Consistent blue/green**: Calm herd
- ⚠️ **Yellow at night**: Possible predator presence
- 🔴 **Red cluster at fence**: Predator attempting entry

---

### **4. Grazing Optimization** 🌱
**Problem**: Are animals using all available pasture?

**Solution**:
1. Select "Activity" mode
2. Set time range to "Last 30 Days"
3. Check coverage percentage

**Interpretation**:
- ✅ **>80% coverage**: Good pasture utilization
- ⚠️ **50-80% coverage**: Some areas underused
- 🔴 **<50% coverage**: Poor rotation, overgrazing risk

---

### **5. Disease Outbreak Tracking** 🦠
**Problem**: Where did the illness start?

**Solution**:
1. Select "Alert Locations" mode
2. Set time range to "Last 7 Days"
3. Look for red cluster patterns

**Interpretation**:
- ✅ **Scattered alerts**: Individual cases
- ⚠️ **Cluster forming**: Possible contagion
- 🔴 **Dense red zone**: Outbreak epicenter (contaminated area)

---

## 🧮 Technical Details

### **Heatmap Algorithm**
```javascript
// Leaflet.heat plugin
L.heatLayer(dataPoints, {
    radius: 40,           // Size of heat blob
    blur: 20,             // Smoothing factor
    maxZoom: 18,          // Detail level
    max: 1.0,             // Maximum intensity
    minOpacity: 0.4,      // Minimum visibility
    gradient: {           // Color scale
        0.0: 'blue',
        0.25: 'cyan',
        0.5: 'lime',
        0.75: 'yellow',
        1.0: 'red'
    }
})
```

### **Data Point Format**
```javascript
[latitude, longitude, intensity]

Example:
[13.0827, 80.2707, 0.85]  // High intensity (red)
[13.0830, 80.2710, 0.35]  // Low intensity (blue)
```

### **Intensity Calculation**

#### **For Temperature**
```javascript
intensity = (temperature - 35) / 5
// 35°C → 0.0 (blue)
// 37.5°C → 0.5 (lime)
// 40°C → 1.0 (red)
```

#### **For Heart Rate**
```javascript
intensity = (heart_rate - 50) / 50
// 50 BPM → 0.0 (blue)
// 75 BPM → 0.5 (lime)
// 100 BPM → 1.0 (red)
```

---

## 📚 Best Practices

### **Daily Monitoring**
1. Check "Activity" heatmap every morning
2. Verify water source hotspot exists
3. Look for unusual patterns

### **Weekly Analysis**
1. Review "Temperature" heatmap for heat stress zones
2. Check "Heart Rate" for stress patterns
3. Analyze "Alert Locations" for problem areas

### **Monthly Planning**
1. Use 30-day "Activity" to plan pasture rotation
2. Identify underutilized areas
3. Plan infrastructure (shade, water) based on hotspots

---

## ✅ Summary

### **What the Heatmap Does**
- **Visualizes** animal location, health, and activity patterns
- **Identifies** hotspots, problem zones, and trends
- **Enables** data-driven pasture management decisions

### **Four Modes**
1. **Activity** - Where animals spend time
2. **Temperature** - Health by location
3. **Heart Rate** - Stress by location
4. **Alerts** - Problem locations

### **Key Benefits**
- 🎯 **Early Detection** - Spot issues before they escalate
- 💰 **Cost Savings** - Optimize resources (water, shade, feed)
- 🐄 **Animal Welfare** - Identify stress and illness quickly
- 📈 **Productivity** - Better grazing management

---

**Access**: http://localhost:8000/settings/heatmap  
**Last Updated**: 2025-12-19
