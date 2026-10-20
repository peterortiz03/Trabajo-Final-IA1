# Lote de extracción por catálogo activo.
# No modifica audios, decisiones humanas ni particiones.

import argparse
from collections import Counter
from datetime import datetime, timezone
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import sys
import wave

import numpy as np

import caracteristicas_audio as extractor
import preprocesamiento_audio as pp

RAIZ = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha_codigo(p):
    # CRLF y LF representan el mismo código.
    contenido = Path(p).read_text(encoding="utf-8-sig")
    contenido = contenido.replace("\r\n", "\n")
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def leer_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def guardar_json(p, objeto):
    Path(p).write_text(
        json.dumps(
            objeto, ensure_ascii=False, indent=2, allow_nan=False
        ),
        encoding="utf-8",
    )


def canonico(objeto):
    return json.dumps(
        objeto, ensure_ascii=False, sort_keys=True, allow_nan=False
    ).encode("utf-8")


def ruta(raiz, nombre):
    if not isinstance(nombre, str) or not nombre.strip():
        raise ValueError("Ruta vacía en el catálogo.")
    p = (raiz / nombre).resolve()
    if not p.is_relative_to(raiz):
        raise ValueError("Ruta fuera del repositorio.")
    return p


def cargar_activo(raiz):
    # Mecanismo existente: actual.json -> ruta_catalogo.
    actual_path = raiz / "datos/audio/procesados/actual.json"
    actual = leer_json(actual_path)
    catpath = ruta(raiz, actual["ruta_catalogo"])

    with catpath.open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        columnas = lector.fieldnames or []
        filas = list(lector)

    requeridas = {
        "muestra_id", "hablante", "comando", "particion",
        "version_procesamiento", "firma_procedimiento",
        "sha256_original", "sha256_procesado", "ruta_procesada",
        "ruta_detalle", "estado_procesamiento",
        "decision_revision", "motivo_revision",
        "avisos_preprocesamiento", "avisos_calidad",
    }
    if (
        not filas
        or not requeridas.issubset(columnas)
        or any(None in r or None in r.values() for r in filas)
    ):
        raise ValueError("Catálogo activo vacío o incompleto.")

    ids = [r["muestra_id"] for r in filas]
    if len(set(ids)) != len(ids) or any(not s.strip() for s in ids):
        raise ValueError("Identificadores vacíos o duplicados.")

    if any(
        r["version_procesamiento"] != actual["version"]
        for r in filas
    ):
        raise ValueError("El catálogo mezcla versiones de procesamiento.")

    soporte = {
        "actual.json": actual_path,
        "catalogo_origen.csv": catpath,
        "procedimiento_origen.json": catpath.parent / "procedimiento.json",
        "revisiones_aplicadas.json": catpath.parent / "revisiones_aplicadas.json",
    }

    procedimiento = leer_json(soporte["procedimiento_origen.json"])
    if any(
        r["firma_procedimiento"] != procedimiento["firma_procedimiento"]
        for r in filas
    ):
        raise ValueError("Firma distinta al procedimiento activo.")

    aplicadas = leer_json(soporte["revisiones_aplicadas.json"])
    config_revision = raiz / "config/revisiones_audio_v1.json"

    if config_revision.exists():
        if leer_json(config_revision) != aplicadas:
            raise ValueError(
                "Las revisiones cambiaron. Ejecutá "
                "src/preprocesar_dataset_audio.py para actualizar "
                "el catálogo activo y repetí la extracción."
            )
        soporte["revisiones_config.json"] = config_revision

    por_hablante = {}
    for r in filas:
        revision = aplicadas.get(r["muestra_id"], {})

        if (
            r["decision_revision"] != revision.get("decision", "pendiente")
            or r["motivo_revision"] != revision.get("motivo", "")
        ):
            raise ValueError(
                "Catálogo y revisiones inconsistentes: " + r["muestra_id"]
            )

        if r["decision_revision"] not in {
            "conservar", "excluir", "pendiente"
        }:
            raise ValueError("Decisión humana desconocida.")

        if (
            r["decision_revision"] != "pendiente"
            and not r["motivo_revision"].strip()
        ):
            raise ValueError("Una decisión explícita requiere motivo.")

        if r["particion"] not in {
            "sin_asignar", "entrenamiento", "validacion", "prueba"
        }:
            raise ValueError("Partición desconocida.")

        if not r["hablante"].strip():
            raise ValueError("Hablante vacío.")

        por_hablante.setdefault(r["hablante"], set()).add(r["particion"])

    if any(len(particiones) > 1 for particiones in por_hablante.values()):
        raise ValueError(
            "Un hablante aparece en distintas particiones. "
            "Corregir mediante un mapa persistente."
        )

    return actual, filas, columnas, soporte, procedimiento


