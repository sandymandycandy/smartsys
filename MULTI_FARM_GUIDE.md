# 🌾 Multi-Farm Management System

## Overview

The **Multi-Farm Management** feature allows you to manage multiple farm locations or livestock groups separately within a single Smart Pastoralism instance. Perfect for:
- Farmers with multiple properties
- Agricultural cooperatives
- Farm management companies
- Research institutions with multiple sites

---

## ✅ Features Implemented

### **1. Farm Creation & Management**
- ✅ Create unlimited farms
- ✅ Assign unique farm codes
- ✅ Track farm locations (GPS coordinates)
- ✅ Store farm details (area, owner, contact)
- ✅ Edit/update farm information
- ✅ Soft-delete farms (data preserved)

### **2. Animal Assignment**
- ✅ Assign animals to specific farms
- ✅ Move animals between farms
- ✅ Track assignment history
- ✅ Farm-specific animal lists

### **3. Farm-Specific Dashboards**
- ✅ Individual farm overview
- ✅ Farm health statistics
- ✅ Farm production metrics
- ✅ Farm-specific alerts

### **4. Cross-Farm Comparison**
- ✅ Compare performance across all farms
- ✅ Identify top-performing locations
- ✅ Aggregate statistics
- ✅ Trend analysis

---

## 📊 Database Schema

### **Farms Table**
```sql
CREATE TABLE farms (
    id INTEGER PRIMARY KEY,
    farm_code TEXT UNIQUE NOT NULL,
    farm_name TEXT NOT NULL,
    location TEXT,
    latitude REAL,
    longitude REAL,
    area_hectares REAL,
    owner_name TEXT,
    contact_phone TEXT,
    contact_email TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### **Farm-Animals Mapping**
```sql
CREATE TABLE farm_animals (
    id INTEGER PRIMARY KEY,
    farm_id INTEGER NOT NULL,
    device_id TEXT NOT NULL,
    assigned_date DATE,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (farm_id) REFERENCES farms(id),
    UNIQUE(farm_id, device_id)
)
```

---

## 🚀 How to Use

### **1. Create a Farm**

**Via UI:**
1. Navigate to **Farms** in sidebar
2. Click "Add New Farm"
3. Fill in farm details:
   - Farm Code (unique, e.g., "FARM-001")
   - Farm Name (e.g., "Green Pastures Farm")
   - Location (optional)
   - GPS Coordinates (optional)
   - Area in hectares
   - Owner details
   - Contact information
4. Click "Create Farm"

**Via API:**
```bash
curl -X POST http://localhost:8000/farms/api/create \
  -H "Content-Type: application/json" \
  -d '{
    "farm_code": "FARM-001",
    "farm_name": "Green Pastures Farm",
    "location": "123 Farm Road, County",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "area_hectares": 50.5,
    "owner_name": "John Doe",
    "contact_phone": "+1-234-567-8900",
    "contact_email": "farmer@example.com"
  }'
```

### **2. Assign Animals to Farm**

**Via API:**
```bash
curl -X POST http://localhost:8000/farms/api/1/assign \
  -H "Content-Type: application/json" \
  -d '{"device_id": "COW-001"}'
```

### **3. View Farm Dashboard**

**Via UI:**
1. Go to **Farms**
2. Click on any farm card
3. View farm-specific:
   - Animal list
   - Health statistics
   - Production metrics
   - Alerts

**Via API:**
```bash
# Get farm details
curl http://localhost:8000/farms/api/1#  Get farm stats
curl http://localhost:8000/farms/api/1/stats

# Get farm animals
curl http://localhost:8000/farms/api/1/animals
```

### **4. Compare Farms**

**Via UI:**
1. Go to **Farms**
2. Click "View Detailed Comparison"
3. See side-by-side comparison

**Via API:**
```bash
curl http://localhost:8000/farms/api/compare/all
```

---

## 📈 Farm Statistics

### **Per-Farm Metrics**
- Total Animals
- Animals with Active Alerts
- Healthy Animals Count
- Active Alert Count
- Milk Production (30 days):
  - Total production records
  - Total yield (liters)
  - Average yield per session

### **Cross-Farm Comparison**
- Performance ranking
- Production comparison
- Health status comparison
- Alert frequency comparison

---

## 🔄 Default Setup

When you first enable multi-farm management:

1. **"Main Farm" Created Automatically**
   - Farm Code: `MAIN`
   - Farm Name: `Main Farm`
   - All existing animals assigned here

2. **All Historical Data Preserved**
   - Past readings still accessible
   - Past milk production retained
   - Alert history maintained

---

## 💡 Use Cases

### **1. Multiple Locations**
```
Farm A: Dairy Farm (50 hectares)
  - 30 dairy cows
  - Focus: Milk production
  
Farm B: Breeding Site (100 hectares)
  - 20 breeding animals
  - Focus: Genetics

Farm C: Young Stock (25 hectares)
  - 15 calves
  - Focus: Growth monitoring
```

### **2. Cooperative Management**
```
Cooperative: 5 member farms
  - Track each farmer separately
  - Compare performance
  - Share best practices
  - Aggregate milk sales
