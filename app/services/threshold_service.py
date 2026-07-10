"""
Threshold Configuration Service
Allows dynamic configuration of alert thresholds
"""
import sqlite3
import os
from datetime import datetime
from typing import Dict, Optional

try:
    from app.config import settings
except:
    from config import settings

# Database path
DB_PATH = os.path.join(os.path.dirname(settings.LORA_DB_PATH), "thresholds.db")

# Default thresholds from config
DEFAULT_THRESHOLDS = {
    'temp_warning': settings.TEMP_WARNING,
    'temp_critical': settings.TEMP_CRITICAL,
    'hr_warning': settings.HR_WARNING,
    'hr_critical': settings.HR_CRITICAL,
    'battery_low': settings.BATTERY_LOW,
    'battery_critical': settings.BATTERY_CRITICAL,
    'ambient_temp_high': 35.0,
    'ambient_temp_low': 5.0,
    'humidity_high': 85,
    'humidity_low': 20,
    'motion_inactive': 0.1,
    'motion_hyperactive': 5.0
}


def init_thresholds_db():
    """Initialize the thresholds database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Thresholds table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS thresholds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            threshold_key TEXT UNIQUE NOT NULL,
            threshold_value REAL NOT NULL,
            description TEXT,
            unit TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Threshold change log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS threshold_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            threshold_key TEXT NOT NULL,
            old_value REAL,
            new_value REAL,
            changed_by TEXT,
            changed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default thresholds if not exist
    threshold_metadata = {
        'temp_warning': ('Body Temperature Warning', '°C'),
        'temp_critical': ('Body Temperature Critical', '°C'),
        'hr_warning': ('Heart Rate Warning', 'BPM'),
        'hr_critical': ('Heart Rate Critical', 'BPM'),
        'battery_low': ('Battery Low Warning', '%'),
        'battery_critical': ('Battery Critical', '%'),
        'ambient_temp_high': ('Ambient Temperature High', '°C'),
        'ambient_temp_low': ('Ambient Temperature Low', '°C'),
        'humidity_high': ('Humidity High', '%'),
        'humidity_low': ('Humidity Low', '%'),
        'motion_inactive': ('Motion Inactive Threshold', 'g'),
        'motion_hyperactive': ('Motion Hyperactive Threshold', 'g')
    }
    
    for key, value in DEFAULT_THRESHOLDS.items():
        desc, unit = threshold_metadata.get(key, ('', ''))
        cursor.execute('''
            INSERT OR IGNORE INTO thresholds (threshold_key, threshold_value, description, unit)
            VALUES (?, ?, ?, ?)
        ''', (key, value, desc, unit))
    
    conn.commit()
    conn.close()

# Initialize database on import
init_thresholds_db()


class ThresholdService:
    """Service for managing configurable alert thresholds"""
    
    _cache = None
    _cache_time = None
    
    @classmethod
    def get_all_thresholds(cls) -> Dict[str, float]:
        """Get all threshold values"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT threshold_key, threshold_value FROM thresholds')
            thresholds = {row['threshold_key']: row['threshold_value'] for row in cursor.fetchall()}
            conn.close()
            
            # Merge with defaults for any missing values
            for key, value in DEFAULT_THRESHOLDS.items():
                if key not in thresholds:
                    thresholds[key] = value
            
            cls._cache = thresholds
            return thresholds
            
        except Exception as e:
            print(f"Error getting thresholds: {e}")
            return DEFAULT_THRESHOLDS.copy()
    
    @classmethod
    def get_threshold(cls, key: str) -> float:
        """Get a specific threshold value"""
        thresholds = cls.get_all_thresholds()
        return thresholds.get(key, DEFAULT_THRESHOLDS.get(key, 0))
    
    @classmethod
    def set_threshold(cls, key: str, value: float, changed_by: str = 'system') -> bool:
        """Set a threshold value"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get old value
            cursor.execute('SELECT threshold_value FROM thresholds WHERE threshold_key = ?', (key,))
            result = cursor.fetchone()
            old_value = result[0] if result else None
            
            # Update or insert
            cursor.execute('''
                INSERT OR REPLACE INTO thresholds (threshold_key, threshold_value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, value, datetime.now().isoformat()))
            
            # Log the change
            cursor.execute('''
                INSERT INTO threshold_log (threshold_key, old_value, new_value, changed_by)
                VALUES (?, ?, ?, ?)
            ''', (key, old_value, value, changed_by))
            
            conn.commit()
            conn.close()
            
            # Invalidate cache
            cls._cache = None
            
            print(f"✅ Threshold {key} set to {value}")
            return True
            
        except Exception as e:
            print(f"Error setting threshold: {e}")
            return False
    
    @classmethod
    def get_thresholds_with_metadata(cls) -> list:
        """Get all thresholds with their metadata"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM thresholds ORDER BY threshold_key')
            thresholds = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return thresholds
            
        except Exception as e:
            print(f"Error getting thresholds with metadata: {e}")
            return []
    
    @classmethod
    def get_change_log(cls, limit: int = 50) -> list:
        """Get threshold change history"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM threshold_log ORDER BY changed_at DESC LIMIT ?
            ''', (limit,))
            logs = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return logs
            
        except Exception as e:
            print(f"Error getting change log: {e}")
            return []
    
    @classmethod
    def reset_to_defaults(cls) -> bool:
        """Reset all thresholds to default values"""
        try:
            for key, value in DEFAULT_THRESHOLDS.items():
                cls.set_threshold(key, value, 'system_reset')
            return True
        except Exception as e:
            print(f"Error resetting thresholds: {e}")
            return False


# Convenience functions
def get_threshold(key: str) -> float:
    """Get a threshold value"""
    return ThresholdService.get_threshold(key)


def get_all_thresholds() -> Dict[str, float]:
    """Get all thresholds"""
    return ThresholdService.get_all_thresholds()


def set_threshold(key: str, value: float, changed_by: str = 'system') -> bool:
    """Set a threshold value"""
    return ThresholdService.set_threshold(key, value, changed_by)


def get_thresholds_with_metadata() -> list:
    """Get all thresholds with metadata"""
    return ThresholdService.get_thresholds_with_metadata()
