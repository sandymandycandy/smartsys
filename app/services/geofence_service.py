"""
Geofencing Service for livestock boundary monitoring
"""
import sqlite3
import json
import math
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple

try:
    from app.config import settings
except:
    from config import settings

# Get database path
DB_PATH = os.path.join(os.path.dirname(settings.LORA_DB_PATH), "geofences.db")

def init_geofence_db():
    """Initialize the geofences database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Geofences table - stores polygon boundaries
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geofences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            polygon TEXT NOT NULL,
            color TEXT DEFAULT '#3B82F6',
            alert_on_exit BOOLEAN DEFAULT 1,
            alert_on_enter BOOLEAN DEFAULT 0,
            active BOOLEAN DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Geofence violations log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geofence_violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            geofence_id INTEGER NOT NULL,
            device_id TEXT NOT NULL,
            violation_type TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            alert_sent BOOLEAN DEFAULT 0,
            resolved BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (geofence_id) REFERENCES geofences (id)
        )
    ''')
    
    # Device last known zone status
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_zone_status (
            device_id TEXT PRIMARY KEY,
            geofence_id INTEGER,
            is_inside BOOLEAN,
            last_check TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (geofence_id) REFERENCES geofences (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on import
init_geofence_db()


def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """
    Check if a point is inside a polygon using ray casting algorithm.
    Point format: (latitude, longitude)
    Polygon format: [(lat1, lng1), (lat2, lng2), ...]
    """
    x, y = point
    n = len(polygon)
    inside = False
    
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    
    return inside


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance between two points on Earth using Haversine formula.
    Returns distance in meters.
    """
    R = 6371000  # Earth's radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


