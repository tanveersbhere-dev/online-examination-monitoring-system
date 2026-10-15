@echo off
title AI Monitoring Unit Host — Frontend
echo.
echo  ======================================================
echo    AI Monitoring Unit Host — Frontend UI (React + Vite)
echo  ======================================================
echo.
cd /d "%~dp0frontend"

if not exist "node_modules\" (
    echo  Installing frontend dependencies...
    call npm install
)

echo.
echo  Starting Vite dev server on https://localhost:5173 ...
echo.
call npm run dev
if errorlevel 1 (
    echo.
    echo  [ERROR] Frontend dev server stopped or failed.
    pause
)
