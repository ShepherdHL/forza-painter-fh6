@echo off
:: Shows console output if startup fails.
call "%~dp0scripts\launch_app.bat" "%~dp0" console
exit /b %ERRORLEVEL%
