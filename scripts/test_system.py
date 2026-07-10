#!/usr/bin/env python3
"""
Test script to verify the Smart Pastoralism system
"""
import sys
import os
import sqlite3
import subprocess
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

def check_python_version():
    """Check Python version"""
    print("[PYTHON] Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"   [OK] Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   [FAIL] Python {version.major}.{version.minor}.{version.micro} (need 3.9+)")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print("\n[PKG] Checking dependencies...")
    required = ['fastapi', 'uvicorn', 'jinja2', 'sqlite3']
    missing = []
    
    for package in required:
        try:
            if package == 'sqlite3':
                import sqlite3
            else:
                __import__(package)
            print(f"   [OK] {package}")
        except ImportError:
            print(f"   [FAIL] {package} not found")
            missing.append(package)
    
    if missing:
        print(f"\n   Install missing packages: pip install {' '.join(missing)}")
        return False
    return True

def check_project_structure():
    """Check if project structure is correct"""
    print("\n[DIR] Checking project structure...")
    required_paths = [
        'app',
        'app/routes',
        'app/services',
        'app/websocket',
        'app/templates',
        'app/static',
        'deployment',
        'scripts',
        'run.py',
        'requirements.txt',
        '.env'
    ]
    
    all_exist = True
    for path in required_paths:
        if os.path.exists(path):
            print(f"   [OK] {path}")
        else:
            print(f"   [FAIL] {path} missing")
            all_exist = False
    
    return all_exist

def check_database():
    """Check database"""
    print("\n[DB] Checking database...")
    db_path = 'livestock_data.db'
    
    if not os.path.exists(db_path):
        print(f"   [WARN]  Database not found: {db_path}")
        print("   Run: python scripts/init_db.py")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        if 'livestock_readings' in tables:
            print("   [OK] livestock_readings table exists")
            cursor.execute("SELECT COUNT(*) FROM livestock_readings")
            count = cursor.fetchone()[0]
            print(f"   [DATA] Records: {count}")
        else:
            print("   [FAIL] livestock_readings table missing")
            return False
        
        if 'alerts' in tables:
            print("   [OK] alerts table exists")
        else:
            print("   [WARN]  alerts table missing (will be created automatically)")
        
        conn.close()
        return True
    except Exception as e:
        print(f"   [FAIL] Database error: {e}")
        return False

def check_env_file():
    """Check .env configuration"""
    print("\n[CONF]  Checking configuration...")
    if not os.path.exists('.env'):
        print("   [WARN]  .env file not found")
        print("   Using default configuration")
        return True
    
    with open('.env', 'r') as f:
        content = f.read()
        if 'RPI_HOST' in content:
            print("   [OK] .env file configured")
        else:
            print("   [WARN]  .env file incomplete")
    return True

def test_import():
    """Test if main modules can be imported"""
    print("\n[SEARCH] Testing imports...")
    try:
        from app.config import settings
        print(f"   [OK] Configuration loaded")
        print(f"   [HOST] Host: {settings.HOST}:{settings.PORT}")
        
        from app.services.lora_service import LoRaMonitor
        print("   [OK] LoRa service imported")
        
        from app.routes import dashboard, api, auth
        print("   [OK] Routes imported")
        
        return True
    except Exception as e:
        print(f"   [FAIL] Import error: {e}")
        return False

def main():
    """Run all checks"""
    print("[SEARCH] Smart Pastoralism System - Pre-flight Check")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Project Structure", check_project_structure),
        ("Database", check_database),
        ("Configuration", check_env_file),
        ("Module Imports", test_import)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            results.append(check_func())
        except Exception as e:
            print(f"\n[FAIL] Error in {name}: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("[DATA] Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    for i, (name, _) in enumerate(checks):
        status = "[OK]" if results[i] else "[FAIL]"
        print(f"{status} {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if all(results):
        print("\n[OK] All checks passed! System ready to run.")
        print("\nStart the application:")
        print("  python run.py")
        print("\nOr deploy to Raspberry Pi:")
        print("  .\\deploy_to_rpi.ps1  (Windows)")
        print("  ./deploy_to_rpi.sh   (Linux/Mac)")
        return 0
    else:
        print("\n[WARN]  Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Initialize database: python scripts/init_db.py")
        print("  3. Create demo data: python scripts/create_demo_data.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())
