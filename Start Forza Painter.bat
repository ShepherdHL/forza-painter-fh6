@echo off
:: Main launcher — double-click this after extracting the download.
call "%~dp0scripts\launch_app.bat" "%~dp0"
exit /b %ERRORLEVEL%
