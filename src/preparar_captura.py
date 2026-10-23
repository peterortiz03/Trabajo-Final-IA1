"""Prepara UNA consulta sintética en memoria reutilizando el generador vigente.

No conoce identidades, no consulta el reconocedor y no escribe datasets.
Guardar es una operación explícita que conserva PNG y procedencia juntos.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import secrets
import shutil
import tempfile

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
ETIQUETAS = {
    'local_leve': 'Deformación leve',
    'local_moderada': 'Deformación moderada',
    'movimiento': 'Movimiento',
    'contraste_y_calidad': 'Contraste y calidad',
    'contacto_parcial': 'Contacto parcial',
}


def leer_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def sha_codigo(p):
    return hashlib.sha256(Path(p).read_text(encoding='utf-8-sig').encode()).hexdigest()


def huella_pixeles(imagen):
    a = np.asarray(imagen)
    return hashlib.sha256(a.tobytes()).hexdigest()


def validar_semilla(valor):
    texto = str(valor).strip()
    if not texto.isascii() or not texto.isdecimal() or not 0 <= int(texto) <= 2**32-1:
        raise ValueError('Semilla de captura: usá un entero entre 0 y 4294967295.')
    return int(texto)


def elegir_parametros_aleatorios(preparador, semilla_anterior=None):
    """Elige antes de generar, sin mirar la base ni el resultado del reconocedor.

    Sortea uniformemente uno de los perfiles existentes y una semilla de 32 bits.
    La nueva semilla difiere de la anterior, si se proporciona. La receta guarda
    ambos valores para reproducir la captura sin depender de este sorteo.
    """
    perfiles = [p['nombre'] for p in preparador['generador']['perfiles']]
    if not perfiles:
        raise ValueError('No hay perfiles de captura disponibles.')
    perfil = secrets.choice(perfiles)
    if semilla_anterior is None:
        semilla = secrets.randbelow(2**32)
    else:
        anterior = validar_semilla(semilla_anterior)
        semilla = secrets.randbelow(2**32-1)
        if semilla >= anterior:
            semilla += 1
    return perfil, semilla


def cargar_preparador(ruta=RAIZ/'config/preparar_captura_v1.json', raiz=RAIZ):
    ruta, raiz = Path(ruta), Path(raiz)
    cfg = leer_json(ruta)
    if cfg['version'] != 'preparar_captura_v1':
        raise ValueError('Versión de preparador desconocida.')
    generador = leer_json(raiz/cfg['config_generador'])
    perfiles = generador['perfiles']
    nombres = [p['nombre'] for p in perfiles]
    if len(set(nombres)) != len(nombres) or cfg['perfil_inicial'] not in nombres:
        raise ValueError('Perfiles duplicados o perfil inicial ausente.')
    validar_semilla(cfg['semilla_inicial'])
    for s in cfg['semillas_verificacion']:
        validar_semilla(s)
    # Solo configuración de captura. Las etiquetas y bases del dataset no pasan
    # al preparador ni intervienen en la generación de una consulta del usuario.
    return dict(config=cfg, generador=dict(version=generador['version'], perfiles=perfiles,
                preprocesamiento=generador['preprocesamiento']),
                codigo={n: sha_codigo(raiz/'src'/n) for n in
                        ('preparar_captura.py', 'generar_conjunto.py', 'piloto_deformaciones.py')},
                dependencias={n:importlib.metadata.version(n) for n in ('numpy','scipy','Pillow')})


def abrir_base(ruta):
    with Image.open(ruta) as im:
        im.load()
        if im.mode != 'L' or im.size != (275,400):
            raise ValueError('Seleccioná una base de Anguli en gris de 8 bits, 275 × 400 píxeles. No se reescala automáticamente.')
        return im.copy()


def preparar_captura(base, perfil, semilla, preparador):
    """Misma función producir() del dataset; devuelve captura SIN normalizar."""
    from generar_conjunto import producir
    if not isinstance(base, Image.Image) or base.mode != 'L' or base.size != (275,400):
        raise ValueError('La base debe ser una imagen gris L de 275 × 400 píxeles.')
    semilla = validar_semilla(semilla)
    cfg = preparador['generador']
    opciones = {p['nombre']:p for p in cfg['perfiles']}
    if perfil not in opciones:
        raise ValueError('Perfil de captura desconocido.')
    # producir calcula también la representación preliminar heredada. Se descarta:
    # la consulta usa su salida ORIGINAL, que se normalizará al reconocer.
    original, _, parametros = producir(np.array(base), dict(perfil=opciones[perfil],semilla=semilla),cfg)
    imagen = Image.fromarray(original)
    receta = dict(version='consulta_sintetica_v1', perfil=perfil, semilla_captura=semilla,
        base=dict(modo=base.mode,tamano=list(base.size),sha256_pixeles=huella_pixeles(base)),
        captura=dict(modo=imagen.mode,tamano=list(imagen.size),sha256_pixeles=huella_pixeles(imagen)),
        parametros=parametros, configuracion_generador=cfg, codigo=preparador['codigo'],
        dependencias=preparador['dependencias'], python=platform.python_version(),
        normalizada=False, incorporada_entrenamiento=False,
        nota='Consulta sintética. No contiene etiqueta verdadera ni resultado de reconocimiento.')
    return imagen, receta


def guardar_consulta(imagen, base, receta, destino, raiz=RAIZ):
    """Crea una carpeta nueva con ambas imágenes y receta, sin sobrescribir.

    Usa un directorio temporal hermano y rename al finalizar. No contiene resultados
    ni etiquetas del reconocedor. El usuario elige explícitamente este guardado.
    """
    destino, raiz = Path(destino).resolve(), Path(raiz).resolve()
    if not destino.name or destino.exists():
        raise ValueError('Elegí un nombre de carpeta nuevo; no se sobrescriben consultas.')
    for protegida in ('datos', 'config', 'src', 'tests', 'notebooks', 'documentos'):
        if destino.is_relative_to(raiz/protegida):
            raise ValueError('Guardá en consultas/ o en una carpeta externa; no dentro de los datos o archivos del proyecto.')
    if huella_pixeles(imagen) != receta['captura']['sha256_pixeles'] or huella_pixeles(base) != receta['base']['sha256_pixeles']:
        raise ValueError('La captura/base no coincide con su receta. Generá nuevamente antes de guardar.')
    destino.parent.mkdir(parents=True,exist_ok=True)
    temporal = Path(tempfile.mkdtemp(prefix='.consulta_',dir=destino.parent))
    try:
        imagen.save(temporal/'captura.png')
        base.save(temporal/'base.png')
        r = dict(receta, archivos={n:hashlib.sha256((temporal/n).read_bytes()).hexdigest()
                                  for n in ('captura.png','base.png')})
        (temporal/'receta.json').write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        temporal.rename(destino)
    finally:
        if temporal.exists():
            shutil.rmtree(temporal)
    return destino
