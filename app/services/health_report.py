"""
Full health report for one animal, as a PDF a vet can read on a phone.

Everything comes from the herd database: profile, farm and owner, the problem right now,
latest vitals against the normal range, graphs (last 24 hours, last 30 days, past 12 months
with illnesses shaded), the year's health history and alert log, and where the animal is.

Reports can also be shared with a signed link (/r/<token>) that works without signing in
and expires after REPORT_LINK_DAYS days.
"""
import base64
import hashlib
import hmac
import io
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # no screen on a server
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

from app.config import settings

TEMP_RANGE = (38.0, 39.3)  # same normal ranges as the animal page
HR_RANGE = (48, 75)
REPORT_LINK_DAYS = int(os.getenv("REPORT_LINK_DAYS", "7"))

INK = colors.HexColor("#1F2A1F")
MUTED = colors.HexColor("#5A6457")
BRAND = colors.HexColor("#3F7D2A")
EMERG = colors.HexColor("#C2410C")
LINE = colors.HexColor("#DDD4C3")
TINT = colors.HexColor("#F4EFE6")


# ── Share links ─────────────────────────────────────────────

def _secret():
    """REPORT_SECRET from .env, else one generated once and kept next to the database"""
    s = os.getenv("REPORT_SECRET", "").strip()
    if s:
        return s.encode()
    path = Path(settings.LORA_DB_PATH).resolve().parent / ".report_secret"
    if not path.exists():
        # Owner-only from the moment it is created (O_EXCL: never reuse a file someone else planted)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(secrets.token_urlsafe(32))
        except FileExistsError:
            pass  # created by another worker in the meantime
    return path.read_text().strip().encode()


def report_token(device_id):
    expires = int(time.time()) + REPORT_LINK_DAYS * 86400
    payload = f"{device_id}|{expires}"
    sig = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()[:24]
    return base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode().rstrip("=")


def device_from_token(token):
    """The device id a share link is for, or None if it's forged or expired"""
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode()
        device_id, expires, sig = raw.rsplit("|", 2)
        good = hmac.new(_secret(), f"{device_id}|{expires}".encode(), hashlib.sha256).hexdigest()[:24]
        if hmac.compare_digest(sig, good) and int(expires) > time.time():
            return device_id
    except Exception:
        pass
    return None


def public_base_url(request_base=None):
    """Where a phone can reach this dashboard: PUBLIC_BASE_URL, else the address the farmer
    opened it on (works on the Wi-Fi), else this machine on the LAN"""
    url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if url:
        return url
    if request_base and not any(h in request_base for h in ("localhost", "127.0.0.1")):
        return request_base.rstrip("/")
    return f"http://{settings.RPI_HOST}:{settings.PORT}"


def report_link(device_id, request_base=None):
    return f"{public_base_url(request_base)}/r/{report_token(device_id)}"


# ── Data ────────────────────────────────────────────────────

def _q(cur, sql, args=()):
    cur.execute(sql, args)
    return [dict(r) for r in cur.fetchall()]


