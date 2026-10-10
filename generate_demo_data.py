"""
Demo Data Generator for Smart Pastoralism System
Generates realistic sample data for testing and demonstration
"""
import sqlite3
import random
from datetime import datetime, timedelta
from app.config import settings

# Base location for all mock data: Guru Nanak University, Ibrahimpatnam, Hyderabad
# (the names CHENNAI_LAT/LON are kept so other scripts that import them keep working)
CHENNAI_LAT = 17.1623
CHENNAI_LON = 78.6586

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
        # Varied health conditions spread across the herd for a rich demo
        # Options: healthy, fever, heat_stress, lethargic, low_battery, recovering
        self.conditions = {
            "COW-001": "healthy",
            "COW-002": "fever",
            "COW-003": "healthy",
            "COW-004": "heat_stress",
            "COW-005": "healthy",
            "COW-006": "lethargic",
            "COW-007": "healthy",
            "COW-008": "recovering",
            "COW-009": "healthy",
            "COW-010": "low_battery",
            "SHEEP-001": "healthy",
            "SHEEP-002": "heat_stress",
            "SHEEP-003": "healthy",
            "SHEEP-004": "fever",
            "SHEEP-005": "healthy",
        }
    
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
                'name': 'Ibrahimpatnam Dairy Farm',
                'location': 'Ibrahimpatnam, Hyderabad',
                'lat': 17.1916,
                'lon': 78.6491,
                'area': 75.5,
                'owner': 'Rajesh Kumar',
                'phone': '+91-98400-10101',
                'email': 'rajesh@ibrahimpatnamdairy.in'
            },
            {
                'code': 'SOUTH-BREED',
                'name': 'Sheriguda Breeding Site',
                'location': 'Sheriguda, Hyderabad',
                'lat': 17.1870,
                'lon': 78.6630,
                'area': 120.0,
                'owner': 'Priya Venkatesan',
                'phone': '+91-98400-10102',
                'email': 'priya@sheridugabreed.in'
            },
            {
                'code': 'EAST-YOUNG',
                'name': 'Adibatla Young Stock',
                'location': 'Adibatla, Hyderabad',
                'lat': 17.2340,
                'lon': 78.5570,
                'area': 45.0,
                'owner': 'Arun Mohan',
                'phone': '+91-98400-10103',
                'email': 'arun@adibatlayoung.in'
            },
            {
                'code': 'WEST-SHEEP',
                'name': 'Turkayamjal Sheep Farm',
                'location': 'Turkayamjal, Hyderabad',
                'lat': 17.2722,
                'lon': 78.5950,
                'area': 90.0,
                'owner': 'Lakshmi Narayanan',
                'phone': '+91-98400-10104',
                'email': 'lakshmi@turkayamjalsheep.in'
            }
        ]

        # Update Main Farm if it exists, otherwise create farms
        cursor.execute("SELECT COUNT(*) FROM farms WHERE farm_code = 'MAIN'")
        if cursor.fetchone()[0] > 0:
            # Update Main Farm
            cursor.execute('''
                UPDATE farms
                SET location = 'Guru Nanak University, Ibrahimpatnam',
                    latitude = 17.1623,
                    longitude = 78.6586,
                    area_hectares = 100.0,
                    owner_name = 'Farm Manager',
                    contact_phone = '+91-98400-10100',
                    contact_email = 'manager@smartstockpulse.in'
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
    
    def _vitals_for(self, condition, base_temp, base_hr, active_issue):
        """Return (temperature, heart_rate, motion, humidity) for a condition.

        active_issue signals whether the animal is currently in its abnormal
        window (so history shows a healthy baseline that trends into the issue).
        """
        humidity = random.gauss(60, 8)

        if not active_issue or condition in ("healthy", "recovering"):
            temperature = random.gauss(base_temp, 0.3)
            heart_rate = int(random.gauss(base_hr, 5))
            motion = random.gauss(0.85, 0.2)
        elif condition == "fever":
            temperature = random.gauss(40.6, 0.4)      # High fever
            heart_rate = int(random.gauss(92, 6))       # Elevated HR
            motion = random.gauss(0.3, 0.1)             # Very low activity
        elif condition == "heat_stress":
            temperature = random.gauss(39.8, 0.3)       # Mildly elevated
            heart_rate = int(random.gauss(88, 6))       # Elevated HR
            motion = random.gauss(0.5, 0.15)            # Reduced activity
            humidity = random.gauss(80, 6)              # Hot/humid
        elif condition == "lethargic":
            temperature = random.gauss(base_temp, 0.3)  # Normal temp
            heart_rate = int(random.gauss(base_hr - 8, 4))  # Low HR
            motion = random.gauss(0.2, 0.08)            # Barely moving
        elif condition == "low_battery":
            temperature = random.gauss(base_temp, 0.35)
            heart_rate = int(random.gauss(base_hr, 6))
            motion = random.gauss(0.8, 0.2)
        else:
            temperature = random.gauss(base_temp, 0.3)
            heart_rate = int(random.gauss(base_hr, 5))
            motion = random.gauss(0.85, 0.2)

        temperature = max(37.0, min(42.0, temperature))
        heart_rate = max(45, min(125, heart_rate))
        motion = max(0.0, min(2.0, motion))
        humidity = max(30.0, min(95.0, humidity))
        return temperature, heart_rate, motion, humidity

    def generate_livestock_readings(self, cursor, days=60):
        """Generate historical health monitoring data with varied conditions"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        readings_per_day = 96  # Every 15 minutes

        for device_id in self.device_ids:
            # Determine if this is a cow or sheep
            is_sheep = device_id.startswith('SHEEP')

            # Base vitals (different for cows vs sheep)
            base_temp = 38.5 if not is_sheep else 39.0
            base_hr = 70 if not is_sheep else 75

            condition = self.conditions.get(device_id, "healthy")
            # The abnormal window starts partway through so history trends in.
            # "recovering" animals were sick and returned to normal recently.
            issue_start = start_date + timedelta(days=random.randint(35, 50))
            recovered_on = end_date - timedelta(days=random.randint(2, 5))

            # Each animal has a home base spread around the demo base (~5 km),
            # so the map shows animals apart and the heatmap shows real density.
            home_lat = CHENNAI_LAT + random.uniform(-0.035, 0.035)
            home_lon = CHENNAI_LON + random.uniform(-0.035, 0.035)

            current_date = start_date
            while current_date <= end_date:
                for reading_num in range(readings_per_day):
                    # Actual moment of this reading (15-min intervals through the day)
                    reading_dt = current_date + timedelta(seconds=reading_num * 900)
                    timestamp = int(reading_dt.timestamp())

                    # Is the animal in its abnormal window right now?
                    if condition == "healthy":
                        active_issue = False
                    elif condition == "recovering":
                        # abnormal between issue_start and recovered_on, then healthy
                        active_issue = issue_start <= current_date <= recovered_on
                        eff_condition = "fever"
                    else:
                        active_issue = current_date >= issue_start
                        eff_condition = condition

                    cond_for_vitals = eff_condition if condition != "healthy" else "healthy"
                    temperature, heart_rate, motion, humidity = self._vitals_for(
                        cond_for_vitals, base_temp, base_hr, active_issue
                    )

                    # Animal grazes around its home base (~300 m wander)
                    lat = home_lat + random.uniform(-0.003, 0.003)
                    lon = home_lon + random.uniform(-0.003, 0.003)

                    # Battery: low_battery devices drain faster and sit low
                    if condition == "low_battery":
                        battery = max(6, 45 - ((end_date - current_date).days * 0.4))
                    else:
                        battery = max(20, 100 - ((end_date - current_date).days * 0.5))
                    ambient = random.gauss(28 if condition == "heat_stress" else 24, 3)

                    cursor.execute('''
                        INSERT OR IGNORE INTO livestock_readings
                        (device_id, timestamp, temperature, body_temperature,
                         heart_rate, motion_magnitude, latitude, longitude,
                         battery, humidity, ambient_temperature, received_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (device_id, timestamp, temperature, temperature,
                          heart_rate, motion, lat, lon, int(battery),
                          round(humidity, 1), round(ambient, 1),
                          reading_dt.strftime('%Y-%m-%d %H:%M:%S')))

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
        """Generate sample alerts that match each animal's actual condition"""
        # Condition-driven alerts so the alert feed reflects the herd's state
        condition_alerts = {
            "fever": ('CRITICAL', 'High temperature detected (40.6°C)', 40.6, 92),
            "heat_stress": ('WARNING', 'Heat stress: elevated temp & humidity', 39.8, 88),
            "lethargic": ('WARNING', 'Low activity / lethargy detected', 38.5, 62),
            "low_battery": ('WARNING', 'Collar battery low (12%)', 38.5, 70),
            "recovering": ('INFO', 'Animal recovering — vitals normalizing', 38.9, 74),
        }

        for device_id, condition in self.conditions.items():
            if condition not in condition_alerts:
                continue
            alert_type, message, temp, hr = condition_alerts[condition]
            # Recent alert time, spread over the last two days
            alert_time = datetime.now() - timedelta(hours=random.randint(1, 40))
            resolved = 1 if condition == "recovering" else 0
            battery = 12 if condition == "low_battery" else random.randint(55, 95)
            lat = CHENNAI_LAT + random.uniform(-0.03, 0.03)
            lon = CHENNAI_LON + random.uniform(-0.03, 0.03)

            cursor.execute('''
                INSERT INTO alerts
                (device_id, alert_type, alert_message, alert_time, resolved,
                 temperature, heart_rate, battery, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (device_id, alert_type, message,
                  alert_time.strftime('%Y-%m-%d %H:%M:%S'), resolved,
                  temp, hr, battery, lat, lon))

    def clear_demo_data(self):
        """Clear ALL mock data for a clean slate (use with caution!)"""
        print("⚠️  Clearing all data...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Wipe everything so no stale/inconsistent device IDs remain
        cursor.execute('DELETE FROM livestock_readings')
        cursor.execute('DELETE FROM milk_production')
        cursor.execute('DELETE FROM alerts')
        cursor.execute('DELETE FROM farm_animals')
        cursor.execute('DELETE FROM animal_profiles')
        cursor.execute('DELETE FROM farms WHERE farm_code != "MAIN"')
        # Optional tables that may hold demo rows
        for tbl in ('geofence_violations', 'notification_log'):
            try:
                cursor.execute(f'DELETE FROM {tbl}')
            except sqlite3.OperationalError:
                pass

        conn.commit()
        conn.close()
        print("✅ All mock data cleared")


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
