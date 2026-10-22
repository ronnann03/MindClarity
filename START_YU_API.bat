@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
REM ================================================================
REM YU v2.0.0 - Iniciar en un puerto configurable
REM ================================================================

cd /d "%~dp0"
echo.
echo ========================================
echo   YU v2.0.0 - Puerto configurable
echo ========================================
echo.

REM Puerto por defecto
SET YU_PORT=8000

REM Si se pasa un argumento, usarlo como puerto
IF NOT "%1"=="" SET YU_PORT=%1

echo Iniciando YU en puerto %YU_PORT%...
echo.
echo Accede a:
echo   - Web:  http://localhost:%YU_PORT%
echo   - Docs: http://localhost:%YU_PORT%/docs
echo   - WS:   ws://localhost:%YU_PORT%/ws/stream
echo.
echo (Presiona Ctrl+C para detener)
echo.

python -X utf8 main.py

pause
