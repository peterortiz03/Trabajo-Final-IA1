"""Calibra un umbral global con validación y un modelo de huellas congelado.

No ajusta escalador/PCA/K-means, no selecciona columnas y no evalúa prueba.
Lee parámetros NPZ sin pickle. FAR/FRR son tasas empíricas de calibración.
"""
import argparse
from collections import Counter
import csv
import hashlib
from datetime import datetime, timezone
import importlib.metadata
from pathlib import Path
import platform
import shutil

import matplotlib.pyplot as plt
import numpy as np

from verificacion_estadistica import cargar_ejecucion, leer_json, guardar_json, guardar_csv, sha

RAIZ = Path(__file__).resolve().parents[1]


def leer_csv(p):
    with Path(p).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def validar_parametros(m):
    """Comprueba el contrato necesario para distancias futuras."""
    n, k = len(m["nombres"]), len(m["indices"])
    if (len(set(m["nombres"].tolist())) != n or m["indices"].dtype.kind not in "iu"
            or len(set(m["indices"].tolist())) != k or k < 1
            or np.any(m["indices"] < 0) or np.any(m["indices"] >= n)):
        raise ValueError("Nombres o índices inválidos.")
    if (m["media"].shape != (k,) or m["escala"].shape != (k,)
            or m["centroides"].shape != (3, k)
            or np.any(m["escala"] <= 0)
            or any(not np.isfinite(m[c]).all() for c in ("media", "escala", "centroides"))):
        raise ValueError("Escalado o centroides incompatibles/no finitos.")
    if set(m["correspondencia"]) != {"0", "1", "2"} or len(set(m["correspondencia"].values())) != 3:
        raise ValueError("Correspondencia de grupos incompleta o no unívoca.")
    if not np.array_equal(m["nombres"][m["indices"]], m["nombres_seleccionados"]):
        raise ValueError("Orden de nombres seleccionados incompatible.")


def leer_parametros(npz, correspondencia):
    with np.load(npz, allow_pickle=False) as z:
        m = {c: z[c].copy() for c in
             ("indices", "nombres", "nombres_seleccionados", "media", "escala", "centroides")}
    m["correspondencia"] = leer_json(correspondencia)
    validar_parametros(m)
    return m


def medir_distancias(X, nombres, modelo):
    """Distancia euclidiana en columnas seleccionadas y escalado guardado; sin fit."""
    X = np.atleast_2d(np.asarray(X, dtype=float))
    if X.shape[1] != len(modelo["nombres"]) or list(nombres) != modelo["nombres"].tolist():
        raise ValueError("Cantidad, nombres u orden de características incorrectos.")
    if not np.isfinite(X).all():
        raise ValueError("Muestra no finita: revisar entrada; no clasificarla como intrusa.")
    Z = (X[:, modelo["indices"]] - modelo["media"]) / modelo["escala"]
    distancias = np.linalg.norm(Z[:, None, :] - modelo["centroides"][None, :, :], axis=2)
    grupos = np.argmin(distancias, axis=1)  # Empate exacto: menor índice.
    return distancias[np.arange(len(X)), grupos], grupos


def decidir_acceso(X, nombres, modelo, umbral):
    """Función para futuras muestras; identidad visible solo cuando se acepta."""
    if not np.isfinite(umbral) or umbral < 0:
        raise ValueError("Umbral debe ser finito y no negativo.")
    distancias, grupos = medir_distancias(X, nombres, modelo)
    return [dict(distancia=float(d), grupo_cercano=int(g), aceptada=bool(d <= umbral),
                 estado="AUTORIZADO" if d <= umbral else "NO AUTORIZADO",
                 identidad=modelo["correspondencia"][str(g)] if d <= umbral else "")
            for d, g in zip(distancias, grupos)]


def tasas(distancias, autorizado, umbral):
    aceptada = distancias <= umbral
    fa = int(np.sum(aceptada & ~autorizado))
    fr = int(np.sum(~aceptada & autorizado))
    far, frr = fa / int((~autorizado).sum()), fr / int(autorizado.sum())
    return dict(umbral=float(umbral), falsas_aceptaciones=fa, falsos_rechazos=fr,
                FAR=float(far), FRR=float(frr), error_balanceado=float((far + frr) / 2))


