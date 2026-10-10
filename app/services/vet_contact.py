"""
Reach a vet about a sick animal.

Nearby vet hospitals come from PawTrack's hospital search (PAWTRACK_API_URL), nearest first,
using the animal's last GPS position; the farmer picks who to contact. If PawTrack can't be
reached, VET_NAME / VET_PHONE from .env are offered instead. Each WhatsApp link opens a chat
with the animal's details and past year already typed in; the farmer just presses send.
WHATSAPP_TO (e.g. for a demo) sends every WhatsApp message to that one number instead.
"""
import os
import re
import time
from datetime import datetime
from urllib.parse import quote

import requests

PAWTRACK_API_URL = os.getenv("PAWTRACK_API_URL", "http://localhost:5000/api").rstrip("/")
_CACHE_SECONDS = 600
_cache = {}


def _fallback_vets():
    phone = os.getenv("VET_PHONE", "").strip()
    return [{"name": os.getenv("VET_NAME", "Your vet"), "phone": phone, "whatsapp": phone, "distance_km": None, "area": ""}] if phone else []


def nearby_vets(lat, lng, limit=6):
    """Vet hospitals with a phone number, nearest first (or the .env fallback)"""
    if lat is None or lng is None:
        return _fallback_vets()
    key = (round(float(lat), 2), round(float(lng), 2))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < _CACHE_SECONDS:
        return hit[1]
    try:
        res = requests.get(f"{PAWTRACK_API_URL}/clinics", params={"lat": lat, "lng": lng}, timeout=4)
        res.raise_for_status()
        vets = [{
            "name": c.get("name", "Vet hospital"),
            "phone": c.get("phone") or c.get("whatsappPhone"),
            "whatsapp": c.get("whatsappPhone") or c.get("phone"),
            "distance_km": c.get("distanceKm"),
            "area": c.get("area") or "",
            "open_24h": bool(c.get("isOpen24Hours")),
        } for c in res.json().get("data", []) if c.get("phone") or c.get("whatsappPhone")][:limit]
    except Exception as e:  # PawTrack offline: fall back, and try again on the next request
        print(f"Vet lookup via PawTrack failed: {e}")
        return _fallback_vets()
    vets = vets or _fallback_vets()
    _cache[key] = (time.time(), vets)
    return vets


def _wa_number(phone):
    """WhatsApp wants the full international number, digits only (Indian numbers get 91)"""
    digits = re.sub(r"\D", "", phone or "")
    return "91" + digits if len(digits) == 10 else digits


def _d(value):
    """'2026-06-25 08:47:00' -> '25 Jun 2026'"""
    try:
        return datetime.fromisoformat(str(value)).strftime("%d %b %Y")
    except ValueError:
        return str(value)[:10]


def history_lines(h):
    """The past year, condensed for the vet: illnesses with treatment, vaccinations, breeding, vitals"""
    if not h:
        return []
    events = h.get("events", [])  # oldest first
    lines = ["", "History (past 12 months):"]
    illnesses = []
    for i, e in enumerate(events):
        if e["event_type"] != "illness":
            continue
        later = events[i + 1:]
        treat = next((x for x in later if x["event_type"] == "treatment"), None)
        rec = next((x for x in later if x["event_type"] == "recovery"), None)
        text = f"- {_d(e['event_date'])}: {e['title']}"
        if treat:
            text += f". Treated by {treat['vet_name'] or 'vet'}: {treat['details']}"
        text += f". Recovered {_d(rec['event_date'])}" if rec else ". Still under treatment"
        illnesses.append(text)
    lines += illnesses[::-1] or ["- No illnesses recorded"]

    def latest(kind, title=None):
        found = [x for x in events if x["event_type"] == kind and (title is None or x["title"] == title)]
        return found[-1] if found else None

    vacc = [x for x in events if x["event_type"] == "vaccination"]
    seen, parts = set(), []
    for x in reversed(vacc):
        if x["title"] not in seen:
            seen.add(x["title"])
            parts.append(f"{x['title'].replace(' vaccination', '')} {_d(x['event_date'])}")
    if parts:
        lines.append("Vaccinations: " + ", ".join(parts))
    dw = latest("deworming")
    if dw:
        lines.append(f"Last deworming: {_d(dw['event_date'])} ({dw['details']})")
    breeding = [f"{x['title']} {_d(x['event_date'])}" for x in events if x["event_type"] in ("breeding", "shearing")]
    if breeding:
        lines.append("Breeding / care: " + "; ".join(breeding))
    ck = latest("checkup")
    if ck:
        lines.append(f"Last check-up {_d(ck['event_date'])}: {ck['details']}")
    v = h.get("vitals30")
    if v and v.get("avg_temp"):
        lines.append(f"Last 30 days: avg temp {v['avg_temp']}°C (highest {v['max_temp']}°C), avg heart rate {v['avg_hr']} bpm, activity {v['avg_motion']}")
    if h.get("alerts_year") is not None:
        lines.append(f"Collar alerts in the past year: {h['alerts_year']}")
    return lines


def animal_report(a, problems):
    """The message the vet receives: who, what's wrong, vitals, history, where, who to call back"""
    name = f"{a['name']} ({a['device_id']})" if a.get("name") else a["device_id"]
    kind = " ".join(x for x in [a.get("breed"), a.get("kind")] if x)
    lines = [
        "PawTrack livestock alert: an animal needs a vet",
        "",
        f"Animal: {name}" + (f", {kind}" if kind else ""),
        f"Problem: {problems[0]}" if problems else f"Problem: {a.get('condition', 'Needs checking')}",
    ]
    if len(problems) > 1:
        lines.append("Also: " + "; ".join(problems[1:4]))
    vitals = []
    if a.get("temp") is not None:
        vitals.append(f"body temp {a['temp']}°C")
    if a.get("hr"):
        vitals.append(f"heart rate {a['hr']} bpm")
    if a.get("battery") is not None:
        vitals.append(f"collar battery {a['battery']}%")
    if vitals:
        lines.append("Latest vitals: " + ", ".join(vitals) + (f" (reported {a['last_seen']} ago)" if a.get("last_seen") else ""))
    if a.get("since"):
        lines.append(f"Alert raised: {a['since']} ago")
    farm = ", ".join(x for x in [a.get("farm"), a.get("area")] if x and x != "Unassigned")
    if farm:
        lines.append(f"Farm: {farm}")
    if a.get("owner") or a.get("phone"):
        lines.append("Owner: " + " · ".join(x for x in [a.get("owner"), a.get("phone")] if x))
    if a.get("lat") is not None and a.get("lng") is not None:
        lines.append(f"Location: https://maps.google.com/?q={a['lat']:.5f},{a['lng']:.5f}")
    lines += history_lines(a.get("history"))
    lines += ["", "Please call back to advise or arrange a visit."]
    return "\n".join(lines)


def demo_whatsapp_to():
    return os.getenv("WHATSAPP_TO", "").strip()


def vet_options(a, problems):
    """Nearby vets for this animal, each with a WhatsApp link carrying the report and a call link"""
    text = quote(animal_report(a, problems))
    override = demo_whatsapp_to()
    options = []
    for v in nearby_vets(a.get("lat"), a.get("lng")):
        to = override or v["whatsapp"]
        options.append({**v, "whatsapp_url": f"https://wa.me/{_wa_number(to)}?text={text}", "tel": f"tel:{v['phone']}"})
    return options
