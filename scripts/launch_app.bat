@echo off
setlocal EnableExtensions
set "PYTHONDONTWRITEBYTECODE=1"

call "%~dp0resolve_app_root.bat" "%~1"
if errorlevel 1 (
    echo.
    echo Could not find the Forza Painter app folder.
    echo.
    echo Make sure you extracted the full ZIP, then run:
    echo   Start Forza Painter.bat
    echo from the folder that contains src\ and scripts\.
    echo.
    echo Normal users: download the .exe from GitHub Releases instead of source ZIP.
    echo https://github.com/ShepherdHL/forza-painter-fh6/releases
    echo.
    pause
    exit /b 1
)

set "ROOT=%RESOLVED_ROOT%"
cd /d "%ROOT%" || (
    echo Cannot enter app folder: "%ROOT%"
    pause
    exit /b 1
)

set "VENV_PYTHON=%ROOT%.venv\Scripts\pythonw.exe"
set "VENV_PYTHON_CONSOLE=%ROOT%.venv\Scripts\python.exe"
set "BOOTSTRAP=%ROOT%scripts\ensure_venv.bat"
set "APP_PY=%ROOT%src\app.py"

echo Forza Painter — preparing environment...
call "%BOOTSTRAP%"
if errorlevel 1 (
    echo.
    echo Dependency setup failed. Install Python 3.10-3.13 ^(64-bit^), then try again.
    pause
    exit /b 1
)

if not exist "%VENV_PYTHON_CONSOLE%" (
    echo Virtual environment is missing: %VENV_PYTHON_CONSOLE%
    pause
    exit /b 1
)

echo Checking startup...
"%VENV_PYTHON_CONSOLE%" -c "import sys; sys.path.insert(0, 'src'); import app"
if errorlevel 1 (
    echo.
    echo The app failed to load. See the error above.
    echo.
    pause
    exit /b 1
)

if not exist "%VENV_PYTHON%" (
    set "VENV_PYTHON=%VENV_PYTHON_CONSOLE%"
)

if /i "%~2"=="console" (
    echo Launching ^(console mode^)...
    "%VENV_PYTHON_CONSOLE%" "%APP_PY%"
    set "EXIT_CODE=%ERRORLEVEL%"
    if not "%EXIT_CODE%"=="0" pause
    exit /b %EXIT_CODE%
)

echo Launching...
start "" /D "%ROOT%" /MIN "%VENV_PYTHON%" "%APP_PY%"
exit /b 0
