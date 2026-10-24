"""Verifica el lote experimental y extrae desarrollo con el modelo congelado.

No entrena, no cambia configuraciones ni evalúa las impresiones de control 26–30.
Estas últimas solo se leen para comprobar formato, integridad y duplicados.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image

from interfaz_servicios import RAIZ, cargar_huellas, leer_json
from normalizacion_final import normalizar_huella
from caracteristicas_huellas import extraer_huella, nombres_caracteristicas
from calibrar_rechazo_huellas import decidir_acceso

EXPERIMENTO = RAIZ/'experimentos/anguli_impresiones_v1'


def particion(identidad, numero):
    if numero >= 26:
        return 'control_apartado'
    if identidad.startswith('A') and numero <= 20:
        return 'ajuste_experimental'
    return 'validacion_experimental'


def sha_archivo(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def leer_imagen(ruta):
    with Image.open(ruta) as im:
        im.load()
        if im.mode != 'L' or im.size != (275, 400):
            raise ValueError(f'{ruta}: se esperaba gris L de 275 x 400 píxeles.')
        return im.copy()


def sha_pixeles(imagen):
    return hashlib.sha256(np.asarray(imagen).tobytes()).hexdigest()


def escribir_csv(ruta, filas):
    with ruta.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)


def verificar_lote(originales):
    """Comprueba las cinco identidades conocidas antes de producir salidas."""
    cfg = leer_json(RAIZ/'config/conjunto_v1.json')
    identidades = [i for i in cfg['identidades']
                   if i['grupo'] == 'autorizado' or i['particion'] == 'validacion']
    esperadas = {}
    for i in identidades:
        tipo = 'autorizada' if i['grupo'] == 'autorizado' else 'intrusa_desarrollo'
        nombre = f"{i['id']}_{tipo}_semilla{i['semilla_base']}"
        esperadas[nombre] = i
    presentes = {p.name for p in originales.iterdir() if p.is_dir()}
    if presentes != set(esperadas):
        raise ValueError(f'Carpetas diferentes del plan. Faltan: {set(esperadas)-presentes}; '
                         f'sobran: {presentes-set(esperadas)}. Revisar --originales.')
    filas, bases, hashes = [], [], {}
    for carpeta, ident in esperadas.items():
        d = originales/carpeta
        conf = ET.parse(d/'Anguli.conf').getroot().find('FingerprintGen')
        if conf is None:
            raise ValueError(f'{carpeta}: falta FingerprintGen en Anguli.conf.')
        campos = {'Translation': {'value':'0'}, 'Rotation': {'value':'0'},
                  'NumScratches': {'low':'0','high':'0'}, 'NoiseLevel': {'low':'0','high':'0'},
                  'customSeed': {'value':'1','seedValue':str(ident['semilla_base'])},
                  'NumThreads': {'value':'1'}, 'ClassDistr': {'value':'0'},
                  'NumFingerprints': {'value':'1'}, 'ImprPerFinger': {'value':'30'},
                  'StartFinger': {'value':'1'}, 'SaveMetaInfo': {'value':'1'}}
        for nombre, atributos in campos.items():
            elemento = conf.find(nombre)
            if elemento is None or any(elemento.get(k) != v for k,v in atributos.items()):
                raise ValueError(f'{carpeta}: configuración inesperada en {nombre}. No regenerar a ciegas.')
        base = leer_imagen(d/'Fingerprints/fp_1/1.png')
        anterior = leer_imagen(RAIZ/ident['base'])
        if not np.array_equal(np.asarray(base), np.asarray(anterior)):
            raise ValueError(f'{carpeta}: la base regenerada no coincide con la original.')
        bases.append(dict(identidad=ident['id'], coincide=True,
                          sha256_pixeles=sha_pixeles(base), sha256_config=sha_archivo(d/'Anguli.conf')))
        nombres = {f'Impression_{j}' for j in range(1,31)}
        if {p.name for p in d.glob('Impression_*')} != nombres:
            raise ValueError(f'{carpeta}: se esperan Impression_1 hasta Impression_30.')
        png = set(d.glob('Impression_*/**/*.png'))
        if png != {d/f'Impression_{j}/fp_1/1.png' for j in range(1,31)}:
            raise ValueError(f'{carpeta}: cantidad o ubicación inesperada de imágenes.')
        for j in range(1,31):
            ruta = d/f'Impression_{j}/fp_1/1.png'
            h = sha_pixeles(leer_imagen(ruta))
            if h in hashes:
                raise ValueError(f'Duplicado exacto: {ruta} y {hashes[h]}. Revisar antes de separar datos.')
            hashes[h] = str(ruta)
            filas.append(dict(identidad_real=ident['id'], grupo_real=ident['grupo'],
                              impresion=j, particion=particion(ident['id'],j),
                              archivo=ruta.relative_to(originales).as_posix(),
                              sha256_pixeles=h, sha256_archivo=sha_archivo(ruta)))
    return filas, bases


def ejecutar(originales=EXPERIMENTO/'originales', salida=None):
    originales = Path(originales).resolve()
    if not originales.is_dir():
        raise ValueError(f'No existe {originales}. Revisar dónde se extrajo originales del ZIP.')
    filas, bases = verificar_lote(originales)
    s = cargar_huellas(leer_json(RAIZ/'config/aplicacion_respaldo.json')['huellas'])
    modelo_dir = RAIZ/s['carpeta']
    def hashes_modelo():
        return {p.name:sha_archivo(p) for p in sorted(modelo_dir.iterdir()) if p.is_file()}
    antes = hashes_modelo()
    fecha = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    salida = Path(salida).resolve() if salida else EXPERIMENTO/'diagnosticos'/fecha
    if salida == originales or originales in salida.parents:
        raise ValueError('La salida no puede estar dentro de originales.')
    if salida.exists():
        raise ValueError(f'La carpeta de salida ya existe: {salida}. Usar una carpeta nueva.')
    # No se producen vectores, imágenes normalizadas o decisiones del control.
    nombres = nombres_caracteristicas(s['cfg_ext'])
    consultas, vectores, ids_filas = [], [], []
    for indice, fila in enumerate(filas):
        if fila['particion'] == 'control_apartado':
            continue
        registro = dict(fila)
        try:
            im = leer_imagen(originales/fila['archivo'])
            if sha_pixeles(im) != fila['sha256_pixeles']:
                raise ValueError('La entrada cambió después de verificar el lote.')
            normal, info = normalizar_huella(im, s['cfg_norm'])
            vector, detalle = extraer_huella(normal, info['mascara_normalizada'], s['cfg_ext'])
            decision = decidir_acceso(vector, nombres, s['modelo'], s['umbral'])[0]
            registro.update(distancia=decision['distancia'], aceptada=decision['aceptada'],
                identidad_predicha=decision['identidad'],
                avisos=' | '.join(info['avisos']+detalle['avisos']), error='')
            vectores.append(vector)
            ids_filas.append(indice)
        except Exception as e:
            registro.update(distancia='', aceptada='', identidad_predicha='', avisos='',
                            error=f'{type(e).__name__}: {e}')
        consultas.append(registro)
    if antes != hashes_modelo():
        raise RuntimeError('Cambió un archivo del modelo durante el diagnóstico.')
    resumen = dict(fecha_utc=fecha, python=platform.python_version(),
        dependencias={n:importlib.metadata.version(n)
                      for n in ('numpy','scipy','Pillow')},
        modelo=s['identificador'], umbral=s['umbral'], modelo_sha256=antes,
        codigo_script_sha256=sha_archivo(__file__), bases=bases,
        impresiones_verificadas=len(filas), duplicados_exactos=0,
        consultas_evaluadas=len(consultas), controles_sin_inferencia=25,
        modelo_modificado=False, entrenamiento_ejecutado=False,
        prueba_final_utilizada=False, resultados=[])
    for ident in dict.fromkeys(f['identidad_real'] for f in filas):
        rs=[q for q in consultas if q['identidad_real']==ident]
        validas=[q for q in rs if not q['error']]
        ds=[q['distancia'] for q in validas]
        resumen['resultados'].append(dict(identidad=ident, evaluadas=len(rs),
            errores=len(rs)-len(validas), con_avisos=sum(bool(q['avisos']) for q in validas),
            aceptadas=sum(q['aceptada'] for q in validas),
            identificadas_correctamente=sum(q['aceptada'] and q['identidad_predicha']==ident for q in validas),
            distancia_min=min(ds) if ds else None, distancia_max=max(ds) if ds else None))
    salida.mkdir(parents=True,exist_ok=False)
    escribir_csv(salida/'manifiesto.csv',filas)
    escribir_csv(salida/'consultas_modelo_actual.csv',consultas)
    # indices_manifiesto relaciona cada vector con una fila del CSV, base cero.
    np.savez_compressed(salida/'caracteristicas_desarrollo.npz',
        X=np.asarray(vectores,dtype=float).reshape(-1,len(nombres)),
        nombres=np.asarray(nombres), indices_manifiesto=np.asarray(ids_filas,dtype=int))
    (salida/'resumen.json').write_text(json.dumps(resumen,ensure_ascii=False,indent=2),encoding='utf-8')
    for r in resumen['resultados']:
        print(f"{r['identidad']}: {r['evaluadas']} evaluadas; {r['aceptadas']} aceptadas; {r['errores']} errores")
    print('150 impresiones verificadas; 5 bases idénticas; 0 duplicados exactos.')
    print('125 consultas de desarrollo; 25 controles sin inferencia. Modelo sin modificar.')
    print('Salida:',salida)
    return salida


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--originales',type=Path,default=EXPERIMENTO/'originales')
    p.add_argument('--salida',type=Path,help='Carpeta NUEVA para resultados; por defecto corrida fechada.')
    args=p.parse_args()
    try:
        ejecutar(args.originales,args.salida)
    except (OSError,ValueError,ET.ParseError) as e:
        p.exit(1,f'No se completó el diagnóstico: {e}\nNo ejecutar entrenamiento para resolver este error.\n')