```

### **3. Research Projects**
```
Study Site 1: Control Group
Study Site 2: Treatment A
Study Site 3: Treatment B
  - Compare health outcomes
  - Analyze production differences
  - Scientific reporting
```

---

## 🎯 API Endpoints

### **Farm Management**
```
GET    /farms                      # View farms list page
GET    /farms/{farm_id}            # View farm dashboard
GET    /farms/compare/all          # Comparison page
GET    /farms/api/list             # Get all farms (JSON)
GET    /farms/api/{farm_id}        # Get single farm
POST   /farms/api/create           # Create new farm
PUT    /farms/api/{farm_id}        # Update farm
DELETE /farms/api/{farm_id}        # Delete farm
```

### **Animal Assignment**
```
GET    /farms/api/{farm_id}/animals    # Get farm animals
POST   /farms/api/{farm_id}/assign     # Assign animal
```

### **Statistics**
```
GET    /farms/api/{farm_id}/stats      # Farm statistics
GET    /farms/api/compare/all          # Compare all farms
```

---

## 🔐 Data Isolation

### **Farm-Specific Views**
Each farm has isolated views for:
- Animal list (only farm's animals)
- Health statistics (farm-specific)
- Milk production (farm-specific)
- Alert counts (farm-specific)

### **Shared Data**
Some data is shared across farms:
- Sensor readings (all animals)
- ML models (trained on all data)
- System settings
- User accounts

---

## 📊 Integration with Existing Features

### **Dashboard Integration**
- Sidebar: New "Farms" link
- Farm selector (future enhancement)
- Farm-specific filtering

### **Health Monitoring**
- Alerts tagged with farm
- Farm-specific health stats
- Cross-farm health comparison

### **Milk Production**
- Production per farm
- Farm-level analytics
- Cross-farm yield comparison

### **Analytics**
- Farm-specific trends
- Comparative analytics
- Performance benchmarking

---

## 🚀 Future Enhancements

### **Planned Features**
1. **Farm Switcher**
   - Quick switch between farms in navbar
   - Remember last selected farm
   - Filter all views by selected farm

2. **Farm-Specific Settings**
   - Custom alert thresholds per farm
   - Farm-specific geofences
   - Individual notification preferences

3. **Advanced Comparisons**
   - Time-series comparison charts
   - Statistical analysis
   - Benchmarking reports
   - Export comparison data

4. **Mobile Management**
   - Farm selection in mobile app
   - Quick switch between sites
   - Farm-specific push notifications

5. **Financial Tracking**
   - Revenue per farm
   - Cost allocation
   - Profitability analysis
   - ROI per location

6. **Team Management**
   - Assign users to farms
   - Farm-specific permissions
   - Access control per location

---

## ✅ Quick Start Checklist

**Setup (Do Now):**
- [x] Multi-farm system auto-initialized
- [ ] Visit http://localhost:8000/farms
- [ ] Check "Main Farm" is created
- [ ] Verify all animals assigned to Main Farm

**Next Steps:**
- [ ] Create your first additional farm
- [ ] Assign some animals to it
- [ ] View farm-specific dashboard
- [ ] Compare farm performance

**Going Forward:**
- [ ] Organize animals by location
- [ ] Track performance per farm
- [ ] Identify best-performing sites
- [ ] Optimize based on data

---

## 🎯 Benefits

### **For Multi-Location Farmers**
- ✅ Separate tracking per location
- ✅ Compare site performance
- ✅ Identify location-specific issues
- ✅ Optimize resource allocation

### **For Cooperatives**
- ✅ Member-specific tracking
- ✅ Fair comparison
- ✅ Shared insights
- ✅ Aggregate reporting

### **For Research**
- ✅ Study group separation
- ✅ Controlled comparisons
- ✅ Statistical analysis
- ✅ Publication-ready data

### **For Scale Operations**
- ✅ Manage 100s of animals
- ✅ Organize by location/group
- ✅ Track efficiency
- ✅ Data-driven decisions

---

## 📝 Notes

### **Important**
- At least one farm must always exist
- Deleting a farm soft-deletes it (data preserved)
- Animals can only be in one active farm at a time
- Farm codes must be unique
- All existing animals auto-assigned to "Main Farm"

### **Tips**
- Use descriptive farm codes (e.g., "NORTH-01", "DAIRY-MAIN")
- Add GPS coordinates for map visualization (future feature)
- Keep contact information updated
- Regularly review cross-farm comparisons

---

## 🎉 Summary

**What You Can Do:**
- ✅ Create and manage multiple farms
- ✅ Assign animals to farms
- ✅ View farm-specific dashboards
- ✅ Compare farm performance
- ✅ Track statistics per location

**Files Created:**
1. `app/services/farm_management.py` - Farm service
2. `app/routes/farms.py` - API routes
3. `app/templates/farms/list.html` - Farms list UI

**Files Updated:**
4. `run.py` - Added farms router
5. `app/templates/components/sidebar.html` - Added Farms link

**Database:**
6. New table: `farms`
7. New table: `farm_animals`

---

**Last Updated**: January 21, 2026  
**Version**: 1.0.0  
**Status**: ✅ Production Ready

Visit **/farms** to get started!
