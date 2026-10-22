@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
REM YU en puerto 8080
cd /d "%~dp0"
set YU_PORT=8080
echo Iniciando YU en puerto 8080...
echo Accede a: http://localhost:8080
python -X utf8 main.py
pause
