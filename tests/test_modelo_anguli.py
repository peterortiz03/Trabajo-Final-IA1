"""Contrato de carga e inferencia real del paquete experimental; sin micrófono."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest

RAIZ=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(RAIZ/'src'))
from interfaz_servicios import cargar_huellas,leer_json,evaluar_huella,abrir_imagen

PAQUETE=RAIZ/'documentos/evidencias/08_huellas_combinadas'


class ModeloAnguli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=leer_json(RAIZ/'config/aplicacion.json')
        cls.s=cargar_huellas(cls.cfg['huellas'])

    def test_configuracion_conserva_audio_y_normalizacion(self):
        base=leer_json(RAIZ/'config/aplicacion_respaldo.json')
        self.assertEqual(self.cfg['audio'],base['audio'])
        for k in base['huellas'].keys()-{'modelo','seleccion'}:
            self.assertEqual(self.cfg['huellas'][k],base['huellas'][k])

    def test_inferencia_real_autorizada_e_intrusa_anteriores(self):
        import csv
        with (RAIZ/'datos/metadatos_con_rotaciones_train_v1.csv').open(encoding='utf-8-sig') as f:
            filas={r['muestra']:r for r in csv.DictReader(f) if r['particion']=='validacion'}
        a=evaluar_huella(abrir_imagen(RAIZ/filas['A01_M21']['original']),self.s)
        i=evaluar_huella(abrir_imagen(RAIZ/filas['I01_M01']['original']),self.s)
        self.assertTrue(a['aceptada']);self.assertEqual(a['identidad'],'A01')
        self.assertFalse(i['aceptada']);self.assertEqual(i['identidad'],'')

    def test_no_se_usaron_controles_o_intrusos_en_centroides(self):
        import csv
        with (PAQUETE/'catalogo_desarrollo.csv').open(encoding='utf-8-sig') as f:
            filas=list(csv.DictReader(f))
        train=[r for r in filas if r['particion']=='entrenamiento']
        self.assertEqual(len(train),180)
        self.assertTrue(all(r['grupo']=='autorizado' for r in train))
        self.assertTrue(all(int(r['muestra'].rsplit('_',1)[1])<=25 for r in filas if r['fuente']=='anguli'))
        self.assertEqual(len(set(r['muestra'] for r in filas)),295)

    def test_modelo_alterado_se_bloquea(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta=Path(tmp)/'modelo';shutil.copytree(PAQUETE/'modelo',carpeta)
            p=carpeta/'modelo_congelado.npz';p.write_bytes(p.read_bytes()+b'ALTERADO')
            cfg=dict(self.cfg['huellas'],modelo=str(carpeta))
            with self.assertRaisesRegex(ValueError,'Calibración modificada'):
                cargar_huellas(cfg)


if __name__=='__main__':
    unittest.main()
