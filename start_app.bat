@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%" || (
    echo Cannot enter app folder: "%ROOT%"
    pause
    exit /b 1
)
set "PYTHONDONTWRITEBYTECODE=1"
set "VENV_PYTHON=%ROOT%.venv\Scripts\python.exe"
set "BOOTSTRAP=%ROOT%scripts\ensure_venv.bat"
if not exist "%BOOTSTRAP%" (
    echo Required startup file is missing:
    echo "%BOOTSTRAP%"
    echo.
    echo Extract the whole release ZIP first, then run start_app.bat from the extracted folder.
    pause
    exit /b 1
)
call "%BOOTSTRAP%"
if errorlevel 1 (
    pause
    exit /b 1
)
"%VENV_PYTHON%" src\app.py
pause
exit /b %errorlevel%
