@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%" || (
    echo Cannot enter app folder: "%ROOT%"
    pause
    exit /b 1
)
set "PYTHONDONTWRITEBYTECODE=1"
set "BOOTSTRAP=%ROOT%scripts\ensure_venv.bat"
if not exist "%BOOTSTRAP%" (
    echo Required startup file is missing:
    echo "%BOOTSTRAP%"
    echo.
    echo Extract the whole release ZIP first, then run this file from the extracted folder.
    pause
    exit /b 1
)
call "%BOOTSTRAP%"
if errorlevel 1 (
    pause
    exit /b 1
)
pause
exit /b 0
