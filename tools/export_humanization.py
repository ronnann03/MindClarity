"""Exportación por lista permitida: nunca copia .env, perfiles, audios ni logs."""
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    'core/conversation_style.py', 'voice/audio_capture.py', 'core/voice_commands.py',
    'tests/test_conversation_style.py', 'START_YU_LOCAL.ps1', 'CONFIGURAR_INICIO_YU.ps1',
    'core/orchestrator.py', 'voice/voice_pipeline.py', 'voice/speech_to_text.py',
    'voice/wake_word.py', 'config/settings.py', 'tests/test_voice_commands.py',
    'voice/vosk_wake.py', 'tests/test_vosk_wake.py', 'tools/setup_vosk.py', 'VOZ_YU.md',
    'voice/audio_service.py', 'voice/audio_worker.py',
    'tests/test_audio_service.py', 'tools/verify_vosk_voice.py',
]
README = """# Proyecto 07 · Humanización de un asistente de IA

## Objetivo
Crear una presencia cercana y discreta mediante saludos contextuales, voz en español y una experiencia que describa con honestidad las capacidades del asistente.

## Implementación real en YU
- Ollama para conversación local; Vosk para activación continua «YU escucha», Whisper para la orden y Piper para voz.
- Saludó según la hora de Lima: mañana 05:00–11:59, tarde 12:00–19:59 y noche el resto.
- Saludo al primer contacto, al cambiar de día o tras cuatro horas de pausa; no se usa un porcentaje aleatorio por respuesta.
- La transformación se aplica en el orquestador antes de guardar y enviar la respuesta. Texto y voz reciben la misma frase.
- Activación en dos pasos: «YU escucha», esperar «Te escucho» y dar la orden. El modo anterior de Whisper permanece configurable como alternativa.
- Confirmaciones de voz explícitas para las operaciones de riesgo.
- Arranque nativo de Windows con supervisor y bloqueo de duplicados.

## Uso
Los archivos son un módulo educativo extraído de YU, no una distribución completa ni un ejecutable independiente. Los iniciadores requieren ejecutarse desde una instalación completa de YU con Python, sus dependencias, Ollama y los modelos preparados.

Para probar solo los saludos, instala pytest y ejecuta:

```powershell
python -m pytest tests/test_conversation_style.py -k 'not orchestrator'
```

Ejemplo determinista:

```python
from datetime import datetime
from core.conversation_style import LIMA, humanize_response_by_time
for hour in (10,15,22):
    print(humanize_response_by_time('Estoy disponible.', now=datetime(2026,10,16,hour,tzinfo=LIMA)))
```

## Comprobación y límites
Las pruebas verifican horarios, zona horaria, ausencia de duplicados, orden completo, parámetros y confirmaciones. La prueba acústica del micrófono real y un nuevo inicio de sesión en Windows deben validarse en el equipo de destino; no se sustituyen con una prueba simulada.

Ningún asistente puede garantizar ejecutar cualquier petición. Las capacidades externas necesitan configuración, permisos y conectividad. Se debe comunicar una función no soportada o un fallo real en vez de afirmar que tuvo éxito.

## Privacidad del paquete
Se exporta una lista explícita de fuentes y pruebas. No contiene claves, perfiles, conversaciones, bases de datos, grabaciones ni modelos descargados.
"""


def export(destination: Path):
    destination = destination.resolve()
    target = destination / 'Anro IA Infoproducto' / '07_Humanizacion_Asistente_IA'
    if target.exists():
        target = target / ('edicion_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    target.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        source = ROOT / name
        output = target / name
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, output)
    (target / 'README.md').write_text(README, encoding='utf-8')
    archive = target.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in target.rglob('*'):
            if path.is_file():
                bundle.write(path, path.relative_to(target.parent))
    print(target)
    print(archive)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('desktop', type=Path)
    export(parser.parse_args().desktop)
