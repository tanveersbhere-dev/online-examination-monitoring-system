@echo off
title ExamShield - Full Stack Launcher
color 0E

echo ======================================================
echo           ExamShield - Project Launcher
echo ======================================================
echo.
echo Launching Backend and Frontend in separate windows...
echo.

:: Launch Backend
start "ExamShield Backend" "%~dp0start_backend.bat"

:: Small delay to let backend start initializing
timeout /t 3 /nobreak >nul

:: Launch Frontend
start "ExamShield Frontend" "%~dp0start_frontend.bat"

echo.
echo ======================================================
echo [OK] Both servers are starting up!
echo - Frontend: http://localhost:5173
echo - Backend API: http://127.0.0.1:8000
echo - Swagger Docs: http://127.0.0.1:8000/docs
echo ======================================================
echo You can close this launcher window at any time.
echo.
pause
