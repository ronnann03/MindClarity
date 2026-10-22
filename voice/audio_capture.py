"""Captura por frases: termina al detectar silencio, sin grabar mientras YU habla."""
from collections import deque
from typing import Callable
import time
import threading
import numpy as np

AUDIO_LEVEL = {'rms':0.0, 'peak':0.0, 'updated_at':0.0, 'ready':False}
_STREAM = None
_STREAM_LOCK = threading.Lock()


def resolve_input_device(sd):
    from config.settings import settings
    device = settings.voice_input_device
    if settings.voice_input_hostapi:
        match = next((api for api in sd.query_hostapis()
                      if settings.voice_input_hostapi.lower() in api['name'].lower()), None)
        if match is None or match['default_input_device'] < 0:
            raise RuntimeError('No hay micrófono disponible en ' + settings.voice_input_hostapi)
        device = match['default_input_device']
    info = sd.query_devices(device, 'input')
    host = sd.query_hostapis(info['hostapi'])['name']
    AUDIO_LEVEL.update(device=info['name'], hostapi=host, sample_rate=int(info['default_samplerate']))
    return device, int(info['default_samplerate'])


def close_microphone():
    global _STREAM
    if _STREAM is not None:
        try:
            _STREAM.abort()
            _STREAM.close()
        finally:
            _STREAM = None
            AUDIO_LEVEL['ready'] = False


class SpeechSegmenter:
    def __init__(self, sample_rate: int, threshold: float, silence_seconds: float):
        self.threshold = threshold
        self.silence_limit = int(sample_rate * silence_seconds)
        self.pre = deque(maxlen=8)
        self.frames = []
        self.silent_samples = 0
        self.started = False

    def feed(self, frame: np.ndarray) -> bool:
        frame = frame.flatten().copy()
        voiced = bool(frame.size and np.sqrt(np.mean(frame ** 2)) >= self.threshold)
        if not self.started:
            self.pre.append(frame)
            if not voiced:
                return False
            self.started = True
            self.frames.extend(self.pre)
        else:
            self.frames.append(frame)
        self.silent_samples = 0 if voiced else self.silent_samples + frame.size
        return self.silent_samples >= self.silence_limit

    def audio(self) -> np.ndarray:
        return np.concatenate(self.frames) if self.frames else np.array([], dtype=np.float32)


def capture_utterance(*, sample_rate: int, threshold: float, silence_seconds: float,
                      start_timeout: float, max_seconds: float,
                      should_stop: Callable[[], bool] | None = None) -> np.ndarray:
    import sounddevice as sd
    global _STREAM
    with _STREAM_LOCK:
        block = int(sample_rate * 0.2)
        from config.settings import settings
        capture_rate = sample_rate
        device = settings.voice_input_device
        if device is not None or settings.voice_input_hostapi:
            device, capture_rate = resolve_input_device(sd)
        capture_block = int(capture_rate * .2)
        if _STREAM is None or not _STREAM.active:
            close_microphone()
            _STREAM = sd.InputStream(samplerate=capture_rate, channels=1, dtype='float32', blocksize=capture_block,
                                     device=device)
            _STREAM.start()
            AUDIO_LEVEL['ready'] = True
        stream = _STREAM
        # Descarta audio acumulado mientras YU hablaba o transcribía.
        available = stream.read_available
        if available:
            stream.read(available)
        segmenter = SpeechSegmenter(sample_rate, threshold, silence_seconds)
        begin = time.monotonic()
        speech_begin = None
        while True:
            if should_stop and should_stop():
                return np.array([], dtype=np.float32)
            frame, overflowed = stream.read(capture_block)
            if overflowed:
                raise RuntimeError('El micrófono perdió audio durante la orden')
            if capture_rate != sample_rate:
                from math import gcd
                from scipy.signal import resample_poly
                divisor = gcd(capture_rate, sample_rate)
                frame = resample_poly(frame, sample_rate // divisor, capture_rate // divisor, axis=0)
            AUDIO_LEVEL.update(rms=float(np.sqrt(np.mean(frame ** 2))),
                               peak=float(np.max(np.abs(frame))), updated_at=time.time())
            if should_stop and should_stop():
                return np.array([], dtype=np.float32)
            if segmenter.feed(frame):
                break
            now = time.monotonic()
            if segmenter.started:
                if speech_begin is None:
                    speech_begin = now
                if now - speech_begin >= max_seconds:
                    break
            elif now - begin >= start_timeout:
                break
        return segmenter.audio()
