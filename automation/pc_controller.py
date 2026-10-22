"""Control del sistema: volumen, brillo, capturas, mouse, teclado, bloqueo."""
from __future__ import annotations

import ctypes
import datetime
from pathlib import Path

from config.settings import settings
from core.logger import log

# --- Importaciones opcionales (degradación elegante) ------------------- #
try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:  # noqa: BLE001
    pyautogui = None  # type: ignore

try:
    from ctypes import POINTER, cast
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    _PYCAW = True
except Exception:  # noqa: BLE001
    _PYCAW = False

try:
    import screen_brightness_control as sbc
except Exception:  # noqa: BLE001
    sbc = None  # type: ignore


class PCController:
    """Controla parámetros del sistema operativo."""

    # ------------------------------------------------------------------ #
    # Volumen
    # ------------------------------------------------------------------ #
    def _volume_interface(self):
        devices = AudioUtilities.GetSpeakers()
        if hasattr(devices, "EndpointVolume"):
            return devices.EndpointVolume
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))

    def set_volume(self, level: int) -> str:
        """Ajusta el volumen maestro (0-100)."""
        level = max(0, min(100, int(level)))
        if not _PYCAW:
            return "Control de volumen no disponible (instala pycaw)."
        try:
            vol = self._volume_interface()
            vol.SetMasterVolumeLevelScalar(level / 100.0, None)
            log.info("Volumen ajustado a {}%.", level)
            return f"Volumen al {level}%."
        except Exception as exc:  # noqa: BLE001
            log.error("Error ajustando volumen: {}", exc)
            return f"No pude ajustar el volumen: {exc}"

    def get_volume(self) -> str:
        if not _PYCAW:
            return "Control de volumen no disponible."
        try:
            vol = self._volume_interface()
            level = round(vol.GetMasterVolumeLevelScalar() * 100)
            return f"El volumen está al {level}%."
        except Exception as exc:  # noqa: BLE001
            return f"No pude leer el volumen: {exc}"

    # ------------------------------------------------------------------ #
    # Brillo
    # ------------------------------------------------------------------ #
    def set_brightness(self, level: int) -> str:
        level = max(0, min(100, int(level)))
        if sbc is None:
            return "Control de brillo no disponible (instala screen-brightness-control)."
        try:
            sbc.set_brightness(level)
            log.info("Brillo ajustado a {}%.", level)
            return f"Brillo al {level}%."
        except Exception as exc:  # noqa: BLE001
            return f"No pude ajustar el brillo: {exc}"

    # ------------------------------------------------------------------ #
    # Captura de pantalla
    # ------------------------------------------------------------------ #
    def take_screenshot(self, path: str | None = None) -> str:
        if pyautogui is None:
            return "Captura no disponible (instala pyautogui)."
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            out = Path(path) if path else settings.base_dir / f"captura_{ts}.png"
            img = pyautogui.screenshot()
            img.save(str(out))
            log.info("Captura guardada en {}.", out)
            return f"Captura de pantalla guardada en {out}."
        except Exception as exc:  # noqa: BLE001
            return f"No pude hacer la captura: {exc}"

    # ------------------------------------------------------------------ #
    # Bloqueo de pantalla
    # ------------------------------------------------------------------ #
    def lock_screen(self) -> str:
        try:
            ctypes.windll.user32.LockWorkStation()  # type: ignore[attr-defined]
            log.info("Pantalla bloqueada.")
            return "He bloqueado la pantalla."
        except Exception as exc:  # noqa: BLE001
            return f"No pude bloquear la pantalla: {exc}"

    # ------------------------------------------------------------------ #
    # Mouse y teclado
    # ------------------------------------------------------------------ #
    def control_mouse(self, x: int, y: int, click: bool = False) -> str:
        if pyautogui is None:
            return "Control de mouse no disponible."
        try:
            pyautogui.moveTo(int(x), int(y), duration=0.2)
            if click:
                pyautogui.click()
            return f"Mouse movido a ({x}, {y}){' y clic' if click else ''}."
        except Exception as exc:  # noqa: BLE001
            return f"Error controlando el mouse: {exc}"

    def type_text(self, text: str) -> str:
        """Escribe texto con soporte completo de Unicode (ñ, á, é…).

        Usa `keyboard.write` (Unicode) como primera opción y cae a
        `pyautogui.typewrite` (ASCII) si no está disponible.
        """
        try:
            import keyboard as kb  # noqa: PLC0415
            kb.write(text, delay=0.02)
            return "He escrito el texto solicitado."
        except Exception:  # noqa: BLE001
            pass
        if pyautogui is None:
            return "Escritura no disponible."
        try:
            # pyautogui.typewrite no soporta caracteres no-ASCII; se usa
            # como último recurso advirtiendo de la limitación.
            pyautogui.typewrite(text, interval=0.02)
            return "He escrito el texto (solo ASCII; instala 'keyboard' para Unicode)."
        except Exception as exc:  # noqa: BLE001
            return f"Error escribiendo texto: {exc}"

    def press_key(self, key: str) -> str:
        if pyautogui is None:
            return "Pulsación de teclas no disponible."
        try:
            # Soporta combinaciones tipo "ctrl+c".
            if "+" in key:
                pyautogui.hotkey(*[k.strip() for k in key.split("+")])
            else:
                pyautogui.press(key)
            return f"Tecla(s) '{key}' pulsada(s)."
        except Exception as exc:  # noqa: BLE001
            return f"Error pulsando tecla: {exc}"


pc_controller = PCController()
