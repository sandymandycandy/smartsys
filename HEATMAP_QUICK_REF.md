# 🔥 Heatmap Quick Reference

## What Is It?
A **color-coded map** showing where animals are and their health status.

## Color Scale
```
🔵 Blue → 🟦 Cyan → 🟩 Lime → 🟨 Yellow → 🔴 Red
(Low/Normal)                            (High/Critical)
```

## 4 Visualization Modes

### 1. 📍 Activity (Location Density)
**Shows**: Where animals spend time  
**Red = High traffic** (water, shade, favorite spots)  
**Blue = Low traffic** (avoided areas)

### 2. 🌡️ Body Temperature
**Shows**: Health by location  
**Red = Fever/Heat stress** (>39.5°C)  
**Blue = Normal** (37-39°C)

### 3. ❤️ Heart Rate
**Shows**: Stress levels by location  
**Red = High stress** (>85 BPM)  
**Blue = Calm** (50-75 BPM)

### 4. 🚨 Alert Locations
**Shows**: Where health problems occurred  
**Red = Critical alerts**  
**Yellow = Warnings**

## Quick Interpretation

### Good Signs ✅
- Red hotspot at water source
- Blue/green in shade areas
- Even distribution across pasture
- Morning/evening activity peaks

### Warning Signs ⚠️
- No hotspot at water
- Red zones in open sun (heat stress)
- Animals avoiding large areas
- Unusual nighttime activity

### Critical Issues 🔴
- Red temperature clusters (fever outbreak)
- Red HR zones (predator/stress)
- Dense alert clusters (disease hotspot)
- <50% pasture coverage

## Stats Explained

- **Data Points**: Total GPS readings
- **Animals Tracked**: Number of animals
- **Hotspot Zones**: High-activity areas (3-7 normal)
- **Coverage**: % of pasture used (>70% good)

## Access
http://localhost:8000/settings/heatmap

---
**Full Documentation**: `HEATMAP_EXPLAINED.md`
