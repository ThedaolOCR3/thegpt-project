::프론트엔드 서버와 백엔드 서버를 한번에 실행할 수 있습니다.

@echo off
chcp 65001 > nul
title Medical AI Project Launcher

echo ========================================
echo   Medical AI Project Start
echo ========================================
echo.

REM ================================
REM Backend 실행
REM ================================
echo [1/2] Starting Backend...

start "FastAPI Backend" cmd /k ^
"cd /d "%~dp0backend" && .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload"

REM ================================
REM Frontend 실행
REM ================================
echo [2/2] Starting Frontend...

start "React Frontend" cmd /k ^
"cd /d "%~dp0frontend" && npm.cmd run dev"

echo.
echo ========================================
echo   Backend / Frontend launched
echo ========================================
echo.
echo Backend      : http://localhost:8000
echo Swagger Docs : http://localhost:8000/docs
echo Frontend     : http://localhost:5173
echo Admin Page   : http://localhost:5173/admin
echo.

pause