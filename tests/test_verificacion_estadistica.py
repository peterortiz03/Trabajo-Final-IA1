"""Casos pequeños de fórmula, degeneraciones y particiones persistentes."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from verificacion_estadistica import (estadisticas, separacion, controles,
                                     aplicar_mapa_audio, representantes)


class VerificacionEstadisticaTest(unittest.TestCase):
    def test_media_por_columna_y_desvio_muestral(self):
        X = np.array([[1., 100.], [3., 104.], [9., 108.]])
        tabla = estadisticas(X, np.array(['a', 'a', 'b']), ['c1', 'c2'])
        self.assertEqual(tabla[0]['media'], 2.)
        self.assertAlmostEqual(tabla[0]['desviacion_muestral'], np.sqrt(2))
        self.assertEqual(tabla[1]['media'], 102.)
        self.assertIsNone(tabla[2]['desviacion_muestral'])
        self.assertEqual(tabla[2]['estado'], 'n_menor_2')

    def test_razon_entre_dentro_y_cambio_escala(self):
        X = np.array([[0.], [2.], [4.], [6.]])
        y = np.array(['a', 'a', 'b', 'b'])
        original = separacion(X, y, ['c'])[0]
        self.assertEqual(original['separacion'], 4.)
        self.assertAlmostEqual(separacion(-7 * X + 100, y, ['c'])[0]['separacion'], 4.)

    def test_dispersion_nula_constante_y_sin_grados_libertad(self):
        y = np.array(['a', 'a', 'b', 'b'])
        tabla = separacion(np.array([[0., 1.], [0., 1.], [2., 1.], [2., 1.]]), y, ['c', 'd'])
        self.assertEqual(tabla[0]['estado'], 'infinita_dispersion_interna_nula')
        self.assertEqual(tabla[1]['estado'], 'constante_global_0_0')
        self.assertEqual(separacion(np.array([[0.], [1.]]), np.array(['a', 'b']), ['c'])[0]['estado'], 'insuficiente')

    def test_no_finitos_visibles_y_sin_descarte(self):
        X = np.array([[1., np.nan], [1., np.inf]])
        errores, constantes = controles(X, ['m1', 'm2'], ['c', 'd'], np.array(['a', 'a']))
        self.assertEqual(len(errores), 2)
        self.assertEqual(errores[0]['muestra'], 'm1')
        self.assertTrue(any(r['caracteristica'] == 'c' for r in constantes))
        with self.assertRaises(ValueError):
            estadisticas(X, np.array(['a', 'a']), ['c', 'd'])

    def test_mapa_no_muta_y_nuevos_hablantes_requieren_asignacion(self):
        mapa = {'hablantes': {'H001': {'particion': 'entrenamiento'}}}
        fila = {'muestra_id': 'm1', 'hablante': 'H001', 'particion': 'sin_asignar'}
        self.assertEqual(aplicar_mapa_audio([fila], mapa)[0]['particion_analisis'], 'entrenamiento')
        self.assertEqual(fila['particion'], 'sin_asignar')
        with self.assertRaises(ValueError):
            aplicar_mapa_audio([dict(fila, hablante='H007')], mapa)
        with self.assertRaises(ValueError):
            aplicar_mapa_audio([dict(fila, particion='prueba')], mapa)

    def test_muestra_casos_bajo_mediano_alto(self):
        rows = [dict(caracteristica=str(i), separacion=float(i), estado='ok') for i in range(5)]
        self.assertEqual([r['caracteristica'] for r in representantes(rows)], ['0', '2', '4'])


if __name__ == '__main__':
    unittest.main()
