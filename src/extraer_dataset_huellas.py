"""Extraer GLCM del catálogo vigente en una ejecución nueva e inmutable.

Por defecto solo entrenamiento y validación. Nunca entrena modelos.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import sys

import numpy as np
from PIL import Image
import caracteristicas_huellas as extractor

RAIZ = Path(__file__).resolve().parents[1]


def sha(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def json_texto(valor):
    return json.dumps(valor, ensure_ascii=False, sort_keys=True, allow_nan=False)


def guardar_json(ruta, valor):
    ruta.write_text(json.dumps(valor, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def ruta_interna(raiz, texto):
    if not texto:
        raise ValueError("Ruta vacía en catálogo/configuración.")
    p = (raiz / texto).resolve()
    if not p.is_relative_to(raiz.resolve()):
        raise ValueError("La ruta debe pertenecer al repositorio.")
    return p


def leer_gris(ruta):
    with Image.open(ruta) as im:
        if im.mode != "L":
            raise ValueError(f"Se esperaba PNG gris L: {ruta.name}")
        return np.array(im)


def ejecutar(raiz=RAIZ, catalogo="datos/procesados/normalizacion_final_v1/catalogo_normalizado.csv",
             config="config/caracteristicas_huellas_glcm_v1.json", incluir_prueba=False,
             verificar_180=False):
    raiz = Path(raiz).resolve()
    catpath, cfgpath = ruta_interna(raiz, catalogo), ruta_interna(raiz, config)
    cfg = extractor.cargar_config(cfgpath)
    with catpath.open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        columnas = lector.fieldnames or []
        filas = list(lector)
    requeridas = {"muestra", "identidad", "grupo", "particion", "normalizada", "alternativa_180",
                  "sha256_normalizada", "sha256_alternativa_180", "estado_normalizacion"}
    if not requeridas.issubset(columnas) or not filas:
        raise ValueError("Catálogo vacío o sin las columnas vigentes de normalización.")
    ids = [r["muestra"] for r in filas]
    if len(set(ids)) != len(ids) or any(not s.strip() for s in ids):
        raise ValueError("Identificadores de muestra vacíos o duplicados.")
    if any(r["particion"] not in {"entrenamiento", "validacion", "prueba"} for r in filas):
        raise ValueError("Particiones desconocidas: no se reasignan automáticamente.")
    nuevas_cols = ["fila_vector", "estado_extraccion", "motivo_extraccion", "avisos_extraccion_json",
                   "mascara_caracteristicas", "sha256_mascara_caracteristicas", "sha256_entrada_leida",
                   "version_preprocesamiento", "avisos_normalizacion_json", "id_extractor"]
    if set(columnas) & set(nuevas_cols):
        raise ValueError("Se requiere catálogo normalizado, no un catálogo de características.")
    soporte = {n: catpath.parent / n for n in ("detalle.json", "config_efectiva.json", "entorno.json")}
    for p in soporte.values():
        if not p.is_file():
            raise FileNotFoundError(f"Falta procedencia de normalización: {p}")
    detalles_norm = json.loads(soporte["detalle.json"].read_text(encoding="utf-8-sig"))
    if len({r["muestra"] for r in detalles_norm}) != len(detalles_norm):
        raise ValueError("Detalle de normalización duplicado.")
    por_id = {r["muestra"]: r for r in detalles_norm}
    if not set(ids).issubset(por_id):
        raise ValueError("Faltan registros de procedencia por muestra.")
    versiones = {p: importlib.metadata.version(p) for p in ("numpy", "scipy", "Pillow")}
    codigo = {"caracteristicas_huellas.py": sha(extractor.__file__),
              "extraer_dataset_huellas.py": sha(__file__)}
    contrato = dict(config=cfg, codigo=codigo, dependencias=versiones,
                    sha256_config_normalizacion=sha(soporte["config_efectiva.json"]))
    huella_contrato = hashlib.sha256(json_texto(contrato).encode()).hexdigest()
    id_extractor = cfg["version"] + "_" + huella_contrato[:12]
    nombre_run = "ejecucion_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    base = raiz / "datos/caracteristicas/huellas" / id_extractor
    salida, parcial = base / nombre_run, base / (nombre_run + ".parcial")
    parcial.mkdir(parents=True, exist_ok=False)
    nombres = extractor.nombres_caracteristicas(cfg)
    registros, detalles, vectores, muestras = [], [], [], []
    for r in filas:
        norm = por_id[r["muestra"]]
        row = dict(r, **{k: "" for k in nuevas_cols})
        row.update(id_extractor=id_extractor, version_preprocesamiento=norm.get("version", ""),
                   avisos_normalizacion_json=json_texto(norm.get("avisos", [])),
                   avisos_extraccion_json="[]")
        if r["particion"] == "prueba" and not incluir_prueba:
            row.update(estado_extraccion="diferida_prueba", motivo_extraccion="Reserva de prueba: imagen no leída.")
            registros.append(row)
            continue
        try:
            if r["estado_normalizacion"] not in {"ok", "revisar"} or not row["version_preprocesamiento"]:
                raise ValueError("Normalización sin estado utilizable o sin versión.")
            path = ruta_interna(raiz, r["normalizada"])
            altpath = ruta_interna(raiz, r["alternativa_180"])
            # El catálogo actual no tiene columna de máscara: convención de normalizar_todas.py.
            maskpath = path.with_name(path.stem + "_mascara.png")
            row["mascara_caracteristicas"] = maskpath.relative_to(raiz).as_posix()
            row["sha256_entrada_leida"] = sha(path)
            if row["sha256_entrada_leida"] != r["sha256_normalizada"]:
                raise ValueError("Hash de normalizada distinto al catálogo.")
            if sha(altpath) != r["sha256_alternativa_180"]:
                raise ValueError("Hash de alternativa distinto al catálogo.")
            row["sha256_mascara_caracteristicas"] = sha(maskpath)
            im, mask, alt = leer_gris(path), leer_gris(maskpath), leer_gris(altpath)
            if not np.array_equal(alt, np.rot90(im, 2)):
                raise ValueError("La alternativa no es el giro exacto de 180°.")
            vector, info = extractor.extraer_huella(im, mask, cfg)
            diferencia = None
            if verificar_180:
                otro, _ = extractor.extraer_huella(alt, np.rot90(mask, 2), cfg)
                diferencia = float(np.max(np.abs(vector - otro)))
                if not np.allclose(vector, otro, atol=1e-12, rtol=0):
                    raise RuntimeError("Error interno: el descriptor no respetó la invariancia 180°.")
            row.update(fila_vector=len(vectores), estado_extraccion="vectorizada",
                       avisos_extraccion_json=json_texto(info["avisos"]))
            vectores.append(vector)
            muestras.append(r["muestra"])
            detalles.append(dict(muestra=r["muestra"], particion=r["particion"],
                                 diferencia_max_180=diferencia, **info))
        except extractor.HuellaNoVectorizable as e:
            row.update(estado_extraccion="no_vectorizable", motivo_extraccion=str(e))
        except (OSError, ValueError) as e:
            row.update(estado_extraccion="error_entrada", motivo_extraccion=f"{type(e).__name__}: {e}")
        registros.append(row)
    X = np.vstack(vectores) if vectores else np.empty((0, len(nombres)), dtype=np.float64)
    if X.shape != (len(muestras), len(nombres)) or not np.isfinite(X).all():
        raise RuntimeError("Matriz final incoherente.")
    np.savez_compressed(parcial / "vectores.npz", X=X, muestras=np.asarray(muestras, dtype=str),
                        nombres=np.asarray(nombres, dtype=str))
    with (parcial / "vectores.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["muestra", *nombres])
        for muestra, v in zip(muestras, X):
            w.writerow([muestra, *[format(x, ".17g") for x in v]])
    with (parcial / "catalogo_caracteristicas.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas + nuevas_cols)
        w.writeheader()
        w.writerows(registros)
    for n, p in soporte.items():
        shutil.copyfile(p, parcial / ("normalizacion_" + n))
    shutil.copyfile(catpath, parcial / "catalogo_origen.csv")
    guardar_json(parcial / "config_efectiva.json", cfg)
    guardar_json(parcial / "nombres_caracteristicas.json", nombres)
    guardar_json(parcial / "detalle_extraccion.json", detalles)
    # Snapshot de código para reproducir el método incluso si src cambia más adelante.
    shutil.copyfile(extractor.__file__, parcial / "fuente_caracteristicas_huellas.py")
    shutil.copyfile(__file__, parcial / "fuente_extraer_dataset_huellas.py")
    input_fingerprint = hashlib.sha256(json_texto([
        [r["muestra"], r["sha256_entrada_leida"], r["sha256_mascara_caracteristicas"],
         r["estado_extraccion"]] for r in registros]).encode()).hexdigest()
    manifest = dict(id_extractor=id_extractor, firma_contrato=huella_contrato, contrato=contrato,
                    ejecucion=nombre_run, python=platform.python_version(), plataforma=platform.platform(),
                    catalogo_origen=catpath.relative_to(raiz).as_posix(), sha256_catalogo=sha(catpath),
                    huella_entradas=input_fingerprint, dimension=len(nombres), nombres=nombres,
                    incluir_prueba=incluir_prueba, verificar_180=verificar_180,
                    escalado_aprendido=False, pca_ajustado=False,
                    desplazamientos=[dict(distancia_nominal=d, angulo=a, dy=dy, dx=dx,
                                          distancia_efectiva=float(np.hypot(dy, dx)))
                                     for d, a, dy, dx in extractor.desplazamientos(cfg)])
    manifest["sha256_archivos"] = {p.name: sha(p) for p in parcial.iterdir() if p.is_file()}
    guardar_json(parcial / "manifiesto.json", manifest)
    estados = dict(Counter(r["estado_extraccion"] for r in registros))
    diferencias = [d["diferencia_max_180"] for d in detalles if d["diferencia_max_180"] is not None]
    resumen = dict(id_extractor=id_extractor, ejecucion=nombre_run, total_catalogo=len(filas),
                   estados=estados, forma_X=list(X.shape), valores_finitos=bool(np.isfinite(X).all()),
                   vectorizadas_por_particion=dict(Counter(r["particion"] for r in registros
                                                          if r["estado_extraccion"] == "vectorizada")),
                   muestras_con_avisos_extractor=sum(bool(d["avisos"]) for d in detalles),
                   vectorizadas_con_aviso_normalizacion=sum(r["estado_normalizacion"] == "revisar"
                        for r in registros if r["estado_extraccion"] == "vectorizada"),
                   verificadas_180=len(diferencias), diferencia_max_180=max(diferencias, default=None),
                   salida=salida.relative_to(raiz).as_posix(),
                   nota="Vectorizable no significa aprobada para modelado ni identidad reconocida.")
    guardar_json(parcial / "resumen.json", resumen)
    parcial.rename(salida)
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    fallos = estados.get("error_entrada", 0) + estados.get("no_vectorizable", 0)
    return salida, fallos


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalogo", default="datos/procesados/normalizacion_final_v1/catalogo_normalizado.csv")
    p.add_argument("--config", default="config/caracteristicas_huellas_glcm_v1.json")
    p.add_argument("--incluir-prueba", action="store_true", help="Solo después de congelar las decisiones de desarrollo.")
    p.add_argument("--verificar-180", action="store_true", help="Comparar los vectores de ambas orientaciones.")
    args = p.parse_args()
    try:
        _, fallos = ejecutar(catalogo=args.catalogo, config=args.config,
                            incluir_prueba=args.incluir_prueba, verificar_180=args.verificar_180)
    except (OSError, ValueError) as e:
        p.exit(2, f"No se pudo extraer: {e}\n")
    if fallos:
        print("Revisar motivos en catalogo_caracteristicas.csv. No usar filas fallidas.", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
