@echo off
chcp 65001 >nul
REM ================================================================
REM YU v2.0.0 - Iniciar API (Con información detallada)
REM ================================================================

cd /d "%~dp0"

echo.
echo ================================================================
echo         YU v2.0.0 - INICIANDO API REST
echo ================================================================
echo.
echo Puerto: 8080
echo URL:    http://localhost:8080
echo Docs:   http://localhost:8080/docs
echo WS:     ws://localhost:8080/ws/stream
echo.
echo ================================================================
echo INICIANDO SERVIDOR...
echo ================================================================
echo.

python -X utf8 -m uvicorn api.server:app --reload --host 0.0.0.0 --port 8080

echo.
echo ================================================================
echo SERVIDOR DETENIDO
echo ================================================================
echo.

pause
