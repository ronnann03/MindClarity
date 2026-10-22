"""Comparación sintética local; no usa el micrófono ni ejecuta órdenes."""
import asyncio
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main():
    from vosk import Model, KaldiRecognizer, SetLogLevel
    from voice.tts_offline import PiperTTS
    from voice.vosk_wake import accepts_activation, wake_grammar
    SetLogLevel(-1)
    model = Model(str(Path('.cache/vosk/vosk-model-small-es-0.42').resolve()))
    voice = PiperTTS()
    for phrase in ['Yu, escucha.', 'Yu escucha, abre la calculadora.', 'Yu.', 'Abre la calculadora.',
                   'Estoy hablando con otra persona.', 'Yo quiero abrir la calculadora.',
                   'Ayuda con mis ideas.', 'YouTube.', 'Yu, dime la hora.',
                   'Yo escucho música.', 'Escucha lo que te digo.']:
        pcm = await voice.synthesize(phrase)
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
        audio = np.interp(np.arange(round(len(audio)*16000/voice.sample_rate))*voice.sample_rate/16000, np.arange(len(audio)), audio)
        pcm = audio.astype(np.int16).tobytes() + b'\x00\x00' * 16000
        results = []
        for grammar in [None, json.dumps(wake_grammar())]:
            rec = KaldiRecognizer(model, 16000, grammar) if grammar else KaldiRecognizer(model,16000)
            rec.SetWords(True)
            rec.AcceptWaveform(pcm)
            results.append(json.loads(rec.FinalResult()))
        print(json.dumps({'phrase':phrase,'results':results},ensure_ascii=False),flush=True)
        expected = phrase in {'Yu, escucha.', 'Yu escucha, abre la calculadora.'}
        assert accepts_activation(results[1]) == expected, results[1]


if __name__ == '__main__':
    asyncio.run(main())
