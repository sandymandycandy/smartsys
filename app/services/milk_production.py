import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.config import settings

class MilkProductionService:
    """Service for managing milk production records"""
    
    def __init__(self):
        self.db_path = settings.LORA_DB_PATH
        self._init_database()
    
    def _init_database(self):
        """Initialize milk production tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Milk production records table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS milk_production (
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
            ''')
            
            # Index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_milk_device_date 
                ON milk_production(device_id, collection_date)
            ''')
            
            # Animal profiles table (extended info)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS animal_profiles (
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
            ''')
            
            conn.commit()
            conn.close()
            print("✅ Milk production tables initialized")
        except Exception as e:
            print(f"❌ Error initializing milk production tables: {e}")
    
    def record_production(self, data: Dict) -> Dict:
        """Record milk production for an animal"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO milk_production 
                (device_id, collection_date, collection_time, yield_liters, 
                 fat_percentage, protein_percentage, lactose_percentage,
                 quality_grade, milking_session, notes, recorded_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('device_id'),
                data.get('collection_date'),
                data.get('collection_time', datetime.now().strftime('%H:%M:%S')),
                data.get('yield_liters'),
                data.get('fat_percentage'),
                data.get('protein_percentage'),
                data.get('lactose_percentage'),
                data.get('quality_grade'),
                data.get('milking_session', 'morning'),
                data.get('notes'),
                data.get('recorded_by', 'system')
            ))
            
            record_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {"success": True, "id": record_id, "message": "Production recorded successfully"}
        except sqlite3.IntegrityError:
            return {"success": False, "message": "Record already exists for this date and time"}
        except Exception as e:
            return {"success": False, "message": f"Error recording production: {str(e)}"}
    
    def get_production_by_animal(self, device_id: str, days: int = 30) -> List[Dict]:
        """Get production records for a specific animal"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            cursor.execute('''
                SELECT * FROM milk_production
                WHERE device_id = ?
                AND collection_date >= ?
                ORDER BY collection_date DESC, collection_time DESC
            ''', (device_id, since_date))
            
            records = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return records
        except Exception as e:
            print(f"Error fetching production records: {e}")
            return []
    
    def get_daily_total(self, device_id: str, date: str = None) -> Dict:
        """Get total production for a specific day"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    SUM(yield_liters) as total_yield,
                    AVG(fat_percentage) as avg_fat,
                    AVG(protein_percentage) as avg_protein,
                    COUNT(*) as session_count
                FROM milk_production
                WHERE device_id = ? AND collection_date = ?
            ''', (device_id, date))
            
            result = cursor.fetchone()
            conn.close()
            
            return {
                "date": date,
                "total_yield": result[0] or 0,
                "avg_fat": result[1] or 0,
                "avg_protein": result[2] or 0,
                "session_count": result[3] or 0
            }
        except Exception as e:
            print(f"Error fetching daily total: {e}")
            return {"date": date, "total_yield": 0, "avg_fat": 0, "avg_protein": 0, "session_count": 0}
    
    def get_herd_production_summary(self, days: int = 30) -> Dict:
        """Get overall herd production statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Overall stats
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT device_id) as active_producers,
                    SUM(yield_liters) as total_yield,
                    AVG(yield_liters) as avg_yield_per_session,
                    AVG(fat_percentage) as avg_fat,
                    AVG(protein_percentage) as avg_protein
                FROM milk_production
                WHERE collection_date >= ?
            ''', (since_date,))
            
            summary = dict(cursor.fetchone())
            
            # Top producers
            cursor.execute('''
                SELECT 
                    device_id,
                    SUM(yield_liters) as total_yield,
                    AVG(yield_liters) as avg_yield,
                    COUNT(*) as sessions
                FROM milk_production
                WHERE collection_date >= ?
                GROUP BY device_id
                ORDER BY total_yield DESC
                LIMIT 10
            ''', (since_date,))
            
            top_producers = [dict(row) for row in cursor.fetchall()]
            
            # Daily trends
            cursor.execute('''
                SELECT 
                    collection_date,
                    SUM(yield_liters) as daily_yield,
                    COUNT(DISTINCT device_id) as animals_milked
                FROM milk_production
                WHERE collection_date >= ?
                GROUP BY collection_date
                ORDER BY collection_date ASC
            ''', (since_date,))
            
            daily_trends = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                "summary": summary,
                "top_producers": top_producers,
                "daily_trends": daily_trends
            }
        except Exception as e:
            print(f"Error fetching herd summary: {e}")
            return {"summary": {}, "top_producers": [], "daily_trends": []}
    
    def get_production_trends(self, device_id: str, days: int = 30) -> List[Dict]:
        """Get production trends for charts"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            cursor.execute('''
                SELECT 
                    collection_date,
                    SUM(yield_liters) as daily_yield,
                    AVG(fat_percentage) as avg_fat,
                    AVG(protein_percentage) as avg_protein,
                    COUNT(*) as sessions
                FROM milk_production
                WHERE device_id = ? AND collection_date >= ?
                GROUP BY collection_date
                ORDER BY collection_date ASC
            ''', (device_id, since_date))
            
            trends = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return trends
        except Exception as e:
            print(f"Error fetching trends: {e}")
            return []
    
    def update_animal_profile(self, device_id: str, profile_data: Dict) -> Dict:
        """Update or create animal profile"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO animal_profiles
                (device_id, animal_name, breed, birth_date, lactation_number,
                 last_calving_date, expected_yield_per_day, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                device_id,
                profile_data.get('animal_name'),
                profile_data.get('breed'),
                profile_data.get('birth_date'),
                profile_data.get('lactation_number'),
                profile_data.get('last_calving_date'),
                profile_data.get('expected_yield_per_day'),
                profile_data.get('notes')
            ))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Profile updated successfully"}
        except Exception as e:
            return {"success": False, "message": f"Error updating profile: {str(e)}"}
    
    def get_animal_profile(self, device_id: str) -> Optional[Dict]:
        """Get animal profile"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM animal_profiles WHERE device_id = ?', (device_id,))
            result = cursor.fetchone()
            conn.close()
            
            return dict(result) if result else None
        except Exception as e:
            print(f"Error fetching profile: {e}")
            return None
    
    def delete_production_record(self, record_id: int) -> Dict:
        """Delete a production record"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM milk_production WHERE id = ?', (record_id,))
            conn.commit()
            deleted = cursor.rowcount
            conn.close()
            
            if deleted > 0:
                return {"success": True, "message": "Record deleted successfully"}
            else:
                return {"success": False, "message": "Record not found"}
        except Exception as e:
            return {"success": False, "message": f"Error deleting record: {str(e)}"}

# Global instance
milk_service = MilkProductionService()
