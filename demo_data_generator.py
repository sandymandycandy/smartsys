"""
Enhanced Demo Data Generator for Smart Pastoralism
Generates realistic data for multiple animals with various health conditions
"""

import sqlite3
import random
import time
import requests
from datetime import datetime, timedelta

# Configuration
API_URL = "http://localhost:8000/api/ingest/reading"
DB_PATH = "livestock_data.db"

# Multiple animals with different profiles
ANIMALS = [
    {
        'device_id': 'COW001',
        'name': 'Bessie',
        'health': 'healthy',
        'base_temp': 38.5,
        'base_hr': 65,
        'location': (13.0827, 80.2707)  # Chennai
    },
    {
        'device_id': 'COW002',
        'name': 'Daisy',
        'health': 'fever',
        'base_temp': 40.2,  # Fever
        'base_hr': 85,
        'location': (13.0830, 80.2710)
    },
    {
        'device_id': 'COW003',
        'name': 'Molly',
        'health': 'healthy',
        'base_temp': 38.8,
        'base_hr': 70,
        'location': (13.0825, 80.2705)
    },
    {
        'device_id': 'SHEEP001',
        'name': 'Dolly',
        'health': 'heat_stress',
        'base_temp': 39.8,
        'base_hr': 90,
        'location': (13.0828, 80.2708)
    },
    {
        'device_id': 'SHEEP002',
        'name': 'Shaun',
        'health': 'healthy',
        'base_temp': 39.0,
        'base_hr': 75,
        'location': (13.0829, 80.2706)
    }
]

def generate_reading(animal, variation=True):
    """Generate a realistic reading for an animal"""
    
    # Add random variation if enabled
    if variation:
        temp_var = random.uniform(-0.3, 0.3)
        hr_var = random.randint(-5, 5)
    else:
        temp_var = 0
        hr_var = 0
    
    # Random walk for GPS
    lat = animal['location'][0] + random.uniform(-0.0002, 0.0002)
    lon = animal['location'][1] + random.uniform(-0.0002, 0.0002)
    
    # Generate motion based on health
    if animal['health'] == 'healthy':
        motion = round(random.uniform(0.8, 1.2), 3)
    elif animal['health'] == 'fever':
        motion = round(random.uniform(0.3, 0.6), 3)  # Low activity
    elif animal['health'] == 'heat_stress':
        motion = round(random.uniform(0.5, 0.9), 3)
    else:
        motion = round(random.uniform(0.7, 1.1), 3)
    
    data = {
        'device_id': animal['device_id'],
        'timestamp': int(time.time() * 1000),
        'latitude': round(lat, 6),
        'longitude': round(lon, 6),
        'satellites': random.randint(6, 12),
        'temperature': round(animal['base_temp'] + temp_var, 2),
        'body_temperature': round(animal['base_temp'] + temp_var, 2),
        'ambient_temperature': round(random.uniform(26.0, 33.0), 1),
        'humidity': round(random.uniform(45, 75), 1),
        'heart_rate': max(40, min(120, animal['base_hr'] + hr_var)),
        'battery': random.randint(75, 100),
        'accel_x': round(random.uniform(-0.5, 0.5), 3),
        'accel_y': round(random.uniform(-0.5, 0.5), 3),
        'accel_z': round(random.uniform(0.8, 1.0), 3),
        'gyro_x': round(random.uniform(-10, 10), 2),
        'gyro_y': round(random.uniform(-10, 10), 2),
        'gyro_z': round(random.uniform(-10, 10), 2),
        'motion_magnitude': motion,
        'rotation_speed': round(random.uniform(0, 25), 2),
        'rssi': random.randint(-85, -35),
        'snr': round(random.uniform(4, 13), 1)
    }
    
    return data

def send_reading(data):
    """Send reading to API"""
    try:
        response = requests.post(API_URL, json=data, timeout=5)
        if response.status_code == 200:
            return True, "Success"
        else:
            return False, f"HTTP {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Connection Error"
    except Exception as e:
        return False, str(e)

