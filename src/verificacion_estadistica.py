"""Diagnóstico por columna; no ajusta modelos ni modifica los catálogos."""
from collections import Counter
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np


def leer_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def guardar_json(p, objeto):
    Path(p).write_text(json.dumps(objeto, ensure_ascii=False, indent=2,
                                allow_nan=False), encoding="utf-8")


def guardar_csv(p, filas, campos=None):
    filas = list(filas)
    campos = campos or (list(filas[0]) if filas else ["sin_registros"])
    with Path(p).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)


def cargar_ejecucion(raiz, modalidad, relativa=""):
    """Reutiliza NPZ y contrato del extractor; rechaza cortes desactualizados."""
    raiz = Path(raiz).resolve()
    if modalidad == "huellas":
        import caracteristicas_huellas as extractor
        config = raiz / "config/caracteristicas_huellas_glcm_v1.json"
        origen = raiz / "datos/procesados/normalizacion_final_v1/catalogo_normalizado.csv"
        dependencias = ("numpy", "scipy", "Pillow")
        clave_id = "muestra"
    elif modalidad == "audio":
        import caracteristicas_audio as extractor
        config = raiz / "config/caracteristicas_audio_v1.json"
        activo = leer_json(raiz / "datos/audio/procesados/actual.json")
        origen = raiz / activo["ruta_catalogo"]
        dependencias = ("numpy", "scipy")
        clave_id = "muestra_id"
    else:
        raise ValueError("Modalidad desconocida.")
    cfg = extractor.cargar_config(config)
    deps = {p: importlib.metadata.version(p) for p in dependencias}
    candidatos = ([raiz / relativa / "manifiesto.json"] if relativa else
                  sorted((raiz / f"datos/caracteristicas/{modalidad}").glob(
                      "*/ejecucion_*/manifiesto.json")))
    compatibles = []
    for p in candidatos:
        if p.parent.name.endswith(".parcial"):
            continue
        m = leer_json(p)
        c = m["contrato"]
        codigo_ok = True
        for nombre, digest in c["codigo"].items():
            fuente = raiz / "src" / nombre
            if modalidad == "audio":
                texto = fuente.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
                actual_sha = hashlib.sha256(texto.encode()).hexdigest()
            else:
                actual_sha = sha(fuente)
            codigo_ok &= actual_sha == digest
        if (c["config"] == cfg and c["dependencias"] == deps and codigo_ok
                and sha(p.parent / "catalogo_origen.csv") == sha(origen)
                and not m.get("incluir_prueba", False)):
            if modalidad == "audio":
                # Reutiliza el control de revisiones y del procedimiento vigente.
                from extraer_dataset_audio import cargar_activo
                _, _, _, soporte, _ = cargar_activo(raiz)
                if any(sha(v) != m["sha256_entradas"].get(k)
                       for k, v in soporte.items()):
                    continue
            compatibles.append(p)
    if not compatibles:
        raise FileNotFoundError(f"Regenerá las características de {modalidad}; no hay corte compatible.")
    if len({p.parent.parent.name for p in compatibles}) != 1:
        raise ValueError(f"Hay varios contratos de {modalidad}; indicá su ruta exacta.")
    p = sorted(compatibles, key=lambda p: p.parent.name)[-1]
    carpeta, m = p.parent, leer_json(p)
    for nombre, digest in m["sha256_archivos"].items():
        if sha(carpeta / nombre) != digest:
            raise ValueError(f"Archivo modificado: {carpeta / nombre}")
    with (carpeta / "catalogo_caracteristicas.csv").open(encoding="utf-8-sig", newline="") as f:
        catalogo = list(csv.DictReader(f))
    with np.load(carpeta / "vectores.npz", allow_pickle=False) as z:
        X, ids, nombres = z["X"].copy(), z["muestras"].copy(), z["nombres"].copy()
    if X.shape != (len(ids), len(nombres)) or len(set(ids)) != len(ids):
        raise ValueError("Dimensiones o IDs incoherentes.")
    if nombres.tolist() != extractor.nombres_caracteristicas(cfg):
        raise ValueError("Orden de características distinto del extractor.")
    if len(set(r[clave_id] for r in catalogo)) != len(catalogo):
        raise ValueError("Catálogo con IDs duplicados.")
    filas = [None] * len(ids)
    for r in catalogo:
        if r["estado_extraccion"] == "vectorizada":
            k = int(r["fila_vector"])
            if not 0 <= k < len(ids) or ids[k] != r[clave_id] or filas[k] is not None:
                raise ValueError("Desalineación de IDs y fila_vector.")
            filas[k] = r
        elif r["fila_vector"]:
            raise ValueError("Una fila no vectorizada tiene índice.")
    if any(r is None for r in filas):
        raise ValueError("Faltan filas de catálogo para la matriz.")
    return dict(X=X, ids=ids, nombres=nombres, filas=filas, catalogo=catalogo,
                carpeta=carpeta, manifiesto=m)


