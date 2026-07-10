#!/bin/bash
# Smart Pastoralism System - Raspberry Pi 5 Setup Script
# Run this script on your Raspberry Pi 5

set -e

echo "🚀 Smart Pastoralism System - RPi5 Setup"
echo "=========================================="
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo "⚠️  Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "📦 Installing system dependencies..."
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-gpiozero \
    nginx \
    redis-server \
    build-essential \
    build-essential \
    git

# Enable SPI Interface
echo "⚙️  Enabling SPI interface..."
sudo raspi-config nonint do_spi 0

# Create project directory
CURRENT_USER=$(whoami)
PROJECT_DIR="/home/$CURRENT_USER/smart_pastoralism"
echo "📁 Setting up project directory: $PROJECT_DIR"

# If running from current directory, copy files
if [ -f "run.py" ]; then
    echo "Copying files to $PROJECT_DIR..."
    # Only copy if we are not already in the target directory
    if [ "$(pwd)" != "$PROJECT_DIR" ]; then
        sudo mkdir -p $PROJECT_DIR
        sudo cp -r . $PROJECT_DIR/
        sudo chown -R $CURRENT_USER:$CURRENT_USER $PROJECT_DIR
    else
        echo "Already in project directory, skipping copy."
    fi
else
    echo "⚠️  Please run this script from the smart_pastoralism directory"
    exit 1
fi

cd $PROJECT_DIR

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Configure Nginx
echo "⚙️  Configuring Nginx..."
sudo cp deployment/nginx.conf /etc/nginx/sites-available/smartpastoral
sudo ln -sf /etc/nginx/sites-available/smartpastoral /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Setup systemd service
echo "⚙️  Setting up systemd service..."
sudo cp deployment/systemd/smartpastoral.service /etc/systemd/system/
sudo cp deployment/systemd/smartpastoral-receiver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable smartpastoral
sudo systemctl enable smartpastoral-receiver
sudo systemctl start smartpastoral
sudo systemctl start smartpastoral-receiver

# Enable Redis
echo "⚙️  Enabling Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Get IP address
IP_ADDR=$(hostname -I | awk '{print $1}')

echo ""
echo "✅ Setup complete!"
echo ""
echo "========================================"
echo "🌐 Web interface: http://$IP_ADDR"
echo "📊 API Docs: http://$IP_ADDR/docs"
echo "========================================"
echo ""
echo "Default login:"
echo "  Username: admin"
echo "  Password: admin123"
echo "  ⚠️  CHANGE THIS IMMEDIATELY IN PRODUCTION!"
echo ""
echo "Useful commands:"
echo "  Check status: sudo systemctl status smartpastoral"
echo "  View logs: sudo journalctl -u smartpastoral -f"
echo "  Restart: sudo systemctl restart smartpastoral"
echo "  Stop: sudo systemctl stop smartpastoral"
echo ""
echo "📝 Make sure your LoRa receiver is saving to: $PROJECT_DIR/livestock_data.db"
echo ""
