"""Pruebas del contrato de selección, ajuste interno y reutilización."""
from pathlib import Path
import pickle
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import mejorar_clusterizacion_huellas as mejora


class SeleccionHuellas(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(13)
        self.y = np.repeat(["A01", "A02", "A03"], 10)
        self.X = rng.normal(size=(30, 8))
        self.X[:, 0] = np.repeat([0., 20., 40.], 10) + rng.normal(0, .1, 30)
        self.X[:, 7] = 1.
        self.nombres = np.array([f"f{i}" for i in range(8)])
        self.config = mejora.leer_json(mejora.RAIZ / "config/mejora_huellas_v1.json")
        self.config["divisiones_cv"] = 3
        self.config["kmeans"]["n_init"] = 2

    def test_ranking_no_depende_de_unidades_y_constante_no_se_prioriza(self):
        a, _ = mejora.ranking_entrenamiento(self.X, self.y, self.nombres)
        b, _ = mejora.ranking_entrenamiento(self.X * np.arange(1, 9) * 100, self.y, self.nombres)
        np.testing.assert_array_equal(a, b)
        self.assertEqual(a[0], 0)
        self.assertEqual(a[-1], 7)

    def test_cv_ajusta_solo_subentrenamiento_en_cada_pliegue(self):
        original = mejora.ajustar
        with patch.object(mejora, "ajustar", wraps=original) as ajuste:
            _, resumen, detalle, pliegues = mejora.elegir_con_cv(
                self.X, self.y, self.nombres, self.config)
        self.assertEqual(ajuste.call_count, 9)  # 3 variantes x 3 pliegues.
        for llamada in ajuste.call_args_list:
            Xsub, ysub = llamada.args[:2]
            self.assertEqual(len(Xsub), 20)
            self.assertEqual(len(ysub), 20)
        self.assertEqual(len(detalle), 9)
        self.assertEqual(sorted(r["fila_train"] for r in pliegues), list(range(30)))

    def test_etiquetas_no_cambian_kmeans_si_no_hay_seleccion(self):
        a = mejora.ajustar(self.X, self.y, self.nombres, 8, self.config)
        b = mejora.ajustar(self.X, np.roll(self.y, 10), self.nombres, 8, self.config)
        np.testing.assert_allclose(a["kmeans"].cluster_centers_, b["kmeans"].cluster_centers_)

    def test_transformacion_y_recarga_no_reajustan(self):
        modelo = mejora.ajustar(self.X, self.y, self.nombres, 4, self.config, con_pca=True)
        modelo = pickle.loads(pickle.dumps(modelo))
        antes = modelo["escalador"].mean_.copy()
        centros = modelo["kmeans"].cluster_centers_.copy()
        nuevas = self.X[:2] + 1000
        pred = mejora.transformar(nuevas, self.nombres, modelo)
        np.testing.assert_array_equal(modelo["escalador"].mean_, antes)
        np.testing.assert_array_equal(modelo["kmeans"].cluster_centers_, centros)
        Z = modelo["escalador"].transform(nuevas[:, modelo["indices"]])
        np.testing.assert_array_equal(pred["grupos"], modelo["kmeans"].predict(Z))
        self.assertEqual(pred["proyeccion"].shape[0], 2)
        with self.assertRaises(ValueError):
            mejora.transformar(nuevas, self.nombres[::-1], modelo)
        with self.assertRaises(ValueError):
            mejora.transformar(np.full((1, 8), np.nan), self.nombres, modelo)


if __name__ == "__main__":
    unittest.main()
