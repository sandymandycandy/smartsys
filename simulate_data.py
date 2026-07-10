
import sqlite3
import time
import random
import requests
import json
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000/api/ingest/reading"
DEVICE_ID = "COW001"

def generate_packet(lat=13.0827, lon=80.2707):
    """Generate a realistic mock packet"""
    
    # Simulate random walk
    lat += random.uniform(-0.0001, 0.0001)
    lon += random.uniform(-0.0001, 0.0001)
    
    # Simulate values
    data = {
        'device_id': DEVICE_ID,
        'timestamp': int(time.time() * 1000),
        'latitude': lat,
        'longitude': lon,
        'satellites': random.randint(5, 12),
        'temperature': round(random.uniform(38.0, 39.5), 2),        # Body temp mapped to 'temperature'
        'body_temperature': round(random.uniform(38.0, 39.5), 2),
        'ambient_temperature': round(random.uniform(25.0, 32.0), 1),
        'humidity': round(random.uniform(40, 70), 1),
        'heart_rate': random.randint(50, 80),
        'battery': random.randint(80, 100),
        'accel_x': round(random.uniform(-0.5, 0.5), 3),
        'accel_y': round(random.uniform(-0.5, 0.5), 3),
        'accel_z': round(random.uniform(0.8, 1.0), 3),
        'gyro_x': round(random.uniform(-10, 10), 2),
        'gyro_y': round(random.uniform(-10, 10), 2),
        'gyro_z': round(random.uniform(-10, 10), 2),
        'motion_magnitude': round(random.uniform(0.9, 1.1), 3),
        'rotation_speed': round(random.uniform(0, 20), 2),
        'rssi': random.randint(-80, -40),
        'snr': round(random.uniform(5, 12), 1)
    }
    return data

def send_data():
    print(f"🚀 Starting data simulation for device {DEVICE_ID}...")
    print(f"📡 Sending to: {API_URL}")
    print("Press Ctrl+C to stop.\n")
    
    lat, lon = 13.0827, 80.2707
    
    try:
        while True:
            packet = generate_packet(lat, lon)
            
            # Send to API
            try:
                response = requests.post(API_URL, json=packet)
                if response.status_code == 200:
                    print(f"✅ Sent packet: HR={packet['heart_rate']} BPM, Temp={packet['body_temperature']}°C")
                else:
                    print(f"⚠️ API Error {response.status_code}: {response.text}")
            except requests.exceptions.ConnectionError:
                print("❌ Connection Error: Is the server running on localhost:8000?")
            
            # Update random walk base
            lat = packet['latitude']
            lon = packet['longitude']
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped.")

if __name__ == "__main__":
    send_data()
