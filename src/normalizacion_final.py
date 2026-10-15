"""Normalización geométrica reutilizable; orientación definida módulo 180 grados."""
import numpy as np
from scipy.ndimage import rotate
from roi_normalizacion_v1 import normalizar_huella as centrar_roi


def eje(mascara):
    y, x = np.where(mascara)
    valores, vectores = np.linalg.eigh(np.cov(np.vstack((x, y))))
    relacion = float(valores[1] / max(valores[0], 1e-9))
    vx, vy = vectores[:, 1]
    angulo = float((np.degrees(np.arctan2(vy, vx)) - 90 + 90) % 180 - 90)
    return angulo, relacion


def normalizar_huella(imagen, configuracion=None):
    """PIL o uint8 -> (imagen uint8, info). Mismo uso en lote y captura nueva.

    info contiene mascara_normalizada y alternativa_180 como arrays.
    No usa identidad, base original, semilla ni ángulo conocido de generación.
    No normaliza resolución física, contraste ni deformaciones elásticas.
    """
    centrada, info = centrar_roi(imagen, configuracion)
    mascara = info.pop('mascara_normalizada')
    info.pop('mascara_original')
    angulo, relacion = eje(mascara)
    fiable = relacion >= 1.2
    if not fiable:
        info['avisos'].append('Contorno casi circular: orientación no estimable con este método.')
        angulo = 0.0
    # Lienzo ampliado: no recortar la huella durante la rotación.
    girada = rotate(centrada, angulo, reshape=True, order=1, mode='constant', cval=255, prefilter=False)
    mask = rotate(mascara.astype(np.uint8), angulo, reshape=True, order=0, mode='constant', cval=0, prefilter=False).astype(bool)
    y, x = np.where(mask)
    x0, x1, y0, y1 = int(x.min()), int(x.max()+1), int(y.min()), int(y.max()+1)
    lado = centrada.shape[0]
    ancho, alto = x1-x0, y1-y0
    if max(ancho, alto) > lado-4:
        raise ValueError('La región girada no cabe con margen; no se recorta ni reescala.')
    dx, dy = (lado-ancho)//2, (lado-alto)//2
    salida = np.full((lado, lado), 255, np.uint8)
    final_mask = np.zeros((lado, lado), bool)
    final_mask[dy:dy+alto, dx:dx+ancho] = mask[y0:y1, x0:x1]
    salida[dy:dy+alto, dx:dx+ancho] = girada[y0:y1, x0:x1]
    salida[~final_mask] = 255
    residual, _ = eje(final_mask)
    if fiable and abs(residual) > 1:
        info['avisos'].append('El eje residual supera 1 grado: revisar orientación.')
    info.update(version='geometrica-1.0.0', angulo_aplicado_grados=angulo,
        relacion_autovalores=relacion, orientacion_estimable=fiable,
        eje_residual_grados=residual, ambiguedad_180=True,
        rotacion_corregida=fiable, mascara_normalizada=final_mask,
        alternativa_180=np.rot90(salida, 2).copy(),
        centro_bbox_salida_x_y=[dx+(ancho-1)/2, dy+(alto-1)/2],
        error_centrado_max_px=float(max(abs(dx+(ancho-1)/2-(lado-1)/2),abs(dy+(alto-1)/2-(lado-1)/2))))
    return salida, info
