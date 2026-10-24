"""Recorrido gráfico del preparador con generador y huellas reales, sin audio."""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('MPLBACKEND','Agg')
RAIZ=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(RAIZ/'src'))


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requiere escritorio o DISPLAY virtual')
class PreparadorVentana(unittest.TestCase):
    def test_preparar_usar_guardar_cancelar_e_invalidar(self):
        import tkinter as tk
        from interfaz import Aplicacion
        from interfaz_estado import EstadoHuella as E
        r=tk.Tk();a=Aplicacion(r,RAIZ/'config/aplicacion_respaldo.json')
        errores=[]
        r.report_callback_exception=lambda *args:errores.append(args)
        def esperar():
            limite=time.monotonic()+20
            while a.sesion.operacion:
                r.update();self.assertLess(time.monotonic(),limite);time.sleep(.01)
            r.update()
        try:
            esperar()
            self.assertIsNotNone(a.servicios.preparador)
            self.assertFalse(a.preparacion_visible.get())
            original=RAIZ/'datos/originales/conjunto_v1/validacion/A01/A01_M21.png'
            with patch('interfaz.filedialog.askopenfilename',return_value=str(original)):
                a.seleccionar()
            esperar();a.ejecutar('reconocer','manual');esperar();a.ejecutar('identificar','manual')
            antes=vars(a.sesion).copy()
            a.preparacion_visible.set(True);a._desplegar();r.update()
            base=RAIZ/'datos/bases/piloto_01/Fingerprints/fp_1/1.png'
            with patch('interfaz.filedialog.askopenfilename',return_value=str(base)):
                a.seleccionar_base()
            esperar()
            self.assertEqual(a.sesion.estado,E.AUTORIZADA)
            self.assertEqual(a.sesion.identidad_visible,'A01')
            self.assertEqual(a.sesion.revision,antes['revision'])
            a.parametros_manuales.set(True);a._cambiar_modo_captura()
            a.semilla_preparacion.set('abc');a.generar_captura()
            self.assertFalse(a.sesion.operacion)
            self.assertIn('Semilla',a.preparacion_mensaje.get())
            a.semilla_preparacion.set('2026102301');a.generar_captura()
            secuencia=a.sesion.secuencia;a.generar_captura()
            self.assertEqual(a.sesion.secuencia,secuencia)
            self.assertEqual(str(a.base_boton.cget('state')),'disabled')
            esperar()
            self.assertIsNotNone(a.receta_preparada)
            self.assertEqual(a.captura_preparada.size,(275,400))
            # Preparar no cambió la autorización de la consulta todavía activa.
            self.assertEqual(a.sesion.identidad_visible,'A01')
            from preparar_captura import huella_pixeles
            hash_antes=huella_pixeles(a.captura_preparada)
            with patch('interfaz.filedialog.askopenfilename',return_value=''):
                a.seleccionar_base()
            self.assertEqual(huella_pixeles(a.captura_preparada),hash_antes)
            with tempfile.TemporaryDirectory() as tmp:
                with patch('interfaz.filedialog.askdirectory',return_value=''):
                    a.guardar_captura()
                self.assertEqual(list(Path(tmp).iterdir()),[])
                with patch('interfaz.filedialog.askdirectory',return_value=tmp):
                    a.guardar_captura()
                esperar()
                carpeta=next(Path(tmp).iterdir())
                self.assertTrue((carpeta/'receta.json').is_file())
                a.usar_captura();r.update()
                self.assertEqual(a.sesion.estado,E.PENDIENTE)
                self.assertEqual(a.sesion.identidad_visible,'')
                self.assertIsNone(a.sesion.resultado)
                self.assertFalse(a.preparacion_visible.get())
                self.assertIsNotNone(a.receta_entrada)
                a.ejecutar('reconocer','manual');esperar()
                memoria=a.sesion.resultado.copy()
                self.assertTrue(memoria['aceptada'])
                a.ejecutar('identificar','manual');self.assertEqual(a.sesion.identidad_visible,'A01')
                # Cambiar la semilla invalida solo el borrador del preparador.
                a.semilla_preparacion.set('2026102302')
                self.assertIsNone(a.captura_preparada)
                self.assertEqual(a.sesion.identidad_visible,'A01')
                self.assertTrue(a.usar_boton.instate(['disabled']))
                with patch('interfaz.filedialog.askopenfilename',return_value=str(carpeta/'captura.png')):
                    a.seleccionar()
                esperar();self.assertIsNone(a.receta_entrada)
                a.ejecutar('reconocer','manual');esperar()
                self.assertEqual(a.sesion.resultado,memoria)
            a.preparacion_visible.set(True);a._desplegar();r.geometry('720x700');r.update()
            self.assertTrue(a._apilado)
            self.assertTrue(a.preparacion_panel.winfo_ismapped())
        finally:
            a._destruir()
        self.assertEqual(errores,[])

    def test_seleccion_genera_automaticamente_y_avanzadas_no_regenera(self):
        import tkinter as tk
        from interfaz import Aplicacion
        from preparar_captura import preparar_captura,huella_pixeles
        r=tk.Tk();a=Aplicacion(r,RAIZ/'config/aplicacion_respaldo.json')
        errores=[];r.report_callback_exception=lambda *args:errores.append(args)
        def esperar():
            limite=time.monotonic()+20
            while a.sesion.operacion:
                r.update();self.assertLess(time.monotonic(),limite);time.sleep(.01)
            r.update()
        try:
            esperar()
            self.assertFalse(a.avanzadas_preparacion.get())
            self.assertFalse(a.parametros_manuales.get())
            base=RAIZ/'datos/bases/piloto_01/Fingerprints/fp_1/1.png'
            # Sorteo controlado SOLO en este test; generador e imágenes reales.
            with patch('preparar_captura.elegir_parametros_aleatorios',
                       side_effect=[('local_leve',2026102301),('movimiento',2026102302)]) as elegir:
                with patch('interfaz.filedialog.askopenfilename',return_value=str(base)):
                    a.seleccionar_base()
                esperar()
                self.assertEqual(elegir.call_count,1)
                self.assertEqual(a.receta_preparada['eleccion_parametros'],'automatica')
                self.assertIsNone(a.sesion.resultado)
                self.assertIsNone(a.imagen)
                anterior=huella_pixeles(a.captura_preparada)
                a.generar_captura();esperar()
                self.assertEqual(elegir.call_count,2)
                self.assertEqual(a.receta_preparada['semilla_captura'],2026102302)
                self.assertNotEqual(huella_pixeles(a.captura_preparada),anterior)
                a.avanzadas_preparacion.set(True);a._mostrar_avanzadas();r.update()
                self.assertTrue(a.avanzadas_panel.winfo_manager()=='pack')
                self.assertTrue(a.semilla_entrada.instate(['disabled']))
                self.assertEqual(elegir.call_count,2)
                with patch('interfaz.filedialog.askopenfilename',return_value=''):
                    a.seleccionar_base()
                self.assertEqual(elegir.call_count,2)
                a.parametros_manuales.set(True);a._cambiar_modo_captura()
                self.assertTrue(a.semilla_entrada.instate(['!disabled']))
                esperado=huella_pixeles(a.captura_preparada)
                a.generar_captura();esperar()
                self.assertEqual(elegir.call_count,2)
                self.assertEqual(a.receta_preparada['eleccion_parametros'],'manual')
                self.assertEqual(huella_pixeles(a.captura_preparada),esperado)
            a.usar_captura()
            self.assertEqual(a.receta_entrada['eleccion_parametros'],'manual')
            self.assertIsNone(a.sesion.resultado)
        finally:a._destruir()
        self.assertEqual(errores,[])


if __name__=='__main__':
    unittest.main()
