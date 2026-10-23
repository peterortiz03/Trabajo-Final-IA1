"""Comparación acotada: todas las columnas, mejor mitad y mejor cuarto.

Reutiliza vectores existentes. Selección supervisada con identidades conocidas
de entrenamiento; K-means sigue sin recibir etiquetas. Validación se consulta
después de elegir variante con CV interna. Prueba e intrusos se reservan.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
from pathlib import Path
import pickle
import platform
import shutil

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, confusion_matrix
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

from clusterizacion_pca import preparar, RAIZ
from verificacion_estadistica import leer_json, guardar_json, guardar_csv, separacion, sha


def ranking_entrenamiento(X, y, nombres):
    """Razón entre/dentro de etapa 05; invariante a escala lineal por columna."""
    tabla = separacion(X, y, nombres)
    scores = np.array([
        np.inf if r["estado"] == "infinita_dispersion_interna_nula"
        else -np.inf if r["separacion"] is None else r["separacion"]
        for r in tabla
    ])
    # Empates por nombre para reproducibilidad. Constantes al final.
    orden = np.lexsort((np.asarray(nombres), -scores))
    return orden, tabla


def ajustar(X, y, nombres, cantidad, config, semilla=None, con_pca=False):
    """Recibe únicamente entrenamiento (o subentrenamiento de un pliegue)."""
    X, y, nombres = np.asarray(X), np.asarray(y), np.asarray(nombres)
    if X.ndim != 2 or X.shape != (len(y), len(nombres)) or not np.isfinite(X).all():
        raise ValueError("Matriz de entrenamiento incoherente o no finita.")
    if len(set(y)) != 3 or not 1 <= cantidad <= X.shape[1]:
        raise ValueError("Se requieren tres identidades y una cantidad válida de columnas.")
    orden, _ = ranking_entrenamiento(X, y, nombres)
    # Conservar el orden original en la entrada reducida, no el orden de ranking.
    indices = np.arange(X.shape[1]) if cantidad == X.shape[1] else np.sort(orden[:cantidad])
    if cantidad < X.shape[1] and np.any(np.ptp(X[:, indices], axis=0) == 0):
        raise ValueError("No hay suficientes columnas informativas para esta variante.")
    scaler = StandardScaler().fit(X[:, indices])
    Z = scaler.transform(X[:, indices])
    seed = config["semilla"] if semilla is None else semilla
    km = KMeans(random_state=seed, **config["kmeans"]).fit(Z)
    clases = sorted(set(y))
    conteos = np.array([[np.sum((y == c) & (km.labels_ == g))
                         for g in range(3)] for c in clases])
    filas, columnas = linear_sum_assignment(-conteos)
    mapa = {int(g): str(clases[f]) for f, g in zip(filas, columnas)}
    return dict(indices=indices, nombres_entrada=nombres.tolist(),
                nombres_seleccionados=nombres[indices].tolist(), escalador=scaler,
                kmeans=km, correspondencia=mapa,
                pca=PCA(n_components=None, svd_solver="full", whiten=False).fit(Z) if con_pca else None)


def transformar(X, nombres, modelo):
    """Transforma futuros vectores COMPLETOS de 144 componentes, sin ningún fit.

    El grupo y la identidad aproximada NO equivalen a autorización de acceso.
    """
    X = np.atleast_2d(np.asarray(X, dtype=float))
    if list(nombres) != modelo["nombres_entrada"] or X.shape[1] != len(nombres):
        raise ValueError("Cantidad, nombres u orden de características incorrectos.")
    if not np.isfinite(X).all():
        raise ValueError("Vector con valores no finitos.")
    Z = modelo["escalador"].transform(X[:, modelo["indices"]])
    grupos = modelo["kmeans"].predict(Z)
    return dict(grupos=grupos, identidades=np.array([modelo["correspondencia"][int(g)] for g in grupos]),
                proyeccion=None if modelo["pca"] is None else modelo["pca"].transform(Z))


def evaluar(y, pred):
    clases = sorted(set(y))
    cm = confusion_matrix(y, pred["identidades"], labels=clases)
    return dict(n=len(y), ari=float(adjusted_rand_score(y, pred["grupos"])),
                coincidencia=float(np.mean(y == pred["identidades"])),
                acierto_por_identidad={str(c): float(cm[i, i] / cm[i].sum())
                                      for i, c in enumerate(clases)},
                tabla_identidad_grupo=[dict(identidad=str(c), **{
                    f"G{g}": int(np.sum((y == c) & (pred["grupos"] == g))) for g in range(3)})
                    for c in clases])


def elegir_con_cv(X, y, nombres, config):
    """Dentro de CADA pliegue vuelve a seleccionar, escalar y ajustar K-means.

    CV estratificada entre capturas sintéticas de identidades conocidas. No es
    evaluación de nuevos dedos, ni una estimación final independiente.
    """
    nfold = config["divisiones_cv"]
    if min(Counter(y).values()) < nfold:
        raise ValueError("No hay suficientes muestras por identidad para la CV configurada.")
    cantidades = sorted({max(1, int(np.ceil(len(nombres) * f)))
                         for f in config["fracciones_conservar"]}, reverse=True)
    folds = list(StratifiedKFold(nfold, shuffle=True, random_state=config["semilla"]).split(X, y))
    detalles, resumen, particiones = [], [], []
    for fold, (tr, va) in enumerate(folds, 1):
        for i in va:
            particiones.append(dict(fila_train=int(i), pliegue_interno=fold))
        for cantidad in cantidades:
            modelo = ajustar(X[tr], y[tr], nombres, cantidad, config)
            pred = transformar(X[va], nombres, modelo)
            metricas = evaluar(y[va], pred)
            detalles.append(dict(columnas=cantidad, pliegue=fold, ari=metricas["ari"],
                                 coincidencia=metricas["coincidencia"],
                                 seleccion=";".join(modelo["nombres_seleccionados"])))
    for cantidad in cantidades:
        filas = [r for r in detalles if r["columnas"] == cantidad]
        resumen.append(dict(columnas=cantidad, ari_medio=float(np.mean([r["ari"] for r in filas])),
                            ari_minimo=float(min(r["ari"] for r in filas)),
                            coincidencia_media=float(np.mean([r["coincidencia"] for r in filas]))))
    mejor_score = max(r["ari_medio"] for r in resumen)
    # Empate: cambio más moderado; conservar más columnas.
    elegida = max(r["columnas"] for r in resumen if abs(r["ari_medio"] - mejor_score) <= 1e-12)
    return elegida, resumen, detalles, particiones


def panel(ax, P, etiquetas, clases, titulo, pca, centroides=None):
    colores = plt.get_cmap("tab10")
    for i, clase in enumerate(clases):
        mask = etiquetas == clase
        if mask.any():
            ax.scatter(P[mask, 0], P[mask, 1], s=36, alpha=.75, color=colores(i), label=str(clase))
    if centroides is not None:
        ax.scatter(centroides[:, 0], centroides[:, 1], marker="X", c="black", s=140, label="Centroides")
        for g, centro in enumerate(centroides):
            ax.annotate(f"G{g}", centro[:2], xytext=(6, 6), textcoords="offset points")
    v = pca.explained_variance_ratio_ * 100
    ax.set(title=titulo, xlabel=f"PC1 ({v[0]:.1f} %)", ylabel=f"PC2 ({v[1]:.1f} %)")
    ax.grid(alpha=.2); ax.legend(fontsize=9)


def graficos(X, y, partes, nombres, modelos, salida):
    # Mismo PCA original para comparar dónde asignan grupos ambos modelos.
    base = modelos["referencia"]
    P = transformar(X, nombres, base)["proyeccion"]
    disponibles = [p for p in ("entrenamiento", "validacion") if np.any(partes == p)]
    fig, axs = plt.subplots(2, len(disponibles), figsize=(7*len(disponibles), 10),
                            squeeze=False, sharex=True, sharey=True, layout="constrained")
    for fila, nombre_modelo in enumerate(("referencia", "seleccionada")):
        pred = transformar(X, nombres, modelos[nombre_modelo])
        etiquetas = np.array([f"G{g}" for g in pred["grupos"]])
        for col, part in enumerate(disponibles):
            m = partes == part
            panel(axs[fila, col], P[m], etiquetas[m], ["G0", "G1", "G2"],
                  f"{nombre_modelo} · {part}", base["pca"])
    fig.suptitle("Grupos sobre el mismo PCA de referencia; numeración arbitraria", fontsize=14)
    fig.savefig(salida / "comparacion_grupos.png", dpi=150); plt.close(fig)
    nuevo = modelos["seleccionada"]
    pred = transformar(X, nombres, nuevo)
    centros = nuevo["pca"].transform(nuevo["kmeans"].cluster_centers_)
    fig, axs = plt.subplots(2, len(disponibles), figsize=(7*len(disponibles), 10),
                            squeeze=False, sharex=True, sharey=True, layout="constrained")
    for col, part in enumerate(disponibles):
        m = partes == part
        panel(axs[0, col], pred["proyeccion"][m], y[m], sorted(set(y)),
              f"Identidad real · {part}", nuevo["pca"])
        panel(axs[1, col], pred["proyeccion"][m], np.array([f"G{g}" for g in pred["grupos"][m]]),
              ["G0", "G1", "G2"], f"Grupo asignado · {part}", nuevo["pca"], centroides=centros)
    fig.suptitle(f"PCA de las {len(nuevo['indices'])} columnas seleccionadas; ajuste solo entrenamiento", fontsize=14)
    fig.savefig(salida / "pca_seleccionada.png", dpi=150); plt.close(fig)


def ejecutar(raiz=RAIZ, extraccion="", config_path="config/mejora_huellas_v1.json"):
    raiz = Path(raiz).resolve()
    config = leer_json(raiz / config_path)
    if (config["kmeans"]["n_clusters"] != 3 or
            sorted(config["fracciones_conservar"]) != [.25, .5, 1.0]):
        raise ValueError("Este experimento compara únicamente referencia, mitad y cuarto, con k=3.")
    datos = preparar(raiz, "huellas", extraccion, {})
    X, y, nombres, train = datos["X"], datos["y"], datos["nombres"], datos["train"]
    # Prueba/intrusos ya quedaron fuera de X. Elegir recibe SOLO entrenamiento.
    elegida, cv, detalles, pliegues = elegir_con_cv(X[train], y[train], nombres, config)
    corte = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    salida = raiz / "resultados/mejora_huellas" / corte
    salida.mkdir(parents=True, exist_ok=False)
    guardar_csv(salida / "comparacion_cv_train.csv", cv)
    guardar_csv(salida / "detalle_cv_train.csv", detalles)
    for r in pliegues:
        r["muestra"] = str(datos["ids"][train][r["fila_train"]])
    guardar_csv(salida / "pliegues_train.csv", pliegues)
    decision = dict(columnas_elegidas=elegida, criterio=config["criterio"],
                    elegida_sin_validacion=True, cv=cv, config=config)
    guardar_json(salida / "decision_solo_train.json", decision)
    modelos = {nombre: ajustar(X[train], y[train], nombres, cantidad, config, con_pca=True)
               for nombre, cantidad in [("referencia", len(nombres)), ("seleccionada", elegida)]}
    orden, tabla = ranking_entrenamiento(X[train], y[train], nombres)
    puestos = {int(j): i+1 for i, j in enumerate(orden)}
    for j, r in enumerate(tabla):
        r.update(puesto=puestos[j], seleccionada=j in modelos["seleccionada"]["indices"])
    guardar_csv(salida / "ranking_y_seleccion.csv", sorted(tabla, key=lambda r: r["puesto"]))
    guardar_csv(salida / "catalogo_uso.csv", datos["catalogo_uso"])
    resumen = dict(fecha_utc=corte, python=platform.python_version(), plataforma=platform.platform(),
        dependencias={p: importlib.metadata.version(p) for p in
                      ("numpy", "scipy", "Pillow", "matplotlib", "scikit-learn")},
        extraccion=datos["carpeta"].relative_to(raiz).as_posix(),
        manifiesto_extraccion_sha256=sha(datos["carpeta"] / "manifiesto.json"),
        config=config, columnas_originales=len(nombres), columnas_elegidas=elegida,
        seleccion_supervisada=True, prueba_analizada=False, intrusos_analizados=False,
        nota_cv="CV interna entre variantes de tres bases conocidas; no prueba independencia biométrica.",
        cv=cv, modelos={})
    filas_perfil, predicciones = [], []
    for nombre_modelo, modelo in modelos.items():
        carpeta = salida / nombre_modelo
        carpeta.mkdir()
        pred = transformar(X, nombres, modelo)
        resumen["modelos"][nombre_modelo] = {}
        for part in ("entrenamiento", "validacion"):
            m = datos["particiones"] == part
            if not m.any():
                continue
            met = evaluar(y[m], {k: pred[k][m] for k in ("grupos", "identidades")})
            resumen["modelos"][nombre_modelo][part] = met
            guardar_csv(carpeta / f"identidad_grupo_{part}.csv", met["tabla_identidad_grupo"])
            for perfil in sorted({r["perfil"] for r, ok in zip(datos["filas"], m) if ok}):
                sub = m & np.array([r["perfil"] == perfil for r in datos["filas"]])
                filas_perfil.append(dict(modelo=nombre_modelo, particion=part, perfil=perfil,
                    n=int(sub.sum()), coincidencia=float(np.mean(pred["identidades"][sub] == y[sub]))))
        for i, r in enumerate(datos["filas"]):
            predicciones.append(dict(modelo=nombre_modelo, muestra=str(datos["ids"][i]),
                particion=str(datos["particiones"][i]), identidad_real=str(y[i]), perfil=r["perfil"],
                grupo=int(pred["grupos"][i]), identidad_asignada=str(pred["identidades"][i]),
                PC1=float(pred["proyeccion"][i, 0]), PC2=float(pred["proyeccion"][i, 1])))
        with (carpeta / "modelo.pkl").open("wb") as f:
            pickle.dump(modelo, f, protocol=5)
        np.savez_compressed(carpeta / "parametros.npz", indices=modelo["indices"], nombres=nombres,
            nombres_seleccionados=np.array(modelo["nombres_seleccionados"]),
            media=modelo["escalador"].mean_, escala=modelo["escalador"].scale_,
            centroides=modelo["kmeans"].cluster_centers_, componentes=modelo["pca"].components_,
            media_pca=modelo["pca"].mean_, varianza=modelo["pca"].explained_variance_ratio_)
        guardar_json(carpeta / "correspondencia.json", modelo["correspondencia"])
        guardar_csv(carpeta / "escalado.csv", [dict(caracteristica=n,
            media=float(modelo["escalador"].mean_[j]), escala=float(modelo["escalador"].scale_[j]))
            for j, n in enumerate(modelo["nombres_seleccionados"])])
    # Solo dos variantes finales y tres semillas prefijadas. Ninguna se elige por validación.
    estabilidad = []
    for nombre_modelo, cantidad in [("referencia", len(nombres)), ("seleccionada", elegida)]:
        for seed in config["semillas_estabilidad"]:
            modelo = ajustar(X[train], y[train], nombres, cantidad, config, semilla=seed)
            pred = transformar(X, nombres, modelo)
            for part in ("entrenamiento", "validacion"):
                m = datos["particiones"] == part
                if m.any():
                    met = evaluar(y[m], {k: pred[k][m] for k in ("grupos", "identidades")})
                    estabilidad.append(dict(modelo=nombre_modelo, semilla=seed, particion=part,
                                             ari=met["ari"], coincidencia=met["coincidencia"]))
    guardar_csv(salida / "estabilidad.csv", estabilidad)
    guardar_csv(salida / "resultados_por_perfil.csv", filas_perfil)
    guardar_csv(salida / "predicciones.csv", predicciones)
    ref_val = resumen["modelos"]["referencia"].get("validacion")
    nueva_val = resumen["modelos"]["seleccionada"].get("validacion")
    resumen["mejora_confirmada_en_validacion_desarrollo"] = (
        None if ref_val is None else bool(
            nueva_val["ari"] > ref_val["ari"] and
            nueva_val["coincidencia"] >= ref_val["coincidencia"] and
            all(nueva_val["acierto_por_identidad"][c] >= v
                for c, v in ref_val["acierto_por_identidad"].items())))
    resumen["familias_seleccionadas"] = dict(Counter(
        n.rsplit("_", 1)[-1] for n in modelos["seleccionada"]["nombres_seleccionados"]))
    graficos(X, y, datos["particiones"], nombres, modelos, salida)
    shutil.copyfile(datos["carpeta"] / "manifiesto.json", salida / "manifiesto_extraccion.json")
    shutil.copyfile(datos["carpeta"] / "config_efectiva.json", salida / "config_extractor_efectiva.json")
    for p in [Path(__file__), raiz / config_path, raiz / "src/clusterizacion_pca.py",
              raiz / "src/verificacion_estadistica.py"]:
        shutil.copyfile(p, salida / p.name)
    resumen["archivos_sha256"] = {p.relative_to(salida).as_posix(): sha(p)
                                   for p in salida.rglob("*") if p.is_file()}
    guardar_json(salida / "resumen.json", resumen)
    print("Salida:", salida.relative_to(raiz))
    print("CV usando SOLO entrenamiento:", cv)
    print("Columnas elegidas:", elegida)
    for nombre, resultados in resumen["modelos"].items():
        for part, met in resultados.items():
            print(nombre, part, "ARI:", round(met["ari"], 4),
                  "Coincidencia:", f"{100*met['coincidencia']:.2f}%",
                  "Por identidad:", met["acierto_por_identidad"])
    return salida, resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraccion", default="", help="Carpeta relativa exacta; vacío elige corte compatible.")
    args = parser.parse_args()
    ejecutar(extraccion=args.extraccion)
