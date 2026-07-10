# 🚀 Advanced Features Guide

This guide covers the advanced features of Smart Pastoralism: **Geofencing** and **Email/SMS Notifications**.

---

## 📍 Geofencing System

### What is Geofencing?
Geofencing allows you to define virtual boundaries for your pasture. The system automatically detects when animals leave designated safe zones and triggers immediate alerts.

### How It Works
1. **Define Boundaries**: Create circular geofences by specifying:
   - Center coordinates (latitude/longitude)
   - Radius (in meters)
   - Name (e.g., "North Pasture", "Water Source Area")

2. **Automatic Monitoring**: The system checks each animal's GPS location against all active geofences every 2 seconds (configurable).

3. **Instant Alerts**: When an animal crosses a geofence:
   - Alert is logged in the database
   - WebSocket notification is sent (real-time dashboard update)
   - Email/SMS notification is sent (if configured)
   - Violation is recorded with distance outside fence

### Creating a Geofence

**Via Python API:**
```python
from app.services.geofence import geofence_service

# Create a circular geofence
fence_id = geofence_service.create_geofence(
    name="Main Pasture",
    center_lat=28.6139,  # Your pasture center
    center_lng=77.2090,
 radius_meters=500,   # 500 meter radius
    notification_enabled=True
)
```

**Via Database:**
```sql
INSERT INTO geofences (name, center_lat, center_lng, radius_meters, enabled, notification_enabled)
VALUES ('North Pasture', 28.6139, 77.2090, 500, 1, 1);
```

### Viewing Violations

**Get All Violations:**
```python
violations = geofence_service.get_violations(limit=100)
for v in violations:
    print(f"{v['device_id']} violated {v['geofence_name']} at {v['violated_at']}")
```

**Get Violations for Specific Animal:**
```python
violations = geofence_service.get_violations(device_id="COW-001")
```

### Managing Geofences

**List All Geofences:**
```python
fences = geofence_service.get_all_geofences()
```

**Update a Geofence:**
```python
geofence_service.update_geofence(
    geofence_id=1,
    radius_meters=1000,  # Expand to  1km
    enabled=True
)
```

**Delete a Geofence:**
```python
geofence_service.delete_geofence(geofence_id=1)
```

---

## 📧 Email & SMS Notifications

### What is it?
Automatically send email and SMS alerts when critical events occur:
- **Critical health alerts** (high temperature, high heart rate)
- **Battery warnings** (low/critical battery levels)
- **Geofence violations** (animal leaves safe zone)
- **Custom alerts** (configurable per user)

### Email Setup (Gmail Example)

1. **Enable 2-Step Verification** on your Google account:
   - Go to https://myaccount.google.com/security
   - Turn on 2-Step Verification

2. **Generate App Password**:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Name it "Smart Pastoralism"
   - Copy the 16-character password

3. **Configure .env file**:
```bash
SMTP_ENABLED=True
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop  # 16-char app password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=Smart Pastoralism Alerts
```

4. **Restart the application** for changes to take effect.

### SMS Setup (Twilio)

1. **Sign up for Twilio** (free trial available):
   - Go to https://www.twilio.com/try-twilio
   - Verify your phone number
   - Get $15.50 in free credit

2. **Get a Twilio Phone Number**:
   - Go to Console > Phone Numbers
   - Get a free number

3. **Copy Credentials**:
   - Go to Console > Settings > General
   - Copy Account SID and Auth Token

4. **Install Twilio SDK**:
```bash
pip install twilio
```

5. **Configure .env file**:
```bash
SMS_ENABLED=True
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+12025551234
```

### Managing Notification Settings

**Via Python API:**
```python
from app.services.notifications import notification_service

# Set up notifications for a user
notification_service.update_notification_settings(
    user_id=1,
    email="farmer@example.com",
    phone="+1234567890",
    email_enabled=True,
    sms_enabled=True,
    critical_alerts=True,    # Get critical alerts
    warning_alerts=False,    # Skip warnings
    geofence_alerts=True,    # Get geofence alerts
    battery_alerts=True      # Get battery alerts
)
```

**Via Database**:
```sql
INSERT INTO notification_settings (
    user_id, email, phone, 
    email_enabled, sms_enabled,
    critical_alerts, geofence_alerts
) VALUES (
    1, 'farmer@example.com', '+1234567890',
    1, 1,
    1, 1
);
```

### Sending Test Notifications

**Test Email:**
```python
from app.services.notifications import notification_service

notification_service.send_email(
    to_email="test@example.com",
    subject="Test Alert",
    body="<h1>This is a test alert</h1><p>System is working!</p>",
    html=True
)
```

**Test SMS:**
```python
notification_service.send_sms(
    to_phone="+1234567890",
    message="Test SMS from Smart Pastoralism system"
)
```

### Notification Flow

```
1. Sensor Reading Received
   ↓
2. Anomaly Detection (temp/hr/battery/geofence)
   ↓
3. Alert Created in Database
   ↓
4. Check Notification Settings
   ↓
5. Send Email (if enabled)
   ↓
6. Send SMS (if enabled)
   ↓
7. Log Notification Attempt
```

