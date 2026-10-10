from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import re
import sqlite3
from datetime import datetime, timedelta
from app.config import settings
from app.services.lora_service import get_herd_stats
from app.routes.auth import is_authenticated
from fastapi.responses import JSONResponse, Response
from app.services.health_report import build_pdf, report_link
from app.services.vet_contact import vet_options, demo_whatsapp_to

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def require_auth(request: Request):
    """Dependency to require authentication"""
    if not is_authenticated(request):
        raise HTTPException(status_code=302, headers={"Location": "/auth/login"})
    return True

def _parse_time(value):
    """Parse the mixed timestamp formats stored in the DB"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except ValueError:
        return None


def _ago(dt, now):
    """Short relative time: 12m, 3h, 2d"""
    if not dt:
        return "never"
    secs = max(0, int((now - dt).total_seconds()))
    if secs < 3600:
        return f"{max(1, secs // 60)}m"
    if secs < 86400:
        return f"{secs // 3600}h"
    return f"{secs // 86400}d"


def _condition(message):
    """'CRITICAL: High heart rate (81 BPM)' -> 'High heart rate (81 BPM)'"""
    msg = (message or "").strip()
    if ":" in msg and msg.split(":", 1)[0].isupper():
        msg = msg.split(":", 1)[1].strip()
    msg = msg.replace("\ufffd", "\u00b0")
    # Long sensor floats -> one decimal: 39.02550597117886 -> 39.0
    return re.sub(r"(\d+\.\d)\d+", r"\1", msg)


def herd_lookup(cur):
    """Names, breeds and farms for every device: (profiles, farms, farm_of)"""
    def table_exists(name):
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,))
        return cur.fetchone() is not None

    profiles = {}
    if table_exists("animal_profiles"):
        cur.execute("SELECT device_id, animal_name, breed FROM animal_profiles")
        profiles = {r["device_id"]: dict(r) for r in cur.fetchall()}

    farms, farm_of = {}, {}
    if table_exists("farms") and table_exists("farm_animals"):
        cur.execute("SELECT * FROM farms WHERE is_active = 1")
        farms = {r["id"]: dict(r) for r in cur.fetchall()}
        cur.execute("SELECT farm_id, device_id FROM farm_animals WHERE is_active = 1")
        for r in cur.fetchall():
            if r["farm_id"] in farms:
                farm_of[r["device_id"]] = farms[r["farm_id"]]
    return profiles, farms, farm_of


def describe_alert(alert, profiles, farm_of, now):
    """Add plain-language fields to an alert row"""
    farm = farm_of.get(alert["device_id"])
    alert["condition"] = _condition(alert["alert_message"])
    alert["since"] = _ago(_parse_time(alert["alert_time"]), now)
    alert["name"] = profiles.get(alert["device_id"], {}).get("animal_name") or ""
    alert["farm"] = farm["farm_name"] if farm else ""
    alert["severity"] = {"CRITICAL": "critical", "WARNING": "warning"}.get(alert["alert_type"], "info")
    return alert


def animal_history(cur, device_id):
    """A year of health records, 30-day vital averages and the year's alert count for one animal"""
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='health_history'")
    events = []
    if cur.fetchone():
        cur.execute("""SELECT event_date, event_type, title, details, vet_name FROM health_history
                       WHERE device_id = ? AND event_date > datetime('now', 'localtime', '-365 days')
                       ORDER BY event_date""", (device_id,))
        events = [dict(r) for r in cur.fetchall()]
    cur.execute("""SELECT ROUND(AVG(COALESCE(body_temperature, temperature)), 1) AS avg_temp,
                          ROUND(MAX(COALESCE(body_temperature, temperature)), 1) AS max_temp,
                          CAST(ROUND(AVG(heart_rate)) AS INT) AS avg_hr, ROUND(AVG(motion_magnitude), 2) AS avg_motion
                   FROM livestock_readings WHERE device_id = ? AND received_time > datetime('now', 'localtime', '-30 days')""", (device_id,))
    vitals30 = dict(cur.fetchone())
    cur.execute("SELECT COUNT(*) FROM alerts WHERE device_id = ? AND alert_time > datetime('now', 'localtime', '-365 days')", (device_id,))
    return {"events": events, "vitals30": vitals30, "alerts_year": cur.fetchone()[0]}


