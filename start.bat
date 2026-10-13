@echo off
rem Startet Mochi ohne Konsolenfenster
cd /d "%~dp0"
if exist "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" main.py
) else (
    start "" pythonw main.py
)
