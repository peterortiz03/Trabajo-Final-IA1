import sys
import unittest
from pathlib import Path
import numpy as np
RAIZ=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(RAIZ/'src'))
from knn_audio_precision import clasificador, cargar_paquete

class VotoCercano(unittest.TestCase):
    def test_mayoria_gana_a_minoria_mas_proxima(self):
        X=np.array([[.1],[1.],[2.],[3.],[4.]])
        y=np.array(['salir','identificar','identificar','identificar','reconocer'])
        self.assertEqual(clasificador(5).fit(X,y).predict([[0]])[0],'identificar')

    def test_empate_solo_entre_mayoritarias(self):
        X=np.array([[.1],[1.],[2.],[3.],[4.]])
        y=np.array(['salir','reconocer','identificar','reconocer','identificar'])
        self.assertEqual(clasificador(5).fit(X,y).predict([[0]])[0],'reconocer')

    def test_distancia_igual_conserva_indice(self):
        self.assertEqual(clasificador(1).fit([[-1],[1]],['salir','reconocer']).predict([[0]])[0],'salir')

    def test_empate_en_limite_k(self):
        X=np.array([[1.],[-1.],[1.],[-1.],[1.],[-1.]])
        y=['reconocer','reconocer','identificar','identificar','salir','salir']
        self.assertEqual(clasificador(5).fit(X,y).predict([[0]])[0],'reconocer')

    def test_paquete_real_y_recarga(self):
        carpeta=RAIZ/'modelos/audio/precision_v2'
        if not carpeta.exists(): self.skipTest('Paquete no instalado')
        s=cargar_paquete(carpeta)
        self.assertEqual(s['modelo']['knn'].n_neighbors,5)
        self.assertEqual(len(s['modelo']['etiquetas']),179)
        self.assertTrue(np.isfinite(s['modelo']['Z_entrenamiento']).all())
        q=s['modelo']['Z_entrenamiento'][:7]
        esperado=s['modelo']['knn'].predict(q)
        np.testing.assert_array_equal(esperado,cargar_paquete(carpeta)['modelo']['knn'].predict(q))

if __name__=='__main__': unittest.main()
