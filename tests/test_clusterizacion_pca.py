"""Controles relevantes: ausencia de fuga, constantes y reutilización."""
import copy
from pathlib import Path
import pickle
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import clusterizacion_pca as cp


class ContratoPCA(unittest.TestCase):
    def test_validacion_y_etiquetas_no_modifican_ajuste(self):
        rng = np.random.default_rng(7)
        X = np.column_stack([rng.normal(size=(21, 3)), np.ones(21)])
        train = np.arange(21) < 18
        y = np.array(['A01', 'A02', 'A03'] * 7)
        partes = np.where(train, 'entrenamiento', 'validacion')
        filas = [dict(muestra=f'M{i}', identidad=y[i], particion=partes[i]) for i in range(21)]
        datos = dict(X=X, train=train, y=y, nombres=np.array(['f0', 'f1', 'f2', 'f3']),
                     particiones=partes, filas=filas, ids=np.array([r['muestra'] for r in filas]),
                     catalogo_uso=filas, campo_particion='particion')
        config = cp.leer_json(cp.RAIZ / 'config/clusterizacion_pca_v1.json')
        config['mostrar_pc3'] = []
        alterados = copy.deepcopy(datos)
        alterados['X'][~train] += 10000  # No debe mover los parámetros aprendidos.
        alterados['y'] = np.roll(y, 1)  # Las etiquetas no entrenan K-means/PCA.
        with tempfile.TemporaryDirectory() as tmp, patch.object(cp, 'proyectar_paneles'):
            _, a, _ = cp.ajustar(datos, 'huellas', config, Path(tmp) / 'a')
            _, b, _ = cp.ajustar(alterados, 'huellas', config, Path(tmp) / 'b')
            for attr in ['mean_', 'scale_']:
                np.testing.assert_allclose(getattr(a['escalador'], attr), getattr(b['escalador'], attr))
            np.testing.assert_allclose(a['pca'].components_, b['pca'].components_)
            np.testing.assert_allclose(a['kmeans'].cluster_centers_, b['kmeans'].cluster_centers_)
            self.assertEqual(a['escalador'].scale_[-1], 1)
            self.assertEqual(a['escalador'].n_features_in_, 4)
            with open(Path(tmp) / 'a/modelos.pkl', 'rb') as f:
                recargado = pickle.load(f)
            pred = cp.transformar_nuevas(X, datos['nombres'], recargado)
            np.testing.assert_allclose(pred['pca'], a['pca'].transform(a['escalador'].transform(X)))
            with self.assertRaises(ValueError):
                cp.transformar_nuevas(X, datos['nombres'][::-1], a)

    def test_mapa_rechaza_conflictos_y_voces_nuevas(self):
        mapa = {'hablantes': {'H001': {'particion': 'entrenamiento'}}}
        for voz, part in [('H001', 'prueba'), ('H009', 'sin_asignar')]:
            with self.assertRaises(ValueError):
                cp.aplicar_mapa_audio([dict(hablante=voz, particion=part, muestra_id='m')], mapa)

    def test_intrusos_y_prueba_no_entran(self):
        filas = [dict(muestra=f'M{i}', identidad=f'A{i%3+1:02}', grupo='autorizado',
                      particion='entrenamiento', estado_extraccion='vectorizada') for i in range(6)]
        filas += [dict(muestra='I', identidad='I01', grupo='intruso', particion='validacion', estado_extraccion='vectorizada'),
                  dict(muestra='P', identidad='A01', grupo='autorizado', particion='prueba', estado_extraccion='vectorizada')]
        datos = dict(X=np.arange(32).reshape(8, 4), catalogo=filas, filas=filas,
                     ids=np.array([r['muestra'] for r in filas]), nombres=np.array(['a', 'b', 'c', 'd']))
        with patch.object(cp, 'cargar_ejecucion', return_value=datos):
            r = cp.preparar(cp.RAIZ, 'huellas', '', {})
        self.assertEqual(len(r['X']), 6)
        self.assertNotIn('I', r['ids']); self.assertNotIn('P', r['ids'])


if __name__ == '__main__':
    unittest.main()
