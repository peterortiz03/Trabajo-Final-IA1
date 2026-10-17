"""Pruebas de integridad con señales temporales; no generan un dataset de voz."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from audio_archivos import Catalogo, bloqueo, calidad_inicial

CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'config/audio_v1.json').read_text())


class IntegridadAudio(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cat = Catalogo(Path(self.tmp.name))
        (self.cat.originales / 'H001/S001').mkdir(parents=True)
        # Señal de prueba de archivos: no es voz ni se entrega como muestra.
        self.audio = np.full((1600, 1), 1000, dtype=np.int16)

    def guardar(self, sesion='S001', comando='reconocer'):
        with bloqueo(self.cat.base):
            return self.cat.guardar(self.audio, 16000, 'H001', sesion, comando,
                                    CONFIG, 'dispositivo simulado', 'sin hardware')

    def test_numeracion_despues_de_reabrir(self):
        self.assertTrue(self.guardar()['muestra_id'].endswith('_0001'))
        self.cat = Catalogo(Path(self.tmp.name))
        self.assertTrue(self.guardar()['muestra_id'].endswith('_0002'))
        self.assertEqual(len(self.cat.verificar()), 2)

    def test_contadores_por_sesion_y_palabra(self):
        self.guardar()
        self.assertTrue(self.guardar(comando='salir')['muestra_id'].endswith('_0001'))
        (self.cat.originales / 'H001/S002').mkdir()
        self.assertTrue(self.guardar(sesion='S002')['muestra_id'].endswith('_0001'))

    def test_recupera_corte_entre_wav_y_csv(self):
        with patch.object(self.cat, 'escribir', side_effect=OSError('corte simulado')):
            with self.assertRaises(OSError):
                self.guardar()
        self.assertTrue(self.cat.pendiente.exists())
        self.assertEqual(self.cat.leer(), [])
        self.cat = Catalogo(Path(self.tmp.name))
        with bloqueo(self.cat.base):
            self.assertTrue(self.cat.recuperar())
            self.assertFalse(self.cat.recuperar())
        self.assertEqual(len(self.cat.verificar()), 1)

    def test_recupera_corte_antes_de_incorporar_original(self):
        with patch.object(self.cat, 'recuperar', side_effect=OSError('corte simulado')):
            with self.assertRaises(OSError):
                self.guardar()
        self.assertTrue(self.cat.temporal.exists())
        with bloqueo(self.cat.base):
            self.cat.recuperar()
        self.assertEqual(len(self.cat.verificar()), 1)

    def test_no_duplica_csv_si_falla_fin_de_guardado(self):
        fila = self.guardar()
        self.cat.pendiente.write_text(json.dumps(fila), encoding='utf-8')
        with bloqueo(self.cat.base):
            self.cat.recuperar()
        self.assertEqual(len(self.cat.verificar()), 1)

    def test_recupera_corte_entre_enlace_y_borrado_temporal(self):
        with patch.object(self.cat, 'recuperar', side_effect=OSError('corte simulado')):
            with self.assertRaises(OSError):
                self.guardar()
        fila = json.loads(self.cat.pendiente.read_text())
        original = self.cat.ruta(fila['ruta_original'])
        os.link(self.cat.temporal, original)
        antes = original.read_bytes()
        with bloqueo(self.cat.base):
            self.cat.recuperar()
        self.assertFalse(self.cat.temporal.exists())
        self.guardar()
        self.assertEqual(original.read_bytes(), antes)
        self.assertEqual(len(self.cat.verificar()), 2)

    def test_no_sobrescribe_wav_existente(self):
        primera = self.guardar()
        ruta = self.cat.ruta(primera['ruta_original'])
        antes = ruta.read_bytes()
        self.guardar()
        self.assertEqual(ruta.read_bytes(), antes)

    def test_detecta_wav_truncado_y_huerfano(self):
        fila = self.guardar()
        p = self.cat.ruta(fila['ruta_original'])
        original = p.read_bytes()
        p.write_bytes(original[:-20])
        with self.assertRaises(ValueError):
            self.cat.verificar()
        p.write_bytes(original)
        (p.parent / 'huerfano.wav').write_bytes(original)
        with self.assertRaises(RuntimeError):
            self.cat.verificar()

    def test_detecta_configuracion_modificada(self):
        fila = self.guardar()
        self.cat.ruta(fila['configuracion_ref']).write_text('{}')
        with self.assertRaises(ValueError):
            self.cat.verificar()

    def test_silencio_saturacion_y_original_sin_transformar(self):
        silencio = calidad_inicial(np.zeros((1600, 1), dtype=np.int16), CONFIG['calidad'])
        self.assertIn('captura_nula', silencio['avisos_calidad'])
        saturado = calidad_inicial(np.full((1600, 2), 32767, dtype=np.int16), CONFIG['calidad'])
        self.assertIn('posible_saturacion', saturado['avisos_calidad'])
        copia = self.audio.copy()
        self.guardar()
        np.testing.assert_array_equal(self.audio, copia)

    def test_captura_sin_guardar_no_registra_filas(self):
        calidad_inicial(self.audio, CONFIG['calidad'])
        self.assertEqual(self.cat.leer(), [])
        self.assertEqual(list(self.cat.originales.rglob('*.wav')), [])


if __name__ == '__main__':
    unittest.main()
