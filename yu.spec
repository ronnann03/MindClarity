# -*- mode: python ; coding: utf-8 -*-
# ============================================================
# YU — especificación de empaquetado con PyInstaller
#
# Uso:
#   pip install pyinstaller
#   pyinstaller yu.spec
#
# El ejecutable final queda en:  dist/YU/YU.exe  (modo carpeta)
# ============================================================

import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # raíz del proyecto

block_cipher = None

# ------------------------------------------------------------------ #
# Datos a incluir (archivos no-Python que la app necesita en runtime) #
# ------------------------------------------------------------------ #
datas = [
    # Archivo .env con claves (se incluye; el usuario debe editarlo antes)
    (str(ROOT / ".env"),              "."),
    # Icono y recursos de UI (si existen)
    (str(ROOT / "ui" / "assets"),    "ui/assets"),
    # faster-whisper necesita sus modelos ONNX en disco
    # (se descargan al directorio de caché la primera vez)
]

# Incluir credentials.json de Google sólo si existe
_creds = ROOT / "credentials.json"
if _creds.exists():
    datas.append((str(_creds), "."))

# ------------------------------------------------------------------ #
# Imports ocultos — módulos que PyInstaller no detecta automáticamente #
# ------------------------------------------------------------------ #
hiddenimports = [
    # PyQt6 y sus plugins
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.sip",
    # faster-whisper / CTranslate2
    "faster_whisper",
    "ctranslate2",
    # sounddevice / soundfile / numpy
    "sounddevice",
    "soundfile",
    "numpy",
    "numpy.core._multiarray_umath",
    # httpx y cliente async
    "httpx",
    "anyio",
    "anyio._backends._asyncio",
    # Pydantic v2
    "pydantic",
    "pydantic_core",
    "pydantic_settings",
    # OpenAI SDK
    "openai",
    "openai._client",
    "openai.resources",
    # Automatización Windows
    "pyautogui",
    "psutil",
    "keyboard",
    "mouse",
    "pygetwindow",
    "pycaw",
    "comtypes",
    "screen_brightness_control",
    "send2trash",
    "win32api",
    "win32con",
    "win32gui",
    "win32com",
    # Google APIs
    "googleapiclient",
    "google.auth",
    "google.oauth2",
    "google_auth_oauthlib",
    # Supabase
    "supabase",
    "postgrest",
    "gotrue",
    "realtime",
    "storage3",
    # loguru
    "loguru",
    # Otros
    "dotenv",
    "python_dotenv",
]

# ------------------------------------------------------------------ #
# Binarios adicionales (DLLs de sounddevice, etc.)                   #
# ------------------------------------------------------------------ #
binaries = []

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Excluir módulos de desarrollo/test para reducir el tamaño
        "pytest",
        "pytest_asyncio",
        "tkinter",
        "matplotlib",
        "PIL",
        "IPython",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YU",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # Sin ventana de consola (modo GUI)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="ui/assets/yu.ico",  # Descomenta si tienes un icono
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="YU",
)
