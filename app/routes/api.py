from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import sqlite3
from datetime import datetime, timedelta
from app.config import settings
from pydantic import BaseModel

router = APIRouter()

# Data models for LoRa ingestion
class LoRaReading(BaseModel):
    """Single LoRa reading from livestock device"""
    device_id: str
    timestamp: int
    temperature: Optional[float] = None  # Legacy (usually body temp)
    ambient_temperature: Optional[float] = None
    body_temperature: Optional[float] = None
    heart_rate: Optional[int] = None
    battery: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    humidity: Optional[float] = None
    accel_x: Optional[float] = None
    accel_y: Optional[float] = None
    accel_z: Optional[float] = None
    gyro_x: Optional[float] = None
    gyro_y: Optional[float] = None
    gyro_z: Optional[float] = None
    rotation_speed: Optional[float] = None
    motion_magnitude: Optional[float] = None
    rssi: Optional[int] = None

@router.post("/ingest/reading")
def ingest_single_reading(reading: LoRaReading):
    """
    Ingest a single LoRa reading from livestock device
    
    This endpoint accepts data from your LoRa receiver/ESP32
    and stores it in the livestock_readings table.
    
    Example:
    POST /api/ingest/reading
    {
        "device_id": "COW-001",
        "timestamp": 1701234567,
        "temperature": 38.5,
        "heart_rate": 72,
        "battery": 85,
        "latitude": 0.0,
        "longitude": 0.0
    }
    """
    try:
        from app.services.lora_ingester import insert_lora_reading
        
        reading_dict = reading.dict()
        success = insert_lora_reading(reading_dict)
        
        if success:
            # Broadcast via WebSocket if monitoring is active
            from app.websocket.handlers import broadcast_update
            broadcast_update({
                'type': 'new_reading',
                'device_id': reading.device_id,
                'data': reading_dict
            })
            
            return {
                "status": "success",
                "message": f"Reading ingested for {reading.device_id}",
                "device_id": reading.device_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to insert reading")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest/batch")
