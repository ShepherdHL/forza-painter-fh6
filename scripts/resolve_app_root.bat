@echo off
setlocal EnableExtensions
:: Resolve the directory that contains src\app.py and scripts\ensure_venv.bat.
:: Handles GitHub ZIP double-extract (forza-painter-fh6-main\forza-painter-fh6-main).
set "TRY=%~1"
if not defined TRY exit /b 1
if "%TRY:~-1%"=="\" set "TRY=%TRY:~0,-1%"

call :_is_app_root "%TRY%"
if not errorlevel 1 (
    endlocal & set "RESOLVED_ROOT=%TRY%\"
    exit /b 0
)

if exist "%TRY%\forza-painter-fh6-main\scripts\ensure_venv.bat" if exist "%TRY%\forza-painter-fh6-main\src\app.py" (
    endlocal & set "RESOLVED_ROOT=%TRY%\forza-painter-fh6-main\"
    exit /b 0
)

for /d %%D in ("%TRY%\*") do (
    if exist "%%~D\scripts\ensure_venv.bat" if exist "%%~D\src\app.py" (
        endlocal & set "RESOLVED_ROOT=%%~D\"
        exit /b 0
    )
)

endlocal
exit /b 1

:_is_app_root
if exist "%~1\scripts\ensure_venv.bat" if exist "%~1\src\app.py" exit /b 0
exit /b 1
