"""
Weather Service for weather data integration
Uses OpenWeatherMap API to fetch current weather and forecasts
"""
import sqlite3
import os
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import urllib.request
import urllib.error

try:
    from app.config import settings
except:
    from config import settings

# Database path
DB_PATH = os.path.join(os.path.dirname(settings.LORA_DB_PATH), "weather.db")

def init_weather_db():
    """Initialize the weather database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Weather data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL,
            feels_like REAL,
            humidity INTEGER,
            pressure INTEGER,
            wind_speed REAL,
            wind_direction INTEGER,
            clouds INTEGER,
            weather_main TEXT,
            weather_description TEXT,
            weather_icon TEXT,
            visibility INTEGER,
            uv_index REAL,
            rain_1h REAL,
            latitude REAL,
            longitude REAL,
            location_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Weather settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on import
init_weather_db()


class WeatherService:
    """Service for fetching and caching weather data"""
    
    BASE_URL = "https://api.openweathermap.org/data/2.5"
    
    def __init__(self):
        self.api_key = settings.WEATHER_API_KEY
        self.enabled = settings.WEATHER_API_ENABLED and bool(self.api_key)
        self.lat = settings.WEATHER_LOCATION_LAT
        self.lon = settings.WEATHER_LOCATION_LON
        self.update_interval = settings.WEATHER_UPDATE_INTERVAL
        self._cache = {}
        self._cache_time = None
    
    def get_current_weather(self, lat: float = None, lon: float = None, force_refresh: bool = False) -> Optional[Dict]:
        """Get current weather data"""
        lat = lat or self.lat
        lon = lon or self.lon
        
        # Check if we have valid coordinates
        if lat == 0 and lon == 0:
            # Try to get from latest animal reading
            coords = self._get_coords_from_animals()
            if coords:
                lat, lon = coords
        
        if lat == 0 and lon == 0:
            return self._get_demo_weather()
        
        # Check cache
        cache_key = f"{lat},{lon}"
        if not force_refresh and self._cache.get(cache_key) and self._cache_time:
            if datetime.now() - self._cache_time < timedelta(seconds=self.update_interval):
                return self._cache[cache_key]
        
        # Fetch from API
        if self.enabled:
            weather = self._fetch_from_api(lat, lon)
            if weather:
                self._cache[cache_key] = weather
                self._cache_time = datetime.now()
                self._save_to_db(weather)
                return weather
        
        # Return cached or demo data
        return self._get_latest_from_db() or self._get_demo_weather()
    
    def _fetch_from_api(self, lat: float, lon: float) -> Optional[Dict]:
        """Fetch weather from OpenWeatherMap API"""
        try:
            url = f"{self.BASE_URL}/weather?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'SmartPastoralism/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            weather = {
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'wind_speed': data['wind']['speed'],
                'wind_direction': data['wind'].get('deg', 0),
                'clouds': data['clouds']['all'],
                'weather_main': data['weather'][0]['main'],
                'weather_description': data['weather'][0]['description'],
                'weather_icon': data['weather'][0]['icon'],
                'visibility': data.get('visibility', 10000),
                'rain_1h': data.get('rain', {}).get('1h', 0),
                'latitude': lat,
                'longitude': lon,
                'location_name': data.get('name', 'Unknown'),
                'timestamp': datetime.now().isoformat(),
                'sunrise': datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M'),
                'sunset': datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M')
            }
            
            print(f"🌤️ Weather fetched: {weather['temperature']}°C, {weather['weather_description']}")
            return weather
            
        except Exception as e:
            print(f"❌ Error fetching weather: {e}")
            return None
    
    def _get_coords_from_animals(self) -> Optional[tuple]:
        """Get coordinates from latest animal reading"""
        try:
            conn = sqlite3.connect(settings.LORA_DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT latitude, longitude FROM livestock_readings 
                WHERE latitude != 0 AND longitude != 0 
                ORDER BY timestamp DESC LIMIT 1
            ''')
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return (result[0], result[1])
            return None
        except:
            return None
    
    def _save_to_db(self, weather: Dict):
        """Save weather data to database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO weather_data 
                (timestamp, temperature, feels_like, humidity, pressure, wind_speed, 
                 wind_direction, clouds, weather_main, weather_description, weather_icon,
                 visibility, rain_1h, latitude, longitude, location_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                weather['timestamp'],
                weather['temperature'],
                weather['feels_like'],
                weather['humidity'],
                weather['pressure'],
                weather['wind_speed'],
                weather['wind_direction'],
                weather['clouds'],
                weather['weather_main'],
                weather['weather_description'],
                weather['weather_icon'],
                weather['visibility'],
                weather['rain_1h'],
                weather['latitude'],
                weather['longitude'],
                weather['location_name']
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving weather: {e}")
    
    def _get_latest_from_db(self) -> Optional[Dict]:
        """Get latest weather from database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM weather_data ORDER BY created_at DESC LIMIT 1
            ''')
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None
        except:
            return None
    
    def _get_demo_weather(self) -> Dict:
        """Return demo weather data when API is not available"""
        return {
            'temperature': 28.5,
            'feels_like': 30.2,
            'humidity': 65,
            'pressure': 1013,
            'wind_speed': 3.5,
            'wind_direction': 180,
            'clouds': 25,
            'weather_main': 'Partly Cloudy',
            'weather_description': 'few clouds',
            'weather_icon': '02d',
            'visibility': 10000,
            'rain_1h': 0,
            'latitude': 0,
            'longitude': 0,
            'location_name': 'Demo Location',
            'timestamp': datetime.now().isoformat(),
            'sunrise': '06:30',
            'sunset': '18:45',
            'is_demo': True
        }
    
    def get_weather_history(self, hours: int = 24) -> List[Dict]:
        """Get weather history from database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM weather_data 
                WHERE datetime(timestamp) > datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp ASC
            ''', (hours,))
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return rows
        except Exception as e:
            print(f"Error getting weather history: {e}")
            return []
    
    def get_weather_impact_analysis(self) -> Dict:
        """Analyze correlation between weather and animal health"""
        try:
            # Get last 7 days of weather and animal data
            conn_weather = sqlite3.connect(DB_PATH)
            conn_weather.row_factory = sqlite3.Row
            cursor_weather = conn_weather.cursor()
            
            cursor_weather.execute('''
                SELECT 
                    strftime('%Y-%m-%d', timestamp) as date,
                    AVG(temperature) as avg_temp,
                    AVG(humidity) as avg_humidity,
                    MAX(temperature) as max_temp
                FROM weather_data
                WHERE datetime(timestamp) > datetime('now', '-7 days')
                GROUP BY date
            ''')
            weather_data = {row['date']: dict(row) for row in cursor_weather.fetchall()}
            conn_weather.close()
            
            # Get animal health data
            conn_animals = sqlite3.connect(settings.LORA_DB_PATH)
            conn_animals.row_factory = sqlite3.Row
            cursor_animals = conn_animals.cursor()
            
            cursor_animals.execute('''
                SELECT 
                    strftime('%Y-%m-%d', received_time) as date,
                    AVG(temperature) as avg_animal_temp,
                    COUNT(*) as reading_count
                FROM livestock_readings
                WHERE datetime(received_time) > datetime('now', '-7 days')
                GROUP BY date
            ''')
            animal_data = {row['date']: dict(row) for row in cursor_animals.fetchall()}
            conn_animals.close()
            
            # Correlation analysis (simple)
            correlations = []
            for date, weather in weather_data.items():
                if date in animal_data:
                    correlations.append({
                        'date': date,
                        'ambient_temp': weather['avg_temp'],
                        'animal_temp': animal_data[date]['avg_animal_temp'],
                        'humidity': weather['avg_humidity']
                    })
            
            return {
                'correlations': correlations,
                'summary': {
                    'avg_ambient_temp': sum(c['ambient_temp'] or 0 for c in correlations) / len(correlations) if correlations else 0,
                    'avg_animal_temp': sum(c['animal_temp'] or 0 for c in correlations) / len(correlations) if correlations else 0
                }
            }
        except Exception as e:
            print(f"Error analyzing weather impact: {e}")
            return {'correlations': [], 'summary': {}}


# Global instance
weather_service = WeatherService()


def get_current_weather(lat: float = None, lon: float = None) -> Optional[Dict]:
    """Get current weather data"""
    return weather_service.get_current_weather(lat, lon)


def get_weather_history(hours: int = 24) -> List[Dict]:
    """Get weather history"""
    return weather_service.get_weather_history(hours)


def get_weather_impact() -> Dict:
    """Get weather impact analysis"""
    return weather_service.get_weather_impact_analysis()
