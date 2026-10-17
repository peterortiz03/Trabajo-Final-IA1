"""Preprocesamiento reutilizable, sin clasificación ni parámetros aprendidos.

La detección por energía es una heurística de actividad, no reconocimiento de voz.
Las funciones no modifican originales ni escriben archivos.
"""
import math
from pathlib import Path
import re
import wave

import numpy as np
from scipy.signal import resample_poly

VERSION_ALGORITMO = '1.0.0'


def validar_config(cfg):
    if not isinstance(cfg.get('version'), str) or not re.fullmatch(r'[A-Za-z0-9_-]+', cfg['version']):
        raise ValueError('version debe contener solo letras, números, guiones o guiones bajos.')
    if cfg.get('frecuencia_hz') != 16000:
        raise ValueError('Esta versión de la etapa produce audio a 16000 Hz.')
    if not isinstance(cfg.get('quitar_media'), bool):
        raise ValueError('quitar_media debe ser true o false.')
    for nombre in ('ventana_ms', 'salto_ms', 'hueco_max_ms', 'isla_min_ms',
                   'actividad_min_ms', 'margen_ms', 'borde_aviso_ms'):
        if not isinstance(cfg.get(nombre), (int, float)) or not math.isfinite(cfg[nombre]) or cfg[nombre] <= 0:
            raise ValueError(f'{nombre} debe ser positivo y finito.')
    if cfg['salto_ms'] > cfg['ventana_ms'] or cfg['salto_ms'] < 1:
        raise ValueError('El salto debe estar entre 1 ms y el tamaño de ventana.')
    for nombre in ('umbral_fuerte_min_dbfs', 'umbral_debil_min_dbfs'):
        if not math.isfinite(cfg[nombre]) or cfg[nombre] >= 0:
            raise ValueError(f'{nombre} debe ser negativo y finito.')
    if cfg['umbral_debil_min_dbfs'] > cfg['umbral_fuerte_min_dbfs']:
        raise ValueError('El umbral débil no puede ser mayor que el fuerte.')
    if not 0 < cfg['percentil_ruido'] < 50:
        raise ValueError('percentil_ruido debe estar entre 0 y 50.')
    if not 0 <= cfg['contraste_debil_db'] <= cfg['contraste_fuerte_db'] < 100:
        raise ValueError('Revisar los contrastes fuerte y débil.')
    if not 0 < cfg['pico_objetivo'] < 1 or not 0 <= cfg['ganancia_max_db'] <= 40:
        raise ValueError('Revisar normalización de amplitud.')
    if not 0 < cfg['pico_saturacion'] <= 1 or not 0 < cfg['fraccion_saturada_aviso'] <= 1:
        raise ValueError('Revisar umbrales de saturación.')
    return cfg


def leer_wav_pcm16(ruta):
    """Formato producido por el grabador: WAV PCM16 mono o multicanal."""
    with wave.open(str(Path(ruta)), 'rb') as w:
        if w.getsampwidth() != 2 or w.getcomptype() != 'NONE':
            raise ValueError('Se espera WAV PCM16 sin compresión del grabador.')
        fs, canales, n = w.getframerate(), w.getnchannels(), w.getnframes()
        datos = w.readframes(n)
    if fs <= 0 or canales <= 0 or n == 0 or len(datos) != 2 * n * canales:
        raise ValueError('WAV vacío o truncado.')
    return np.frombuffer(datos, dtype='<i2').reshape(-1, canales).copy(), fs


def a_flotante(audio):
    x = np.asarray(audio)
    if x.ndim == 1:
        x = x[:, None]
    if x.ndim != 2 or x.shape[0] == 0 or x.shape[1] == 0:
        raise ValueError('Se espera audio no vacío: [cuadros] o [cuadros, canales].')
    if x.dtype.kind == 'i' and x.dtype.itemsize == 2:
        x = x.astype(np.float64) / 32768.0
    elif x.dtype.kind == 'f':
        x = x.astype(np.float64, copy=True)
    else:
        raise ValueError('Usar PCM int16 o flotantes con escala [-1, 1].')
    if not np.isfinite(x).all() or np.max(np.abs(x)) > 1:
        raise ValueError('Audio con NaN, infinito o valores fuera de [-1, 1].')
    return x


def db(amplitud):
    return float(20 * np.log10(max(float(amplitud), 1e-12)))


def tramos(mascara):
    """Intervalos [inicio, fin) de valores True."""
    cambios = np.diff(np.r_[False, mascara, False].astype(np.int8))
    return list(zip(np.flatnonzero(cambios == 1), np.flatnonzero(cambios == -1)))


