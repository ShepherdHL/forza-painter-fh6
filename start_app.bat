@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%" || (
    echo Cannot enter app folder: "%ROOT%"
    pause
    exit /b 1
)

:: Development launcher — does not auto-elevate. Use Import in the app to trigger
:: administrator access when FH6 memory attach is required.
set "PYTHONDONTWRITEBYTECODE=1"
set "VENV_PYTHON=%ROOT%.venv\Scripts\pythonw.exe"
set "VENV_PYTHON_CONSOLE=%ROOT%.venv\Scripts\python.exe"
set "BOOTSTRAP=%ROOT%scripts\ensure_venv.bat"
if not exist "%BOOTSTRAP%" (
    echo Required startup file is missing:
    echo "%BOOTSTRAP%"
    pause
    exit /b 1
)

:: Dependency setup may flash a console briefly on first run
call "%BOOTSTRAP%"
if errorlevel 1 (
    pause
    exit /b 1
)

if not exist "%VENV_PYTHON%" (
    set "VENV_PYTHON=%VENV_PYTHON_CONSOLE%"
)

:: Launch GUI without a lingering command window
start "" /MIN "%VENV_PYTHON%" "%ROOT%src\app.py"
exit /b 0
