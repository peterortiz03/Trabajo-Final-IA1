"""Sortea una base de DESARROLLO y genera una sola captura, sin reconocerla."""
import json
from pathlib import Path
import secrets

from preparar_captura import abrir_base, preparar_captura, elegir_parametros_aleatorios

RAIZ = Path(__file__).resolve().parents[1]


def bases_disponibles(tipo, raiz=RAIZ):
    raiz=Path(raiz)
    cfg=json.loads((raiz/'config/generacion_interfaz_v1.json').read_text(encoding='utf-8-sig'))
    conjunto=json.loads((raiz/'config/conjunto_v1.json').read_text(encoding='utf-8-sig'))
    if tipo not in ('Aleatoria','Autorizada','Intrusa'):
        raise ValueError('Elegí Aleatoria, Autorizada o Intrusa.')
    permitidas=set(cfg['bases_desarrollo'])
    esperadas={'A01','A02','A03','I01','I02'}
    if not permitidas.issubset(esperadas) or not permitidas:
        raise ValueError('La generación automática solo admite las cinco bases de desarrollo.')
    candidatos=[]
    for r in conjunto['identidades']:
        if r['id'] not in permitidas:
            continue
        if r.get('particion')=='prueba':
            raise ValueError('Una base configurada está reservada para prueba.')
        if tipo=='Autorizada' and r['grupo']!='autorizado':continue
        if tipo=='Intrusa' and r['grupo']!='intruso':continue
        ruta=(raiz/r['base']).resolve()
        if not ruta.is_relative_to(raiz.resolve()):
            raise ValueError('La base debe estar dentro del proyecto.')
        if not ruta.is_file():
            raise ValueError('Falta una base de desarrollo configurada: '+r['base'])
        candidatos.append((r,ruta))
    if not candidatos:
        raise ValueError('No hay bases disponibles para '+tipo+'.')
    return candidatos


def generar_muestra(tipo, preparador, raiz=RAIZ):
    """Una elección, una generación; nunca repite buscando una aceptación."""
    referencia,ruta=secrets.choice(bases_disponibles(tipo,raiz))
    base=abrir_base(ruta)
    perfil,semilla=elegir_parametros_aleatorios(preparador)
    imagen,receta=preparar_captura(base,perfil,semilla,preparador)
    receta['eleccion_parametros']='automatica'
    receta['origen_sorteo']=dict(tipo_solicitado=tipo,base_id=referencia['id'],
        grupo_referencia=referencia['grupo'],archivo_base=referencia['base'])
    return base,imagen,receta
