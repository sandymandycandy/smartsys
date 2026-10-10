"""
Notification Service for Email and SMS alerts
"""
import smtplib
import sqlite3
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional, Dict
import threading

try:
    from app.config import settings
except:
    from config import settings

# Get database path
DB_PATH = os.path.join(os.path.dirname(settings.LORA_DB_PATH), "notifications.db")

def init_notification_db():
    """Initialize the notifications database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Notification settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Notification log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_type TEXT NOT NULL,
            recipient TEXT NOT NULL,
            subject TEXT,
            message TEXT,
            alert_id INTEGER,
            status TEXT DEFAULT 'pending',
            sent_at TEXT,
            error_message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Email recipients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_recipients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            notify_critical BOOLEAN DEFAULT 1,
            notify_warning BOOLEAN DEFAULT 1,
            notify_geofence BOOLEAN DEFAULT 1,
            active BOOLEAN DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Phone recipients table (for SMS)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phone_recipients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            name TEXT,
            notify_critical BOOLEAN DEFAULT 1,
            notify_warning BOOLEAN DEFAULT 0,
            notify_geofence BOOLEAN DEFAULT 1,
            active BOOLEAN DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on import
init_notification_db()


class EmailNotificationService:
    """Service for sending email notifications"""
    
    def __init__(self):
        self.enabled = settings.SMTP_ENABLED
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME
    
    def send_email(self, to_email: str, subject: str, html_body: str, text_body: str = None) -> bool:
        """Send an email notification"""
        if not self.enabled:
            print(f"📧 Email disabled. Would send to {to_email}: {subject}")
            self._log_notification('email', to_email, subject, text_body or html_body, 'disabled')
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add plain text and HTML versions
            if text_body:
                msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Connect and send
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
            
            self._log_notification('email', to_email, subject, text_body or html_body, 'sent')
            print(f"✅ Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            self._log_notification('email', to_email, subject, text_body or html_body, 'failed', error_msg)
            print(f"❌ Email failed to {to_email}: {error_msg}")
            return False
    
    def _log_notification(self, ntype: str, recipient: str, subject: str, message: str, 
                          status: str, error: str = None, alert_id: int = None):
        """Log notification to database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notification_log 
                (notification_type, recipient, subject, message, alert_id, status, sent_at, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ntype, recipient, subject, message[:500] if message else None, 
                  alert_id, status, datetime.now().isoformat() if status == 'sent' else None, error))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging notification: {e}")

    def send_alert_notification(self, alert: Dict):
        """Send alert notification to all active email recipients"""
        recipients = self.get_active_recipients(alert.get('alert_type', ''))
        
        for recipient in recipients:
            subject = f"🚨 {alert.get('alert_type', 'Alert')}: {alert.get('device_id', 'Unknown')}"
            
            html_body = self._create_alert_email_html(alert)
            text_body = self._create_alert_email_text(alert)
            
            # Send in background thread
            thread = threading.Thread(
                target=self.send_email,
                args=(recipient['email'], subject, html_body, text_body)
            )
            thread.start()
    
    def get_active_recipients(self, alert_type: str = '') -> List[Dict]:
        """Get active email recipients based on alert type"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM email_recipients WHERE active = 1'
            
            if 'CRITICAL' in alert_type.upper():
                query += ' AND notify_critical = 1'
            elif 'WARNING' in alert_type.upper():
                query += ' AND notify_warning = 1'
            elif 'GEOFENCE' in alert_type.upper():
                query += ' AND notify_geofence = 1'
            
            cursor.execute(query)
            recipients = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return recipients
        except Exception as e:
            print(f"Error getting recipients: {e}")
            return []
    
    def _create_alert_email_html(self, alert: Dict) -> str:
        """Create HTML email body for alert"""
        alert_type = alert.get('alert_type', 'Alert')
        device_id = alert.get('device_id', 'Unknown')
        message = alert.get('alert_message', 'No details available')
        timestamp = alert.get('alert_time', datetime.now().isoformat())
        
        color = '#EF4444' if 'CRITICAL' in alert_type else '#F59E0B' if 'WARNING' in alert_type else '#3B82F6'
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f3f4f6; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: {color}; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; }}
                .alert-box {{ background: #f9fafb; border-left: 4px solid {color}; padding: 15px; margin: 20px 0; border-radius: 4px; }}
                .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .stat {{ text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #1f2937; }}
                .stat-label {{ font-size: 12px; color: #6b7280; }}
                .footer {{ background: #f3f4f6; padding: 15px; text-align: center; font-size: 12px; color: #6b7280; }}
                .btn {{ display: inline-block; background: {color}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 {alert_type}</h1>
                </div>
                <div class="content">
                    <h2>Device: {device_id}</h2>
                    <div class="alert-box">
                        <p><strong>Alert Message:</strong></p>
                        <p>{message}</p>
                    </div>
                    <div class="stats">
                        <div class="stat">
                            <div class="stat-value">{alert.get('temperature', 'N/A')}°C</div>
                            <div class="stat-label">Temperature</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">{alert.get('heart_rate', 'N/A')}</div>
                            <div class="stat-label">Heart Rate</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">{alert.get('battery', 'N/A')}%</div>
                            <div class="stat-label">Battery</div>
                        </div>
                    </div>
                    <p><strong>Time:</strong> {timestamp}</p>
                    <center>
                        <a href="http://{settings.RPI_HOST}:{settings.PORT}/dashboard/animals/{device_id}" class="btn">
                            View Animal Details
                        </a>
                    </center>
                </div>
                <div class="footer">
                    <p>PawTrack Monitoring System</p>
                    <p>This is an automated alert. Do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        '''
    
    def _create_alert_email_text(self, alert: Dict) -> str:
        """Create plain text email body for alert"""
        return f'''
        PAWTRACK ALERT
        =======================
        
        Alert Type: {alert.get('alert_type', 'Alert')}
        Device: {alert.get('device_id', 'Unknown')}
        
        Message: {alert.get('alert_message', 'No details available')}
        
        Readings:
        - Temperature: {alert.get('temperature', 'N/A')}°C
        - Heart Rate: {alert.get('heart_rate', 'N/A')} BPM
        - Battery: {alert.get('battery', 'N/A')}%
        
        Time: {alert.get('alert_time', 'N/A')}
        
        View details: http://{settings.RPI_HOST}:{settings.PORT}/dashboard/animals/{alert.get('device_id', '')}
        
        --
        PawTrack Monitoring System
        '''


class SMSNotificationService:
    """Service for sending SMS notifications via Twilio"""
    
    def __init__(self):
        self.enabled = settings.SMS_ENABLED
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_phone = settings.TWILIO_PHONE_NUMBER
        self.client = None
        
        if self.enabled and self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
            except ImportError:
                print("⚠️ Twilio library not installed. SMS notifications disabled.")
                self.enabled = False
            except Exception as e:
                print(f"⚠️ Twilio initialization failed: {e}")
                self.enabled = False
    
    def send_sms(self, to_phone: str, message: str) -> bool:
        """Send an SMS notification"""
        if not self.enabled or not self.client:
            print(f"📱 SMS disabled. Would send to {to_phone}: {message[:50]}...")
            self._log_notification(to_phone, message, 'disabled')
            return False
        
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_phone,
                to=to_phone
            )
            self._log_notification(to_phone, message, 'sent')
            print(f"✅ SMS sent to {to_phone}")
            return True
        except Exception as e:
            error_msg = str(e)
            self._log_notification(to_phone, message, 'failed', error_msg)
            print(f"❌ SMS failed to {to_phone}: {error_msg}")
            return False
    
    def _log_notification(self, recipient: str, message: str, status: str, error: str = None):
        """Log SMS notification to database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notification_log 
                (notification_type, recipient, message, status, sent_at, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('sms', recipient, message[:500], status, 
                  datetime.now().isoformat() if status == 'sent' else None, error))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging SMS: {e}")
    
    def send_alert_notification(self, alert: Dict):
        """Send SMS alert to all active phone recipients"""
        recipients = self.get_active_recipients(alert.get('alert_type', ''))
        
        message = f"🚨 {alert.get('alert_type', 'Alert')}\n"
        message += f"Device: {alert.get('device_id', 'Unknown')}\n"
        message += f"Temp: {alert.get('temperature', 'N/A')}°C | HR: {alert.get('heart_rate', 'N/A')} BPM\n"
        message += f"Message: {alert.get('alert_message', '')[:100]}"
        
        for recipient in recipients:
            thread = threading.Thread(
                target=self.send_sms,
                args=(recipient['phone'], message)
            )
            thread.start()
    
    def get_active_recipients(self, alert_type: str = '') -> List[Dict]:
        """Get active phone recipients based on alert type"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM phone_recipients WHERE active = 1'
            
            if 'CRITICAL' in alert_type.upper():
                query += ' AND notify_critical = 1'
            elif 'WARNING' in alert_type.upper():
                query += ' AND notify_warning = 1'
            elif 'GEOFENCE' in alert_type.upper():
                query += ' AND notify_geofence = 1'
            
            cursor.execute(query)
            recipients = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return recipients
        except Exception as e:
            print(f"Error getting phone recipients: {e}")
            return []


# Global instances
email_service = EmailNotificationService()
sms_service = SMSNotificationService()


def send_alert_notifications(alert: Dict):
    """Send notifications for an alert via all enabled channels"""
    email_service.send_alert_notification(alert)
    sms_service.send_alert_notification(alert)


# Helper functions for managing recipients
def add_email_recipient(email: str, name: str = None, notify_critical: bool = True,
                        notify_warning: bool = True, notify_geofence: bool = True) -> bool:
    """Add an email recipient"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO email_recipients 
            (email, name, notify_critical, notify_warning, notify_geofence, active)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (email, name, notify_critical, notify_warning, notify_geofence))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding email recipient: {e}")
        return False


def add_phone_recipient(phone: str, name: str = None, notify_critical: bool = True,
                        notify_warning: bool = False, notify_geofence: bool = True) -> bool:
    """Add a phone recipient"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO phone_recipients 
            (phone, name, notify_critical, notify_warning, notify_geofence, active)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (phone, name, notify_critical, notify_warning, notify_geofence))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding phone recipient: {e}")
        return False


def get_all_email_recipients() -> List[Dict]:
    """Get all email recipients"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM email_recipients ORDER BY id')
        recipients = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return recipients
    except Exception as e:
        print(f"Error getting email recipients: {e}")
        return []


def get_all_phone_recipients() -> List[Dict]:
    """Get all phone recipients"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM phone_recipients ORDER BY id')
        recipients = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return recipients
    except Exception as e:
        print(f"Error getting phone recipients: {e}")
        return []


def get_notification_log(limit: int = 50) -> List[Dict]:
    """Get recent notification log"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM notification_log 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return logs
    except Exception as e:
        print(f"Error getting notification log: {e}")
        return []
