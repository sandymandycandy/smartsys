from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.services.milk_production import milk_service
from app.routes.auth import is_authenticated

# Import ML predictor
try:
    from app.services.milk_yield_predictor import milk_yield_predictor
    ML_PREDICTION_AVAILABLE = milk_yield_predictor is not None
except ImportError:
    ML_PREDICTION_AVAILABLE = False
    milk_yield_predictor = None

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def require_auth(request: Request):
    """Dependency to require authentication"""
    if not is_authenticated(request):
        raise HTTPException(status_code=302, headers={"Location": "/auth/login"})
    return True

# Pydantic models
class MilkProductionRecord(BaseModel):
    device_id: str
    collection_date: str
    collection_time: Optional[str] = None
    yield_liters: float
    fat_percentage: Optional[float] = None
    protein_percentage: Optional[float] = None
    lactose_percentage: Optional[float] = None
    quality_grade: Optional[str] = None
    milking_session: Optional[str] = "morning"
    notes: Optional[str] = None
    recorded_by: Optional[str] = "system"

class AnimalProfile(BaseModel):
    animal_name: Optional[str] = None
    breed: Optional[str] = None
    birth_date: Optional[str] = None
    lactation_number: Optional[int] = None
    last_calving_date: Optional[str] = None
    expected_yield_per_day: Optional[float] = None
    notes: Optional[str] = None

# Dashboard Pages
@router.get("/dashboard", response_class=HTMLResponse)
async def milk_dashboard(request: Request, _: bool = Depends(require_auth)):
    """Main milk production dashboard"""
    return templates.TemplateResponse("milk/dashboard.html", {
        "request": request,
        "show_sidebar": True
    })

@router.get("/record", response_class=HTMLResponse)
async def record_page(request: Request, _: bool = Depends(require_auth)):
    """Page to record new milk production"""
    return templates.TemplateResponse("milk/record.html", {
        "request": request,
        "show_sidebar": True
    })

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, _: bool = Depends(require_auth)):
    """Milk production analytics page"""
    return templates.TemplateResponse("milk/analytics.html", {
        "request": request,
        "show_sidebar": True
    })

@router.get("/animal/{device_id}", response_class=HTMLResponse)
async def animal_milk_detail(request: Request, device_id: str, _: bool = Depends(require_auth)):
    """Individual animal milk production page"""
    profile = milk_service.get_animal_profile(device_id)
    
    return templates.TemplateResponse("milk/animal_detail.html", {
        "request": request,
        "device_id": device_id,
        "profile": profile or {},
        "show_sidebar": True
    })

# API Endpoints
@router.post("/api/record")
async def record_production(record: MilkProductionRecord, _: bool = Depends(require_auth)):
    """Record milk production"""
    result = milk_service.record_production(record.dict())
    return JSONResponse(content=result)

@router.get("/api/production/{device_id}")
async def get_production(device_id: str, days: int = 30, _: bool = Depends(require_auth)):
    """Get production records for an animal"""
    records = milk_service.get_production_by_animal(device_id, days)
    return JSONResponse(content={"records": records})

@router.get("/api/daily/{device_id}")
async def get_daily_total(device_id: str, date: Optional[str] = None, _: bool = Depends(require_auth)):
    """Get daily total for an animal"""
    result = milk_service.get_daily_total(device_id, date)
    return JSONResponse(content=result)

@router.get("/api/trends/{device_id}")
async def get_trends(device_id: str, days: int = 30, _: bool = Depends(require_auth)):
    """Get production trends for charts"""
    trends = milk_service.get_production_trends(device_id, days)
    return JSONResponse(content={"trends": trends})

@router.get("/api/herd/summary")
async def get_herd_summary(days: int = 30, _: bool = Depends(require_auth)):
    """Get herd production summary"""
    summary = milk_service.get_herd_production_summary(days)
    return JSONResponse(content=summary)

@router.post("/api/profile/{device_id}")
async def update_profile(device_id: str, profile: AnimalProfile, _: bool = Depends(require_auth)):
    """Update animal profile"""
    result = milk_service.update_animal_profile(device_id, profile.dict())
    return JSONResponse(content=result)

@router.get("/api/profile/{device_id}")
async def get_profile(device_id: str, _: bool = Depends(require_auth)):
    """Get animal profile"""
    profile = milk_service.get_animal_profile(device_id)
    if profile:
        return JSONResponse(content=profile)
    else:
        return JSONResponse(content={"message": "Profile not found"}, status_code=404)

@router.delete("/api/record/{record_id}")
async def delete_record(record_id: int, _: bool = Depends(require_auth)):
    """Delete a production record"""
    result = milk_service.delete_production_record(record_id)
    return JSONResponse(content=result)

# ML Prediction Endpoints
@router.get("/api/predict/{device_id}")
async def predict_yield(device_id: str, session: str = "morning", _: bool = Depends(require_auth)):
    """Predict milk yield for next session"""
    if not ML_PREDICTION_AVAILABLE:
        return JSONResponse(content={
            "error": "ML prediction not available",
            "message": "Install scikit-learn to enable predictions"
        }, status_code=503)
    
    prediction = milk_yield_predictor.predict_next_yield(device_id, session)
    return JSONResponse(content=prediction)

@router.post("/api/check-anomaly/{device_id}")
async def check_yield_anomaly(device_id: str, actual_yield: float, _: bool = Depends(require_auth)):
    """Check if actual yield is anomalous"""
    if not ML_PREDICTION_AVAILABLE:
        return JSONResponse(content={"is_anomaly": False, "message": "ML not available"})
    
    result = milk_yield_predictor.detect_yield_anomaly(device_id, actual_yield)
    return JSONResponse(content=result)

@router.post("/api/ml/retrain")
async def retrain_predictor(_: bool = Depends(require_auth)):
    """Retrain milk yield prediction model"""
    if not ML_PREDICTION_AVAILABLE:
        return JSONResponse(content={"error": "ML not available"}, status_code=503)
    
    try:
        milk_yield_predictor.retrain_model()
        return JSONResponse(content={
            "status": "success",
            "message": "Milk yield predictor retrained successfully"
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.get("/api/ml/info")
async def get_ml_info(_: bool = Depends(require_auth)):
    """Get ML prediction system information"""
    return JSONResponse(content={
        "ml_available": ML_PREDICTION_AVAILABLE,
        "model_type": "RandomForestRegressor" if ML_PREDICTION_AVAILABLE else None,
        "features_used": [
            "days_in_lactation",
            "lactation_number",
            "7-day average yield",
            "30-day average yield",
            "yield trend",
            "health metrics",
            "session type"
        ] if ML_PREDICTION_AVAILABLE else []
    })
