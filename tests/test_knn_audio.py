"""Contratos relevantes: voces separadas, escalado sin fuga e inferencia guardada."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from threadpoolctl import threadpool_limits

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import knn_audio as audio


class ContratosAudio(unittest.TestCase):
    def setUp(self):
        self.c = audio.leer_json(audio.RAIZ / "config/knn_audio_v1.json")
        self.y = np.tile(self.c["comandos"], 6)
        self.voces = np.repeat(["A", "B", "C"], 6)
        self.ids = np.array([f"m{i}" for i in range(18)])
        self.X = np.column_stack([np.tile([0., 10., 20.], 6), np.arange(18.), np.ones(18)])

    def test_loso_no_ajusta_con_hablante_retenido(self):
        with threadpool_limits(limits=1):
            _, _, _, preds, contratos = audio.comparar_loso(
                self.X, self.y, self.voces, self.ids, ["a", "b", "constante"], self.c)
        self.assertEqual(len(preds), len(self.X)*8)
        for contrato in contratos:
            voz = contrato["hablante_retenido"]
            self.assertNotIn(voz, contrato["hablantes_ajuste"])
            self.assertFalse(set(contrato["muestras_ajuste"]) & set(contrato["muestras_retenidas"]))
            np.testing.assert_allclose(contrato["medias"], self.X[self.voces != voz].mean(axis=0))
            self.assertEqual(contrato["escalas"][-1], 1.)
        # Un cambio extremo de la voz retenida no debe cambiar su escalador.
        alterada = self.X.copy()
        alterada[self.voces == "A"] += 100000
        with threadpool_limits(limits=1):
            otros = audio.comparar_loso(alterada, self.y, self.voces, self.ids,
                                       ["a", "b", "constante"], self.c)[-1]
        np.testing.assert_equal(contratos[0]["medias"], otros[0]["medias"])

    def test_prueba_no_entra_y_revision_pendiente_detiene(self):
        filas = [dict(muestra_id=str(i), hablante=v, comando=y, decision_revision="conservar",
                      estado_extraccion="vectorizada", particion_analisis=p)
                 for i, (v, y, p) in enumerate(zip(
                     ["A"]*3 + ["B"]*3 + ["TEST"]*3,
                     self.c["comandos"]*3, ["entrenamiento"]*6 + ["prueba"]*3))]
        X = np.arange(27., dtype=float).reshape(9, 3)
        X[-3:] = np.nan  # Ni siquiera los valores de prueba deben ser analizados.
        d = dict(X=X, filas=filas, catalogo=copy.deepcopy(filas))
        with patch.object(audio, "cargar_ejecucion", return_value=d), \
                patch.object(audio, "leer_json", return_value={}), \
                patch.object(audio, "aplicar_mapa_audio", side_effect=lambda f, m: copy.deepcopy(f)):
            r = audio.preparar_audio(Path("."), self.c)
            self.assertEqual(len(r["X"]), 6)
            self.assertNotIn("TEST", r["voces"])
        d["catalogo"][0]["decision_revision"] = "pendiente"
        with patch.object(audio, "cargar_ejecucion", return_value=d), \
                patch.object(audio, "leer_json", return_value={}), \
                patch.object(audio, "aplicar_mapa_audio", side_effect=lambda f, m: copy.deepcopy(f)):
            with self.assertRaisesRegex(ValueError, "Revisión pendiente"):
                audio.preparar_audio(Path("."), self.c)

    def test_recarga_no_cambia_predicciones_y_exige_orden(self):
        scaler = audio.StandardScaler().fit(self.X)
        Z = scaler.transform(self.X)
        original = dict(nombres=["a", "b", "constante"], media=scaler.mean_, escala=scaler.scale_,
                        knn=audio.clasificador(1, "uniform").fit(Z, self.y))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            np.savez_compressed(p / "modelo.npz", nombres=original["nombres"], media=scaler.mean_,
                escala=scaler.scale_, Z_entrenamiento=Z, etiquetas=self.y)
            audio.guardar_json(p / "parametros_elegidos.json", dict(k=1, votos="uniform"))
            audio.guardar_json(p / "resumen.json", dict(archivos_sha256={
                f: audio.sha(p/f) for f in ["modelo.npz", "parametros_elegidos.json"]}))
            recargado = audio.cargar_modelo(p)
            consulta = self.X[:4] + .01
            np.testing.assert_equal(audio.predecir_vectores(consulta, original["nombres"], original),
                                    audio.predecir_vectores(consulta, original["nombres"], recargado))
            with self.assertRaisesRegex(ValueError, "orden"):
                audio.predecir_vectores(consulta, ["b", "a", "constante"], recargado)
            (p / "parametros_elegidos.json").write_text(json.dumps(dict(k=3, votos="uniform")))
            with self.assertRaisesRegex(ValueError, "modificados"):
                audio.cargar_modelo(p)


if __name__ == "__main__":
    unittest.main()
