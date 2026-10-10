import sqlite3
import threading
import time
from datetime import datetime, timedelta
from app.config import settings
from typing import Dict, List, Optional

# Import notification and geofencing services
try:
    from app.services.notifications import notification_service
    NOTIFICATIONS_ENABLED = True
except ImportError:
    NOTIFICATIONS_ENABLED = False
    print("⚠️ Notification service not available")

try:
    from app.services.geofence import geofence_service
    GEOFENCING_ENABLED = True
except ImportError:
    GEOFENCING_ENABLED = False
    print("⚠️ Geofencing service not available")

try:
    from app.services.ml_disease_detector import ml_detector
    ML_ENABLED = ml_detector is not None
except ImportError:
    ML_ENABLED = False
    ml_detector = None
    print("⚠️ ML disease detector not available")

class LoRaMonitor:
    """Monitor SQLite database for new packets from LoRa receiver"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.LORA_DB_PATH
        self.last_check_id = 0
        self.running = False
        self.thread = None
        self._load_last_id()
        
    def _load_last_id(self):
        """Get the latest ID from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(id) FROM livestock_readings')
            result = cursor.fetchone()
            self.last_check_id = result[0] if result[0] else 0
            conn.close()
            print(f"📊 Starting from reading ID: {self.last_check_id}")
        except Exception as e:
            print(f"⚠️  Could not load last ID: {e}")
            self.last_check_id = 0
    
    def start_monitoring(self):
        """Run in background thread"""
        if self.running:
            print("⚠️  Monitor already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("✅ LoRa monitoring thread started")
        
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("🛑 LoRa monitoring stopped")
        
    def _monitor_loop(self):
        """Check database every N seconds for new data"""
        while self.running:
            try:
                new_data = self._check_new_readings()
                if new_data:
                    for reading in new_data:
                        self._process_reading(reading)
            except Exception as e:
                print(f"❌ Error in monitor loop: {e}")
            
            time.sleep(settings.LORA_CHECK_INTERVAL)
    
    def _check_new_readings(self) -> List[Dict]:
        """Get new readings since last check"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM livestock_readings 
                WHERE id > ? 
                ORDER BY id ASC
            ''', (self.last_check_id,))
            
            rows = cursor.fetchall()
            
            if rows:
                self.last_check_id = rows[-1]['id']
                print(f"📦 Found {len(rows)} new readings (up to ID: {self.last_check_id})")
            
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Error checking readings: {e}")
            return []
    
    def _process_reading(self, reading: Dict):
        """Process new reading and broadcast via WebSocket"""
        try:
            # Check for anomalies (rule-based)
            anomalies = self._detect_anomalies(reading)
            
            # ML-based predictions
            ml_anomaly = None
            ml_disease = None
            ml_forecast = None
            
            if ML_ENABLED and ml_detector:
                # 1. Anomaly Detection
                ml_anomaly = ml_detector.predict_anomaly(reading)
                
                # 2. Disease Prediction
                ml_disease = ml_detector.predict_disease(reading)
                
                # 3. Health Forecast (every 10th reading to reduce load)
                if reading.get('id', 0) % 10 == 0:
                    ml_forecast = ml_detector.forecast_health(
                        reading['device_id'],
                        hours_ahead=24
                    )
                
                # Add ML anomaly to alerts if confident
                if ml_anomaly and ml_anomaly.get('is_anomaly') and ml_anomaly.get('confidence', 0) > 70:
                    anomalies.append(f"ML_ANOMALY: {ml_anomaly.get('explanation')}")
                
                # Create alert for predicted diseases
                if ml_disease and ml_disease.get('disease') != 'healthy' and ml_disease.get('probability', 0) > 0.7:
                    anomalies.append(f"ML_PREDICTION: {ml_disease.get('disease').upper()} ({ml_disease.get('probability')*100:.0f}% confidence)")
            
            # Check geofencing
            geofence_violations = self._check_geofencing(reading)
            
            # Broadcast to connected clients
            from app.websocket.handlers import broadcast_update
            broadcast_update({
                'type': 'new_reading',
                'device_id': reading['device_id'],
                'data': reading,
                'anomalies': anomalies,
                'geofence_violations': geofence_violations,
                'ml_predictions': {
                    'anomaly': ml_anomaly,
                    'disease': ml_disease,
                    'forecast': ml_forecast
                } if ML_ENABLED else None,
                'timestamp': datetime.now().isoformat()
            })
            
            # Create alerts if needed
            if anomalies:
                self._create_alerts(reading, anomalies)
            
            # Handle geofence violations
            if geofence_violations:
                self._handle_geofence_violations(reading, geofence_violations)
                
        except Exception as e:
            print(f"❌ Error processing reading: {e}")
    
    def _check_geofencing(self, reading: Dict) -> List[Dict]:
        """Check if the animal has violated any geofence"""
        if not GEOFENCING_ENABLED:
            return []
        
        try:
            lat = reading.get('latitude', 0)
            lng = reading.get('longitude', 0)
            
            if lat == 0 or lng == 0:
                return []  # No GPS data
            
            violations = geofence_service.check_animal_location(
                reading['device_id'],
                lat,
                lng
            )
            
            if violations:
                print(f"🚨 Geofence violation: {reading['device_id']} - {len(violations)} violations")
            
            return violations
            
        except Exception as e:
            print(f"❌ Error checking geofence: {e}")
            return []
    
    def _handle_geofence_violations(self, reading: Dict, violations: List[Dict]):
        """Handle geofence violations - create alerts and send notifications"""
        try:
            for violation in violations:
                # Log violation
                geofence_service.log_violation(violation)
                
                # Create alert
                alert_data = {
                    'alert_type': 'GEOFENCE_VIOLATION',
                    'device_id': reading['device_id'],
                    'alert_message': f"Animal left {violation.get('geofence_name', 'safe zone')} ({violation.get('distance_outside', 0):.0f}m outside)",
                    'temperature': reading.get('temperature'),
                    'heart_rate': reading.get('heart_rate'),
                    'battery': reading.get('battery'),
                    'alert_time': datetime.now().isoformat()
                }
                
                # Send notification
                if NOTIFICATIONS_ENABLED and violation.get('notification_enabled'):
                    notification_service.send_alert_notification(alert_data)
                
                # Broadcast via WebSocket
                from app.websocket.handlers import broadcast_update
                broadcast_update({
                    'type': 'geofence_violation',
                    'device_id': reading['device_id'],
                    'violation': violation,
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e:
            print(f"❌ Error handling geofence violation: {e}")
    
    def _detect_anomalies(self, reading: Dict) -> List[str]:
        """Detect health anomalies in the reading"""
        anomalies = []
        
        # Temperature checks
        if reading.get('temperature'):
            temp = reading['temperature']
            if temp >= settings.TEMP_CRITICAL:
                anomalies.append(f"CRITICAL: High temperature ({temp}°C)")
            elif temp >= settings.TEMP_WARNING:
                anomalies.append(f"WARNING: Elevated temperature ({temp}°C)")
        
        # Heart rate checks
        if reading.get('heart_rate'):
            hr = reading['heart_rate']
            if hr >= settings.HR_CRITICAL:
                anomalies.append(f"CRITICAL: High heart rate ({hr} BPM)")
            elif hr >= settings.HR_WARNING:
                anomalies.append(f"WARNING: Elevated heart rate ({hr} BPM)")
        
        # Battery checks
        if reading.get('battery'):
            battery = reading['battery']
            if battery <= settings.BATTERY_CRITICAL:
                anomalies.append(f"CRITICAL: Low battery ({battery}%)")
            elif battery <= settings.BATTERY_LOW:
                anomalies.append(f"WARNING: Battery low ({battery}%)")
        
        # Location check (geofencing - placeholder)
        if reading.get('latitude') == 0 and reading.get('longitude') == 0:
            anomalies.append("WARNING: No GPS signal")
        
        return anomalies
    
    def _create_alerts(self, reading: Dict, anomalies: List[str]):
        """Create alert entries in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create alerts table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    alert_message TEXT NOT NULL,
                    alert_time TEXT NOT NULL,
                    resolved INTEGER DEFAULT 0,
                    temperature REAL,
                    heart_rate INTEGER,
                    battery INTEGER
                )
            ''')
            
            # Migrate existing table if needed (add missing columns)
            cursor.execute("PRAGMA table_info(alerts)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'temperature' not in columns:
                print("🔄 Migrating alerts table: adding temperature column")
                cursor.execute("ALTER TABLE alerts ADD COLUMN temperature REAL")
            
            if 'heart_rate' not in columns:
                print("🔄 Migrating alerts table: adding heart_rate column")
                cursor.execute("ALTER TABLE alerts ADD COLUMN heart_rate INTEGER")
            
            if 'battery' not in columns:
                print("🔄 Migrating alerts table: adding battery column")
                cursor.execute("ALTER TABLE alerts ADD COLUMN battery INTEGER")
            
            conn.commit()
            
            # Insert alerts
            # Insert or update alerts
            for anomaly in anomalies:
                alert_type = "CRITICAL" if "CRITICAL" in anomaly else "WARNING"
                
                # Check duplicates (Resolved or Unresolved)
                cursor.execute('SELECT id, resolved, alert_time FROM alerts WHERE device_id=? AND alert_type=? ORDER BY id DESC LIMIT 1',
                             (reading['device_id'], alert_type))
                existing = cursor.fetchone()
                
                if existing:
                    eid, resolved, etime = existing
                    if resolved == 0:
                        # Update existing
                        cursor.execute('UPDATE alerts SET alert_time=?, alert_message=?, temperature=?, heart_rate=?, battery=? WHERE id=?',
                                     (datetime.now().isoformat(), anomaly, reading.get('temperature'), reading.get('heart_rate'), reading.get('battery'), eid))
                    else:
                        # Resolved: Check cooldown
                        try:
                            last_time = datetime.fromisoformat(etime)
                            if datetime.now() - last_time < timedelta(minutes=60):
                                print(f"Skipping snoozed alert {alert_type}")
                                continue
                        except ValueError:
                            pass
                        
                        # Re-create
                        cursor.execute('''
                            INSERT INTO alerts (device_id, alert_type, alert_message, alert_time, 
                                              temperature, heart_rate, battery)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            reading['device_id'],
                            alert_type,
                            anomaly,
                            datetime.now().isoformat(),
                            reading.get('temperature'),
                            reading.get('heart_rate'),
                            reading.get('battery')
                        ))
                else:
                    # Insert new
                    cursor.execute('''
                        INSERT INTO alerts (device_id, alert_type, alert_message, alert_time, 
                                          temperature, heart_rate, battery)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        reading['device_id'],
                        alert_type,
                        anomaly,
                        datetime.now().isoformat(),
                        reading.get('temperature'),
                        reading.get('heart_rate'),
                        reading.get('battery')
                    ))
            
            conn.commit()
            conn.close()
            
            # Broadcast alert to connected clients
            from app.websocket.handlers import broadcast_update
            broadcast_update({
                'type': 'new_alert',
                'device_id': reading['device_id'],
                'anomalies': anomalies,
                'timestamp': datetime.now().isoformat()
            })
            
            # Send notifications for critical alerts
            if NOTIFICATIONS_ENABLED:
                for anomaly in anomalies:
                    if 'CRITICAL' in anomaly:
                        alert_data = {
                            'alert_type': 'TEMP_CRITICAL' if 'temperature' in anomaly.lower() else 
                                         'HR_CRITICAL' if 'heart' in anomaly.lower() else 
                                         'BATTERY_CRITICAL' if 'battery' in anomaly.lower() else 'CRITICAL',
                            'device_id': reading['device_id'],
                            'alert_message': anomaly,
                            'temperature': reading.get('temperature'),
                            'heart_rate': reading.get('heart_rate'),
                            'battery': reading.get('battery'),
                            'alert_time': datetime.now().isoformat()
                        }
                        notification_service.send_alert_notification(alert_data)
            
        except Exception as e:
            print(f"❌ Error creating alerts: {e}")


def get_herd_stats() -> Dict:
    """Get overall herd statistics"""
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get total animals (unique devices)
        cursor.execute('SELECT COUNT(DISTINCT device_id) FROM livestock_readings')
        total = cursor.fetchone()[0]
        
        # Get count of animals with unresolved alerts (any type)
        cursor.execute('''
            SELECT COUNT(DISTINCT device_id) as count
            FROM alerts 
            WHERE resolved = 0
        ''')
        animals_with_alerts = cursor.fetchone()[0] or 0
        
        # Get alert counts by type
        cursor.execute('''
            SELECT COUNT(DISTINCT device_id) as count, alert_type 
            FROM alerts 
            WHERE resolved = 0 
            GROUP BY alert_type
        ''')
        alerts = {row['alert_type']: row['count'] for row in cursor.fetchall()}
        
        critical = alerts.get('CRITICAL', 0)
        warnings = alerts.get('WARNING', 0)
        
        # Healthy = total animals - animals with any unresolved alerts
        healthy = total - animals_with_alerts if total > 0 else 0
        
        # Get average values from latest readings
        cursor.execute('''
            SELECT AVG(l1.temperature) as avg_temp, AVG(l1.heart_rate) as avg_hr
            FROM livestock_readings l1
            INNER JOIN (
                SELECT device_id, MAX(id) as max_id
                FROM livestock_readings
                GROUP BY device_id
            ) l2 ON l1.device_id = l2.device_id AND l1.id = l2.max_id
        ''')
        averages = cursor.fetchone()
        
        # Battery status
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN battery > 50 THEN 1 ELSE 0 END) as good,
                SUM(CASE WHEN battery BETWEEN 20 AND 50 THEN 1 ELSE 0 END) as low,
                SUM(CASE WHEN battery < 20 THEN 1 ELSE 0 END) as critical
            FROM (
                SELECT device_id, battery, MAX(id) as max_id
                FROM livestock_readings
                GROUP BY device_id
            )
        ''')
        battery = cursor.fetchone()
        
        conn.close()
        
        return {
            'total': total,
            'healthy': healthy,
            'warnings': warnings,
            'critical': critical,
            'avg_temp': averages['avg_temp'] or 0,
            'avg_hr': averages['avg_hr'] or 0,
            'battery_good': battery['good'] or 0,
            'battery_low': battery['low'] or 0,
            'battery_critical': battery['critical'] or 0
        }
        
    except Exception as e:
        print(f"❌ Error getting herd stats: {e}")
        return {
            'total': 0, 'healthy': 0, 'warnings': 0, 'critical': 0,
            'avg_temp': 0, 'avg_hr': 0,
            'battery_good': 0, 'battery_low': 0, 'battery_critical': 0
        }