def generate_historical_data(hours=24):
    """Generate historical data for the past N hours"""
    print(f"📊 Generating {hours} hours of historical data...")
    print(f"   Animals: {len(ANIMALS)}")
    print(f"   Readings per animal: ~{hours * 4}")
    print()
    
    total_sent = 0
    total_failed = 0
    
    # Generate data going backwards in time
    for hour in range(hours, 0, -1):
        for minute in [0, 15, 30, 45]:  # 4 readings per hour
            for animal in ANIMALS:
                data = generate_reading(animal)
                
                # Adjust timestamp to be in the past
                past_time = datetime.now() - timedelta(hours=hour, minutes=minute)
                data['timestamp'] = int(past_time.timestamp() * 1000)
                
                success, msg = send_reading(data)
                if success:
                    total_sent += 1
                    print(f"✅ {animal['device_id']}: {data['temperature']}°C, {data['heart_rate']} BPM", end='\r')
                else:
                    total_failed += 1
                    print(f"❌ {animal['device_id']}: {msg}")
                
                time.sleep(0.05)  # Small delay to avoid overwhelming the server
    
    print(f"\n\n✅ Historical data generation complete!")
    print(f"   Total sent: {total_sent}")
    print(f"   Failed: {total_failed}")
    print()

def live_simulation():
    """Run live data simulation"""
    print("🔴 LIVE SIMULATION MODE")
    print("   Sending real-time data for all animals...")
    print("   Press Ctrl+C to stop\n")
    
    try:
        while True:
            for animal in ANIMALS:
                data = generate_reading(animal)
                success, msg = send_reading(data)
                
                status = "✅" if success else "❌"
                health_icon = "🟢" if animal['health'] == 'healthy' else "🔴"
                
                print(f"{status} {health_icon} {animal['device_id']:10s} | "
                      f"Temp: {data['temperature']:5.2f}°C | "
                      f"HR: {data['heart_rate']:3d} BPM | "
                      f"Motion: {data['motion_magnitude']:.2f}g | "
                      f"Battery: {data['battery']:3d}%")
            
            print()
            time.sleep(10)  # Send batch every 10 seconds
            
    except KeyboardInterrupt:
        print("\n\n🛑 Live simulation stopped")

def show_menu():
    """Show interactive menu"""
    print("╔═══════════════════════════════════════════════════════╗")
    print("║   SMART PASTORALISM - DEMO DATA GENERATOR            ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print()
    print("📋 Available Options:")
    print()
    print("  1. Generate 1 hour of historical data")
    print("  2. Generate 6 hours of historical data")
    print("  3. Generate 24 hours of historical data")
    print("  4. Start live simulation (real-time)")
    print("  5. Quick test (10 readings)")
    print("  6. Exit")
    print()
    
    choice = input("Select option (1-6): ").strip()
    return choice

def quick_test():
    """Send 10 quick test readings"""
    print("🧪 Quick Test - Sending 10 readings...\n")
    
    for i in range(10):
        animal = random.choice(ANIMALS)
        data = generate_reading(animal)
        success, msg = send_reading(data)
        
        status = "✅" if success else "❌"
        print(f"{status} Reading {i+1}/10: {animal['device_id']} - "
              f"{data['temperature']}°C, {data['heart_rate']} BPM")
        time.sleep(0.5)
    
    print("\n✅ Quick test complete!\n")

def main():
    """Main function"""
    while True:
        choice = show_menu()
        
        if choice == '1':
            generate_historical_data(hours=1)
        elif choice == '2':
            generate_historical_data(hours=6)
        elif choice == '3':
            generate_historical_data(hours=24)
        elif choice == '4':
            live_simulation()
        elif choice == '5':
            quick_test()
        elif choice == '6':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option. Please try again.\n")
        
        if choice != '6':
            input("\nPress Enter to continue...")
            print("\n" * 2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
