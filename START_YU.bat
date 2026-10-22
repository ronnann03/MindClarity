@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
REM ================================================================
REM YU v2.0.0 - Iniciar (agentes + wake word + interfaz web)
REM ================================================================

cd /d "%~dp0"
echo.
echo ========================================
echo       YU v2.0.0
echo ========================================
echo.
echo Iniciando YU...
echo Interfaz web: http://localhost:8000
echo.

python -X utf8 main.py

pause
