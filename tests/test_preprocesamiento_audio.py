"""Casos de señal e integridad; todos los fixtures viven en carpetas temporales."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from audio_archivos import Catalogo, bloqueo, hash_archivo
import preprocesamiento_audio as pp
import preprocesar_dataset_audio as lote

RAIZ = Path(__file__).resolve().parents[1]
CFG = json.loads((RAIZ/'config/preprocesamiento_audio_v1.json').read_text())
CAPTURA = json.loads((RAIZ/'config/audio_v1.json').read_text())


def pulso(fs=48000, frecuencia=500, amplitud=.15):
    x = np.zeros(fs*3)
    n = fs//2
    t = np.arange(n)/fs
    x[fs:fs+n] = amplitud*np.sin(2*np.pi*frecuencia*t)*np.hanning(n)
    return x


class Senales(unittest.TestCase):
    def test_silencio_no_se_amplifica(self):
        y, d = pp.preprocesar_audio(np.zeros(48000*3), 48000, CFG)
        self.assertIsNone(y)
        self.assertEqual(d['estado'], 'sin_salida_revisar')
        self.assertNotIn('ganancia_db', d)

    def test_ruido_estacionario_no_es_voz_por_tener_energia(self):
        x = np.random.default_rng(123).normal(0,.025,48000*3)
        y, d = pp.preprocesar_audio(x,48000,CFG)
        self.assertIsNone(y)
        self.assertIn('sin_actividad_suficiente_segun_energia',d['avisos'])

    def test_impulso_aislado_no_es_palabra(self):
        x=np.zeros(48000*3);x[48000]=.8
        y,_=pp.preprocesar_audio(x,48000,CFG)
        self.assertIsNone(y)

    def test_remuestreo_margenes_y_duracion_sin_estirar(self):
        y,d=pp.preprocesar_audio(pulso(),48000,CFG)
        self.assertIsNotNone(y)
        self.assertEqual(d['frecuencia_procesada_hz'],16000)
        self.assertLess(d['recorte_inicio_s'],1)
        self.assertGreater(d['recorte_fin_s'],1.5)
        self.assertLess(d['duracion_procesada_s'],1.2)
        frecuencias=np.fft.rfftfreq(len(y),1/16000)
        dominante=frecuencias[np.argmax(abs(np.fft.rfft(y)))]
        self.assertLess(abs(dominante-500),5)

    def test_antialias_atenua_frecuencia_fuera_de_banda(self):
        x=pulso(frecuencia=500,amplitud=.15)+pulso(frecuencia=12000,amplitud=.15)
        y,_=pp.preprocesar_audio(x,48000,CFG)
        espectro=abs(np.fft.rfft(y));freq=np.fft.rfftfreq(len(y),1/16000)
        baja=max(espectro[(freq>480)&(freq<520)])
        alias=max(espectro[(freq>3950)&(freq<4050)])
        self.assertLess(alias/baja,.02)

    def test_amplificacion_limitada(self):
        y,d=pp.preprocesar_audio(pulso(amplitud=.03),48000,CFG)
        self.assertIsNotNone(y)
        self.assertAlmostEqual(d['ganancia_db'],6)
        self.assertLessEqual(max(abs(y)),.8+1e-12)

    def test_saturacion_se_conserva_como_aviso(self):
        x=pulso(amplitud=.5);x[50000:50100]=1
        y,d=pp.preprocesar_audio(x,48000,CFG)
        self.assertIsNotNone(y)
        self.assertIn('picos_cercanos_al_limite_original',d['avisos'])
        self.assertLessEqual(max(abs(y)),.8+1e-12)

    def test_borde_no_descarta(self):
        x=pulso();x[-4800:]=.1*np.sin(2*np.pi*500*np.arange(4800)/48000)
        y,d=pp.preprocesar_audio(x,48000,CFG)
        self.assertIsNotNone(y)
        self.assertIn('actividad_cerca_del_final',d['avisos'])
        self.assertEqual(d['recorte_fin_s'],3)

    def test_estereo_y_cancelacion(self):
        x=pulso();y,d=pp.preprocesar_audio(np.column_stack([x,x]),48000,CFG)
        self.assertEqual(y.ndim,1)
        y,d=pp.preprocesar_audio(np.column_stack([x,-x]),48000,CFG)
        self.assertIsNone(y)
        self.assertIn('posible_cancelacion_al_convertir_a_mono',d['avisos'])

    def test_nan_vacio_y_config_invalida(self):
        for x in (np.array([]),np.array([np.nan]),np.array([np.inf])):
            with self.assertRaises(ValueError):pp.preprocesar_audio(x,48000,CFG)
        with self.assertRaises(ValueError):pp.validar_config(dict(CFG,pico_objetivo=1.5))


class Incremental(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.raiz=Path(self.tmp.name);self.cat=Catalogo(self.raiz)
        (self.cat.originales/'H001/S001').mkdir(parents=True)
        self.guardar()

    def guardar(self):
        with bloqueo(self.cat.base):
            return self.cat.guardar(np.rint(pulso()*32768).astype(np.int16)[:,None],48000,
                                    'H001','S001','reconocer',CAPTURA,'simulado','simulado')

    def ejecutar(self,cfg=CFG,revisiones=None):
        with redirect_stdout(io.StringIO()):
            return lote.ejecutar(self.raiz,cfg,revisiones)

    def test_repeticion_y_nueva_captura(self):
        fila=self.cat.leer()[0];original=self.cat.ruta(fila['ruta_original'])
        antes=hash_archivo(original)
        self.assertEqual(self.ejecutar()['nuevos'],1)
        salida=self.cat.ruta(self.cat.leer()[0]['ruta_procesada'])
        tiempo=salida.stat().st_mtime_ns
        self.assertEqual(self.ejecutar()['omitidos'],1)
        self.assertEqual(salida.stat().st_mtime_ns,tiempo)
        self.guardar()
        r=self.ejecutar();self.assertEqual((r['nuevos'],r['omitidos']),(1,1))
        self.assertEqual(hash_archivo(original),antes)
        self.assertEqual(len(self.cat.verificar()),2)

    def test_cambio_config_conserva_resultado_anterior(self):
        self.ejecutar();anterior=self.cat.ruta(self.cat.leer()[0]['ruta_procesada'])
        contenido=anterior.read_bytes()
        self.ejecutar(dict(CFG,margen_ms=200))
        nuevo=self.cat.ruta(self.cat.leer()[0]['ruta_procesada'])
        self.assertNotEqual(nuevo,anterior)
        self.assertEqual(anterior.read_bytes(),contenido)

    def test_interrupcion_antes_de_consolidar_se_recupera(self):
        with patch.object(lote,'csv_atomico',side_effect=OSError('corte simulado')):
            with self.assertRaises(OSError):self.ejecutar()
        self.assertEqual(self.cat.leer()[0]['estado_procesamiento'],'pendiente')
        r=self.ejecutar()
        self.assertEqual(r['omitidos'],1)
        self.assertTrue(self.cat.leer()[0]['ruta_procesada'])

    def test_carpeta_temporal_se_reconstruye(self):
        with patch.object(lote.os,'rename',side_effect=OSError('corte simulado')):
            with self.assertRaises(OSError):self.ejecutar()
        r=self.ejecutar()
        self.assertEqual(r['nuevos'],1)
        self.assertEqual(len(self.cat.verificar()),1)

    def test_procesado_alterado_no_se_sobrescribe(self):
        self.ejecutar();p=self.cat.ruta(self.cat.leer()[0]['ruta_procesada'])
        p.write_bytes(b'modificado')
        with self.assertRaises(RuntimeError):self.ejecutar()
        self.assertEqual(p.read_bytes(),b'modificado')

    def test_revision_manual_no_asigna_particion(self):
        id_=self.cat.leer()[0]['muestra_id']
        self.ejecutar(revisiones={id_:dict(decision='conservar',motivo='Escucha del autor')})
        self.assertEqual(self.cat.leer()[0]['particion'],'sin_asignar')


if __name__=='__main__':
    unittest.main()
