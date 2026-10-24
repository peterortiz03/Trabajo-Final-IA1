"""Recorrido de ventana real; requiere pantalla o DISPLAY virtual.

La selección del diálogo se controla para que la prueba sea reproducible.
No se usa micrófono real. La segunda prueba SIMULA solo la coordinación de voz.
"""
import csv
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('MPLBACKEND', 'Agg')
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ/'src'))
from interfaz_estado import EstadoHuella as E


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Requiere escritorio o DISPLAY virtual')
class Ventana(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from interfaz import Aplicacion
        self.r = tk.Tk()
        self.errores_tk = []
        self.r.report_callback_exception = lambda *args: self.errores_tk.append(args)
        self.a = Aplicacion(self.r, RAIZ/'config/aplicacion_respaldo.json')
        self.esperar()
        with (RAIZ/'datos/metadatos_con_rotaciones_train_v1.csv').open(encoding='utf-8-sig') as f:
            self.filas = {r['muestra']:r for r in csv.DictReader(f) if r['particion'] != 'prueba'}

    def tearDown(self):
        try:
            self.a._destruir()
        except Exception:
            pass
        self.assertEqual(self.errores_tk, [])

    def esperar(self):
        limite = time.monotonic()+20
        while self.a.sesion.operacion:
            self.r.update()
            self.assertLess(time.monotonic(), limite, 'Operación no terminada')
            time.sleep(.01)
        self.r.update()

    def seleccionar(self, ruta):
        with patch('interfaz.filedialog.askopenfilename', return_value=str(ruta) if ruta else ''):
            self.a.seleccionar()
        self.esperar()

    def boton_dialogo(self, nombre):
        def buscar(w):
            for hijo in w.winfo_children():
                if hasattr(hijo, 'invoke') and hijo.cget('text') == nombre:
                    return hijo
                encontrado = buscar(hijo)
                if encontrado is not None:
                    return encontrado
        return buscar(self.a.dialogo)

    def test_recorrido_manual_real_y_cancelacion_sin_perder_sesion(self):
        a = self.a
        self.assertIsNotNone(a.servicios.huellas)
        self.assertFalse(a.manual_visible.get())
        a.ejecutar('reconocer', 'manual')
        self.assertIn('Seleccioná', a.aviso.get())
        a.ejecutar('identificar', 'manual')
        self.assertIn('Primero reconocé', a.aviso.get())
        self.seleccionar(RAIZ/self.filas['A01_M21']['original'])
        self.assertIsNotNone(a.foto)
        self.assertEqual(a.imagen.size, (275,400))
        a.ejecutar('reconocer', 'manual')
        self.assertEqual(str(a.seleccionar_boton.cget('state')), 'disabled')
        a.ejecutar('reconocer', 'manual')  # El coordinador también bloquea llamadas directas.
        self.esperar()
        self.assertEqual(a.sesion.estado, E.AUTORIZADA)
        self.assertEqual(a.sesion.identidad_visible, '')
        a.ejecutar('identificar', 'manual')
        self.assertEqual(a.sesion.identidad_visible, 'A01')
        self.assertIn('manual', a.origen_label.cget('text'))
        antes = vars(a.sesion).copy()
        self.seleccionar(None)
        self.assertEqual(vars(a.sesion), antes)
        for origen in ('manual', 'voz', 'ventana'):
            # Invoca el mismo punto de confirmación; no simula un acierto acústico.
            a.confirmar_salida(origen)
            self.r.update()
            self.boton_dialogo('Cancelar').invoke()
            self.r.update()
            self.assertEqual(vars(a.sesion), antes)
        self.seleccionar(RAIZ/self.filas['I01_M01']['original'])
        self.assertIsNone(a.sesion.resultado)
        self.assertEqual(a.sesion.identidad_visible, '')
        a.ejecutar('reconocer', 'manual'); self.esperar()
        self.assertEqual(a.sesion.estado, E.RECHAZADA)
        a.ejecutar('identificar', 'manual')
        self.assertEqual(a.sesion.identidad_visible, '')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'no_imagen.png';p.write_text('no es una imagen')
            self.seleccionar(p)
        self.assertEqual(a.sesion.estado, E.ERROR)
        self.assertEqual(a.resultado_titulo.cget('text'), 'No se pudo evaluar')
        self.r.geometry('720x700');self.r.update()
        self.assertTrue(a._apilado)
        self.assertTrue(a.botones_manuales[0].instate(['!disabled']))
        a.confirmar_salida('manual');self.r.update()
        self.boton_dialogo('Cerrar').invoke()
        self.assertTrue(a.sesion.cerrada)

    def test_voz_simulada_solo_coordinacion_y_captura_invalida(self):
        a = self.a
        # Doble explícito: NO es un modelo acústico ni una prueba de precisión.
        a.servicios.voz = dict(modelo=dict(nombres=list(range(160))), carpeta=Path('SIMULACION'),
                              resumen=dict(parametros=dict(k=1,votos='uniform')))
        a.servicios.cfg_captura = dict(cuenta_regresiva_s=0)
        a.formato = (0,16000,1,'SIMULADO','SIMULADA')
        silencio=dict(prediccion=None, avisos=['sin_actividad_suficiente_segun_energia'],
                      detalle=dict(estado='sin_salida_revisar'))
        with patch.object(a.servicios, 'escuchar', return_value=silencio) as escuchar:
            a.hablar();token=a.sesion.secuencia;a.hablar()
            self.assertEqual(a.sesion.secuencia,token)
            self.esperar()
            escuchar.assert_called_once()
        self.assertIn('No se detectó voz útil',a.aviso.get())
        self.assertEqual(a.sesion.estado,E.SIN_IMAGEN)
        prediccion=dict(prediccion='salir',avisos=[])
        with patch.object(a.servicios, 'escuchar', return_value=prediccion):
            a.hablar();self.esperar()
        self.assertIsNotNone(a.dialogo)
        texto=' '.join(str(w.cget('text')) for w in a.dialogo.winfo_children() if w.winfo_class()=='Label')
        self.assertIn('Se interpretó el comando Salir',texto)
        self.boton_dialogo('Cancelar').invoke()
        self.assertFalse(a.sesion.cerrada)
        # Cierre durante una operación: el doble espera la cancelación, sin Tk.
        from threading import Event
        empezo = Event()
        def captura_en_curso(formato, al_iniciar, al_procesar, cancelar):
            empezo.set()
            cancelar.wait(2)
            return prediccion
        with patch.object(a.servicios, 'escuchar', side_effect=captura_en_curso):
            a.hablar()
            self.assertTrue(empezo.wait(1))
            a.confirmar_salida('ventana');self.r.update()
            self.boton_dialogo('Cerrar').invoke()
            a.trabajador.join(.5)
            self.r.update()
        self.assertTrue(a.sesion.cerrada)
        self.assertTrue(a.cancelar.is_set())
        self.assertFalse(a.trabajador.is_alive())


if __name__ == '__main__':
    unittest.main()
