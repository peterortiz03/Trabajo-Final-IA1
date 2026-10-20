# Extracción por muestra, sin aprendizaje ni clasificación.
# Entrada: audio ya procesado y límites de actividad de ese procesamiento.

import json
from pathlib import Path

import numpy as np
from scipy.fft import rfft, dct
from scipy.signal.windows import hann

from preprocesamiento_audio import a_flotante


class AudioNoVectorizable(ValueError):
    pass


def validar_config(c):
    claves = {
        "version", "frecuencia_hz", "segmentos", "ventana_ms",
        "salto_ms", "n_fft", "n_mel", "fmin_hz", "fmax_hz",
        "indices_mfcc", "piso_potencia", "rms_minimo",
    }
    if set(c) != claves:
        raise ValueError("Configuración incompleta o con claves desconocidas.")
    if c["version"] != "audio_segmentos_v1":
        raise ValueError("Versión del extractor incompatible.")
    if c["frecuencia_hz"] != 16000:
        raise ValueError("Esta versión requiere audio procesado a 16 kHz.")

    for k, minimo, maximo in [
        ("segmentos", 1, 100),
        ("n_fft", 64, 8192),
        ("n_mel", 6, 128),
    ]:
        if type(c[k]) is not int or not minimo <= c[k] <= maximo:
            raise ValueError(f"Parámetro inválido: {k}")

    for k in [
        "ventana_ms", "salto_ms", "fmin_hz", "fmax_hz",
        "piso_potencia", "rms_minimo",
    ]:
        if not isinstance(c[k], (int, float)) or not np.isfinite(c[k]):
            raise ValueError(f"Parámetro no finito: {k}")

    if not 1 <= c["salto_ms"] <= c["ventana_ms"] <= 100:
        raise ValueError("Se requiere 1 <= salto_ms <= ventana_ms <= 100.")

    W = round(c["frecuencia_hz"] * c["ventana_ms"] / 1000)
    if c["n_fft"] < W:
        raise ValueError("n_fft no puede truncar la ventana acústica.")

    if not 0 <= c["fmin_hz"] < c["fmax_hz"] <= 8000:
        raise ValueError("Límites de frecuencia incompatibles con Nyquist.")

    if not 0 < c["piso_potencia"] < 1:
        raise ValueError("Piso de potencia inválido.")
    if not 0 < c["rms_minimo"] < 1:
        raise ValueError("RMS mínimo inválido.")

    ks = c["indices_mfcc"]
    if (
        not isinstance(ks, list)
        or not ks
        or any(type(k) is not int or not 0 <= k < c["n_mel"] for k in ks)
        or len(set(ks)) != len(ks)
    ):
        raise ValueError("Índices MFCC inválidos o repetidos.")
    return c


def cargar_config(ruta=None):
    if ruta is None:
        ruta = (
            Path(__file__).resolve().parents[1]
            / "config/caracteristicas_audio_v1.json"
        )
    return validar_config(
        json.loads(Path(ruta).read_text(encoding="utf-8-sig"))
    )


def nombres_caracteristicas(c):
    validar_config(c)
    locales = [
        "zcr_media", "zcr_max",
        "amplitud_abs_media", "amplitud_abs_max",
    ]
    locales += [
        f"mfcc_c{k}_{estadistico}"
        for k in c["indices_mfcc"]
        for estadistico in ("media", "max", "std")
    ]
    return [
        f"s{s + 1:02d}_{nombre}"
        for s in range(c["segmentos"])
        for nombre in locales
    ]


def limites_desde_detalle(detalle, fs, cantidad):
    # Los tiempos guardados se refieren al audio anterior al recorte.
    try:
        inicio = float(detalle["inicio_actividad_s"])
        fin = float(detalle["fin_actividad_s"])
        recorte = float(detalle["recorte_inicio_s"])
    except (KeyError, TypeError, ValueError) as e:
        raise AudioNoVectorizable(
            "Faltan límites de actividad del preprocesamiento."
        ) from e

    if not np.isfinite([inicio, fin, recorte]).all():
        raise AudioNoVectorizable("Tiempos de actividad no finitos.")

    a = round((inicio - recorte) * fs)
    b = round((fin - recorte) * fs)

    # Solo se tolera un sample por redondeo en los extremos.
    if a < -1 or b > cantidad + 1 or b <= a:
        raise AudioNoVectorizable(
            "Límites incompatibles con el WAV procesado."
        )
    a, b = max(a, 0), min(b, cantidad)
    if b <= a:
        raise AudioNoVectorizable("Intervalo de actividad vacío.")
    return a, b