def elegir_umbral(distancias, autorizado):
    """Un candidato por intervalo de decisiones; no optimiza sobre prueba.

    Minimiza BER; empate por menor FAR y después menor umbral. El punto medio
    evita elegir arbitrariamente el valor exacto de una muestra como frontera.
    Si todas las distancias son cero, tau=0 es la única decisión no negativa.
    """
    d, a = np.asarray(distancias, dtype=float), np.asarray(autorizado, dtype=bool)
    if (d.ndim != 1 or a.shape != d.shape or not len(d) or not np.isfinite(d).all()
            or np.any(d < 0) or not a.any() or a.all()):
        raise ValueError("Se necesitan autorizados e intrusos con distancias finitas no negativas.")
    u = np.unique(d)
    candidatos = np.unique(np.r_[0., u[:-1] + (u[1:] - u[:-1]) / 2, u[-1]])
    curva = [tasas(d, a, tau) for tau in candidatos]
    ber = min(r["error_balanceado"] for r in curva)
    empatados = [r for r in curva if abs(r["error_balanceado"] - ber) <= 1e-12]
    elegida = min(empatados, key=lambda r: (r["FAR"], r["umbral"]))
    return elegida, curva


def cargar_modelo_congelado(raiz, carpeta, datos):
    """Evita mezclar un modelo anterior con otro entrenamiento/extractor."""
    base = Path(carpeta)
    r = leer_json(base / "resumen.json")
    archivos = ("seleccionada/parametros.npz", "seleccionada/correspondencia.json",
                "catalogo_uso.csv", "config_extractor_efectiva.json", "manifiesto_extraccion.json")
    for nombre in archivos:
        if sha(base / nombre) != r["archivos_sha256"].get(nombre):
            raise ValueError(f"Archivo de modelo modificado o no registrado: {nombre}")
    if leer_json(base / "config_extractor_efectiva.json") != leer_json(datos["carpeta"] / "config_efectiva.json"):
        raise ValueError("El modelo corresponde a otro extractor/configuración.")
    viejo = leer_csv(base / "catalogo_uso.csv")
    anteriores = {v["muestra"]: v for v in viejo
                  if v["particion"] == "entrenamiento" and v["grupo"] == "autorizado"}
    actuales = {v["muestra"]: v for v in datos["catalogo"]
                if v["particion"] == "entrenamiento" and v["grupo"] == "autorizado"}
    if anteriores.keys() != actuales.keys():
        raise ValueError("Cambió el entrenamiento. Congelar una ejecución coherente antes de calibrar.")
    for id_, row in actuales.items():
        for campo in ("identidad", "sha256_normalizada", "sha256_mascara_caracteristicas"):
            if row[campo] != anteriores[id_][campo]:
                raise ValueError(f"Cambió el entrenamiento: {id_}, {campo}")
    m = leer_parametros(base / archivos[0], base / archivos[1])
    if m["nombres"].tolist() != datos["nombres"].tolist():
        raise ValueError("Nombres del extractor/modelo distintos.")
    # Comprobación, sin asignar nuevos parámetros: los vectores deben conservar
    # las medias, escalas y centroides ya guardados. No se vuelve a entrenar.
    train = np.array([v["particion"] == "entrenamiento" and v["grupo"] == "autorizado"
                      for v in datos["filas"]])
    Xtr = datos["X"][train][:, m["indices"]]
    escala = Xtr.std(axis=0, ddof=0)
    escala[escala == 0] = 1
    if not (np.allclose(Xtr.mean(axis=0), m["media"], rtol=1e-9, atol=1e-10)
            and np.allclose(escala, m["escala"], rtol=1e-9, atol=1e-10)):
        raise ValueError("Los vectores de entrenamiento no reproducen el escalado congelado.")
    return m, r


