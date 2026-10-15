"""30 originales adicionales de entrenamiento con rotaciones, sin normalización."""
import argparse
import csv
import json
import platform
import sys
from pathlib import Path
import numpy as np
import scipy
from scipy.ndimage import rotate
import PIL
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ampliar_entrenamiento import crear
from generar_conjunto import hash_archivo, json_guardar, verificar_bases

RAIZ = Path(__file__).resolve().parents[1]
ANGULOS = [-90,-60,-45,-30,-15,15,30,45,60,90]
PERFIL = dict(nombre='rotacion_amplia', amplitud_local_px=[2,4], rotacion_max_grados=0,
    traslacion_max_px=2, contraste=[.85,1], desenfoque_sigma=[.15,.3], ruido_sigma=[.8,1.5],recorte_borde=False)


def generar_rotada(base, semilla, angulo):
    captura, parametros = crear(base,semilla,PERFIL)
    # Lienzo mayor sin reescalar: diagonal de 275x400 ≈485.4, menor que 512.
    lienzo = np.full((512,512),255,dtype=np.uint8)
    h,w = captura.shape
    y0,x0 = (512-h)//2,(512-w)//2
    lienzo[y0:y0+h,x0:x0+w] = captura
    # Los múltiplos de 90 no requieren interpolación. Los restantes usan una sola
    # interpolación lineal para esta rotación final, con fondo blanco.
    if abs(angulo)==90:
        resultado = np.rot90(lienzo,1 if angulo>0 else -1).copy()
    else:
        resultado = np.clip(np.rint(rotate(lienzo.astype(float),angulo,reshape=False,
                            order=1,mode='constant',cval=255,prefilter=False)),0,255).astype(np.uint8)
    parametros['rotacion_final'] = dict(grados=angulo,positivo='antihorario',
        lienzo_ancho_alto=[512,512],origen_en_lienzo_x_y=[x0,y0],reescala=False,
        centro_rotacion_x_y=[255.5,255.5],interpolacion='sin interpolacion' if abs(angulo)==90 else 'lineal')
    return resultado,parametros


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nombre',default='rotaciones_train_v1')
    args=parser.parse_args()
    if not args.nombre.replace('_','').replace('-','').isalnum():raise ValueError('Nombre inválido.')
    conf=json.loads((RAIZ/'config/conjunto_v1.json').read_text(encoding='utf-8-sig'))
    bases,fuentes=verificar_bases(conf)
    previo=RAIZ/'datos/metadatos_con_ampliacion_train_v1.csv'
    with previo.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);columnas=reader.fieldnames;anteriores=list(reader)
    if len(anteriores)!=190:raise ValueError('Se esperaba el catálogo de 190 muestras tras la primera ampliación.')
    autorizados=[i for i in conf['identidades'] if i['grupo']=='autorizado']
    if len(autorizados)!=3:raise ValueError('Se esperaban tres autorizados.')
    for ident in autorizados:
        if sum(r['identidad']==ident['id'] and r['particion']=='entrenamiento' for r in anteriores)!=30:
            raise ValueError('Se esperaban 30 muestras previas de entrenamiento por autorizado.')
    origdir=RAIZ/'datos/originales'/args.nombre
    reportdir=RAIZ/'resultados'/args.nombre
    meta=RAIZ/'datos'/f'metadatos_{args.nombre}.csv'
    completo=RAIZ/'datos'/f'metadatos_con_{args.nombre}.csv'
    for p in [origdir,reportdir,meta,completo]:
        if p.exists():raise FileExistsError(f'Ya existe {p}. Usá --nombre con otro destino nuevo.')
    for r in anteriores:
        if hash_archivo(RAIZ/r['original'])!=r['sha256_original']:
            raise ValueError(f'Original anterior modificado: {r["muestra"]}')
    origdir.mkdir(parents=True);reportdir.mkdir(parents=True)
    json_guardar(reportdir/'config_efectiva.json',dict(angulos=ANGULOS,perfil=PERFIL,lienzo=[512,512],normalizacion=False))
    json_guardar(reportdir/'fuentes.json',fuentes)
    json_guardar(reportdir/'entorno.json',dict(python=platform.python_version(),sistema=platform.platform(),
        numpy=np.__version__,scipy=scipy.__version__,pillow=PIL.__version__,matplotlib=matplotlib.__version__,
        sha256_catalogo_previo=hash_archivo(previo),codigo={n:hash_archivo(RAIZ/'src'/n) for n in
        ['ampliar_rotaciones.py','ampliar_entrenamiento.py','generar_conjunto.py','piloto_deformaciones.py']}))
    nuevas,imagenes=[],{}
    for ident in autorizados:
        for j,angulo in enumerate(ANGULOS):
            nombre=f"{ident['id']}_M{51+j:02}"
            semilla=1900000+ident['indice_semillas']*1000+j
            if any(r['muestra']==nombre or int(r['semilla_muestra'])==semilla for r in anteriores):
                raise ValueError('Colisión de identificador o semilla.')
            arr,params=generar_rotada(bases[ident['id']],semilla,angulo)
            otra,_=generar_rotada(bases[ident['id']],semilla,angulo)
            if not np.array_equal(arr,otra):raise ValueError('Falló la repetición.')
            # El marco permanece blanco salvo el ruido leve del fondo nativo.
            borde=np.concatenate([arr[0],arr[-1],arr[:,0],arr[:,-1]])
            if np.any(borde<250):raise ValueError(f'Contenido alcanza el borde: {nombre}')
            if not .02<np.mean(arr<128)<.5:raise ValueError(f'Contenido anómalo: {nombre}')
            if any(np.array_equal(arr,a) for a in imagenes.values()):raise ValueError('Duplicado exacto.')
            path=origdir/'entrenamiento'/ident['id']/(nombre+'.png')
            path.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(arr).save(path)
            fila=dict(identidad=ident['id'],grupo='autorizado',muestra=nombre,particion='entrenamiento',reserva_demo=False,
                base=ident['base'],sha256_base=ident['sha256_base'],tipo_morfologico=ident['tipo_morfologico'],
                generador_base='Anguli',version_anguli='no indicada en About',semilla_base=ident['semilla_base'],
                config_anguli=ident['config_anguli'],generador_variantes='rotaciones-train-1.0.0',semilla_muestra=semilla,
                perfil=f'rotacion_{angulo:+d}_grados',parametros_json=json.dumps(params,ensure_ascii=False),
                preprocesamiento_json=json.dumps({'aplicado':False,'motivo':'Original de captura simulada; normalización pendiente'}),
                original=path.relative_to(RAIZ).as_posix(),procesado='',sha256_original=hash_archivo(path),sha256_procesado='',
                jacobiano_min=params['deformacion']['jacobiano_muestreo_min'],jacobiano_max=params['deformacion']['jacobiano_muestreo_max'],
                entorno=(reportdir/'entorno.json').relative_to(RAIZ).as_posix())
            nuevas.append(fila);imagenes[nombre]=arr
    for p,filas in [(meta,nuevas),(completo,anteriores+nuevas)]:
        with p.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=columnas);writer.writeheader();writer.writerows(filas)
    for ident in autorizados:
        fig,axs=plt.subplots(2,5,figsize=(13,6))
        for j,(ax,angulo) in enumerate(zip(axs.flat,ANGULOS)):
            nombre=f"{ident['id']}_M{51+j:02}"
            ax.imshow(imagenes[nombre],cmap='gray',vmin=0,vmax=255);ax.axis('off');ax.set_title(f'{nombre}: {angulo:+d}°')
        fig.suptitle(f"{ident['id']} — originales de entrenamiento; sin normalización")
        fig.tight_layout(rect=(0,0,1,.94));fig.savefig(reportdir/f'rotaciones_{ident["id"]}.png',dpi=140);plt.close(fig)
    json_guardar(reportdir/'verificacion.json',dict(nuevas=30,nuevas_por_identidad=10,total=220,
        entrenamiento=120,validacion=50,prueba=50,repeticion_exacta=True,duplicados_exactos_nuevos=0,
        control_bordes='sin contenido oscuro en el marco del lienzo',normalizacion=False,
        dimensiones_nuevas=[512,512],reescala=False,
        limite_control_duplicados='No se detectan casi duplicados con alineación; tamaño distinto de los originales anteriores.',
        bytes_imagenes=sum(p.stat().st_size for p in origdir.rglob('*.png'))))
    print('OK: 30 originales nuevos, 10 por autorizado; sin normalización.')
    print('Total: 120 entrenamiento + 50 validación + 50 prueba = 220 muestras.')
    print(f'Catálogo completo: {completo}')
    print(f'Comparaciones: {reportdir}')


if __name__=='__main__':
    try:main()
    except (ValueError,FileNotFoundError,FileExistsError) as e:sys.exit(f'ERROR: {e}')