STATUS_BY_ALERT = {"CRITICAL": "critical", "WARNING": "watch", "INFO": "recovering"}
ALERT_RANK = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}


def build_overview():
    """Everything the Field Kit overview needs, from the live LoRa database"""
    now = datetime.now()
    conn = sqlite3.connect(settings.LORA_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Latest reading per animal
    cur.execute('''
        SELECT r.* FROM livestock_readings r
        JOIN (SELECT device_id, MAX(id) AS max_id FROM livestock_readings GROUP BY device_id) m
          ON r.id = m.max_id
        ORDER BY r.device_id
    ''')
    latest = {row["device_id"]: dict(row) for row in cur.fetchall()}

    profiles, farms, farm_of = herd_lookup(cur)

    cur.execute("SELECT * FROM alerts WHERE resolved = 0 ORDER BY alert_time DESC")
    open_alerts = [dict(r) for r in cur.fetchall()]

    # Paired bars: alerts raised vs critical, for the 7 days ending on the latest alert day
    cur.execute("SELECT MAX(substr(alert_time, 1, 10)) FROM alerts")
    last_day = cur.fetchone()[0]
    week = []
    if last_day:
        end_day = datetime.fromisoformat(last_day)
        cur.execute('''
            SELECT substr(alert_time, 1, 10) AS day, COUNT(*) AS raised,
                   SUM(CASE WHEN alert_type = 'CRITICAL' THEN 1 ELSE 0 END) AS critical
            FROM alerts WHERE substr(alert_time, 1, 10) > ?
            GROUP BY day
        ''', ((end_day - timedelta(days=7)).date().isoformat(),))
        by_day = {r["day"]: dict(r) for r in cur.fetchall()}
        for i in range(6, -1, -1):
            d = (end_day - timedelta(days=i)).date()
            row = by_day.get(d.isoformat(), {})
            week.append({
                "label": d.strftime("%a"),
                "date": d.strftime("%d %b"),
                "raised": row.get("raised", 0) or 0,
                "critical": row.get("critical", 0) or 0,
            })
    conn.close()

    # Per-animal open alerts
    by_animal = {}
    for a in open_alerts:
        by_animal.setdefault(a["device_id"], []).append(a)

    animals = []
    for device_id, reading in latest.items():
        alerts = sorted(by_animal.get(device_id, []), key=lambda a: ALERT_RANK.get(a["alert_type"], 3))
        worst = alerts[0]["alert_type"] if alerts else None
        status = STATUS_BY_ALERT.get(worst, "healthy")
        profile = profiles.get(device_id, {})
        farm = farm_of.get(device_id)
        seen = _parse_time(reading.get("received_time"))
        temp = reading.get("body_temperature") or reading.get("temperature")
        animals.append({
            "device_id": device_id,
            "name": profile.get("animal_name") or "",
            "breed": profile.get("breed") or "",
            "kind": "Sheep" if device_id.upper().startswith("SHEEP") else "Cow",
            "status": status,
            "condition": _condition(alerts[0]["alert_message"]) if alerts else "Vitals normal",
            "problems": [_condition(x["alert_message"]) for x in alerts],
            "alert_ids": [a["id"] for a in alerts],
            "farm": farm["farm_name"] if farm else "Unassigned",
            "area": (farm.get("location") or "").split(",")[0] if farm else "",
            "owner": farm.get("owner_name") if farm else "",
            "phone": farm.get("contact_phone") if farm else "",
            "temp": round(temp, 1) if temp else None,
            "hr": reading.get("heart_rate"),
            "battery": reading.get("battery"),
            "last_seen": _ago(seen, now),
            "since": _ago(_parse_time(alerts[0]["alert_time"]), now) if alerts else "",
            "lat": reading.get("latitude"),
            "lng": reading.get("longitude"),
        })
    order = {"critical": 0, "watch": 1, "recovering": 2, "healthy": 3}
    animals.sort(key=lambda a: (order[a["status"]], a["device_id"]))

    needs_help = [a for a in animals if a["status"] == "critical"]
    temps = [a["temp"] for a in animals if a["temp"]]
    healthy = sum(1 for a in animals if a["status"] == "healthy")

    # Hotspots: farms ranked by animals that need attention
    hotspot_counts = {}
    for a in animals:
        if a["status"] in ("critical", "watch") and a["farm"] != "Unassigned":
            hotspot_counts[a["farm"]] = hotspot_counts.get(a["farm"], 0) + 1
    farm_area = {f["farm_name"]: (f.get("location") or "").split(",")[0] for f in farms.values()}
    hotspots = sorted(
        [{"farm": k, "area": farm_area.get(k, ""), "count": v} for k, v in hotspot_counts.items()],
        key=lambda h: -h["count"])

    # Farm contacts, with the state of their herd
    contacts = []
    for f in farms.values():
        herd = [a for a in animals if a["farm"] == f["farm_name"]]
        if not herd:
            continue
        flagged = [a for a in herd if a["status"] in ("critical", "watch")]
        state = "critical" if any(a["status"] == "critical" for a in herd) else ("watch" if flagged else "healthy")
        contacts.append({
            "name": f.get("owner_name") or f["farm_name"],
            "farm": f["farm_name"],
            "area": (f.get("location") or "").split(",")[0],
            "phone": f.get("contact_phone") or "",
            "herd": len(herd),
            "flagged": len(flagged),
            "state": state,
        })
    contacts.sort(key=lambda c: ({"critical": 0, "watch": 1, "healthy": 2}[c["state"]], c["name"]))

    for a in open_alerts:
        describe_alert(a, profiles, farm_of, now)

    cities = [f["location"].split(",")[-1].strip() for f in farms.values() if f.get("location")]
    week_raised = sum(d["raised"] for d in week)
    week_critical = sum(d["critical"] for d in week)
    busiest = max(week, key=lambda d: d["raised"]) if week_raised else None

    return {
        "animals": animals,
        "needs_help": needs_help,
        "alerts": open_alerts,
        "week": week,
        "week_max": max([d["raised"] for d in week] + [1]),
        "week_raised": week_raised,
        "week_critical": week_critical,
        "busiest": busiest,
        "hotspots": hotspots,
        "hotspot_max": max([h["count"] for h in hotspots] + [1]),
        "contacts": contacts,
        "kpi": {
            "tracked": len(animals),
            "attention": sum(1 for a in animals if a["status"] in ("critical", "watch")),
            "healthy": healthy,
            "healthy_pct": round(100 * healthy / len(animals)) if animals else 0,
            "avg_temp": round(sum(temps) / len(temps), 1) if temps else None,
            "low_battery": sum(1 for a in animals if (a["battery"] or 100) < 50),
        },
        "today": now,
        "city": max(cities, key=cities.count) if cities else "",
    }


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, _: bool = Depends(require_auth)):
    """Dashboard home: the Field Kit overview"""
    try:
        overview = build_overview()
    except Exception as e:
        print(f"Error building overview: {e}")
        overview = None

    return templates.TemplateResponse("dashboard/home.html", {
        "request": request,
        "o": overview,
        "show_sidebar": True
    })

