"""Referencia PCA/K-means. Reutiliza contratos y diagnóstico del notebook 05.

No cambia extractores, revisiones ni particiones. No evalúa prueba ni intrusos.
"""
from collections import Counter
from datetime import datetime, timezone
import argparse
import importlib.metadata
import platform
from pathlib import Path
import pickle
import shutil

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import linear_sum_assignment
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score

from verificacion_estadistica import (
    cargar_ejecucion, aplicar_mapa_audio, leer_json, guardar_json,
    guardar_csv, cantidades, separacion, estadisticas, sha,
)

RAIZ = Path(__file__).resolve().parents[1]
PARTICIONES = ("entrenamiento", "validacion")


def preparar(raiz, modalidad, ruta, config):
    """Comprueba el corte vigente y selecciona desarrollo sin cambiar datos."""
    datos = cargar_ejecucion(raiz, modalidad, ruta)
    cat, filas = datos["catalogo"], datos["filas"]
    if modalidad == "audio":
        mapa = leer_json(raiz / config["mapa_audio"])
        cat = aplicar_mapa_audio(cat, mapa)
        filas = aplicar_mapa_audio(filas, mapa)
        campo, etiqueta, identificador = "particion_analisis", "comando", "muestra_id"
        if any(r[campo] == "sin_asignar" for r in cat):
            raise ValueError("Asigná los hablantes pendientes antes de ajustar PCA.")
        # El mapa es único por hablante; verificamos además el resultado aplicado.
        voces = {p: {r["hablante"] for r in cat if r[campo] == p}
                 for p in (*PARTICIONES, "prueba")}
        if any(voces[a] & voces[b] for a, b in
               [("entrenamiento", "validacion"), ("entrenamiento", "prueba"), ("validacion", "prueba")]):
            raise ValueError("Hay hablantes compartidos entre particiones.")
    else:
        campo, etiqueta, identificador = "particion", "identidad", "muestra"

    def desarrollo(r):
        return r[campo] in PARTICIONES and (
            r["grupo"] == "autorizado" if modalidad == "huellas"
            else r["decision_revision"] != "excluir")

    problemas = [r[identificador] for r in cat if desarrollo(r) and
                (r["estado_extraccion"] != "vectorizada" or
                 (modalidad == "audio" and r["decision_revision"] != "conservar"))]
    if problemas:
        raise ValueError(f"Muestras pendientes o sin vector: {problemas}. Revisar sin descartarlas.")
    usar = np.array([desarrollo(r) for r in filas])
    seleccion = [r for r, ok in zip(filas, usar) if ok]
    X = datos["X"][usar]
    if not len(X) or not np.isfinite(X).all():
        raise ValueError("Se necesitan vectores finitos de desarrollo.")
    particiones = np.array([r[campo] for r in seleccion])
    y = np.array([r[etiqueta] for r in seleccion])
    train = particiones == "entrenamiento"
    if train.sum() < 3 or len(set(y[train])) != 3:
        raise ValueError("Se requieren las tres clases en entrenamiento.")
    if set(y[~train]) - set(y[train]):
        raise ValueError("Validación contiene clases desconocidas.")
    if np.all(np.ptp(X[train], axis=0) == 0):
        raise ValueError("Todas las columnas son constantes: PCA no es interpretable.")
    cat_uso = []
    for r in cat:
        motivo = ("reservada_prueba" if r[campo] == "prueba" else
                  "intruso_pendiente_calibracion" if modalidad == "huellas" and r["grupo"] != "autorizado" else
                  "excluida_revision" if modalidad == "audio" and r["decision_revision"] == "excluir" else
                  "desarrollo")
        cat_uso.append(dict(r, uso_etapa=motivo))
    datos.update(X=X, filas=seleccion, catalogo_uso=cat_uso, y=y,
                 particiones=particiones, train=train, campo_particion=campo,
                 ids=np.array([r[identificador] for r in seleccion]))
    return datos