def banco_mel(c):
    # Escala HTK. Triángulos de altura teórica 1, sin normalizar área.
    def mel(f):
        return 2595 * np.log10(1 + np.asarray(f) / 700)

    def hz(m):
        return 700 * (10 ** (np.asarray(m) / 2595) - 1)

    nodos = hz(
        np.linspace(
            mel(c["fmin_hz"]),
            mel(c["fmax_hz"]),
            c["n_mel"] + 2,
        )
    )
    frecuencias = np.fft.rfftfreq(
        c["n_fft"], d=1 / c["frecuencia_hz"]
    )

    filtros = []
    for lo, centro, hi in zip(
        nodos[:-2], nodos[1:-1], nodos[2:]
    ):
        ascendente = (frecuencias - lo) / (centro - lo)
        descendente = (hi - frecuencias) / (hi - centro)
        filtros.append(
            np.maximum(0, np.minimum(ascendente, descendente))
        )

    B = np.asarray(filtros)
    if np.any(B.sum(axis=1) <= 0):
        raise ValueError(
            "Filtros Mel sin soporte: revisar n_fft y n_mel."
        )
    return B, frecuencias, nodos


def calcular_locales(ventanas, c):
    ventanas = np.asarray(ventanas, dtype=np.float64)
    if (
        ventanas.ndim != 2
        or ventanas.shape[1] < 2
        or not np.isfinite(ventanas).all()
    ):
        raise AudioNoVectorizable("Ventanas acústicas inválidas.")

    # ZCR y amplitud se calculan ANTES de aplicar Hann.
    # El cero pertenece al lado no negativo.
    cambios = (
        np.signbit(ventanas[:, 1:])
        != np.signbit(ventanas[:, :-1])
    )
    zcr = cambios.mean(axis=1)
    amplitud_media = np.abs(ventanas).mean(axis=1)
    amplitud_max = np.abs(ventanas).max(axis=1)

    ventana_hann = hann(ventanas.shape[1], sym=False)
    espectro = rfft(
        ventanas * ventana_hann,
        n=c["n_fft"],
        axis=1,
        workers=1,
    )
    potencia = np.abs(espectro) ** 2 / c["n_fft"]

    B, _, _ = banco_mel(c)
    energias = potencia @ B.T
    logmel = np.log(np.maximum(energias, c["piso_potencia"]))

    coeficientes = dct(
        logmel,
        type=2,
        norm="ortho",
        orthogonalize=True,
        axis=1,
        workers=1,
    )
    mfcc = coeficientes[:, c["indices_mfcc"]]

    return {
        "zcr": zcr,
        "amplitud_media": amplitud_media,
        "amplitud_max": amplitud_max,
        "mfcc": mfcc,
        "logmel": logmel,
        "rms": np.sqrt(np.mean(ventanas ** 2, axis=1)),
    }


def resumir_segmentos(locales, segmentos, c):
    valores = []
    conteos = []

    for s in range(c["segmentos"]):
        seleccion = segmentos == s
        n = int(seleccion.sum())
        conteos.append(n)

        if n == 0:
            raise AudioNoVectorizable(
                f"Segmento {s + 1} sin ventanas: "
                "actividad demasiado corta para esta configuración."
            )

        z = locales["zcr"][seleccion]
        valores.extend([
            float(z.mean()),
            float(z.max()),
            float(locales["amplitud_media"][seleccion].mean()),
            float(locales["amplitud_max"][seleccion].max()),
        ])

        for j in range(len(c["indices_mfcc"])):
            v = locales["mfcc"][seleccion, j]
            valores.extend([
                float(v.mean()),
                float(v.max()),
                float(v.std(ddof=0)),
            ])

    return np.asarray(valores, dtype=np.float64), conteos


