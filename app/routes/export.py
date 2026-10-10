from fastapi import APIRouter, HTTPException, Query, Response
from typing import Optional
import sqlite3
import csv
import io
from datetime import datetime
from app.config import settings

router = APIRouter()

@router.get("/export/readings/csv")
def export_readings_csv(
    device_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=10000, le=50000)
):
    """
    Export livestock readings as CSV file
    
    Parameters:
    - device_id: Optional filter by specific animal
    - start_date: Optional start date (YYYY-MM-DD)
    - end_date: Optional end date (YYYY-MM-DD)
    - limit: Maximum number of records (default: 10000, max: 50000)
    """
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT 
                device_id,
                datetime(timestamp, 'unixepoch', 'localtime') as datetime,
                temperature,
                body_temperature,
                ambient_temperature,
                heart_rate,
                battery,
                latitude,
                longitude,
                humidity,
                motion_magnitude,
                rssi,
                received_time
            FROM livestock_readings
            WHERE 1=1
        """
        params = []
        
        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)
        
        if start_date:
            query += " AND DATE(received_time) >= DATE(?)"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(received_time) <= DATE(?)"
            params.append(end_date)
        
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            raise HTTPException(status_code=404, detail="No data found for the specified criteria")
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Device ID', 'Date/Time', 'Temperature (°C)', 'Body Temp (°C)', 
            'Ambient Temp (°C)', 'Heart Rate (BPM)', 'Battery (%)', 
            'Latitude', 'Longitude', 'Humidity (%)', 'Motion (g)', 'RSSI', 'Received Time'
        ])
        
        # Write data rows
        for row in rows:
            writer.writerow([
                row['device_id'],
                row['datetime'],
                row['temperature'],
                row['body_temperature'],
                row['ambient_temperature'],
                row['heart_rate'],
                row['battery'],
                row['latitude'],
                row['longitude'],
                row['humidity'],
                row['motion_magnitude'],
                row['rssi'],
                row['received_time']
            ])
        
        # Prepare response
        csv_content = output.getvalue()
        output.close()
        
        filename = f"livestock_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        if device_id:
            filename = f"{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/alerts/csv")
def export_alerts_csv(
    device_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    resolved: Optional[bool] = None
):
    """
    Export alerts as CSV file
    
    Parameters:
    - device_id: Optional filter by specific animal
    - start_date: Optional start date (YYYY-MM-DD)
    - end_date: Optional end date (YYYY-MM-DD)
    - resolved: Optional filter by resolution status (true/false)
    """
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT 
                id,
                device_id,
                alert_type,
                alert_message,
                temperature,
                heart_rate,
                battery,
                alert_time,
                resolved,
                resolved_time
            FROM alerts
            WHERE 1=1
        """
        params = []
        
        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)
        
        if start_date:
            query += " AND DATE(alert_time) >= DATE(?)"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(alert_time) <= DATE(?)"
            params.append(end_date)
        
        if resolved is not None:
            query += " AND resolved = ?"
            params.append(1 if resolved else 0)
        
        query += " ORDER BY alert_time DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            raise HTTPException(status_code=404, detail="No alerts found for the specified criteria")
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Alert ID', 'Device ID', 'Alert Type', 'Message', 
            'Temperature (°C)', 'Heart Rate (BPM)', 'Battery (%)',
            'Alert Time', 'Resolved', 'Resolution Time'
        ])
        
        # Write data rows
        for row in rows:
            writer.writerow([
                row['id'],
                row['device_id'],
                row['alert_type'],
                row['alert_message'],
                row['temperature'],
                row['heart_rate'],
                row['battery'],
                row['alert_time'],
                'Yes' if row['resolved'] else 'No',
                row['resolved_time'] or 'N/A'
            ])
        
        # Prepare response
        csv_content = output.getvalue()
        output.close()
        
        filename = f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/analytics/summary")
def export_analytics_summary():
    """
    Export a comprehensive analytics summary as CSV
    """
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get summary for each device
        cursor.execute("""
            SELECT 
                device_id,
                COUNT(*) as total_readings,
                ROUND(AVG(temperature), 2) as avg_temperature,
                ROUND(MIN(temperature), 2) as min_temperature,
                ROUND(MAX(temperature), 2) as max_temperature,
                ROUND(AVG(heart_rate), 2) as avg_heart_rate,
                ROUND(MIN(heart_rate), 2) as min_heart_rate,
                ROUND(MAX(heart_rate), 2) as max_heart_rate,
                ROUND(AVG(battery), 2) as avg_battery,
                MIN(battery) as lowest_battery,
                datetime(MIN(timestamp), 'unixepoch', 'localtime') as first_reading,
                datetime(MAX(timestamp), 'unixepoch', 'localtime') as last_reading,
                (SELECT COUNT(*) FROM alerts WHERE device_id = livestock_readings.device_id) as total_alerts,
                (SELECT COUNT(*) FROM alerts WHERE device_id = livestock_readings.device_id AND resolved = 0) as active_alerts
            FROM livestock_readings
            GROUP BY device_id
            ORDER BY device_id
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            raise HTTPException(status_code=404, detail="No data available for export")
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Device ID', 'Total Readings', 
            'Avg Temp (°C)', 'Min Temp (°C)', 'Max Temp (°C)',
            'Avg HR (BPM)', 'Min HR (BPM)', 'Max HR (BPM)',
            'Avg Battery (%)', 'Lowest Battery (%)',
            'First Reading', 'Last Reading',
            'Total Alerts', 'Active Alerts'
        ])
        
        # Write data
        for row in rows:
            writer.writerow([
                row['device_id'],
                row['total_readings'],
                row['avg_temperature'],
                row['min_temperature'],
                row['max_temperature'],
                row['avg_heart_rate'],
                row['min_heart_rate'],
                row['max_heart_rate'],
                row['avg_battery'],
                row['lowest_battery'],
                row['first_reading'],
                row['last_reading'],
                row['total_alerts'],
                row['active_alerts']
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        filename = f"analytics_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