def diagnostico(X, Z, y, nombres, salida):
    """Misma razón entre/dentro que el notebook 05; solo entrenamiento."""
    tabla = separacion(X, y, nombres)
    est = separacion(Z, y, nombres)
    for r, s in zip(tabla, est):
        # RMS interno estandarizado, comparable entre unidades distintas.
        r["dispersion_interna_estandarizada"] = float(np.sqrt(s["suma_dentro"] / len(Z)))
    tabla.sort(key=lambda r: (-r["dispersion_interna_estandarizada"], r["caracteristica"]))
    guardar_csv(salida / "diagnostico_dispersion.csv", tabla)
    guardar_csv(salida / "medias_desviaciones_train.csv", estadisticas(X, y, nombres))
    return tabla


def proyectar_paneles(P, etiquetas, particiones, pca, titulo, salida,
                      centroides=None, componentes=(0, 1)):
    """Paneles separados con la misma escala y colores estables por etiqueta."""
    presentes = [p for p in PARTICIONES if np.any(particiones == p)]
    fig, axs = plt.subplots(1, len(presentes), figsize=(7 * len(presentes), 6),
                            squeeze=False, sharex=True, sharey=True, layout="constrained")
    clases = sorted(set(etiquetas))
    colores = {c: plt.get_cmap("tab10")(i % 10) for i, c in enumerate(clases)}
    a, b = componentes
    for ax, part in zip(axs.flat, presentes):
        for clase in clases:
            m = (particiones == part) & (etiquetas == clase)
            if m.any():
                ax.scatter(P[m, a], P[m, b], color=colores[clase], s=42,
                           alpha=.75, marker="o" if part == "entrenamiento" else "^", label=str(clase))
        if centroides is not None:
            ax.scatter(centroides[:, a], centroides[:, b], marker="X", s=200,
                       c="black", edgecolors="white", label="Centroides de entrenamiento")
            for k, centro in enumerate(centroides):
                ax.annotate(f"G{k}", (centro[a], centro[b]), xytext=(7, 7), textcoords="offset points")
        ax.set(title=f"{titulo} · {part}",
               xlabel=f"PC{a+1} ({100*pca.explained_variance_ratio_[a]:.1f} %)",
               ylabel=f"PC{b+1} ({100*pca.explained_variance_ratio_[b]:.1f} %)")
        ax.grid(alpha=.2)
        ax.legend(fontsize=9)
    fig.savefig(salida, dpi=160)
    plt.close(fig)


