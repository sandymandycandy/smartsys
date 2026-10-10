#!/usr/bin/env python3
"""
Smart Pastoralism - Complete Gateway with Detailed MPU6050 Analysis
Final Version with All Improvements (RPi 5 Compatible)
"""

import spidev
from gpiozero import DigitalOutputDevice
import time
import sqlite3
import math
import json
import os
import urllib.request
from datetime import datetime, timedelta

# ===== CONFIGURATION =====
DB_NAME = 'livestock_data.db'

# Pin configuration
RST_PIN = 25
# DIO0_PIN = 24  # Not used in polling mode
CS_PIN = 8

# SX1276/78 Registers
REG_FIFO = 0x00
REG_OP_MODE = 0x01
REG_LNA = 0x0C
REG_FRF_MSB = 0x06
REG_FRF_MID = 0x07
REG_FRF_LSB = 0x08
REG_FIFO_ADDR_PTR = 0x0D
REG_FIFO_RX_BASE = 0x0F
REG_FIFO_RX_CURRENT_ADDR = 0x10
REG_IRQ_FLAGS = 0x12
REG_RX_NB_BYTES = 0x13
REG_PKT_RSSI_VALUE = 0x1A
REG_PKT_SNR_VALUE = 0x1B
REG_MODEM_CONFIG_1 = 0x1D
REG_MODEM_CONFIG_2 = 0x1E
REG_MODEM_CONFIG_3 = 0x26
REG_DIO_MAPPING_1 = 0x40
REG_VERSION = 0x42

# Modes
MODE_SLEEP = 0x00
MODE_RXCONT = 0x05
LORA_MODE = 0x80

# Anomaly thresholds (Optimized)
TEMP_NORMAL_RANGE = (37.5, 39.5)  # Cattle body temp
HUMIDITY_HIGH = 85.0  # Ambient humidity threshold
HR_NORMAL_RANGE = (40, 80)  # Resting cattle heart rate
MOTION_LOW_THRESHOLD = 0.5  # g-force
MOTION_HIGH_THRESHOLD = 2.0  # g-force
BATTERY_LOW = 20  # percentage

# Location used when a collar has no GPS fix. Set GATEWAY_LAT / GATEWAY_LON
# to pin it; otherwise it is looked up once from the gateway's IP address.
GATEWAY_LAT = os.getenv("GATEWAY_LAT")
GATEWAY_LON = os.getenv("GATEWAY_LON")


def get_gateway_location():
    """Return (lat, lon) of the gateway, or None if unknown"""
    if GATEWAY_LAT and GATEWAY_LON:
        return float(GATEWAY_LAT), float(GATEWAY_LON)
    try:
        with urllib.request.urlopen("http://ip-api.com/json/?fields=status,lat,lon", timeout=5) as r:
            loc = json.loads(r.read().decode())
        if loc.get("status") == "success":
            return float(loc["lat"]), float(loc["lon"])
    except Exception:
        pass
    return None

