from fastapi import APIRouter, Request, Form, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import secrets
import hashlib
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Get database path from config
try:
    from app.config import settings
    DB_PATH = os.path.join(os.path.dirname(settings.LORA_DB_PATH), "sessions.db")
except:
    DB_PATH = "sessions.db"

def init_session_db():
    """Initialize the sessions database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        )
    ''')
    
    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create default admin user if not exists
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        password_hash = hash_password('admin123')
        cursor.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            ('admin', password_hash, 'admin')
        )
    
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """Hash a password with salt"""
    salt = "smart_pastoralism_salt_2024"
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash"""
    return hash_password(password) == password_hash

def create_session(user_id: int, username: str) -> str:
    """Create a new session and return session ID"""
    session_id = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(days=7)).isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clean up expired sessions
    cursor.execute('DELETE FROM sessions WHERE expires_at < ?', (datetime.now().isoformat(),))
    
    # Create new session
    cursor.execute(
        'INSERT INTO sessions (session_id, user_id, username, expires_at) VALUES (?, ?, ?, ?)',
        (session_id, user_id, username, expires_at)
    )
    
    # Update last login
    cursor.execute(
        'UPDATE users SET last_login = ? WHERE id = ?',
        (datetime.now().isoformat(), user_id)
    )
    
    conn.commit()
    conn.close()
    
    return session_id

def get_session(session_id: str) -> Optional[dict]:
    """Get session by ID if valid"""
    if not session_id:
        return None
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.*, u.role 
        FROM sessions s 
        JOIN users u ON s.user_id = u.id
        WHERE s.session_id = ? AND s.expires_at > ?
    ''', (session_id, datetime.now().isoformat()))
    
    result = cursor.fetchone()
    conn.close()
    
    return dict(result) if result else None

def delete_session(session_id: str):
    """Delete a session"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()

def is_authenticated(request: Request) -> bool:
    """Check if user is authenticated"""
    session_id = request.cookies.get("session_id")
    return get_session(session_id) is not None

def get_current_user(request: Request) -> Optional[dict]:
    """Get current authenticated user from session"""
    session_id = request.cookies.get("session_id")
    return get_session(session_id)

# Initialize database on import
init_session_db()

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    """Login page"""
    # If already logged in, redirect to dashboard
    if is_authenticated(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "error": error
    })

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...), 
    password: str = Form(...),
    remember: bool = Form(False)
):
    """Handle login"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and verify_password(password, user['password_hash']):
            # Create session
            session_id = create_session(user['id'], user['username'])
            
            response = RedirectResponse(url="/dashboard", status_code=302)
            
            # Set cookie (longer expiry if "remember me" is checked)
            max_age = 60 * 60 * 24 * 30 if remember else 60 * 60 * 24 * 7  # 30 or 7 days
            response.set_cookie(
                key="session_id", 
                value=session_id,
                max_age=max_age,
                httponly=True,
                samesite="lax"
            )
            return response
        else:
            return RedirectResponse(url="/auth/login?error=1", status_code=302)
            
    except Exception as e:
        print(f"Login error: {e}")
        return RedirectResponse(url="/auth/login?error=1", status_code=302)

@router.get("/logout")
async def logout(request: Request):
    """Handle logout"""
    session_id = request.cookies.get("session_id")
    if session_id:
        delete_session(session_id)
    
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session_id")
    return response

@router.get("/me")
async def current_user_info(request: Request):
    """Signed-in user's name and role, for the app shell"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"username": user["username"], "role": user.get("role")}

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """User profile page"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    return templates.TemplateResponse("auth/profile.html", {
        "request": request,
        "user": user
    })

@router.post("/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Handle password change"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    if new_password != confirm_password:
        return RedirectResponse(url="/auth/profile?error=passwords_dont_match", status_code=302)
    
    if len(new_password) < 6:
        return RedirectResponse(url="/auth/profile?error=password_too_short", status_code=302)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user['user_id'],))
        db_user = cursor.fetchone()
        
        if not db_user or not verify_password(current_password, db_user['password_hash']):
            conn.close()
            return RedirectResponse(url="/auth/profile?error=wrong_password", status_code=302)
        
        # Update password
        new_hash = hash_password(new_password)
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user['user_id']))
        conn.commit()
        conn.close()
        
        return RedirectResponse(url="/auth/profile?success=password_changed", status_code=302)
        
    except Exception as e:
        print(f"Password change error: {e}")
        return RedirectResponse(url="/auth/profile?error=1", status_code=302)

# Admin routes for user management
@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request):
    """Admin user management page"""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        return RedirectResponse(url="/auth/login", status_code=302)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, role, created_at, last_login FROM users ORDER BY id')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return templates.TemplateResponse("auth/admin_users.html", {
        "request": request,
        "user": user,
        "users": users
    })

@router.post("/admin/users/create")
async def admin_create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("user")
):
    """Create a new user (admin only)"""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        cursor.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            (username, password_hash, role)
        )
        conn.commit()
        conn.close()
        
        return RedirectResponse(url="/auth/admin/users?success=user_created", status_code=302)
    except sqlite3.IntegrityError:
        return RedirectResponse(url="/auth/admin/users?error=username_exists", status_code=302)
    except Exception as e:
        print(f"User creation error: {e}")
        return RedirectResponse(url="/auth/admin/users?error=1", status_code=302)

@router.post("/admin/users/{user_id}/delete")
async def admin_delete_user(request: Request, user_id: int):
    """Delete a user (admin only)"""
    user = get_current_user(request)
    if not user or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if user['user_id'] == user_id:
        return RedirectResponse(url="/auth/admin/users?error=cannot_delete_self", status_code=302)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Delete user sessions first
        cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        
        return RedirectResponse(url="/auth/admin/users?success=user_deleted", status_code=302)
    except Exception as e:
        print(f"User deletion error: {e}")
        return RedirectResponse(url="/auth/admin/users?error=1", status_code=302)
