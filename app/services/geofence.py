"""
Geofencing Service for Smart Pastoralism
Monitors animal locations and triggers alerts when they leave designated areas
"""
import sqlite3
import math
from typing import List, Dict, Tuple, Optional
from app.config import settings


class GeofenceService:
    """Manage geofences and check if animals are within boundaries"""
    
    def __init__(self):
        self.db_path = settings.LORA_DB_PATH
        self._init_geofence_table()
    
    def _init_geofence_table(self):
        """Create geofence table if it doesn't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS geofences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    center_lat REAL NOT NULL,
                    center_lng REAL NOT NULL,
                    radius_meters REAL NOT NULL,
                    shape TEXT DEFAULT 'circle',
                    polygon_points TEXT,
                    enabled INTEGER DEFAULT 1,
                    notification_enabled INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS geofence_violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    geofence_id INTEGER,
                    device_id TEXT,
                    latitude REAL,
                    longitude REAL,
                    distance_from_fence REAL,
                    violated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    alert_sent INTEGER DEFAULT 0,
                    FOREIGN KEY (geofence_id) REFERENCES geofences (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            print("✅ Geofence tables initialized")
        except Exception as e:
            print(f"❌ Error initializing geofence tables: {e}")
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two GPS coordinates using Haversine formula
        Returns distance in meters
        """
        R = 6371000  # Earth's radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda/2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def is_inside_circular_fence(self, lat: float, lng: float, 
                                  center_lat: float, center_lng: float, 
                                  radius: float) -> bool:
        """Check if a point is inside a circular geofence"""
        distance = self.calculate_distance(lat, lng, center_lat, center_lng)
        return distance <= radius
    
    def create_geofence(self, name: str, center_lat: float, center_lng: float, 
                       radius_meters: float, notification_enabled: bool = True) -> int:
        """Create a new circular geofence"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO geofences (name, center_lat, center_lng, radius_meters, notification_enabled)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, center_lat, center_lng, radius_meters, 1 if notification_enabled else 0))
            
            geofence_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ Created geofence: {name} (ID: {geofence_id})")
            return geofence_id
        except Exception as e:
            print(f"❌ Error creating geofence: {e}")
            return -1
    
    def get_all_geofences(self, enabled_only: bool = True) -> List[Dict]:
        """Get all geofences"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM geofences"
            if enabled_only:
                query += " WHERE enabled = 1"
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query)
            geofences = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return geofences
        except Exception as e:
            print(f"❌ Error getting geofences: {e}")
            return []
    
    def check_animal_location(self, device_id: str, lat: float, lng: float) -> List[Dict]:
        """
        Check if an animal's location violates any geofences
        Returns list of violated geofences
        """
        violations = []
        geofences = self.get_all_geofences(enabled_only=True)
        
        for fence in geofences:
            if fence['shape'] == 'circle':
                inside = self.is_inside_circular_fence(
                    lat, lng, 
                    fence['center_lat'], 
                    fence['center_lng'], 
                    fence['radius_meters']
                )
                
                if not inside:
                    distance = self.calculate_distance(
                        lat, lng,
                        fence['center_lat'],
                        fence['center_lng']
                    ) - fence['radius_meters']
                    
                    violations.append({
                        'geofence_id': fence['id'],
                        'geofence_name': fence['name'],
                        'device_id': device_id,
                        'latitude': lat,
                        'longitude': lng,
                        'distance_outside': distance,
                        'notification_enabled': fence['notification_enabled']
                    })
        
        return violations
    
    def log_violation(self, violation: Dict) -> int:
        """Log a geofence violation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO geofence_violations 
                (geofence_id, device_id, latitude, longitude, distance_from_fence)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                violation['geofence_id'],
                violation['device_id'],
                violation['latitude'],
                violation['longitude'],
                violation['distance_outside']
            ))
            
            violation_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return violation_id
        except Exception as e:
            print(f"❌ Error logging violation: {e}")
            return -1
    
    def get_violations(self, device_id: Optional[str] = None, 
                      limit: int = 100) -> List[Dict]:
        """Get geofence violations"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    v.*,
                    g.name as geofence_name
                FROM geofence_violations v
                JOIN geofences g ON v.geofence_id = g.id
                WHERE 1=1
            '''
            params = []
            
            if device_id:
                query += " AND v.device_id = ?"
                params.append(device_id)
            
            query += " ORDER BY v.violated_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            violations = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return violations
        except Exception as e:
            print(f"❌ Error getting violations: {e}")
            return []
    
    def update_geofence(self, geofence_id: int, **kwargs) -> bool:
        """Update a geofence"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            allowed_fields = ['name', 'center_lat', 'center_lng', 'radius_meters', 
                            'enabled', 'notification_enabled']
            
            updates = []
            values = []
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    updates.append(f"{field} = ?")
                    values.append(value)
            
            if not updates:
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(geofence_id)
            
            query = f"UPDATE geofences SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"❌ Error updating geofence: {e}")
            return False
    
    def delete_geofence(self, geofence_id: int) -> bool:
        """Delete a geofence"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM geofences WHERE id = ?", (geofence_id,))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"❌ Error deleting geofence: {e}")
            return False


# Global instance
geofence_service = GeofenceService()
