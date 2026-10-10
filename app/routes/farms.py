from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from app.services.farm_management import farm_service
from app.routes.auth import is_authenticated
from app.routes.dashboard import build_overview

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def _herd_by_farm():
    """Animals from the overview, grouped by farm name"""
    try:
        overview = build_overview()
    except Exception as e:
        print(f"Error building herd data: {e}")
        return {}
    grouped = {}
    for a in overview["animals"]:
        grouped.setdefault(a["farm"], []).append(a)
    return grouped


def _farm_health(animals):
    """Counts and overall state for one farm's herd"""
    critical = sum(1 for a in animals if a["status"] == "critical")
    watch = sum(1 for a in animals if a["status"] in ("watch", "recovering"))
    healthy = sum(1 for a in animals if a["status"] == "healthy")
    temps = [a["temp"] for a in animals if a["temp"]]
    return {
        "herd": len(animals),
        "critical": critical,
        "watch": watch,
        "healthy": healthy,
        "healthy_pct": round(100 * healthy / len(animals)) if animals else None,
        "avg_temp": round(sum(temps) / len(temps), 1) if temps else None,
        "low_battery": sum(1 for a in animals if (a["battery"] or 100) < 50),
        "state": "critical" if critical else ("watch" if watch else ("healthy" if animals else "empty")),
    }


def require_auth(request: Request):
    """Dependency to require authentication"""
    if not is_authenticated(request):
        raise HTTPException(status_code=302, headers={"Location": "/auth/login"})
    return True

# Pydantic models
class FarmCreate(BaseModel):
    farm_code: str
    farm_name: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area_hectares: Optional[float] = None
    owner_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None

class FarmUpdate(BaseModel):
    farm_name: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area_hectares: Optional[float] = None
    owner_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None

class AnimalAssignment(BaseModel):
    device_id: str

# Dashboard Pages
@router.get("/", response_class=HTMLResponse)
async def farms_list(request: Request, _: bool = Depends(require_auth)):
    """Farms management page"""
    farms = farm_service.get_all_farms()
    herd = _herd_by_farm()
    for f in farms:
        f["health"] = _farm_health(herd.get(f["farm_name"], []))
    unassigned = herd.get("Unassigned", [])

    return templates.TemplateResponse("farms/list.html", {
        "request": request,
        "farms": farms,
        "unassigned": unassigned,
        "show_sidebar": True
    })

@router.get("/{farm_id}", response_class=HTMLResponse)
async def farm_detail(request: Request, farm_id: int, _: bool = Depends(require_auth)):
    """Individual farm dashboard"""
    farm = farm_service.get_farm(farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    
    herd = _herd_by_farm()
    animals = herd.get(farm["farm_name"], [])
    unassigned = [a["device_id"] for a in herd.get("Unassigned", [])]

    return templates.TemplateResponse("farms/detail.html", {
        "request": request,
        "farm": farm,
        "animals": animals,
        "health": _farm_health(animals),
        "unassigned": unassigned,
        "show_sidebar": True
    })

@router.get("/compare/all", response_class=HTMLResponse)
async def farms_comparison(request: Request, _: bool = Depends(require_auth)):
    """Compare all farms"""
    farms = farm_service.get_all_farms()
    herd = _herd_by_farm()
    for f in farms:
        f["health"] = _farm_health(herd.get(f["farm_name"], []))
        area = f.get("area_hectares") or 0
        f["density"] = round(f["health"]["herd"] / area, 2) if area else None

    return templates.TemplateResponse("farms/comparison.html", {
        "request": request,
        "farms": farms,
        "show_sidebar": True
    })

# API Endpoints
@router.get("/api/list")
async def get_farms(_: bool = Depends(require_auth)):
    """Get all farms"""
    farms = farm_service.get_all_farms()
    return JSONResponse(content={"farms": farms})

@router.get("/api/{farm_id}")
async def get_farm(farm_id: int, _: bool = Depends(require_auth)):
    """Get single farm"""
    farm = farm_service.get_farm(farm_id)
    if farm:
        return JSONResponse(content=farm)
    else:
        raise HTTPException(status_code=404, detail="Farm not found")

@router.post("/api/create")
async def create_farm(farm: FarmCreate, _: bool = Depends(require_auth)):
    """Create new farm"""
    result = farm_service.create_farm(farm.dict())
    return JSONResponse(content=result)

@router.put("/api/{farm_id}")
async def update_farm(farm_id: int, farm: FarmUpdate, _: bool = Depends(require_auth)):
    """Update farm"""
    result = farm_service.update_farm(farm_id, farm.dict())
    return JSONResponse(content=result)

@router.delete("/api/{farm_id}")
async def delete_farm(farm_id: int, _: bool = Depends(require_auth)):
    """Delete farm"""
    result = farm_service.delete_farm(farm_id)
    return JSONResponse(content=result)

@router.get("/api/{farm_id}/animals")
async def get_farm_animals(farm_id: int, _: bool = Depends(require_auth)):
    """Get all animals in a farm"""
    animals = farm_service.get_farm_animals(farm_id)
    return JSONResponse(content={"animals": animals})

@router.post("/api/{farm_id}/assign")
async def assign_animal(farm_id: int, assignment: AnimalAssignment, _: bool = Depends(require_auth)):
    """Assign animal to farm"""
    result = farm_service.assign_animal(farm_id, assignment.device_id)
    return JSONResponse(content=result)

@router.get("/api/{farm_id}/stats")
async def get_stats(farm_id: int, _: bool = Depends(require_auth)):
    """Get farm statistics"""
    stats = farm_service.get_farm_stats(farm_id)
    return JSONResponse(content=stats)

@router.get("/api/compare/all")
async def compare_all(_: bool = Depends(require_auth)):
    """Compare all farms"""
    comparison = farm_service.compare_farms()
    return JSONResponse(content={"farms": comparison})
