from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import os

from app import create_app
from app.config import settings
from app.websocket.handlers import setup_websocket
from app.services.lora_service import LoRaMonitor

# Create FastAPI app
app = create_app()

# Static files and templates
from pathlib import Path

# ... existing code ...

# Get absolute path to project root
BASE_DIR = Path(__file__).resolve().parent

# Static files and templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app/static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "app/templates"))

# Import and include routers
from app.routes import dashboard, api, auth, export, ml_api, farms
from app.routes import settings as settings_routes

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(api.router,prefix="/api", tags=["API"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(ml_api.router, prefix="/api", tags=["ML & AI"])
app.include_router(settings_routes.router, prefix="/settings", tags=["Settings"])
# Milk Production feature removed from the app
app.include_router(farms.router, prefix="/farms", tags=["Farm Management"])

# Check if we are running on Vercel
IS_VERCEL = os.environ.get("VERCEL") == "1"

# WebSocket setup (Not supported on Vercel)
if not IS_VERCEL:
    setup_websocket(app)

# Global LoRa monitor instance
lora_monitor = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global lora_monitor
    
    if IS_VERCEL:
        print("✅ Running in Vercel environment. Skipping background threads and WebSockets.")
        return
        
    # Set the event loop for WebSocket broadcasting from background threads
    import asyncio
    from app.websocket.handlers import set_event_loop
    loop = asyncio.get_running_loop()
    set_event_loop(loop)
    print("✅ Event loop configured for WebSocket broadcasting")
    
    # Check if database exists
    if os.path.exists(settings.LORA_DB_PATH):
        lora_monitor = LoRaMonitor()
        lora_monitor.start_monitoring()
        print(f"✅ LoRa monitor started (checking every {settings.LORA_CHECK_INTERVAL}s)")
    else:
        print(f"⚠️  Warning: Database not found at {settings.LORA_DB_PATH}")
        print("    LoRa monitoring will start when database is available")
    
    print(f"🚀 {settings.APP_NAME} started successfully!")
    print(f"📊 Dashboard: http://{settings.RPI_HOST}:{settings.PORT}/dashboard")
    print(f"📡 API Docs: http://{settings.RPI_HOST}:{settings.PORT}/docs")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global lora_monitor
    if lora_monitor:
        lora_monitor.stop_monitoring()
    print("👋 Application shutdown complete")

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page"""
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "app_name": settings.APP_NAME
    })

@app.get("/r/{token}")
def shared_report(token: str):
    """A vet opens the health report from the WhatsApp link, without signing in (link expires)"""
    from fastapi.responses import Response, HTMLResponse as _Html
    from app.services.health_report import build_pdf, device_from_token
    device_id = device_from_token(token)
    pdf = build_pdf(device_id) if device_id else None
    if not pdf:
        return _Html("<p style='font-family:sans-serif'>This report link has expired or is not valid. Ask the farmer to send it again.</p>", status_code=404)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="health-report-{device_id}.pdf"'})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "lora_monitor": "running" if lora_monitor and lora_monitor.running else "stopped"
    }

@app.get("/test-chart", response_class=HTMLResponse)
async def test_chart(request: Request):
    """Test chart rendering"""
    return templates.TemplateResponse("chart_test.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run(
        "run:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
