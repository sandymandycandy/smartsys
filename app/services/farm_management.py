"""
Multi-Farm Management Service
Allows managing multiple farms/locations with separate livestock groups
"""
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from app.config import settings


class FarmManagementService:
    """
    Manages multiple farms and their associated livestock
    """
    
    def __init__(self):
        self.db_path = settings.LORA_DB_PATH
        self._init_database()
    
    def _init_database(self):
        """Initialize farm management tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Farms table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS farms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Farm-Animal mapping
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS farm_animals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    farm_id INTEGER NOT NULL,
                    device_id TEXT NOT NULL,
                    assigned_date DATE DEFAULT CURRENT_DATE,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (farm_id) REFERENCES farms(id),
                    UNIQUE(farm_id, device_id)
                )
            ''')
            
            # Create default farm if none exists
            cursor.execute('SELECT COUNT(*) FROM farms')
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO farms (farm_code, farm_name, location, is_active)
                    VALUES ('MAIN', 'Main Farm', 'Primary Location', 1)
                ''')
                
                # Assign all existing animals to default farm
                cursor.execute('SELECT DISTINCT device_id FROM livestock_readings')
                animals = cursor.fetchall()
                farm_id = cursor.lastrowid
                
                for (device_id,) in animals:
                    cursor.execute('''
                        INSERT OR IGNORE INTO farm_animals (farm_id, device_id)
                        VALUES (?, ?)
                    ''', (farm_id, device_id))
            
            conn.commit()
            conn.close()
            print("✅ Farm management tables initialized")
            
        except Exception as e:
            print(f"❌ Error initializing farm tables: {e}")
    
    def create_farm(self, farm_data: Dict) -> Dict:
        """Create a new farm"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO farms 
                (farm_code, farm_name, location, latitude, longitude, 
                 area_hectares, owner_name, contact_phone, contact_email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                farm_data.get('farm_code'),
                farm_data.get('farm_name'),
                farm_data.get('location'),
                farm_data.get('latitude'),
                farm_data.get('longitude'),
                farm_data.get('area_hectares'),
                farm_data.get('owner_name'),
                farm_data.get('contact_phone'),
                farm_data.get('contact_email')
            ))
            
            farm_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "farm_id": farm_id,
                "message": f"Farm '{farm_data.get('farm_name')}' created successfully"
            }
            
        except sqlite3.IntegrityError:
            return {"success": False, "message": "Farm code already exists"}
        except Exception as e:
            return {"success": False, "message": f"Error creating farm: {str(e)}"}
    
    def get_all_farms(self) -> List[Dict]:
        """Get list of all farms"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT f.*,
                       COUNT(fa.device_id) as animal_count
                FROM farms f
                LEFT JOIN farm_animals fa ON f.id = fa.farm_id AND fa.is_active = 1
                WHERE f.is_active = 1
                GROUP BY f.id
                ORDER BY f.farm_name
            ''')
            
            farms = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return farms
            
        except Exception as e:
            print(f"Error fetching farms: {e}")
            return []
    
    def get_farm(self, farm_id: int) -> Optional[Dict]:
        """Get single farm details"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM farms WHERE id = ? AND is_active = 1', (farm_id,))
            result = cursor.fetchone()
            conn.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            print(f"Error fetching farm: {e}")
            return None
    
    def update_farm(self, farm_id: int, farm_data: Dict) -> Dict:
        """Update farm information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE farms
                SET farm_name = ?,
                    location = ?,
                    latitude = ?,
                    longitude = ?,
                    area_hectares = ?,
                    owner_name = ?,
                    contact_phone = ?,
                    contact_email = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                farm_data.get('farm_name'),
                farm_data.get('location'),
                farm_data.get('latitude'),
                farm_data.get('longitude'),
                farm_data.get('area_hectares'),
                farm_data.get('owner_name'),
                farm_data.get('contact_phone'),
                farm_data.get('contact_email'),
                farm_id
            ))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Farm updated successfully"}
            
        except Exception as e:
            return {"success": False, "message": f"Error updating farm: {str(e)}"}
    
    def delete_farm(self, farm_id: int) -> Dict:
        """Soft delete a farm"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Don't allow deleting the last farm
            cursor.execute('SELECT COUNT(*) FROM farms WHERE is_active = 1')
            if cursor.fetchone()[0] <= 1:
                return {"success": False, "message": "Cannot delete the last farm"}
            
            cursor.execute('''
                UPDATE farms SET is_active = 0 WHERE id = ?
            ''', (farm_id,))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Farm deleted successfully"}
            
        except Exception as e:
            return {"success": False, "message": f"Error deleting farm: {str(e)}"}
    
    def assign_animal(self, farm_id: int, device_id: str) -> Dict:
        """Assign animal to a farm"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Remove from other farms first
            cursor.execute('UPDATE farm_animals SET is_active = 0 WHERE device_id = ?', (device_id,))
            
            # Assign to new farm
            cursor.execute('''
                INSERT OR REPLACE INTO farm_animals (farm_id, device_id, is_active)
                VALUES (?, ?, 1)
            ''', (farm_id, device_id))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": f"Animal {device_id} assigned to farm"}
            
        except Exception as e:
            return {"success": False, "message": f"Error assigning animal: {str(e)}"}
    
    def get_farm_animals(self, farm_id: int) -> List[Dict]:
        """Get all animals in a farm"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    fa.device_id,
                    fa.assigned_date,
                    lr.temperature,
                    lr.heart_rate,
                    lr.battery,
                    lr.latitude,
                    lr.longitude,
                    lr.received_time as last_update,
                    (SELECT COUNT(*) FROM alerts 
                     WHERE device_id = fa.device_id AND resolved = 0) as alert_count
                FROM farm_animals fa
                LEFT JOIN (
                    SELECT device_id, MAX(received_time) as max_time
                    FROM livestock_readings
                    GROUP BY device_id
                ) latest ON fa.device_id = latest.device_id
                LEFT JOIN livestock_readings lr 
                    ON fa.device_id = lr.device_id 
                    AND lr.received_time = latest.max_time
                WHERE fa.farm_id = ? AND fa.is_active = 1
                ORDER BY fa.device_id
            ''', (farm_id,))
            
            animals = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return animals
            
        except Exception as e:
            print(f"Error fetching farm animals: {e}")
            return []
    
    def get_farm_stats(self, farm_id: int) -> Dict:
        """Get statistics for a specific farm"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get animal count and health stats
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT fa.device_id) as total_animals,
                    COUNT(DISTINCT CASE WHEN a.resolved = 0 THEN a.device_id END) as animals_with_alerts,
                    COUNT(CASE WHEN a.resolved = 0 THEN 1 END) as active_alerts
                FROM farm_animals fa
                LEFT JOIN alerts a ON fa.device_id = a.device_id
                WHERE fa.farm_id = ? AND fa.is_active = 1
            ''', (farm_id,))
            
            basic_stats = dict(cursor.fetchone())
            
            # Get milk production stats (last 30 days)
            cursor.execute('''
                SELECT 
                    COUNT(*) as production_records,
                    SUM(mp.yield_liters) as total_yield,
                    AVG(mp.yield_liters) as avg_yield
                FROM farm_animals fa
                JOIN milk_production mp ON fa.device_id = mp.device_id
                WHERE fa.farm_id = ? 
                AND fa.is_active = 1
                AND mp.collection_date >= date('now', '-30 days')
            ''', (farm_id,))
            
            milk_stats = dict(cursor.fetchone())
            
            conn.close()
            
            return {
                **basic_stats,
                **milk_stats,
                "healthy_animals": basic_stats['total_animals'] - basic_stats['animals_with_alerts']
            }
            
        except Exception as e:
            print(f"Error fetching farm stats: {e}")
            return {}
    
    def compare_farms(self) -> List[Dict]:
        """Compare statistics across all farms"""
        try:
            farms = self.get_all_farms()
            comparison = []
            
            for farm in farms:
                stats = self.get_farm_stats(farm['id'])
                comparison.append({
                    'farm_id': farm['id'],
                    'farm_name': farm['farm_name'],
                    'farm_code': farm['farm_code'],
                    'location': farm['location'],
                    **stats
                })
            
            return comparison
            
        except Exception as e:
            print(f"Error comparing farms: {e}")
            return []


# Global instance
farm_service = FarmManagementService()
