# Quick Start Guide

## For Raspberry Pi 5 Deployment

### 1. Transfer Files
```bash
# From your Windows machine
scp -r smart_pastoralism pi@192.168.1.12:~/
```

### 2. SSH to Raspberry Pi
```bash
ssh pi@192.168.1.12
```

### 3. Run Setup
```bash
cd ~/smart_pastoralism
chmod +x scripts/setup_rpi5.sh
./scripts/setup_rpi5.sh
```

### 4. Access Dashboard
Open browser: `http://192.168.1.12`

Login:
- Username: `admin`
- Password: `admin123`

---

## For Local Development/Testing

### 1. Install Dependencies
```bash
cd smart_pastoralism
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python scripts/init_db.py
```

### 3. (Optional) Generate Demo Data
```bash
python scripts/create_demo_data.py
```

### 4. Run Application
```bash
python run.py
```

### 5. Access Dashboard
Open browser: `http://localhost:8000`

---

## Testing the Dashboard

1. **Dashboard Home** - View overview stats
2. **Live Map** - See animal locations (if GPS data available)
3. **Animals List** - Browse all animals
4. **Alerts** - Check active alerts
5. **Analytics** - View trends

---

## Connecting Your LoRa Receiver

Make sure your LoRa receiver Python script saves data to:
```
/home/pi/smart_pastoralism/livestock_data.db
```

Or update the path in `.env`:
```bash
LORA_DB_PATH="/path/to/your/livestock_data.db"
```

---

## Troubleshooting

### No data showing?
```bash
# Check if database has data
sqlite3 livestock_data.db "SELECT COUNT(*) FROM livestock_readings;"

# Generate demo data for testing
python scripts/create_demo_data.py
```

### Service not starting?
```bash
# Check logs
sudo journalctl -u smartpastoral -xe

# Check if port 8000 is in use
sudo lsof -i :8000
```

### WebSocket not connecting?
```bash
# Restart services
sudo systemctl restart smartpastoral
sudo systemctl restart nginx
```

---

## Next Steps

1. Change default password in authentication
2. Configure alert thresholds in `.env`
3. Set up SSL/HTTPS for production
4. Configure your LoRa receiver path
5. Customize dashboard as needed

---

## Support

Check `README.md` for full documentation.
