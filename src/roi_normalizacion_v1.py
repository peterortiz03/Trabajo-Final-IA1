"""Etapa 1: ROI y centrado a escala nativa. Sin orientación ni reconocimiento."""
import numpy as np
from PIL import Image
from scipy.ndimage import (gaussian_filter, binary_closing, binary_fill_holes,
                           binary_dilation, label)

CONFIG_PREDETERMINADA = dict(lado_salida=512,sigma_deteccion=2.0,
    fraccion_contraste=.12,diferencia_minima_fondo=12.0,radio_cierre=5,
    margen_mascara=6,margen_recorte=8,area_minima=500,contraste_minimo=20)


def disco(radio):
    y,x=np.mgrid[-radio:radio+1,-radio:radio+1]
    return x*x+y*y<=radio*radio


def normalizar_huella(imagen, configuracion=None):
    """Recibe PIL.Image o array uint8 (gris/RGB/RGBA).

    Devuelve (normalizada_uint8, informacion). informacion incluye dos máscaras
    booleanas: mascara_original y mascara_normalizada; el resto es JSON serializable.
    No lee archivos, no escribe, no usa identidad/semilla/ángulo, no modifica la entrada.
    Levanta ValueError para imagen sin señal suficiente o ROI mayor que el lienzo.
    """
    cfg=CONFIG_PREDETERMINADA.copy()
    if configuracion is not None:
        desconocidas=set(configuracion)-set(cfg)
        if desconocidas:raise ValueError(f'Parámetros desconocidos: {desconocidas}')
        cfg.update(configuracion)
    if not isinstance(imagen,Image.Image):
        a=np.asarray(imagen)
        if a.dtype!=np.uint8 or a.ndim not in [2,3] or (a.ndim==3 and a.shape[2] not in [3,4]):
            raise ValueError('Usá una imagen uint8 en gris, RGB o RGBA.')
        imagen=Image.fromarray(a)
    if imagen.mode in ['RGBA','LA'] or 'transparency' in imagen.info:
        rgba=imagen.convert('RGBA');fondo=Image.new('RGBA',rgba.size,'white')
        imagen=Image.alpha_composite(fondo,rgba)
    a=np.array(imagen.convert('L'),dtype=np.uint8)
    if min(a.shape)<32:raise ValueError('La imagen es demasiado pequeña.')
    oscuro,fondo=np.percentile(a,[2,98])
    contraste=float(fondo-oscuro)
    if contraste<cfg['contraste_minimo']:
        raise ValueError('No se detecta contraste suficiente entre huella y fondo.')
    # Suavizado SOLO para detectar ROI; nunca se aplica a los píxeles de salida.
    suave=gaussian_filter(a.astype(float),cfg['sigma_deteccion'],mode='constant',cval=float(fondo))
    umbral=float(fondo-max(cfg['diferencia_minima_fondo'],cfg['fraccion_contraste']*contraste))
    candidata=suave<umbral
    candidata=binary_closing(candidata,structure=disco(cfg['radio_cierre']))
    etiquetas,n=label(candidata)
    if n==0:raise ValueError('No se encontró una región de huella.')
    areas=np.bincount(etiquetas.ravel());areas[0]=0
    region=etiquetas==areas.argmax()
    region=binary_fill_holes(region)
    if region.sum()<cfg['area_minima']:raise ValueError('Región detectada demasiado pequeña.')
    # Margen conservador para no eliminar crestas débiles del contorno.
    mascara=binary_dilation(region,structure=disco(cfg['margen_mascara']))
    yy,xx=np.where(mascara)
    x0,x1,y0,y1=int(xx.min()),int(xx.max()+1),int(yy.min()),int(yy.max()+1)
    m=cfg['margen_recorte']
    cx0,cx1,cy0,cy1=max(0,x0-m),min(a.shape[1],x1+m),max(0,y0-m),min(a.shape[0],y1+m)
    # Centrar el centro del bbox DE LA MÁSCARA, no el recorte con márgenes asimétricos.
    centro_x=(x0+x1-1)/2;centro_y=(y0+y1-1)/2
    lado=int(cfg['lado_salida']);centro_destino=(lado-1)/2
    tx=int(round(centro_destino-centro_x));ty=int(round(centro_destino-centro_y))
    dx0,dx1,dy0,dy1=cx0+tx,cx1+tx,cy0+ty,cy1+ty
    if min(dx0,dy0)<0 or max(dx1,dy1)>lado:
        raise ValueError('La ROI no cabe a escala nativa. Revisá detección/lienzo; no se reescala automáticamente.')
    salida=np.full((lado,lado),255,dtype=np.uint8)
    mask_out=np.zeros((lado,lado),bool)
    recorte=np.where(mascara[cy0:cy1,cx0:cx1],a[cy0:cy1,cx0:cx1],255).astype(np.uint8)
    salida[dy0:dy1,dx0:dx1]=recorte
    mask_out[dy0:dy1,dx0:dx1]=mascara[cy0:cy1,cx0:cx1]
    tinta=a<(fondo-.35*contraste)
    cobertura=float(np.count_nonzero(tinta & mascara)/max(1,np.count_nonzero(tinta)))
    avisos=[]
    if cobertura<.995:avisos.append('La máscara excluye parte de los píxeles oscuros: revisar segmentación.')
    if x0==0 or y0==0 or x1==a.shape[1] or y1==a.shape[0]:
        avisos.append('La región alcanza un borde de la entrada: posible recorte previo.')
    info=dict(version='roi-centrado-0.1.0',tamano_entrada_ancho_alto=[a.shape[1],a.shape[0]],
        tamano_salida_ancho_alto=[lado,lado],umbral_deteccion=umbral,contraste_estimado=contraste,
        bbox_mascara_xyxy=[x0,y0,x1,y1],traslacion_x_y=[tx,ty],
        centro_bbox_salida_x_y=[centro_x+tx,centro_y+ty],error_centrado_max_px=float(max(abs(centro_x+tx-centro_destino),abs(centro_y+ty-centro_destino))),
        cobertura_tinta=cobertura,area_mascara_px=int(mascara.sum()),avisos=avisos,
        rotacion_corregida=False,reescalado=False,contraste_salida_modificado=False,
        mascara_original=mascara,mascara_normalizada=mask_out)
    return salida,info
