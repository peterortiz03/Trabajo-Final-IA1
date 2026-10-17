"""Persistencia local de captura v1. No modifica los datos de huellas."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import json
import os
import re
import wave

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
CAMPOS = (
    'muestra_id hablante sesion comando ruta_original ruta_procesada '
    'frecuencia_hz canales duracion_s cuadros estado_procesamiento '
    'avisos_calidad rms_dbfs pico fraccion_saturada configuracion_ref '
    'particion fecha_utc dispositivo api_audio sha256_original'
).split()
COMANDOS = ('reconocer', 'identificar', 'salir')


def ahora():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def hash_archivo(ruta):
    with Path(ruta).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def json_atomico(ruta, objeto):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + '.tmp')
    with temporal.open('w', encoding='utf-8') as f:
        json.dump(objeto, f, ensure_ascii=False, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporal, ruta)


@contextmanager
def bloqueo(base):
    """El SO libera el bloqueo incluso al terminar abruptamente el proceso."""
    base.mkdir(parents=True, exist_ok=True)
    with (base / '.captura.lock').open('a+b') as f:
        f.seek(0, 2)
        if f.tell() == 0:
            f.write(b'0')
            f.flush()
        f.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            raise RuntimeError('Ya hay otro grabador abierto. Cerralo primero.') from e
        try:
            yield
        finally:
            f.seek(0)
            if os.name == 'nt':
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def calidad_inicial(audio, cfg):
    """Indicadores de amplitud; NO son un detector de voz ni de palabras."""
    if audio.dtype != np.int16 or audio.ndim != 2 or len(audio) == 0:
        raise ValueError('La captura debe contener cuadros PCM16 y canales.')
    x = audio.astype(np.float64) / 32768.0
    pico = float(np.max(np.abs(x)))
    # Máximo entre canales: evita ocultar saturación o cancelaciones estéreo.
    rms = float(np.max(np.sqrt(np.mean(x*x, axis=0))))
    dbfs = 20 * np.log10(max(rms, 1e-12))
    fraccion = float(np.max(np.mean(np.abs(x) >= cfg['pico_saturacion'], axis=0)))
    avisos = []
    if pico == 0:
        avisos.append('captura_nula')
    elif dbfs < cfg['rms_bajo_dbfs']:
        avisos.append('nivel_bajo_o_silencio')
    if pico >= cfg['pico_saturacion']:
        avisos.append('picos_cercanos_al_limite')
    if fraccion >= cfg['fraccion_saturada_aviso']:
        avisos.append('posible_saturacion')
    return dict(avisos_calidad=';'.join(avisos), rms_dbfs=f'{dbfs:.2f}',
                pico=f'{pico:.6f}', fraccion_saturada=f'{fraccion:.6f}')


class Catalogo:
    def __init__(self, raiz=RAIZ):
        self.raiz = Path(raiz)
        self.base = self.raiz / 'datos/audio'
        self.originales = self.base / 'originales'
        self.csv = self.base / 'metadatos.csv'
        self.pendiente = self.base / '.pendiente.json'
        self.temporal = self.base / '.toma.wav.tmp'
        self.originales.mkdir(parents=True, exist_ok=True)

    def leer(self):
        if not self.csv.exists():
            return []
        with self.csv.open(encoding='utf-8-sig', newline='') as f:
            lector = csv.DictReader(f)
            if lector.fieldnames != CAMPOS:
                raise ValueError('Encabezado de metadatos inesperado. No se modificó el CSV.')
            filas = list(lector)
        if any(None in r or any(v is None for v in r.values()) for r in filas):
            raise ValueError('CSV incompleto: revisar antes de seguir.')
        ids = [r['muestra_id'] for r in filas]
        if len(ids) != len(set(ids)):
            raise ValueError('Hay identificadores duplicados en el CSV.')
        return filas

    def escribir(self, filas):
        temporal = self.csv.with_suffix('.csv.tmp')
        with temporal.open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS)
            w.writeheader()
            w.writerows(filas)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporal, self.csv)

    def ruta(self, relativa):
        p = (self.raiz / relativa).resolve()
        if not p.is_relative_to(self.base.resolve()):
            raise ValueError('La ruta del catálogo debe estar dentro de datos/audio.')
        return p

    def validar_wav(self, ruta, fila):
        with wave.open(str(ruta), 'rb') as w:
            esperado = (int(fila['canales']), 2, int(fila['frecuencia_hz']), int(fila['cuadros']))
            real = (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes())
            if real != esperado or w.getcomptype() != 'NONE':
                raise ValueError(f'Formato o duración inconsistente: {ruta.name}')
            contenido = w.readframes(w.getnframes())
            if len(contenido) != esperado[0] * 2 * esperado[3]:
                raise ValueError(f'WAV truncado: {ruta.name}')
        if hash_archivo(ruta) != fila['sha256_original']:
            raise ValueError(f'El original cambió o quedó incompleto: {ruta.name}')

    def recuperar(self):
        """Finaliza un guardado confirmado interrumpido, sin repetir filas."""
        if not self.pendiente.exists():
            return False
        fila = json.loads(self.pendiente.read_text(encoding='utf-8'))
        destino = self.ruta(fila['ruta_original'])
        fuente = destino if destino.exists() else self.temporal
        if not fuente.exists():
            raise RuntimeError('Hay un guardado pendiente sin WAV. Conservar archivos y revisar.')
        self.validar_wav(fuente, fila)
        filas = self.leer()
        existentes = [r for r in filas if r['muestra_id'] == fila['muestra_id']]
        if existentes and existentes != [fila]:
            raise RuntimeError('El guardado pendiente no coincide con el CSV. Revisar.')
        if not destino.exists():
            # No se reemplaza un original existente; bloqueo obligatorio en el llamador.
            os.link(self.temporal, destino)
        # También retirar el enlace temporal si el corte ocurrió después de os.link.
        self.temporal.unlink(missing_ok=True)
        if not existentes:
            self.escribir(filas + [fila])
        self.pendiente.unlink()
        return True

    def verificar(self):
        filas = self.leer()
        conocidas = set()
        for fila in filas:
            p = self.ruta(fila['ruta_original'])
            if p in conocidas:
                raise ValueError('Dos filas apuntan al mismo original.')
            conocidas.add(p)
            self.validar_wav(p, fila)
            config = self.ruta(fila['configuracion_ref'])
            if hash_archivo(config) != config.stem:
                raise ValueError(f'Configuración alterada: {config.name}')
        huerfanos = set(p.resolve() for p in self.originales.rglob('*.wav')) - conocidas
        if huerfanos:
            nombres = ', '.join(p.name for p in sorted(huerfanos))
            raise RuntimeError(f'WAV sin metadatos: {nombres}. Se conservan; revisar antes de continuar.')
        return filas

    def guardar(self, audio, fs, hablante, sesion, comando, config, dispositivo, api):
        """Debe llamarse bajo bloqueo. El contador avanza solo al guardar."""
        if not re.fullmatch(r'H\d+', hablante) or not re.fullmatch(r'S\d+', sesion):
            raise ValueError('Identificadores de persona o sesión inválidos.')
        if comando not in COMANDOS:
            raise ValueError('Comando desconocido.')
        carpeta = self.originales / hablante / sesion
        if not carpeta.is_dir():
            raise ValueError('Seleccionar primero una persona y una sesión registradas.')
        filas = self.leer()
        prefijo = f'{hablante}_{sesion}_{comando}_'
        usados = [int(r['muestra_id'][len(prefijo):]) for r in filas
                  if r['muestra_id'].startswith(prefijo)]
        usados += [int(p.stem[len(prefijo):]) for p in carpeta.glob(prefijo + '*.wav')]
        numero = max(usados, default=0) + 1
        muestra = f'{prefijo}{numero:04d}'
        destino = carpeta / f'{muestra}.wav'
        if destino.exists() or self.pendiente.exists():
            raise RuntimeError('Existe un archivo o guardado pendiente. Reiniciar y verificar.')
        chequeo = calidad_inicial(audio, config['calidad'])
        contenido = (json.dumps(config, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
        ref = self.base / 'configuraciones' / (hashlib.sha256(contenido).hexdigest() + '.json')
        ref.parent.mkdir(exist_ok=True)
        if not ref.exists():
            with ref.open('xb') as f:
                f.write(contenido)
                f.flush()
                os.fsync(f.fileno())
        if hash_archivo(ref) != ref.stem:
            raise ValueError('La copia de configuración no coincide con su hash.')
        # Hasta este punto no hay ninguna muestra registrada como válida.
        with self.temporal.open('wb') as f:
            with wave.open(f, 'wb') as w:
                w.setnchannels(audio.shape[1])
                w.setsampwidth(2)
                w.setframerate(fs)
                w.writeframes(audio.astype('<i2', copy=False).tobytes())
            f.flush()
            os.fsync(f.fileno())
        fila = dict.fromkeys(CAMPOS, '')
        fila.update(muestra_id=muestra, hablante=hablante, sesion=sesion, comando=comando,
                    ruta_original=destino.relative_to(self.raiz).as_posix(),
                    frecuencia_hz=str(fs), canales=str(audio.shape[1]),
                    duracion_s=f'{len(audio)/fs:.6f}', cuadros=str(len(audio)),
                    estado_procesamiento='pendiente', particion='sin_asignar',
                    configuracion_ref=ref.relative_to(self.raiz).as_posix(),
                    fecha_utc=ahora(), dispositivo=dispositivo, api_audio=api,
                    sha256_original=hash_archivo(self.temporal), **chequeo)
        self.validar_wav(self.temporal, fila)
        json_atomico(self.pendiente, fila)
        self.recuperar()
        return fila


def resumen(cat):
    filas = cat.leer()
    personas = sorted(p.name for p in cat.originales.iterdir() if p.is_dir() and p.name.startswith('H'))
    print('\nHablante    Reconocer  Identificar  Salir  Con avisos')
    for h in personas:
        propias = [r for r in filas if r['hablante'] == h]
        n = [sum(r['comando'] == c for r in propias) for c in COMANDOS]
        avisos = sum(bool(r['avisos_calidad']) for r in propias)
        print(f'{h:<12}{n[0]:<11}{n[1]:<13}{n[2]:<7}{avisos}')
    print(f'Total: {len(filas)} tomas guardadas; todavía no validadas para entrenar.')
    print('Procurar los tres comandos por persona. No hay cupos ni máximos.\n')
