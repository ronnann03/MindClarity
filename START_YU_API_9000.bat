@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
REM YU en puerto 9000
cd /d "%~dp0"
set YU_PORT=9000
echo Iniciando YU en puerto 9000...
echo Accede a: http://localhost:9000
python -X utf8 main.py
pause
