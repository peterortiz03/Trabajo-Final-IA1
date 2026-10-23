"""Contrato del umbral, inferencia sin etiquetas y reserva de prueba."""
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import calibrar_rechazo_huellas as rechazo


class RechazoHuellas(unittest.TestCase):
    def test_separacion_perfecta_elige_punto_medio(self):
        mejor, _ = rechazo.elegir_umbral([1., 2., 6., 7.], [True, True, False, False])
        self.assertEqual(mejor["umbral"], 4.)
        self.assertEqual(mejor["FAR"], 0.)
        self.assertEqual(mejor["FRR"], 0.)

    def test_solapamiento_y_desempate_priorizan_menor_far(self):
        mejor, _ = rechazo.elegir_umbral([1., 3., 2., 4.], [True, True, False, False])
        self.assertEqual(mejor["umbral"], 1.5)
        self.assertEqual(mejor["FAR"], 0.)
        self.assertEqual(mejor["FRR"], .5)

    def test_distancias_iguales_no_se_separan_por_etiqueta(self):
        mejor, _ = rechazo.elegir_umbral([2., 2.], [True, False])
        self.assertEqual(mejor["umbral"], 0.)
        self.assertEqual(mejor["error_balanceado"], .5)
        for d, a in [([1.], [True]), ([np.nan, 2.], [True, False]),
                     ([-1., 2.], [True, False])]:
            with self.assertRaises(ValueError):
                rechazo.elegir_umbral(d, a)

    def modelo(self):
        return dict(nombres=np.array(["a", "b"]), indices=np.array([0, 1]),
                    nombres_seleccionados=np.array(["a", "b"]),
                    media=np.zeros(2), escala=np.ones(2),
                    centroides=np.array([[0., 0.], [10., 0.], [20., 0.]]),
                    correspondencia={"0": "A01", "1": "A02", "2": "A03"})

    def test_borde_inclusivo_identidad_oculta_y_sin_reajuste(self):
        m = self.modelo()
        originales = {k: v.copy() for k, v in m.items() if isinstance(v, np.ndarray)}
        salida = rechazo.decidir_acceso([[1., 0.], [1.1, 0.]], ["a", "b"], m, 1.)
        self.assertEqual(salida[0]["identidad"], "A01")
        self.assertTrue(salida[0]["aceptada"])
        self.assertFalse(salida[1]["aceptada"])
        self.assertEqual(salida[1]["identidad"], "")
        self.assertEqual(salida[1]["estado"], "NO AUTORIZADO")
        for k, v in originales.items():
            np.testing.assert_array_equal(m[k], v)
        with self.assertRaises(ValueError):
            rechazo.decidir_acceso([[1., 0.]], ["b", "a"], m, 1.)
        with self.assertRaises(ValueError):
            rechazo.decidir_acceso([[np.nan, 0.]], ["a", "b"], m, 1.)

    def test_calibracion_no_incluye_entrenamiento_ni_prueba(self):
        filas = [dict(muestra="a", particion="validacion", grupo="autorizado", estado_extraccion="vectorizada", sha256_base="A"),
                 dict(muestra="i", particion="validacion", grupo="intruso", estado_extraccion="vectorizada", sha256_base="I_val"),
                 dict(muestra="tr", particion="entrenamiento", grupo="autorizado", estado_extraccion="vectorizada", sha256_base="A"),
                 dict(muestra="te", particion="prueba", grupo="intruso", estado_extraccion="diferida_prueba", sha256_base="I_test")]
        d = dict(X=np.array([[1., 2.], [3., 4.], [99., 99.], [np.nan, np.nan]]),
                 filas=filas, catalogo=filas)
        X, elegidas = rechazo.seleccionar_validacion(d)
        self.assertEqual([r["muestra"] for r in elegidas], ["a", "i"])
        np.testing.assert_array_equal(X, [[1., 2.], [3., 4.]])
        d["catalogo"][-1]["sha256_base"] = "I_val"
        with self.assertRaises(ValueError):
            rechazo.seleccionar_validacion(d)


if __name__ == "__main__":
    unittest.main()
