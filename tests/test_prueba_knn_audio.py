"""La captura y el WAV deben seguir el mismo camino acústico que el dataset."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import probar_knn_audio as prueba


class ContratosPruebaAudio(unittest.TestCase):
    def setUp(self):
        self.pp = prueba.leer_json(prueba.RAIZ / "config/preprocesamiento_audio_v1.json")
        self.ext = prueba.ca.cargar_config()
        # Señal artificial para verificar equivalencia de formato, no reconocimiento.
        fs = 16000
        t = np.arange(fs) / fs
        activa = .2*np.sin(2*np.pi*240*t)*np.sin(np.pi*t)**2
        self.audio = np.rint(np.r_[np.zeros(fs//2), activa, np.zeros(fs//2)]*32768).astype("int16")

    def test_vector_igual_al_trayecto_wav_pcm16(self):
        v, detalle, info = prueba.vectorizar(self.audio, 16000, self.pp, self.ext)
        x, d = prueba.pp.preprocesar_audio(self.audio, 16000, self.pp)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "procesado.wav"
            prueba.guardar_wav(p, np.rint(x*32768).astype("int16"), 16000)
            pcm, fs = prueba.pp.leer_wav_pcm16(p)
        limites = prueba.ca.limites_desde_detalle(d, fs, len(pcm))
        esperado, _ = prueba.ca.extraer_audio(pcm, fs, limites, self.ext)
        np.testing.assert_array_equal(v, esperado)
        self.assertEqual(len(v), 160)

    def test_silencio_sin_vector_no_fuerza_palabra(self):
        sistema = dict(cfg_pp=self.pp, cfg_ext=self.ext)
        with patch.object(prueba, "predecir_vectores") as predict:
            r, v = prueba.interpretar(np.zeros(48000, dtype="int16"), 16000, sistema)
        self.assertIsNone(v)
        self.assertIsNone(r["prediccion"])
        predict.assert_not_called()

    def test_consulta_no_ajusta_modelo_y_conserva_fallos(self):
        v, _, _ = prueba.vectorizar(self.audio, 16000, self.pp, self.ext)
        nombres = np.array(prueba.ca.nombres_caracteristicas(self.ext))
        from knn_audio import clasificador
        knn = clasificador(1, "uniform").fit(np.vstack([v, v+10]), ["salir", "reconocer"])
        sistema = dict(cfg_pp=self.pp, cfg_ext=self.ext, ids=np.array(["a", "b"]),
            voces=np.array(["A", "B"]), modelo_sha256="modelo_fijo",
            modelo=dict(knn=knn, nombres=nombres, media=np.zeros(160), escala=np.ones(160),
                        etiquetas=np.array(["salir", "reconocer"])))
        antes = knn._fit_X.copy()
        with tempfile.TemporaryDirectory() as tmp, patch.object(knn, "fit", side_effect=AssertionError("No ajustar en consulta")):
            filas = []
            with patch("builtins.print"):
                prueba.registrar(Path(tmp), 1, self.audio, 16000, "identificar", sistema, filas)
                prueba.registrar(Path(tmp), 2, np.zeros(48000, dtype="int16"), 16000, "identificar", sistema, filas)
            resumen = prueba.leer_json(Path(tmp) / "resumen_prueba.json")
            self.assertEqual(resumen["comandos_intentados"], 2)
            self.assertEqual(resumen["aciertos"], 0)
            self.assertEqual(resumen["sin_vector"], 1)
            self.assertEqual(len(list(Path(tmp).glob("toma_*.wav"))), 2)
        np.testing.assert_array_equal(antes, knn._fit_X)


if __name__ == "__main__":
    unittest.main()
