"""Descarga únicamente el modelo español oficial de activación local."""
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / '.cache/vosk'
NAME = 'vosk-model-small-es-0.42'
URL = f'https://alphacephei.com/vosk/models/{NAME}.zip'


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    if (TARGET / NAME / 'am/final.mdl').is_file():
        print('Modelo Vosk español ya preparado.')
        return
    archive = TARGET / (NAME + '.zip')
    urllib.request.urlretrieve(URL, archive)
    with zipfile.ZipFile(archive) as source:
        for item in source.infolist():
            if not (TARGET / item.filename).resolve().is_relative_to(TARGET.resolve()):
                raise ValueError('El archivo contiene una ruta externa al destino')
        source.extractall(TARGET)
    print('Modelo preparado:', TARGET / NAME)


if __name__ == '__main__':
    main()
