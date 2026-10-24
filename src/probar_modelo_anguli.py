"""Evalúa una vez fijado el modelo: 25 impresiones de control, sin entrenar.

No usa ni abre la prueba final original. Es control de impresiones adicionales
con las mismas cinco bases conocidas, no validación biométrica independiente.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path

from interfaz_servicios import RAIZ, leer_json, cargar_huellas, evaluar_huella, abrir_imagen
from diagnosticar_impresiones_anguli import verificar_lote, escribir_csv, sha_archivo
from adaptar_modelo_anguli import guardar_json, leer_csv

CONFIG=RAIZ/'documentos/resultados_adaptacion_anguli_v1/config_interfaz_experimental.json'
EXPERIMENTO=RAIZ/'experimentos/anguli_impresiones_v1'


def ejecutar(config=CONFIG, originales=EXPERIMENTO/'originales', salida=None):
    config=Path(config).resolve();originales=Path(originales).resolve()
    cfg=leer_json(config);s=cargar_huellas(cfg['huellas'])
    modelo_dir=RAIZ/s['carpeta'];paquete=modelo_dir.parent
    manifest=leer_csv(paquete/'manifiesto_anguli.csv')
    actuales,_=verificar_lote(originales)
    if [(r['archivo'],r['sha256_pixeles']) for r in manifest] != [(r['archivo'],r['sha256_pixeles']) for r in actuales]:
        raise ValueError('Las impresiones difieren de las registradas al congelar el modelo.')
    controles=[r for r in manifest if r['particion']=='control_apartado']
    if len(controles)!=25:
        raise ValueError('Se requieren exactamente 25 controles del plan original.')
    antes={n:sha_archivo(modelo_dir/n) for n in
           ('modelo_congelado.npz','umbral.json','correspondencia_congelada.json','resumen.json')}
    fecha=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    salida=Path(salida).resolve() if salida else EXPERIMENTO/'control_modelo_combinado'/fecha
    if salida.exists() or salida==originales or originales in salida.parents:
        raise ValueError('La salida debe ser una carpeta nueva fuera de originales.')
    filas=[]
    for fila in controles:
        r=dict(fila)
        try:
            x=evaluar_huella(abrir_imagen(originales/fila['archivo']),s)
            r.update(distancia=x['distancia'],aceptada=x['aceptada'],identidad_predicha=x['identidad'],
                     avisos=' | '.join(x['avisos']),error='')
        except Exception as e:
            r.update(distancia='',aceptada='',identidad_predicha='',avisos='',error=f'{type(e).__name__}: {e}')
        filas.append(r)
    if antes!={n:sha_archivo(modelo_dir/n) for n in antes}:
        raise RuntimeError('Cambió el modelo durante el control.')
    resumen=dict(fecha_utc=fecha,modelo=s['identificador'],modelo_sha256=antes,umbral=s['umbral'],
        entrenamiento_ejecutado=False,modelo_modificado=False,prueba_final_original_utilizada=False,
        advertencia='Control posterior al ajuste, mismas bases y corrida de Anguli. No es prueba con nuevas identidades.',
        resultados=[])
    for ident in ('A01','A02','A03','I01','I02'):
        rs=[r for r in filas if r['identidad_real']==ident]
        validas=[r for r in rs if not r['error']]
        met=dict(identidad=ident,n=len(rs),errores=len(rs)-len(validas),
            aceptadas=sum(r['aceptada'] for r in validas),
            identificadas_correctamente=sum(r['aceptada'] and r['identidad_predicha']==ident for r in validas))
        resumen['resultados'].append(met)
        print(f"{ident}: {met['n']} controles; {met['aceptadas']} aceptadas; "
              f"{met['identificadas_correctamente']} identificaciones correctas; {met['errores']} errores")
    salida.mkdir(parents=True)
    escribir_csv(salida/'consultas_control.csv',filas)
    guardar_json(salida/'resumen_control.json',resumen)
    print('Modelo sin modificar. Prueba final original sin utilizar.')
    print('Salida:',salida)
    return salida


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--control',action='store_true',required=True,help='Ejecutar explícitamente el control apartado 26–30.')
    p.add_argument('--config',type=Path,default=CONFIG)
    p.add_argument('--originales',type=Path,default=EXPERIMENTO/'originales')
    p.add_argument('--salida',type=Path)
    a=p.parse_args()
    try:
        ejecutar(a.config,a.originales,a.salida)
    except (OSError,ValueError,KeyError) as e:
        p.exit(1,f'No se completó el control: {e}\nNo se entrenó ni reemplazó el modelo.\n')