def seleccionar_validacion(datos):
    """Solo validación; los intrusos no intervienen en ningún ajuste de centroides."""
    val = [r for r in datos["catalogo"] if r["particion"] == "validacion"]
    pendientes = [r["muestra"] for r in val if r["estado_extraccion"] != "vectorizada"]
    if pendientes:
        raise ValueError(f"Validación sin vector: {pendientes}. Revisar sin eliminar automáticamente.")
    if {r["grupo"] for r in val} != {"autorizado", "intruso"}:
        raise ValueError("Se requieren autorizados e intrusos en validación.")
    if any(r["grupo"] == "intruso" and r["particion"] == "entrenamiento" for r in datos["catalogo"]):
        raise ValueError("Hay intrusos asignados a entrenamiento; revisar el contrato del dataset.")
    # Se comparan metadatos de bases, sin leer imágenes/vectores reservados.
    bases_val = {r["sha256_base"] for r in val if r["grupo"] == "intruso"}
    bases_test = {r["sha256_base"] for r in datos["catalogo"]
                  if r["particion"] == "prueba" and r["grupo"] == "intruso"}
    if bases_val & bases_test:
        raise ValueError("Los intrusos de validación y prueba comparten base.")
    mask = np.array([r["particion"] == "validacion" for r in datos["filas"]])
    filas = [r for r, ok in zip(datos["filas"], mask) if ok]
    return datos["X"][mask], filas