def extraer_audio(
    audio,
    fs,
    limites_actividad,
    cfg=None,
    devolver_intermedios=False,
):
    c = cargar_config() if cfg is None else validar_config(cfg)

    if fs != c["frecuencia_hz"]:
        raise AudioNoVectorizable(
            "Se requiere audio procesado a 16 kHz."
        )

    try:
        x = a_flotante(audio)
    except ValueError as e:
        raise AudioNoVectorizable(str(e)) from e

    if x.shape[1] != 1:
        raise AudioNoVectorizable(
            "Se requiere mono; no se mezclan canales en esta etapa."
        )
    x = x[:, 0]

    if (
        not isinstance(limites_actividad, (tuple, list, np.ndarray))
        or len(limites_actividad) != 2
        or any(
            not isinstance(k, (int, np.integer))
            for k in limites_actividad
        )
    ):
        raise AudioNoVectorizable(
            "Los límites deben ser dos índices enteros [inicio, fin)."
        )

    a, b = map(int, limites_actividad)
    if not 0 <= a < b <= len(x):
        raise AudioNoVectorizable("Límites fuera del WAV.")

    rms = float(np.sqrt(np.mean(x[a:b] ** 2)))
    if rms <= c["rms_minimo"] or np.std(x[a:b]) <= 1e-8:
        raise AudioNoVectorizable(
            "Actividad silenciosa, casi nula o constante."
        )

    W = round(fs * c["ventana_ms"] / 1000)
    H = round(fs * c["salto_ms"] / 1000)

    # Ventanas centradas en el intervalo activo.
    centros = np.arange(a + H // 2, b, H, dtype=np.int64)
    if centros.size == 0:
        raise AudioNoVectorizable("Actividad demasiado corta.")

    posiciones = centros[:, None] - W // 2 + np.arange(W)
    validos = (posiciones >= 0) & (posiciones < len(x))

    # Los márgenes existentes aportan contexto. Solo fuera del WAV
    # se completa con ceros, dejando un aviso explícito.
    ventanas = np.zeros(posiciones.shape, dtype=np.float64)
    ventanas[validos] = x[posiciones[validos]]

    segmentos = (
        (centros - a) * c["segmentos"] // (b - a)
    ).astype(int)

    locales = calcular_locales(ventanas, c)
    vector, conteos = resumir_segmentos(locales, segmentos, c)

    if (
        vector.shape != (len(nombres_caracteristicas(c)),)
        or not np.isfinite(vector).all()
    ):
        raise RuntimeError("Vector no finito o dimensión incoherente.")

    avisos = []
    if not validos.all():
        avisos.append("contexto_fuera_del_wav_completado_con_ceros")

    silenciosas = locales["rms"] <= c["rms_minimo"]
    if silenciosas.any():
        avisos.append(
            f"ventanas_casi_silenciosas:{int(silenciosas.sum())}"
        )

    for s, n in enumerate(conteos):
        if n == 1:
            avisos.append(f"segmento_con_una_ventana:{s + 1}")
        if np.all(silenciosas[segmentos == s]):
            avisos.append(f"segmento_casi_silencioso:{s + 1}")

    info = {
        "version": c["version"],
        "dimension": int(vector.size),
        "frecuencia_hz": int(fs),
        "limites_actividad_muestras": [a, b],
        "duracion_actividad_s": (b - a) / fs,
        "ventana_muestras": W,
        "salto_muestras": H,
        "ventanas": int(centros.size),
        "ventanas_por_segmento": conteos,
        "centros_muestras": centros.tolist(),
        "segmentos_por_ventana": (segmentos + 1).tolist(),
        "bordes_segmentos_s": (
            np.linspace(a, b, c["segmentos"] + 1) / fs
        ).tolist(),
        "rms_actividad": rms,
        "avisos": avisos,
    }

    if devolver_intermedios:
        intermedios = dict(
            locales,
            centros_s=centros / fs,
            segmentos=segmentos,
        )
        return vector, info, intermedios

    return vector, info
