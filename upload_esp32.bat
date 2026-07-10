@echo off
echo ========================================
echo  ESP32 Code Upload to COM3
echo ========================================
echo.

REM Set Arduino CLI path (adjust if needed)
set ARDUINO_CLI=arduino-cli

REM Check if arduino-cli is installed
where %ARDUINO_CLI% >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: arduino-cli not found!
    echo.
    echo Please install Arduino CLI:
    echo https://arduino.github.io/arduino-cli/latest/installation/
    echo.
    pause
    exit /b 1
)

echo Compiling ESP32 code...
echo.

REM Compile the sketch
%ARDUINO_CLI% compile --fqbn esp32:esp32:t-beam esp32code_sketch

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Compilation failed!
    pause
    exit /b 1
)

echo.
echo Compilation successful!
echo.
echo Uploading to COM3...
echo.

REM Upload to COM3
%ARDUINO_CLI% upload -p COM3 --fqbn esp32:esp32:t-beam esp32code_sketch

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Upload failed!
    echo Make sure:
    echo  - ESP32 is connected to COM3
    echo  - No other program is using COM3
    echo  - Correct board selected
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Upload Complete!
echo ========================================
echo.
echo Opening Serial Monitor on COM3...
echo.

REM Open serial monitor
%ARDUINO_CLI% monitor -p COM3 -c baudrate=115200

pause
