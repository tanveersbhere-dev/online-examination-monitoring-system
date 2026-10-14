@echo off
title ExamShield - Frontend UI
color 0A

echo ======================================================
echo           ExamShield - Frontend Application
echo ======================================================
echo.

cd /d "%~dp0"

call node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in your PATH.
    echo Please install Node.js [v18 or higher] from https://nodejs.org/
    pause
    exit /b 1
)

if not exist "node_modules\" (
    echo [*] node_modules not found. Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install npm dependencies.
        pause
        exit /b 1
    )
)

echo [*] Starting Vite Frontend Dev Server...
echo [*] Local URL: http://localhost:5173
echo [*] Press CTRL+C to stop the server.
echo.

call npm run dev

if errorlevel 1 (
    echo.
    echo [ERROR] Frontend dev server stopped unexpectedly.
    pause
)
