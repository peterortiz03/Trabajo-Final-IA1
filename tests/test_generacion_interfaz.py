import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

import numpy as np
RAIZ=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(RAIZ/'src'))
from generacion_muestra import bases_disponibles,generar_muestra
from preparar_captura import cargar_preparador
from interfaz_servicios import cargar_huellas,leer_json,evaluar_huella

class Generacion(unittest.TestCase):
    def test_filtros_y_reservas(self):
        esperado={'Aleatoria':{'A01','A02','A03','I01','I02'},
                  'Autorizada':{'A01','A02','A03'},'Intrusa':{'I01','I02'}}
        for tipo,ids in esperado.items():
            candidatos=bases_disponibles(tipo,RAIZ)
            self.assertEqual({r['id'] for r,_ in candidatos},ids)
            self.assertFalse(any(r.get('particion')=='prueba' for r,_ in candidatos))

    def test_tipo_invalido_no_genera(self):
        with self.assertRaises(ValueError):bases_disponibles('Prueba final',RAIZ)

    def test_generacion_real_una_vez_y_no_incorpora_datos(self):
        preparador=cargar_preparador(raiz=RAIZ)
        with patch('generacion_muestra.secrets.choice',side_effect=lambda opciones:opciones[0]), \
             patch('generacion_muestra.elegir_parametros_aleatorios',return_value=('local_leve',2026102301)), \
             patch('generacion_muestra.preparar_captura',wraps=__import__('preparar_captura').preparar_captura) as generar:
            base,imagen,receta=generar_muestra('Autorizada',preparador,RAIZ)
        generar.assert_called_once()
        self.assertEqual(imagen.size,(275,400))
        self.assertEqual(receta['origen_sorteo']['base_id'],'A01')
        self.assertFalse(receta['incorporada_entrenamiento'])
        self.assertFalse(receta['normalizada'])
        self.assertNotIn('aceptada',receta)

    def test_vista_es_normalizacion_real_sin_alterar_decision(self):
        cfg=leer_json(RAIZ/'config/aplicacion.json')
        sistema=cargar_huellas(cfg['huellas'],RAIZ)
        from PIL import Image
        from normalizacion_final import normalizar_huella
        ruta=RAIZ/'datos/originales/conjunto_v1/entrenamiento/A01/A01_M01.png'
        with Image.open(ruta) as f:imagen=f.copy()
        original=evaluar_huella(imagen,sistema)
        con_vistas=evaluar_huella(imagen,sistema,incluir_vistas=True)
        normal,_=normalizar_huella(imagen,sistema['cfg_norm'])
        np.testing.assert_array_equal(np.array(con_vistas.pop('_vista_normalizada')),normal)
        mascara=con_vistas.pop('_vista_mascara')
        self.assertEqual(mascara.size,(512,512))
        self.assertEqual(con_vistas,original)

@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requiere escritorio gráfico')
class VentanaNueva(unittest.TestCase):
    def test_generar_evaluar_limpiar_y_bloquear(self):
        import tkinter as tk
        from interfaz import Aplicacion
        from interfaz_estado import EstadoHuella
        r=tk.Tk();errores=[]
        r.report_callback_exception=lambda *args:errores.append(args)
        a=Aplicacion(r,RAIZ/'config/aplicacion.json')
        def esperar():
            limite=time.monotonic()+30
            while a.sesion.operacion:
                r.update();time.sleep(.01)
                self.assertLess(time.monotonic(),limite)
            r.update()
        try:
            esperar()
            a.tipo_muestra.set('Autorizada')
            with patch('generacion_muestra.secrets.choice',side_effect=lambda opciones:opciones[0]), \
                 patch('generacion_muestra.elegir_parametros_aleatorios',return_value=('local_leve',2026102301)):
                a.generar_muestra_automatica()
                secuencia=a.sesion.secuencia;a.generar_muestra_automatica()
                self.assertEqual(a.sesion.secuencia,secuencia)
                esperar()
            self.assertEqual(a.sesion.estado,EstadoHuella.PENDIENTE)
            self.assertIsNotNone(a.imagen)
            self.assertIsNone(a.normalizada)
            a.ejecutar('reconocer','manual');esperar()
            self.assertIsNotNone(a.normalizada)
            self.assertIsNotNone(a.foto_normal)
            a.ver_mascara.set(True);a._dibujar_normal();r.update()
            a.tipo_muestra.set('Intrusa');a.generar_muestra_automatica();esperar()
            self.assertIsNone(a.normalizada)
            self.assertIsNone(a.sesion.resultado)
            self.assertEqual(a.sesion.identidad_visible,'')
        finally:a._destruir()
        self.assertEqual(errores,[])

if __name__=='__main__':unittest.main()
