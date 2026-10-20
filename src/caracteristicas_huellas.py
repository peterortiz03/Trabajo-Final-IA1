"""GLCM con máscara y agrupación de cuadrantes opuestos: un vector por huella.

No lee etiquetas ni ajusta parámetros sobre un conjunto de datos. La misma
función extraer_huella(imagen, mascara, config) sirve para una muestra nueva.
Consultar documentos/caracteristicas_huellas_hito1.md para fórmulas y límites.
"""
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_erosion

BLOQUES = ("global", "NO_SE", "NE_SO")
MEDIDAS = ("contraste", "homogeneidad", "energia", "correlacion")


class HuellaNoVectorizable(ValueError):
    """Entrada no apta para este descriptor; no equivale a identidad intrusa."""


def validar_config(cfg):
    claves = {"version", "niveles", "distancias_px", "angulos_grados",
              "percentiles", "contraste_minimo", "erosion_radio_px",
              "min_pixeles_region", "min_pares_region"}
    if set(cfg) != claves or cfg["version"] != "glcm_opuestas_v1":
        raise ValueError("Configuración incompleta, claves desconocidas o versión incompatible.")
    for k, minimo, maximo in [("niveles", 2, 256), ("erosion_radio_px", 0, 32),
                              ("min_pixeles_region", 1, 1000000),
                              ("min_pares_region", 1, 1000000)]:
        if type(cfg[k]) is not int or not minimo <= cfg[k] <= maximo:
            raise ValueError(f"Parámetro inválido: {k}")
    ds, ang = cfg["distancias_px"], cfg["angulos_grados"]
    if not isinstance(ds, list) or not ds or any(type(d) is not int or not 1 <= d <= 64 for d in ds):
        raise ValueError("Distancias: lista de enteros entre 1 y 64.")
    if len(set(ds)) != len(ds) or ds != sorted(ds):
        raise ValueError("Distancias repetidas o fuera de orden.")
    if ang != [0, 45, 90, 135]:
        raise ValueError("Esta versión conserva las cuatro direcciones: 0,45,90,135.")
    ps = cfg["percentiles"]
    if not isinstance(ps, list) or len(ps) != 2 or not 0 <= ps[0] < ps[1] <= 100:
        raise ValueError("Percentiles inválidos.")
    if not 0 < cfg["contraste_minimo"] <= 255:
        raise ValueError("Contraste mínimo inválido.")
    return cfg


def cargar_config(ruta=None):
    if ruta is None:
        ruta = Path(__file__).resolve().parents[1] / "config/caracteristicas_huellas_glcm_v1.json"
    return validar_config(json.loads(Path(ruta).read_text(encoding="utf-8-sig")))


def desplazamientos(cfg):
    """Direcciones en coordenadas de imagen: y crece hacia abajo.

    Distancia nominal euclídea; se redondean dy y dx al píxel más cercano.
    La distancia efectiva diagonal puede diferir de la nominal.
    """
    for d in cfg["distancias_px"]:
        for a in cfg["angulos_grados"]:
            t = np.deg2rad(a)
            yield d, a, int(np.rint(d * np.sin(t))), int(np.rint(d * np.cos(t)))


def nombres_caracteristicas(cfg):
    validar_config(cfg)
    return [f"{b}_d{d}_a{a}_{m}" for b in BLOQUES
            for d, a, _, _ in desplazamientos(cfg) for m in MEDIDAS]


def preparar_huella(imagen, mascara, cfg):
    """Erosión de ROI, contraste por muestra y cuantización. Sin filtrado de crestas.

    Acepta imagen gris uint8 y máscara bool o binaria 0/1/255 de igual tamaño.
    Las regiones se definen respecto del rectángulo de la máscara erosionada.
    Una fila/columna central exacta (tamaño impar) solo participa en el global.
    """
    validar_config(cfg)
    im, m = np.asarray(imagen), np.asarray(mascara)
    if im.ndim != 2 or im.dtype != np.uint8 or im.size == 0:
        raise HuellaNoVectorizable("Se requiere una imagen gris uint8 2D no vacía.")
    if m.shape != im.shape or not np.isin(m, [0, 1, 255]).all():
        raise HuellaNoVectorizable("Máscara no binaria o de tamaño distinto a la imagen.")
    m = m > 0
    r = cfg["erosion_radio_px"]
    if r:
        yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
        m = binary_erosion(m, structure=xx * xx + yy * yy <= r * r, border_value=0)
    if int(m.sum()) < cfg["min_pixeles_region"]:
        raise HuellaNoVectorizable("ROI vacía o insuficiente después de la erosión.")
    ys, xs = np.where(m)
    y0, y1, x0, x1 = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
    im = im[y0:y1, x0:x1]
    m = m[y0:y1, x0:x1]
    bajo, alto = np.percentile(im[m], cfg["percentiles"], method="linear")
    if alto - bajo < cfg["contraste_minimo"]:
        raise HuellaNoVectorizable(f"Contraste insuficiente: percentil alto-bajo={alto-bajo:.6g}.")
    acondicionado = np.clip((im.astype(np.float64) - bajo) / (alto - bajo), 0, 1)
    L = cfg["niveles"]
    q = np.minimum(np.floor(acondicionado * L), L - 1).astype(np.int64)
    h, w = m.shape
    y, x = np.ogrid[:h, :w]
    arriba, abajo = 2 * y < h - 1, 2 * y > h - 1
    izquierda, derecha = 2 * x < w - 1, 2 * x > w - 1
    regiones = {"global": m,
                "NO": m & arriba & izquierda, "NE": m & arriba & derecha,
                "SO": m & abajo & izquierda, "SE": m & abajo & derecha}
    for nombre, region in regiones.items():
        if int(region.sum()) < cfg["min_pixeles_region"]:
            raise HuellaNoVectorizable(f"Región {nombre}: menos de {cfg['min_pixeles_region']} píxeles.")
    info = {"bbox_xyxy": [x0, y0, x1, y1], "percentil_bajo": float(bajo),
            "percentil_alto": float(alto), "pixeles_regiones":
            {k: int(v.sum()) for k, v in regiones.items()}}
    return q, regiones, acondicionado, info