def ingest_batch_readings(readings: List[LoRaReading]):
    """
    Ingest multiple LoRa readings at once
    
    This endpoint accepts batch data from your LoRa receiver
    for bulk ingestion.
    
    Example:
    POST /api/ingest/batch
    [
        {
            "device_id": "COW-001",
            "timestamp": 1701234567,
            "temperature": 38.5,
            "heart_rate": 72,
            "battery": 85
        },
        {
            "device_id": "COW-002",
            "timestamp": 1701234568,
            "temperature": 39.2,
            "heart_rate": 68,
            "battery": 92
        }
    ]
    """
    try:
        from app.services.lora_ingester import insert_lora_readings
        
        readings_list = [r.dict() for r in readings]
        count = insert_lora_readings(readings_list)
        
        # Broadcast all readings via WebSocket
        from app.websocket.handlers import broadcast_update
        for reading_dict in readings_list:
            broadcast_update({
                'type': 'new_reading',
                'device_id': reading_dict.get('device_id'),
                'data': reading_dict
            })
        
        return {
            "status": "success",
            "message": f"Ingested {count}/{len(readings)} readings",
            "count": count,
            "total": len(readings)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/readings")
def get_readings(
    device_id: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """Get livestock readings with filters"""
    
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM livestock_readings WHERE 1=1"
        params = []
        
        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)
        
        if start_time:
            query += " AND received_time >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND received_time <= ?"
            params.append(end_time)
        
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        readings = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {"count": len(readings), "data": readings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/animals/summary")
def get_animals_summary():
    """Get summary of all animals"""
    
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                device_id,
                COUNT(*) as reading_count,
                AVG(temperature) as avg_temp,
                AVG(heart_rate) as avg_hr,
                AVG(battery) as avg_battery,
                MAX(received_time) as last_seen
            FROM livestock_readings
            GROUP BY device_id
        ''')
        
        summary = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {"animals": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts/active")
def get_active_alerts():
    """Get unresolved alerts"""
    
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM alerts 
            WHERE resolved = 0 
            ORDER BY alert_time DESC
        ''')
        
        alerts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {"count": len(alerts), "alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int):
    """Mark alert as resolved"""
    
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH, timeout=10.0)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE alerts 
            SET resolved = 1 
            WHERE id = ?
        ''', (alert_id,))
        
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Alert not found")
        
        conn.close()
        return {"message": "Alert resolved", "alert_id": alert_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/temperature")
def get_temperature_analytics(device_id: Optional[str] = None, days: int = 7):
    """Get temperature trends"""
    
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = f'''
            SELECT 
                strftime('%Y-%m-%d %H:00', received_time) as hour,
                AVG(temperature) as avg_temp,
                MIN(temperature) as min_temp,
                MAX(temperature) as max_temp,
                COUNT(*) as reading_count
            FROM livestock_readings
            WHERE datetime(received_time) > datetime('now', '-{days} days')
        '''
        
        if device_id:
            query += " AND device_id = ?"
            cursor.execute(query + " GROUP BY hour ORDER BY hour", (device_id,))
        else:
            cursor.execute(query + " GROUP BY hour ORDER BY hour")
        
        data = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {"period_days": days, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/heartrate")
def get_heartrate_analytics(device_id: Optional[str] = None, days: int = 7):
    """Get heart rate distribution analytics"""
    
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get heart rate distribution in ranges
        query = f'''
            SELECT 
                CASE 
                    WHEN heart_rate < 50 THEN 'Low (<50)'
                    WHEN heart_rate BETWEEN 50 AND 65 THEN 'Normal (50-65)'
                    WHEN heart_rate BETWEEN 66 AND 75 THEN 'Elevated (66-75)'
                    WHEN heart_rate BETWEEN 76 AND 85 THEN 'High (76-85)'
                    ELSE 'Critical (>85)'
                END as range,
                COUNT(*) as count
            FROM livestock_readings
            WHERE datetime(received_time) > datetime('now', '-{days} days')
            AND heart_rate IS NOT NULL
        '''
        
        if device_id:
            query += " AND device_id = ?"
            cursor.execute(query + " GROUP BY range ORDER BY range", (device_id,))
        else:
            cursor.execute(query + " GROUP BY range ORDER BY range")
        
        distribution = [dict(row) for row in cursor.fetchall()]
        
        # Get average heart rate over time
        time_query = f'''
            SELECT 
                strftime('%Y-%m-%d %H:00', received_time) as hour,
                AVG(heart_rate) as avg_hr,
                MIN(heart_rate) as min_hr,
                MAX(heart_rate) as max_hr,
                COUNT(*) as reading_count
            FROM livestock_readings
            WHERE datetime(received_time) > datetime('now', '-{days} days')
            AND heart_rate IS NOT NULL
        '''
        
        if device_id:
            time_query += " AND device_id = ?"
            cursor.execute(time_query + " GROUP BY hour ORDER BY hour", (device_id,))
        else:
            cursor.execute(time_query + " GROUP BY hour ORDER BY hour")
        
        trends = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {"period_days": days, "distribution": distribution, "trends": trends}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/alerts")
def get_alerts_analytics(days: int = 30):
    """Get alert frequency analytics"""
    
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Alerts by type
        cursor.execute(f'''
            SELECT 
                alert_type,
                COUNT(*) as count
            FROM alerts
            WHERE datetime(alert_time) > datetime('now', '-{days} days')
            GROUP BY alert_type
            ORDER BY count DESC
        ''')
        by_type = [dict(row) for row in cursor.fetchall()]
        
        # Alerts by day
        cursor.execute(f'''
            SELECT 
                strftime('%Y-%m-%d', alert_time) as date,
                COUNT(*) as count,
                SUM(CASE WHEN resolved = 1 THEN 1 ELSE 0 END) as resolved,
                SUM(CASE WHEN resolved = 0 THEN 1 ELSE 0 END) as active
            FROM alerts
            WHERE datetime(alert_time) > datetime('now', '-{days} days')
            GROUP BY date
            ORDER BY date
        ''')
        by_day = [dict(row) for row in cursor.fetchall()]
        
        # Top devices with most alerts
        cursor.execute(f'''
            SELECT 
                device_id,
                COUNT(*) as alert_count,
                SUM(CASE WHEN 'CRITICAL' IN (alert_type) THEN 1 ELSE 0 END) as critical_count
            FROM alerts
            WHERE datetime(alert_time) > datetime('now', '-{days} days')
            GROUP BY device_id
            ORDER BY alert_count DESC
            LIMIT 10
        ''')
        by_device = [dict(row) for row in cursor.fetchall()]
        
        # Overall stats
        cursor.execute(f'''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN resolved = 0 THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN resolved = 1 THEN 1 ELSE 0 END) as resolved
            FROM alerts
            WHERE datetime(alert_time) > datetime('now', '-{days} days')
        ''')
        summary = dict(cursor.fetchone())
        
        conn.close()
        
        return {
            "period_days": days,
            "summary": summary,
            "by_type": by_type,
            "by_day": by_day,
            "by_device": by_device
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/map/locations")
def get_current_locations():
    """Get current location of all animals"""
    
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                l1.device_id,
                l1.latitude,
                l1.longitude,
                l1.temperature,
                l1.heart_rate,
                l1.battery,
                l1.motion_magnitude,
                l1.received_time,
                (SELECT COUNT(*) FROM alerts WHERE device_id = l1.device_id AND resolved = 0) as alert_count
            FROM livestock_readings l1
            INNER JOIN (
                SELECT device_id, MAX(id) as max_id
                FROM livestock_readings
                WHERE latitude != 0 AND longitude != 0
                GROUP BY device_id
            ) l2 ON l1.id = l2.max_id
        ''')
        
        locations = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Add status based on health parameters
        for loc in locations:
            status = "healthy"
            if loc['alert_count'] > 0:
                if loc.get('temperature', 0) > settings.TEMP_CRITICAL or loc.get('heart_rate', 0) > settings.HR_CRITICAL:
                    status = "critical"
                else:
                    status = "warning"
            elif loc.get('temperature', 0) > settings.TEMP_WARNING or loc.get('heart_rate', 0) > settings.HR_WARNING:
                status = "warning"
            loc['status'] = status
        
        return {"locations": locations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/animals/list")
def get_animals_list():
    """Get simple list of all animals for dropdowns"""
    
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT device_id
            FROM livestock_readings
            ORDER BY device_id
        ''')
        
        animals = [{"device_id": row['device_id']} for row in cursor.fetchall()]
        conn.close()
        
        return {"animals": animals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
def get_stats():
    """Get overall system statistics"""
    from app.services.lora_service import get_herd_stats
    return get_herd_stats()
