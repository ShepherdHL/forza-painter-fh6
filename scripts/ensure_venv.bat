@echo off
setlocal
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"
set "PYTHONDONTWRITEBYTECODE=1"
set "VENV_DIR=%ROOT%\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" -c "import psutil, win32api" >nul 2>nul
    if not errorlevel 1 (
        echo Project virtual environment is ready: %VENV_DIR%
        exit /b 0
    )
    echo Project virtual environment exists but core dependencies are missing.
    goto HaveVenv
)

call :find_python
if errorlevel 1 (
    echo No usable Python was found. Install 64-bit Python 3.10 to 3.13, then run this again.
    exit /b 1
)
echo Creating project virtual environment: %VENV_DIR%
%PYTHON_CMD% -m venv "%VENV_DIR%"
if errorlevel 1 goto Failed

:HaveVenv
if not exist "%VENV_PYTHON%" (
    echo Virtual environment was not created correctly: %VENV_PYTHON%
    goto Failed
)

echo Using project Python: "%VENV_PYTHON%"
"%VENV_PYTHON%" -m pip --version >nul 2>nul
if errorlevel 1 (
    echo Project Python is missing pip. Bootstrapping pip with ensurepip...
    "%VENV_PYTHON%" -m ensurepip --upgrade
    if errorlevel 1 goto Failed
)

"%VENV_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto Failed

"%VENV_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto Failed

"%VENV_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info < (3, 13) else 1)" >nul 2>nul
if errorlevel 1 (
    echo.
    echo Optional preview dependencies were skipped on Python 3.13 or newer.
    echo JSON generation and FH6 import can still run. If preview is required, install Python 3.12, delete .venv, then run this again.
) else (
    echo.
    echo Installing optional preview dependencies for image/JSON preview...
    "%VENV_PYTHON%" -m pip install -r requirements-preview.txt
    if errorlevel 1 (
        echo Optional preview dependencies failed. The app can still generate and import JSON.
    )
)

echo.
echo Dependencies installed.
echo Virtual environment: %VENV_DIR%
exit /b 0

:Failed
echo.
echo Dependency installation failed. Check the Python version and network, then try again.
exit /b 1

:find_python
for %%V in (3.12 3.11 3.10 3.13) do (
    py -%%V -c "import sys; raise SystemExit(0 if sys.maxsize > 2**32 else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=py -%%V"
        exit /b 0
    )
)
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) and sys.maxsize > 2**32 else 1)" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    exit /b 0
)
exit /b 1
