# Milk Production Tracking Feature

## Overview

The Milk Production feature is a comprehensive module added to the Smart Pastoralism System that enables farmers to track, analyze, and optimize milk yield from their livestock. This feature integrates seamlessly with the existing health monitoring system to provide holistic livestock management.

## Features

### 1. **Production Recording**
- Record daily milk production for each animal
- Track multiple milking sessions (morning, afternoon, evening)
- Record quality metrics:
  - Yield in liters
  - Fat percentage
  - Protein percentage
  - Lactose percentage
  - Quality grade (A+, A, B, C)
- Add custom notes for each collection
- Automatic timestamp tracking

### 2. **Herd Management Dashboard**
- Real-time summary cards showing:
  - Today's total production
  - 7-day average yield
  - Number of active producing animals
  - Monthly cumulative total
- Production trend visualization (last 30 days)
- Top producers ranking table
- Quick access to record and analytics pages

### 3. **Analytics & Insights**
- Quality metrics analysis:
  - Average fat content
  - Average protein content
  - Most common quality grade
- Session comparison (morning vs evening production)
- Fat and protein content trends over time
- Historical data visualization with interactive charts

### 4. **Animal Profiles**
- Extended animal information:
  - Animal name and breed
  - Birth date and age calculation
  - Lactation number
  - Last calving date
  - Expected daily yield targets
  - Custom notes

### 5. **Individual Animal Tracking**
- Per-animal production history
- Daily totals and averages
- Session-by-session breakdown
- Production trends visualization
- Comparison with expected yields

## Technical Implementation

### Database Schema

#### 1. `milk_production` Table
```sql
CREATE TABLE milk_production (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    collection_date DATE NOT NULL,
    collection_time TIME NOT NULL,
    yield_liters REAL NOT NULL,
    fat_percentage REAL,
    protein_percentage REAL,
    lactose_percentage REAL,
    quality_grade TEXT,
    milking_session TEXT,
    notes TEXT,
    recorded_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(device_id, collection_date, collection_time)
)
```

#### 2. `animal_profiles` Table
```sql
CREATE TABLE animal_profiles (
    device_id TEXT PRIMARY KEY,
    animal_name TEXT,
    breed TEXT,
    birth_date DATE,
    lactation_number INTEGER,
    last_calving_date DATE,
    expected_yield_per_day REAL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### API Endpoints

#### Recording Milk Production
```http
POST /milk/api/record
Content-Type: application/json

{
    "device_id": "COW-001",
    "collection_date": "2026-01-21",
    "collection_time": "06:30:00",
    "yield_liters": 8.5,
    "fat_percentage": 3.5,
    "protein_percentage": 3.2,
    "quality_grade": "A",
    "milking_session": "morning",
    "notes": "Animal in good health"
}
```

#### Get Production Records
```http
GET /milk/api/production/{device_id}?days=30
```

#### Get Daily Total
```http
GET /milk/api/daily/{device_id}?date=2026-01-21
```

#### Get Production Trends
```http
GET /milk/api/trends/{device_id}?days=30
```

#### Get Herd Summary
```http
GET /milk/api/herd/summary?days=30
```

#### Update Animal Profile
```http
POST /milk/api/profile/{device_id}
Content-Type: application/json

{
    "animal_name": "Bessie",
    "breed": "Holstein",
    "birth_date": "2022-03-15",
    "lactation_number": 2,
    "expected_yield_per_day": 25.0
}
```

### File Structure

```
app/
├── services/
│   └── milk_production.py       # Core service with database operations
├── routes/
│   └── milk.py                  # API routes and page handlers
└── templates/
    └── milk/
        ├── dashboard.html       # Main milk production dashboard
        ├── record.html          # Production recording form
        ├── analytics.html       # Advanced analytics page
        └── animal_detail.html   # Individual animal milk profile
