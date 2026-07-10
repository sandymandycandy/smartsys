#!/bin/bash
# Deploy from Linux/Mac to Raspberry Pi 5

RPI_HOST="192.168.1.12"
RPI_USER="pi"
PROJECT_DIR="smart_pastoralism"

echo "🚀 Smart Pastoralism - Deploy to Raspberry Pi 5"
echo "================================================"
echo ""

# Check if scp is available
if ! command -v scp &> /dev/null; then
    echo "❌ Error: scp command not found"
    echo "Please install OpenSSH"
    exit 1
fi

echo "📦 Preparing files for deployment..."

# Test connection
echo "📡 Testing connection to $RPI_HOST..."
if ! ping -c 1 $RPI_HOST &> /dev/null; then
    echo "❌ Error: Cannot reach $RPI_HOST"
    echo "Please check:"
    echo "  1. Raspberry Pi is powered on"
    echo "  2. IP address is correct"
    echo "  3. Network connection is working"
    exit 1
fi

echo "✅ Connection successful!"

# Deploy files
echo "📤 Transferring files to Raspberry Pi..."
echo "This may take a few minutes..."

# Use rsync if available, otherwise scp
if command -v rsync &> /dev/null; then
    rsync -avz --exclude '*.pyc' --exclude '__pycache__' --exclude '*.db' --exclude 'venv' --exclude '.git' \
        . ${RPI_USER}@${RPI_HOST}:~/${PROJECT_DIR}
else
    scp -r . ${RPI_USER}@${RPI_HOST}:~/${PROJECT_DIR}
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Files transferred successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. SSH to Raspberry Pi: ssh $RPI_USER@$RPI_HOST"
    echo "  2. Navigate to project: cd $PROJECT_DIR"
    echo "  3. Run setup: ./scripts/setup_rpi5.sh"
    echo ""
    
    read -p "Do you want to run setup automatically? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚀 Running setup on Raspberry Pi..."
        ssh ${RPI_USER}@${RPI_HOST} "cd ${PROJECT_DIR} && chmod +x scripts/setup_rpi5.sh && ./scripts/setup_rpi5.sh"
    fi
else
    echo "❌ Transfer failed!"
    echo "Please check your credentials and try again"
    exit 1
fi

echo ""
echo "🌐 After setup, access dashboard at: http://$RPI_HOST"
echo ""
