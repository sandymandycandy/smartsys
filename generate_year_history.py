"""
One year of history for every animal (demo data).

Run after generate_demo_data.py (it reuses its herd, farms and current conditions):
    python generate_year_history.py

- Collar readings for the last 365 days: hourly, and every 15 minutes for the last 30 days,
  ending now. Vitals follow each animal's past illnesses and its current condition.
- A health_history table: vaccinations, deworming, check-ups, calving/insemination (cows),
  shearing (sheep), and 2-4 past illnesses each with vet visit, treatment and recovery.
- A resolved alert for every past illness, so the alert history matches.
Replaces livestock_readings, health_history and past (resolved) alerts; keeps current alerts.
"""
import random
import sqlite3
from datetime import datetime, timedelta

from generate_demo_data import DemoDataGenerator, CHENNAI_LAT, CHENNAI_LON

random.seed(2026)
NOW = datetime.now().replace(second=0, microsecond=0)
YEAR_AGO = NOW - timedelta(days=365)
VETS = ["Dr. R. Sundararajan (MVC)", "Dr. Meera Krishnan (Blue Cross)", "Dr. Priya Balan (Adyar)", "Dr. Senthil Kumar (Tambaram)"]

# Past illnesses: vitals while sick, the alert raised, and how the vet treated it
ILLNESSES = {
    "fever": {"temp": 40.4, "hr": 92, "motion": 0.35, "alert": ("CRITICAL", "High temperature detected ({t}°C)"),
              "title": "Fever", "treatment": "Antipyretic (meloxicam) for 3 days and oxytetracycline; kept in shade with extra water"},
    "tick_fever": {"temp": 40.8, "hr": 96, "motion": 0.3, "alert": ("CRITICAL", "High temperature detected ({t}°C)"),
                   "title": "Tick fever (babesiosis)", "treatment": "Diminazene injection, tick dip for the herd, iron supplement"},
    "mastitis": {"temp": 39.8, "hr": 86, "motion": 0.5, "alert": ("WARNING", "Elevated temperature ({t}°C) and reduced activity"),
                 "title": "Mastitis (front-left quarter)", "treatment": "Intramammary antibiotic for 5 days, milk discarded, teat dip after milking", "cows_only": True},
    "lameness": {"temp": None, "hr": 78, "motion": 0.25, "alert": ("WARNING", "Low activity / lethargy detected"),
                 "title": "Lameness (foot rot, hind right)", "treatment": "Hoof trimmed and cleaned, zinc sulphate foot bath, 3-day antibiotic"},
    "heat_stress": {"temp": 39.8, "hr": 88, "motion": 0.5, "alert": ("WARNING", "Heat stress: elevated temp & humidity"),
                    "title": "Heat stress", "treatment": "Moved to shade, sprinklers at noon, electrolytes in water", "summer": True},
    "diarrhoea": {"temp": 39.5, "hr": 84, "motion": 0.45, "alert": ("WARNING", "Elevated temperature ({t}°C) and reduced activity"),
                  "title": "Diarrhoea", "treatment": "Oral rehydration, probiotics, sulpha drug for 3 days"},
}
# Current condition (from generate_demo_data) -> how many days ago it started
CURRENT_START_DAYS = {"fever": 2, "heat_stress": 4, "lethargic": 3, "low_battery": 6, "recovering": 10}


def pick_episodes(device_id, is_sheep):
    """2-4 past illnesses spread over months 1-11 ago, never overlapping"""
    kinds = [k for k, v in ILLNESSES.items() if not (is_sheep and v.get("cows_only"))]
    episodes, used = [], []
    for _ in range(random.randint(2, 4)):
        kind = random.choice(kinds)
        for _try in range(20):
            if ILLNESSES[kind].get("summer"):  # April-June
                start = datetime(NOW.year if NOW.month > 6 else NOW.year - 1, random.randint(4, 6), random.randint(1, 25), 7)
            else:
                start = NOW - timedelta(days=random.randint(35, 340))
            if start < YEAR_AGO + timedelta(days=5) or start > NOW - timedelta(days=30):
                continue
            length = random.randint(3, 9)
            if all(abs((start - s).days) > 20 for s in used):
                used.append(start)
                episodes.append({"kind": kind, "start": start, "end": start + timedelta(days=length), "vet": random.choice(VETS)})
                break
    return sorted(episodes, key=lambda e: e["start"])