### Email Template
The system sends beautiful HTML emails with:
- Gradient header with your app branding
- Alert type and severity
- Device ID and timestamp
- Sensor values in a table format
- "View Dashboard" button
- Responsive design (mobile-friendly)

### Viewing Notification Logs

**Via Database:**
```sql
SELECT * FROM notification_log
ORDER BY sent_at DESC
LIMIT 100;
```

**Via Python:**
```python
import sqlite3
conn = sqlite3.connect('livestock_data.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT notification_type, recipient, status, sent_at
    FROM notification_log
    WHERE status = 'sent'
    ORDER BY sent_at DESC
    LIMIT 10
""")

for row in cursor.fetchall():
    print(f"{row[0]} to {row[1]}: {row[2]} at {row[3]}")
```

---

## 🔧 Troubleshooting

### Email Not Sending

**Problem**: "SMTP not configured" error
**Solution**: 
- Verify SMTP_ENABLED=True in .env
- Check SMTP_USER and SMTP_PASSWORD are set
- For Gmail, use App Password, not regular password

**Problem**: "Authentication failed"
**Solution**:
- Enable "Less secure app access" or use App Password
- Check username/password are correct
- Verify SMTP_HOST and SMTP_PORT match your provider

### SMS Not Sending

**Problem**: "Twilio not installed"
**Solution**:
```bash
pip install twilio
```

**Problem**: "SMS not enabled"
**Solution**:
- Set SMS_ENABLED=True in .env
- Restart application

**Problem**: "Authentication Error"
**Solution**:
- Verify Account SID and Auth Token from Twilio Console
- Check phone number format: +[country][number]

### Geofencing Not Working

**Problem**: No violations detected
**Solution**:
- Verify geofences are created and enabled=1
- Check animal GPS coordinates are not (0, 0)
- Ensure GEOFENCE_ALERT_ENABLED=True in .env

**Problem**: Too many false alerts
**Solution**:
- Increase geofence radius
- Check GPS accuracy of device
- Adjust GEOFENCE_CHECK_INTERVAL (increase for less frequent checks)

---

## 📊 Database Schema

### Geofences Table
```sql
CREATE TABLE geofences (
    id INTEGER PRIMARY KEY,
    name TEXT,
    center_lat REAL,
    center_lng REAL,
    radius_meters REAL,
    shape TEXT DEFAULT 'circle',
    enabled INTEGER DEFAULT 1,
    notification_enabled INTEGER DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);
```

### Geofence Violations Table
```sql
CREATE TABLE geofence_violations (
    id INTEGER PRIMARY KEY,
    geofence_id INTEGER,
    device_id TEXT,
    latitude REAL,
    longitude REAL,
    distance_from_fence REAL,
    violated_at TEXT,
    alert_sent INTEGER DEFAULT 0
);
```

### Notification Settings Table
```sql
CREATE TABLE notification_settings (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    email TEXT,
    phone TEXT,
    email_enabled INTEGER DEFAULT 1,
    sms_enabled INTEGER DEFAULT 0,
    critical_alerts INTEGER DEFAULT 1,
    warning_alerts INTEGER DEFAULT 1,
    geofence_alerts INTEGER DEFAULT 1,
    battery_alerts INTEGER DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);
```

### Notification Log Table
```sql
CREATE TABLE notification_log (
    id INTEGER PRIMARY KEY,
    notification_type TEXT,  -- 'email' or 'sms'
    recipient TEXT,
    subject TEXT,
    message TEXT,
    status TEXT,  -- 'sent', 'failed', 'not_configured'
    sent_at TEXT,
    error_message TEXT
);
```

---

## 🎯 Best Practices

1. **Test Before Production**:
   - Send test emails/SMS to verify configuration
   - Create small geofences and test with one device first

2. **Monitor Notification Costs**:
   - SMS notifications cost money (Twilio charges per message)
   - Consider email-only for non-critical alerts
   - Use notification preferences to avoid spam

3. **Geofence Design**:
   - Make geofences slightly larger than actual pasture boundaries
   - Account for GPS accuracy (±5-10 meters)
   - Use descriptive names ("North Pasture" not "Fence1")

4. **Security**:
   - Never commit .env file to version control
   - Use App Passwords, not main account passwords
   - Rotate credentials periodically

5. **Performance**:
   - Don't set LORA_CHECK_INTERVAL too low (< 1 second)
   - Limit notification recipients to essential personnel
   - Archive old notification logs monthly

---

## 📱 API Endpoints (Future Web UI)

These features will be accessible via web UI in future updates:

- `/settings/geofences` - Manage geofences
- `/settings/notifications` - Configure email/SMS preferences
- `/api/geofences` - CRUD operations for geofences
- `/api/notifications/test` - Send test notifications

---

## 💡 Pro Tips

1. **Multi-Zone Setup**: Create overlapping geofences for "warning" and "critical" zones
2. **Time-Based Alerts**: Modify notification settings based on time of day
3. **Integration**: Use webhooks to integrate with other farm management systems
4. **Analytics**: Query geofence_violations table for movement pattern analysis
5. **Escalation**: Set up multiple recipients with different alert thresholds

---

**Need Help?** Check the main README.md or contact support.
