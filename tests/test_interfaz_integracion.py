"""Contratos de integración; no usan la prueba reservada ni entrenan modelos.

Los resultados inventados se limitan a pruebas de coordinación de Sesion.
La concordancia biométrica usa parámetros reales publicados y desarrollo.
"""
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from threading import Event
import unittest
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image

os.environ.setdefault('MPLBACKEND', 'Agg')
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'src'))
from interfaz_estado import Sesion, EstadoHuella as E
from interfaz_servicios import Servicios, abrir_imagen, cargar_huellas, evaluar_huella, leer_json
from grabar_audio import capturar_pcm, configurar_dispositivo


class Ciclo(unittest.TestCase):
    def setUp(self):
        self.s = Sesion()
        # SIMULACIÓN exclusiva de coordinación, sin pretender evaluar huellas.
        self.autorizada = dict(aceptada=True, identidad='SIMULADA')

    def autorizar(self):
        self.s.seleccionar('ejemplo.png')
        t = self.s.reconocer()
        self.s.evaluada(t, self.autorizada)

    def test_precondiciones_cancelacion_y_reemplazo(self):
        with self.assertRaisesRegex(ValueError, 'Seleccioná'):
            self.s.reconocer()
        self.autorizar()
        self.assertEqual(self.s.identidad_visible, '')
        self.assertEqual(self.s.identificar(), 'SIMULADA')
        antes = vars(self.s).copy()
        self.s.seleccionar(None)
        self.assertEqual(vars(self.s), antes)
        self.s.seleccionar('otra.png')
        self.assertEqual(self.s.estado, E.PENDIENTE)
        self.assertIsNone(self.s.resultado)
        self.assertEqual(self.s.identidad_visible, '')
        with self.assertRaisesRegex(ValueError, 'Primero reconocé'):
            self.s.identificar()

    def test_rechazo_y_error_no_conservan_autorizacion(self):
        self.autorizar()
        self.s.identificar()
        token = self.s.reconocer()
        self.assertIsNone(self.s.resultado)
        self.assertEqual(self.s.identidad_visible, '')
        self.s.evaluada(token, dict(aceptada=False, identidad=''))
        self.assertEqual(self.s.estado, E.RECHAZADA)
        with self.assertRaises(ValueError):
            self.s.identificar()
        token = self.s.reconocer()
        self.s.evaluada(token, error=ValueError('imagen inválida'))
        self.assertEqual(self.s.estado, E.ERROR)
        self.assertIsNone(self.s.resultado)

    def test_operaciones_excluyentes_y_respuestas_tardias(self):
        self.s.seleccionar('una.png')
        t = self.s.reconocer()
        for operacion in (lambda: self.s.seleccionar('otra.png'), self.s.reconocer,
                          self.s.identificar, lambda: self.s.iniciar('voz')):
            with self.assertRaises(ValueError):
                operacion()
        self.assertFalse(self.s.evaluada((t[0]-1, t[1]), self.autorizada))
        self.s.cerrar()
        self.assertFalse(self.s.evaluada(t, self.autorizada))
        self.assertIsNone(self.s.resultado)


class InferenciaReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = leer_json(RAIZ / 'config/aplicacion_respaldo.json')
        cls.sistema = cargar_huellas(cls.cfg['huellas'])
        with (RAIZ / 'datos/metadatos_con_rotaciones_train_v1.csv').open(encoding='utf-8-sig') as f:
            cls.filas = {r['muestra']: r for r in csv.DictReader(f) if r['particion'] != 'prueba'}

    def test_original_a_inferencia_coincide_con_modulos_y_distancias_publicadas(self):
        from normalizacion_final import normalizar_huella
        from caracteristicas_huellas import extraer_huella, nombres_caracteristicas
        from calibrar_rechazo_huellas import decidir_acceso
        with (RAIZ / 'documentos/evidencias/06_huellas_referencia/03_rechazo/decisiones_validacion.csv').open(encoding='utf-8-sig') as f:
            evidencia = {r['muestra']: r for r in csv.DictReader(f)}
        muestras = ['A01_M21', 'A02_M21', 'A03_M21', 'I01_M01']
        # También el rechazo de una autorizada: no ocultar esa limitación previa.
        muestras += [n for n, r in evidencia.items() if r['grupo_real'] == 'autorizado' and r['aceptada'] == 'False']
        for muestra in muestras:
            with self.subTest(muestra=muestra):
                p = RAIZ / self.filas[muestra]['original']
                antes = hashlib.sha256(p.read_bytes()).hexdigest()
                imagen = abrir_imagen(p)
                r = evaluar_huella(imagen, self.sistema)
                normal, info = normalizar_huella(imagen, self.sistema['cfg_norm'])
                v, _ = extraer_huella(normal, info['mascara_normalizada'], self.sistema['cfg_ext'])
                directo = decidir_acceso(v, nombres_caracteristicas(self.sistema['cfg_ext']),
                    self.sistema['modelo'], self.sistema['umbral'])[0]
                for clave in directo:
                    self.assertEqual(r[clave], directo[clave])
                self.assertAlmostEqual(r['distancia'], float(evidencia[muestra]['distancia']), places=10)
                self.assertEqual(r['aceptada'], evidencia[muestra]['aceptada'] == 'True')
                self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), antes)
                if not r['aceptada']:
                    self.assertEqual(r['identidad'], '')

    def test_imagen_vacia_es_error_no_rechazo_y_lectura_no_depende_del_nombre(self):
        with self.assertRaises(ValueError):
            evaluar_huella(Image.new('L', (275, 400), 255), self.sistema)
        p = RAIZ / self.filas['A01_M21']['original']
        with tempfile.TemporaryDirectory() as tmp:
            renombrada = Path(tmp) / 'nombre_sin_identidad.png'
            renombrada.write_bytes(p.read_bytes())
            self.assertEqual(evaluar_huella(abrir_imagen(p), self.sistema),
                             evaluar_huella(abrir_imagen(renombrada), self.sistema))
            with self.assertRaises(OSError):
                abrir_imagen(Path(tmp) / 'ausente.png')

    def test_recursos_ausentes_son_independientes(self):
        with tempfile.TemporaryDirectory() as tmp:
            sin_config = Servicios.cargar(Path(tmp) / 'config_ausente.json')
        self.assertIn('configuración', sin_config.errores)
        self.assertIsNone(sin_config.huellas)
        self.assertIsNone(sin_config.voz)
        cfg = json.loads(json.dumps(self.cfg))
        cfg['huellas']['modelo'] = 'modelo_ausente_controlado'
        with tempfile.TemporaryDirectory() as tmp:
            archivo = Path(tmp) / 'config.json'
            archivo.write_text(json.dumps(cfg), encoding='utf-8')
            s = Servicios.cargar(archivo)
        self.assertIsNone(s.huellas)
        self.assertIn('Restaurar', s.errores['huellas'])
        # En esta copia el modelo de voz tampoco está distribuido.
        cfg['audio']['modelo'] = 'voz_ausente_controlada'
        with tempfile.TemporaryDirectory() as tmp:
            archivo = Path(tmp) / 'config.json'
            cfg['huellas'] = self.cfg['huellas']
            archivo.write_text(json.dumps(cfg), encoding='utf-8')
            with patch.dict(sys.modules, {'sounddevice': None}):
                s = Servicios.cargar(archivo)
        self.assertIsNotNone(s.huellas)
        self.assertIsNone(s.voz)
        self.assertIn('extracción', s.errores['voz'])
        self.assertIsNone(s.sd)
        self.assertIn('micrófono', s.errores)

    def test_control_integridad_tolerasolo_saltos_de_linea(self):
        from calibrar_rechazo_huellas import cargar_sistema
        carpeta = RAIZ / self.cfg['huellas']['modelo']
        with tempfile.TemporaryDirectory() as tmp:
            for n in ('resumen.json', 'modelo_congelado.npz', 'umbral.json', 'correspondencia_congelada.json'):
                b = (carpeta/n).read_bytes()
                if n.endswith('.json'):
                    b = b.replace(b'\r\n', b'\n')
                (Path(tmp)/n).write_bytes(b)
            cargar_sistema(tmp)
            p = Path(tmp)/'umbral.json'
            p.write_text(p.read_text().replace('5.292172575840761', '999.0'))
            with self.assertRaisesRegex(ValueError, 'Calibración modificada'):
                cargar_sistema(tmp)


class CapturaCoordinada(unittest.TestCase):
    """PortAudio simulado: verifica liberación y negociación, no audio real."""
    def test_captura_pcm_original_liberada_y_cancelable(self):
        sd = Mock()
        audio = np.zeros((160, 1), dtype='int16')
        sd.rec.return_value = audio
        sd.wait.return_value = None
        inicio = Mock()
        self.assertIs(capturar_pcm(sd, 7, 16000, 1, {'duracion_s': .01}, inicio), audio)
        sd.rec.assert_called_once_with(160, samplerate=16000, channels=1, dtype='int16', device=7, blocking=False)
        inicio.assert_called_once()
        sd.stop.assert_called_once()
        evento = Event()
        sd.reset_mock()
        sd.get_stream.return_value.active = True
        with self.assertRaises(InterruptedError):
            capturar_pcm(sd, 7, 16000, 1, {'duracion_s': .01}, evento.set, evento)
        sd.stop.assert_called_once()
        sd.wait.assert_not_called()

    def test_sin_voz_util_no_se_consulta_knn(self):
        import probar_knn_audio as p
        sistema = dict(cfg_pp=leer_json(RAIZ/'config/preprocesamiento_audio_v1.json'),
                       cfg_ext=p.ca.cargar_config())
        with patch.object(p, 'predecir_vectores') as predecir:
            r, v = p.interpretar(np.zeros(48000, dtype='int16'), 16000, sistema)
        self.assertIsNone(v)
        self.assertIsNone(r['prediccion'])
        self.assertIn('sin_actividad_suficiente_segun_energia', r['avisos'])
        predecir.assert_not_called()

    def test_negociacion_mantiene_frecuencias_y_canales_existentes(self):
        sd = Mock()
        sd.query_devices.return_value = dict(default_samplerate=48000, max_input_channels=1, name='SIMULADO', hostapi=0)
        sd.query_hostapis.return_value = {'name': 'SIMULADA'}
        formato = configurar_dispositivo(sd, 3, dict(frecuencia_captura_hz=None, frecuencias_alternativas_hz=[48000, 16000]))
        self.assertEqual(formato, (3, 48000, 1, 'SIMULADO', 'SIMULADA'))


if __name__ == '__main__':
    unittest.main()
