"""
Settings and Configuration Routes
Handles notification settings, geofence management, and system configuration
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from pydantic import BaseModel

from app.routes.auth import is_authenticated, get_current_user
from app.services.notification_service import (
    email_service, sms_service,
    add_email_recipient, add_phone_recipient,
    get_all_email_recipients, get_all_phone_recipients,
    get_notification_log
)
from app.services.geofence_service import (
    geofence_service, get_all_geofences, get_violations
)
from app.services.threshold_service import (
    ThresholdService, get_all_thresholds, set_threshold, get_thresholds_with_metadata
)
from app.services.weather_service import (
    get_current_weather, get_weather_history, get_weather_impact
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def require_auth(request: Request):
    """Dependency to require authentication"""
    if not is_authenticated(request):
        raise HTTPException(status_code=302, headers={"Location": "/auth/login"})
    return True


# ============ Notifications API ============

class EmailRecipientCreate(BaseModel):
    email: str
    name: Optional[str] = None
    notify_critical: bool = True
    notify_warning: bool = True
    notify_geofence: bool = True

class PhoneRecipientCreate(BaseModel):
    phone: str
    name: Optional[str] = None
    notify_critical: bool = True
    notify_warning: bool = False
    notify_geofence: bool = True


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, _: bool = Depends(require_auth)):
    """Notification settings page"""
    user = get_current_user(request)
    
    email_recipients = get_all_email_recipients()
    phone_recipients = get_all_phone_recipients()
    notification_log = get_notification_log(limit=20)
    
    return templates.TemplateResponse("settings/notifications.html", {
        "request": request,
        "user": user,
        "email_recipients": email_recipients,
        "phone_recipients": phone_recipients,
        "notification_log": notification_log,
        "show_sidebar": True
    })


@router.post("/notifications/email/add")
async def add_email(
    request: Request,
    email: str = Form(...),
    name: str = Form(None),
    notify_critical: bool = Form(True),
    notify_warning: bool = Form(False),
    notify_geofence: bool = Form(True),
    _: bool = Depends(require_auth)
):
    """Add email recipient"""
    success = add_email_recipient(
        email=email,
        name=name,
        notify_critical=notify_critical,
        notify_warning=notify_warning,
        notify_geofence=notify_geofence
    )
    
    if success:
        return RedirectResponse(url="/settings/notifications?success=email_added", status_code=302)
    return RedirectResponse(url="/settings/notifications?error=email_failed", status_code=302)


@router.post("/notifications/email/{email_id}/delete")
async def delete_email(request: Request, email_id: int, _: bool = Depends(require_auth)):
    """Delete email recipient"""
    import sqlite3
    from app.services.notification_service import DB_PATH
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM email_recipients WHERE id = ?', (email_id,))
        conn.commit()
        conn.close()
        return RedirectResponse(url="/settings/notifications?success=deleted", status_code=302)
    except Exception as e:
        return RedirectResponse(url="/settings/notifications?error=delete_failed", status_code=302)


@router.post("/notifications/email/test")
async def test_email(
    request: Request,
    email: str = Form(...),
    _: bool = Depends(require_auth)
):
    """Send a test email"""
    try:
        subject = "PawTrack test email"
        html_body = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; background-color: #f3f4f6; padding: 20px; }
                .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                .header { background: #3F7D2A; color: white; padding: 20px; text-align: center; }
                .content { padding: 30px; }
                .footer { background: #f3f4f6; padding: 15px; text-align: center; font-size: 12px; color: #6b7280; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Test Email Successful!</h1>
                </div>
                <div class="content">
                    <h2>Email notifications are working correctly</h2>
                    <p>This is a test email from your PawTrack monitoring system.</p>
                    <p>You will receive alerts for:</p>
                    <ul>
                        <li>🌡️ Critical temperature warnings</li>
                        <li>💓 High heart rate alerts</li>
                        <li>🔋 Low battery warnings</li>
                        <li>📍 Geofence violations</li>
                    </ul>
                    <p><strong>System Status:</strong> All systems operational ✓</p>
                </div>
                <div class="footer">
                    <p>PawTrack Monitoring System</p>
                    <p>This is an automated test email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = """
        PAWTRACK - TEST EMAIL
        ===============================
        
        ✅ Email notifications are working correctly!
        
        This is a test email from your PawTrack monitoring system.
        
        You will receive alerts for:
        - Critical temperature warnings
        - High heart rate alerts
        - Low battery warnings
        - Geofence violations
        
        System Status: All systems operational ✓
        
        --
        PawTrack Monitoring System
        """
        
        success = email_service.send_email(email, subject, html_body, text_body)
        
        if success:
            return {"success": True, "message": f"Test email sent to {email}"}
        else:
            return {"success": False, "message": "Failed to send test email"}
            
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/notifications/phone/add")
async def add_phone(
    request: Request,
    phone: str = Form(...),
    name: str = Form(None),
    notify_critical: bool = Form(True),
    notify_warning: bool = Form(False),
    notify_geofence: bool = Form(True),
    _: bool = Depends(require_auth)
):
    """Add phone recipient"""
    success = add_phone_recipient(
        phone=phone,
        name=name,
        notify_critical=notify_critical,
        notify_warning=notify_warning,
        notify_geofence=notify_geofence
    )
    
    if success:
        return RedirectResponse(url="/settings/notifications?success=phone_added", status_code=302)
    return RedirectResponse(url="/settings/notifications?error=phone_failed", status_code=302)


@router.post("/notifications/phone/{phone_id}/delete")
async def delete_phone(request: Request, phone_id: int, _: bool = Depends(require_auth)):
    """Delete phone recipient"""
    import sqlite3
    from app.services.notification_service import DB_PATH
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM phone_recipients WHERE id = ?', (phone_id,))
        conn.commit()
        conn.close()
        return RedirectResponse(url="/settings/notifications?success=deleted", status_code=302)
    except Exception as e:
        return RedirectResponse(url="/settings/notifications?error=delete_failed", status_code=302)


@router.post("/notifications/test-email")
async def test_email(request: Request, _: bool = Depends(require_auth)):
    """Send a test email"""
    user = get_current_user(request)
    
    recipients = get_all_email_recipients()
    if not recipients:
        return RedirectResponse(url="/settings/notifications?error=no_recipients", status_code=302)
    
    test_alert = {
        'alert_type': 'TEST_ALERT',
        'device_id': 'TEST-001',
        'alert_message': 'This is a test notification from PawTrack system.',
        'temperature': 38.5,
        'heart_rate': 72,
        'battery': 85,
        'alert_time': 'Just now'
    }
    
    email_service.send_alert_notification(test_alert)
    
    return RedirectResponse(url="/settings/notifications?success=test_sent", status_code=302)


# ============ Geofencing API ============

class GeofenceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    polygon: List[dict]
    color: str = "#3B82F6"
    alert_on_exit: bool = True
    alert_on_enter: bool = False


@router.get("/geofencing", response_class=HTMLResponse)
async def geofencing_page(request: Request, _: bool = Depends(require_auth)):
    """Geofencing management page"""
    user = get_current_user(request)
    
    geofences = get_all_geofences()
    violations = get_violations(limit=20, unresolved_only=False)
    
    return templates.TemplateResponse("settings/geofencing.html", {
        "request": request,
        "user": user,
        "geofences": geofences,
        "violations": violations,
        "show_sidebar": True
    })


@router.post("/geofencing/create")
async def create_geofence_route(data: GeofenceCreate, _: bool = Depends(require_auth)):
    """Create a new geofence"""
    geofence_id = geofence_service.create_geofence(
        name=data.name,
        polygon=data.polygon,
        description=data.description,
        color=data.color,
        alert_on_exit=data.alert_on_exit,
        alert_on_enter=data.alert_on_enter
    )
    
    if geofence_id:
        return {"success": True, "geofence_id": geofence_id}
    raise HTTPException(status_code=500, detail="Failed to create geofence")


@router.get("/geofencing/{geofence_id}")
async def get_geofence_route(geofence_id: int, _: bool = Depends(require_auth)):
    """Get a specific geofence"""
    geofence = geofence_service.get_geofence(geofence_id)
    if geofence:
        return geofence
    raise HTTPException(status_code=404, detail="Geofence not found")


@router.put("/geofencing/{geofence_id}")
async def update_geofence_route(geofence_id: int, data: GeofenceCreate, _: bool = Depends(require_auth)):
    """Update a geofence"""
    success = geofence_service.update_geofence(
        geofence_id,
        name=data.name,
        polygon=data.polygon,
        description=data.description,
        color=data.color,
        alert_on_exit=data.alert_on_exit,
        alert_on_enter=data.alert_on_enter
    )
    
    if success:
        return {"success": True}
    raise HTTPException(status_code=500, detail="Failed to update geofence")


@router.delete("/geofencing/{geofence_id}")
async def delete_geofence_route(geofence_id: int, _: bool = Depends(require_auth)):
    """Delete a geofence"""
    success = geofence_service.delete_geofence(geofence_id)
    if success:
        return {"success": True}
    raise HTTPException(status_code=500, detail="Failed to delete geofence")


@router.post("/geofencing/violations/{violation_id}/resolve")
async def resolve_violation_route(violation_id: int, _: bool = Depends(require_auth)):
    """Resolve a geofence violation"""
    success = geofence_service.resolve_violation(violation_id)
    if success:
        return {"success": True}
    raise HTTPException(status_code=500, detail="Failed to resolve violation")


@router.get("/geofencing/api/all")
async def get_all_geofences_api(_: bool = Depends(require_auth)):
    """Get all geofences as JSON for map rendering"""
    return {"geofences": get_all_geofences(active_only=False)}


@router.get("/geofencing/api/violations")
async def get_violations_api(limit: int = 50, unresolved_only: bool = False, _: bool = Depends(require_auth)):
    """Get violations as JSON"""
    return {"violations": get_violations(limit=limit, unresolved_only=unresolved_only)}


# ============ Thresholds API ============

@router.get("/thresholds", response_class=HTMLResponse)
async def thresholds_page(request: Request, _: bool = Depends(require_auth)):
    """Threshold configuration page"""
    user = get_current_user(request)
    
    thresholds = get_thresholds_with_metadata()
    change_log = ThresholdService.get_change_log(limit=10)
    
    return templates.TemplateResponse("settings/thresholds.html", {
        "request": request,
        "user": user,
        "thresholds": thresholds,
        "change_log": change_log,
        "show_sidebar": True
    })


@router.post("/thresholds/update")
async def update_threshold(
    request: Request,
    threshold_key: str = Form(...),
    threshold_value: float = Form(...),
    _: bool = Depends(require_auth)
):
    """Update a threshold value"""
    user = get_current_user(request)
    username = user.get('username', 'unknown') if user else 'unknown'
    
    success = set_threshold(threshold_key, threshold_value, username)
    
    if success:
        return RedirectResponse(url="/settings/thresholds?success=updated", status_code=302)
    return RedirectResponse(url="/settings/thresholds?error=update_failed", status_code=302)


@router.post("/thresholds/reset")
async def reset_thresholds(request: Request, _: bool = Depends(require_auth)):
    """Reset all thresholds to defaults"""
    success = ThresholdService.reset_to_defaults()
    
    if success:
        return RedirectResponse(url="/settings/thresholds?success=reset", status_code=302)
    return RedirectResponse(url="/settings/thresholds?error=reset_failed", status_code=302)


@router.get("/thresholds/api/all")
async def get_thresholds_api(_: bool = Depends(require_auth)):
    """Get all thresholds as JSON"""
    return {"thresholds": get_all_thresholds()}


# ============ Weather API ============

@router.get("/weather", response_class=HTMLResponse)
async def weather_page(request: Request, _: bool = Depends(require_auth)):
    """Weather integration page"""
    user = get_current_user(request)
    
    current_weather = get_current_weather()
    weather_history = get_weather_history(hours=24)
    impact_analysis = get_weather_impact()
    
    return templates.TemplateResponse("settings/weather.html", {
        "request": request,
        "user": user,
        "weather": current_weather,
        "history": weather_history,
        "impact": impact_analysis,
        "show_sidebar": True
    })


@router.get("/weather/api/current")
async def get_weather_api(lat: float = None, lon: float = None, _: bool = Depends(require_auth)):
    """Get current weather as JSON"""
    return {"weather": get_current_weather(lat, lon)}


@router.get("/weather/api/history")
async def get_weather_history_api(hours: int = 24, _: bool = Depends(require_auth)):
    """Get weather history as JSON"""
    return {"history": get_weather_history(hours)}


@router.get("/weather/api/impact")
async def get_weather_impact_api(_: bool = Depends(require_auth)):
    """Get weather impact analysis as JSON"""
    return get_weather_impact()


# ============ Heatmap API ============

@router.get("/heatmap", response_class=HTMLResponse)
async def heatmap_page(request: Request, _: bool = Depends(require_auth)):
    """Heatmap visualization page"""
    user = get_current_user(request)
    
    return templates.TemplateResponse("settings/heatmap.html", {
        "request": request,
        "user": user,
        "show_sidebar": True
    })


@router.get("/geofences", response_class=HTMLResponse)
async def geofences_page(request: Request, _: bool = Depends(require_auth)):
    """Geofence management page"""
    user = get_current_user(request)
    
    return templates.TemplateResponse("settings/geofences.html", {
        "request": request,
        "user": user,
        "show_sidebar": True
    })

