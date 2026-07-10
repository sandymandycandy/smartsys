import sqlite3

conn = sqlite3.connect('livestock_data.db')
cursor = conn.cursor()

# Check total readings
cursor.execute("SELECT COUNT(*) FROM livestock_readings")
total = cursor.fetchone()[0]
print(f"Total readings in database: {total}")

# Check recent readings
cursor.execute("SELECT device_id, temperature, heart_rate, received_time FROM livestock_readings ORDER BY id DESC LIMIT 5")
recent = cursor.fetchall()

print("\nRecent 5 readings:")
for r in recent:
    print(f"  Device: {r[0]}, Temp: {r[1]}°C, HR: {r[2]} BPM, Time: {r[3]}")

conn.close()