class GeofenceService:
    """Service for managing geofences and checking violations"""
    
    def __init__(self):
        self.enabled = settings.GEOFENCE_ALERT_ENABLED
    
    # ============ Geofence CRUD Operations ============
    
    def create_geofence(self, name: str, polygon: List[Dict], description: str = None,
                        color: str = '#3B82F6', alert_on_exit: bool = True,
                        alert_on_enter: bool = False) -> Optional[int]:
        """
        Create a new geofence.
        Polygon format: [{"lat": 12.34, "lng": 56.78}, ...]
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            polygon_json = json.dumps(polygon)
            
            cursor.execute('''
                INSERT INTO geofences 
                (name, description, polygon, color, alert_on_exit, alert_on_enter, active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            ''', (name, description, polygon_json, color, alert_on_exit, alert_on_enter))
            
            geofence_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ Geofence '{name}' created with ID {geofence_id}")
            return geofence_id
            
        except Exception as e:
            print(f"❌ Error creating geofence: {e}")
            return None
    
    def update_geofence(self, geofence_id: int, **kwargs) -> bool:
        """Update a geofence"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            updates = []
            values = []
            
            for key in ['name', 'description', 'color', 'alert_on_exit', 'alert_on_enter', 'active']:
                if key in kwargs:
                    updates.append(f"{key} = ?")
                    values.append(kwargs[key])
            
            if 'polygon' in kwargs:
                updates.append("polygon = ?")
                values.append(json.dumps(kwargs['polygon']))
            
            if not updates:
                return False
            
            updates.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            values.append(geofence_id)
            
            cursor.execute(f'''
                UPDATE geofences 
                SET {', '.join(updates)}
                WHERE id = ?
            ''', values)
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error updating geofence: {e}")
            return False
    
    def delete_geofence(self, geofence_id: int) -> bool:
        """Delete a geofence"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM geofence_violations WHERE geofence_id = ?', (geofence_id,))
            cursor.execute('DELETE FROM device_zone_status WHERE geofence_id = ?', (geofence_id,))
            cursor.execute('DELETE FROM geofences WHERE id = ?', (geofence_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error deleting geofence: {e}")
            return False
    
    def get_geofence(self, geofence_id: int) -> Optional[Dict]:
        """Get a single geofence"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM geofences WHERE id = ?', (geofence_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                geofence = dict(row)
                geofence['polygon'] = json.loads(geofence['polygon'])
                return geofence
            return None
            
        except Exception as e:
            print(f"Error getting geofence: {e}")
            return None
    
    def get_all_geofences(self, active_only: bool = False) -> List[Dict]:
        """Get all geofences"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if active_only:
                cursor.execute('SELECT * FROM geofences WHERE active = 1 ORDER BY name')
            else:
                cursor.execute('SELECT * FROM geofences ORDER BY name')
            
            geofences = []
            for row in cursor.fetchall():
                gf = dict(row)
                gf['polygon'] = json.loads(gf['polygon'])
                geofences.append(gf)
            
            conn.close()
            return geofences
            
        except Exception as e:
            print(f"Error getting geofences: {e}")
            return []
    
    # ============ Geofence Checking ============
    
    def check_device_location(self, device_id: str, latitude: float, longitude: float) -> List[Dict]:
        """
        Check if a device location violates any geofence.
        Returns list of violations.
        """
        if not self.enabled or latitude == 0 or longitude == 0:
            return []
        
        violations = []
        geofences = self.get_all_geofences(active_only=True)
        
        for geofence in geofences:
            polygon = [(p['lat'], p['lng']) for p in geofence['polygon']]
            is_inside = point_in_polygon((latitude, longitude), polygon)
            
            # Get previous status
            was_inside = self._get_device_zone_status(device_id, geofence['id'])
            
            # Check for violations
            if was_inside is not None:
                # Exited the zone
                if was_inside and not is_inside and geofence['alert_on_exit']:
                    violation = self._create_violation(
                        geofence['id'], device_id, 'exit', latitude, longitude
                    )
                    if violation:
                        violation['geofence_name'] = geofence['name']
                        violations.append(violation)
                
                # Entered the zone
                if not was_inside and is_inside and geofence['alert_on_enter']:
                    violation = self._create_violation(
                        geofence['id'], device_id, 'enter', latitude, longitude
                    )
                    if violation:
                        violation['geofence_name'] = geofence['name']
                        violations.append(violation)
            
            # Update device zone status
            self._update_device_zone_status(device_id, geofence['id'], is_inside)
        
        return violations
    
    def _get_device_zone_status(self, device_id: str, geofence_id: int) -> Optional[bool]:
        """Get the last known zone status for a device"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT is_inside FROM device_zone_status 
                WHERE device_id = ? AND geofence_id = ?
            ''', (device_id, geofence_id))
            
            row = cursor.fetchone()
            conn.close()
            
            return bool(row[0]) if row else None
            
        except Exception as e:
            print(f"Error getting device zone status: {e}")
            return None
    
    def _update_device_zone_status(self, device_id: str, geofence_id: int, is_inside: bool):
        """Update device zone status"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO device_zone_status 
                (device_id, geofence_id, is_inside, last_check)
                VALUES (?, ?, ?, ?)
            ''', (device_id, geofence_id, is_inside, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error updating device zone status: {e}")
    
    def _create_violation(self, geofence_id: int, device_id: str, 
                          violation_type: str, latitude: float, longitude: float) -> Optional[Dict]:
        """Create a geofence violation record"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO geofence_violations 
                (geofence_id, device_id, violation_type, latitude, longitude)
                VALUES (?, ?, ?, ?, ?)
            ''', (geofence_id, device_id, violation_type, latitude, longitude))
            
            violation_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {
                'id': violation_id,
                'geofence_id': geofence_id,
                'device_id': device_id,
                'violation_type': violation_type,
                'latitude': latitude,
                'longitude': longitude,
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error creating violation: {e}")
            return None
    
    def get_violations(self, limit: int = 50, unresolved_only: bool = False) -> List[Dict]:
        """Get geofence violations"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT v.*, g.name as geofence_name, g.color as geofence_color
                FROM geofence_violations v
                JOIN geofences g ON v.geofence_id = g.id
            '''
            
            if unresolved_only:
                query += ' WHERE v.resolved = 0'
            
            query += ' ORDER BY v.created_at DESC LIMIT ?'
            
            cursor.execute(query, (limit,))
            violations = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return violations
            
        except Exception as e:
            print(f"Error getting violations: {e}")
            return []
    
    def resolve_violation(self, violation_id: int) -> bool:
        """Mark a violation as resolved"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE geofence_violations 
                SET resolved = 1 
                WHERE id = ?
            ''', (violation_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error resolving violation: {e}")
            return False
    
    def get_device_status_summary(self) -> List[Dict]:
        """Get summary of all devices and their zone status"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    d.device_id,
                    g.name as geofence_name,
                    d.is_inside,
                    d.last_check
                FROM device_zone_status d
                JOIN geofences g ON d.geofence_id = g.id
                ORDER BY d.device_id, g.name
            ''')
            
            statuses = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return statuses
            
        except Exception as e:
            print(f"Error getting device status summary: {e}")
            return []


# Global instance
geofence_service = GeofenceService()


# Helper functions for easy access
def check_location(device_id: str, latitude: float, longitude: float) -> List[Dict]:
    """Check if a device location has any geofence violations"""
    return geofence_service.check_device_location(device_id, latitude, longitude)


def create_geofence(name: str, polygon: List[Dict], **kwargs) -> Optional[int]:
    """Create a new geofence"""
    return geofence_service.create_geofence(name, polygon, **kwargs)


def get_all_geofences(active_only: bool = False) -> List[Dict]:
    """Get all geofences"""
    return geofence_service.get_all_geofences(active_only)


def get_violations(limit: int = 50, unresolved_only: bool = False) -> List[Dict]:
    """Get geofence violations"""
    return geofence_service.get_violations(limit, unresolved_only)
