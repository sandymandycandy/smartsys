
import sqlite3
import os

db_path = 'livestock_data.db'
print(f"fixing database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create livestock_readings table
print("Creating livestock_readings table...")
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
        rssi INTEGER,
        snr REAL,
        anomaly_detected INTEGER DEFAULT 0
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
        battery INTEGER,
        latitude REAL,
        longitude REAL
    )
''')

# Create indexes
print("Creating indexes...")
cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_id ON livestock_readings(device_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON livestock_readings(timestamp)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_device ON alerts(device_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved)')

# Add missing columns if needed (migration)
try:
    cursor.execute('ALTER TABLE livestock_readings ADD COLUMN ambient_temperature REAL')
except: pass
try:
    cursor.execute('ALTER TABLE livestock_readings ADD COLUMN body_temperature REAL')
except: pass
try:
    cursor.execute('ALTER TABLE livestock_readings ADD COLUMN snr REAL')
except: pass
try:
    cursor.execute('ALTER TABLE livestock_readings ADD COLUMN anomaly_detected INTEGER DEFAULT 0')
except: pass
try:
    cursor.execute('ALTER TABLE alerts ADD COLUMN latitude REAL')
except: pass
try:
    cursor.execute('ALTER TABLE alerts ADD COLUMN longitude REAL')
except: pass


conn.commit()
conn.close()
print("✅ Database repaired!")
