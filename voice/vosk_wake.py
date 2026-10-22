"""Detector continuo de «YU escucha», sin Whisper, sin almacenar grabaciones."""
import json
from pathlib import Path
import queue
import time
import numpy as np

from config.settings import settings, BASE_DIR
from core.logger import log
from voice.audio_capture import AUDIO_LEVEL, close_microphone, resolve_input_device


def wake_grammar(wake_word='yu'):
    # Competidores acústicos: no forzar «yo escucho» o «YouTube» a ser el nombre.
    return [wake_word + ' escucha', 'iu escucha', 'yo escucho', 'yo quiero',
            'youtube', 'ayuda', 'escucha', '[unk]']


def accepts_activation(result: dict, wake_word='yu') -> bool:
    words = result.get('result') or []
    if len(words) < 2:
        return False
    first, second = words[:2]
    return (first.get('word') in {wake_word.lower(), 'iu'}
            and second.get('word') == 'escucha'
            and 0 <= second.get('start', 99) - first.get('end', 0) <= .8
            and all(word.get('conf', 0) >= .80 for word in (first, second)))


class VoskWake:
    def __init__(self):
        self.model = None

    def _ensure_model(self):
        if self.model is None:
            from vosk import Model, SetLogLevel
            path = Path(settings.vosk_model_path)
            if not path.is_absolute():
                path = BASE_DIR / path
            if not (path / 'am/final.mdl').is_file():
                raise RuntimeError('Falta el modelo Vosk español: ' + str(path))
            SetLogLevel(-1)
            self.model = Model(str(path))
            log.info('Detector Vosk español preparado: YU escucha')
        return self.model

    def listen(self, *, timeout=60, should_stop=None):
        import sounddevice as sd
        from scipy.signal import resample_poly
        from math import gcd
        from vosk import KaldiRecognizer
        model = self._ensure_model()
        rec = KaldiRecognizer(model, 16000, json.dumps(wake_grammar(settings.wake_word)))
        rec.SetWords(True)
        frames = queue.Queue(maxsize=30)
        errors = []
        close_microphone()
        device, rate = resolve_input_device(sd)
        log.info('Entrada de activación: {} / {} / {} Hz', AUDIO_LEVEL['device'], AUDIO_LEVEL['hostapi'], rate)

        def callback(indata, frame_count, time_info, status):
            audio = np.frombuffer(indata, dtype=np.int16).astype(np.float32) / 32768
            AUDIO_LEVEL.update(ready=True, rms=float(np.sqrt(np.mean(audio ** 2))),
                               peak=float(np.max(np.abs(audio))), updated_at=time.time())
            if status:
                errors.append(str(status))
            try:
                # Ganancia limitada; el motor recibe audio continuo, sin umbral de energía.
                frames.put_nowait(audio.copy())
            except queue.Full:
                errors.append('cola de audio llena')

        try:
            with sd.RawInputStream(samplerate=rate, blocksize=rate // 10, channels=1,
                    dtype='int16', device=device, callback=callback):
                AUDIO_LEVEL['ready'] = True
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    if should_stop and should_stop():
                        return False
                    if errors:
                        raise RuntimeError('Captura de activación interrumpida: ' + errors[0])
                    try:
                        block = frames.get(timeout=.2)
                    except queue.Empty:
                        continue
                    if rate != 16000:
                        divisor = gcd(rate, 16000)
                        block = resample_poly(block, 16000 // divisor, rate // divisor)
                    pcm = (np.clip(block * 6, -1, 1) * 32767).astype(np.int16).tobytes()
                    if rec.AcceptWaveform(pcm):
                        result = json.loads(rec.Result())
                        if accepts_activation(result, settings.wake_word):
                            return True
                        rec.Reset()
                return False
        finally:
            AUDIO_LEVEL['ready'] = False


vosk_wake = VoskWake()
