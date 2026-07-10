from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from app.config import settings
from app.services.lora_service import get_herd_stats
from app.routes.auth import is_authenticated

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def require_auth(request: Request):
    """Dependency to require authentication"""
    if not is_authenticated(request):
        raise HTTPException(status_code=302, headers={"Location": "/auth/login"})
    return True

@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, _: bool = Depends(require_auth)):
    """Dashboard home page with overview"""
    
    # Get statistics
    stats = get_herd_stats()
    
    try:
        # Get recent alerts
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM alerts 
            WHERE resolved = 0 
            ORDER BY alert_time DESC 
            LIMIT 10
        ''')
        recent_alerts = [dict(row) for row in cursor.fetchall()]
        
        # Get animal locations
        cursor.execute('''
            SELECT DISTINCT device_id, latitude, longitude, 
                   temperature, body_temperature, ambient_temperature, heart_rate, battery,
                   MAX(timestamp) as last_update
            FROM livestock_readings
            WHERE latitude != 0 AND longitude != 0
            GROUP BY device_id
        ''')
        animal_locations = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
    except Exception as e:
        print(f"Error fetching dashboard data: {e}")
        recent_alerts = []
        animal_locations = []
    
    return templates.TemplateResponse("dashboard/home.html", {
        "request": request,
        "stats": stats,
        "alerts": recent_alerts,
        "locations": animal_locations,
        "show_sidebar": True
    })

@router.get("/animals", response_class=HTMLResponse)
async def animals_list(request: Request, _: bool = Depends(require_auth)):
    """List all animals"""
    
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get latest reading for each animal
        cursor.execute('''
            SELECT 
                l1.device_id,
                l1.latitude,
                l1.longitude,
                l1.temperature,
                l1.body_temperature,
                l1.ambient_temperature,
                l1.humidity,
                l1.heart_rate,
                l1.battery,
                l1.motion_magnitude,
                l1.received_time,
                (SELECT COUNT(*) FROM alerts WHERE device_id = l1.device_id AND resolved = 0) as alert_count
            FROM livestock_readings l1
            INNER JOIN (
                SELECT device_id, MAX(received_time) as max_time
                FROM livestock_readings
                GROUP BY device_id
            ) l2 ON l1.device_id = l2.device_id AND l1.received_time = l2.max_time
            ORDER BY l1.device_id
        ''')
        
        animals = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        print(f"Error fetching animals: {e}")
        animals = []
    
    return templates.TemplateResponse("dashboard/animals.html", {
        "request": request,
        "animals": animals,
        "show_sidebar": True
    })

@router.get("/animals/{device_id}", response_class=HTMLResponse)
async def animal_detail(request: Request, device_id: str, _: bool = Depends(require_auth)):
    """Individual animal profile"""
    
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Latest reading
        cursor.execute('''
            SELECT * FROM livestock_readings 
            WHERE device_id = ? 
            ORDER BY received_time DESC 
            LIMIT 1
        ''', (device_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Animal not found")
        latest = dict(result)
        
        # Historical data (last 24 hours)
        cursor.execute('''
            SELECT timestamp, temperature, body_temperature, ambient_temperature, heart_rate, motion_magnitude, battery
            FROM livestock_readings 
            WHERE device_id = ? 
            AND datetime(received_time) > datetime('now', '-24 hours')
            ORDER BY received_time ASC
        ''', (device_id,))
        history = [dict(row) for row in cursor.fetchall()]
        
        # Alerts for this animal
        cursor.execute('''
            SELECT * FROM alerts 
            WHERE device_id = ? 
            ORDER BY alert_time DESC 
            LIMIT 20
        ''', (device_id,))
        alerts = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
    except Exception as e:
        print(f"Error fetching animal detail: {e}")
        raise HTTPException(status_code=500, detail="Error fetching animal data")
    
    return templates.TemplateResponse("dashboard/animal_detail.html", {
        "request": request,
        "animal": latest,
        "history": history,
        "alerts": alerts,
        "show_sidebar": True
    })

@router.get("/map", response_class=HTMLResponse)
async def live_map(request: Request, _: bool = Depends(require_auth)):
    """Live map with all animals"""
    return templates.TemplateResponse("dashboard/map.html", {
        "request": request,
        "show_sidebar": True
    })

@router.get("/alerts", response_class=HTMLResponse)
async def alerts_page(request: Request, _: bool = Depends(require_auth)):
    """Alerts management page"""
    
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM alerts 
            ORDER BY alert_time DESC 
            LIMIT 100
        ''')
        alerts = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        print(f"Error fetching alerts: {e}")
        alerts = []
    
    return templates.TemplateResponse("dashboard/alerts.html", {
        "request": request,
        "alerts": alerts,
        "show_sidebar": True
    })

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, _: bool = Depends(require_auth)):
    """Health analytics page"""
    return templates.TemplateResponse("dashboard/analytics.html", {
        "request": request,
        "show_sidebar": True
    })

@router.get("/ml-insights", response_class=HTMLResponse)
async def ml_insights_page(request: Request, _: bool = Depends(require_auth)):
    """ML-powered disease detection and predictions"""
    return templates.TemplateResponse("dashboard/ml_insights.html", {
        "request": request,
        "show_sidebar": True
    })
