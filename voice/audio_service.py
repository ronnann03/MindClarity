"""Cliente del proceso de audio local; nunca usa la red ni graba en disco."""
import asyncio
import json
import os
import sys
import time
from config.settings import BASE_DIR
from voice.audio_capture import AUDIO_LEVEL


class AudioService:
    def __init__(self):
        self.process = None

    async def listen(self, kind, timeout=3600, should_stop=None):
        if self.process is None or self.process.returncode is not None:
            options = {'creationflags': 0x08000000} if os.name == 'nt' else {}
            self.process = await asyncio.create_subprocess_exec(sys.executable, '-X', 'utf8', '-m',
                'voice.audio_worker', cwd=str(BASE_DIR), stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, **options)
        process = self.process
        process.stdin.write((json.dumps({'kind': kind, 'timeout': timeout}) + '\n').encode())
        await process.stdin.drain()
        read = None
        completed = False
        try:
            deadline = time.monotonic() + timeout + 180
            while time.monotonic() < deadline:
                if should_stop and should_stop():
                    return False if kind == 'wake' else ''
                if read is None:
                    read = asyncio.create_task(process.stdout.readline())
                done, _ = await asyncio.wait({read}, timeout=.2)
                if not done:
                    continue
                line = read.result()
                read = None
                if not line:
                    raise RuntimeError('El proceso de audio se cerró inesperadamente')
                event = json.loads(line)
                if event['type'] == 'level':
                    AUDIO_LEVEL.update(event['level'])
                elif event['type'] == 'error':
                    raise RuntimeError(event['message'])
                elif event['type'] == 'result':
                    completed = True
                    AUDIO_LEVEL['ready'] = False
                    return event['value']
            raise TimeoutError('El proceso de audio no respondió a tiempo')
        finally:
            if read is not None:
                read.cancel()
                await asyncio.gather(read, return_exceptions=True)
            if not completed:
                self.stop()
                await process.wait()
            AUDIO_LEVEL['ready'] = False

    def stop(self):
        if self.process is not None and self.process.returncode is None:
            self.process.kill()

    async def close(self):
        process = self.process
        if process is not None:
            self.stop()
            await process.communicate()
            self.process = None


audio_service = AudioService()
