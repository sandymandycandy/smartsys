"""
Demo Data Generator for Smart Pastoralism System
Generates realistic sample data for testing and demonstration
"""
import sqlite3
import random
from datetime import datetime, timedelta
from app.config import settings

class DemoDataGenerator:
    """Generate realistic demo data for all system features"""
    
    def __init__(self):
        self.db_path = settings.LORA_DB_PATH
        self.device_ids = [
            "COW-001", "COW-002", "COW-003", "COW-004", "COW-005",
            "COW-006", "COW-007", "COW-008", "COW-009", "COW-010",
            "SHEEP-001", "SHEEP-002", "SHEEP-003", "SHEEP-004", "SHEEP-005"
        ]
        self.animal_names = [
            "Bessie", "Daisy", "Buttercup", "Rosie", "Molly",
            "Luna", "Bella", "Maggie", "Penny", "Ruby",
            "Woolly", "Fluffy", "Cotton", "Snowball", "Cloud"
        ]
        self.breeds = [
            "Holstein", "Jersey", "Guernsey", "Brown Swiss", "Ayrshire",
            "Merino", "Dorset", "Suffolk", "Romney", "Texel"
        ]
    
    def generate_all(self):
        """Generate all demo data"""
        print("🔄 Generating demo data...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Step 1: Create farms
        print("1️⃣ Creating farms...")
        self.create_farms(cursor)
        
        # Step 2: Generate livestock readings (health data)
        print("2️⃣ Generating livestock readings (60 days)...")
        self.generate_livestock_readings(cursor, days=60)
        
        # Step 3: Create animal profiles
        print("3️⃣ Creating animal profiles...")
        self.create_animal_profiles(cursor)
        
        # Step 4: Generate milk production data
        print("4️⃣ Generating milk production records (90 days)...")
        self.generate_milk_production(cursor, days=90)
        
        # Step 5: Assign animals to farms
        print("5️⃣ Assigning animals to farms...")
        self.assign_animals_to_farms(cursor)
        
        # Step 6: Generate some alerts
        print("6️⃣ Creating sample alerts...")
        self.generate_alerts(cursor)
        
        conn.commit()
        conn.close()
        
        print("✅ Demo data generation complete!")
        print(f"   - {len(self.device_ids)} animals")
        print(f"   - 4 farms")
        print(f"   - ~{len(self.device_ids) * 60 * 96} health readings (60 days)")
        print(f"   - ~{len(self.device_ids) * 90 * 2} milk records (90 days)")
        print(f"   - Sample alerts and profiles")
    
    def create_farms(self, cursor):
        """Create demo farms"""
        farms = [
            {
                'code': 'NORTH-DAIRY',
                'name': 'North Dairy Farm',
                'location': 'North Pasture, County',
                'lat': 40.7128,
                'lon': -74.0060,
                'area': 75.5,
                'owner': 'John Smith',
                'phone': '+1-555-0101',
                'email': 'john@northdairy.com'
            },
            {
                'code': 'SOUTH-BREED',
                'name': 'South Breeding Site',
                'location': 'South Valley, County',
                'lat': 40.7228,
                'lon': -74.0160,
                'area': 120.0,
                'owner': 'Sarah Johnson',
                'phone': '+1-555-0102',
                'email': 'sarah@southbreed.com'
            },
            {
                'code': 'EAST-YOUNG',
                'name': 'East Young Stock',
                'location': 'East Hills, County',
                'lat': 40.7328,
                'lon': -73.9960,
                'area': 45.0,
                'owner': 'Mike Williams',
                'phone': '+1-555-0103',
                'email': 'mike@eastyoung.com'
            },
            {
                'code': 'WEST-SHEEP',
                'name': 'West Sheep Farm',
                'location': 'West Range, County',
                'lat': 40.7028,
                'lon': -74.0260,
                'area': 90.0,
                'owner': 'Emily Brown',
                'phone': '+1-555-0104',
                'email': 'emily@westsheep.com'
            }
        ]
        
        # Update Main Farm if it exists, otherwise create farms
        cursor.execute("SELECT COUNT(*) FROM farms WHERE farm_code = 'MAIN'")
        if cursor.fetchone()[0] > 0:
            # Update Main Farm
            cursor.execute('''
                UPDATE farms 
                SET location = 'Primary Location, County',
                    latitude = 40.7128,
                    longitude = -74.0060,
                    area_hectares = 100.0,
                    owner_name = 'Farm Manager',
                    contact_phone = '+1-555-0100',
                    contact_email = 'manager@mainfarm.com'
                WHERE farm_code = 'MAIN'
            ''')
        
        # Create additional farms
        for farm in farms:
            cursor.execute('''
                INSERT OR IGNORE INTO farms 
                (farm_code, farm_name, location, latitude, longitude, 
                 area_hectares, owner_name, contact_phone, contact_email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (farm['code'], farm['name'], farm['location'], farm['lat'], farm['lon'],
                  farm['area'], farm['owner'], farm['phone'], farm['email']))
    
    def generate_livestock_readings(self, cursor, days=60):
        """Generate historical health monitoring data"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        readings_per_day = 96  # Every 15 minutes
        
        for device_id in self.device_ids:
            # Determine if this is a cow or sheep
            is_sheep = device_id.startswith('SHEEP')
            
            # Base vitals (different for cows vs sheep)
            base_temp = 38.5 if not is_sheep else 39.0
            base_hr = 70 if not is_sheep else 75
            
            # Simulate gradual health trends
            has_issue = random.random() < 0.2  # 20% chance of health issue
            issue_start = start_date + timedelta(days=random.randint(30, 50)) if has_issue else None
            
            current_date = start_date
            while current_date <= end_date:
                for reading_num in range(readings_per_day):
                    timestamp = int(current_date.timestamp()) + (reading_num * 900)  # 15 min intervals
                    
                    # Check if animal has health issue
                    is_sick = has_issue and issue_start and current_date >= issue_start
                    
                    # Generate realistic vitals
                    if is_sick:
                        temperature = random.gauss(40.5, 0.5)  # Fever
                        heart_rate = int(random.gauss(90, 5))  # Elevated HR
                        motion = random.gauss(0.3, 0.1)  # Low activity
                    else:
                        temperature = random.gauss(base_temp, 0.3)
                        heart_rate = int(random.gauss(base_hr, 5))
                        motion = random.gauss(0.8, 0.2)
                    
                    # Clamp values to realistic ranges
                    temperature = max(37.0, min(42.0, temperature))
                    heart_rate = max(50, min(120, heart_rate))
                    motion = max(0.0, min(2.0, motion))
                    
                    # Add some randomness to location
                    lat = 40.7128 + random.uniform(-0.01, 0.01)
                    lon = -74.0060 + random.uniform(-0.01, 0.01)
                    
                    battery = max(10, 100 - ((end_date - current_date).days * 0.5))
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO livestock_readings
                        (device_id, timestamp, temperature, body_temperature, 
                         heart_rate, motion_magnitude, latitude, longitude, 
                         battery, received_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (device_id, timestamp, temperature, temperature,
                          heart_rate, motion, lat, lon, int(battery),
                          current_date.strftime('%Y-%m-%d %H:%M:%S')))
                
                current_date += timedelta(days=1)
    
    def create_animal_profiles(self, cursor):
        """Create animal profiles with lactation info"""
        for i, device_id in enumerate(self.device_ids):
            if device_id.startswith('COW'):
                # Cows can produce milk
                birth_date = (datetime.now() - timedelta(days=random.randint(800, 2000))).strftime('%Y-%m-%d')
                last_calving = (datetime.now() - timedelta(days=random.randint(30, 250))).strftime('%Y-%m-%d')
                lactation_num = random.randint(1, 4)
                expected_yield = random.uniform(18.0, 28.0)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO animal_profiles
                    (device_id, animal_name, breed, birth_date, lactation_number,
                     last_calving_date, expected_yield_per_day, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (device_id, self.animal_names[i], self.breeds[i % len(self.breeds)],
                      birth_date, lactation_num, last_calving, expected_yield,
                      f"Producing dairy cow - Lactation #{lactation_num}"))
    
    def generate_milk_production(self, cursor, days=90):
        """Generate milk production records"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        for device_id in self.device_ids:
            if not device_id.startswith('COW'):
                continue  # Only cows produce milk
            
            # Get expected yield for this cow
            cursor.execute('SELECT expected_yield_per_day, lactation_number FROM animal_profiles WHERE device_id = ?', 
                          (device_id,))
            result = cursor.fetchone()
            if not result:
                continue
            
            expected_daily = result[0]
            lactation_num = result[1]
            
            # Simulate lactation curve
            current_date = start_date
            while current_date <= end_date:
                # Morning session (usually higher yield)
                morning_yield = random.gauss(expected_daily * 0.55, 1.5)
                morning_yield = max(3.0, min(20.0, morning_yield))
                
                cursor.execute('''
                    INSERT OR IGNORE INTO milk_production
                    (device_id, collection_date, collection_time, yield_liters,
                     fat_percentage, protein_percentage, lactose_percentage,
                     quality_grade, milking_session, recorded_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (device_id, current_date.strftime('%Y-%m-%d'), '06:30:00',
                      round(morning_yield, 2),
                      round(random.gauss(3.5, 0.3), 1),
                      round(random.gauss(3.2, 0.2), 1),
                      round(random.gauss(4.8, 0.2), 1),
                      random.choice(['A+', 'A', 'A', 'B']),  # Mostly good quality
                      'morning', 'demo_generator'))
                
                # Evening session (usually lower yield)
                evening_yield = random.gauss(expected_daily * 0.45, 1.2)
                evening_yield = max(2.0, min(15.0, evening_yield))
                
                cursor.execute('''
                    INSERT OR IGNORE INTO milk_production
                    (device_id, collection_date, collection_time, yield_liters,
                     fat_percentage, protein_percentage, lactose_percentage,
                     quality_grade, milking_session, recorded_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (device_id, current_date.strftime('%Y-%m-%d'), '18:30:00',
                      round(evening_yield, 2),
                      round(random.gauss(3.4, 0.3), 1),
                      round(random.gauss(3.1, 0.2), 1),
                      round(random.gauss(4.7, 0.2), 1),
                      random.choice(['A', 'A', 'B', 'B']),
                      'evening', 'demo_generator'))
                
                current_date += timedelta(days=1)
    
    def assign_animals_to_farms(self, cursor):
        """Assign animals to different farms"""
        # Get farm IDs
        cursor.execute('SELECT id, farm_code FROM farms ORDER BY id')
        farms = cursor.fetchall()
        
        if len(farms) < 2:
            print("   ⚠️  Only one farm exists, all animals assigned to main farm")
            return
        
        # Distribute animals across farms
        farm_assignments = {
            'MAIN': ['COW-001', 'COW-002', 'COW-003'],
            'NORTH-DAIRY': ['COW-004', 'COW-005', 'COW-006'],
            'SOUTH-BREED': ['COW-007', 'COW-008'],
            'EAST-YOUNG': ['COW-009', 'COW-010'],
            'WEST-SHEEP': ['SHEEP-001', 'SHEEP-002', 'SHEEP-003', 'SHEEP-004', 'SHEEP-005']
        }
        
        for farm_id, farm_code in farms:
            animals = farm_assignments.get(farm_code, [])
            for device_id in animals:
                if device_id in self.device_ids:
                    cursor.execute('''
                        INSERT OR REPLACE INTO farm_animals (farm_id, device_id, is_active)
                        VALUES (?, ?, 1)
                    ''', (farm_id, device_id))
    
    def generate_alerts(self, cursor):
        """Generate some sample alerts"""
        alert_data = [
            ('CRITICAL', 'High temperature detected (40.5°C)'),
            ('WARNING', 'Elevated heart rate (88 BPM)'),
            ('WARNING', 'Battery low (15%)'),
            ('INFO', 'Low activity detected')
        ]
        
        # Create a few alerts for demonstration
        for i in range(5):
            device_id = random.choice(self.device_ids)
            alert_type, alert_message = random.choice(alert_data)
            alert_time = datetime.now() - timedelta(hours=random.randint(1, 48))
            
            cursor.execute('''
                INSERT INTO alerts 
                (device_id, alert_type, alert_message, alert_time, resolved)
                VALUES (?, ?, ?, ?, ?)
            ''', (device_id, alert_type, alert_message,
                  alert_time.strftime('%Y-%m-%d %H:%M:%S'),
                  random.choice([0, 0, 1])))  # Most unresolved

    def clear_demo_data(self):
        """Clear all demo data (use with caution!)"""
        print("⚠️  Clearing all data...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM livestock_readings WHERE 1=1')
        cursor.execute('DELETE FROM milk_production WHERE recorded_by = "demo_generator"')
        cursor.execute('DELETE FROM alerts WHERE 1=1')
        cursor.execute('DELETE FROM farm_animals WHERE 1=1')
        cursor.execute('DELETE FROM animal_profiles WHERE 1=1')
        cursor.execute('DELETE FROM farms WHERE farm_code != "MAIN"')
        
        conn.commit()
        conn.close()
        print("✅ Demo data cleared")


def main():
    """Run demo data generation"""
    import sys
    
    generator = DemoDataGenerator()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--clear':
        generator.clear_demo_data()
    else:
        generator.generate_all()
        print("\n🎉 Demo data is ready!")
        print("📊 Visit http://localhost:8000 to see the populated system")
        print("\n💡 To clear demo data, run: python generate_demo_data.py --clear")


if __name__ == '__main__':
    main()
