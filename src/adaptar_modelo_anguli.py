"""Ajusta un modelo COMBINADO experimental sin modificar el modelo vigente.

Usa 120 capturas autorizadas anteriores + 60 impresiones autorizadas de Anguli.
Selección/escalado/centroides: solo entrenamiento. Umbral: solo validación.
No lee imágenes ni vectores de prueba final o del control Anguli 26–30.
"""
import os
os.environ.setdefault('MPLBACKEND', 'Agg')
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform

import numpy as np

from interfaz_servicios import RAIZ, leer_json, cargar_huellas, abrir_imagen
from diagnosticar_impresiones_anguli import escribir_csv, sha_archivo, particion
from normalizacion_final import normalizar_huella
from caracteristicas_huellas import extraer_huella, nombres_caracteristicas
from mejorar_clusterizacion_huellas import elegir_con_cv, ajustar
from calibrar_rechazo_huellas import medir_distancias, elegir_umbral, decidir_acceso

EXPERIMENTO = RAIZ/'experimentos/anguli_impresiones_v1'


def guardar_json(p, dato):
    p.write_text(json.dumps(dato, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def leer_csv(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def cargar_anguli(diagnostico, nombres):
    """Solo vectores ya extraídos de desarrollo; control no tiene vectores."""
    manifest = leer_csv(diagnostico/'manifiesto.csv')
    resumen = leer_json(diagnostico/'resumen.json')
    consultas = leer_csv(diagnostico/'consultas_modelo_actual.csv')
    if (len(manifest) != 150 or len(consultas) != 125
            or resumen['controles_sin_inferencia'] != 25
            or any(c['error'] for c in consultas)):
        raise ValueError('Diagnóstico incompleto o con errores: revisar antes de entrenar.')
    esperados = {(i,j) for i in ('A01','A02','A03','I01','I02') for j in range(1,31)}
    if {(r['identidad_real'],int(r['impresion'])) for r in manifest} != esperados:
        raise ValueError('El manifiesto no corresponde al plan fijo de cinco identidades.')
    if any(r['particion'] != particion(r['identidad_real'],int(r['impresion'])) for r in manifest):
        raise ValueError('Se modificó la separación de desarrollo/control.')
    if len({r['sha256_pixeles'] for r in manifest}) != 150:
        raise ValueError('Hay duplicados en el manifiesto.')
    with np.load(diagnostico/'caracteristicas_desarrollo.npz', allow_pickle=False) as z:
        X, indices, ns = z['X'].copy(), z['indices_manifiesto'].copy(), z['nombres'].tolist()
    esperados_indices = [j for j,r in enumerate(manifest) if r['particion'] != 'control_apartado']
    if (ns != list(nombres) or X.shape != (125,144) or not np.isfinite(X).all()
            or not np.array_equal(indices,esperados_indices)):
        raise ValueError('Matriz o referencias del diagnóstico incompatibles; no ajustar.')
    filas=[]
    for idx in indices:
        r=manifest[int(idx)]
        filas.append(dict(muestra=f"ANG_{r['identidad_real']}_{int(r['impresion']):02}",
            identidad=r['identidad_real'], grupo=r['grupo_real'], fuente='anguli',
            particion='entrenamiento' if r['particion']=='ajuste_experimental' else 'validacion',
            archivo=r['archivo'], sha256=r['sha256_archivo']))
    if any(r['grupo'] != ('autorizado' if r['identidad'].startswith('A') else 'intruso') for r in filas):
        raise ValueError('Etiquetas de referencia de grupo incoherentes.')
    return X,filas


def cargar_anteriores(s):
    """Reextrae únicamente las imágenes de desarrollo existentes, sin escribirlas."""
    filas=leer_csv(RAIZ/'datos/metadatos_con_rotaciones_train_v1.csv')
    filas=[r for r in filas if r['particion'] in ('entrenamiento','validacion')]
    if (sum(r['particion']=='entrenamiento' for r in filas)!=120
            or sum(r['particion']=='validacion' for r in filas)!=50):
        raise ValueError('Cambió el conjunto anterior: se esperan 120 de entrenamiento y 50 de validación.')
    X,meta=[],[]
    for r in filas:
        if r['particion']=='entrenamiento' and r['grupo']!='autorizado':
            raise ValueError('No se admiten intrusos en el ajuste de centroides.')
        p=RAIZ/r['original']
        if sha_archivo(p)!=r['sha256_original']:
            raise ValueError(f"Imagen anterior modificada: {r['original']}")
        normal,info=normalizar_huella(abrir_imagen(p),s['cfg_norm'])
        v,_=extraer_huella(normal,info['mascara_normalizada'],s['cfg_ext'])
        X.append(v)
        meta.append(dict(muestra=r['muestra'],identidad=r['identidad'],grupo=r['grupo'],
                         fuente='anterior',particion=r['particion'],archivo=r['original'],
                         sha256=r['sha256_original']))
    return np.asarray(X),meta


def metricas(filas, decisiones):
    resumen=[]
    for fuente in ('anterior','anguli'):
        for grupo in ('autorizado','intruso'):
            sub=[(f,d) for f,d in zip(filas,decisiones) if f['fuente']==fuente and f['grupo']==grupo]
            resumen.append(dict(fuente=fuente,grupo=grupo,n=len(sub),
                aceptadas=sum(d['aceptada'] for _,d in sub),
                rechazadas=sum(not d['aceptada'] for _,d in sub),
                identificadas_correctamente=sum(d['aceptada'] and d['identidad']==f['identidad'] for f,d in sub),
                identidades_incorrectas_aceptadas=sum(d['aceptada'] and d['identidad']!=f['identidad'] for f,d in sub)
                    if grupo=='autorizado' else 0))
    return resumen


def ejecutar(diagnostico, salida=None):
    diagnostico=Path(diagnostico).resolve()
    fecha=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    salida=Path(salida).resolve() if salida else EXPERIMENTO/'modelos_combinados'/fecha
    if salida.exists():
        raise ValueError(f'La salida ya existe: {salida}. Elegir una carpeta nueva.')
    cfg_base=leer_json(RAIZ/'config/interfaz_v1.json')
    s=cargar_huellas(cfg_base['huellas'])
    modelo_actual=RAIZ/s['carpeta']
    antes={p.name:sha_archivo(p) for p in modelo_actual.iterdir() if p.is_file()}
    nombres=nombres_caracteristicas(s['cfg_ext'])
    xn,fn=cargar_anguli(diagnostico,nombres)
    xo,fo=cargar_anteriores(s)
    X=np.vstack([xo,xn]);filas=fo+fn
    y=np.asarray([r['identidad'] for r in filas])
    train=np.asarray([r['particion']=='entrenamiento' for r in filas])
    if train.sum()!=180 or any(r['grupo']!='autorizado' for r in filas if r['particion']=='entrenamiento'):
        raise ValueError('Se requieren 180 autorizadas para el ajuste combinado.')
    config=leer_json(RAIZ/'config/mejora_huellas_v1.json')
    # Plan anterior, fijado antes de consultar validación: 144/72/36 y cinco pliegues.
    cantidad,cv,detalle,pliegues=elegir_con_cv(X[train],y[train],nombres,config)
    ajustado=ajustar(X[train],y[train],nombres,cantidad,config)
    modelo=dict(indices=ajustado['indices'],nombres=np.asarray(nombres),
        nombres_seleccionados=np.asarray(ajustado['nombres_seleccionados']),
        media=ajustado['escalador'].mean_,escala=ajustado['escalador'].scale_,
        centroides=ajustado['kmeans'].cluster_centers_,
        correspondencia={str(g):i for g,i in ajustado['correspondencia'].items()})
    val=~train;fv=[r for r,ok in zip(filas,val) if ok]
    dist,_=medir_distancias(X[val],nombres,modelo)
    umbral,curva=elegir_umbral(dist,np.asarray([r['grupo']=='autorizado' for r in fv]))
    nuevos=decidir_acceso(X[val],nombres,modelo,umbral['umbral'])
    viejos=decidir_acceso(X[val],nombres,s['modelo'],s['umbral'])
    ma,mb=metricas(fv,nuevos),metricas(fv,viejos)
    if antes!={p.name:sha_archivo(p) for p in modelo_actual.iterdir() if p.is_file()}:
        raise RuntimeError('Cambió un archivo del modelo vigente.')
    # Registro de correspondencia con la evidencia anterior, sin leer prueba.
    evidencia={r['muestra']:float(r['distancia']) for r in
               leer_csv(modelo_actual/'decisiones_validacion.csv')}
    for r,d in zip(fv,viejos):
        if r['fuente']=='anterior' and abs(d['distancia']-evidencia[r['muestra']])>1e-9:
            raise ValueError('Las entradas anteriores no reproducen la evidencia congelada.')
    salida.mkdir(parents=True)
    carpeta=salida/'modelo';carpeta.mkdir()
    np.savez_compressed(carpeta/'modelo_congelado.npz',**{k:v for k,v in modelo.items() if k!='correspondencia'})
    guardar_json(carpeta/'correspondencia_congelada.json',modelo['correspondencia'])
    guardar_json(carpeta/'umbral.json',umbral)
    hashes={p.name:sha_archivo(p) for p in carpeta.iterdir()}
    resumen=dict(fecha_utc=fecha,tipo='anguli_combinado_experimental_v1',python=platform.python_version(),
        dependencias={p:importlib.metadata.version(p) for p in ('numpy','scipy','Pillow','scikit-learn')},
        columnas_entrada=144,columnas_utilizadas=cantidad,cv=cv,config=config,
        muestras_entrenamiento=dict(anterior=120,anguli=60),
        ponderacion='Cada captura pesa uno: anterior 2/3, Anguli 1/3; sin duplicación ni sobremuestreo.',
        validacion_modelo_anterior=mb,validacion_modelo_combinado=ma,resultado_calibracion=umbral,
        control_evaluado=False,prueba_final_evaluada=False,modelo_actual_modificado=False,
        advertencia='Validación usada para calibrar, no evaluación independiente; bases conocidas y correlacionadas.',
        entradas_sha256={p.name:sha_archivo(p) for p in diagnostico.iterdir() if p.is_file()},
        metadatos_anteriores_sha256=sha_archivo(RAIZ/'datos/metadatos_con_rotaciones_train_v1.csv'),
        codigo_sha256=sha_archivo(__file__),archivos_sha256=hashes)
    guardar_json(carpeta/'resumen.json',resumen)
    # Metadatos de selección con el mismo contrato que el adaptador existente.
    texto=json.dumps(s['cfg_ext'],ensure_ascii=False,indent=2,allow_nan=False)
    seleccion=dict(columnas_elegidas=cantidad,seleccion_supervisada=True,cv=cv,
        archivos_sha256={'seleccionada/parametros.npz':hashes['modelo_congelado.npz'],
                        'config_extractor_efectiva.json':hashlib.sha256(texto.encode()).hexdigest()})
    guardar_json(salida/'seleccion.json',seleccion)
    cfg=json.loads(json.dumps(cfg_base))
    try:
        ruta=salida.relative_to(RAIZ).as_posix()
    except ValueError:
        ruta=salida.as_posix()
    cfg['huellas']['modelo']=ruta+'/modelo'
    cfg['huellas']['seleccion']=ruta+'/seleccion.json'
    guardar_json(salida/'config_interfaz_experimental.json',cfg)
    escribir_csv(salida/'manifiesto_anguli.csv',leer_csv(diagnostico/'manifiesto.csv'))
    escribir_csv(salida/'catalogo_desarrollo.csv',filas)
    escribir_csv(salida/'comparacion_cv.csv',cv)
    escribir_csv(salida/'detalle_cv.csv',detalle)
    train_filas=[r for r,ok in zip(filas,train) if ok]
    escribir_csv(salida/'pliegues_cv.csv',[dict(muestra=train_filas[r['fila_train']]['muestra'],
        fuente=train_filas[r['fila_train']]['fuente'],pliegue=r['pliegue_interno']) for r in pliegues])
    escribir_csv(salida/'curva_umbral.csv',curva)
    consultas=[]
    for r,a,b in zip(fv,nuevos,viejos):
        consultas.append(dict(r,distancia=a['distancia'],aceptada=a['aceptada'],identidad_predicha=a['identidad'],
            distancia_anterior=b['distancia'],aceptada_anterior=b['aceptada'],identidad_anterior=b['identidad']))
    escribir_csv(salida/'comparacion_validacion.csv',consultas)
    print(f'Modelo combinado: {cantidad}/144 características; 180 muestras de entrenamiento.')
    print(f"Umbral experimental: {umbral['umbral']:.12f}")
    for r in ma:
        print(f"{r['fuente']} / {r['grupo']}: {r['n']} consultas; {r['aceptadas']} aceptadas; "
              f"{r['identificadas_correctamente']} identificaciones correctas")
    print('Modelo anterior intacto. Control Anguli y prueba final sin evaluar.')
    print('Configuración:',salida/'config_interfaz_experimental.json')
    return salida


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--diagnostico',type=Path,required=True,help='Carpeta que contiene los cuatro archivos del diagnóstico.')
    p.add_argument('--salida',type=Path,help='Carpeta nueva para modelo y evidencia; por defecto corrida fechada en experimentos.')
    a=p.parse_args()
    try:
        ejecutar(a.diagnostico,a.salida)
    except (OSError,ValueError,KeyError) as e:
        p.exit(1,f'No se completó el ajuste experimental: {e}\nNo se reemplazó el modelo vigente.\n')
