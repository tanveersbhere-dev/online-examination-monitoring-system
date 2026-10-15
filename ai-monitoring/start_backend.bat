@echo off
title AI Monitoring Unit Host — Backend
echo.
echo  ======================================================
echo    AI Monitoring Unit Host — Backend Server (FastAPI)
echo  ======================================================
echo.
cd /d "%~dp0"

set "PYTHONPATH=%~dp0;%PYTHONPATH%"


if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo  Starting FastAPI backend on http://localhost:8000 ...
echo  Loading AI Pipeline (19 stages)...
echo.
"%PYTHON_EXE%" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info --reload
if errorlevel 1 (
    echo.
    echo  [ERROR] Backend server stopped or failed.
    pause
)
