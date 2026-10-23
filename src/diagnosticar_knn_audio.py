"""Inspeccionar vecinos de errores LOSO sin cambiar el modelo ni excluir datos."""
from datetime import datetime, timezone
from pathlib import Path
import argparse

import numpy as np
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from knn_audio import RAIZ, preparar_audio, clasificador
from probar_knn_audio import cargar_sistema
from verificacion_estadistica import guardar_csv, guardar_json


def diagnosticar(carpeta, raiz=RAIZ):
    raiz = Path(raiz).resolve()
    sistema = cargar_sistema(carpeta, raiz)
    r, m = sistema["resumen"], sistema["modelo"]
    d = preparar_audio(raiz, r["config"], r["extraccion"])
    tr = d["train"]
    X, y, voces, ids = d["X"][tr], d["y"][tr], d["voces"][tr], d["ids"][tr]
    if not np.array_equal(ids, sistema["ids"]) or not np.array_equal(y, m["etiquetas"]):
        raise ValueError("Cambió el conjunto de entrenamiento del modelo. No mezclar corridas.")
    if not np.allclose((X-m["media"])/m["escala"], m["Z_entrenamiento"], rtol=1e-12, atol=1e-12):
        raise ValueError("Los vectores de origen no coinciden con el modelo guardado.")
    catalogo = {f["muestra_id"]: f for f in d["filas"]}
    errores, aportes = [], []
    aciertos = 0
    with threadpool_limits(limits=1):
        for voz in sorted(set(voces)):
            ajuste, retenida = voces != voz, voces == voz
            scaler = StandardScaler().fit(X[ajuste])
            Ztr, Zva = scaler.transform(X[ajuste]), scaler.transform(X[retenida])
            knn = clasificador(r["parametros"]["k"], r["parametros"]["votos"]).fit(Ztr, y[ajuste])
            pred = knn.predict(Zva)
            aciertos += int(np.sum(pred == y[retenida]))
            ids_tr, y_tr, voces_tr = ids[ajuste], y[ajuste], voces[ajuste]
            for j, (ident, real, palabra) in enumerate(zip(ids[retenida], y[retenida], pred)):
                if real == palabra:
                    continue
                dist2 = np.sum((Ztr-Zva[j])**2, axis=1)
                fila = dict(muestra=str(ident), hablante=str(voz), real=str(real), prediccion=str(palabra),
                            ruta_original=catalogo[ident].get("ruta_original", ""))
                indices = {}
                for comando in r["config"]["comandos"]:
                    candidatos = np.flatnonzero(y_tr == comando)
                    i = candidatos[np.argmin(dist2[candidatos])]
                    indices[comando] = i
                    fila.update({f"vecino_{comando}": str(ids_tr[i]), f"voz_{comando}": str(voces_tr[i]),
                                 f"distancia_{comando}": float(np.sqrt(dist2[i])),
                                 f"ruta_{comando}": catalogo[ids_tr[i]].get("ruta_original", "")})
                errores.append(fila)
                # Diferencia de distancias cuadradas: positivo favorece al vecino
                # de la palabra confundida. Describe geometría, no causa acústica.
                ic, ie = indices[str(real)], indices[str(palabra)]
                contrib_correcta = (Ztr[ic]-Zva[j])**2
                contrib_confundida = (Ztr[ie]-Zva[j])**2
                diferencia = contrib_correcta-contrib_confundida
                for q in np.argsort(-diferencia)[:10]:
                    aportes.append(dict(muestra=str(ident), caracteristica=str(d["nombres"][q]),
                        diferencia_cuadratica=float(diferencia[q]),
                        aporte_vecino_correcto=float(contrib_correcta[q]),
                        aporte_vecino_confundido=float(contrib_confundida[q])))
    if not np.isclose(aciertos/len(y), r["cv_seleccion"]["exactitud"], atol=1e-12):
        raise ValueError("No se reprodujo la exactitud LOSO de origen: revisar versiones/orden antes de interpretar.")
    fecha = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    salida = raiz / "resultados/diagnostico_knn_audio" / fecha
    salida.mkdir(parents=True)
    campos = ["muestra", "hablante", "real", "prediccion", "ruta_original"]
    for c in r["config"]["comandos"]:
        campos += [f"vecino_{c}", f"voz_{c}", f"distancia_{c}", f"ruta_{c}"]
    guardar_csv(salida / "errores_vecinos_loso.csv", errores, campos=campos)
    guardar_csv(salida / "aportes_geometricos.csv", aportes, campos=["muestra", "caracteristica", "diferencia_cuadratica",
        "aporte_vecino_correcto", "aporte_vecino_confundido"])
    guardar_json(salida / "resumen.json", dict(modelo=str(Path(carpeta).resolve()),
        modelo_sha256=sistema["modelo_sha256"], muestras=len(y), aciertos=aciertos, errores=len(errores),
        entrenamiento_modificado=False, columnas_eliminadas=[],
        nota="Reproduce LOSO con parámetros elegidos previamente. No es otra evaluación independiente. Aportes geométricos no prueban causas acústicas ni autorizan eliminar columnas o muestras."))
    print("LOSO reproducido:", aciertos, "/", len(y), "| errores:", len(errores))
    print("Diagnóstico:", salida)
    return salida


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--modelo", default="", help="Carpeta del modelo; por defecto última corrida local.")
    args = p.parse_args()
    try:
        if args.modelo:
            carpeta = RAIZ / args.modelo
        else:
            opciones = sorted((RAIZ / "resultados/knn_audio").glob("*/resumen.json"))
            if not opciones:
                raise ValueError("Primero ejecutar src/knn_audio.py.")
            carpeta = opciones[-1].parent
        diagnosticar(carpeta)
    except (OSError, ValueError, KeyError, RuntimeError) as e:
        p.exit(2, f"No se pudo diagnosticar: {e}\n")
