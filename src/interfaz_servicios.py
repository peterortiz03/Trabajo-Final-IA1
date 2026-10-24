"""Adaptadores de inferencia real. No entrenan ni guardan consultas.

Las importaciones científicas ocurren en el trabajador de inicio, no en Tk.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def leer_json(ruta):
    return json.loads(Path(ruta).read_text(encoding='utf-8-sig'))


def sha_codigo(ruta):
    return hashlib.sha256(Path(ruta).read_text(encoding='utf-8-sig').encode()).hexdigest()


def hash_json_windows(config):
    """Las instantáneas de Windows usaron JSON indentado y CRLF."""
    texto = json.dumps(config, ensure_ascii=False, indent=2, allow_nan=False)
    return {hashlib.sha256(t.encode()).hexdigest() for t in (texto, texto.replace('\n', '\r\n'))}


def cargar_huellas(cfg, raiz=RAIZ):
    import caracteristicas_huellas as ch
    from calibrar_rechazo_huellas import cargar_sistema
    from verificacion_estadistica import sha

    raiz = Path(raiz)
    carpeta = raiz / cfg['modelo']
    modelo, umbral = cargar_sistema(carpeta)
    resumen = leer_json(carpeta / 'resumen.json')
    seleccion = leer_json(raiz / cfg['seleccion'])
    if resumen['archivos_sha256']['modelo_congelado.npz'] != seleccion['archivos_sha256']['seleccionada/parametros.npz']:
        raise ValueError('El modelo congelado y la selección documentada no corresponden.')
    cfg_ext = ch.cargar_config(raiz / cfg['extractor'])
    if seleccion['archivos_sha256']['config_extractor_efectiva.json'] not in hash_json_windows(cfg_ext):
        raise ValueError('La configuración GLCM difiere de la usada por el modelo congelado.')
    if sha_codigo(ch.__file__) != cfg['codigo_extractor_sha256']:
        raise ValueError('Cambió el extractor de huellas. Revisar el contrato antes de continuar.')
    if ch.nombres_caracteristicas(cfg_ext) != modelo['nombres'].tolist():
        raise ValueError('Nombres u orden de características de huellas incompatibles.')
    entorno = leer_json(raiz / cfg['entorno_normalizacion'])
    ruta_norm = raiz / cfg['normalizacion']
    if sha(ruta_norm) != entorno['sha256_config']:
        # git puede convertir únicamente los saltos de línea en Windows.
        texto = ruta_norm.read_text(encoding='utf-8-sig')
        hashes = {hashlib.sha256(t.encode()).hexdigest() for t in (texto, texto.replace('\n', '\r\n'))}
        if entorno['sha256_config'] not in hashes:
            raise ValueError('Cambió la configuración de normalización de huellas.')
    for nombre in ('roi_normalizacion_v1.py', 'normalizacion_final.py'):
        if sha_codigo(raiz / 'src' / nombre) != entorno['codigo'][nombre]:
            raise ValueError('Cambió el procedimiento de normalización: ' + nombre)
    for paquete, clave in [('numpy', 'numpy'), ('scipy', 'scipy'), ('Pillow', 'pillow')]:
        if importlib.metadata.version(paquete) != entorno[clave]:
            raise ValueError(f'Usar {paquete}=={entorno[clave]} para respetar la normalización registrada.')
    return dict(modelo=modelo, umbral=umbral, cfg_ext=cfg_ext, cfg_norm=leer_json(ruta_norm),
                identificador=resumen['fecha_utc'], carpeta=cfg['modelo'])


def abrir_imagen(ruta):
    """Una copia en memoria sirve tanto para la vista previa como para inferir."""
    from PIL import Image
    with Image.open(ruta) as imagen:
        imagen.load()
        return imagen.copy()


def evaluar_huella(imagen, sistema):
    from normalizacion_final import normalizar_huella
    from caracteristicas_huellas import extraer_huella, nombres_caracteristicas
    from calibrar_rechazo_huellas import decidir_acceso
    normal, info = normalizar_huella(imagen, sistema['cfg_norm'])
    vector, detalle = extraer_huella(normal, info['mascara_normalizada'], sistema['cfg_ext'])
    resultado = decidir_acceso(vector, nombres_caracteristicas(sistema['cfg_ext']),
                               sistema['modelo'], sistema['umbral'])[0]
    return dict(resultado, umbral=sistema['umbral'], modelo=sistema['identificador'],
                avisos=info['avisos'] + detalle['avisos'])


class Servicios:
    def __init__(self):
        self.huellas = None
        self.voz = None
        self.sd = None
        self.cfg_captura = None
        self.preparador = None
        self.errores = {}

    @classmethod
    def cargar(cls, ruta_config=RAIZ / 'config/aplicacion.json', raiz=RAIZ):
        servicio = cls()
        try:
            cfg = leer_json(ruta_config)
            if cfg['version'] != 'interfaz_v1':
                raise ValueError('Versión de configuración de interfaz desconocida.')
        except Exception as e:
            servicio.errores['configuración'] = f'{type(e).__name__}: {e}. Revisar {ruta_config}.'
            return servicio
        try:
            servicio.huellas = cargar_huellas(cfg['huellas'], raiz)
        except Exception as e:
            servicio.errores['huellas'] = (f'{type(e).__name__}: {e}. '
                'Restaurar los archivos de huellas indicados en config/aplicacion.json; no recalibrar.')
        try:
            from probar_knn_audio import cargar_sistema, COMANDOS
            voz = cargar_sistema(Path(raiz) / cfg['audio']['modelo'], raiz)
            if set(voz['modelo']['etiquetas']) != set(COMANDOS):
                raise ValueError('El modelo de voz no contiene exactamente los tres comandos.')
            servicio.voz = voz
        except Exception as e:
            servicio.errores['voz'] = (f'{type(e).__name__}: {e}. '
                f"Restaurar {cfg['audio']['modelo']} y la extracción indicada en su resumen.json. "
                'Ver documentos/guias/interfaz_integracion.md; el control manual sigue disponible.')
        try:
            from grabar_audio import cargar_config
            servicio.cfg_captura = cargar_config(Path(raiz) / cfg['audio']['captura'])
            import sounddevice as sd
            servicio.sd = sd
        except Exception as e:
            servicio.errores['micrófono'] = (f'{type(e).__name__}: {e}. '
                'Instalar requirements-audio.txt y revisar micrófono/permisos de Windows.')
        try:
            from preparar_captura import cargar_preparador
            servicio.preparador = cargar_preparador(Path(raiz)/'config/preparar_captura_v1.json',raiz)
        except Exception as e:
            servicio.errores['preparación'] = (f'{type(e).__name__}: {e}. '
                'Revisar config/preparar_captura_v1.json y la configuración del generador. '
                'Se puede seguir seleccionando una captura original directamente.')
        return servicio

    def microfonos(self):
        if self.sd is None:
            raise RuntimeError(self.errores.get('micrófono', 'Captura no disponible.'))
        apis = self.sd.query_hostapis()
        entradas = [(i, f"{d['name']} · {apis[d['hostapi']]['name']}")
                    for i, d in enumerate(self.sd.query_devices()) if d['max_input_channels'] > 0]
        if not entradas:
            raise RuntimeError('No se detectó micrófono. Conectalo y revisá los permisos de Windows.')
        return entradas

    def formato(self, indice):
        from grabar_audio import configurar_dispositivo
        return configurar_dispositivo(self.sd, indice, self.cfg_captura)

    def escuchar(self, formato, al_iniciar, al_procesar, cancelar):
        from grabar_audio import capturar_pcm
        from probar_knn_audio import interpretar
        indice, fs, canales, _, _ = formato
        audio = capturar_pcm(self.sd, indice, fs, canales, self.cfg_captura, al_iniciar, cancelar)
        if cancelar.is_set():
            raise InterruptedError('Sesión cerrada.')
        al_procesar()
        resultado, _ = interpretar(audio, fs, self.voz)
        return resultado  # Audio y vector dejan de conservarse al terminar la llamada.


if __name__ == '__main__':
    import argparse
    import os
    import platform
    os.environ.setdefault('MPLBACKEND', 'Agg')
    p = argparse.ArgumentParser(description='Verificar recursos de la interfaz sin abrir ventana ni grabar.')
    p.add_argument('--config', type=Path, default=RAIZ/'config/aplicacion.json')
    args = p.parse_args()
    ruta = args.config if args.config.is_absolute() else RAIZ / args.config
    s = Servicios.cargar(ruta)
    print('Python:', platform.python_version())
    print('Huellas:', 'disponible · modelo ' + s.huellas['identificador'] if s.huellas else 'no disponible')
    print('Voz:', 'disponible · modelo ' + s.voz['carpeta'].name if s.voz else 'no disponible')
    for recurso, error in s.errores.items():
        print(f'{recurso}: {error}')
    try:
        entradas = s.microfonos()
        for indice, nombre in entradas:
            print(f'Micrófono {indice}: {nombre}')
    except Exception as e:
        print('Captura no lista:', e)