def gather(device_id):
    conn = sqlite3.connect(settings.LORA_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        latest = _q(cur, "SELECT * FROM livestock_readings WHERE device_id = ? ORDER BY id DESC LIMIT 1", (device_id,))
        if not latest:
            return None
        latest = latest[0]
        end = datetime.fromisoformat(latest["received_time"])
        profile = (_q(cur, "SELECT * FROM animal_profiles WHERE device_id = ?", (device_id,)) or [{}])[0]
        farm = (_q(cur, """SELECT f.* FROM farms f JOIN farm_animals fa ON fa.farm_id = f.id
                           WHERE fa.device_id = ? AND fa.is_active = 1""", (device_id,)) or [{}])[0]
        day = _q(cur, """SELECT received_time t, COALESCE(body_temperature, temperature) temp, heart_rate hr, motion_magnitude motion
                         FROM livestock_readings WHERE device_id = ? AND received_time > ? ORDER BY id""",
                 (device_id, (end - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")))
        month = _q(cur, """SELECT substr(received_time, 1, 10) d,
                                  AVG(COALESCE(body_temperature, temperature)) temp, MIN(COALESCE(body_temperature, temperature)) tmin,
                                  MAX(COALESCE(body_temperature, temperature)) tmax, AVG(heart_rate) hr, MAX(heart_rate) hrmax,
                                  AVG(motion_magnitude) motion
                           FROM livestock_readings WHERE device_id = ? AND received_time > ? GROUP BY d ORDER BY d""",
                   (device_id, (end - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")))
        year = _q(cur, """SELECT strftime('%Y-%W', received_time) w, MIN(received_time) t,
                                 AVG(COALESCE(body_temperature, temperature)) temp, MAX(COALESCE(body_temperature, temperature)) tmax,
                                 AVG(heart_rate) hr
                          FROM livestock_readings WHERE device_id = ? AND received_time > ? GROUP BY w ORDER BY w""",
                  (device_id, (end - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")))
        history = []
        if _q(cur, "SELECT 1 FROM sqlite_master WHERE type='table' AND name='health_history'"):
            history = _q(cur, """SELECT * FROM health_history WHERE device_id = ? AND event_date > ?
                                 ORDER BY event_date""", (device_id, (end - timedelta(days=365)).strftime("%Y-%m-%d")))
        alerts = _q(cur, """SELECT * FROM alerts WHERE device_id = ? AND alert_time > ? ORDER BY alert_time DESC""",
                    (device_id, (end - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")))
    finally:
        conn.close()
    return {"device_id": device_id, "latest": latest, "end": end, "profile": profile, "farm": farm,
            "day": day, "month": month, "year": year, "history": history, "alerts": alerts}


# ── Graphs ──────────────────────────────────────────────────

def _style(ax, title, unit):
    ax.set_title(title, loc="left", fontsize=10, color="#1F2A1F", fontweight="bold")
    ax.set_ylabel(unit, fontsize=8, color="#5A6457")
    ax.tick_params(labelsize=7, colors="#5A6457")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#DDD4C3")
    ax.grid(axis="y", color="#EAE3D5", linewidth=0.6)


def _png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def chart_24h(d):
    t = [datetime.fromisoformat(r["t"]) for r in d["day"]]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 4.2), sharex=True)
    a1.axhspan(*TEMP_RANGE, color="#E3EDD5", zorder=0)
    a1.plot(t, [r["temp"] for r in d["day"]], color="#C2410C", linewidth=1.4)
    _style(a1, "Body temperature, last 24 hours", "°C")
    a2.axhspan(*HR_RANGE, color="#E3EDD5", zorder=0)
    a2.plot(t, [r["hr"] for r in d["day"]], color="#1F7A3D", linewidth=1.2)
    _style(a2, "Heart rate, last 24 hours", "bpm")
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.tight_layout()
    return _png(fig)


def chart_30d(d):
    t = [datetime.fromisoformat(r["d"]) for r in d["month"]]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 4.0), sharex=True)
    a1.axhspan(*TEMP_RANGE, color="#E3EDD5", zorder=0)
    a1.fill_between(t, [r["tmin"] for r in d["month"]], [r["tmax"] for r in d["month"]], color="#F0C9AE", alpha=0.7, label="daily range")
    a1.plot(t, [r["temp"] for r in d["month"]], color="#C2410C", linewidth=1.4, label="daily average")
    a1.legend(fontsize=7, frameon=False, loc="upper left")
    _style(a1, "Body temperature, last 30 days", "°C")
    a2.axhspan(*HR_RANGE, color="#E3EDD5", zorder=0)
    a2.bar(t, [r["hr"] for r in d["month"]], color="#6F9E55", width=0.7, label="daily average")
    a2.plot(t, [r["hrmax"] for r in d["month"]], color="#1F7A3D", linewidth=1, marker=".", markersize=3, label="daily peak")
    a2.legend(fontsize=7, frameon=False, loc="upper left")
    _style(a2, "Heart rate, last 30 days", "bpm")
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    fig.tight_layout()
    return _png(fig)


def chart_year(d):
    t = [datetime.fromisoformat(r["t"]) for r in d["year"]]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 4.0), sharex=True)
    # Shade every past illness, from its start to its recovery
    events = d["history"]
    for i, e in enumerate(events):
        if e["event_type"] != "illness":
            continue
        end = next((x for x in events[i + 1:] if x["event_type"] == "recovery"), None)
        s = datetime.fromisoformat(e["event_date"])
        f = datetime.fromisoformat(end["event_date"]) if end else d["end"]
        for ax in (a1, a2):
            ax.axvspan(s, f, color="#FBE6D9", zorder=0)
        a1.annotate(e["title"].split(" (")[0], (s, 1), xycoords=("data", "axes fraction"), fontsize=6,
                    color="#9A3309", va="top", rotation=90)
    a1.plot(t, [r["temp"] for r in d["year"]], color="#C2410C", linewidth=1.3, label="weekly average")
    a1.plot(t, [r["tmax"] for r in d["year"]], color="#C2410C", linewidth=0.8, linestyle=":", label="weekly highest")
    a1.legend(fontsize=7, frameon=False, loc="lower left")
    _style(a1, "Body temperature, past 12 months (illnesses shaded)", "°C")
    a2.plot(t, [r["hr"] for r in d["year"]], color="#1F7A3D", linewidth=1.3)
    _style(a2, "Heart rate, past 12 months (weekly average)", "bpm")
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    fig.tight_layout()
    return _png(fig)


# ── PDF ─────────────────────────────────────────────────────

def _fmt_date(v, with_time=False):
    try:
        return datetime.fromisoformat(str(v)).strftime("%d %b %Y, %H:%M" if with_time else "%d %b %Y")
    except ValueError:
        return str(v)


def _age(birth):
    try:
        days = (datetime.now() - datetime.fromisoformat(birth)).days
        return f"{days // 365} years {days % 365 // 30} months"
    except (TypeError, ValueError):
        return "Not recorded"


def build_pdf(device_id, link=None):
    d = gather(device_id)
    if not d:
        return None
    ss = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12.5, textColor=INK)
    small = ParagraphStyle("s", parent=body, fontSize=7.5, leading=10, textColor=MUTED)
    h1 = ParagraphStyle("h1", parent=body, fontName="Helvetica-Bold", fontSize=18, leading=22)
    h2 = ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=12, leading=15, spaceBefore=10, spaceAfter=5)
    eyebrow = ParagraphStyle("e", parent=small, fontName="Helvetica-Bold", textColor=BRAND)

    p, f, latest = d["profile"], d["farm"], d["latest"]
    name = p.get("animal_name") or device_id
    kind = "Sheep" if device_id.upper().startswith("SHEEP") else "Cow"
    temp = latest.get("body_temperature") or latest.get("temperature")
    hr = latest.get("heart_rate")
    open_alerts = [a for a in d["alerts"] if not a["resolved"]]
    lat, lng = latest.get("latitude"), latest.get("longitude")
    map_url = f"https://maps.google.com/?q={lat:.5f},{lng:.5f}" if lat is not None else ""

    def table(rows, widths, header=True, zebra=True):
        t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
        style = [("FONT", (0, 0), (-1, -1), "Helvetica", 8.5), ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                 ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4),
                 ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE)]
        if header:
            style += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5), ("BACKGROUND", (0, 0), (-1, 0), TINT)]
        t.setStyle(TableStyle(style))
        return t

    W = 180 * mm
    story = [
        Paragraph("PAWTRACK · ANIMAL HEALTH REPORT", eyebrow),
        Paragraph(f"{name} <font size=11 color='#5A6457'>({device_id})</font>", h1),
        Paragraph(f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')} · readings up to {_fmt_date(d['end'], True)}", small),
        Spacer(1, 6),
    ]
    if open_alerts:
        worst = open_alerts[0]
        tone = EMERG if any(a["alert_type"] == "CRITICAL" for a in open_alerts) else colors.HexColor("#B7791F")
        banner = Table([[Paragraph(f"<b>Needs attention:</b> " + "; ".join(a["alert_message"] for a in open_alerts[:4]) +
                                   f" (first raised {_fmt_date(worst['alert_time'], True)})", ParagraphStyle("w", parent=body, textColor=colors.white))]],
                       colWidths=[W])
        banner.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), tone), ("LEFTPADDING", (0, 0), (-1, -1), 8),
                                    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story += [banner, Spacer(1, 8)]

    # Animal and owner
    story.append(Paragraph("Animal and owner", h2))
    story.append(table([
        ["Animal", f"{name} · {(p.get('breed') + ' ') if p.get('breed') else ''}{kind.lower()}", "Farm", f.get("farm_name", "Not assigned")],
        ["Collar ID", device_id, "Farm location", f.get("location", "")],
        ["Age", _age(p.get("birth_date")), "Owner", f.get("owner_name", "")],
        ["Lactation", f"#{p['lactation_number']}" if p.get("lactation_number") else "—", "Owner phone", f.get("contact_phone", "")],
        ["Last calving", _fmt_date(p["last_calving_date"]) if p.get("last_calving_date") else "—", "Last GPS",
         Paragraph(f"{lat:.5f}, {lng:.5f}<br/><link href='{map_url}' color='#3F7D2A'>Open in Google Maps</link>" if map_url else "—", body)],
    ], [28 * mm, 62 * mm, 28 * mm, 62 * mm], header=False))

    # Vitals now
    def judge(v, lo, hi):
        if v is None:
            return "—"
        return "High" if v > hi else "Low" if v < lo else "Normal"
    month = d["month"]
    avg30 = lambda k: sum(r[k] for r in month if r[k] is not None) / max(1, len(month))
    story.append(Paragraph("Vitals now", h2))
    story.append(table([
        ["Measure", "Latest", "Normal range", "Status", "30-day average"],
        ["Body temperature", f"{temp:.1f} °C" if temp else "—", f"{TEMP_RANGE[0]}–{TEMP_RANGE[1]} °C", judge(temp, *TEMP_RANGE), f"{avg30('temp'):.1f} °C"],
        ["Heart rate", f"{hr} bpm" if hr else "—", f"{HR_RANGE[0]}–{HR_RANGE[1]} bpm", judge(hr, *HR_RANGE), f"{avg30('hr'):.0f} bpm"],
        ["Activity", f"{latest.get('motion_magnitude') or 0:.2f} g", "0.6–1.2 g", judge(latest.get("motion_magnitude"), 0.6, 1.2), f"{avg30('motion'):.2f} g"],
        ["Surroundings", f"{latest.get('ambient_temperature') or 0:.0f} °C, {latest.get('humidity') or 0:.0f}% humidity", "", "", ""],
        ["Collar battery", f"{latest.get('battery')}%", "", "Low" if (latest.get("battery") or 100) < 30 else "OK", ""],
    ], [38 * mm, 38 * mm, 34 * mm, 24 * mm, 46 * mm]))

    # Graphs
    story.append(Paragraph("Graphs", h2))
    story.append(Paragraph("Green bands show the normal range.", small))
    if d["day"]:
        story.append(Image(chart_24h(d), width=W, height=W * 4.2 / 7.2))
    if month:
        story.append(KeepTogether([Image(chart_30d(d), width=W, height=W * 4.0 / 7.2)]))
    if d["year"]:
        story.append(KeepTogether([Image(chart_year(d), width=W, height=W * 4.0 / 7.2)]))

    # Health history
    story.append(Paragraph("Health history, past 12 months", h2))
    if d["history"]:
        rows = [["Date", "Type", "Event", "Details", "Vet"]]
        for e in reversed(d["history"]):
            rows.append([_fmt_date(e["event_date"]), e["event_type"].capitalize(), Paragraph(e["title"], body),
                         Paragraph(e.get("details") or "", body), Paragraph(e.get("vet_name") or "", small)])
        story.append(table(rows, [22 * mm, 22 * mm, 38 * mm, 66 * mm, 32 * mm]))
    else:
        story.append(Paragraph("No health records yet.", body))

    # Alert log
    story.append(Paragraph(f"Collar alerts, past 12 months ({len(d['alerts'])})", h2))
    if d["alerts"]:
        rows = [["Raised", "Level", "Alert", "Temp", "Heart rate", "Status"]]
        for a in d["alerts"]:
            rows.append([_fmt_date(a["alert_time"], True), a["alert_type"].capitalize(), Paragraph(a["alert_message"], body),
                         f"{a['temperature']:.1f} °C" if a.get("temperature") else "", f"{a['heart_rate']} bpm" if a.get("heart_rate") else "",
                         "Resolved" if a["resolved"] else "Open"])
        story.append(table(rows, [32 * mm, 18 * mm, 66 * mm, 20 * mm, 22 * mm, 22 * mm]))

    story += [Spacer(1, 10), Paragraph(
        "Readings come from the animal's collar sensors and are summaries, not a diagnosis. "
        "Please call the owner to confirm the animal's condition." + (f" Online copy: <link href='{link}' color='#3F7D2A'>{link}</link>" if link else ""), small)]

    buf = io.BytesIO()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(15 * mm, 10 * mm, f"PawTrack health report · {name} ({device_id})")
        canvas.drawRightString(195 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
                            title=f"Health report – {name} ({device_id})", author="PawTrack")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
