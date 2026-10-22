"""Configuración de logging con loguru.

Proporciona salida coloreada a consola y archivos rotados diariamente.
"""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from config.settings import settings

_CONFIGURED = False


def setup_logger() -> "logger.__class__":
    """Configura loguru (idempotente) y devuelve el logger global.

    - Consola con colores y nivel configurable.
    - Archivo diario con rotación a medianoche y retención de 14 días.
    - Archivo separado solo para errores.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return logger

    log_dir: Path = settings.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()  # Elimina el handler por defecto.

    # ---- Consola (coloreada) -------------------------------------------- #
    logger.add(
        sys.stderr,
        level=settings.log_level,
        colorize=True,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        backtrace=True,
        diagnose=False,
    )

    # ---- Archivo general (rotación diaria) ------------------------------ #
    logger.add(
        log_dir / "yu_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="00:00",        # Rota cada medianoche.
        retention="14 days",     # Conserva 14 días.
        compression="zip",
        encoding="utf-8",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        enqueue=True,            # Seguro entre hilos/procesos.
    )

    # ---- Archivo de errores --------------------------------------------- #
    logger.add(
        log_dir / "errors_{time:YYYY-MM-DD}.log",
        level="ERROR",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    _CONFIGURED = True
    logger.info("Logger inicializado | nivel={}", settings.log_level)
    return logger


# Logger global ya configurado al importar el módulo.
log = setup_logger()
