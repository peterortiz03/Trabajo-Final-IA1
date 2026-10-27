from pathlib import Path
import sys
import unittest
from copy import deepcopy
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from referencia_muestra import comparar_referencia


class ReferenciaMuestra(unittest.TestCase):
    def test_cinco_resultados_y_sin_modificar_decision(self):
        casos = [
            ('A01', 'autorizado', True, 'A01', 'identificacion_correcta'),
            ('A01', 'autorizado', True, 'A02', 'identidad_incorrecta'),
            ('A01', 'autorizado', False, None, 'falso_rechazo'),
            ('I01', 'intruso', False, None, 'rechazo_correcto'),
            ('I01', 'intruso', True, 'A01', 'falsa_aceptacion'),
        ]
        for identidad, grupo, aceptada, predicha, esperado in casos:
            with self.subTest(esperado=esperado):
                receta = {'origen_sorteo': {'base_id': identidad, 'grupo_referencia': grupo}}
                resultado = {'aceptada': aceptada, 'identidad': predicha, 'distancia': 3.5}
                copia = deepcopy((receta, resultado))
                self.assertEqual(comparar_referencia(receta, resultado)['codigo'], esperado)
                self.assertEqual((receta, resultado), copia)

    def test_sin_referencia_no_adivina_por_identidad_predicha(self):
        for receta in (None, {}, {'base': {'nombre': 'A01.png'}}, {'origen_sorteo': {}}):
            self.assertEqual(comparar_referencia(receta, {'aceptada': True, 'identidad': 'A01'})['estado'], 'desconocido')

    def test_interfaz_bloquea_antes_de_evaluar_y_durante_operacion(self):
        from types import SimpleNamespace
        from interfaz import Aplicacion
        for resultado, operacion, cerrada in [(None, '', False), ({'aceptada': True}, 'voz', False), ({'aceptada': True}, '', True)]:
            llamadas=[]
            app=SimpleNamespace(sesion=SimpleNamespace(resultado=resultado, operacion=operacion, cerrada=cerrada),
                                referencia_visible=False, _actualizar_referencia=lambda:llamadas.append(True))
            Aplicacion.mostrar_referencia(app)
            self.assertFalse(app.referencia_visible)
            self.assertEqual(llamadas, [])

if __name__ == '__main__':
    unittest.main()
