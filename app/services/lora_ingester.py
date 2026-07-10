#!/usr/bin/env python3
"""
LoRa Data Ingestion Service
Accepts livestock data from LoRa receiver via multiple methods:
- Direct database inserts
- HTTP POST requests
- MQTT subscriptions
- Serial port readings
"""

import sqlite3
import json
import time
from datetime import datetime
from typing import Dict, Optional
from app.config import settings

class LoRaDataIngester:
    """Handle LoRa data ingestion from various sources"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.LORA_DB_PATH
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure database tables exist and have correct schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Base table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS livestock_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    temperature REAL,
                    ambient_temperature REAL,
                    body_temperature REAL,
                    humidity REAL,
                    heart_rate INTEGER,
                    battery INTEGER,
                    accel_x REAL,
                    accel_y REAL,
                    accel_z REAL,
                    gyro_x REAL,
                    gyro_y REAL,
                    gyro_z REAL,
                    rotation_speed REAL,
                    motion_magnitude REAL,
                    received_time TEXT,
                    rssi INTEGER
                )
            ''')
            
            # Migration: Add new columns if they don't exist (SQLite doesn't support IF NOT EXISTS for columns)
            # We try to add them and ignore the error if they exist
            try:
                cursor.execute('ALTER TABLE livestock_readings ADD COLUMN ambient_temperature REAL')
            except sqlite3.OperationalError:
                pass  # Column likely exists
                
            try:
                cursor.execute('ALTER TABLE livestock_readings ADD COLUMN body_temperature REAL')
            except sqlite3.OperationalError:
                pass  # Column likely exists
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    alert_time TEXT NOT NULL,
                    details TEXT,
                    resolved INTEGER DEFAULT 0,
                    resolved_at TEXT,
                    latitude REAL, 
                    longitude REAL
                )
            ''')
            
            # Create indexes if they don't exist
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_id ON livestock_readings(device_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON livestock_readings(timestamp)')
            
            conn.commit()
            conn.close()
            print("✅ Database tables verified")
        except Exception as e:
            print(f"❌ Error ensuring tables: {e}")
    
    def insert_reading(self, reading: Dict) -> bool:
        """
        Insert a single reading into the database
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Prepare received_time
            ts = reading.get('timestamp', time.time())
            # If timestamp is in milliseconds (13 digits), convert to seconds
            if ts > 10_000_000_000:
                ts = ts / 1000.0
            
            received_time = datetime.fromtimestamp(ts).isoformat()
            
            cursor.execute('''
                INSERT INTO livestock_readings (
                    device_id, timestamp, temperature, ambient_temperature, body_temperature,
                    heart_rate, battery,
                    latitude, longitude, humidity, accel_x, accel_y, accel_z,
                    gyro_x, gyro_y, gyro_z, rotation_speed, motion_magnitude,
                    received_time, rssi
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                reading.get('device_id'),
                reading.get('timestamp', int(time.time())),
                reading.get('temperature'),          # Legacy/Compatibility
                reading.get('ambient_temperature'),  # New
                reading.get('body_temperature'),     # New
                reading.get('heart_rate'),
                reading.get('battery'),
                reading.get('latitude'),
                reading.get('longitude'),
                reading.get('humidity'),
                reading.get('accel_x'),
                reading.get('accel_y'),
                reading.get('accel_z'),
                reading.get('gyro_x'),
                reading.get('gyro_y'),
                reading.get('gyro_z'),
                reading.get('rotation_speed'),
                reading.get('motion_magnitude'),
                received_time,
                reading.get('rssi')
            ))
            
            conn.commit()
            reading_id = cursor.lastrowid
            conn.close()
            
            print(f"✅ Inserted reading ID {reading_id} for {reading.get('device_id')}")
            return True
        except Exception as e:
            print(f"❌ Error inserting reading: {e}")
            return False
    
    def batch_insert_readings(self, readings: list) -> int:
        """Insert multiple readings at once"""
        count = 0
        for reading in readings:
            if self.insert_reading(reading):
                count += 1
        print(f"📊 Inserted {count}/{len(readings)} readings")
        return count


# Standalone functions for direct usage
def insert_lora_reading(reading: Dict) -> bool:
    """Quick function to insert a single LoRa reading"""
    ingester = LoRaDataIngester()
    return ingester.insert_reading(reading)


def insert_lora_readings(readings: list) -> int:
    """Quick function to insert multiple LoRa readings"""
    ingester = LoRaDataIngester()
    return ingester.batch_insert_readings(readings)


if __name__ == "__main__":
    # Example usage
    ingester = LoRaDataIngester()
    
    # Example reading
    example_reading = {
        'device_id': 'COW-006',
        'timestamp': int(time.time()),
        'temperature': 38.5,
        'heart_rate': 72,
        'battery': 85,
        'latitude': 0.0,
        'longitude': 0.0,
        'humidity': 65.0,
        'accel_x': 0.1,
        'accel_y': 0.2,
        'accel_z': 9.8,
        'gyro_x': 0.01,
        'gyro_y': 0.02,
        'gyro_z': 0.03,
        'rotation_speed': 0.5,
        'motion_magnitude': 0.25,
        'rssi': -75
    }
    
    print("\n📡 LoRa Data Ingestion Service")
    print("=" * 50)
    ingester.insert_reading(example_reading)
    print("✅ Service ready for data ingestion")