@router.get("/animals", response_class=HTMLResponse)
async def animals_list(request: Request, _: bool = Depends(require_auth)):
    """Every collared animal, with its latest reading and status"""
    try:
        overview = build_overview()
    except Exception as e:
        print(f"Error fetching animals: {e}")
        overview = None

    return templates.TemplateResponse("dashboard/animals.html", {
        "request": request,
        "o": overview,
        "show_sidebar": True
    })

@router.get("/animals/{device_id}", response_class=HTMLResponse)
async def animal_detail(request: Request, device_id: str, _: bool = Depends(require_auth)):
    """Individual animal profile"""
    now = datetime.now()
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Latest reading
        cursor.execute('''
            SELECT * FROM livestock_readings
            WHERE device_id = ?
            ORDER BY id DESC
            LIMIT 1
        ''', (device_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Animal not found")
        latest = dict(result)

        # The 24 hours leading up to the latest reading (data may be older than "now")
        cursor.execute('''
            SELECT timestamp, received_time, temperature, body_temperature, ambient_temperature,
                   heart_rate, motion_magnitude, battery
            FROM livestock_readings
            WHERE device_id = ?
            AND datetime(received_time) > datetime(?, '-24 hours')
            ORDER BY id ASC
        ''', (device_id, latest["received_time"]))
        history = [dict(row) for row in cursor.fetchall()]
        # Thin to ~150 points so the charts stay readable
        step = max(1, len(history) // 150)
        history = history[::step]

        # Alerts for this animal
        cursor.execute('''
            SELECT * FROM alerts
            WHERE device_id = ?
            ORDER BY alert_time DESC
            LIMIT 20
        ''', (device_id,))
        alerts = [dict(row) for row in cursor.fetchall()]

        profiles, _farms, farm_of = herd_lookup(cursor)
        history = animal_history(cursor, device_id)
        conn.close()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching animal detail: {e}")
        raise HTTPException(status_code=500, detail="Error fetching animal data")

    for a in alerts:
        describe_alert(a, profiles, farm_of, now)
    open_alerts = sorted([a for a in alerts if not a["resolved"]],
                         key=lambda a: ALERT_RANK.get(a["alert_type"], 3))
    profile = profiles.get(device_id, {})
    farm = farm_of.get(device_id)

    return templates.TemplateResponse("dashboard/animal_detail.html", {
        "history": history,
        "request": request,
        "animal": latest,
        "history": history,
        "alerts": alerts,
        "profile": {
            "name": profile.get("animal_name") or "",
            "breed": profile.get("breed") or "",
            "kind": "Sheep" if device_id.upper().startswith("SHEEP") else "Cow",
            "farm": farm,
            "status": STATUS_BY_ALERT.get(open_alerts[0]["alert_type"], "healthy") if open_alerts else "healthy",
            "condition": open_alerts[0]["condition"] if open_alerts else "Vitals normal",
            "open_count": len(open_alerts),
            "last_seen": _ago(_parse_time(latest.get("received_time")), now),
        },
        "show_sidebar": True
    })

def contact_report(cur, device_id, now, base=None):
    """Everything about one animal that goes to a vet: (animal dict, list of current problems)"""
    cur.execute("SELECT * FROM livestock_readings WHERE device_id = ? ORDER BY id DESC LIMIT 1", (device_id,))
    row = cur.fetchone()
    if not row:
        return None, []
    latest = dict(row)
    cur.execute("SELECT * FROM alerts WHERE device_id = ? AND resolved = 0", (device_id,))
    open_alerts = sorted([dict(r) for r in cur.fetchall()], key=lambda a: ALERT_RANK.get(a["alert_type"], 3))
    profiles, _farms, farm_of = herd_lookup(cur)
    profile = profiles.get(device_id, {})
    farm = farm_of.get(device_id)
    temp = latest.get("body_temperature") or latest.get("temperature")
    problems = [_condition(a["alert_message"]) for a in open_alerts]
    animal = {
        "device_id": device_id,
        "name": profile.get("animal_name") or "",
        "breed": profile.get("breed") or "",
        "kind": "Sheep" if device_id.upper().startswith("SHEEP") else "Cow",
        "condition": problems[0] if problems else "Needs a check-up",
        "temp": round(temp, 1) if temp else None,
        "hr": latest.get("heart_rate"),
        "battery": latest.get("battery"),
        "last_seen": _ago(_parse_time(latest.get("received_time")), now),
        "since": _ago(_parse_time(open_alerts[0]["alert_time"]), now) if open_alerts else "",
        "farm": farm["farm_name"] if farm else "",
        "area": (farm.get("location") or "").split(",")[0] if farm else "",
        "owner": farm.get("owner_name") if farm else "",
        "phone": farm.get("contact_phone") if farm else "",
        "lat": latest.get("latitude"),
        "lng": latest.get("longitude"),
        "history": animal_history(cur, device_id),
        "report_link": report_link(device_id, base),
    }
    return animal, problems


@router.get("/animals/{device_id}/report.pdf")
def animal_report_pdf(request: Request, device_id: str, _: bool = Depends(require_auth)):
    """Full health report with graphs and history, as a PDF"""
    pdf = build_pdf(device_id, report_link(device_id, str(request.base_url)))
    if not pdf:
        return JSONResponse({"detail": "Animal not found"}, status_code=404)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="health-report-{device_id}.pdf"'})


@router.get("/animals/{device_id}/vets")
async def animal_vets(request: Request, device_id: str, _: bool = Depends(require_auth)):
    """Nearby vet hospitals for this animal, nearest first, each with a ready-to-send WhatsApp message"""
    conn = sqlite3.connect(settings.LORA_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        animal, problems = contact_report(conn.cursor(), device_id, datetime.now(), str(request.base_url))
    finally:
        conn.close()
    if not animal:
        return JSONResponse({"detail": "Animal not found"}, status_code=404)
    near = ", ".join(x for x in [animal["farm"], animal["area"]] if x)
    return {
        "animal": animal["name"] or animal["device_id"],
        "problem": animal["condition"],
        # Where the distances are measured from: the collar's last GPS position
        "near": near,
        "map": f"https://maps.google.com/?q={animal['lat']:.5f},{animal['lng']:.5f}" if animal["lat"] is not None else "",
        "last_seen": animal["last_seen"],
        "vets": vet_options(animal, problems),
        "report_pdf": f"/dashboard/animals/{device_id}/report.pdf",
        "report_link": animal["report_link"],
        "whatsapp_to": demo_whatsapp_to(),
    }


@router.get("/map", response_class=HTMLResponse)
async def live_map(request: Request, _: bool = Depends(require_auth)):
    """Live map with all animals"""
    try:
        animals = build_overview()["animals"]
    except Exception as e:
        print(f"Error loading animals for map: {e}")
        animals = []
    return templates.TemplateResponse("dashboard/map.html", {
        "request": request,
        "animals": animals,
        "show_sidebar": True
    })

@router.get("/alerts", response_class=HTMLResponse)
async def alerts_page(request: Request, _: bool = Depends(require_auth)):
    """Alerts management page"""
    now = datetime.now()
    try:
        conn = sqlite3.connect(settings.LORA_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM alerts
            ORDER BY resolved ASC, alert_time DESC
            LIMIT 200
        ''')
        alerts = [dict(row) for row in cursor.fetchall()]
        profiles, _farms, farm_of = herd_lookup(cursor)
        conn.close()
        for a in alerts:
            describe_alert(a, profiles, farm_of, now)
    except Exception as e:
        print(f"Error fetching alerts: {e}")
        alerts = []

    return templates.TemplateResponse("dashboard/alerts.html", {
        "request": request,
        "alerts": alerts,
        "show_sidebar": True
    })

def build_trends(days):
    """Health trends over `days`, counted back from the newest reading (data may be older than today)"""
    conn = sqlite3.connect(settings.LORA_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT MAX(received_time) FROM livestock_readings")
    newest = cur.fetchone()[0]
    if not newest:
        conn.close()
        return None
    end = _parse_time(newest)
    start = end - timedelta(days=days)
    start_s = start.strftime("%Y-%m-%d %H:%M:%S")
    end_s = end.strftime("%Y-%m-%d %H:%M:%S")

    # Hourly buckets for a single day, daily otherwise
    bucket = "%Y-%m-%d %H:00" if days <= 1 else "%Y-%m-%d"
    cur.execute(f'''
        SELECT strftime('{bucket}', received_time) AS t,
               ROUND(AVG(COALESCE(body_temperature, temperature)), 2) AS avg_temp,
               ROUND(MIN(COALESCE(body_temperature, temperature)), 2) AS min_temp,
               ROUND(MAX(COALESCE(body_temperature, temperature)), 2) AS max_temp,
               ROUND(AVG(heart_rate), 1) AS avg_hr,
               COUNT(*) AS n
        FROM livestock_readings
        WHERE received_time > ? AND received_time <= ?
        GROUP BY t ORDER BY t
    ''', (start_s, end_s))
    series = [dict(r) for r in cur.fetchall()]

    cur.execute('''
        SELECT SUM(CASE WHEN heart_rate < 48 THEN 1 ELSE 0 END) AS low,
               SUM(CASE WHEN heart_rate BETWEEN 48 AND 75 THEN 1 ELSE 0 END) AS normal,
               SUM(CASE WHEN heart_rate BETWEEN 76 AND 80 THEN 1 ELSE 0 END) AS elevated,
               SUM(CASE WHEN heart_rate > 80 THEN 1 ELSE 0 END) AS high,
               COUNT(heart_rate) AS total
        FROM livestock_readings
        WHERE received_time > ? AND received_time <= ? AND heart_rate IS NOT NULL
    ''', (start_s, end_s))
    hr = dict(cur.fetchone())

    cur.execute('''
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN COALESCE(body_temperature, temperature) > 39.3 THEN 1 ELSE 0 END) AS feverish
        FROM livestock_readings
        WHERE received_time > ? AND received_time <= ?
    ''', (start_s, end_s))
    readings = dict(cur.fetchone())

    # Alerts in the same window (alert_time uses ISO "T" format)
    a_start, a_end = start.isoformat(), (end + timedelta(minutes=1)).isoformat()
    cur.execute('''
        SELECT substr(alert_time, 1, 10) AS day,
               SUM(CASE WHEN alert_type = 'CRITICAL' THEN 1 ELSE 0 END) AS critical,
               SUM(CASE WHEN alert_type = 'WARNING' THEN 1 ELSE 0 END) AS warning,
               SUM(CASE WHEN alert_type NOT IN ('CRITICAL', 'WARNING') THEN 1 ELSE 0 END) AS info
        FROM alerts WHERE alert_time > ? AND alert_time <= ?
        GROUP BY day ORDER BY day
    ''', (a_start, a_end))
    alert_days = {r["day"]: dict(r) for r in cur.fetchall()}
    alerts_by_day = []
    d = start.date()
    while d <= end.date():
        row = alert_days.get(d.isoformat(), {})
        alerts_by_day.append({"day": d.isoformat(), "critical": row.get("critical") or 0,
                              "warning": row.get("warning") or 0, "info": row.get("info") or 0})
        d += timedelta(days=1)

    cur.execute('''
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN resolved = 0 THEN 1 ELSE 0 END) AS open,
               SUM(CASE WHEN alert_type = 'CRITICAL' THEN 1 ELSE 0 END) AS critical
        FROM alerts WHERE alert_time > ? AND alert_time <= ?
    ''', (a_start, a_end))
    alert_sum = {k: (v or 0) for k, v in dict(cur.fetchone()).items()}

    cur.execute('''
        SELECT device_id, COUNT(*) AS total,
               SUM(CASE WHEN alert_type = 'CRITICAL' THEN 1 ELSE 0 END) AS critical,
               SUM(CASE WHEN resolved = 0 THEN 1 ELSE 0 END) AS open
        FROM alerts WHERE alert_time > ? AND alert_time <= ?
        GROUP BY device_id ORDER BY critical DESC, total DESC LIMIT 8
    ''', (a_start, a_end))
    top = [dict(r) for r in cur.fetchall()]
    profiles, _farms, farm_of = herd_lookup(cur)
    conn.close()

    for t in top:
        t["name"] = profiles.get(t["device_id"], {}).get("animal_name") or ""
        farm = farm_of.get(t["device_id"])
        t["farm"] = farm["farm_name"] if farm else ""

    temps = [s["avg_temp"] for s in series if s["avg_temp"] is not None]
    return {
        "days": days,
        "start": start,
        "end": end,
        "stale_days": (datetime.now() - end).days,
        "series": series,
        "hr": hr,
        "readings": readings,
        "fever_pct": round(100 * (readings["feverish"] or 0) / readings["total"], 1) if readings["total"] else 0,
        "avg_temp": round(sum(temps) / len(temps), 2) if temps else None,
        "alerts_by_day": alerts_by_day,
        "alert_sum": alert_sum,
        "top": top,
    }


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, days: int = 7, _: bool = Depends(require_auth)):
    """Health trends page"""
    days = days if days in (1, 7, 30) else 7
    try:
        trends = build_trends(days)
    except Exception as e:
        print(f"Error building trends: {e}")
        trends = None
    return templates.TemplateResponse("dashboard/analytics.html", {
        "request": request,
        "t": trends,
        "show_sidebar": True
    })

@router.get("/ml-insights", response_class=HTMLResponse)
async def ml_insights_page(request: Request, _: bool = Depends(require_auth)):
    """ML-powered disease detection and predictions"""
    try:
        animals = build_overview()["animals"]
    except Exception as e:
        print(f"Error loading animals for AI page: {e}")
        animals = []
    return templates.TemplateResponse("dashboard/ml_insights.html", {
        "request": request,
        "animals": animals,
        "show_sidebar": True
    })
