"""Proceso de audio aislado de COM e integraciones de escritorio de YU."""
import asyncio
import json
import os
import queue
import sys
import threading

os.environ['YU_AUDIO_WORKER'] = '1'
from voice.audio_capture import AUDIO_LEVEL, close_microphone
from voice.vosk_wake import vosk_wake


def emit(event):
    print(json.dumps(event, ensure_ascii=True), flush=True)


async def main():
    # Cargar las librerías nativas antes de crear el lector de stdin.
    from scipy.signal import resample_poly
    import sounddevice
    vosk_wake._ensure_model()
    from voice.speech_to_text import speech_to_text
    speech_to_text._ensure_model()
    emit({'type': 'started'})
    requests = queue.Queue()
    stopped = threading.Event()

    def read_commands():
        try:
            while True:
                line = sys.stdin.readline()
                if not line:
                    break
                requests.put(json.loads(line))
        finally:
            stopped.set()

    threading.Thread(target=read_commands, daemon=True).start()
    while not stopped.is_set():
        try:
            request = requests.get_nowait()
        except queue.Empty:
            await asyncio.sleep(.1)
            continue
        try:
            emit({'type': 'accepted', 'kind': request['kind']})
            if request['kind'] == 'wake':
                operation = asyncio.create_task(asyncio.to_thread(vosk_wake.listen,
                    timeout=request['timeout'], should_stop=stopped.is_set))
            else:
                async def command():
                    audio = await speech_to_text.record_audio(should_stop=stopped.is_set)
                    return await speech_to_text.transcribe(audio) if audio.size else ''

                operation = asyncio.create_task(command())
            while not operation.done():
                emit({'type': 'level', 'level': dict(AUDIO_LEVEL)})
                await asyncio.wait({operation}, timeout=.3)
            value = operation.result()
            emit({'type': 'result', 'value': value})
        except Exception as exc:
            close_microphone()
            emit({'type': 'error', 'message': str(exc)})
    close_microphone()


if __name__ == '__main__':
    asyncio.run(main())