def ajustar(datos, modalidad, config, salida):
    salida.mkdir()
    X, train, y = datos["X"], datos["train"], datos["y"]
    nombres = datos["nombres"]
    # La entrada conserva sus 144/160 columnas. ddof=0 en StandardScaler.
    scaler = StandardScaler(with_mean=True, with_std=True).fit(X[train])
    Z = scaler.transform(X)
    pca = PCA(**config["pca"]).fit(Z[train])
    P = pca.transform(Z)
    constantes = nombres[np.ptp(X[train], axis=0) == 0].tolist()
    tabla = diagnostico(X[train], Z[train], y[train], nombres, salida)
    acumulada = np.cumsum(pca.explained_variance_ratio_)
    resumen = dict(muestras_por_particion=dict(Counter(datos["particiones"])),
                   caracteristicas_entrada=X.shape[1], constantes_train=constantes,
                   pc1_pc2_porcentaje=float(100 * acumulada[1]),
                   pc3_porcentaje=float(100 * pca.explained_variance_ratio_[2]),
                   componentes_90=int(np.searchsorted(acumulada, .90) + 1),
                   componentes_95=int(np.searchsorted(acumulada, .95) + 1),
                   validacion_disponible=bool((~train).any()),
                   prueba_analizada=False)
    guardar_csv(salida / "parametros_escalado.csv", [
        dict(caracteristica=str(n), media=float(scaler.mean_[j]),
             desviacion_ddof0=float(np.sqrt(scaler.var_[j])), escala=float(scaler.scale_[j]),
             constante_train=str(n) in constantes) for j, n in enumerate(nombres)])
    guardar_csv(salida / "varianza_explicada.csv", [
        dict(componente=i+1, proporcion=float(v), acumulada=float(acumulada[i]))
        for i, v in enumerate(pca.explained_variance_ratio_)])
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    ax.plot(np.arange(1, len(acumulada)+1), 100*acumulada, color="#2463a0", linewidth=2)
    for nivel in (90, 95):
        ax.axhline(nivel, linestyle="--", alpha=.5, label=f"{nivel} %")
    ax.set(xlabel="Cantidad de componentes", ylabel="Varianza acumulada (%)",
           title=f"{modalidad.capitalize()} · PCA ajustado con entrenamiento", ylim=(0, 102))
    ax.grid(alpha=.2); ax.legend()
    fig.savefig(salida / "varianza_acumulada.png", dpi=160); plt.close(fig)
    proyectar_paneles(P, y, datos["particiones"], pca,
                      "Identidad real" if modalidad == "huellas" else "Palabra",
                      salida / "pca_clases.png")
    if modalidad in config["mostrar_pc3"]:
        proyectar_paneles(P, y, datos["particiones"], pca, "Vista complementaria PC1-PC3",
                          salida / "pca_pc3.png", componentes=(0, 2))
    modelo = dict(escalador=scaler, pca=pca, nombres=nombres.tolist(),
                  modalidad=modalidad, kmeans=None, correspondencia=None)
    grupos = None
    if modalidad == "audio":
        voces = np.array([r["hablante"] for r in datos["filas"]])
        proyectar_paneles(P, voces, datos["particiones"], pca, "Hablante (mismas coordenadas)",
                          salida / "pca_hablantes.png")
        condicionales = []
        for analisis, estratos, etiquetas in [("palabra_dentro_hablante", voces, y),
                                             ("hablante_dentro_palabra", y, voces)]:
            for estrato in sorted(set(estratos[train])):
                mask = train & (estratos == estrato)
                condicionales.extend(dict(analisis=analisis, estrato=str(estrato), **r)
                    for r in separacion(X[mask], etiquetas[mask], nombres))
        guardar_csv(salida / "separacion_condicional.csv", condicionales)
    else:
        km = KMeans(random_state=config["semilla"], **config["kmeans"]).fit(Z[train])
        grupos = km.predict(Z)  # No se entrena sobre PC1-PC2.
        clases = sorted(set(y[train]))
        tabla_train = np.array([[np.sum(train & (y == c) & (grupos == g))
                                for g in range(3)] for c in clases])
        filas, columnas = linear_sum_assignment(-tabla_train)
        correspondencia = {int(g): str(clases[f]) for f, g in zip(filas, columnas)}
        modelo.update(kmeans=km, correspondencia=correspondencia)
        resumen.update(correspondencia_solo_train=correspondencia,
                       inercia_train=float(km.inertia_), iteraciones=int(km.n_iter_))
        for part in PARTICIONES:
            m = datos["particiones"] == part
            if not m.any():
                continue
            resumen[f"ari_{part}"] = float(adjusted_rand_score(y[m], grupos[m]))
            resumen[f"coincidencia_mapa_train_{part}"] = float(np.mean(
                [correspondencia[int(g)] == real for g, real in zip(grupos[m], y[m])]))
            guardar_csv(salida / f"identidad_grupo_{part}.csv", [
                dict(identidad=c, **{f"G{g}": int(np.sum(m & (y == c) & (grupos == g)))
                                    for g in range(3)}) for c in clases])
        proyectar_paneles(P, np.array([f"G{g}" for g in grupos]), datos["particiones"], pca,
                          f"K-means ({X.shape[1]} características)",
                          salida / "pca_grupos.png", centroides=pca.transform(km.cluster_centers_))
    registros = []
    for i, row in enumerate(datos["filas"]):
        registros.append(dict(muestra=str(datos["ids"][i]), particion=str(datos["particiones"][i]),
                              clase=str(y[i]), hablante=row.get("hablante", ""),
                              grupo="" if grupos is None else int(grupos[i]),
                              PC1=float(P[i, 0]), PC2=float(P[i, 1]), PC3=float(P[i, 2])))
    guardar_csv(salida / "proyecciones.csv", registros)
    guardar_csv(salida / "catalogo_uso.csv", datos["catalogo_uso"])
    guardar_csv(salida / "cantidades.csv", cantidades(datos["filas"],
                [datos["campo_particion"], "identidad" if modalidad == "huellas" else "hablante",]
                + ([] if modalidad == "huellas" else ["comando"])))
    # Formato sencillo de sklearn. Cargar solo modelos propios y con el mismo entorno.
    with (salida / "modelos.pkl").open("wb") as f:
        pickle.dump(modelo, f, protocol=5)
    np.savez_compressed(salida / "parametros.npz", nombres=nombres, media=scaler.mean_,
                        escala=scaler.scale_, media_pca=pca.mean_, componentes=pca.components_,
                        varianza_explicada=pca.explained_variance_ratio_,
                        centroides=np.empty((0, len(nombres))) if grupos is None else modelo["kmeans"].cluster_centers_)
    guardar_json(salida / "resumen.json", resumen)
    return resumen, modelo, tabla


