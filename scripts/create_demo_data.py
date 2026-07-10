#!/usr/bin/env python3
"""
Test script to generate demo data for the dashboard
"""
import sqlite3
import random
import time
from datetime import datetime, timedelta

def generate_demo_data(db_path='livestock_data.db', num_devices=5, num_readings=100):
    """Generate demo livestock data"""
    
    print(f"📊 Generating demo data...")
    print(f"   Devices: {num_devices}")
    print(f"   Readings per device: {num_readings}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Base coordinates (example: somewhere in a farm)
    base_lat = 40.7128
    base_lon = -74.0060
    
    device_ids = [f"COW-{i:03d}" for i in range(1, num_devices + 1)]
    
    for device_id in device_ids:
        print(f"  Generating data for {device_id}...")
        
        for i in range(num_readings):
            # Generate timestamp (last 24 hours)
            timestamp = int(time.time()) - (num_readings - i) * 900  # 15 min intervals
            received_time = datetime.fromtimestamp(timestamp).isoformat()
            
            # Random walk for GPS coordinates
            latitude = base_lat + random.uniform(-0.01, 0.01)
            longitude = base_lon + random.uniform(-0.01, 0.01)
            
            # Realistic health data
            temperature = random.normalvariate(38.5, 0.5)  # Normal bovine temp
            humidity = random.uniform(40, 70)
            heart_rate = random.randint(50, 70)
            battery = max(10, 100 - (i * 0.5))  # Slowly draining
            
            # Accelerometer data
            accel_x = random.normalvariate(0, 0.2)
            accel_y = random.normalvariate(0, 0.2)
            accel_z = random.normalvariate(9.8, 0.2)
            
            # Gyroscope data
            gyro_x = random.normalvariate(0, 10)
            gyro_y = random.normalvariate(0, 10)
            gyro_z = random.normalvariate(0, 10)
            
            rotation_speed = (gyro_x**2 + gyro_y**2 + gyro_z**2)**0.5
            motion_magnitude = ((accel_x**2 + accel_y**2 + (accel_z-9.8)**2)**0.5)
            
            rssi = random.randint(-100, -40)
            
            # Occasionally create anomalies
            if random.random() < 0.05:  # 5% chance
                temperature += random.uniform(1, 2)
                heart_rate += random.randint(10, 30)
            
            cursor.execute('''
                INSERT INTO livestock_readings 
                (device_id, timestamp, latitude, longitude, temperature, humidity, 
                 heart_rate, battery, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z,
                 rotation_speed, motion_magnitude, received_time, rssi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                device_id, timestamp, latitude, longitude, temperature, humidity,
                heart_rate, int(battery), accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z,
                rotation_speed, motion_magnitude, received_time, rssi
            ))
    
    conn.commit()
    total_records = num_devices * num_readings
    print(f"✅ Generated {total_records} demo records")
    
    # Show summary
    cursor.execute('SELECT COUNT(*) FROM livestock_readings')
    count = cursor.fetchone()[0]
    print(f"📊 Total records in database: {count}")
    
    cursor.execute('SELECT COUNT(DISTINCT device_id) FROM livestock_readings')
    devices = cursor.fetchone()[0]
    print(f"🐮 Total unique devices: {devices}")
    
    conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--clear':
            response = input("⚠️  This will DELETE all existing data. Continue? (yes/no): ")
            if response.lower() == 'yes':
                conn = sqlite3.connect('livestock_data.db')
                cursor = conn.cursor()
                cursor.execute('DELETE FROM livestock_readings')
                cursor.execute('DELETE FROM alerts')
                conn.commit()
                conn.close()
                print("✅ Data cleared")
            else:
                print("❌ Cancelled")
                sys.exit(0)
    
    generate_demo_data()
