"""Voto uniforme: mayoría; empate por vecino más próximo entre clases empatadas.

La selección compara precisión macro media por hablante para k=5/7.
No cambia los extractores, el módulo de huellas ni el K-NN histórico.
"""
import argparse
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import precision_score, recall_score, accuracy_score, confusion_matrix
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

RAIZ = Path(__file__).resolve().parents[1]
REGLA = 'mayoria_vecino_cercano_v1'
CLASES = ['identificar', 'reconocer', 'salir']


def leer(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def guardar(p, obj):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def sha(p):
    p=Path(p)
    contenido=p.read_bytes()
    if p.suffix in {'.json', '.csv'}:
        contenido=contenido.replace(b'\r\n', b'\n')
    return hashlib.sha256(contenido).hexdigest()


class KNNMayoriaCercano(KNeighborsClassifier):
    """Consulta determinista; igualdad exacta de distancia: orden guardado.

    Se ordenan TODOS los ejemplos por distancia e índice para definir también
    el empate entre los vecinos k y k+1. Una distancia casi igual no es empate.
    """
    def fit(self, X, y):
        super().fit(X, y)
        self.etiquetas_guardadas_ = np.asarray(y).copy()
        return self

    def predict(self, X):
        if self.weights != 'uniform':
            raise ValueError('Esta regla requiere voto uniforme.')
        X = np.atleast_2d(np.asarray(X, dtype=float))
        respuestas = []
        for q in X:
            dist = np.linalg.norm(self._fit_X - q, axis=1)
            orden = np.lexsort((np.arange(len(dist)), dist))[:self.n_neighbors]
            palabras = self.etiquetas_guardadas_[orden]
            clases, cuentas = np.unique(palabras, return_counts=True)
            empatadas = clases[cuentas == cuentas.max()]
            # Palabras ya ordenadas por distancia; saltar clases no mayoritarias.
            respuestas.append(next(p for p in palabras if p in empatadas))
        return np.asarray(respuestas, dtype=self.etiquetas_guardadas_.dtype)


def clasificador(k):
    return KNNMayoriaCercano(n_neighbors=k, weights='uniform', metric='euclidean',
                            algorithm='brute', n_jobs=1)


def comparar(X, y, voces, ids):
    detalle, predicciones = [], []
    for tr, va in LeaveOneGroupOut().split(X, y, voces):
        scaler = StandardScaler().fit(X[tr])
        Ztr, Zva = scaler.transform(X[tr]), scaler.transform(X[va])
        for k in [1, 3, 5, 7]:
            pred = clasificador(k).fit(Ztr, y[tr]).predict(Zva)
            detalle.append(dict(k=k, hablante=str(voces[va][0]), n=len(va),
                precision_macro=float(precision_score(y[va], pred, labels=CLASES, average='macro', zero_division=0)),
                recall_macro=float(recall_score(y[va], pred, labels=CLASES, average='macro', zero_division=0)),
                exactitud=float(accuracy_score(y[va], pred))))
            predicciones.extend(dict(k=k, muestra=str(ids[i]), hablante=str(voces[i]),
                real=str(y[i]), prediccion=str(p)) for i, p in zip(va, pred))
    tabla = [dict(k=k, votos='uniform',
        precision_macro_media=float(np.mean([r['precision_macro'] for r in detalle if r['k']==k])),
        recall_macro_medio=float(np.mean([r['recall_macro'] for r in detalle if r['k']==k])),
        exactitud_media=float(np.mean([r['exactitud'] for r in detalle if r['k']==k]))) for k in [1,3,5,7]]
    candidatas = [r for r in tabla if r['k'] in [5,7]]
    mejor = max(r['precision_macro_media'] for r in candidatas)
    k = min(r['k'] for r in candidatas if abs(r['precision_macro_media']-mejor)<=1e-12)
    return k, tabla, detalle, predicciones


def csv_salida(p, filas):
    with Path(p).open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)


def cargar_paquete(carpeta):
    """Carga autocontenida; no depende del manifiesto local de la etapa histórica."""
    import caracteristicas_audio as ca
    import preprocesamiento_audio as pp
    p=Path(carpeta); resumen=leer(p/'resumen.json')
    for nombre, esperado in resumen['archivos_sha256'].items():
        if sha(p/nombre)!=esperado:
            raise ValueError('Archivo del paquete modificado: '+nombre)
    for dep in ['numpy','scipy','scikit-learn']:
        if importlib.metadata.version(dep)!=resumen['dependencias'][dep]:
            raise ValueError('Usar versión registrada de '+dep+': '+resumen['dependencias'][dep])
    cfg_pp=pp.validar_config(leer(p/'preprocesamiento.json'))
    cfg_ext=ca.validar_config(leer(p/'extractor.json'))
    # Código del extractor/preprocesador debe ser el mismo, tolerando CRLF/LF.
    for modulo in [ca,pp]:
        texto=Path(modulo.__file__).read_text(encoding='utf-8-sig').replace('\r\n','\n')
        if hashlib.sha256(texto.encode()).hexdigest()!=resumen['codigo'][Path(modulo.__file__).name]:
            raise ValueError('Código acústico distinto al del paquete: '+modulo.__name__)
    with np.load(p/'modelo.npz',allow_pickle=False) as z:
        m={c:z[c].copy() for c in ['nombres','media','escala','Z_entrenamiento','etiquetas']}
        ids=z['ids_entrenamiento'].copy();voces=z['hablantes'].copy()
    params=leer(p/'parametros_elegidos.json')
    if params['desempate']!=REGLA or params['votos']!='uniform':
        raise ValueError('Regla de voto incompatible.')
    if list(m['nombres'])!=ca.nombres_caracteristicas(cfg_ext):
        raise ValueError('Cambió el orden de las características.')
    if not np.isfinite(m['Z_entrenamiento']).all() or np.any(m['escala']<=0):
        raise ValueError('Parámetros acústicos inválidos.')
    m['knn']=clasificador(params['k']).fit(m['Z_entrenamiento'],m['etiquetas'])
    return dict(modelo=m,cfg_pp=cfg_pp,cfg_ext=cfg_ext,ids=ids,voces=voces,
                carpeta=p,resumen=resumen,modelo_sha256=sha(p/'modelo.npz'))


def reproducir(datos, salida):
    """Repite LOSO y guarda tablas nuevas. No cambia el modelo activo."""
    salida=Path(salida)
    salida.mkdir(parents=True,exist_ok=False)
    z=np.load(datos,allow_pickle=False)
    X,y,voces,ids=z['X'],z['y'],z['hablantes'],z['ids']
    with threadpool_limits(limits=1):
        k,tabla,detalle,preds=comparar(X,y,voces,ids)
    csv_salida(salida/'comparacion_precision_recall.csv',tabla)
    csv_salida(salida/'detalle_loso.csv',detalle)
    csv_salida(salida/'predicciones_todas.csv',preds)
    seleccion=[r for r in preds if r['k']==k]
    csv_salida(salida/'predicciones_cv_seleccion.csv',seleccion)
    guardar(salida/'parametros_elegidos.json',dict(k=k,votos='uniform',desempate=REGLA))
    return k,tabla,detalle,seleccion


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--datos',default=str(RAIZ/'modelos/audio/precision_v2/entrada_desarrollo.npz'))
    parser.add_argument('--salida',required=True)
    args=parser.parse_args()
    k,tabla,_,_=reproducir(args.datos,args.salida)
    print('k seleccionado:',k)
    for r in tabla: print(r)
    print('Reproducción de métricas; no cambia el modelo activo ni la configuración.')
