"""Procesamiento incremental versionado de los originales de audio.

Comparte el bloqueo con el grabador. Reiniciar el mismo comando permite completar
una tanda interrumpida: cada resultado se confirma como una carpeta completa.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import wave

import numpy as np
import scipy

from audio_archivos import RAIZ, Catalogo, ahora, bloqueo, hash_archivo, json_atomico
import preprocesamiento_audio as pp


def canonico(objeto):
    return (json.dumps(objeto, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode('utf-8')


def csv_atomico(ruta, filas, campos):
    temporal = ruta.with_suffix('.csv.tmp')
    with temporal.open('w', encoding='utf-8', newline='') as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(filas)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporal, ruta)


def firma_procedimiento(cfg):
    # Normalizar CRLF a LF para que Git/Windows no altere la referencia del código.
    codigo = Path(pp.__file__).read_text(encoding='utf-8').replace('\r\n', '\n')
    datos = dict(configuracion=cfg, algoritmo=pp.VERSION_ALGORITMO,
                 sha256_codigo=hashlib.sha256(codigo.encode('utf-8')).hexdigest(),
                 numpy=np.__version__, scipy=scipy.__version__,
                 sha256_ejecutor=hashlib.sha256(Path(__file__).read_text(encoding='utf-8').replace('\r\n', '\n').encode('utf-8')).hexdigest())
    return hashlib.sha256(canonico(datos)).hexdigest(), datos


def guardar_resultado(carpeta, fila, audio, detalle, firma, raiz):
    temporal = carpeta.with_name('.'+carpeta.name+'.tmp')
    if temporal.exists():
        print('Reconstruyendo resultado temporal interrumpido:', carpeta.name)
        shutil.rmtree(temporal)
    temporal.mkdir()
    resultado = dict(muestra_id=fila['muestra_id'], sha256_original=fila['sha256_original'],
                     firma_procedimiento=firma, fecha_utc=ahora(),
                     python=platform.python_version(), plataforma=platform.system(),
                     ruta_procesada='', sha256_procesado='', detalle=detalle)
    if audio is not None:
        # La ganancia ya limita el pico a 0.8; la conversión no usa clipping reparador.
        if np.max(np.abs(audio)) >= 1:
            raise ValueError('Error interno: salida fuera del rango PCM16.')
        pcm = np.rint(audio * 32768).astype('<i2')
        ruta = temporal / 'audio.wav'
        with ruta.open('wb') as f:
            with wave.open(f, 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(detalle['frecuencia_procesada_hz'])
                w.writeframes(pcm.tobytes())
            f.flush()
            os.fsync(f.fileno())
        resultado['ruta_procesada'] = (carpeta/'audio.wav').relative_to(raiz).as_posix()
        resultado['sha256_procesado'] = hash_archivo(ruta)
    json_atomico(temporal/'resultado.json', resultado)
    if carpeta.exists():
        raise FileExistsError(f'No se reemplazará un resultado existente: {carpeta}')
    os.rename(temporal, carpeta)
    return resultado


def comprobar_resultado(carpeta, fila, firma, cat):
    p = carpeta/'resultado.json'
    if not p.exists():
        raise RuntimeError(f'Resultado incompleto en {carpeta}. Conservar y revisar.')
    r = json.loads(p.read_text(encoding='utf-8'))
    if (r['muestra_id'], r['sha256_original'], r['firma_procedimiento']) != (fila['muestra_id'], fila['sha256_original'], firma):
        raise RuntimeError(f'Resultado inconsistente: {fila["muestra_id"]}. No se sobrescribe.')
    if r['ruta_procesada']:
        ruta = cat.ruta(r['ruta_procesada'])
        if ruta != (carpeta/'audio.wav').resolve() or not ruta.exists() or hash_archivo(ruta) != r['sha256_procesado']:
            raise RuntimeError(f'Procesado ausente o modificado: {fila["muestra_id"]}. Conservar y revisar.')
        d = r['detalle']
        with wave.open(str(ruta), 'rb') as w:
            if (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) != (1, 2, 16000, d['cuadros_procesados']):
                raise RuntimeError(f'Formato de procesado inconsistente: {ruta}')
    elif r['detalle']['estado'] not in ('sin_salida_revisar', 'error'):
        raise RuntimeError(f'Resultado sin ruta ni motivo: {fila["muestra_id"]}')
    return r


def ejecutar(raiz, cfg, revisiones=None):
    pp.validar_config(cfg)
    revisiones = revisiones or {}
    if not isinstance(revisiones, dict):
        raise ValueError('Las revisiones deben ser un objeto indexado por muestra_id.')
    for clave, valor in revisiones.items():
        if not isinstance(valor, dict) or valor.get('decision') not in ('conservar', 'excluir', 'pendiente') or not valor.get('motivo'):
            raise ValueError(f'Revisión inválida: {clave}. Usar decision y motivo.')
    raiz = Path(raiz).resolve()
    if not (raiz/'datos/audio/metadatos.csv').exists():
        raise FileNotFoundError('No hay metadatos de captura en esta raíz. Grabar primero.')
    cat = Catalogo(raiz)
    with bloqueo(cat.base):
        if cat.recuperar():
            print('Se recuperó un guardado de captura pendiente.')
        filas = cat.verificar()
        if not filas:
            print('No hay muestras para procesar.')
            return dict(nuevos=0, omitidos=0, total=0)
        for fila in filas:
            if not re.fullmatch(r'H\d+_S\d+_(reconocer|identificar|salir)_\d+', fila['muestra_id']):
                raise ValueError('Identificador de muestra no válido: '+fila['muestra_id'])
        firma, manifiesto = firma_procedimiento(cfg)
        version = cfg['version']+'_'+firma[:12]
        destino = cat.base/'procesados'/version
        print('Procedimiento seleccionado:', version)
        if not destino.exists():
            print('Se creará una versión nueva; las anteriores se conservan.')
        destino.mkdir(parents=True, exist_ok=True)
        ruta_manifiesto = destino/'procedimiento.json'
        manifiesto['firma_procedimiento'] = firma
        if ruta_manifiesto.exists():
            if json.loads(ruta_manifiesto.read_text(encoding='utf-8')) != manifiesto:
                raise RuntimeError('La configuración guardada fue modificada. No se sobrescribe.')
        else:
            json_atomico(ruta_manifiesto, manifiesto)
        carpeta_muestras = destino/'muestras'
        carpeta_muestras.mkdir(exist_ok=True)
        resultados = []
        nuevos = omitidos = 0
        for fila in filas:
            carpeta = carpeta_muestras/fila['muestra_id']
            if carpeta.exists():
                r = comprobar_resultado(carpeta, fila, firma, cat)
                omitidos += 1
            else:
                try:
                    audio, fs = pp.leer_wav_pcm16(cat.ruta(fila['ruta_original']))
                    salida, detalle = pp.preprocesar_audio(audio, fs, cfg)
                except (ValueError, wave.Error) as e:
                    salida, detalle = None, dict(estado='error', avisos=['error_preprocesamiento'], motivo=str(e))
                r = guardar_resultado(carpeta, fila, salida, detalle, firma, raiz)
                nuevos += 1
                print(f"{fila['muestra_id']}: {detalle['estado']} | {', '.join(detalle['avisos']) or 'sin avisos'}")
            resultados.append(r)
        catalogo = []
        for fila, r in zip(filas, resultados):
            detalle = r['detalle']
            revision = revisiones.get(fila['muestra_id'], {})
            # Conserva avisos, formato y configuración ORIGINALES. Solo cambia
            # la referencia activa de procesamiento, nunca particiones o etiquetas.
            fila['ruta_procesada'] = r['ruta_procesada']
            fila['estado_procesamiento'] = detalle['estado']
            registro = dict(fila)
            registro.update(version_procesamiento=version, firma_procedimiento=firma,
                            sha256_procesado=r['sha256_procesado'],
                            avisos_preprocesamiento=';'.join(detalle.get('avisos', [])),
                            decision_revision=revision.get('decision', 'pendiente'),
                            motivo_revision=revision.get('motivo', ''),
                            ruta_detalle=(carpeta_muestras/fila['muestra_id']/'resultado.json').relative_to(raiz).as_posix())
            for clave in ('frecuencia_procesada_hz', 'canales_procesados', 'duracion_procesada_s',
                          'recorte_inicio_s', 'recorte_fin_s', 'actividad_estimada_s',
                          'ganancia_db', 'pico_procesado', 'piso_energia_dbfs',
                          'umbral_fuerte_dbfs', 'umbral_debil_dbfs'):
                registro[clave] = detalle.get(clave, '')
            catalogo.append(registro)
        ids = {f['muestra_id'] for f in filas}
        desconocidas = sorted(set(revisiones)-ids)
        estados = dict(Counter(r['detalle']['estado'] for r in resultados))
        avisos = dict(Counter(a for r in resultados for a in r['detalle'].get('avisos', [])))
        resumen = dict(version=version, firma_procedimiento=firma, total=len(filas),
                       nuevos=nuevos, omitidos=omitidos, estados=estados, avisos=avisos,
                       revisiones_sin_muestra=desconocidas, actualizado_utc=ahora())
        csv_atomico(destino/'catalogo_procesado.csv', catalogo, list(catalogo[0]))
        json_atomico(destino/'revisiones_aplicadas.json', revisiones)
        json_atomico(destino/'resumen.json', resumen)
        cat.escribir(filas)
        json_atomico(cat.base/'procesados/actual.json', dict(
            version=version, ruta_catalogo=(destino/'catalogo_procesado.csv').relative_to(raiz).as_posix(),
            ruta_resumen=(destino/'resumen.json').relative_to(raiz).as_posix()))
        print('\nVersión:', version)
        print(f'Total: {len(filas)} | Nuevos: {nuevos} | Omitidos ya verificados: {omitidos}')
        print('Estados:', estados)
        print('Avisos:', avisos)
        if desconocidas:
            print('Revisiones sin muestra en este catálogo:', ', '.join(desconocidas))
        print('Originales conservados. Procesado no significa validado para entrenamiento.')
        return resumen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config/preprocesamiento_audio_v1.json')
    parser.add_argument('--revisiones', default='config/revisiones_audio_v1.json')
    parser.add_argument('--raiz', type=Path, default=RAIZ, help='Raíz del proyecto; normalmente no se modifica')
    args = parser.parse_args()
    try:
        def resolver(ruta):
            p = Path(ruta)
            return p if p.is_absolute() else RAIZ/p
        cfg = json.loads(resolver(args.config).read_text(encoding='utf-8-sig'))
        p = resolver(args.revisiones)
        revisiones = json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {}
        ejecutar(args.raiz, cfg, revisiones)
    except KeyboardInterrupt:
        print('\nInterrumpido. Repetí el mismo comando para completar y consolidar los resultados.')
        return 130
    except (OSError, ValueError, RuntimeError, KeyError, wave.Error) as e:
        print(f'No se puede continuar: {e}', file=sys.stderr)
        print('No borres originales. Cerrá el grabador y conservá los archivos para revisar.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
