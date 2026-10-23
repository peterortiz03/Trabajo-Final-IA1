"""Prueba local de WAV o micrófono con el K-NN guardado, sin reentrenar."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
from pathlib import Path
import re
import shutil
import wave

import numpy as np
from threadpoolctl import threadpool_limits

import caracteristicas_audio as ca
import preprocesamiento_audio as pp
from extraer_dataset_audio import sha_codigo
from grabar_audio import cargar_config, elegir_dispositivo, capturar
from knn_audio import RAIZ, cargar_modelo, predecir_vectores
from verificacion_estadistica import guardar_json, guardar_csv, leer_json, sha

COMANDOS = ("identificar", "reconocer", "salir")


def cargar_sistema(carpeta, raiz=RAIZ):
    """Reutilizar el procedimiento exacto del modelo, sin leer audios del dataset."""
    carpeta, raiz = Path(carpeta).resolve(), Path(raiz).resolve()
    r = leer_json(carpeta / "resumen.json")
    modelo = cargar_modelo(carpeta)
    extraccion = (raiz / r["extraccion"]).resolve()
    if not extraccion.is_relative_to(raiz):
        raise ValueError("La extracción debe estar dentro del repositorio.")
    manifiesto = extraccion / "manifiesto.json"
    if sha(manifiesto) != r["manifiesto_extraccion_sha256"]:
        raise ValueError("La extracción de origen no coincide con el modelo. No regenerar ni sustituir a ciegas.")
    m = leer_json(manifiesto)
    for nombre in ["config_efectiva.json", "procedimiento_origen.json"]:
        if sha(extraccion / nombre) != m["sha256_archivos"][nombre]:
            raise ValueError("Configuración de origen modificada: " + nombre)
    proc = leer_json(extraccion / "procedimiento_origen.json")
    cfg_ext = ca.validar_config(leer_json(extraccion / "config_efectiva.json"))
    cfg_pp = pp.validar_config(proc["configuracion"])
    if (proc["firma_procedimiento"] != m["contrato"]["firma_preprocesamiento"] or
            cfg_ext != m["contrato"]["config"]):
        raise ValueError("Contrato de preprocesamiento/extracción inconsistente.")
    for modulo in (ca, pp):
        nombre = Path(modulo.__file__).name
        if sha_codigo(modulo.__file__) != m["contrato"]["codigo"][nombre]:
            raise ValueError("Cambió el código del procedimiento: " + nombre)
    for paquete in ("numpy", "scipy"):
        if importlib.metadata.version(paquete) != m["contrato"]["dependencias"][paquete]:
            raise ValueError("Versión incompatible con la extracción: " + paquete)
    if importlib.metadata.version("scikit-learn") != r["dependencias"]["scikit-learn"]:
        raise ValueError("Usar la versión scikit-learn registrada por el modelo.")
    if list(modelo["nombres"]) != ca.nombres_caracteristicas(cfg_ext):
        raise ValueError("Nombres u orden del extractor distintos al modelo.")
    with np.load(carpeta / "modelo.npz", allow_pickle=False) as z:
        ids = z["ids_entrenamiento"].copy()
        voces = z["hablantes"].copy()
    return dict(modelo=modelo, cfg_pp=cfg_pp, cfg_ext=cfg_ext, ids=ids, voces=voces,
                carpeta=carpeta, resumen=r, modelo_sha256=sha(carpeta / "modelo.npz"))


def vectorizar(audio, fs, cfg_pp, cfg_ext):
    """Igualar el trayecto original -> procesado PCM16 -> vector del dataset."""
    procesado, detalle = pp.preprocesar_audio(audio, fs, cfg_pp)
    if procesado is None:
        return None, detalle, None
    # En el dataset se escribe WAV PCM16 antes de extraer. Omitir este redondeo
    # produciría vectores ligeramente distintos incluso con el mismo WAV original.
    pcm = np.rint(procesado * 32768).astype("<i2")
    limites = ca.limites_desde_detalle(detalle, cfg_pp["frecuencia_hz"], len(pcm))
    try:
        vector, info = ca.extraer_audio(pcm, cfg_pp["frecuencia_hz"], limites, cfg_ext)
    except ca.AudioNoVectorizable as e:
        return None, detalle, dict(motivo=str(e), avisos=[])
    return vector, detalle, info


def interpretar(audio, fs, sistema):
    """La palabra esperada NO es un argumento: no puede orientar la predicción."""
    vector, detalle, info = vectorizar(audio, fs, sistema["cfg_pp"], sistema["cfg_ext"])
    resultado = dict(prediccion=None, estado="sin_vector_revisar", detalle=detalle, extraccion=info,
                     avisos=detalle["avisos"] + ([] if info is None else info.get("avisos", [])))
    if vector is None:
        return resultado, None
    m = sistema["modelo"]
    resultado["prediccion"] = str(predecir_vectores(vector, m["nombres"], m)[0])
    resultado["estado"] = "prediccion_con_avisos" if resultado["avisos"] else "prediccion"
    Z = (vector - m["media"]) / m["escala"]
    with threadpool_limits(limits=1):
        distancias, indices = m["knn"].kneighbors(Z[None, :], n_neighbors=min(5, len(m["etiquetas"])))
    resultado["vecinos_diagnostico"] = [dict(muestra=str(sistema["ids"][i]),
        hablante=str(sistema["voces"][i]), palabra=str(m["etiquetas"][i]), distancia=float(d))
        for i, d in zip(indices[0], distancias[0])]
    resultado["nota_vecinos"] = "Hasta cinco para inspección; el voto usa el k guardado, no necesariamente cinco. Distancia no es confianza."
    return resultado, vector


def guardar_wav(p, audio, fs):
    x = np.asarray(audio)
    if x.ndim == 1:
        x = x[:, None]
    if x.dtype != np.dtype("int16"):
        raise ValueError("El original debe ser PCM16.")
    with wave.open(str(p), "wb") as w:
        w.setnchannels(x.shape[1]); w.setsampwidth(2); w.setframerate(fs)
        w.writeframes(x.astype("<i2").tobytes())


def registrar(salida, numero, audio, fs, esperada, sistema, filas, captura=None):
    muestra = f"toma_{numero:03d}"
    guardar_wav(salida / f"{muestra}.wav", audio, fs)
    r, vector = interpretar(audio, fs, sistema)
    r.update(muestra=muestra, esperada=esperada, captura=captura,
        sha256_original=sha(salida / f"{muestra}.wav"), modelo_sha256=sistema["modelo_sha256"],
        acierto=(r["prediccion"] == esperada) if esperada in COMANDOS else None)
    guardar_json(salida / f"{muestra}.json", r)
    if vector is not None:
        np.savez_compressed(salida / f"{muestra}_vector.npz", vector=vector,
                            nombres=sistema["modelo"]["nombres"])
    filas.append(dict(muestra=muestra, esperada=esperada, prediccion=r["prediccion"] or "SIN_VECTOR",
        estado=r["estado"], acierto="" if r["acierto"] is None else int(r["acierto"]),
        avisos=";".join(r["avisos"])))
    guardar_csv(salida / "intentos.csv", filas)
    conocidas = [f for f in filas if f["esperada"] in COMANDOS]
    aciertos = sum(f["acierto"] for f in conocidas)
    guardar_json(salida / "resumen_prueba.json", dict(intentos=len(filas), comandos_intentados=len(conocidas),
        aciertos=aciertos, sin_vector=sum(f["prediccion"] == "SIN_VECTOR" for f in filas),
        exactitud_por_intento=aciertos/len(conocidas) if conocidas else None,
        nota="Prueba práctica de desarrollo; sin_vector cuenta como fallo en comandos conocidos. No es prueba final independiente."))
    print("Predicción:", r["prediccion"] or "SIN VECTOR: revisar captura/actividad")
    print("Avisos:", r["avisos"] or "ninguno; esto no garantiza que sea una palabra válida")
    if esperada in COMANDOS:
        print("Esperada:", esperada, "|", "ACIERTO" if r["acierto"] else "FALLO")
    for vecino in r.get("vecinos_diagnostico", []):
        print("  Vecino:", vecino)
    print("El modelo no rechaza palabras desconocidas. No interpreta distancias como porcentajes.")


def ejecutar(args):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.hablante):
        raise ValueError("Usar un ID de hablante sin espacios ni nombres personales.")
    if args.rondas < 0:
        raise ValueError("Rondas debe ser cero (modo libre) o un entero positivo.")
    carpeta = (RAIZ / args.modelo).resolve() if args.modelo else None
    if carpeta is None:
        opciones = sorted((RAIZ / "resultados/knn_audio").glob("*/resumen.json"))
        if not opciones:
            raise ValueError("Primero ejecutar src/knn_audio.py o indicar --modelo.")
        carpeta = opciones[-1].parent
    sistema = cargar_sistema(carpeta)
    print("Modelo fijo:", carpeta, "|", sistema["resumen"]["parametros"])
    conocida = args.hablante in sistema["resumen"]["hablantes_entrenamiento"]
    print("Hablante:", args.hablante, "(ya participó en desarrollo)" if conocida else "(ID declarado fuera del entrenamiento; no verifica identidad)")
    sd = None
    dispositivo = None
    if not args.wav:
        import sounddevice as sd
        cfg = cargar_config(RAIZ / "config/audio_v1.json")
        dispositivo, fs, canales, nombre, api = elegir_dispositivo(sd, cfg)
    fecha = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    salida = RAIZ / "resultados/prueba_audio" / fecha
    salida.mkdir(parents=True, exist_ok=False)
    guardar_json(salida / "sesion.json", dict(hablante=args.hablante, voces_entrenamiento=sistema["resumen"]["hablantes_entrenamiento"],
        modelo=str(carpeta), modelo_sha256=sistema["modelo_sha256"], fecha_utc=fecha,
        python=__import__("platform").python_version(), configuracion_pp=sistema["cfg_pp"],
        configuracion_extractor=sistema["cfg_ext"], vocabulario=list(COMANDOS), rondas=args.rondas,
        uso="Diagnóstico; sin incorporar al dataset ni reentrenar ni evaluar prueba reservada."))
    shutil.copy2(__file__, salida / "probar_knn_audio.py")
    filas = []
    print("Se guardan todos los intentos en:", salida)
    try:
        if args.wav:
            audio, fs = pp.leer_wav_pcm16(args.wav)
            registrar(salida, 1, audio, fs, args.esperada, sistema, filas, dict(origen=str(Path(args.wav).resolve())))
        else:
            agenda = list(COMANDOS) * args.rondas
            while True:
                numero = len(filas)+1
                if args.rondas:
                    if numero > len(agenda):
                        break
                    esperada = agenda[numero-1]
                else:
                    print("1 identificar | 2 reconocer | 3 salir (palabra) | 4 otra palabra | 5 silencio | Q terminar")
                    op = input("Elegí ANTES de grabar: ").strip().upper()
                    if op == "Q":
                        break
                    if op not in "12345" or len(op) != 1:
                        continue
                    esperada = [*COMANDOS, "otra", "silencio"][int(op)-1]
                audio = capturar(sd, dispositivo, fs, canales, cfg, esperada)
                registrar(salida, numero, audio, fs, esperada, sistema, filas,
                          dict(dispositivo=nombre, api=api, frecuencia_hz=fs, canales=canales))
                print("No repetir hasta acertar para reemplazar fallos: cada intento queda registrado.")
    finally:
        if sd is not None:
            sd.stop()
        print("Carpeta de la sesión:", salida)
    if sha(carpeta / "modelo.npz") != sistema["modelo_sha256"]:
        raise RuntimeError("El modelo cambió durante la sesión: no mezclar sus resultados.")
    return salida


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--modelo", default="", help="Carpeta de la corrida K-NN; por defecto última local.")
    p.add_argument("--hablante", required=True, help="ID anónimo; H001–H006 son voces ya conocidas.")
    p.add_argument("--rondas", type=int, default=0, help="0: menú libre. N: N repeticiones de cada comando, sin descartar fallos.")
    p.add_argument("--wav", type=Path, help="Probar un WAV PCM16 sin micrófono; no usar audios de prueba reservada.")
    p.add_argument("--esperada", choices=[*COMANDOS, "otra", "silencio", "no_informada"], default="no_informada")
    args = p.parse_args()
    try:
        ejecutar(args)
    except (KeyboardInterrupt, EOFError):
        print("\nSesión interrumpida. Los intentos ya guardados se conservan.")
    except Exception as e:
        p.exit(2, f"No se pudo completar la prueba: {type(e).__name__}: {e}\n")