def contar_pares(q, region, dy, dx, niveles):
    """Cuenta SOLO pares cuyos dos extremos pertenecen a esta misma región.

    No cuenta fondo, no conecta cuadrantes, no envuelve bordes con np.roll.
    Devuelve matriz dirigida (aún no simétrica) y cantidad de pares físicos.
    """
    h, w = q.shape
    if abs(dy) >= h or abs(dx) >= w:
        return np.zeros((niveles, niveles), dtype=np.int64), 0
    s = (slice(max(0, -dy), min(h, h - dy)), slice(max(0, -dx), min(w, w - dx)))
    t = (slice(max(0, dy), min(h, h + dy)), slice(max(0, dx), min(w, w + dx)))
    validos = region[s] & region[t]
    indices = q[s][validos] * niveles + q[t][validos]
    C = np.bincount(indices, minlength=niveles * niveles).reshape(niveles, niveles)
    return C, int(validos.sum())


def medidas_glcm(C):
    """Simetriza los conteos y calcula cuatro estadísticas con orden fijo.

    La correlación constante se define como 1 por convenio y se informa.
    El contraste se divide por (L-1)^2; esto NO es un escalador aprendido.
    """
    if C.ndim != 2 or C.shape[0] != C.shape[1] or C.shape[0] < 2 or np.any(C < 0):
        raise ValueError("Conteos GLCM inválidos.")
    S = C.astype(np.float64) + C.T.astype(np.float64)
    total = S.sum()
    if not np.isfinite(S).all() or total <= 0:
        raise HuellaNoVectorizable("GLCM sin pares válidos o no finita.")
    P = S / total
    L = P.shape[0]
    i, j = np.indices(P.shape, dtype=np.float64)
    delta2 = (i - j) ** 2
    mi, mj = np.sum(P * i), np.sum(P * j)
    vi, vj = np.sum(P * (i - mi) ** 2), np.sum(P * (j - mj) ** 2)
    constante = bool(vi <= 1e-15 or vj <= 1e-15)
    corr = 1.0 if constante else float(np.sum(P * (i-mi) * (j-mj)) / np.sqrt(vi*vj))
    valores = [float(np.sum(P * delta2) / (L-1)**2),
               float(np.sum(P / (1 + delta2))), float(np.sqrt(np.sum(P * P))),
               float(np.clip(corr, -1, 1))]
    return valores, constante, P


def extraer_huella(imagen, mascara, cfg=None):
    """Devuelve (vector float64, diagnóstico JSON). No incorpora metadatos.

    Los dos cuadrantes de cada pareja se cuentan POR SEPARADO y luego se suman
    sus matrices. Bajo 180° se intercambian y se invierte el sentido de los
    pares; C+C.T elimina ese cambio. No se concatenan cuadrantes orientados.
    """
    cfg = cargar_config() if cfg is None else validar_config(cfg)
    q, regiones, _, info = preparar_huella(imagen, mascara, cfg)
    grupos = {"global": ("global",), "NO_SE": ("NO", "SE"), "NE_SO": ("NE", "SO")}
    valores, avisos, conteos = [], [], {}
    for region, mask in regiones.items():
        if np.unique(q[mask]).size == 1:
            avisos.append(f"textura_cuantizada_constante:{region}")
    for bloque, integrantes in grupos.items():
        for d, a, dy, dx in desplazamientos(cfg):
            C = np.zeros((cfg["niveles"], cfg["niveles"]), dtype=np.int64)
            detalle = {}
            for region in integrantes:
                sub, n = contar_pares(q, regiones[region], dy, dx, cfg["niveles"])
                if n < cfg["min_pares_region"]:
                    raise HuellaNoVectorizable(f"{region}/d{d}/a{a}: {n} pares; mínimo {cfg['min_pares_region']}.")
                C += sub
                detalle[region] = n
            medidas, constante, _ = medidas_glcm(C)
            clave = f"{bloque}_d{d}_a{a}"
            conteos[clave] = detalle
            if constante:
                avisos.append(f"correlacion_convencional_1:{clave}")
            valores.extend(medidas)
    vector = np.asarray(valores, dtype=np.float64)
    if vector.shape != (len(nombres_caracteristicas(cfg)),) or not np.isfinite(vector).all():
        raise RuntimeError("Error interno: dimensión o valores inválidos.")
    return vector, dict(info, pares_por_region=conteos, avisos=avisos,
                        dimension=int(vector.size), version=cfg["version"])
