@echo off
setlocal
color 0F
title Forza Painter 1.6.X (Experimental)
set "PYTHONDONTWRITEBYTECODE=1"

set "ROOT=%~dp0"
cd /d "%ROOT%" || (
    echo Cannot enter app folder: "%ROOT%"
    pause
    exit /b 1
)
set "ARG1=%~1"
set "VENV_PYTHON=%ROOT%.venv\Scripts\python.exe"
set "BOOTSTRAP=%ROOT%scripts\ensure_venv.bat"

IF NOT "%ARG1%" == "" GOTO Dragged

set /p ARG1="[MANUAL MODE] Paste the image path: "

:Dragged
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

"%VENV_PYTHON%" src\app.py "%ARG1%"
cls
color 0F
echo FINISHED!
pause
exit /b %errorlevel%
