"""Contratos del preparador: equivalencia, reproducción y guardado explícito."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('MPLBACKEND','Agg')
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(RAIZ/'src'))
import numpy as np
from PIL import Image
from preparar_captura import (cargar_preparador,abrir_base,preparar_captura,guardar_consulta,
                             validar_semilla,huella_pixeles,leer_json)


class Preparador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=cargar_preparador()
        cls.base=abrir_base(RAIZ/'datos/bases/piloto_01/Fingerprints/fp_1/1.png')

    def test_equivalencia_con_generador_y_repetibilidad_sin_mutar_base(self):
        from generar_conjunto import producir
        antes=huella_pixeles(self.base)
        for perfil in self.p['generador']['perfiles']:
            with self.subTest(perfil=perfil['nombre']):
                im,r=preparar_captura(self.base,perfil['nombre'],2026102301,self.p)
                otra,r2=preparar_captura(self.base,perfil['nombre'],2026102301,self.p)
                original,_,params=producir(np.array(self.base),dict(perfil=perfil,semilla=2026102301),self.p['generador'])
                np.testing.assert_array_equal(np.array(im),original)
                np.testing.assert_array_equal(np.array(im),np.array(otra))
                self.assertEqual(r,r2)
                self.assertEqual(r['parametros'],params)
                self.assertFalse(r['normalizada'])
                self.assertFalse(r['incorporada_entrenamiento'])
                self.assertNotIn('identidades',r['configuracion_generador'])
                self.assertNotIn('identidad',r)
                self.assertNotIn('aceptada',r)
        self.assertEqual(huella_pixeles(self.base),antes)

    def test_validacion_entradas_sin_reescalar(self):
        for valor in ('-1','1.2','abc','4294967296',True):
            with self.subTest(valor=valor),self.assertRaisesRegex(ValueError,'Semilla'):
                validar_semilla(valor)
        for im in (Image.new('L',(512,512)),Image.new('RGB',(275,400))):
            with self.assertRaisesRegex(ValueError,'275'):
                preparar_captura(im,'local_leve',123,self.p)
        with self.assertRaisesRegex(ValueError,'Perfil'):
            preparar_captura(self.base,'inventado',123,self.p)

    def test_sorteo_solo_utiliza_perfiles_existentes_y_semilla_nueva(self):
        from preparar_captura import elegir_parametros_aleatorios
        with patch('preparar_captura.secrets.choice',return_value='movimiento') as elegir, \
             patch('preparar_captura.secrets.randbelow',return_value=123) as sortear:
            self.assertEqual(elegir_parametros_aleatorios(self.p,123),('movimiento',124))
            elegir.assert_called_once_with([p['nombre'] for p in self.p['generador']['perfiles']])
            sortear.assert_called_once_with(2**32-1)

    def test_captura_sorteada_se_reproduce_con_parametros_registrados(self):
        from preparar_captura import elegir_parametros_aleatorios
        perfil,semilla=elegir_parametros_aleatorios(self.p)
        imagen,r=preparar_captura(self.base,perfil,semilla,self.p)
        reproducida,_=preparar_captura(self.base,r['perfil'],r['semilla_captura'],self.p)
        np.testing.assert_array_equal(np.array(imagen),np.array(reproducida))

    def test_guardado_reproducible_sin_sobrescribir_ni_escribir_dataset(self):
        im,r=preparar_captura(self.base,'local_leve',2026102301,self.p)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'consulta'
            guardar_consulta(im,self.base,r,out)
            self.assertEqual({p.name for p in out.iterdir()},{'base.png','captura.png','receta.json'})
            guardada=leer_json(out/'receta.json')
            self.assertEqual(guardada['captura']['sha256_pixeles'],huella_pixeles(abrir_base(out/'captura.png')))
            reproducida,_=preparar_captura(abrir_base(out/'base.png'),guardada['perfil'],guardada['semilla_captura'],self.p)
            np.testing.assert_array_equal(np.array(reproducida),np.array(im))
            with self.assertRaisesRegex(ValueError,'sobrescriben'):
                guardar_consulta(im,self.base,r,out)
            with self.assertRaisesRegex(ValueError,'no dentro'):
                guardar_consulta(im,self.base,r,RAIZ/'datos'/'consulta_control_no_crear')
            alterada=im.copy();alterada.putpixel((0,0),0)
            with self.assertRaisesRegex(ValueError,'receta'):
                guardar_consulta(alterada,self.base,r,Path(tmp)/'inconsistente')
            self.assertEqual(len(list(Path(tmp).iterdir())),1)

    def test_consulta_en_memoria_o_guardada_da_misma_inferencia_real(self):
        from interfaz_servicios import cargar_huellas,evaluar_huella
        sistema=cargar_huellas(leer_json(RAIZ/'config/interfaz_v1.json')['huellas'])
        cfg=leer_json(RAIZ/'config/conjunto_v1.json')
        for i in cfg['identidades']:
            if i['grupo']!='autorizado' and i['particion']!='validacion':
                continue
            with self.subTest(base=i['id']):
                base=abrir_base(RAIZ/i['base'])
                im,r=preparar_captura(base,'local_leve',2026102301,self.p)
                real=evaluar_huella(im,sistema)
                with tempfile.TemporaryDirectory() as tmp:
                    out=Path(tmp)/'consulta'
                    guardar_consulta(im,base,r,out)
                    self.assertEqual(real,evaluar_huella(abrir_base(out/'captura.png'),sistema))
                if i['grupo']=='autorizado':
                    self.assertTrue(real['aceptada'])
                    self.assertEqual(real['identidad'],i['id'])
                else:
                    self.assertFalse(real['aceptada'])
                    self.assertEqual(real['identidad'],'')


if __name__=='__main__':
    unittest.main()
