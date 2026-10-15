@echo off
title AI Monitoring Unit Host — Launcher
echo.
echo  ======================================================
echo    AI Monitoring Unit Host — Full System Launcher
echo  ======================================================
echo.
cd /d "%~dp0"

echo  [1/3] Launching Backend Server on http://localhost:8000 ...
start "AI Monitoring Host - Backend" cmd /c "call "%~dp0start_backend.bat""

echo  [2/3] Launching Frontend Server on http://localhost:5173 ...
start "AI Monitoring Host - Frontend" cmd /c "call "%~dp0start_frontend.bat""

echo  [3/3] Fast-probing backend readiness...
powershell -NoProfile -Command "$count=0; while($count -lt 40) { try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 1 -UseBasicParsing -ErrorAction Stop; if ($r.StatusCode -eq 200) { Write-Host '  Backend is READY and healthy!'; break; } } catch {} Start-Sleep -Milliseconds 300; $count++ }"

echo.
echo  Opening browser to https://localhost:5173 ...
start https://localhost:5173

echo.
echo  ======================================================
echo    AI Monitoring Unit Host is running!
echo    - Frontend UI:   https://localhost:5173
echo    - Backend API:   http://localhost:8000
echo    - WebSocket:     ws://localhost:8000/ws/monitor
echo    - Session Info:  http://localhost:8000/session
echo  ======================================================
echo.
