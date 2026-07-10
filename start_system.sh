#!/bin/bash
# Smart Pastoralism - Robust One-Click Startup Script
# Starts dashboard first, then LoRa receiver with automatic recovery

set -e  # Exit on error

PROJECT_DIR=~/smart_pastoralism
LOG_DIR=$PROJECT_DIR/logs
DASHBOARD_PID_FILE=$LOG_DIR/dashboard.pid
RECEIVER_PID_FILE=$LOG_DIR/receiver.pid

# Create logs directory if it doesn't exist
mkdir -p $LOG_DIR

# Function to cleanup all processes
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    
    # Kill dashboard
    if [ -f "$DASHBOARD_PID_FILE" ]; then
        DASH_PID=$(cat $DASHBOARD_PID_FILE)
        kill $DASH_PID 2>/dev/null && echo "   ✅ Dashboard stopped (PID: $DASH_PID)"
        rm -f $DASHBOARD_PID_FILE
    fi
    
    # Kill receiver
    if [ -f "$RECEIVER_PID_FILE" ]; then
        REC_PID=$(cat $RECEIVER_PID_FILE)
        kill $REC_PID 2>/dev/null && echo "   ✅ LoRa receiver stopped (PID: $REC_PID)"
        rm -f $RECEIVER_PID_FILE
    fi
    
    # Kill anything on port 8000
    sudo lsof -ti:8000 | xargs sudo kill -9 2>/dev/null
    
    echo "✅ All services stopped cleanly"
    exit 0
}

# Trap Ctrl+C and errors
trap cleanup SIGINT SIGTERM ERR

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  🐄 Smart Pastoralism - Robust Startup System            ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Navigate to project directory
cd $PROJECT_DIR || exit 1

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate || {
    echo "❌ Failed to activate virtual environment"
    exit 1
}

# Clean up any existing processes
echo "🧹 Cleaning up old processes..."
sudo lsof -ti:8000 | xargs sudo kill -9 2>/dev/null
rm -f $DASHBOARD_PID_FILE $RECEIVER_PID_FILE
sleep 2

# Step 1: Start Web Dashboard FIRST
echo "🌐 Starting web dashboard..."
nohup python3 run.py > $LOG_DIR/dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo $DASHBOARD_PID > $DASHBOARD_PID_FILE
echo "   ✅ Dashboard started (PID: $DASHBOARD_PID)"

# Wait for dashboard to be ready
echo "   ⏳ Waiting for dashboard to initialize..."
sleep 5

# Check if dashboard is running
if ! kill -0 $DASHBOARD_PID 2>/dev/null; then
    echo "   ❌ Dashboard failed to start! Check logs/dashboard.log"
    cleanup
fi

# Verify port 8000 is listening
if ! lsof -ti:8000 > /dev/null 2>&1; then
    echo "   ❌ Dashboard not listening on port 8000!"
    cleanup
fi

echo "   ✅ Dashboard is ready at http://192.168.1.12:8000/dashboard"

# Step 2: Start LoRa Receiver
echo "📡 Starting LoRa receiver..."
nohup python3 reciver_rpi5.py > $LOG_DIR/receiver.log 2>&1 &
RECEIVER_PID=$!
echo $RECEIVER_PID > $RECEIVER_PID_FILE
echo "   ✅ LoRa receiver started (PID: $RECEIVER_PID)"

# Monitor both processes
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ All services running successfully!"
echo ""
echo "📊 Dashboard:     http://192.168.1.12:8000/dashboard"
echo "📡 LoRa Receiver: Active (PID: $RECEIVER_PID)"
echo "📝 Logs:          $LOG_DIR/"
echo ""
echo "Press Ctrl+C to stop all services"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Monitor loop - restart services if they crash
while true; do
    sleep 10
    
    # Check dashboard
    if ! kill -0 $DASHBOARD_PID 2>/dev/null; then
        echo "⚠️  Dashboard crashed! Restarting..."
        cleanup
        exec $0  # Restart this script
    fi
    
    # Check receiver
    if ! kill -0 $RECEIVER_PID 2>/dev/null; then
        echo "⚠️  LoRa receiver crashed! Restarting..."
        nohup python3 reciver_rpi5.py > $LOG_DIR/receiver.log 2>&1 &
        RECEIVER_PID=$!
        echo $RECEIVER_PID > $RECEIVER_PID_FILE
        echo "   ✅ LoRa receiver restarted (PID: $RECEIVER_PID)"
    fi
done