class LivestockGateway:
    def __init__(self):
        self.packet_count = 0
        self.anomaly_count = 0
        self.parse_errors = 0
        self.last_packet_time = None
        
        # Setup GPIO using gpiozero (Pi 5 compatible)
        # RST Pin (Active Low) - Start High (Not Reset)
        try:
            self.rst = DigitalOutputDevice(RST_PIN, active_high=True, initial_value=True)
        except Exception as e:
            print(f"⚠️  GPIO Warning: {e}")
            print("   Ensure you are running on a Raspberry Pi with gpiozero installed.")
        
        # Setup SPI
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 5000000
        
        self.init_lora()
        self.init_database()
        self.gateway_location = get_gateway_location()
        self.print_header()
    
    def write_reg(self, addr, value):
        """Write to register"""
        self.spi.xfer2([addr | 0x80, value])
    
    def read_reg(self, addr):
        """Read from register"""
        return self.spi.xfer2([addr & 0x7F, 0x00])[1]
    
    def init_lora(self):
        """Initialize LoRa module"""
        print("🔧 Initializing LoRa module...")
        
        # Hardware reset with longer timing
        if hasattr(self, 'rst'):
            self.rst.off()  # Pull Low (Reset)
            time.sleep(0.1)
            self.rst.on()   # Pull High (Release)
            time.sleep(0.2) # Wait for module to fully initialize
        
        # Check version with retries
        max_retries = 3
        version = 0x00
        for i in range(max_retries):
            version = self.read_reg(REG_VERSION)
            if version == 0x12:
                break
            print(f"   ⚠️  Attempt {i+1}: Got version 0x{version:02X}, retrying...")
            time.sleep(0.1)
        
        if version != 0x12:
            raise Exception(f"Invalid module version: 0x{version:02X} (after {max_retries} attempts)")
        print(f"   ✓ Module version: 0x{version:02X}")
        
        # Sleep mode
        self.write_reg(REG_OP_MODE, MODE_SLEEP | LORA_MODE)
        time.sleep(0.01)
        
        # Frequency: 433 MHz
        frf = int((433.0 * 524288) / 32.0)
        self.write_reg(REG_FRF_MSB, (frf >> 16) & 0xFF)
        self.write_reg(REG_FRF_MID, (frf >> 8) & 0xFF)
        self.write_reg(REG_FRF_LSB, frf & 0xFF)
        print("   ✓ Frequency: 433 MHz")
        
        # BW: 125kHz, CR: 4/5
        self.write_reg(REG_MODEM_CONFIG_1, 0x72)
        print("   ✓ Bandwidth: 125 kHz, Coding Rate: 4/5")
        
        # SF: 12, CRC: enabled
        self.write_reg(REG_MODEM_CONFIG_2, 0xC4)
        print("   ✓ Spreading Factor: 12, CRC: enabled")
        
        # Low data rate optimization
        self.write_reg(REG_MODEM_CONFIG_3, 0x0C)
        print("   ✓ Low data rate optimization: ON")

        # LNA: max gain + boost (same as Arduino LoRa library)
        self.write_reg(REG_LNA, 0x23)
        print("   ✓ LNA boost: ON")
        
        # Sync word
        self.write_reg(0x39, 0x12)
        print("   ✓ Sync word: 0x12")
        
        # FIFO
        self.write_reg(REG_FIFO_RX_BASE, 0x00)
        
        # DIO mapping
        self.write_reg(REG_DIO_MAPPING_1, 0x00)
        
        print("✅ LoRa initialization complete\n")
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS livestock_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT, latitude REAL, longitude REAL, satellites INTEGER,
            temperature REAL, ambient_temperature REAL, body_temperature REAL, humidity REAL, heart_rate INTEGER,
            accel_x REAL, accel_y REAL, accel_z REAL,
            gyro_x REAL, gyro_y REAL, gyro_z REAL,
            motion_magnitude REAL, rotation_speed REAL,
            battery INTEGER, rssi INTEGER, snr REAL,
            timestamp INTEGER, received_time TEXT, anomaly_detected INTEGER DEFAULT 0
        )''')
        
        # Migration: Add new columns if they don't exist
        try:
            cursor.execute('ALTER TABLE livestock_readings ADD COLUMN ambient_temperature REAL')
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute('ALTER TABLE livestock_readings ADD COLUMN body_temperature REAL')
        except sqlite3.OperationalError:
            pass
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT, alert_time TEXT, alert_type TEXT,
            alert_message TEXT, latitude REAL, longitude REAL, resolved INTEGER DEFAULT 0
        )''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized\n")
    
    def print_header(self):
        """Print header"""
        print("=" * 75)
        print("  🐄 SMART PASTORALISM - FINAL RASPBERRY PI GATEWAY")
        print("=" * 75)
        print(f"  Frequency:        433 MHz")
        print(f"  Spreading Factor: 12")
        print(f"  Bandwidth:        125 kHz")
        print(f"  Packet Format:    START:data:END")
        print(f"  Database:         {DB_NAME}")
        print(f"  Started:          {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 75 + "\n")
    
    def start_rx(self):
        """Start continuous receive"""
        self.write_reg(REG_FIFO_ADDR_PTR, 0x00)
        self.write_reg(REG_OP_MODE, MODE_RXCONT | LORA_MODE)
    
    def check_packet(self):
        """Check for received packet with proper FIFO management"""
        irq = self.read_reg(REG_IRQ_FLAGS)
        
        if irq & 0x40:  # RxDone
            time.sleep(0.005)

            # Drop packets that failed the CRC check (corrupted over the air)
            if irq & 0x20:
                print("   ⚠️  CRC error - packet dropped")
                self.write_reg(REG_IRQ_FLAGS, 0xFF)
                self.write_reg(REG_FIFO_ADDR_PTR, 0x00)
                return None, None, None

            # Get packet info
            current_addr = self.read_reg(REG_FIFO_RX_CURRENT_ADDR)
            length = self.read_reg(REG_RX_NB_BYTES)
            
            # Validate length
            if length == 0 or length > 255:
                self.write_reg(REG_IRQ_FLAGS, 0xFF)
                self.write_reg(REG_FIFO_ADDR_PTR, 0x00)
                return None, None, None
            
            # Set FIFO pointer
            self.write_reg(REG_FIFO_ADDR_PTR, current_addr)
            
            # Read payload
            payload = []
            for i in range(length):
                payload.append(self.read_reg(REG_FIFO))
            
            # Get signal info
            rssi = self.read_reg(REG_PKT_RSSI_VALUE) - 164  # 164 for 433 MHz (LF port)
            snr_raw = self.read_reg(REG_PKT_SNR_VALUE)
            snr = snr_raw / 4.0 if snr_raw < 128 else (snr_raw - 256) / 4.0
            
            # Clear ALL IRQ flags
            self.write_reg(REG_IRQ_FLAGS, 0xFF)
            
            # PROPER FIFO RESET - Go to standby, reset FIFO, back to RX
            self.write_reg(REG_OP_MODE, MODE_SLEEP | LORA_MODE)
            time.sleep(0.01)
            
            # Reset FIFO pointers
            self.write_reg(REG_FIFO_ADDR_PTR, 0x00)
            self.write_reg(REG_FIFO_RX_BASE, 0x00)
            
            # Back to RX mode
            self.write_reg(REG_OP_MODE, MODE_RXCONT | LORA_MODE)
            time.sleep(0.01)
            
            return payload, rssi, snr
        
        return None, None, None
    
    def parse_packet(self, payload):
        """Parse packet with START:END delimiter support (Robust v4)"""
        data_str_raw = ""
        try:
            # Convert to string, cleaning out non-printable chars
            data_str = ''.join([chr(b) for b in payload if 32 <= b < 127])
            data_str = data_str.strip()
            data_str_raw = data_str
            
            if not data_str:
                raise ValueError("Packet is empty or non-printable")

            # Find START and END markers
            start_marker = 'START:'
            end_marker = ':END'
            
            # Handle concatenated packets: ":ENDSTART:"
            if ':ENDSTART:' in data_str:
                # Split at the boundary
                parts = data_str.split(':ENDSTART:')
                # Take the second part (new packet) if it exists and looks complete
                if len(parts) > 1 and len(parts[1]) > 50:
                    data_str = start_marker + parts[1]
                    print(f"   ⚠️  Split concatenated packet, using newer one")
                else:
                    # Use the first part (old packet)
                    data_str = parts[0]
                    if not data_str.startswith(start_marker):
                        data_str = start_marker + data_str
                    if not data_str.endswith(end_marker):
                        data_str = data_str + end_marker
                    print(f"   ⚠️  Split concatenated packet, using older one")
            
            # Find the *last* start marker (handles concatenated packets)
            start_idx = data_str.rfind(start_marker)
            if start_idx == -1:
                raise ValueError(f"No '{start_marker}' marker found")

            # Find the *next* END marker *after* START
            end_idx = data_str.find(end_marker, start_idx)
            if end_idx == -1:
                # No END found - check if we have enough data
                temp_str = data_str[start_idx + len(start_marker):]
                if len(temp_str) > 70:  # Full packet is ~90 chars
                    # Assume END is missing, use what we have
                    data_str = temp_str
                    print(f"   ⚠️  No END marker, using available data")
                else:
                    raise ValueError(f"No '{end_marker}' marker found after 'START:'")
            else:
                # Extract clean data between markers
                data_str = data_str[start_idx + len(start_marker) : end_idx]
                print(f"   ✓ Found delimiters, extracted: {data_str[:60]}...")
            
            # Clean up any nested delimiters
            data_str = data_str.replace(start_marker, '').replace(end_marker, '')

            # Parse CSV fields
            parts = data_str.split(',')
            
            # Check field count
            expected_fields = 16
            if len(parts) < expected_fields:
                raise ValueError(f"Too few fields: {len(parts)} (need {expected_fields})")
            
            # Safe parsing with validation
            device_id = parts[0].strip()
            if not device_id.startswith('COW'):
                raise ValueError("Invalid Device ID (missing 'COW' prefix)")
            
            return {
                'device_id': device_id,
                'latitude': self._safe_float(parts[1], 0.0),
                'longitude': self._safe_float(parts[2], 0.0),
                'satellites': self._safe_int(parts[3], 0),
                'ambient_temperature': self._safe_float(parts[4], 0.0),
                'humidity': self._safe_float(parts[5], 0.0),
                'body_temperature': self._safe_float(parts[6], 0.0),
                'heart_rate': self._safe_int(parts[7], 0),
                'accel_x': self._safe_float(parts[8], 0.0),
                'accel_y': self._safe_float(parts[9], 0.0),
                'accel_z': self._safe_float(parts[10], 0.0),
                'gyro_x': self._safe_float(parts[11], 0.0),
                'gyro_y': self._safe_float(parts[12], 0.0),
                'gyro_z': self._safe_float(parts[13], 0.0),
                'battery': self._safe_int(parts[14], 0),
                'timestamp': self._safe_int(parts[15], int(time.time() * 1000)),
                'received_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise ValueError(f"{e} | Raw: {data_str_raw[:100]}")
    
    def _safe_float(self, value, default=0.0):
        """Safely convert to float"""
        try:
            cleaned = ''.join([c for c in str(value) if c.isdigit() or c in '.-'])
            if not cleaned or cleaned in ('-', '.', '-.'):
                return default
            return float(cleaned)
        except:
            return default
    
    def _safe_int(self, value, default=0):
        """Safely convert to int"""
        try:
            cleaned = ''.join([c for c in str(value) if c.isdigit() or c == '-'])
            if not cleaned or cleaned == '-':
                return default
            # Remove any trailing text
            for split_char in ['C', 'O', 'W', 'S', 'T', 'A', 'R', 'E', 'N', 'D']:
                if split_char in cleaned:
                    cleaned = cleaned.split(split_char)[0]
                    if not cleaned:
                        return default
            return int(cleaned)
        except:
            return default
    
    def display_data(self, d, rssi, snr):
        """Display received data with DETAILED MPU6050 analysis"""
        self.packet_count += 1
        
        print("\n" + "┌" + "─" * 73 + "┐")
        print(f"│ 📦 PACKET #{self.packet_count}")
        print(f"│ ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"│ 📶 RSSI: {rssi} dBm, SNR: {snr:.1f} dB")
        print("└" + "─" * 73 + "┘")
        
        print(f"\n📋 LIVESTOCK DATA - Device: {d['device_id']}")
        print("═" * 73)
        
        # GPS Location
        print(f"\n📍 GPS LOCATION")
        print("─" * 73)
        if d['latitude'] != 0.0:
            print(f"   Latitude:     {d['latitude']:.6f}°")
            print(f"   Longitude:    {d['longitude']:.6f}°")
            print(f"   Satellites:   {d['satellites']}")
            print(f"   Google Maps:  http://maps.google.com/maps?q={d['latitude']},{d['longitude']}")
        else:
            print(f"   Status:       No GPS fix (Normal indoors)")
            print(f"   Satellites:   {d['satellites']}")
        
        # Environmental Sensors
        print(f"\n🌡️  TEMPERATURE SENSORS")
        print("─" * 73)
        
        # Ambient (DHT11)
        print(f"   Ambient Temp: {d['ambient_temperature']:.1f}°C", end="")
        if d['ambient_temperature'] > 35:
            print(" ⚠️ (High - Heat stress risk)")
        else:
            print(" (DHT11)")

        # Body (DS18B20)
        print(f"   Body Temp:    {d['body_temperature']:.1f}°C", end="")
        if d['body_temperature'] == 0:
            print(" (Sensor error)")
        elif TEMP_NORMAL_RANGE[0] <= d['body_temperature'] <= TEMP_NORMAL_RANGE[1]:
            print(" ✓ (Normal)")
        else:
            print(" ⚠️ (Abnormal)")
        
        print(f"   Humidity:     {d['humidity']:.1f}%", end="")
        print(" ✓" if d['humidity'] < HUMIDITY_HIGH else " ⚠️ (High - Heat stress risk)")
        
        # Heart Rate
        print(f"\n❤️  HEART RATE")
        print("─" * 73)
        print(f"   BPM:          {d['heart_rate']}", end="")
        if d['heart_rate'] == 0:
            print(" (No signal detected)")
        elif d['heart_rate'] < HR_NORMAL_RANGE[0]:
            print(" ⚠️ (LOW - Bradycardia)")
        elif d['heart_rate'] > HR_NORMAL_RANGE[1]:
            print(" ⚠️ (HIGH - Tachycardia/Stress)")
        else:
            print(" ✓ (Normal range for cattle)")
        
        # ========================================
        # DETAILED MPU6050 ANALYSIS
        # ========================================
        
        print(f"\n📊 MPU6050 - COMPLETE 6-AXIS IMU ANALYSIS")
        print("═" * 73)
        
        # RAW ACCELEROMETER DATA
        print(f"\n🔵 ACCELEROMETER (3-Axis Linear Acceleration)")
        print("─" * 73)
        print(f"   X-axis:       {d['accel_x']:+.3f} g   ", end="")
        if abs(d['accel_x']) < 0.1:
            print("(Minimal X movement)")
        elif abs(d['accel_x']) > 0.5:
            print("(Strong X movement)")
        else:
            print("(Moderate X movement)")
        
        print(f"   Y-axis:       {d['accel_y']:+.3f} g   ", end="")
        if abs(d['accel_y']) < 0.1:
            print("(Minimal Y movement)")
        elif abs(d['accel_y']) > 0.5:
            print("(Strong Y movement)")
        else:
            print("(Moderate Y movement)")
        
        print(f"   Z-axis:       {d['accel_z']:+.3f} g   ", end="")
        if abs(d['accel_z']) > 0.85:
            print("(Vertical orientation - Gravity)")
        elif abs(d['accel_z']) < 0.3:
            print("(Horizontal orientation)")
        else:
            print("(Tilted position)")
        
        # Calculate total acceleration magnitude
        motion = math.sqrt(d['accel_x']**2 + d['accel_y']**2 + d['accel_z']**2)
        print(f"\n   📐 Vector Magnitude: {motion:.3f} g")
        
        # Calculate tilt angles
        roll = 0.0
        pitch = 0.0
        try:
            if d['accel_z'] != 0.0:
                roll = math.atan2(d['accel_y'], d['accel_z']) * 180 / math.pi
            if math.sqrt(d['accel_y']**2 + d['accel_z']**2) != 0.0:
                pitch = math.atan2(-d['accel_x'], math.sqrt(d['accel_y']**2 + d['accel_z']**2)) * 180 / math.pi
        except ValueError:
            pass
        
        print(f"   📐 Roll Angle:       {roll:+.1f}°")
        print(f"   📐 Pitch Angle:      {pitch:+.1f}°")
        
        # Activity classification
        print(f"\n   🎯 Activity Analysis:")
        if abs(d['accel_z']) > 0.85 and motion < 1.2:
            activity = "LYING DOWN 🛏️"
            print(f"      Status: {activity}")
            print(f"      Reason: Z-axis dominance (gravity aligned)")
        elif motion < MOTION_LOW_THRESHOLD:
            activity = "VERY LOW ACTIVITY 😴"
            print(f"      Status: {activity}")
            print(f"      Reason: Minimal motion detected")
            print(f"      Alert:  Possible resting or illness")
        elif motion > MOTION_HIGH_THRESHOLD:
            activity = "HIGH ACTIVITY 🏃"
            print(f"      Status: {activity}")
            print(f"      Reason: Strong motion detected")
            print(f"      Alert:  Running, jumping, or stress")
        else:
            activity = "NORMAL ACTIVITY 🚶"
            print(f"      Status: {activity}")
            print(f"      Reason: Moderate motion patterns")
            print(f"      Note:   Typical grazing/walking behavior")
        
        # RAW GYROSCOPE DATA
        print(f"\n🔴 GYROSCOPE (3-Axis Angular Velocity)")
        print("─" * 73)
        print(f"   X-axis (Roll):  {d['gyro_x']:+.2f} °/s   ", end="")
        if abs(d['gyro_x']) < 5:
            print("(Stable)")
        elif abs(d['gyro_x']) < 30:
            print("(Slow rotation)")
        else:
            print("(Fast rotation)")
        
        print(f"   Y-axis (Pitch): {d['gyro_y']:+.2f} °/s   ", end="")
        if abs(d['gyro_y']) < 5:
            print("(Stable)")
        elif abs(d['gyro_y']) < 30:
            print("(Slow rotation)")
        else:
            print("(Fast rotation)")
        
        print(f"   Z-axis (Yaw):   {d['gyro_z']:+.2f} °/s   ", end="")
        if abs(d['gyro_z']) < 5:
            print("(Stable)")
        elif abs(d['gyro_z']) < 30:
            print("(Slow rotation)")
        else:
            print("(Fast rotation)")
        
        # Calculate total rotation rate
        rotation = math.sqrt(d['gyro_x']**2 + d['gyro_y']**2 + d['gyro_z']**2)
        print(f"\n   📐 Vector Magnitude: {rotation:.2f} °/s")
        
        # Rotation interpretation
        print(f"\n   🎯 Rotation Analysis:")
        if rotation < 5:
            print(f"      Status: STABLE 🟢")
            print(f"      Reason: Minimal rotation detected")
            print(f"      Note:   Animal is stationary or moving steadily")
        elif rotation < 30:
            print(f"      Status: MODERATE ROTATION 🟡")
            print(f"      Reason: Normal head/body movements")
            print(f"      Note:   Typical for grazing or walking")
        elif rotation < 100:
            print(f"      Status: HIGH ROTATION 🟠")
            print(f"      Reason: Active head movements or turning")
            print(f"      Note:   May indicate alert behavior")
        else:
            print(f"      Status: VERY HIGH ROTATION 🔴")
            print(f"      Reason: Rapid spinning or falling")
            print(f"      Alert:  POSSIBLE DISTRESS OR FALL!")
        
        # ORIENTATION & POSTURE ANALYSIS
        print(f"\n🎯 ORIENTATION & POSTURE ANALYSIS")
        print("─" * 73)
        
        # Determine primary orientation
        if abs(d['accel_z']) > 0.85:
            if d['accel_z'] > 0:
                orientation = "UPRIGHT 🟢"
                posture = "Standing normally or lying on side"
            else:
                orientation = "INVERTED 🔴"
                posture = "ALERT: Upside down! Possible fall or distress"
        elif abs(d['accel_x']) > 0.7:
            orientation = "TILTED (X-axis) 🟡"
            posture = "Leaning sideways or head lowered"
        elif abs(d['accel_y']) > 0.7:
            orientation = "TILTED (Y-axis) 🟡"
            posture = "Head up/down position"
        else:
            orientation = "UNUSUAL 🟠"
            posture = "Non-standard position - monitor closely"
        
        print(f"   Primary Axis:     {orientation}")
        print(f"   Posture:          {posture}")
        
        # Movement pattern
        if motion < 0.3 and rotation < 5:
            movement = "STATIONARY"
        elif motion < 1.0 and rotation < 30:
            movement = "CALM MOVEMENT"
        elif motion < 2.0 or rotation < 100:
            movement = "ACTIVE MOVEMENT"
        else:
            movement = "VIGOROUS MOVEMENT"
        print(f"   Movement Pattern: {movement}")
        
        # COMBINED HEALTH INDICATORS
        print(f"\n🏥 COMBINED HEALTH INDICATORS")
        print("─" * 73)
        
        # Check for concerning patterns
        concerns = []
        
        if motion < 0.3 and rotation < 5:
            concerns.append("⚠️  Extended period of no movement")
        
        if rotation > 100:
            concerns.append("⚠️  Excessive rotation - possible distress")
        
        if abs(d['accel_z']) < 0.3 and motion < 0.5:
            concerns.append("⚠️  Horizontal position with low motion")
        
        if d['accel_z'] < -0.85:
            concerns.append("🚨 CRITICAL: Inverted position detected!")
        
        if concerns:
            print("   Status: ALERTS DETECTED")
            for concern in concerns:
                print(f"   {concern}")
        else:
            print("   Status: ✓ All motion parameters normal")
        
        # Battery
        print(f"\n🔋 BATTERY STATUS")
        print("─" * 73)
        print(f"   Level:        {d['battery']}%", end="")
        if d['battery'] == 0:
            print(" ⚠️ (Check battery circuit)")
        elif d['battery'] < 10:
            print(" 🚨 CRITICAL")
        elif d['battery'] < 20:
            print(" ⚠️ LOW")
        elif d['battery'] < 50:
            print(" 🟡 Medium")
        else:
            print(" ✓ Good")
        
        print("\n" + "═" * 73)
    
    def save_to_database(self, data, rssi, snr):
        """Save to database and send to FastAPI dashboard with retry logic"""
        motion = math.sqrt(data['accel_x']**2 + data['accel_y']**2 + data['accel_z']**2)
        rotation = math.sqrt(data['gyro_x']**2 + data['gyro_y']**2 + data['gyro_z']**2)
        
        # Retry logic for database locks (WAL mode helps, but still need retries)
        max_retries = 3
        retry_delay = 0.1
        
        # Save to local database AND send to API for redundancy
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(DB_NAME, timeout=5.0)
                conn.execute('PRAGMA journal_mode=WAL')
                cursor = conn.cursor()
                
                cursor.execute('''INSERT INTO livestock_readings 
                    (device_id, latitude, longitude, satellites, temperature, ambient_temperature, body_temperature, humidity, heart_rate,
                     accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z,
                     motion_magnitude, rotation_speed, battery, rssi, snr, timestamp, received_time)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (data['device_id'], data['latitude'], data['longitude'], data['satellites'],
                     data['body_temperature'], data['ambient_temperature'], data['body_temperature'], data['humidity'], data['heart_rate'],
                     data['accel_x'], data['accel_y'], data['accel_z'],
                     data['gyro_x'], data['gyro_y'], data['gyro_z'],
                     motion, rotation, data['battery'], rssi, snr,
                     data['timestamp'], data['received_time']))
                
                conn.commit()
                record_id = cursor.lastrowid
                conn.close()
                
                print(f"\n💾 Saved to database (ID: {record_id})")
                break  # Success, exit retry loop
                
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    print(f"⚠️  Database locked, retry {attempt + 1}/{max_retries}...")
                    time.sleep(0.1)
                else:
                    print(f"❌ Database error: {e}")
                    break
            except Exception as e:
                print(f"❌ Unexpected error saving to DB: {e}")
                break

        # No HTTP post to the dashboard: its LoRa monitor reads new rows from this
        # DB and broadcasts them. Posting as well saved every packet twice.

    def detect_anomalies(self, d):
        """Detect anomalies with improved logic"""
        anomalies = []
        
        # Temperature anomalies (Body)
        if d['body_temperature'] > 0:
            if d['body_temperature'] < 36.0:
                anomalies.append(f"🥶 HYPOTHERMIA: {d['body_temperature']:.1f}°C")
            elif d['body_temperature'] > TEMP_NORMAL_RANGE[1]:
                anomalies.append(f"🤒 FEVER: {d['body_temperature']:.1f}°C")
        
        # Humidity (only flag if very high)
        if d['humidity'] > HUMIDITY_HIGH + 5:
            anomalies.append(f"💧 VERY HIGH HUMIDITY: {d['humidity']:.1f}%")
        
        # Heart Rate
        if d['heart_rate'] > 0:
            if d['heart_rate'] < HR_NORMAL_RANGE[0]:
                anomalies.append(f"💔 LOW HR: {d['heart_rate']} BPM")
            elif d['heart_rate'] > HR_NORMAL_RANGE[1]:
                anomalies.append(f"💓 HIGH HR: {d['heart_rate']} BPM")
        
        # Motion
        motion = math.sqrt(d['accel_x']**2 + d['accel_y']**2 + d['accel_z']**2)
        if motion < MOTION_LOW_THRESHOLD:
            anomalies.append(f"😴 LOW ACTIVITY: {motion:.2f}g")
        elif motion > MOTION_HIGH_THRESHOLD:
            anomalies.append(f"🏃 HIGH ACTIVITY: {motion:.2f}g")
        
        # Battery
        if 0 < d['battery'] < BATTERY_LOW:
            anomalies.append(f"🔋 LOW BATTERY: {d['battery']}%")
        
        # Save anomalies to database
        if anomalies:
            self.anomaly_count += 1
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('UPDATE livestock_readings SET anomaly_detected=1 WHERE device_id=? AND timestamp=?',
                         (d['device_id'], d['timestamp']))
            
            for anomaly in anomalies:
                alert_type = anomaly.split(':')[0].strip()
                
                # Check for ANY existing alert of same type (Resolved or Not) to prevent spam
                cursor.execute('SELECT id, resolved, alert_time FROM alerts WHERE device_id=? AND alert_type=? ORDER BY id DESC LIMIT 1', 
                             (d['device_id'], alert_type))
                existing = cursor.fetchone()
                
                if existing:
                    eid, resolved, etime = existing
                    if resolved == 0:
                        # Unresolved: Just update timestamp
                        cursor.execute('UPDATE alerts SET alert_time=?, alert_message=?, latitude=?, longitude=? WHERE id=?',
                                     (datetime.now().isoformat(), anomaly, d['latitude'], d['longitude'], eid))
                    else:
                        # Resolved: Check cooldown (30 min)
                        try:
                            last_time = datetime.fromisoformat(etime)
                            if datetime.now() - last_time < timedelta(minutes=60):
                                print(f"   💤 Snoozing resolved alert: {alert_type}")
                                continue
                        except ValueError:
                            pass # If time parsing fails, create new
                        
                        # Created > 30 mins ago: Re-create
                        cursor.execute('INSERT INTO alerts (device_id, alert_time, alert_type, alert_message, latitude, longitude) VALUES (?,?,?,?,?,?)',
                                     (d['device_id'], datetime.now().isoformat(), alert_type, anomaly, d['latitude'], d['longitude']))
                else:
                    # New alert
                    cursor.execute('INSERT INTO alerts (device_id, alert_time, alert_type, alert_message, latitude, longitude) VALUES (?,?,?,?,?,?)',
                                 (d['device_id'], datetime.now().isoformat(), alert_type, anomaly, d['latitude'], d['longitude']))
            
            conn.commit()
            conn.close()
        
        return anomalies
    
    def print_alerts(self, anomalies):
        """Print alerts"""
        print("\n⚠️  ALERTS:")
        for i, a in enumerate(anomalies, 1):
            print(f"  {i}. {a}")
    
    def run(self):
        """Main loop"""
        self.start_rx()
        
        print("🎧 Listening for packets...")
        print("   Press Ctrl+C to stop\n")
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        try:
            while True:
                payload, rssi, snr = self.check_packet()
                
                if payload:
                    try:
                        data = self.parse_packet(payload)
                        # No GPS fix: use the gateway's location (satellites stays 0)
                        if data['latitude'] == 0.0 and data['longitude'] == 0.0 and self.gateway_location:
                            data['latitude'], data['longitude'] = self.gateway_location
                        self.display_data(data, rssi, snr)
                        self.save_to_database(data, rssi, snr)
                        
                        anomalies = self.detect_anomalies(data)
                        if anomalies:
                            self.print_alerts(anomalies)
                        else:
                            print("\n✅ All parameters normal")
                        
                        print(f"\n📊 Session Stats: {self.packet_count} packets | {self.anomaly_count} anomalies | {self.parse_errors} parse errors")
                        print("─" * 75)
                        
                        # Reset error counter on success
                        consecutive_errors = 0
                        
                        # LONGER delay after successful packet to allow FIFO to clear
                        time.sleep(0.1)
                    
                    except Exception as e:
                        self.parse_errors += 1
                        print(f"   ❌ Parse Error: {e}")
                        consecutive_errors += 1
                
                else:
                    # No packet
                    time.sleep(0.01)
                
                # Watchdog / Error recovery
                if consecutive_errors > max_consecutive_errors:
                    print("   ⚠️  Too many errors, resetting LoRa module...")
                    self.init_lora()
                    self.start_rx()
                    consecutive_errors = 0
                    
        except KeyboardInterrupt:
            print("\n🛑 Stopped by user")
        finally:
            self.spi.close()
            if hasattr(self, 'rst'):
                self.rst.close()
            print("👋 Bye!")

if __name__ == "__main__":
    gateway = LivestockGateway()
    gateway.run()