def transformar_nuevas(X, nombres, modelo):
    """Reutiliza parámetros sin fit. Grupo asignado NO significa autorización."""
    X = np.atleast_2d(np.asarray(X, dtype=float))
    if list(nombres) != modelo["nombres"] or X.shape[1] != len(nombres):
        raise ValueError("Nombres, cantidad u orden de características incorrectos.")
    if not np.isfinite(X).all():
        raise ValueError("Nueva muestra con valores no finitos.")
    Z = modelo["escalador"].transform(X)
    return dict(pca=modelo["pca"].transform(Z),
                grupos=None if modelo["kmeans"] is None else modelo["kmeans"].predict(Z))


def ejecutar(raiz=RAIZ, huellas="", audio="", config_path="config/clusterizacion_pca_v1.json"):
    raiz = Path(raiz).resolve()
    config = leer_json(raiz / config_path)
    if config["kmeans"]["n_clusters"] != 3 or config["pca"]["n_components"] is not None:
        raise ValueError("La referencia requiere k=3 y PCA completo.")
    datos = {m: preparar(raiz, m, ruta, config) for m, ruta in [("huellas", huellas), ("audio", audio)]}
    corte = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    salida = raiz / "resultados/clusterizacion_pca" / corte
    salida.mkdir(parents=True, exist_ok=False)
    registro = dict(fecha_utc=corte, python=platform.python_version(), plataforma=platform.platform(),
                    dependencias={p: importlib.metadata.version(p) for p in
                                  ("numpy", "scipy", "Pillow", "matplotlib", "scikit-learn")},
                    config=config, prueba_analizada=False, fuentes={})
    for m, d in datos.items():
        registro[m], _, _ = ajustar(d, m, config, salida / m)
        registro["fuentes"][m] = dict(extraccion=d["carpeta"].relative_to(raiz).as_posix(),
            manifiesto_sha256=sha(d["carpeta"] / "manifiesto.json"),
            muestras_usadas=d["ids"].tolist(), nombres=d["nombres"].tolist())
    for p in [raiz / config_path, raiz / config["mapa_audio"],
              Path(__file__), raiz / "src/verificacion_estadistica.py"]:
        shutil.copyfile(p, salida / p.name)
    registro["archivos_sha256"] = {p.relative_to(salida).as_posix(): sha(p)
                                    for p in salida.rglob("*") if p.is_file()}
    guardar_json(salida / "resumen.json", registro)
    print("Resultados:", salida.relative_to(raiz))
    for m in datos:
        print(m, registro[m])
    return salida, registro


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--huellas", default="", help="Carpeta exacta de extracción, opcional")
    parser.add_argument("--audio", default="", help="Carpeta exacta de extracción, opcional")
    args = parser.parse_args()
    ejecutar(huellas=args.huellas, audio=args.audio)
