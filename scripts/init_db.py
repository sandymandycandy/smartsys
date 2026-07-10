#!/usr/bin/env python3
"""
Initialize the livestock database with required tables
"""
import sqlite3
import os
from datetime import datetime

def init_database(db_path='livestock_data.db'):
    """Initialize database with required tables"""
    
    print(f"📊 Initializing database: {db_path}")
    
    # Check if database already exists
    if os.path.exists(db_path):
        response = input(f"⚠️  Database {db_path} already exists. Create alerts table anyway? (y/n): ")
        if response.lower() != 'y':
            print("❌ Cancelled")
            return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create livestock_readings table (should exist from receiver)
    print("Creating livestock_readings table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS livestock_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            latitude REAL,
            longitude REAL,
            temperature REAL,
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
    
    # Create alerts table
    print("Creating alerts table...")
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
    
    # Create indexes for performance
    print("Creating indexes...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_id ON livestock_readings(device_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON livestock_readings(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_device ON alerts(device_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved)')
    
    conn.commit()
    conn.close()
    
    print("✅ Database initialized successfully!")
    print(f"📁 Location: {os.path.abspath(db_path)}")
    
if __name__ == "__main__":
    init_database()
