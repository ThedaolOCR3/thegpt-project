::로컬에서 테스트할 때, node.js와 uvicon 서버를 한번에 실행 가능
::package.json 세팅과 venv 가상환경, 라이브러리 설치가 선행되어야 한다.

@echo off
setlocal
chcp 65001 > nul
title Medical AI Project Launcher

set "PROJECT_ROOT=%~dp0"
set "BACKEND_DIR=%PROJECT_ROOT%backend"
set "FRONTEND_DIR=%PROJECT_ROOT%frontend"
set "VENV_ACTIVATE=%BACKEND_DIR%\.venv\Scripts\activate.bat"

echo ========================================
echo   Medical AI Project Start
echo ========================================
echo.

REM Validate everything before opening either development server.
if not exist "%VENV_ACTIVATE%" (
    echo [ERROR] Backend virtual environment was not found:
    echo         "%VENV_ACTIVATE%"
    echo.
    echo Create it with: python -m venv backend\.venv
    pause
    exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
    echo [ERROR] Frontend package.json was not found:
    echo         "%FRONTEND_DIR%\package.json"
    pause
    exit /b 1
)

where npm.cmd > nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found. Install Node.js and try again.
    pause
    exit /b 1
)

echo [1/2] Starting Backend with backend\.venv...
start "FastAPI Backend" /D "%BACKEND_DIR%" cmd.exe /k "call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload"

echo [2/2] Starting Frontend with npm run dev...
start "React Frontend" /D "%FRONTEND_DIR%" cmd.exe /k "npm.cmd run dev"

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
echo Each server is running in its own terminal window.
echo Close those windows or press Ctrl+C in each one to stop the servers.
echo.
pause

endlocal
