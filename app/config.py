import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Application
    APP_NAME: str = os.getenv("APP_NAME", "Smart Pastoralism System")
    DEBUG: bool = os.getenv("DEBUG", "True") == "True"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./livestock_data.db")
    DATABASE_POOL_SIZE: int = 5
    
    # Redis Cache
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))
    
    # LoRa Receiver
    LORA_DB_PATH: str = os.getenv("LORA_DB_PATH", "livestock_data.db")
    LORA_CHECK_INTERVAL: int = int(os.getenv("LORA_CHECK_INTERVAL", "2"))
    
    # Alert Thresholds
    TEMP_WARNING: float = float(os.getenv("TEMP_WARNING", "39.0"))
    TEMP_CRITICAL: float = float(os.getenv("TEMP_CRITICAL", "39.5"))
    HR_WARNING: int = int(os.getenv("HR_WARNING", "75"))
    HR_CRITICAL: int = int(os.getenv("HR_CRITICAL", "80"))
    BATTERY_LOW: int = int(os.getenv("BATTERY_LOW", "50"))
    BATTERY_CRITICAL: int = int(os.getenv("BATTERY_CRITICAL", "20"))
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    WORKERS: int = int(os.getenv("WORKERS", "4"))
    
    # Raspberry Pi
    RPI_HOST: str = os.getenv("RPI_HOST", "192.168.1.12")
    
    # Email Notifications (SMTP)
    SMTP_ENABLED: bool = os.getenv("SMTP_ENABLED", "False") == "True"
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Smart Pastoralism Alerts")
    NOTIFICATION_EMAILS: str = os.getenv("NOTIFICATION_EMAILS", "")  # Comma-separated
    
    # SMS Notifications (Twilio)
    SMS_ENABLED: bool = os.getenv("SMS_ENABLED", "False") == "True"
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    NOTIFICATION_PHONES: str = os.getenv("NOTIFICATION_PHONES", "")  # Comma-separated
    
    # Geofencing
    GEOFENCE_ALERT_ENABLED: bool = os.getenv("GEOFENCE_ALERT_ENABLED", "True") == "True"
    GEOFENCE_CHECK_INTERVAL: int = int(os.getenv("GEOFENCE_CHECK_INTERVAL", "60"))  # seconds
    
    # Weather API (OpenWeatherMap)
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")
    WEATHER_API_ENABLED: bool = os.getenv("WEATHER_API_ENABLED", "True") == "True"
    WEATHER_LOCATION_LAT: float = float(os.getenv("WEATHER_LOCATION_LAT", "0"))
    WEATHER_LOCATION_LON: float = float(os.getenv("WEATHER_LOCATION_LON", "0"))
    WEATHER_UPDATE_INTERVAL: int = int(os.getenv("WEATHER_UPDATE_INTERVAL", "1800"))  # 30 minutes

def get_settings():
    return Settings()

settings = get_settings()