def aplicar_mapa_audio(catalogo, mapa):
    """Capa explícita de partición. Nuevos hablantes y conflictos bloquean el uso."""
    por_hablante = mapa["hablantes"]
    salida = []
    for r in catalogo:
        if r["hablante"] not in por_hablante:
            raise ValueError(f"Asignar explícitamente al nuevo hablante {r['hablante']} en el mapa.")
        destino = por_hablante[r["hablante"]]["particion"]
        if destino not in {"entrenamiento", "validacion", "prueba", "sin_asignar"}:
            raise ValueError("Partición desconocida en el mapa.")
        if r["particion"] not in {"sin_asignar", destino}:
            raise ValueError(f"Conflicto con partición ya fijada: {r['muestra_id']}")
        salida.append(dict(r, particion_analisis=destino))
    return salida


def cantidades(filas, campos):
    conteo = Counter(tuple(r[c] for c in campos) for r in filas)
    return [dict(zip(campos, valores), n=n) for valores, n in sorted(conteo.items())]


def nombre_legible(nombre):
    if nombre.startswith("s") and "_" in nombre:
        segmento, medida = nombre.split("_", 1)
        return f"Segmento {int(segmento[1:])}: {medida.replace('_', ' ')}"
    return (nombre.replace("NO_SE", "NO+SE").replace("NE_SO", "NE+SO")
            .replace("_d", ", distancia nominal ").replace("_a", " px, ángulo ")
            .replace("_", " "))


def controles(X, ids, nombres, etiquetas):
    """Reporta antes de calcular; no imputa ni elimina muestras."""
    no_finitos = [dict(muestra=str(ids[i]), caracteristica=str(nombres[j]), valor=str(X[i, j]))
                 for i, j in np.argwhere(~np.isfinite(X))]
    constantes = []
    for clase in ["TODAS", *sorted(set(etiquetas))]:
        datos = X if clase == "TODAS" else X[etiquetas == clase]
        for j, nombre in enumerate(nombres):
            if len(datos) and np.isfinite(datos[:, j]).all() and np.ptp(datos[:, j]) == 0:
                constantes.append(dict(clase=clase, caracteristica=str(nombre), n=len(datos),
                                       valor=float(datos[0, j]),
                                       estado="constante" if len(datos) >= 2 else "solo_una_muestra"))
    return no_finitos, constantes


def estadisticas(X, etiquetas, nombres):
    """Una fila por clase y característica; DE muestral entre grabaciones/imágenes."""
    if not np.isfinite(X).all():
        raise ValueError("Hay no finitos: revisar el informe, sin descartar filas automáticamente.")
    salida = []
    for clase in sorted(set(etiquetas)):
        datos = X[etiquetas == clase]
        medias = datos.mean(axis=0)
        desvio = datos.std(axis=0, ddof=1) if len(datos) >= 2 else [None] * X.shape[1]
        for j, nombre in enumerate(nombres):
            salida.append(dict(clase=str(clase), caracteristica=str(nombre),
                               descripcion=nombre_legible(str(nombre)), n=len(datos),
                               media=float(medias[j]),
                               desviacion_muestral=None if len(datos) < 2 else float(desvio[j]),
                               estado="n_menor_2" if len(datos) < 2 else "ok"))
    return salida


def separacion(X, etiquetas, nombres):
    """Único indicador: S = suma n_c(mu_c-mu)^2 / suma (x_ic-mu_c)^2."""
    if not len(X) or not np.isfinite(X).all():
        raise ValueError("Se requieren datos finitos y al menos una muestra.")
    clases = sorted(set(etiquetas))
    global_media = X.mean(axis=0)
    entre = np.zeros(X.shape[1])
    dentro = np.zeros(X.shape[1])
    for clase in clases:
        datos = X[etiquetas == clase]
        media = datos.mean(axis=0)
        entre += len(datos) * (media - global_media) ** 2
        dentro += ((datos - media) ** 2).sum(axis=0)
    resultado = []
    for j, nombre in enumerate(nombres):
        if len(clases) < 2 or len(X) <= len(clases):
            valor, estado = None, "insuficiente"
        elif np.ptp(X[:, j]) == 0:
            valor, estado = None, "constante_global_0_0"
        elif dentro[j] == 0:
            valor, estado = None, "infinita_dispersion_interna_nula"
        else:
            valor, estado = float(entre[j] / dentro[j]), "ok"
        resultado.append(dict(caracteristica=str(nombre), descripcion=nombre_legible(str(nombre)),
                              separacion=valor, estado=estado,
                              suma_entre=float(entre[j]), suma_dentro=float(dentro[j]),
                              clases=len(clases), n=len(X)))
    return resultado


