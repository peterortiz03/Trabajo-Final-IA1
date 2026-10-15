"""Añade 10 impresiones por autorizado. Solo generación: sin normalización."""
import argparse
import csv
import json
import platform
import sys
from pathlib import Path
import numpy as np
from PIL import Image
import PIL
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from generar_conjunto import (hash_archivo, json_guardar, rng_muestra,
                              verificar_bases, simular_captura)
from piloto_deformaciones import generar_muestra

RAIZ = Path(__file__).resolve().parents[1]
VERSION = 'ampliacion-train-1.0.0'


def crear(base, semilla, perfil):
    rng = rng_muestra(semilla, 11)
    semilla_local = int(rng.integers(0, 2**32, dtype=np.uint64))
    local = dict(nombre=perfil['nombre'], amplitud_px=float(rng.uniform(*perfil['amplitud_local_px'])),
        rotacion_max_grados=perfil['rotacion_max_grados'], traslacion_max_px=perfil['traslacion_max_px'],
        desenfoque_sigma_px=0, ruido_sigma_gris=0)
    deformada, params, _, _ = generar_muestra(base, semilla_local, local)
    original, captura = simular_captura(deformada, semilla, perfil)
    return original, dict(semilla_deformacion=semilla_local, deformacion=params, captura=captura)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nombre', default='ampliacion_train_v1')
    args = parser.parse_args()
    if not args.nombre.replace('_','').replace('-','').isalnum(): raise ValueError('Nombre inválido.')
    conf = json.loads((RAIZ/'config/conjunto_v1.json').read_text(encoding='utf-8-sig'))
    extra = json.loads((RAIZ/'config/ampliacion_train_v1.json').read_text(encoding='utf-8-sig'))
    bases, fuentes = verificar_bases(conf)
    meta_anterior = RAIZ/'datos/metadatos.csv'
    with meta_anterior.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f); columnas = reader.fieldnames; anteriores = list(reader)
    if len(anteriores)!=160: raise ValueError('Se esperaba el catálogo original de 160 muestras.')
    autorizados = [i for i in conf['identidades'] if i['grupo']=='autorizado']
    if len(autorizados)!=3: raise ValueError('Se esperaban tres autorizados.')
    for ident in autorizados:
        if sum(r['identidad']==ident['id'] and r['particion']=='entrenamiento' for r in anteriores)!=20:
            raise ValueError('La cantidad de entrenamiento previa no coincide con el plan.')
    origdir = RAIZ/'datos/originales'/args.nombre
    reportdir = RAIZ/'resultados'/args.nombre
    meta_nuevo = RAIZ/'datos'/f'metadatos_{args.nombre}.csv'
    combinado = RAIZ/'datos'/f'metadatos_con_{args.nombre}.csv'
    for p in [origdir, reportdir, meta_nuevo, combinado]:
        if p.exists(): raise FileExistsError(f'Ya existe {p}. No se sobrescribe; usá --nombre con otro nombre.')
    # Solo integridad: leer originales previos no implica evaluar el reconocedor ni mostrar prueba.
    previos = {}
    for r in anteriores:
        p = RAIZ/r['original']
        if hash_archivo(p)!=r['sha256_original']: raise ValueError(f'Original previo modificado: {r["muestra"]}')
        with Image.open(p) as im: previos[r['muestra']] = np.array(im.convert('L'))
    origdir.mkdir(parents=True); reportdir.mkdir(parents=True)
    json_guardar(reportdir/'config_efectiva.json', extra)
    json_guardar(reportdir/'fuentes.json', fuentes)
    json_guardar(reportdir/'entorno.json', dict(version=VERSION, python=platform.python_version(),
        sistema=platform.platform(), numpy=np.__version__, scipy=scipy.__version__, pillow=PIL.__version__,
        matplotlib=matplotlib.__version__, rng='PCG64/SeedSequence',
        sha256_metadatos_anteriores=hash_archivo(meta_anterior),
        codigo={p.name:hash_archivo(p) for p in [Path(__file__),RAIZ/'src/generar_conjunto.py',RAIZ/'src/piloto_deformaciones.py']}))
    nuevas, imagenes, alertas = [], {}, []
    for ident in autorizados:
        for j in range(10):
            nombre = f"{ident['id']}_M{41+j:02d}"
            semilla = 900000 + ident['indice_semillas']*1000+j
            if any(r['muestra']==nombre or int(r['semilla_muestra'])==semilla for r in anteriores):
                raise ValueError('Colisión de identificador o semilla.')
            perfil = extra['perfiles'][j//2]
            arr, params = crear(bases[ident['id']], semilla, perfil)
            repetida, _ = crear(bases[ident['id']], semilla, perfil)
            if not np.array_equal(arr, repetida): raise ValueError('Falló la repetibilidad.')
            if not .05 < np.mean(arr<128) < .7: raise ValueError(f'Contenido anómalo: {nombre}')
            for r in anteriores+nuevas:
                otra = previos[r['muestra']] if r['muestra'] in previos else imagenes[r['muestra']]
                if np.array_equal(arr, otra): raise ValueError(f'Duplicado exacto: {nombre}, {r["muestra"]}')
                if r['identidad']==ident['id']:
                    diferencia = float(np.mean((arr[50:350,35:240]<128)!=(otra[50:350,35:240]<128)))
                    if diferencia<.015: alertas.append([nombre,r['muestra'],diferencia])
            path = origdir/'entrenamiento'/ident['id']/(nombre+'.png')
            path.parent.mkdir(parents=True,exist_ok=True); Image.fromarray(arr).save(path)
            fila = dict(identidad=ident['id'],grupo='autorizado',muestra=nombre,particion='entrenamiento',
                reserva_demo=False,base=ident['base'],sha256_base=ident['sha256_base'],
                tipo_morfologico=ident['tipo_morfologico'],generador_base='Anguli',
                version_anguli='no indicada en About',semilla_base=ident['semilla_base'],config_anguli=ident['config_anguli'],
                generador_variantes=VERSION,semilla_muestra=semilla,perfil=perfil['nombre'],
                parametros_json=json.dumps(params,ensure_ascii=False),
                preprocesamiento_json=json.dumps({'aplicado':False,'motivo':'Solo generación; normalización pendiente'}),
                original=path.relative_to(RAIZ).as_posix(),procesado='',sha256_original=hash_archivo(path),sha256_procesado='',
                jacobiano_min=params['deformacion']['jacobiano_muestreo_min'],
                jacobiano_max=params['deformacion']['jacobiano_muestreo_max'],
                entorno=(reportdir/'entorno.json').relative_to(RAIZ).as_posix())
            nuevas.append(fila);imagenes[nombre]=arr
    for path, filas in [(meta_nuevo,nuevas),(combinado,anteriores+nuevas)]:
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=columnas);writer.writeheader();writer.writerows(filas)
    fig,axs=plt.subplots(3,5,figsize=(13,13),squeeze=False)
    for row,ident in enumerate(autorizados):
        for col,perfil in enumerate(extra['perfiles']):
            nombre=f"{ident['id']}_M{41+2*col:02d}"
            axs[row,col].imshow(imagenes[nombre],cmap='gray',vmin=0,vmax=255)
            axs[row,col].set_title(f"{nombre}\n{perfil['nombre']}",fontsize=9);axs[row,col].axis('off')
    fig.suptitle('Ampliación de entrenamiento: originales, sin normalizar (una de cada par)')
    fig.tight_layout(rect=(0,0,1,.96));fig.savefig(reportdir/'comparacion_ampliacion.png',dpi=130);plt.close(fig)
    informe = dict(nuevas=30,nuevas_por_identidad=10,entrenamiento_total=90,total_muestras=190,
        validacion=50,prueba=50,normalizacion_aplicada=False,duplicados_exactos=0,
        repeticion_exacta_por_muestra=True,candidatos_casi_duplicados=alertas,
        criterio_casi_duplicados='ROI central binarizada, diferencia <1.5%; sin alineación, solo cribado',
        bytes_imagenes=sum(p.stat().st_size for p in origdir.rglob('*.png')),
        catalogo_combinado=combinado.relative_to(RAIZ).as_posix())
    json_guardar(reportdir/'verificacion.json',informe)
    print('OK: 30 originales nuevos, 10 por autorizado. Sin normalización.')
    print('Total: 90 entrenamiento + 50 validación + 50 prueba = 190 muestras.')
    print(f'Catálogo completo: {combinado}')
    print(f'Revisión visual: {reportdir}')
    if alertas: print('REVISAR candidatos casi duplicados en verificacion.json antes de incorporar.')


if __name__=='__main__':
    try: main()
    except (ValueError,FileNotFoundError,FileExistsError) as e: sys.exit(f'ERROR: {e}')
