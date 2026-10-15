"""Conjunto sintético v1: 160 muestras. No incluye reconocimiento ni voz."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import platform
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import numpy as np
import scipy
from scipy.ndimage import gaussian_filter
import PIL
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from piloto_deformaciones import generar_muestra

RAIZ = Path(__file__).resolve().parents[1]
VERSION = 'conjunto-1.0.0'


def hash_archivo(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_guardar(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def rng_muestra(semilla, componente):
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence([semilla, componente])))


def simular_captura(imagen, semilla, perfil):
    """Contorno variable, contraste, desenfoque y ruido. No es biomecánica de la piel."""
    rng = rng_muestra(semilla, 2)
    h, w = imagen.shape
    y, x = np.mgrid[:h, :w]
    cx = (w-1)/2 + rng.uniform(-5, 5)
    cy = .52*(h-1) + rng.uniform(-7, 7)
    rx = rng.uniform(.45, .49)*w
    ry = rng.uniform(.45, .49)*h
    angulo = rng.uniform(-4, 4)
    t = np.deg2rad(angulo)
    xx = np.cos(t)*(x-cx)+np.sin(t)*(y-cy)
    yy = -np.sin(t)*(x-cx)+np.cos(t)*(y-cy)
    radio = np.sqrt((xx/rx)**2+(yy/ry)**2)
    # Transición suave entre la zona de contacto y el fondo blanco.
    a = np.clip((1-radio)/.07, 0, 1)
    contacto = a*a*(3-2*a)
    contraste = float(rng.uniform(*perfil['contraste']))
    pendiente = float(rng.uniform(-.05, .05))
    ganancia = np.clip(contraste+pendiente*(y/(h-1)-.5), .5, 1)
    imagen = 255-(255-imagen.astype(float))*ganancia*contacto
    corte = None
    if perfil['recorte_borde']:
        lado = str(rng.choice(['izquierda','derecha','arriba','abajo']))
        fraccion = float(rng.uniform(.06, .12))
        n = max(1, round(fraccion*(w if lado in ['izquierda','derecha'] else h)))
        if lado == 'izquierda': imagen[:, :n] = 255
        elif lado == 'derecha': imagen[:, -n:] = 255
        elif lado == 'arriba': imagen[:n, :] = 255
        else: imagen[-n:, :] = 255
        corte = dict(lado=lado, pixeles=n, fraccion=fraccion)
    sigma_blur = float(rng.uniform(*perfil['desenfoque_sigma']))
    sigma_ruido = float(rng.uniform(*perfil['ruido_sigma']))
    imagen = gaussian_filter(imagen, sigma_blur, mode='constant', cval=255)
    imagen += rng.normal(0, sigma_ruido, imagen.shape)
    imagen = np.clip(np.rint(imagen), 0, 255).astype(np.uint8)
    params = dict(centro_x_px=cx, centro_y_px=cy, radio_x_px=rx, radio_y_px=ry,
                  angulo_contacto_grados=angulo, transicion_contacto=.07,
                  contraste=contraste, pendiente_iluminacion=pendiente,
                  recorte=corte, desenfoque_sigma_px=sigma_blur, ruido_sigma_gris=sigma_ruido)
    return imagen, params


def preprocesar(original, cfg):
    """ROI fija sin reescala; contraste por imagen y suavizado común muy leve."""
    y0, y1, x0, x1 = cfg['roi_contraste_y0_y1_x0_x1']
    roi = original[y0:y1, x0:x1]
    bajo, alto = np.percentile(roi, cfg['percentiles_contraste'])
    if alto-bajo < 10:
        raise ValueError('Imagen sin contraste suficiente.')
    arr = np.clip((original.astype(float)-bajo)*255/(alto-bajo), 0, 255)
    arr = gaussian_filter(arr, cfg['sigma_suavizado_px'], mode='constant', cval=255)
    return np.rint(arr).astype(np.uint8), dict(percentil_bajo=float(bajo), percentil_alto=float(alto))


def planificar(conf):
    tareas = []
    for identidad in conf['identidades']:
        grupos = [('entrenamiento',20),('validacion',10),('prueba',10)] if identidad['grupo']=='autorizado' else [(identidad['particion'],10)]
        numero = 0
        for particion, cantidad in grupos:
            for j in range(cantidad):
                numero += 1
                # Dos muestras prefijadas por identidad de prueba: posiciones 2 y 9.
                demo = particion=='prueba' and j in [1,8]
                tareas.append(dict(identidad=identidad, muestra=f"{identidad['id']}_M{numero:02}",
                    numero=numero, particion=particion, reserva_demo=demo,
                    semilla=identidad['indice_semillas']*10000+numero,
                    perfil=conf['perfiles'][j % len(conf['perfiles'])]))
    return tareas


def producir(base, tarea, conf):
    perfil = tarea['perfil']
    rng = rng_muestra(tarea['semilla'], 1)
    semilla_local = int(rng.integers(0, 2**32, dtype=np.uint64))
    perfil_local = dict(nombre=perfil['nombre'], amplitud_px=float(rng.uniform(*perfil['amplitud_local_px'])),
        rotacion_max_grados=perfil['rotacion_max_grados'], traslacion_max_px=perfil['traslacion_max_px'],
        desenfoque_sigma_px=0, ruido_sigma_gris=0)
    deformada, params_deformacion, _, _ = generar_muestra(base, semilla_local, perfil_local)
    original, params_captura = simular_captura(deformada, tarea['semilla'], perfil)
    procesada, params_prepro = preprocesar(original, conf['preprocesamiento'])
    return original, procesada, dict(semilla_deformacion=semilla_local,
        deformacion=params_deformacion, captura=params_captura, preprocesamiento_efectivo=params_prepro)


def verificar_bases(conf):
    bases, archivos = {}, []
    for ident in conf['identidades']:
        base = RAIZ/ident['base']
        if not base.is_file(): raise FileNotFoundError(f'Falta {base}')
        if hash_archivo(base) != ident['sha256_base']:
            raise ValueError(f'La base {ident["id"]} no coincide con la revisada.')
        with Image.open(base) as im:
            if im.size != (275,400) or im.mode!='L': raise ValueError(f'Formato inesperado: {base}')
            bases[ident['id']] = np.array(im)
        conf_anguli = RAIZ/ident['config_anguli']
        nodo = ET.parse(conf_anguli).getroot().find('FingerprintGen/customSeed')
        if nodo is None or nodo.attrib.get('value')!='1' or int(nodo.attrib['seedValue'])!=ident['semilla_base']:
            raise ValueError(f'Semilla de Anguli inesperada para {ident["id"]}.')
        archivos.append(dict(identidad=ident['id'], base=ident['base'], sha256_base=hash_archivo(base),
                             config_anguli=ident['config_anguli'], sha256_config_anguli=hash_archivo(conf_anguli)))
    if len({a['sha256_base'] for a in archivos}) != len(archivos):
        raise ValueError('Hay bases repetidas en identidades diferentes.')
    return bases, archivos


def comprobar_conjunto(filas, imagenes, completo):
    # Solo integridad sobre prueba: no se calculan puntuaciones de reconocimiento.
    resumen = dict(total=len(filas), completo=completo,
        cantidades_por_grupo_y_particion=dict(Counter(f"{r['grupo']}/{r['particion']}" for r in filas)),
        reservas_demo=sum(r['reserva_demo'] for r in filas))
    if len({r['semilla_muestra'] for r in filas}) != len(filas): raise ValueError('Semillas repetidas.')
    for campo in ['sha256_original','sha256_procesado']:
        if len({r[campo] for r in filas}) != len(filas): raise ValueError(f'Duplicados exactos: {campo}')
    resumen['duplicados_exactos'] = 0
    resumen['candidatos_casi_duplicados_entre_particiones'] = []
    # Cribado simple en ROI central, sin alineación, no una medida biométrica.
    for i, a in enumerate(filas):
        for j in range(i):
            b = filas[j]
            if a['identidad']!=b['identidad'] or a['particion']==b['particion']: continue
            diferencia = float(np.mean((imagenes[i][50:350,35:240]<128)!=(imagenes[j][50:350,35:240]<128)))
            if diferencia<.015:
                resumen['candidatos_casi_duplicados_entre_particiones'].append([a['muestra'],b['muestra'],diferencia])
    resumen['criterio_casi_duplicados'] = 'menos de 1.5% de píxeles binarios diferentes en ROI central; sin registro geométrico'
    if completo:
        esperado={'autorizado/entrenamiento':60,'autorizado/validacion':30,'autorizado/prueba':30,
                  'intruso/validacion':20,'intruso/prueba':20}
        if resumen['cantidades_por_grupo_y_particion']!=esperado: raise ValueError('Cantidades incorrectas.')
        ids_val={r['identidad'] for r in filas if r['grupo']=='intruso' and r['particion']=='validacion'}
        ids_test={r['identidad'] for r in filas if r['grupo']=='intruso' and r['particion']=='prueba'}
        if ids_val & ids_test: raise ValueError('Intrusos compartidos entre validación y prueba.')
    resumen['jacobiano_muestreo_min'] = min(float(r['jacobiano_min']) for r in filas)
    resumen['jacobiano_muestreo_max'] = max(float(r['jacobiano_max']) for r in filas)
    return resumen


def graficar_desarrollo(filas, originales, procesadas, destino):
    # Cinco primeras muestras de validación por identidad: una de cada perfil.
    grupos = []
    for identidad in dict.fromkeys(r['identidad'] for r in filas):
        indices = [i for i,r in enumerate(filas) if r['identidad']==identidad and r['particion']=='validacion']
        if indices: grupos.append(indices[:5])
    if not grupos: return
    columnas = max(map(len, grupos))
    fig, axs = plt.subplots(len(grupos), columnas, figsize=(2.6*columnas,4*len(grupos)), squeeze=False)
    for row, indices in enumerate(grupos):
        for col, ax in enumerate(axs[row]):
            ax.axis('off')
            if col >= len(indices): continue
            i = indices[col]
            ax.imshow(procesadas[i], cmap='gray', vmin=0, vmax=255)
            ax.set_title(f"{filas[i]['muestra']}\n{filas[i]['perfil']}", fontsize=9)
    fig.suptitle('Procesadas de validación — una muestra de cada perfil por identidad')
    fig.tight_layout(rect=(0,0,1,.975))
    fig.savefig(destino/'comparacion_validacion.png',dpi=110); plt.close(fig)
    # Original/procesada para los cinco perfiles de la primera identidad disponible.
    indices = grupos[0]
    fig, axs = plt.subplots(len(indices),2,figsize=(6,3.8*len(indices)),squeeze=False)
    for row,i in enumerate(indices):
        for col,(arr,titulo) in enumerate([(originales[i],'Original'),(procesadas[i],'Procesada')]):
            axs[row,col].imshow(arr,cmap='gray',vmin=0,vmax=255)
            axs[row,col].set_title(f"{filas[i]['muestra']} — {titulo}")
            axs[row,col].axis('off')
    fig.suptitle('Preprocesamiento — solo validación')
    fig.tight_layout(rect=(0,0,1,.98))
    fig.savefig(destino/'preprocesamiento_validacion.png',dpi=110); plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='config/conjunto_v1.json')
    parser.add_argument('--nombre',default='conjunto_v1',help='Nombre nuevo para las carpetas de salida.')
    parser.add_argument('--muestra',help='Regenerar únicamente un ID, por ejemplo A01_M21.')
    args=parser.parse_args()
    if not args.nombre.replace('_','').replace('-','').isalnum(): raise ValueError('Nombre de salida inválido.')
    conf=json.loads((RAIZ/args.config).read_text(encoding='utf-8-sig'))
    bases,fuentes=verificar_bases(conf)
    tareas=[t for t in planificar(conf) if args.muestra is None or t['muestra']==args.muestra]
    if not tareas: raise ValueError('Muestra inexistente.')
    rutas=[RAIZ/'datos'/'originales'/args.nombre,RAIZ/'datos'/'procesados'/args.nombre,
           RAIZ/'resultados'/args.nombre]
    meta=RAIZ/'datos'/('metadatos.csv' if args.nombre=='conjunto_v1' else f'metadatos_{args.nombre}.csv')
    for p in [*rutas,meta]:
        if p.exists(): raise FileExistsError(f'Ya existe {p}. Usá --nombre con un nombre nuevo.')
    for p in rutas: p.mkdir(parents=True)
    origdir,procdir,reportdir=rutas
    entorno=dict(python=platform.python_version(),sistema=platform.platform(),numpy=np.__version__,
                 scipy=scipy.__version__,pillow=PIL.__version__,matplotlib=matplotlib.__version__,
                 generador=VERSION,rng='NumPy PCG64 con SeedSequence por muestra/componente',
                 codigo={p.name:hash_archivo(p) for p in [Path(__file__),RAIZ/'src'/'piloto_deformaciones.py']},
                 sha256_config=hash_archivo(RAIZ/args.config))
    json_guardar(reportdir/'entorno.json',entorno)
    json_guardar(reportdir/'config_efectiva.json',conf)
    json_guardar(reportdir/'fuentes.json',fuentes)
    filas,originales,procesadas=[],[],[]
    for tarea in tareas:
        ident=tarea['identidad'];nombre=tarea['muestra']
        original,procesada,params=producir(bases[ident['id']],tarea,conf)
        for arr in [original,procesada]:
            tinta=np.mean(arr<128)
            if not .05<tinta<.7: raise ValueError(f'Contenido anómalo en {nombre}: {tinta}')
        po=origdir/tarea['particion']/ident['id']/(nombre+'.png')
        pp=procdir/tarea['particion']/ident['id']/(nombre+'.png')
        po.parent.mkdir(parents=True,exist_ok=True);pp.parent.mkdir(parents=True,exist_ok=True)
        Image.fromarray(original).save(po);Image.fromarray(procesada).save(pp)
        fila=dict(identidad=ident['id'],grupo=ident['grupo'],muestra=nombre,
            particion=tarea['particion'],reserva_demo=tarea['reserva_demo'],
            base=ident['base'],sha256_base=ident['sha256_base'],tipo_morfologico=ident['tipo_morfologico'],
            generador_base='Anguli',version_anguli='no indicada en About',semilla_base=ident['semilla_base'],
            config_anguli=ident['config_anguli'],generador_variantes=VERSION,semilla_muestra=tarea['semilla'],
            perfil=tarea['perfil']['nombre'],parametros_json=json.dumps(params,ensure_ascii=False),
            preprocesamiento_json=json.dumps(conf['preprocesamiento'],ensure_ascii=False),
            original=po.relative_to(RAIZ).as_posix(),procesado=pp.relative_to(RAIZ).as_posix(),
            sha256_original=hash_archivo(po),sha256_procesado=hash_archivo(pp),
            jacobiano_min=params['deformacion']['jacobiano_muestreo_min'],
            jacobiano_max=params['deformacion']['jacobiano_muestreo_max'],
            entorno=(reportdir/'entorno.json').relative_to(RAIZ).as_posix())
        filas.append(fila);originales.append(original);procesadas.append(procesada)
    resumen=comprobar_conjunto(filas,procesadas,args.muestra is None)
    with meta.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(filas[0]));writer.writeheader();writer.writerows(filas)
    graficar_desarrollo(filas,originales,procesadas,reportdir)
    resumen['bytes_imagenes']=sum(p.stat().st_size for d in [origdir,procdir] for p in d.rglob('*.png'))
    resumen['previsualizacion_prueba']=False
    json_guardar(reportdir/'verificacion.json',resumen)
    print(f'OK: {len(filas)} originales y {len(filas)} procesadas.')
    print(f'Metadatos: {meta}')
    print(f'Informe: {reportdir}')
    print(f"Tamaño de imágenes: {resumen['bytes_imagenes']/1024/1024:.2f} MiB")
    print('Duplicados exactos: 0. Prueba final excluida de las comparaciones visuales.')
    if resumen['candidatos_casi_duplicados_entre_particiones']:
        print('REVISAR: candidatos casi duplicados indicados en verificacion.json. No se regeneraron ni descartaron automáticamente.')


if __name__=='__main__':
    try: main()
    except (ValueError,FileNotFoundError,FileExistsError) as error:
        sys.exit(f'ERROR: {error}')
