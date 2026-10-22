@echo off
REM ================================================================
REM YU v2.0.0 - Setup Completo
REM ================================================================

cd /d "%~dp0"
echo.
echo ========================================
echo   YU v2.0.0 - SETUP COMPLETO
echo ========================================
echo.

REM Verificar Python
echo Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado. Instala Python 3.12+
    pause
    exit /b 1
)
echo OK - Python instalado

REM Crear entorno virtual si no existe
if not exist ".venv" (
    echo.
    echo Creando entorno virtual...
    python -m venv .venv
    echo OK - Entorno virtual creado
)

REM Activar entorno virtual
echo.
echo Activando entorno virtual...
call .venv\Scripts\activate.bat
echo OK - Entorno virtual activado

REM Instalar dependencias
echo.
echo Instalando dependencias (esto puede tomar unos minutos)...
pip install -r requirements.txt --upgrade >nul 2>&1
if errorlevel 1 (
    echo ERROR: No se pudieron instalar las dependencias
    pause
    exit /b 1
)
echo OK - Dependencias instaladas

REM Verificar archivos críticos
echo.
echo Verificando archivos...
if not exist ".env" (
    echo AVISO: .env no encontrado, copiando .env.example
    copy .env.example .env >nul
)
echo OK - Configuración lista

echo.
echo ========================================
echo SETUP COMPLETADO EXITOSAMENTE
echo ========================================
echo.
echo Para iniciar YU:
echo   - GUI:  Haz doble clic en "START_YU_GUI.bat"
echo   - API:  Haz doble clic en "START_YU_API.bat"
echo.
pause
