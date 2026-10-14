@echo off
title ExamShield - AI Monitoring Examination Backend
color 0B

echo ======================================================
echo           ExamShield - AI Examination System
echo ======================================================
echo.

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%backend"
set "PYTHONPATH=%PROJECT_ROOT%;%PROJECT_ROOT%backend;%PROJECT_ROOT%ai_monitoring_playground;%PROJECT_ROOT%ai_monitoring_playground\backend;%PYTHONPATH%"

:: Check for virtual environment in backend\venv
if exist "venv\Scripts\activate.bat" (
    echo [*] Activating Python virtual environment in backend\venv...
    call "venv\Scripts\activate.bat"
) else if exist "..\venv\Scripts\activate.bat" (
    echo [*] Activating root virtual environment in ..\venv...
    call "..\venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    echo [*] Activating Python virtual environment in .venv...
    call ".venv\Scripts\activate.bat"
) else (
    echo [!] Warning: No virtual environment found. Using system Python...
)

echo [*] Checking Python executable...
python --version
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ and add it to your PATH.
    pause
    exit /b 1
)

echo.
echo [*] Starting FastAPI Backend server on http://127.0.0.1:8000 ...
echo [*] API Documentation available at: http://127.0.0.1:8000/docs
echo [*] Press CTRL+C to stop the server.
echo.

python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

if errorlevel 1 (
    echo.
    echo [ERROR] Backend server stopped unexpectedly.
    pause
)
