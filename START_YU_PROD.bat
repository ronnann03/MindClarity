@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
REM ================================================================
REM YU v2.0.0 - Arranque de PRODUCCION
REM   - Sin "pause": pensado para correr desatendido (Task Scheduler).
REM   - Auto-reinicio si el proceso se cae, con backoff simple.
REM   - Registra cada arranque/caida en logs\supervisor.log
REM ================================================================

cd /d "%~dp0"

set "PYTHON_EXE=C:\Program Files\Python314\python.exe"
set "LOGDIR=%~dp0logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "SUPLOG=%LOGDIR%\supervisor.log"
set "YU_PORT=8000"

echo [%date% %time%] Supervisor iniciado (puerto %YU_PORT%) >> "%SUPLOG%"

set /a RESTART_COUNT=0

:loop
echo [%date% %time%] Arrancando YU (intento !RESTART_COUNT!)... >> "%SUPLOG%"
"%PYTHON_EXE%" -X utf8 main.py
set "EXITCODE=%ERRORLEVEL%"
echo [%date% %time%] YU termino con codigo %EXITCODE% >> "%SUPLOG%"

set /a RESTART_COUNT+=1
if !RESTART_COUNT! GEQ 20 (
    echo [%date% %time%] Demasiados reinicios ^(!RESTART_COUNT!^), deteniendo supervisor. >> "%SUPLOG%"
    goto :eof
)

REM Pequena espera antes de reintentar para evitar bucles de fallo inmediato.
timeout /t 5 /nobreak >nul
goto loop
