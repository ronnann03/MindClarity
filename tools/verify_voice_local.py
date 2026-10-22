"""Prueba sintética de voz local; no ejecuta órdenes ni graba el micrófono."""
import asyncio
import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def check():
    from voice.tts_router import tts_router
    from voice.speech_to_text import speech_to_text
    from voice.wake_word import wake_word_detector
    import sounddevice as sd
    engine = tts_router.piper_tts
    if not engine or not engine.piper:
        raise RuntimeError('Piper local no está disponible')
    rows = []
    for phrase in ['Yu, abre la calculadora.', 'Confirmar acción.', 'Cancela la acción.']:
        pcm = await engine.synthesize(phrase)
        if not pcm:
            raise RuntimeError('No se generó audio local')
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768
        old_rate = engine.piper.sample_rate
        audio = np.interp(np.arange(round(len(audio) * 16000 / old_rate)) * old_rate / 16000,
                          np.arange(len(audio)), audio).astype(np.float32)
        transcript = await speech_to_text.transcribe(audio)
        row = {'phrase':phrase, 'transcript':transcript}
        if phrase.startswith('Yu'):
            row['command'] = wake_word_detector.extract_command(transcript)
        rows.append(row)
    print(json.dumps({'synthetic_voice':rows, 'input_device':sd.query_devices(kind='input')['name']},ensure_ascii=False))
    assert rows[0]['command'] and 'calculadora' in rows[0]['command'].lower(), rows[0]
    assert 'confirmar' in rows[1]['transcript'].lower(), rows[1]


if __name__ == '__main__':
    asyncio.run(check())