def ejecutar(
    raiz=RAIZ,
    config="config/caracteristicas_audio_v1.json",
    verificar_repetibilidad=False,
):
    raiz = Path(raiz).resolve()
    c = extractor.cargar_config(ruta(raiz, config))
    actual, filas, columnas, soporte, procedimiento = cargar_activo(raiz)

    firmas_entrada = {n: sha(p) for n, p in soporte.items()}
    fuentes = {
        "caracteristicas_audio.py": Path(extractor.__file__),
        "extraer_dataset_audio.py": Path(__file__),
        "preprocesamiento_audio.py": Path(pp.__file__),
    }

    contrato = {
        "config": c,
        "codigo": {n: sha_codigo(p) for n, p in fuentes.items()},
        "dependencias": {
            p: importlib.metadata.version(p)
            for p in ("numpy", "scipy")
        },
        "version_preprocesamiento": actual["version"],
        "firma_preprocesamiento": procedimiento["firma_procedimiento"],
    }

    firma = hashlib.sha256(canonico(contrato)).hexdigest()
    id_extractor = c["version"] + "_" + firma[:12]
    run = "ejecucion_" + datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ"
    )

    base = raiz / "datos/caracteristicas/audio" / id_extractor
    destino = base / run
    temporal = base / (run + ".parcial")

    nuevas = [
        "fila_vector", "estado_extraccion", "motivo_extraccion",
        "avisos_extraccion_json", "revision_aprobada",
        "estado_para_modelado", "id_extractor", "sha256_detalle_leido",
    ]
    if set(nuevas) & set(columnas):
        raise ValueError(
            "Se requiere el catálogo procesado, no uno de características."
        )

    temporal.mkdir(parents=True, exist_ok=False)

    vectores, ids, registros, detalles, repeticiones = [], [], [], [], []

    for r in filas:
        row = dict(r, **{k: "" for k in nuevas})
        row.update(
            id_extractor=id_extractor,
            avisos_extraccion_json="[]",
            revision_aprobada=str(r["decision_revision"] == "conservar"),
            estado_para_modelado="no_habilitada",
        )

        if r["decision_revision"] == "excluir":
            row.update(
                estado_extraccion="excluida_revision",
                motivo_extraccion=r["motivo_revision"],
            )
            registros.append(row)
            continue

        if r["particion"] == "prueba":
            row.update(
                estado_extraccion="diferida_prueba",
                motivo_extraccion="Prueba reservada; WAV no leído en este hito.",
            )
            registros.append(row)
            continue

        try:
            if r["estado_procesamiento"] not in {
                "procesado", "procesado_con_avisos"
            }:
                raise extractor.AudioNoVectorizable(
                    "Preprocesamiento sin salida utilizable: "
                    + r["estado_procesamiento"]
                )

            audio_path = ruta(raiz, r["ruta_procesada"])
            detalle_path = ruta(raiz, r["ruta_detalle"])

            if sha(audio_path) != r["sha256_procesado"]:
                raise ValueError("Hash del WAV distinto al catálogo.")

            resultado = leer_json(detalle_path)
            row["sha256_detalle_leido"] = sha(detalle_path)

            for k in [
                "muestra_id", "sha256_original", "sha256_procesado",
                "firma_procedimiento", "ruta_procesada",
            ]:
                if resultado.get(k) != r[k]:
                    raise ValueError(f"Detalle y catálogo difieren en {k}.")

            d = resultado["detalle"]
            if (
                d["estado"] != r["estado_procesamiento"]
                or ";".join(d.get("avisos", []))
                != r["avisos_preprocesamiento"]
            ):
                raise ValueError("Estados o avisos inconsistentes.")

            audio, fs = pp.leer_wav_pcm16(audio_path)
            formato = (fs, audio.shape[1], len(audio))
            esperado = (
                d["frecuencia_procesada_hz"],
                d["canales_procesados"],
                d["cuadros_procesados"],
            )
            if formato != esperado:
                raise ValueError("Formato o longitud distinta al detalle.")

            limites = extractor.limites_desde_detalle(d, fs, len(audio))
            vector, info = extractor.extraer_audio(
                audio, fs, limites, c
            )

            diferencia = None
            if verificar_repetibilidad:
                otro, _ = extractor.extraer_audio(
                    audio, fs, limites, c
                )
                diferencia = float(np.max(np.abs(vector - otro)))
                if not np.array_equal(vector, otro):
                    raise RuntimeError(
                        "Extracción no determinista en el mismo entorno."
                    )
                repeticiones.append(diferencia)

            pendientes = []
            if r["decision_revision"] != "conservar":
                pendientes.append("revision_humana")
            if info["avisos"]:
                pendientes.append("avisos_extractor")
            if r["particion"] == "sin_asignar":
                pendientes.append("particion")

            estado_modelado = (
                "pendiente:" + ",".join(pendientes)
                if pendientes else "revisar_mapa_y_uso"
            )
            row.update(
                fila_vector=len(vectores),
                estado_extraccion="vectorizada",
                avisos_extraccion_json=json.dumps(
                    info["avisos"], ensure_ascii=False
                ),
                estado_para_modelado=estado_modelado,
            )

            vectores.append(vector)
            ids.append(r["muestra_id"])
            detalles.append(dict(
                muestra_id=r["muestra_id"],
                diferencia_repeticion=diferencia,
                **info,
            ))

        except extractor.AudioNoVectorizable as e:
            row.update(
                estado_extraccion="no_vectorizable",
                motivo_extraccion=str(e),
            )
        except (OSError, ValueError, KeyError, wave.Error) as e:
            row.update(
                estado_extraccion="error_entrada",
                motivo_extraccion=f"{type(e).__name__}: {e}",
            )

        registros.append(row)

    nombres = extractor.nombres_caracteristicas(c)
    X = (
        np.vstack(vectores)
        if vectores
        else np.empty((0, len(nombres)), dtype=np.float64)
    )

    if (
        X.shape != (len(ids), len(nombres))
        or not np.isfinite(X).all()
    ):
        raise RuntimeError("Matriz final inválida.")

    if any(
        sha(p) != firmas_entrada[n]
        for n, p in soporte.items()
    ):
        raise RuntimeError(
            "Catálogo o revisiones cambiaron durante la extracción. "
            "Repetir sin modificar las entradas."
        )

    np.savez_compressed(
        temporal / "vectores.npz",
        X=X,
        muestras=np.asarray(ids, dtype=str),
        nombres=np.asarray(nombres, dtype=str),
    )

    with (temporal / "vectores.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        w = csv.writer(f)
        w.writerow(["muestra_id", *nombres])
        for muestra, vector in zip(ids, X):
            w.writerow([
                muestra,
                *[format(valor, ".17g") for valor in vector],
            ])

    with (temporal / "catalogo_caracteristicas.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        w = csv.DictWriter(f, fieldnames=columnas + nuevas)
        w.writeheader()
        w.writerows(registros)

    for n, p in soporte.items():
        shutil.copyfile(p, temporal / n)
    for n, p in fuentes.items():
        shutil.copyfile(p, temporal / ("fuente_" + n))

    guardar_json(temporal / "config_efectiva.json", c)
    guardar_json(temporal / "nombres_caracteristicas.json", nombres)
    guardar_json(temporal / "detalle_extraccion.json", detalles)

    manifest = {
        "id_extractor": id_extractor,
        "firma_contrato": firma,
        "contrato": contrato,
        "ejecucion": run,
        "python": platform.python_version(),
        "plataforma": platform.platform(),
        "dimension": len(nombres),
        "nombres": nombres,
        "sha256_entradas": firmas_entrada,
        "convenciones": {
            "ventana": "Hann periódica, solo para el espectro",
            "potencia": "abs(rfft)^2/n_fft; sin duplicar bins interiores",
            "mel": "HTK; triángulos de altura 1; sin normalización de área",
            "logaritmo": "natural",
            "dct": "II, ortho, orthogonalize=True",
            "indices_mfcc": "Órdenes cepstrales directos; c0 comienza en índice 0",
            "preenfasis": False,
            "deltas": False,
            "ddof": 0,
        },
        "escalador_ajustado": False,
        "pca_ajustado": False,
        "particiones_modificadas": False,
    }
    manifest["sha256_archivos"] = {
        p.name: sha(p) for p in temporal.iterdir() if p.is_file()
    }
    guardar_json(temporal / "manifiesto.json", manifest)

    estados = dict(Counter(
        r["estado_extraccion"] for r in registros
    ))
    resumen = {
        "id_extractor": id_extractor,
        "ejecucion": run,
        "version_preprocesamiento": actual["version"],
        "total_catalogo": len(filas),
        "estados": estados,
        "forma_X": list(X.shape),
        "valores_finitos": bool(np.isfinite(X).all()),
        "decisiones_revision": dict(Counter(
            r["decision_revision"] for r in filas
        )),
        "particiones": dict(Counter(
            r["particion"] for r in filas
        )),
        "hablantes": len({r["hablante"] for r in filas}),
        "vectorizadas_por_comando": dict(Counter(
            r["comando"] for r in registros
            if r["estado_extraccion"] == "vectorizada"
        )),
        "muestras_con_avisos_extractor": sum(
            bool(d["avisos"]) for d in detalles
        ),
        "vectorizadas_con_avisos_previos": sum(
            bool(r["avisos_preprocesamiento"])
            for r in registros
            if r["estado_extraccion"] == "vectorizada"
        ),
        "verificadas_repetibilidad": len(repeticiones),
        "diferencia_max_repeticion": max(
            repeticiones, default=None
        ),
        "salida": destino.relative_to(raiz).as_posix(),
        "nota": (
            "Vectorizable no implica revisión humana aprobada "
            "ni habilitación para modelado. No hay K-NN, "
            "escalador o PCA."
        ),
    }
    guardar_json(temporal / "resumen.json", resumen)
    temporal.rename(destino)

    print(json.dumps(resumen, ensure_ascii=False, indent=2))

    fallos = (
        estados.get("error_entrada", 0)
        + estados.get("no_vectorizable", 0)
    )
    return destino, fallos


def main():
    parser = argparse.ArgumentParser(
        description="Extraer características del catálogo de audio activo."
    )
    parser.add_argument(
        "--config",
        default="config/caracteristicas_audio_v1.json",
    )
    parser.add_argument(
        "--verificar-repetibilidad",
        action="store_true",
    )
    args = parser.parse_args()

    try:
        _, fallos = ejecutar(
            config=args.config,
            verificar_repetibilidad=args.verificar_repetibilidad,
        )
    except (OSError, ValueError, KeyError, RuntimeError) as e:
        parser.exit(2, f"No se pudo extraer: {e}\n")

    if fallos:
        print(
            "Revisar catalogo_caracteristicas.csv antes de continuar.",
            file=sys.stderr,
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()
