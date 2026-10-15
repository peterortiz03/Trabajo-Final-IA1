"""Aplicar configuración fija a originales y conservar particiones e identidades."""
import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
import scipy
import PIL
from PIL import Image
from normalizacion_final import normalizar_huella

RAIZ = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def guardar_json(path, valor):
    path.write_text(json.dumps(valor, ensure_ascii=False, indent=2), encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solo-desarrollo', action='store_true')
    parser.add_argument('--salida', default='normalizacion_final_v1')
    args = parser.parse_args()
    if not args.salida.replace('_','').replace('-','').isalnum():
        raise ValueError('Nombre de salida inválido.')
    catalogo = RAIZ/'datos/metadatos_con_rotaciones_train_v1.csv'
    cfgpath = RAIZ/'config/roi_normalizacion_v1.json'
    cfg = json.loads(cfgpath.read_text(encoding='utf-8-sig'))
    with catalogo.open(encoding='utf-8-sig', newline='') as f:
        filas = list(csv.DictReader(f))
    if args.solo_desarrollo:
        filas = [r for r in filas if r['particion'] in ['entrenamiento','validacion']]
    esperado = 170 if args.solo_desarrollo else 220
    if len(filas) != esperado or len({r['muestra'] for r in filas}) != esperado:
        raise ValueError(f'Se esperaban {esperado} muestras distintas. Revisá el catálogo.')
    # Verificación previa: no dejar un lote a medias por un original ausente/cambiado.
    for r in filas:
        if sha(RAIZ/r['original']) != r['sha256_original']:
            raise ValueError(f"Original cambiado: {r['muestra']}")
    out = RAIZ/'datos/procesados'/args.salida
    if out.exists():
        raise FileExistsError(f'Ya existe {out}; usá --salida con otro nombre.')
    out.mkdir(parents=True)
    guardar_json(out/'config_efectiva.json', dict(roi=cfg, relacion_autovalores_minima=1.2,
        interpolacion=1, contraste_modificado=False, ambiguedad_180=True))
    guardar_json(out/'entorno.json', dict(python=platform.python_version(), numpy=np.__version__,
        scipy=scipy.__version__, pillow=PIL.__version__, sha256_catalogo=sha(catalogo),
        sha256_config=sha(cfgpath), codigo={n:sha(RAIZ/'src'/n) for n in
        ['roi_normalizacion_v1.py','normalizacion_final.py','normalizar_todas.py']}))
    detalles, nuevas = [], []
    seleccion = {'A01_M21','A01_M43','A02_M44','I01_M01','I02_M01'} | {f'A01_M{n}' for n in range(51,61)}
    for r in filas:
        nombre = r['muestra']
        row = dict(r, normalizada='', alternativa_180='', sha256_normalizada='',
                   sha256_alternativa_180='', estado_normalizacion='error')
        with Image.open(RAIZ/r['original']) as imagen:
            original = imagen.copy()
        try:
            normal, info = normalizar_huella(original, cfg)
            mask = info.pop('mascara_normalizada')
            alternativa = info.pop('alternativa_180')
            carpeta = out/r['particion']/r['identidad']
            carpeta.mkdir(parents=True, exist_ok=True)
            for sufijo, array in [('',normal),('_180',alternativa),('_mascara',mask.astype(np.uint8)*255)]:
                Image.fromarray(array).save(carpeta/f'{nombre}{sufijo}.png')
            path, alt = carpeta/f'{nombre}.png', carpeta/f'{nombre}_180.png'
            estado = 'revisar' if info['avisos'] else 'ok'
            row.update(normalizada=path.relative_to(RAIZ).as_posix(),
                alternativa_180=alt.relative_to(RAIZ).as_posix(),
                sha256_normalizada=sha(path), sha256_alternativa_180=sha(alt), estado_normalizacion=estado)
            detalles.append(dict(muestra=nombre, particion=r['particion'], estado=estado, **info))
            # Comparaciones únicamente de desarrollo, nunca de prueba.
            if nombre in seleccion and r['particion'] != 'prueba':
                panel = Image.new('RGB',(1536,544),'white')
                from PIL import ImageDraw
                draw = ImageDraw.Draw(panel)
                for k,(im,titulo) in enumerate([(original.convert('L'),'Original'),(Image.fromarray(normal),'Normalizada'),(Image.fromarray(alternativa),'Alternativa 180')]):
                    panel.paste(im,(k*512+(512-im.width)//2,32+(512-im.height)//2))
                    draw.text((k*512+12,8),f'{nombre}: {titulo}',fill='black')
                (out/'comparaciones_desarrollo').mkdir(exist_ok=True)
                panel.save(out/'comparaciones_desarrollo'/f'{nombre}.png')
        except ValueError as e:
            detalles.append(dict(muestra=nombre, particion=r['particion'], estado='error', detalle=str(e)))
        nuevas.append(row)
    with (out/'catalogo_normalizado.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=list(nuevas[0])); writer.writeheader(); writer.writerows(nuevas)
    guardar_json(out/'detalle.json', detalles)
    resumen = dict(solicitadas=len(filas), correctas=sum(r['estado']=='ok' for r in detalles),
        revisar=sum(r['estado']=='revisar' for r in detalles), errores=sum(r['estado']=='error' for r in detalles),
        particiones={p:sum(r['particion']==p for r in filas) for p in ['entrenamiento','validacion','prueba']},
        ambiguedad_180=True, contraste_modificado=False)
    guardar_json(out/'resumen.json', resumen)
    print(json.dumps(resumen, indent=2)); print(f'Resultados: {out}')
    if resumen['errores']:
        raise SystemExit('Hay errores: revisar detalle.json antes de usar este lote.')

if __name__ == '__main__':
    main()