def routine_events(device_id, is_sheep, profile):
    """Vaccinations, deworming, check-ups, breeding/shearing across the year"""
    ev = []
    vet = random.choice(VETS)
    first = YEAR_AGO + timedelta(days=random.randint(5, 25))
    for i in range(2):  # FMD every 6 months
        d = first + timedelta(days=182 * i)
        ev.append((d, "vaccination", "FMD vaccination", "Foot-and-mouth disease booster, next due in 6 months", vet))
    d = first + timedelta(days=random.randint(40, 70))
    ev.append((d, "vaccination", "HS vaccination", "Haemorrhagic septicaemia, before monsoon", vet))
    if not is_sheep:
        ev.append((d + timedelta(days=21), "vaccination", "BQ vaccination", "Black quarter, yearly", vet))
    else:
        ev.append((d + timedelta(days=21), "vaccination", "PPR vaccination", "Peste des petits ruminants, every 3 years", vet))
    for q in range(4):  # deworming every 3 months
        dd = first + timedelta(days=30 + 91 * q)
        if dd < NOW:
            ev.append((dd, "deworming", "Deworming", random.choice(["Albendazole", "Fenbendazole", "Ivermectin"]) + " oral dose", ""))
    weight = random.randint(380, 520) if not is_sheep else random.randint(38, 55)
    for m in range(0, 12, 2):  # check-up every 2 months with weight
        dd = YEAR_AGO + timedelta(days=15 + 61 * m // 2 + random.randint(0, 6))
        if dd < NOW:
            weight += random.randint(-4, 9) if not is_sheep else random.randint(-1, 2)
            ev.append((dd, "checkup", "Routine check-up", f"Weight {weight} kg, body condition good, vitals normal", vet))
    if not is_sheep and profile.get("last_calving_date"):
        calved = datetime.fromisoformat(profile["last_calving_date"])
        if calved > YEAR_AGO:
            ev.append((calved, "breeding", "Calved", "Normal delivery, healthy calf; colostrum given within 1 hour", vet))
            if calved + timedelta(days=75) < NOW:
                ev.append((calved + timedelta(days=75), "breeding", "Artificial insemination", "AI with Gir semen; pregnancy check due in 60 days", vet))
    if is_sheep:
        for month in (3, 9):
            dd = datetime(NOW.year if month <= NOW.month else NOW.year - 1, month, 10, 9)
            if YEAR_AGO < dd < NOW:
                ev.append((dd, "shearing", "Shearing", "Fleece shorn, skin checked for ticks", ""))
    return ev


def main():
    gen = DemoDataGenerator()
    conn = sqlite3.connect(gen.db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS health_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT NOT NULL,
        event_date TEXT NOT NULL,
        event_type TEXT NOT NULL,      -- illness | treatment | recovery | vaccination | deworming | checkup | breeding | shearing
        title TEXT NOT NULL,
        details TEXT,
        vet_name TEXT
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_history_device ON health_history(device_id, event_date)")
    cur.execute("DELETE FROM health_history")
    cur.execute("DELETE FROM livestock_readings")
    cur.execute("DELETE FROM alerts WHERE resolved = 1")
    cur.execute("SELECT * FROM animal_profiles")
    profiles = {r["device_id"]: dict(r) for r in cur.fetchall()}

    total = 0
    for device_id in gen.device_ids:
        is_sheep = device_id.startswith("SHEEP")
        base_temp, base_hr = (39.0, 75) if is_sheep else (38.5, 70)
        condition = gen.conditions.get(device_id, "healthy")
        episodes = pick_episodes(device_id, is_sheep)
        cur_start = NOW - timedelta(days=CURRENT_START_DAYS.get(condition, 0)) if condition in CURRENT_START_DAYS else None
        home_lat = CHENNAI_LAT + random.uniform(-0.035, 0.035)
        home_lon = CHENNAI_LON + random.uniform(-0.035, 0.035)

        # History entries
        rows = [(device_id, d.strftime("%Y-%m-%d %H:%M:%S"), t, title, det, v) for d, t, title, det, v in routine_events(device_id, is_sheep, profiles.get(device_id, {}))]
        for e in episodes:
            info = ILLNESSES[e["kind"]]
            peak = info["temp"] or base_temp
            rows += [
                (device_id, e["start"].strftime("%Y-%m-%d %H:%M:%S"), "illness", info["title"],
                 f"Collar alert: temp {peak}°C, heart rate {info['hr']} bpm, activity down", ""),
                (device_id, (e["start"] + timedelta(hours=random.randint(3, 10))).strftime("%Y-%m-%d %H:%M:%S"), "treatment",
                 f"Vet visit: {info['title'].split(' (')[0].lower()}", info["treatment"], e["vet"]),
                (device_id, e["end"].strftime("%Y-%m-%d %H:%M:%S"), "recovery", "Recovered",
                 f"Vitals back to normal after {(e['end'] - e['start']).days} days", e["vet"]),
            ]
            alert_type, msg = info["alert"]
            cur.execute("""INSERT INTO alerts (device_id, alert_type, alert_message, alert_time, resolved,
                           temperature, heart_rate, battery, latitude, longitude) VALUES (?,?,?,?,1,?,?,?,?,?)""",
                        (device_id, alert_type, msg.format(t=peak), e["start"].strftime("%Y-%m-%d %H:%M:%S"),
                         peak, info["hr"], random.randint(50, 95), home_lat, home_lon))
        if condition == "recovering":  # the illness it is recovering from
            rows += [
                (device_id, (NOW - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"), "illness", "Fever", "Collar alert: temp 40.6°C, heart rate 92 bpm", ""),
                (device_id, (NOW - timedelta(days=10, hours=-5)).strftime("%Y-%m-%d %H:%M:%S"), "treatment", "Vet visit: fever", ILLNESSES["fever"]["treatment"], random.choice(VETS)),
            ]
        cur.executemany("INSERT INTO health_history (device_id, event_date, event_type, title, details, vet_name) VALUES (?,?,?,?,?,?)", rows)

        # Collar readings: hourly for the year, every 15 minutes for the last 30 days, ending now
        readings = []
        t = YEAR_AGO
        last_charge = YEAR_AGO
        while t <= NOW:
            step = timedelta(minutes=15) if t > NOW - timedelta(days=30) else timedelta(hours=1)
            sick = next((e for e in episodes if e["start"] <= t <= e["end"]), None)
            if sick:
                info = ILLNESSES[sick["kind"]]
                temp = random.gauss(info["temp"] or base_temp, 0.3)
                hr = int(random.gauss(info["hr"], 5))
                motion = random.gauss(info["motion"], 0.1)
            else:
                active = cur_start is not None and t >= cur_start and not (condition == "recovering" and t > NOW - timedelta(days=4))
                eff = "fever" if condition == "recovering" else condition
                temp, hr, motion, _h = gen._vitals_for(eff, base_temp, base_hr, active)
            # Summer days run warmer
            summer = t.month in (4, 5, 6)
            humidity = random.gauss(72 if summer else 60, 8)
            ambient = random.gauss(33 if summer else 27, 3) + (4 if 11 <= t.hour <= 15 else -2 if t.hour < 6 else 0)
            # Collar is recharged every 30 days; the low-battery collar was missed this month
            if (t - last_charge).days >= 30 and not (condition == "low_battery" and t > NOW - timedelta(days=40)):
                last_charge = t
            battery = max(8, 100 - (t - last_charge).days * (2.3 if condition == "low_battery" else 1.6))
            readings.append((device_id, int(t.timestamp()), round(max(37.0, min(42.0, temp)), 2), round(max(37.0, min(42.0, temp)), 2),
                             max(45, min(125, hr)), round(max(0.0, min(2.0, motion)), 3),
                             home_lat + random.uniform(-0.003, 0.003), home_lon + random.uniform(-0.003, 0.003),
                             int(battery), round(max(30, min(95, humidity)), 1), round(ambient, 1), t.strftime("%Y-%m-%d %H:%M:%S")))
            t += step
        cur.executemany("""INSERT INTO livestock_readings (device_id, timestamp, temperature, body_temperature, heart_rate,
                           motion_magnitude, latitude, longitude, battery, humidity, ambient_temperature, received_time)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", readings)
        total += len(readings)

    # Current alerts sit where the animals actually are now
    cur.execute("""UPDATE alerts SET latitude = (SELECT latitude FROM livestock_readings r WHERE r.device_id = alerts.device_id ORDER BY id DESC LIMIT 1),
                   longitude = (SELECT longitude FROM livestock_readings r WHERE r.device_id = alerts.device_id ORDER BY id DESC LIMIT 1)
                   WHERE resolved = 0""")
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM health_history")
    events = cur.fetchone()[0]
    conn.close()
    print(f"One year of history: {total} readings and {events} health records for {len(gen.device_ids)} animals")


if __name__ == "__main__":
    main()
