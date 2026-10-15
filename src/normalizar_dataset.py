"""Prueba de ROI/centrado exclusivamente sobre desarrollo. Nunca procesa prueba."""
import argparse,csv,json,hashlib,platform
from pathlib import Path
import numpy as np
import scipy,PIL,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from normalizacion import normalizar_huella

RAIZ=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--todas-desarrollo',action='store_true',help='Procesar 170 de entrenamiento/validación, nunca prueba.')
    ap.add_argument('--salida',default='normalizacion_etapa1')
    args=ap.parse_args()
    if not args.salida.replace('_','').replace('-','').isalnum():raise ValueError('Nombre de salida inválido.')
    cfgpath=RAIZ/'config/normalizacion_etapa1.json'
    cfg=json.loads(cfgpath.read_text(encoding='utf-8-sig'))
    catalogo=RAIZ/'datos/metadatos_con_rotaciones_train_v1.csv'
    with catalogo.open(encoding='utf-8-sig',newline='') as f:filas=list(csv.DictReader(f))
    # Selección explícita por ID para cubrir tipos de captura, no por desempeño.
    seleccion={f'{id}_M{n:02}' for id in ['A01','A02','A03'] for n in [21,41,45,47,51,55]}|{'I01_M01','I02_M01'}
    filas=[r for r in filas if r['particion'] in ['entrenamiento','validacion'] and r['reserva_demo'].lower()!='true'
           and (args.todas_desarrollo or r['muestra'] in seleccion)]
    esperado=170 if args.todas_desarrollo else 20
    if len(filas)!=esperado:raise ValueError(f'Se esperaban {esperado} imágenes de desarrollo, encontradas {len(filas)}. Revisá el catálogo.')
    out=RAIZ/'resultados'/args.salida
    if out.exists():raise FileExistsError(f'Ya existe {out}. Usá --salida con otro nombre nuevo.')
    out.mkdir(parents=True)
    for nombre in ['imagenes','mascaras','comparaciones']:(out/nombre).mkdir()
    (out/'config_efectiva.json').write_text(json.dumps(cfg,indent=2),encoding='utf8')
    entorno=dict(python=platform.python_version(),sistema=platform.platform(),numpy=np.__version__,
        scipy=scipy.__version__,pillow=PIL.__version__,matplotlib=matplotlib.__version__,
        sha256_config=sha(cfgpath),sha256_catalogo=sha(catalogo),
        codigo={n:sha(RAIZ/'src'/n) for n in ['normalizacion.py','normalizar_dataset.py']})
    (out/'entorno.json').write_text(json.dumps(entorno,indent=2),encoding='utf8')
    registros,visuales=[],[]
    for r in filas:
        path=RAIZ/r['original'];nombre=r['muestra']
        if sha(path)!=r['sha256_original']:raise ValueError(f'Cambió el original {nombre}.')
        with Image.open(path) as im:original=np.array(im.convert('L'))
        try:
            normal,info=normalizar_huella(original,cfg)
        except ValueError as e:
            registros.append(dict(muestra=nombre,particion=r['particion'],estado='error',detalle=str(e)))
            continue
        mascara=info.pop('mascara_original');mask_out=info.pop('mascara_normalizada')
        Image.fromarray(normal).save(out/'imagenes'/f'{nombre}.png')
        Image.fromarray(mascara.astype(np.uint8)*255).save(out/'mascaras'/f'{nombre}_entrada.png')
        Image.fromarray(mask_out.astype(np.uint8)*255).save(out/'mascaras'/f'{nombre}_salida.png')
        estado='revisar' if info['avisos'] else 'ok'
        registros.append(dict(muestra=nombre,particion=r['particion'],estado=estado,original=r['original'],
            normalizada=f'imagenes/{nombre}.png',sha256_original=sha(path),sha256_normalizada=sha(out/'imagenes'/f'{nombre}.png'),**info))
        # En ejecución amplia, mostrar solo las mismas 20 preseleccionadas.
        if nombre in seleccion:visuales.append((nombre,original,mascara,normal,estado))
    for page,start in enumerate(range(0,len(visuales),5),1):
        batch=visuales[start:start+5]
        fig,axs=plt.subplots(len(batch),3,figsize=(10,3.4*len(batch)),squeeze=False)
        for row,(nombre,original,mask,normal,estado) in enumerate(batch):
            for col,(arr,title) in enumerate([(original,'Original + contorno detectado'),(mask.astype(np.uint8)*255,'Máscara de la región'),(normal,'Centrada; ángulo conservado')]):
                ax=axs[row,col];ax.imshow(arr,cmap='gray',vmin=0,vmax=255)
                if col==0:ax.contour(mask,levels=[.5],colors=['#0088cc'],linewidths=.7)
                if col==2:
                    ax.axhline(255.5,color='#cc5555',lw=.5,ls=':');ax.axvline(255.5,color='#cc5555',lw=.5,ls=':')
                ax.set_xlim(-.5,511.5);ax.set_ylim(511.5,-.5);ax.set_facecolor('white')
                ax.set_title(f'{nombre} — {title}\nEstado: {estado}',fontsize=9);ax.axis('off')
        fig.suptitle('Etapa 1: ROI y centrado — misma escala de píxeles en todos los paneles')
        fig.tight_layout(rect=(0,0,1,.965));fig.savefig(out/'comparaciones'/f'pagina_{page:02}.png',dpi=120);plt.close(fig)
    (out/'detalle.json').write_text(json.dumps(registros,indent=2,ensure_ascii=False),encoding='utf8')
    resumen=dict(solicitadas=len(filas),correctas=sum(r['estado']=='ok' for r in registros),
        revisar=sum(r['estado']=='revisar' for r in registros),errores=sum(r['estado']=='error' for r in registros),
        prueba_procesada=False,orientacion_corregida=False,escala_modificada=False,
        normalizacion_completa=False)
    (out/'resumen.json').write_text(json.dumps(resumen,indent=2),encoding='utf8')
    print(json.dumps(resumen,indent=2));print(f'Resultados: {out}')


if __name__=='__main__':
    try:main()
    except (ValueError,FileNotFoundError,FileExistsError) as e:raise SystemExit(f'ERROR: {e}')