def graficar(filas, curva, elegido, salida):
    fig, ax = plt.subplots(figsize=(12, 6), layout="constrained")
    ids = sorted({r["identidad_real"] for r in filas})
    for i, id_ in enumerate(ids):
        datos = [r for r in filas if r["identidad_real"] == id_]
        autorizado = datos[0]["grupo_real"] == "autorizado"
        offsets = np.linspace(-.13, .13, len(datos))
        ax.scatter([r["distancia"] for r in datos], i + offsets,
                   color="#2878b5" if autorizado else "#cf4a42", s=45,
                   label=("Autorizados" if autorizado else "Intrusos"))
        for row, offset in zip(datos, offsets):
            if row["error"]:
                ax.annotate(row["muestra"], (row["distancia"], i + offset),
                            xytext=(5, 7), textcoords="offset points", fontsize=9)
    ax.axvline(elegido["umbral"], color="black", linestyle="--", label=f"Umbral = {elegido['umbral']:.3f}")
    handles, labels = ax.get_legend_handles_labels()
    unicos = dict(zip(labels, handles))
    ax.legend(unicos.values(), unicos.keys())
    ax.set(yticks=range(len(ids)), yticklabels=ids, xlabel="Distancia euclidiana al centroide más cercano",
           title="Validación: distancias de autorizados e intrusos (modelo congelado)")
    ax.grid(alpha=.2)
    fig.savefig(salida / "distancias_validacion.png", dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
    d = np.array([r["distancia"] for r in filas])
    a = np.array([r["grupo_real"] == "autorizado" for r in filas])
    # Las tasas solo cambian al atravesar una distancia observada; no interpolar.
    puntos = np.unique(np.r_[0., d, elegido["umbral"]])
    curva_grafica = [tasas(d, a, tau) for tau in puntos]
    for campo, texto in [("FAR", "FAR: intrusos aceptados"), ("FRR", "FRR: autorizados rechazados")]:
        ax.step(puntos, [100*r[campo] for r in curva_grafica], where="post", label=texto, linewidth=2)
    ax.axvline(elegido["umbral"], color="black", linestyle="--", label="Umbral elegido")
    ax.set(xlabel="Umbral de distancia (aceptar si distancia ≤ umbral)", ylabel="Tasa empírica (%)",
           title="Calibración con validación: compromiso entre dos errores", ylim=(-2, 102))
    ax.grid(alpha=.2); ax.legend()
    fig.savefig(salida / "tasas_por_umbral.png", dpi=160); plt.close(fig)


def cargar_sistema(carpeta):
    """Carga parámetros y umbral de una calibración completa guardada."""
    p = Path(carpeta)
    resumen = leer_json(p / "resumen.json")
    for nombre in ("umbral.json", "modelo_congelado.npz", "correspondencia_congelada.json"):
        esperado = resumen["archivos_sha256"][nombre]
        coincide = sha(p / nombre) == esperado
        if not coincide and nombre.endswith('.json'):
            # Git puede convertir CRLF/LF. Solo admitimos ese cambio de bytes;
            # no se reserializa JSON ni se toleran valores o espacios distintos.
            contenido = (p / nombre).read_bytes().replace(b'\r\n', b'\n')
            coincide = esperado in {hashlib.sha256(t).hexdigest() for t in
                                    (contenido, contenido.replace(b'\n', b'\r\n'))}
        if not coincide:
            raise ValueError(f"Calibración modificada: {nombre}")
    m = leer_parametros(p / "modelo_congelado.npz", p / "correspondencia_congelada.json")
    return m, float(leer_json(p / "umbral.json")["umbral"])


def ejecutar(raiz=RAIZ, modelo="", extraccion="", config_path="config/rechazo_huellas_v1.json"):
    raiz = Path(raiz).resolve()
    config = leer_json(raiz / config_path)
    if (config["version"] != "rechazo_distancia_global_v1" or
            config["metrica"] != "euclidiana_en_caracteristicas_seleccionadas_estandarizadas" or
            config["regla"] != "aceptar_si_distancia_menor_o_igual_al_umbral" or
            config["criterio_umbral"] != "Minimizar (FAR + FRR)/2 en validacion; empate: menor FAR y luego menor umbral" or
            config["candidatos"] != "Cero, puntos medios entre distancias consecutivas distintas y distancia maxima"):
        raise ValueError("Configuración incompatible con la regla implementada.")
    datos = cargar_ejecucion(raiz, "huellas", extraccion)
    if modelo:
        base = raiz / modelo
    else:
        candidatos = sorted((raiz / "resultados/mejora_huellas").glob("*/resumen.json"))
        if not candidatos:
            raise FileNotFoundError("Falta el modelo de mejora de huellas. Ejecutar esa etapa primero.")
        base = candidatos[-1].parent
    m, resumen_modelo = cargar_modelo_congelado(raiz, base, datos)
    X, filas = seleccionar_validacion(datos)
    distancias, grupos = medir_distancias(X, datos["nombres"], m)
    autorizado = np.array([r["grupo"] == "autorizado" for r in filas])
    elegido, curva = elegir_umbral(distancias, autorizado)
    corte = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    salida = raiz / "resultados/rechazo_huellas" / corte
    salida.mkdir(parents=True, exist_ok=False)
    decisiones = decidir_acceso(X, datos["nombres"], m, elegido["umbral"])
    resultados = []
    for r, dec in zip(filas, decisiones):
        error = ("falsa_aceptacion" if r["grupo"] == "intruso" and dec["aceptada"] else
                 "falso_rechazo" if r["grupo"] == "autorizado" and not dec["aceptada"] else
                 "identidad_incorrecta" if r["grupo"] == "autorizado" and dec["identidad"] != r["identidad"] else "")
        resultados.append(dict(muestra=r["muestra"], identidad_real=r["identidad"],
                               grupo_real=r["grupo"], particion=r["particion"], perfil=r["perfil"],
                               **dec, error=error))
    ident_incorrectas = sum(r["error"] == "identidad_incorrecta" for r in resultados)
    por_identidad = []
    for id_ in sorted({r["identidad_real"] for r in resultados}):
        sub = [r for r in resultados if r["identidad_real"] == id_]
        por_identidad.append(dict(identidad=id_, grupo=sub[0]["grupo_real"], n=len(sub),
            aceptadas=sum(r["aceptada"] for r in sub), rechazadas=sum(not r["aceptada"] for r in sub),
            errores_identidad_aceptada=sum(r["error"] == "identidad_incorrecta" for r in sub)))
    guardar_csv(salida / "decisiones_validacion.csv", resultados)
    guardar_csv(salida / "errores_validacion.csv", [r for r in resultados if r["error"]], campos=list(resultados[0]))
    guardar_csv(salida / "tasas_por_umbral.csv", curva)
    guardar_csv(salida / "resultados_por_identidad.csv", por_identidad)
    guardar_csv(salida / "matriz_acceso.csv", [dict(grupo=g,
        aceptadas=sum(r["aceptada"] for r in resultados if r["grupo_real"] == g),
        rechazadas=sum(not r["aceptada"] for r in resultados if r["grupo_real"] == g))
        for g in ("autorizado", "intruso")])
    guardar_csv(salida / "catalogo_uso.csv", [dict(r, uso_rechazo=(
        "calibracion_validacion" if r["particion"] == "validacion" else
        "solo_verificacion_contrato_modelo" if r["particion"] == "entrenamiento" else
        "reservada_prueba")) for r in datos["catalogo"]])
    guardar_json(salida / "umbral.json", dict(version=config["version"], **elegido,
                 regla=config["regla"], criterio=config["criterio_umbral"],
                 calibrado_con="validacion", prueba_evaluada=False))
    shutil.copyfile(base / "seleccionada/parametros.npz", salida / "modelo_congelado.npz")
    shutil.copyfile(base / "seleccionada/correspondencia.json", salida / "correspondencia_congelada.json")
    graficar(resultados, curva, elegido, salida)
    resumen = dict(fecha_utc=corte, python=platform.python_version(), plataforma=platform.platform(),
        dependencias={p: importlib.metadata.version(p) for p in ("numpy", "matplotlib")}, config=config,
        modelo_origen=base.relative_to(raiz).as_posix(), modelo_resumen_sha256=sha(base / "resumen.json"),
        extraccion=datos["carpeta"].relative_to(raiz).as_posix(),
        extraccion_manifiesto_sha256=sha(datos["carpeta"] / "manifiesto.json"),
        columnas_entrada=len(m["nombres"]), columnas_utilizadas=len(m["indices"]),
        cantidades=dict(Counter(r["grupo_real"] for r in resultados)),
        identidades_intrusas_validacion=len({r["identidad_real"] for r in resultados if r["grupo_real"] == "intruso"}),
        resultado_calibracion=elegido, identidades_incorrectas_entre_aceptadas=ident_incorrectas,
        identificacion_sin_umbral_autorizados=float(np.mean([
            m["correspondencia"][str(g)] == r["identidad"]
            for r, g in zip(filas, grupos) if r["grupo"] == "autorizado"])),
        max_distancia_autorizada=float(distancias[autorizado].max()),
        min_distancia_intrusa=float(distancias[~autorizado].min()),
        separacion_perfecta_con_umbral_global=bool(distancias[autorizado].max() < distancias[~autorizado].min()),
        modelo_reajustado=False, seleccion_modificada=False, prueba_evaluada=False,
        advertencia="Resultado en los mismos datos usados para calibrar; no evaluación final independiente.")
    for p in [Path(__file__), raiz / config_path]:
        shutil.copyfile(p, salida / p.name)
    resumen["archivos_sha256"] = {p.name: sha(p) for p in salida.iterdir() if p.is_file()}
    guardar_json(salida / "resumen.json", resumen)
    print("Salida:", salida.relative_to(raiz))
    print("Modelo congelado:", base.relative_to(raiz))
    print("Validación:", resumen["cantidades"], "Columnas:", len(m["indices"]))
    print(f"Umbral global: {elegido['umbral']:.9f}; aceptar si d <= umbral")
    print(f"FAR: {100*elegido['FAR']:.2f}% ({elegido['falsas_aceptaciones']} intrusos aceptados)")
    print(f"FRR: {100*elegido['FRR']:.2f}% ({elegido['falsos_rechazos']} autorizados rechazados)")
    print("Errores de identidad entre aceptadas:", ident_incorrectas)
    print("Prueba final reservada. Métricas de calibración, no evaluación independiente.")
    return salida, resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo", default="", help="Carpeta de mejora_huellas; vacío: última ejecución.")
    parser.add_argument("--extraccion", default="", help="Extracción compatible exacta, opcional.")
    args = parser.parse_args()
    ejecutar(modelo=args.modelo, extraccion=args.extraccion)
