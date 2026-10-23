"""K-NN de comandos con todas las características y evaluación por hablante.

No modifica revisiones/particiones ni usa prueba. PCA solo visualiza. La CV
LOSO se usa para elegir k/votos; sus resultados no son evaluación final.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
from pathlib import Path
import platform
import shutil

import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from verificacion_estadistica import (
    aplicar_mapa_audio, cargar_ejecucion, cantidades, guardar_csv, guardar_json, leer_json, sha,
)

RAIZ = Path(__file__).resolve().parents[1]


def validar_config(c):
    if (c["version"] != "knn_audio_160_v1" or c["distancia"] != "euclidean"
            or sorted(c["comandos"]) != ["identificar", "reconocer", "salir"]
            or sorted(c["vecinos"]) != [1, 3, 5, 7]
            or sorted(c["votos"]) != ["distance", "uniform"]
            or c["pca"] != dict(n_components=None, svd_solver="full", whiten=False)):
        raise ValueError("La referencia compara k=1,3,5,7, dos votos y PCA completo, sin selección.")


def preparar_audio(raiz, config, extraccion=""):
    d = cargar_ejecucion(raiz, "audio", extraccion)
    mapa = leer_json(raiz / config["mapa_audio"])
    catalogo = aplicar_mapa_audio(d["catalogo"], mapa)
    filas = aplicar_mapa_audio(d["filas"], mapa)
    voces_por_parte = {}
    for r in catalogo:
        p = r["particion_analisis"]
        if p not in {"entrenamiento", "validacion", "prueba"}:
            raise ValueError("Asignar explícitamente los hablantes pendientes en el mapa.")
        voces_por_parte.setdefault(r["hablante"], set()).add(p)
        if (p != "prueba" and r["decision_revision"] != "excluir" and
                (r["decision_revision"] != "conservar" or r["estado_extraccion"] != "vectorizada")):
            raise ValueError("Revisión pendiente o sin vector: " + r["muestra_id"])
    if any(len(partes) != 1 for partes in voces_por_parte.values()):
        raise ValueError("Un hablante aparece en distintas particiones.")
    mask = np.array([r["particion_analisis"] != "prueba" and
                     r["decision_revision"] == "conservar" for r in filas])
    usadas = [r for r, ok in zip(filas, mask) if ok]
    X = d["X"][mask]
    partes = np.array([r["particion_analisis"] for r in usadas])
    y = np.array([r["comando"] for r in usadas])
    voces = np.array([r["hablante"] for r in usadas])
    train = partes == "entrenamiento"
    if (not len(X) or not np.isfinite(X).all() or
            set(y[train]) != set(config["comandos"]) or
            not set(y).issubset(config["comandos"])):
        raise ValueError("Se requieren datos finitos y los tres comandos en entrenamiento.")
    if len(set(voces[train])) < 2:
        raise ValueError("LOSO necesita al menos dos hablantes de entrenamiento.")
    if np.all(np.ptp(X[train], axis=0) == 0):
        raise ValueError("Todas las características son constantes; revisar extracción.")
    for r in catalogo:
        r["uso_knn"] = ("reservada_prueba" if r["particion_analisis"] == "prueba" else
                        "excluida_revision" if r["decision_revision"] == "excluir" else
                        r["particion_analisis"])
    d.update(X=X, filas=usadas, y=y, voces=voces, train=train, partes=partes,
             ids=np.array([r["muestra_id"] for r in usadas]), catalogo_uso=catalogo)
    return d


def clasificador(k, votos):
    return KNeighborsClassifier(n_neighbors=k, weights=votos, metric="euclidean", algorithm="brute", n_jobs=1)


def metricas(y, pred, clases):
    report = classification_report(y, pred, labels=clases, output_dict=True, zero_division=0)
    return dict(n=len(y), exactitud=float(accuracy_score(y, pred)),
                recall_macro=float(report["macro avg"]["recall"]),
                f1_macro=float(report["macro avg"]["f1-score"]), por_comando={
                    str(c): dict(precision=float(report[c]["precision"]), recall=float(report[c]["recall"]),
                                 f1=float(report[c]["f1-score"]), n=int(report[c]["support"])) for c in clases})


def comparar_loso(X, y, voces, ids, nombres, config):
    """Escalador independiente por pliegue; ninguna voz se mezcla con su ajuste.

    Los resultados se usan para selección de parámetros. No son una estimación
    independiente después de elegir la mejor opción.
    """
    clases = config["comandos"]
    folds = list(LeaveOneGroupOut().split(X, y, voces))
    detalle, predicciones, contratos = [], [], []
    for tr, va in folds:
        if set(voces[tr]) & set(voces[va]) or set(y[tr]) != set(clases):
            raise ValueError("Pliegue sin los tres comandos o con hablantes compartidos.")
        if max(config["vecinos"]) > len(tr):
            raise ValueError("Un pliegue tiene menos muestras que el máximo k configurado.")
        if set(y[va]) != set(clases):
            raise ValueError("Faltan comandos en un hablante retenido; revisar cobertura sin descartar filas.")
        voz = str(voces[va][0])
        scaler = StandardScaler().fit(X[tr])
        Ztr, Zva = scaler.transform(X[tr]), scaler.transform(X[va])
        contratos.append(dict(hablante_retenido=voz, hablantes_ajuste=sorted(set(voces[tr])),
            muestras_ajuste=np.asarray(ids)[tr].tolist(), muestras_retenidas=np.asarray(ids)[va].tolist(),
            medias=scaler.mean_.tolist(), escalas=scaler.scale_.tolist(), nombres=list(nombres)))
        for k in config["vecinos"]:
            for votos in config["votos"]:
                knn = clasificador(k, votos).fit(Ztr, y[tr])
                pred = knn.predict(Zva)
                met = metricas(y[va], pred, clases)
                detalle.append(dict(k=k, votos=votos, hablante_retenido=voz,
                                    **{c: met[c] for c in ("n", "exactitud", "recall_macro", "f1_macro")}))
                for i, palabra in zip(va, pred):
                    predicciones.append(dict(k=k, votos=votos, muestra=str(ids[i]), hablante=voz,
                                             real=str(y[i]), prediccion=str(palabra)))
    resumen = []
    for k in config["vecinos"]:
        for votos in config["votos"]:
            sub = [r for r in detalle if r["k"] == k and r["votos"] == votos]
            resumen.append(dict(k=k, votos=votos, hablantes=len(sub),
                recall_macro_medio=float(np.mean([r["recall_macro"] for r in sub])),
                exactitud_media=float(np.mean([r["exactitud"] for r in sub])),
                recall_macro_peor_hablante=float(min(r["recall_macro"] for r in sub))))
    mejor = max(r["recall_macro_medio"] for r in resumen)
    empatadas = [r for r in resumen if abs(r["recall_macro_medio"] - mejor) <= 1e-12]
    elegida = min(empatadas, key=lambda r: (r["votos"] != "uniform", r["k"]))
    return dict(k=elegida["k"], votos=elegida["votos"]), resumen, detalle, predicciones, contratos


def predecir_vectores(X, nombres, modelo):
    """Predice una de tres palabras; no calibra confianza ni rechaza ruido/silencio."""
    X = np.atleast_2d(np.asarray(X, dtype=float))
    if list(nombres) != list(modelo["nombres"]) or X.shape[1] != len(nombres):
        raise ValueError("Cantidad, nombres u orden de características incorrectos.")
    if not np.isfinite(X).all():
        raise ValueError("Características no finitas: revisar audio, no forzar un comando.")
    Z = (X - modelo["media"]) / modelo["escala"]
    with threadpool_limits(limits=1):
        return modelo["knn"].predict(Z)


def cargar_modelo(carpeta):
    """Restaura parámetros y ejemplos guardados sin pickle ni reaprender escalado."""
    p = Path(carpeta)
    r = leer_json(p / "resumen.json")
    if sha(p / "modelo.npz") != r["archivos_sha256"]["modelo.npz"]:
        raise ValueError("El modelo guardado fue modificado.")
    parametros = leer_json(p / "parametros_elegidos.json")
    if sha(p / "parametros_elegidos.json") != r["archivos_sha256"]["parametros_elegidos.json"]:
        raise ValueError("Los parámetros elegidos fueron modificados.")
    with np.load(p / "modelo.npz", allow_pickle=False) as z:
        m = {c: z[c].copy() for c in ("nombres", "media", "escala", "Z_entrenamiento", "etiquetas")}
    if (m["Z_entrenamiento"].shape != (len(m["etiquetas"]), len(m["nombres"])) or
            np.any(m["escala"] <= 0) or not np.isfinite(m["Z_entrenamiento"]).all()):
        raise ValueError("Parámetros guardados incompatibles.")
    # En K-NN, fit reconstruye el índice con los ejemplos YA guardados. No se
    # calcula otro escalador ni se incorporan nuevas grabaciones.
    m["knn"] = clasificador(parametros["k"], parametros["votos"]).fit(m["Z_entrenamiento"], m["etiquetas"])
    return m


def exportar_metricas(salida, nombre, filas, clases):
    y = np.array([r["real"] for r in filas])
    pred = np.array([r["prediccion"] for r in filas])
    met = metricas(y, pred, clases)
    cm = confusion_matrix(y, pred, labels=clases)
    guardar_csv(salida / f"matriz_{nombre}.csv", [dict(real=c, **{
        palabra: int(cm[i, j]) for j, palabra in enumerate(clases)}) for i, c in enumerate(clases)])
    guardar_csv(salida / f"metricas_comando_{nombre}.csv", [dict(comando=c, **met["por_comando"][c]) for c in clases])
    voces = []
    for voz in sorted({r["hablante"] for r in filas}):
        sub = [r for r in filas if r["hablante"] == voz]
        v = metricas(np.array([r["real"] for r in sub]), np.array([r["prediccion"] for r in sub]), clases)
        voces.append(dict(hablante=voz, **{k: v[k] for k in ("n", "exactitud", "recall_macro", "f1_macro")}))
    guardar_csv(salida / f"metricas_hablante_{nombre}.csv", voces)
    return met, cm


def graficos(d, pca, P, cv, cm, elegida, salida):
    clases, partes = sorted(set(d["y"])), [p for p in ("entrenamiento", "validacion") if np.any(d["partes"] == p)]
    fig, axs = plt.subplots(len(partes), 2, figsize=(14, 6*len(partes)), squeeze=False,
                            sharex=True, sharey=True, layout="constrained")
    for fila, part in enumerate(partes):
        for col, (etiquetas, titulo) in enumerate([(d["y"], "Palabra"), (d["voces"], "Hablante")]):
            ax = axs[fila, col]
            for j, etiqueta in enumerate(sorted(set(etiquetas))):
                m = (d["partes"] == part) & (etiquetas == etiqueta)
                if m.any():
                    ax.scatter(P[m, 0], P[m, 1], s=38, alpha=.7,
                               color=plt.get_cmap("tab10")(j % 10), label=str(etiqueta))
            v = 100*pca.explained_variance_ratio_
            ax.set(title=f"{titulo} · {part}", xlabel=f"PC1 ({v[0]:.1f} %)", ylabel=f"PC2 ({v[1]:.1f} %)")
            ax.grid(alpha=.2); ax.legend(fontsize=9)
    fig.suptitle("Mismas coordenadas PCA; entrenamiento ajusta las direcciones", fontsize=14)
    fig.savefig(salida / "pca_palabras_hablantes.png", dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    ax.plot(np.arange(1, len(pca.explained_variance_ratio_)+1), 100*np.cumsum(pca.explained_variance_ratio_), linewidth=2)
    for nivel in (90, 95):
        ax.axhline(nivel, linestyle="--", alpha=.5, label=f"{nivel} %")
    ax.set(xlabel="Componentes", ylabel="Varianza acumulada (%)", ylim=(0, 102),
           title="PCA exploratorio · todas las características · ajuste en entrenamiento")
    ax.grid(alpha=.2); ax.legend()
    fig.savefig(salida / "varianza_acumulada.png", dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    for voto, texto in [("uniform", "Voto uniforme"), ("distance", "Voto por distancia")]:
        sub = sorted([r for r in cv if r["votos"] == voto], key=lambda r: r["k"])
        ax.plot([r["k"] for r in sub], [100*r["recall_macro_medio"] for r in sub], "o-", label=texto)
    ax.set(xlabel="Cantidad de vecinos k", ylabel="Recall macro medio por hablante (%)",
           title="Selección interna LOSO · sin mezclar voces entre ajuste y evaluación", xticks=sorted({r["k"] for r in cv}))
    ax.grid(alpha=.2); ax.legend()
    fig.savefig(salida / "comparacion_k.png", dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 6), layout="constrained")
    ax.imshow(cm, cmap="Blues", vmin=0)
    for i in range(len(clases)):
        for j in range(len(clases)):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=16,
                    color="white" if cm[i, j] > cm.max()/2 else "black")
    ax.set(xticks=range(len(clases)), yticks=range(len(clases)), xticklabels=clases, yticklabels=clases,
           xlabel="Palabra predicha", ylabel="Palabra real",
           title=f"CV de selección LOSO · k={elegida['k']}, voto={elegida['votos']}")
    fig.savefig(salida / "matriz_cv_seleccion.png", dpi=150); plt.close(fig)


def ejecutar(raiz=RAIZ, extraccion="", config_path="config/knn_audio_v1.json"):
    raiz = Path(raiz).resolve()
    config = leer_json(raiz / config_path)
    validar_config(config)
    d = preparar_audio(raiz, config, extraccion)
    X, y, tr = d["X"], d["y"], d["train"]
    with threadpool_limits(limits=1):
        elegida, cv, detalle, preds, contratos = comparar_loso(
            X[tr], y[tr], d["voces"][tr], d["ids"][tr], d["nombres"], config)
        scaler = StandardScaler().fit(X[tr])
        Z = scaler.transform(X)
        knn = clasificador(elegida["k"], elegida["votos"]).fit(Z[tr], y[tr])
        pca = PCA(**config["pca"]).fit(Z[tr])
        P = pca.transform(Z)
    corte = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    salida = raiz / "resultados/knn_audio" / corte
    salida.mkdir(parents=True, exist_ok=False)
    guardar_json(salida / "parametros_elegidos.json", elegida)
    guardar_csv(salida / "comparacion_cv.csv", cv)
    guardar_csv(salida / "detalle_cv_hablante.csv", detalle)
    guardar_json(salida / "contratos_pliegues.json", contratos)
    seleccionadas = [r for r in preds if r["k"] == elegida["k"] and r["votos"] == elegida["votos"]]
    referencia = [r for r in preds if r["k"] == config["referencia"]["k"] and r["votos"] == config["referencia"]["votos"]]
    guardar_csv(salida / "predicciones_cv_seleccion.csv", seleccionadas)
    guardar_csv(salida / "errores_cv_seleccion.csv", [r for r in seleccionadas if r["real"] != r["prediccion"]], campos=list(seleccionadas[0]))
    met, cm = exportar_metricas(salida, "cv_seleccion", seleccionadas, config["comandos"])
    met_ref, _ = exportar_metricas(salida, "cv_referencia", referencia, config["comandos"])
    validacion = None
    if (~tr).any():
        with threadpool_limits(limits=1):
            predval = knn.predict(Z[~tr])
        filasval = [dict(muestra=str(id_), hablante=str(voz), real=str(real), prediccion=str(pred))
                    for id_, voz, real, pred in zip(d["ids"][~tr], d["voces"][~tr], y[~tr], predval)]
        guardar_csv(salida / "predicciones_validacion.csv", filasval)
        validacion, _ = exportar_metricas(salida, "validacion", filasval, config["comandos"])
    guardar_csv(salida / "catalogo_uso.csv", d["catalogo_uso"])
    guardar_csv(salida / "cantidades.csv", cantidades(d["filas"], ["particion_analisis", "hablante", "comando"]))
    guardar_csv(salida / "parametros_escalado.csv", [dict(caracteristica=str(n), media=float(scaler.mean_[j]),
        desviacion_ddof0=float(np.sqrt(scaler.var_[j])), escala=float(scaler.scale_[j])) for j, n in enumerate(d["nombres"])])
    acum = np.cumsum(pca.explained_variance_ratio_)
    guardar_csv(salida / "varianza_explicada.csv", [dict(componente=i+1, proporcion=float(v), acumulada=float(acum[i]))
                for i, v in enumerate(pca.explained_variance_ratio_)])
    np.savez_compressed(salida / "modelo.npz", nombres=d["nombres"], media=scaler.mean_, escala=scaler.scale_,
        Z_entrenamiento=Z[tr], etiquetas=y[tr], ids_entrenamiento=d["ids"][tr], hablantes=d["voces"][tr],
        componentes_pca=pca.components_, media_pca=pca.mean_, varianza_pca=pca.explained_variance_ratio_)
    graficos(d, pca, P, cv, cm, elegida, salida)
    resumen = dict(fecha_utc=corte, python=platform.python_version(), plataforma=platform.platform(),
        dependencias={p: importlib.metadata.version(p) for p in ("numpy", "scipy", "matplotlib", "scikit-learn")},
        config=config, extraccion=d["carpeta"].relative_to(raiz).as_posix(),
        manifiesto_extraccion_sha256=sha(d["carpeta"] / "manifiesto.json"),
        cantidades=dict(Counter(d["partes"])), hablantes_entrenamiento=sorted(set(d["voces"][tr])),
        dimension=len(d["nombres"]), columnas_eliminadas=[],
        constantes_train=d["nombres"][np.ptp(X[tr], axis=0) == 0].tolist(), parametros=elegida,
        cv_referencia=met_ref, cv_seleccion=met, validacion=validacion,
        pc1_pc2_porcentaje=float(100*acum[1]), componentes_95=int(np.searchsorted(acum, .95)+1),
        prueba_evaluada=False, pca_utilizado_para_clasificar=False,
        advertencia="LOSO se usó para elegir parámetros; métricas de desarrollo, no prueba independiente. Las voces actuales participaron del desarrollo previo.")
    for p in [Path(__file__), raiz / config_path, raiz / config["mapa_audio"], raiz / "src/verificacion_estadistica.py"]:
        shutil.copyfile(p, salida / p.name)
    shutil.copyfile(d["carpeta"] / "config_efectiva.json", salida / "config_extractor.json")
    resumen["archivos_sha256"] = {p.name: sha(p) for p in salida.iterdir() if p.is_file()}
    guardar_json(salida / "resumen.json", resumen)
    print("Salida:", salida.relative_to(raiz))
    print("Características:", len(d["nombres"]), "Muestras:", resumen["cantidades"])
    print("Hablantes de entrenamiento:", resumen["hablantes_entrenamiento"])
    print("Elegida por CV interna:", elegida)
    print(f"Exactitud CV de selección: {100*met['exactitud']:.2f}%; recall macro: {100*met['recall_macro']:.2f}%")
    print("Validación con hablantes de otra partición:", "PENDIENTE" if validacion is None else validacion)
    print("Prueba reservada. Modelo de vocabulario cerrado: no rechaza palabras desconocidas.")
    return salida, resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraccion", default="", help="Carpeta relativa exacta de extracción compatible, opcional.")
    args = parser.parse_args()
    ejecutar(extraccion=args.extraccion)
