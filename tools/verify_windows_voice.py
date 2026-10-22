"""Prueba del reconocedor Windows con voz sintética; nunca ejecuta órdenes."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main():
    from voice.tts_offline import PiperTTS
    voice = PiperTTS()
    helper = Path(__file__).with_name('windows_listener_diagnostic.ps1')
    executable = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    cases = [('Yu, abre la calculadora.', True), ('Yu.', True),
             ('Abre la calculadora.', False), ('Estoy hablando con otra persona.', False)]
    with tempfile.TemporaryDirectory() as directory:
        for index, (phrase, expected) in enumerate(cases):
            pcm = await voice.synthesize(phrase)
            if not pcm:
                raise RuntimeError('No se pudo sintetizar el audio de prueba')
            path = Path(directory) / f'synthetic-{index}.wav'
            with wave.open(str(path), 'wb') as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(voice.sample_rate)
                output.writeframes(pcm)
                output.writeframes(b'\x00\x00' * (voice.sample_rate * 2))
            result = subprocess.run([str(executable), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                str(helper), '-AudioPath', str(path), '-Timeout', '10'], capture_output=True, timeout=30)
            events = [json.loads(line) for line in result.stdout.decode('utf-8-sig').splitlines() if line.strip()]
            accepted = any(e.get('type') == 'result' and e.get('confidence', 0) >= .6 for e in events)
            print(json.dumps({'phrase': phrase, 'expected': expected, 'accepted': accepted, 'events': events}, ensure_ascii=False), flush=True)
            assert result.returncode == 0, events
            # Mostrar todos los casos antes de decidir si el motor es utilizable.


if __name__ == '__main__':
    asyncio.run(main())
