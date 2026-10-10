"""
Notification Service for Smart Pastoralism
Send email and SMS alerts for critical events
"""
import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime
from app.config import settings


class NotificationService:
    """Handle email and SMS notifications"""
    
    def __init__(self):
        self.db_path = settings.LORA_DB_PATH
        self._init_notification_tables()
        
        # Email configuration
        self.smtp_server = getattr(settings, 'SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_username = getattr(settings, 'SMTP_USER', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.from_email = getattr(settings, 'SMTP_FROM_EMAIL', self.smtp_username)
        
        # SMS configuration (Twilio)
        self.sms_enabled = getattr(settings, 'SMS_ENABLED', False)
        self.twilio_account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        self.twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        self.twilio_from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '')
    
    def _init_notification_tables(self):
        """Create notification tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    email TEXT,
                    phone TEXT,
                    email_enabled INTEGER DEFAULT 1,
                    sms_enabled INTEGER DEFAULT 0,
                    critical_alerts INTEGER DEFAULT 1,
                    warning_alerts INTEGER DEFAULT 1,
                    geofence_alerts INTEGER DEFAULT 1,
                    battery_alerts INTEGER DEFAULT 1,
                    daily_summary INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notification_type TEXT,
                    recipient TEXT,
                    subject TEXT,
                    message TEXT,
                    status TEXT,
                    sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            print("✅ Notification tables initialized")
        except Exception as e:
            print(f"❌ Error initializing notification tables: {e}")
    
    def send_email(self, to_email: str, subject: str, body: str, html: bool = True) -> bool:
        """Send an email notification"""
        if not self.smtp_username or not self.smtp_password:
            print("⚠️  Email not configured. Set SMTP credentials in config.")
            self._log_notification('email', to_email, subject, body, 'not_configured')
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ Email sent to {to_email}")
            self._log_notification('email', to_email, subject, body, 'sent')
            return True
            
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            self._log_notification('email', to_email, subject, body, 'failed', str(e))
            return False
    
    def send_sms(self, to_phone: str, message: str) -> bool:
        """Send an SMS notification using Twilio"""
        if not self.sms_enabled:
            print("⚠️  SMS not enabled. Set SMS_ENABLED=True and configure Twilio credentials.")
            self._log_notification('sms', to_phone, 'SMS', message, 'not_enabled')
            return False
        
        try:
            from twilio.rest import Client
            
            client = Client(self.twilio_account_sid, self.twilio_auth_token)
            
            sms = client.messages.create(
                body=message,
                from_=self.twilio_from_number,
                to=to_phone
            )
            
            print(f"✅ SMS sent to {to_phone}")
            self._log_notification('sms', to_phone, 'SMS', message, 'sent')
            return True
            
        except ImportError:
            print("⚠️  Twilio not installed. Run: pip install twilio")
            self._log_notification('sms', to_phone, 'SMS', message, 'twilio_not_installed')
            return False
        except Exception as e:
            print(f"❌ Error sending SMS: {e}")
            self._log_notification('sms', to_phone, 'SMS', message, 'failed', str(e))
            return False
    
    def _log_notification(self, ntype: str, recipient: str, subject: str, 
                         message: str, status: str, error: str = None):
        """Log notification attempt"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO notification_log 
                (notification_type, recipient, subject, message, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ntype, recipient, subject, message, status, error))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Error logging notification: {e}")
    
    def send_alert_notification(self, alert_data: dict) -> dict:
        """Send notifications for an alert"""
        results = {'email': [], 'sms': []}
        
        # Get notification settings
        settings_list = self.get_notification_settings()
        
        for settings_row in settings_list:
            # Check if this type of alert should trigger notification
            should_notify = False
            
            if 'CRITICAL' in alert_data.get('alert_type', ''):
                should_notify = settings_row.get('critical_alerts', 0) == 1
            elif 'WARNING' in alert_data.get('alert_type', ''):
                should_notify = settings_row.get('warning_alerts', 0) == 1
            elif 'GEOFENCE' in alert_data.get('alert_type', ''):
                should_notify = settings_row.get('geofence_alerts', 0) == 1
            elif 'BATTERY' in alert_data.get('alert_type', ''):
                should_notify = settings_row.get('battery_alerts', 0) == 1
            
            if not should_notify:
                continue
            
            # Prepare message
            subject = f"🚨 {alert_data.get('alert_type', 'Alert')} - {alert_data.get('device_id', 'Unknown')}"
            
            body_plain = f"""
PawTrack Alert

Device: {alert_data.get('device_id', 'Unknown')}
Type: {alert_data.get('alert_type', 'Alert')}
Message: {alert_data.get('alert_message', 'No details')}
Time: {alert_data.get('alert_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}

Temperature: {alert_data.get('temperature', 'N/A')}°C
Heart Rate: {alert_data.get('heart_rate', 'N/A')} BPM
Battery: {alert_data.get('battery', 'N/A')}%

Check dashboard for more details.
            """
            
            body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; color: white;">
        <h1>🚨 PawTrack Alert</h1>
    </div>
    <div style="padding: 20px; background: #f8f9fa;">
        <h2 style="color: #dc3545;">{alert_data.get('alert_type', 'Alert')}</h2>
        <p><strong>Device:</strong> {alert_data.get('device_id', 'Unknown')}</p>
        <p><strong>Message:</strong> {alert_data.get('alert_message', 'No details')}</p>
        <p><strong>Time:</strong> {alert_data.get('alert_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</p>
        
        <table style="width: 100%; margin-top: 20px; border-collapse: collapse;">
            <tr style="background: #fff;">
                <td style="padding: 10px; border: 1px solid #dee2e6;"><strong>Temperature</strong></td>
                <td style="padding: 10px; border: 1px solid #dee2e6;">{alert_data.get('temperature', 'N/A')}°C</td>
            </tr>
            <tr style="background: #f8f9fa;">
                <td style="padding: 10px; border: 1px solid #dee2e6;"><strong>Heart Rate</strong></td>
                <td style="padding: 10px; border: 1px solid #dee2e6;">{alert_data.get('heart_rate', 'N/A')} BPM</td>
            </tr>
            <tr style="background: #fff;">
                <td style="padding: 10px; border: 1px solid #dee2e6;"><strong>Battery</strong></td>
                <td style="padding: 10px; border: 1px solid #dee2e6;">{alert_data.get('battery', 'N/A')}%</td>
            </tr>
        </table>
        
        <p style="margin-top: 20px; text-align: center;">
            <a href="http://localhost:8000/dashboard" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                View Dashboard
            </a>
        </p>
    </div>
</body>
</html>
            """
            
            # Send email
            if settings_row.get('email_enabled', 0) == 1 and settings_row.get('email'):
                success = self.send_email(settings_row['email'], subject, body_html, html=True)
                results['email'].append({'email': settings_row['email'], 'success': success})
            
            # Send SMS
            if settings_row.get('sms_enabled', 0) == 1 and settings_row.get('phone'):
                sms_message = f"ALERT: {alert_data.get('alert_type')} - {alert_data.get('device_id')}. {alert_data.get('alert_message', '')[:100]}"
                success = self.send_sms(settings_row['phone'], sms_message)
                results['sms'].append({'phone': settings_row['phone'], 'success': success})
        
        return results
    
    def get_notification_settings(self, user_id: Optional[int] = None) -> List[dict]:
        """Get notification settings"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute("SELECT * FROM notification_settings WHERE user_id = ?", (user_id,))
            else:
                cursor.execute("SELECT * FROM notification_settings")
            
            settings_list = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return settings_list
        except Exception as e:
            print(f"❌ Error getting notification settings: {e}")
            return []
    
    def update_notification_settings(self, user_id: int, **kwargs) -> bool:
        """Update notification settings"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if settings exist
            cursor.execute("SELECT id FROM notification_settings WHERE user_id = ?", (user_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                allowed_fields = ['email', 'phone', 'email_enabled', 'sms_enabled',
                                'critical_alerts', 'warning_alerts', 'geofence_alerts',
                                'battery_alerts', 'daily_summary']
                
                updates = []
                values = []
                
                for field, value in kwargs.items():
                    if field in allowed_fields:
                        updates.append(f"{field} = ?")
                        values.append(value)
                
                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    values.append(user_id)
                    
                    query = f"UPDATE notification_settings SET {', '.join(updates)} WHERE user_id = ?"
                    cursor.execute(query, values)
            else:
                # Insert new
                kwargs['user_id'] = user_id
                fields = list(kwargs.keys())
                placeholders = ','.join(['?'] * len(fields))
                
                query = f"INSERT INTO notification_settings ({','.join(fields)}) VALUES ({placeholders})"
                cursor.execute(query, list(kwargs.values()))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"❌ Error updating notification settings: {e}")
            return False


# Global instance
notification_service = NotificationService()
