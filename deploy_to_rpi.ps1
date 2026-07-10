# Smart Pastoralism - Deploy to Raspberry Pi 5
# PowerShell script to deploy from Windows to RPi5

$RPI_HOST = "192.168.1.12"
$RPI_USER = "admin"
$PROJECT_DIR = "smart_pastoralism"
$LOCAL_PATH = "."

Write-Host "Smart Pastoralism - Deploy to Raspberry Pi 5" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if scp is available
if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] scp command not found" -ForegroundColor Red
    Write-Host "Please install OpenSSH Client from Windows Features" -ForegroundColor Yellow
    Write-Host "Or use WSL/Git Bash" -ForegroundColor Yellow
    exit 1
}

Write-Host "[INFO] Preparing files for deployment..." -ForegroundColor Green

Write-Host "[INFO] Connecting to Raspberry Pi at $RPI_HOST..." -ForegroundColor Green

# Test connection
Write-Host "Pinging $RPI_HOST..."
$pingResult = Test-Connection -ComputerName $RPI_HOST -Count 4 -Quiet
if (-not $pingResult) {
    Write-Host "[ERROR] Cannot reach $RPI_HOST" -ForegroundColor Red
    Write-Host "Please check:" -ForegroundColor Yellow
    Write-Host "  1. Raspberry Pi is powered on" -ForegroundColor Yellow
    Write-Host "  2. IP address is correct" -ForegroundColor Yellow
    Write-Host "  3. Network connection is working" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Connection successful!" -ForegroundColor Green

# Clean remote directory for fresh install
Write-Host "[INFO] Cleaning remote directory (removing old data)..." -ForegroundColor Yellow
$remote_cmd_rm = "rm -rf ~/" + $PROJECT_DIR
$remote_cmd_mkdir = "mkdir -p ~/" + $PROJECT_DIR

ssh $RPI_USER@$RPI_HOST $remote_cmd_rm
ssh $RPI_USER@$RPI_HOST $remote_cmd_mkdir

# Deploy files
Write-Host "[INFO] Transferring files to Raspberry Pi..." -ForegroundColor Green
Write-Host "This may take a few minutes..." -ForegroundColor Yellow

# Use scp to transfer files
$target = $RPI_USER + "@" + $RPI_HOST + ":~/" + $PROJECT_DIR
scp -r $LOCAL_PATH $target

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Files transferred successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. SSH to Raspberry Pi: ssh $RPI_USER@$RPI_HOST" -ForegroundColor White
    Write-Host "  2. Navigate to project: cd $PROJECT_DIR" -ForegroundColor White
    Write-Host "  3. Run setup: ./scripts/setup_rpi5.sh" -ForegroundColor White
    Write-Host ""
    Write-Host "Or run automatically:" -ForegroundColor Cyan
    Write-Host "  ssh $RPI_USER@$RPI_HOST 'cd $PROJECT_DIR && chmod +x scripts/setup_rpi5.sh && ./scripts/setup_rpi5.sh'" -ForegroundColor White
    Write-Host ""
}
else {
    Write-Host "[ERROR] Transfer failed!" -ForegroundColor Red
    Write-Host "Please check your credentials and try again" -ForegroundColor Yellow
}

Write-Host "After setup, access dashboard at: http://$RPI_HOST" -ForegroundColor Cyan
Write-Host ""
