"""Diagnóstico reproducible de preparación, con modelo congelado y desarrollo.

Plan fijo: base limpia, contacto, contacto+calidad y procedimiento completo.
No busca semillas exitosas, no ajusta umbral y no utiliza bases de prueba.
"""
import argparse
import csv
from datetime import datetime, timezone
import json
import hashlib
import os
import platform
from pathlib import Path

os.environ.setdefault('MPLBACKEND','Agg')
from preparar_captura import (RAIZ, cargar_preparador, abrir_base, preparar_captura,
                             huella_pixeles, leer_json)
from interfaz_servicios import cargar_huellas, evaluar_huella


def ejecutar(salida=None):
    from generar_conjunto import simular_captura
    import numpy as np
    from PIL import Image
    preparador = cargar_preparador()
    sistema = cargar_huellas(leer_json(RAIZ/'config/interfaz_v1.json')['huellas'])
    modelo_dir=RAIZ/sistema['carpeta']
    def hashes_modelo():
        return {n:hashlib.sha256((modelo_dir/n).read_bytes()).hexdigest() for n in
                ('modelo_congelado.npz','umbral.json','correspondencia_congelada.json')}
    modelo_antes=hashes_modelo()
    plan = preparador['config']['semillas_verificacion']
    cfg = leer_json(RAIZ/preparador['config']['config_generador'])
    # Se leen solo las 3 autorizadas y los 2 intrusos de validación.
    identidades = [i for i in cfg['identidades'] if i['grupo']=='autorizado' or i['particion']=='validacion']
    nombre = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    salida = Path(salida) if salida else RAIZ/'resultados/diagnostico_preparacion'/nombre
    if not salida.is_absolute():
        salida = RAIZ/salida
    salida.mkdir(parents=True,exist_ok=False)
    filas=[]
    def medir(imagen, ident, condicion, perfil='', semilla=''):
        fila=dict(identidad_real=ident['id'],grupo_real=ident['grupo'],condicion=condicion,
                  perfil=perfil,semilla=semilla,sha256_pixeles=huella_pixeles(imagen))
        try:
            r=evaluar_huella(imagen,sistema)
            fila.update(distancia=r['distancia'],aceptada=r['aceptada'],identidad_predicha=r['identidad'],
                correcta=(r['aceptada'] and r['identidad']==ident['id']) if ident['grupo']=='autorizado' else not r['aceptada'],error='')
        except Exception as e:
            fila.update(distancia='',aceptada='',identidad_predicha='',correcta=False,error=f'{type(e).__name__}: {e}')
        filas.append(fila)
    for ident in identidades:
        base=abrir_base(RAIZ/ident['base'])
        medir(base,ident,'base_limpia')
        for semilla in plan:
            leve=cfg['perfiles'][0]
            contacto=dict(leve,contraste=[1,1],desenfoque_sigma=[0,0],ruido_sigma=[0,0],recorte_borde=False)
            im,_=simular_captura(np.array(base),semilla,contacto)
            medir(Image.fromarray(im),ident,'solo_contacto',semilla=semilla)
            for p in cfg['perfiles']:
                im,_=simular_captura(np.array(base),semilla,p)
                medir(Image.fromarray(im),ident,'contacto_y_calidad',p['nombre'],semilla)
                im,_=preparar_captura(base,p['nombre'],semilla,preparador)
                medir(im,ident,'procedimiento_completo',p['nombre'],semilla)
    with (salida/'consultas.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(filas[0]));w.writeheader();w.writerows(filas)
    if hashes_modelo()!=modelo_antes:
        raise RuntimeError('Cambió un archivo del modelo durante el diagnóstico.')
    resumen=dict(modelo=sistema['identificador'],modelo_sha256=modelo_antes,python=platform.python_version(),
        umbral=sistema['umbral'],semillas=plan,
        codigo=preparador['codigo'],dependencias=preparador['dependencias'],
        entradas=len(filas),identidades=[i['id'] for i in identidades],prueba_utilizada=False,
        modelo_modificado=False,seleccion_semillas_por_resultado=False,resultados=[])
    for condicion in dict.fromkeys(r['condicion'] for r in filas):
        for grupo in ('autorizado','intruso'):
            rs=[r for r in filas if r['condicion']==condicion and r['grupo_real']==grupo]
            resumen['resultados'].append(dict(condicion=condicion,grupo=grupo,n=len(rs),
                aceptadas=sum(r['aceptada'] is True for r in rs),
                correctas=sum(r['correcta'] for r in rs),errores=sum(bool(r['error']) for r in rs)))
    (salida/'resumen.json').write_text(json.dumps(resumen,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(resumen,ensure_ascii=False,indent=2))
    print('Salida:',salida)
    return salida


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida',type=Path,help='Carpeta nueva opcional; por defecto resultados/diagnostico_preparacion/FECHA.')
    args=p.parse_args()
    ejecutar(args.salida)
