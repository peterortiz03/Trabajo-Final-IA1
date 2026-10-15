"""Piloto de deformaciones locales. No entrena ni reconoce identidades."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import scipy
from scipy.ndimage import map_coordinates, gaussian_filter
import PIL
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

VERSION = 'piloto-0.1.0'
RAIZ = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def guardar_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def generar_muestra(base, semilla, perfil):
    """Mapeo inverso: para cada píxel de salida se consulta una posición de origen.

    Suma de desplazamientos gaussianos locales, suaves y no uniformes.
    La amplitud es un máximo del campo de muestreo, NO presión física.
    Se limita la norma del gradiente para evitar deformaciones excesivas.
    """
    rng = np.random.Generator(np.random.PCG64(semilla))
    h, w = base.shape
    y, x = np.mgrid[:h, :w].astype(float)
    dx, dy = np.zeros_like(x), np.zeros_like(y)
    nodos = []
    for _ in range(5):
        cx, cy = rng.uniform(.2, .8)*w, rng.uniform(.2, .8)*h
        sigma = rng.uniform(32, 65)
        ax, ay = rng.normal(size=2)
        g = np.exp(-((x-cx)**2+(y-cy)**2)/(2*sigma**2))
        dx += ax*g
        dy += ay*g
        nodos.append(dict(cx=float(cx), cy=float(cy), sigma_px=float(sigma),
                          peso_x=float(ax), peso_y=float(ay)))
    # El desplazamiento local se anula suavemente en el borde del lienzo.
    borde = np.sin(np.pi*x/(w-1))**2 * np.sin(np.pi*y/(h-1))**2
    dx *= borde
    dy *= borde
    factor = perfil['amplitud_px']/max(float(np.hypot(dx, dy).max()), 1e-12)
    dx *= factor
    dy *= factor
    dxy, dxx = np.gradient(dx)
    dyy, dyx = np.gradient(dy)
    norma = np.sqrt(dxy**2+dxx**2+dyy**2+dyx**2).max()
    reduccion = min(1., .30/max(float(norma), 1e-12))
    dx *= reduccion
    dy *= reduccion
    # Rotación/traslación pequeñas, compuestas con el campo, una sola interpolación.
    angulo = float(rng.uniform(-perfil['rotacion_max_grados'], perfil['rotacion_max_grados']))
    tx, ty = rng.uniform(-perfil['traslacion_max_px'], perfil['traslacion_max_px'], size=2)
    theta = np.deg2rad(angulo)
    ux, uy = x-(w-1)/2-tx, y-(h-1)/2-ty
    sx = np.cos(theta)*ux+np.sin(theta)*uy+(w-1)/2+dx
    sy = -np.sin(theta)*ux+np.cos(theta)*uy+(h-1)/2+dy
    sy_y, sy_x = np.gradient(sy)
    sx_y, sx_x = np.gradient(sx)
    det = sx_x*sy_y-sx_y*sy_x
    if det.min() <= .5:
        raise ValueError('Deformación excesiva: determinante del mapeo <= 0.5.')
    result = map_coordinates(base.astype(float), [sy, sx], order=1,
                             mode='constant', cval=255, prefilter=False)
    if perfil['desenfoque_sigma_px'] > 0:
        result = gaussian_filter(result, perfil['desenfoque_sigma_px'], mode='constant', cval=255)
    if perfil['ruido_sigma_gris'] > 0:
        result += rng.normal(0, perfil['ruido_sigma_gris'], result.shape)
    result = np.clip(np.rint(result), 0, 255).astype(np.uint8)
    parametros = dict(perfil=perfil, nodos_gaussianos=nodos,
                      normalizacion_campo=float(factor), reduccion_por_gradiente=reduccion,
                      rotacion_grados=angulo, traslacion_x_px=float(tx), traslacion_y_px=float(ty),
                      desplazamiento_local_max_px=float(np.hypot(dx, dy).max()),
                      jacobiano_muestreo_min=float(det.min()), jacobiano_muestreo_max=float(det.max()),
                      interpolacion='lineal, order=1', fondo=255)
    return result, parametros, dx, dy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config/piloto_deformaciones.json')
    parser.add_argument('--salida', default='resultados/piloto_deformaciones')
    parser.add_argument('--muestra', help='Ejemplo: P01_M02. Genera solo esa muestra.')
    args = parser.parse_args()
    conf = json.loads((RAIZ/args.config).read_text(encoding='utf-8-sig'))
    salida = RAIZ/args.salida
    # Salida nueva obligatoria: nunca pisar un experimento ni sus metadatos.
    if salida.exists():
        raise FileExistsError(f'Ya existe {salida}. Usá --salida con otra carpeta nueva.')
    tareas = []
    bases = {}
    for ident in conf['identidades']:
        path = RAIZ/ident['base']
        if not path.is_file():
            raise FileNotFoundError(f'Falta la base: {path}. Revisá el nombre de la carpeta.')
        if sha256(path) != ident['sha256_base']:
            raise ValueError(f'La base {path} no coincide con la revisada. No se modificó ningún archivo.')
        with Image.open(path) as im:
            if im.size != (275, 400):
                raise ValueError(f'Dimensiones inesperadas en {path}: {im.size}')
            bases[ident['id']] = np.array(im.convert('L'))
        for i, perfil in enumerate(conf['perfiles'], 1):
            nombre = f"{ident['id']}_M{i:02d}"
            if args.muestra is None or nombre == args.muestra:
                tareas.append((ident, perfil, nombre, ident['semillas_muestras'][i-1]))
    if not tareas:
        raise ValueError('No existe esa muestra en la configuración.')
    salida.mkdir(parents=True)
    (salida/'imagenes').mkdir()
    entorno = dict(python=platform.python_version(), sistema=platform.platform(),
                   numpy=np.__version__, scipy=scipy.__version__, pillow=PIL.__version__,
                   matplotlib=matplotlib.__version__, generador=VERSION,
                   sha256_codigo=sha256(__file__), rng='NumPy PCG64')
    guardar_json(salida/'entorno.json', entorno)
    guardar_json(salida/'config_efectiva.json', conf)
    filas, visuales, campos = [], {}, []
    for ident, perfil, nombre, semilla in tareas:
        base = bases[ident['id']]
        salida_im, params, dx, dy = generar_muestra(base, semilla, perfil)
        # Verifica aquí la repetición, usando una instancia RNG nueva.
        otra, _, _, _ = generar_muestra(base, semilla, perfil)
        if not np.array_equal(salida_im, otra):
            raise RuntimeError(f'Falló la repetición de {nombre}')
        path = salida/'imagenes'/f'{nombre}.png'
        Image.fromarray(salida_im).save(path)
        fila = dict(identidad=ident['id'], muestra=nombre, particion='desarrollo_piloto',
                    base=ident['base'], sha256_base=ident['sha256_base'],
                    generador_base='Anguli', version_anguli='no_registrada',
                    semilla_base=ident['semilla_base'], configuracion_anguli=ident['config_anguli'],
                    generador_variantes=VERSION, semilla_muestra=semilla, rng='PCG64',
                    perfil=perfil['nombre'], parametros_json=json.dumps(params, ensure_ascii=False),
                    preparacion='L8; 275x400 nativo; sin ROI, reescala ni binarizacion adicional',
                    original=f'imagenes/{nombre}.png', procesado='', sha256_original=sha256(path),
                    jacobiano_min=params['jacobiano_muestreo_min'],
                    jacobiano_max=params['jacobiano_muestreo_max'],
                    repeticion_exacta=True, entorno='entorno.json')
        filas.append(fila)
        visuales.setdefault(ident['id'], []).append((nombre, perfil['nombre'], salida_im))
        campos.append((nombre, dx, dy))
    hashes = [f['sha256_original'] for f in filas]
    if len(hashes) != len(set(hashes)):
        raise RuntimeError('Hay variantes exactamente duplicadas. Revisar antes de avanzar.')
    with (salida/'metadatos_piloto.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(filas[0])); writer.writeheader(); writer.writerows(filas)
    ncols = max(len(v) for v in visuales.values())+1
    fig, axs = plt.subplots(len(visuales), ncols, figsize=(3*ncols, 5*len(visuales)), squeeze=False)
    for row, (ident, muestras) in enumerate(visuales.items()):
        axs[row, 0].imshow(bases[ident], cmap='gray', vmin=0, vmax=255)
        axs[row, 0].set_title(f'{ident}: base Anguli')
        for col, (nombre, perfil, arr) in enumerate(muestras, 1):
            axs[row, col].imshow(arr, cmap='gray', vmin=0, vmax=255)
            axs[row, col].set_title(f'{nombre}\n{perfil}')
        for ax in axs[row]: ax.axis('off')
    fig.suptitle('Piloto: dos bases y variantes locales — misma escala en todos los paneles')
    fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(salida/'comparacion.png', dpi=140); plt.close(fig)
    fig, axs = plt.subplots(1, len(campos), figsize=(3*len(campos), 5), squeeze=False)
    for ax, (nombre, dx, dy) in zip(axs[0], campos):
        y, x = np.mgrid[:dx.shape[0], :dx.shape[1]]
        ax.set_facecolor('#f0f3f6')
        step = 20
        ax.quiver(x[::step,::step], y[::step,::step], dx[::step,::step], dy[::step,::step],
                  angles='xy', scale_units='xy', scale=.25, width=.006, color='#1758a6')
        ax.set(xlim=(0, dx.shape[1]-1), ylim=(dy.shape[0]-1, 0), aspect='equal', title=nombre)
    fig.suptitle('Desplazamientos locales del muestreo inverso (flechas ampliadas ×4)')
    fig.tight_layout(rect=(0, 0, 1, .92)); fig.savefig(salida/'campos_locales.png', dpi=100); plt.close(fig)
    print(f'OK: {len(filas)} imágenes en {salida}')
    print('Repetición exacta por muestra comprobada. No hay duplicados exactos entre las salidas.')
    print('Abrí comparacion.png y campos_locales.png. La revisión visual sigue siendo necesaria.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, FileNotFoundError, FileExistsError) as error:
        raise SystemExit(f'ERROR: {error}')