def representantes(indicadores):
    # Orden ascendente; desempate por nombre. No usar prueba ni elegir a mano.
    validos = sorted([r for r in indicadores if r["estado"] in {
        "ok", "infinita_dispersion_interna_nula"}],
        key=lambda r: (float("inf") if r["separacion"] is None else r["separacion"],
                       r["caracteristica"]))
    if not validos:
        return []
    indices = [0, (len(validos) - 1) // 2, len(validos) - 1]
    return [dict(criterio=criterio, **validos[i]) for criterio, i in
            zip(["separacion_baja", "separacion_mediana", "separacion_alta"], indices)]


def grafico(X, etiquetas, nombres, elegidas, hablantes=None):
    import matplotlib.pyplot as plt
    if not elegidas:
        return None
    fig, axs = plt.subplots(len(elegidas), 1, figsize=(15, 4.4 * len(elegidas)),
                            squeeze=False, constrained_layout=True)
    clases = sorted(set(etiquetas))
    rng = np.random.default_rng(20261022)  # Solo desplaza puntos horizontalmente.
    voces = sorted(set(hablantes)) if hablantes is not None else []
    colores = plt.get_cmap("tab10")
    for ax, r in zip(axs.flat, elegidas):
        j = list(nombres).index(r["caracteristica"])
        for k, clase in enumerate(clases):
            mascara = etiquetas == clase
            valores = X[mascara, j]
            posiciones = k + rng.uniform(-.20, .20, len(valores))
            if voces:
                for h, voz in enumerate(voces):
                    sub = hablantes[mascara] == voz
                    ax.scatter(posiciones[sub], valores[sub], s=24, alpha=.65,
                               color=colores(h % 10), label=voz if k == 0 else None)
            else:
                ax.scatter(posiciones, valores, s=24, alpha=.55, color="#3679a8")
            if len(valores) >= 2:
                ax.errorbar(k, valores.mean(), yerr=valores.std(ddof=1),
                            fmt="D", color="black", capsize=8, markersize=7, linewidth=2)
            else:
                ax.plot(k, valores.mean(), "D", color="black")
        ax.set_xticks(range(len(clases)), [f"{c}\n(n={sum(etiquetas == c)})" for c in clases])
        ax.set_title(f"{r['criterio'].replace('_', ' ')}: {r['caracteristica']}", fontsize=13)
        ax.set_ylabel("Valor original de esta característica")
        ax.grid(axis="y", alpha=.2)
        if voces:
            ax.legend(title="Hablante", ncol=min(len(voces), 6), fontsize=9)
    fig.suptitle("Puntos: muestras individuales | Rombo y barra: media ± DE muestral", fontsize=14)
    return fig


def analizar(carpeta, X, ids, nombres, etiquetas, hablantes=None):
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=False)
    etiquetas = np.asarray(etiquetas)
    if not len(X):
        raise ValueError("No hay muestras de entrenamiento elegibles.")
    errores, constantes = controles(X, ids, nombres, etiquetas)
    guardar_csv(carpeta / "no_finitos.csv", errores, ["muestra", "caracteristica", "valor"])
    guardar_csv(carpeta / "constantes.csv", constantes,
                ["clase", "caracteristica", "n", "valor", "estado"])
    if errores:
        raise ValueError(f"No finitos: {carpeta / 'no_finitos.csv'}. Análisis detenido.")
    tabla = estadisticas(X, etiquetas, nombres)
    indicadores = separacion(X, etiquetas, nombres)
    elegidas = representantes(indicadores)
    guardar_csv(carpeta / "medias_desviaciones.csv", tabla)
    guardar_csv(carpeta / "separacion.csv", indicadores)
    guardar_csv(carpeta / "caracteristicas_mostradas.csv", elegidas)
    fig = grafico(X, etiquetas, nombres, elegidas, hablantes)
    if fig is not None:
        fig.savefig(carpeta / "distribuciones.png", dpi=150)
    if hablantes is not None:
        hablantes = np.asarray(hablantes)
        guardar_csv(carpeta / "medias_desviaciones_por_hablante.csv",
                    estadisticas(X, hablantes, nombres))
        condicionales, detalle = [], []
        for campo, estratos, grupos in [("palabra_dentro_hablante", hablantes, etiquetas),
                                       ("hablante_dentro_palabra", etiquetas, hablantes)]:
            for estrato in sorted(set(estratos)):
                mask = estratos == estrato
                condicionales.extend(dict(analisis=campo, estrato=str(estrato), **r)
                    for r in separacion(X[mask], grupos[mask], nombres))
                detalle.extend(dict(analisis=campo, estrato=str(estrato), **r)
                    for r in estadisticas(X[mask], grupos[mask], nombres))
        guardar_csv(carpeta / "separacion_condicional.csv", condicionales)
        guardar_csv(carpeta / "medias_desviaciones_condicionales.csv", detalle)
    return dict(tabla=tabla, indicadores=indicadores, elegidas=elegidas, figura=fig,
                resumen=dict(muestras=len(X), caracteristicas=X.shape[1],
                             cantidades=dict(Counter(map(str, etiquetas))),
                             no_finitos=len(errores), constantes_globales=sum(
                                 r["clase"] == "TODAS" for r in constantes)))