def actividad_por_energia(x, fs, cfg):
    """Dos umbrales: evidencia fuerte y extensión a sonidos más débiles.

    El percentil bajo estima un piso de energía, no una SNR acústica medida.
    Los huecos cortos unen sílabas; no se suprimen silencios internos del recorte.
    """
    ventana = max(1, round(fs * cfg['ventana_ms'] / 1000))
    salto = max(1, round(fs * cfg['salto_ms'] / 1000))
    inicios = np.arange(0, max(1, len(x)-ventana+1), salto)
    ultimo = max(0, len(x)-ventana)
    if inicios[-1] != ultimo:
        inicios = np.r_[inicios, ultimo]
    energia = np.array([np.sqrt(np.mean(x[i:min(i+ventana, len(x))]**2)) for i in inicios])
    niveles = 20*np.log10(np.maximum(energia, 1e-12))
    piso = float(np.percentile(niveles, cfg['percentil_ruido']))
    fuerte = max(cfg['umbral_fuerte_min_dbfs'], piso+cfg['contraste_fuerte_db'])
    debil = max(cfg['umbral_debil_min_dbfs'], piso+cfg['contraste_debil_db'])
    mascara = niveles >= debil
    max_hueco = int(cfg['hueco_max_ms'] / cfg['salto_ms'])
    for a, b in tramos(~mascara):
        if a > 0 and b < len(mascara) and b-a <= max_hueco:
            mascara[a:b] = True
    retenida = np.zeros(len(mascara), dtype=bool)
    for a, b in tramos(mascara):
        duracion_ms = (min(len(x), inicios[b-1]+ventana)-inicios[a])/fs*1000
        if duracion_ms >= cfg['isla_min_ms'] and np.any(niveles[a:b] >= fuerte):
            retenida[a:b] = True
    metricas = dict(piso_energia_dbfs=piso, umbral_fuerte_dbfs=float(fuerte),
                    umbral_debil_dbfs=float(debil))
    indices = np.flatnonzero(retenida)
    if not len(indices):
        return None, metricas
    a = int(inicios[indices[0]])
    b = min(len(x), int(inicios[indices[-1]]+ventana))
    # La duración se suma por islas retenidas, no por toda la distancia entre ellas.
    ms = sum((min(len(x), inicios[j-1]+ventana)-inicios[i])/fs*1000 for i, j in tramos(retenida))
    metricas['actividad_estimada_s'] = float(ms/1000)
    if ms < cfg['actividad_min_ms']:
        return None, metricas
    return (a, b), metricas


def preprocesar_audio(audio, frecuencia_hz, cfg):
    """Devuelve (audio_mono_float_o_None, detalle).

    None significa que no se genera WAV procesado; se conserva el original.
    El llamador decide cómo registrar/mostrar la revisión. Una salida no certifica
    voz ni palabra correcta. Se reutiliza sin cambios en una futura captura.
    """
    validar_config(cfg)
    if not isinstance(frecuencia_hz, (int, np.integer)) or frecuencia_hz <= 0:
        raise ValueError('La frecuencia de entrada debe ser un entero positivo.')
    x = a_flotante(audio)
    fs = int(frecuencia_hz)
    avisos = []
    pico = float(np.max(np.abs(x)))
    fraccion = float(np.max(np.mean(np.abs(x) >= cfg['pico_saturacion'], axis=0)))
    info = dict(estado='pendiente', avisos=avisos, frecuencia_original_hz=fs,
                canales_original=x.shape[1], duracion_original_s=len(x)/fs,
                frecuencia_procesada_hz=cfg['frecuencia_hz'], canales_procesados=1,
                pico_original=pico, fraccion_saturada_original=fraccion,
                rms_original_dbfs=db(np.max(np.sqrt(np.mean(x*x, axis=0)))))
    if pico >= cfg['pico_saturacion']:
        avisos.append('picos_cercanos_al_limite_original')
    if fraccion >= cfg['fraccion_saturada_aviso']:
        avisos.append('posible_saturacion_original')
    mono = np.mean(x, axis=1)
    rms_canales = float(np.max(np.sqrt(np.mean(x*x, axis=0))))
    if x.shape[1] > 1 and rms_canales > 0 and np.sqrt(np.mean(mono*mono)) < rms_canales * .25:
        avisos.append('posible_cancelacion_al_convertir_a_mono')
    if cfg['quitar_media']:
        mono = mono - np.mean(mono)
    if fs != cfg['frecuencia_hz']:
        divisor = math.gcd(fs, cfg['frecuencia_hz'])
        mono = resample_poly(mono, cfg['frecuencia_hz']//divisor, fs//divisor,
                             window=('kaiser', 5.0), padtype='constant')
    fs_salida = cfg['frecuencia_hz']
    limites, medidas = actividad_por_energia(mono, fs_salida, cfg)
    info.update(medidas)
    if limites is None:
        avisos.append('sin_actividad_suficiente_segun_energia')
        info['estado'] = 'sin_salida_revisar'
        return None, info
    a, b = limites
    borde = round(fs_salida*cfg['borde_aviso_ms']/1000)
    if a <= borde:
        avisos.append('actividad_cerca_del_inicio')
    if len(mono)-b <= borde:
        avisos.append('actividad_cerca_del_final')
    margen = round(fs_salida*cfg['margen_ms']/1000)
    inicio, fin = max(0, a-margen), min(len(mono), b+margen)
    recorte = mono[inicio:fin].copy()
    maximo = float(np.max(np.abs(recorte)))
    deseada = cfg['pico_objetivo']/maximo
    limite_ganancia = 10**(cfg['ganancia_max_db']/20)
    ganancia = min(deseada, limite_ganancia)
    if deseada > limite_ganancia:
        avisos.append('amplificacion_limitada')
    salida = recorte * ganancia
    info.update(inicio_actividad_s=a/fs_salida, fin_actividad_s=b/fs_salida,
                recorte_inicio_s=inicio/fs_salida, recorte_fin_s=fin/fs_salida,
                duracion_procesada_s=len(salida)/fs_salida, cuadros_procesados=len(salida),
                ganancia_db=db(ganancia), pico_procesado=float(np.max(np.abs(salida))),
                rms_procesado_dbfs=db(np.sqrt(np.mean(salida*salida))))
    info['estado'] = 'procesado_con_avisos' if avisos else 'procesado'
    return salida, info