```

## Usage Guide

### Recording Production

1. Navigate to **Milk Production** → **Record Milk** in the sidebar
2. Select the animal from the dropdown
3. Choose collection date and time
4. Enter yield in liters
5. (Optional) Add quality metrics:
   - Fat percentage
   - Protein percentage
   - Lactose percentage
   - Quality grade
6. Select milking session (morning/afternoon/evening)
7. Add any notes or observations
8. Click "Record Production"

### Viewing Dashboard

1. Navigate to **Milk Production** → **Milk Dashboard**
2. View summary cards for:
   - Today's total production
   - Weekly averages
   - Active producers
   - Monthly totals
3. Analyze production trends in the chart
4. Review top producers table
5. Click on any animal to see detailed records

### Analyzing Data

1. Navigate to **Milk Production** → **Milk Analytics**
2. Review quality metrics (fat, protein, grade)
3. Compare production by time of day
4. Analyze fat and protein content trends
5. Export data for external analysis

### Managing Animal Profiles

1. Go to an individual animal's milk detail page
2. Click "Edit Profile"
3. Update information:
   - Animal name and breed
   - Birth date
   - Lactation number
   - Expected daily yield
4. Save changes

## Integration with Health Monitoring

The milk production feature integrates with the existing health monitoring system:

- **Cross-reference alerts**: Low milk yield can trigger health checks
- **Correlation analysis**: Compare production drops with health anomalies
- **Unified animal profiles**: Health and production data in one view
- **Holistic insights**: ML predictions considering both health and production

## Analytics Calculations

### Daily Total
```python
SUM(yield_liters) WHERE collection_date = today GROUP BY device_id
```

### 7-Day Average
```python
SUM(yield_liters) / 7 WHERE collection_date >= today - 7 days
```

### Top Producers
```python
SELECT device_id, SUM(yield_liters) as total
FROM milk_production
WHERE collection_date >= today - 30 days
GROUP BY device_id
ORDER BY total DESC
```

### Quality Averages
```python
SELECT 
    AVG(fat_percentage) as avg_fat,
    AVG(protein_percentage) as avg_protein
FROM milk_production
WHERE collection_date >= today - 30 days
```

## Best Practices

### Recording
- Record immediately after each milking session
- Measure quality metrics at least weekly
- Note any unusual observations
- Maintain consistent milking times

### Analysis
- Review trends weekly to spot issues early
- Compare individuals against herd averages
- Track quality metrics seasonally
- Set realistic yield targets per animal

### Data Quality
- Ensure accurate measurements
- Validate data entry for outliers
- Regular calibration of measuring equipment
- Consistent recording practices across team

## Future Enhancements

### Planned Features
1. **Feed correlation**: Link feed intake with milk yield
2. **Lactation curves**: Automated lactation stage tracking
3. **Breeding optimization**: Suggest optimal breeding times
4. **Price tracking**: Calculate revenue from production
5. **Mobile app**: Record production on-the-go
6. **Automated alerts**: Notify when yield drops significantly
7. **Export to dairy management software**: Integration options
8. **Bulk import**: CSV upload for historical data
9. **Comparison charts**: Compare current vs previous lactation
10. **Weather impact**: Analyze weather effects on production

### ML/AI Integration
- Predict expected daily yield based on patterns
- Anomaly detection for unusual yield drops
- Optimal milking time recommendations
- Feed optimization suggestions
- Health risk prediction from yield changes

## Troubleshooting

### Common Issues

**Q: Can't see my animals in the dropdown**
- Ensure animals have existing health monitoring records
- Check that device_id is correctly formatted
- Verify database connection

**Q: Duplicate record error**
- A record already exists for this animal, date, and time
- Edit the existing record or choose a different time

**Q: Charts not loading**
- Ensure you have recorded production data
- Check browser console for JavaScript errors
- Verify Chart.js library is loaded

**Q: Missing quality metrics**
- Quality metrics are optional
- They can be added later by editing records
- Analytics will show N/A for missing data

## Support & Feedback

For questions, feature requests, or bug reports related to the milk production feature, please:
1. Check this documentation first
2. Review the API documentation at `/docs`
3. Contact the system administrator
4. Submit feedback through the user profile page

---

**Last Updated**: January 21, 2026
**Version**: 1.0.0
**Module**: Milk Production Tracking
