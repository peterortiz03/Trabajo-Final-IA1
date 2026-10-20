"""Controles numéricos, temporales y de trazabilidad; no son pruebas de K-NN."""
import contextlib
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from caracteristicas_audio import (AudioNoVectorizable, cargar_config, banco_mel, calcular_locales,
    limites_desde_detalle, extraer_audio, nombres_caracteristicas, resumir_segmentos)
from extraer_dataset_audio import ejecutar


def senal():
    fs=16000; x=np.zeros(12800,dtype=float); a,b=2400,10400
    t=np.arange(b-a)/fs
    x[a:b]=(.4+.1*np.sin(2*np.pi*3*t))*np.sin(2*np.pi*(240*t+300*t*t))
    return x,fs,(a,b)


class Numeros(unittest.TestCase):
    def setUp(self): self.c=cargar_config()

    def test_dimension_nombres_y_repeticion(self):
        v,d=extraer_audio(*senal(),self.c)
        u,_=extraer_audio(*senal(),self.c)
        self.assertEqual(v.shape,(160,));self.assertTrue(np.isfinite(v).all())
        np.testing.assert_array_equal(v,u)
        self.assertEqual(d['ventanas_por_segmento'],[5]*10)
        names=nombres_caracteristicas(self.c)
        self.assertEqual(names[0],'s01_zcr_media');self.assertEqual(names[-1],'s10_mfcc_c5_std')
        self.assertEqual(len(set(names)),160)

    def test_mfcc_con_formula_dct_independiente(self):
        rng=np.random.default_rng(9);w=rng.normal(0,.2,(2,400))
        local=calcular_locales(w,self.c)
        ventana=.5-.5*np.cos(2*np.pi*np.arange(400)/400)
        potencia=np.abs(np.fft.rfft(w*ventana,n=512,axis=1))**2/512
        B,_,_=banco_mel(self.c)
        log=np.log(np.maximum(potencia@B.T,1e-12))
        j=np.arange(26)
        esperado=np.column_stack([np.sqrt(2/26)*np.sum(log*np.cos(np.pi*k*(2*j+1)/(2*26)),axis=1)
                                  for k in [1,2,4,5]])
        np.testing.assert_allclose(local['mfcc'],esperado,atol=1e-12,rtol=1e-12)

    def test_zcr_y_amplitud_con_solucion_manual(self):
        w=np.array([[-.5,.5,-.5,.5]*100,[.2]*400])
        r=calcular_locales(w,self.c)
        np.testing.assert_allclose(r['zcr'],[1,0])
        np.testing.assert_allclose(r['amplitud_media'],[.5,.2])
        np.testing.assert_allclose(r['amplitud_max'],[.5,.2])

    def test_resumen_y_std_poblacional(self):
        c=dict(self.c,segmentos=2,indices_mfcc=[1])
        local=dict(zcr=np.array([0.,1.,.5]),amplitud_media=np.array([.2,.4,.1]),
                   amplitud_max=np.array([.3,.8,.5]),mfcc=np.array([[2.],[4.],[9.]]))
        v,counts=resumir_segmentos(local,np.array([0,0,1]),c)
        np.testing.assert_allclose(v,[.5,1,.3,.8,3,4,1,.5,.5,.1,.5,9,9,0])
        self.assertEqual(counts,[2,1])

    def test_limites_temporales(self):
        a,b=limites_desde_detalle(dict(inicio_actividad_s=.75,fin_actividad_s=1.44,recorte_inicio_s=.6),16000,15840)
        self.assertEqual((a,b),(2400,13440))
        with self.assertRaises(AudioNoVectorizable):limites_desde_detalle({},16000,1000)

    def test_margenes_no_cambian_vector_si_contexto_igual(self):
        x,fs,(a,b)=senal()
        v,_=extraer_audio(x,fs,(a,b),self.c)
        x2=np.pad(x,(1600,1600))
        u,_=extraer_audio(x2,fs,(a+1600,b+1600),self.c)
        np.testing.assert_array_equal(v,u)

    def test_silencio_corto_estereo_y_no_finitos(self):
        x,fs,lims=senal()
        casos=[(np.zeros_like(x),fs,lims),(np.ones_like(x)*.2,fs,lims),
               (x,8000,lims),(np.column_stack([x,x]),fs,lims),
               (np.full_like(x,np.nan),fs,lims),(x,fs,(0,999999)),
               (x,fs,(2400,2800))]
        for xx,ff,ll in casos:
            with self.subTest(shape=xx.shape,fs=ff,limites=ll):
                with self.assertRaises(AudioNoVectorizable):extraer_audio(xx,ff,ll,self.c)

    def test_contexto_ausente_se_informa(self):
        x,fs,(a,b)=senal();v,d=extraer_audio(x[a:b],fs,(0,b-a),self.c)
        self.assertTrue(np.isfinite(v).all())
        self.assertIn('contexto_fuera_del_wav_completado_con_ceros',d['avisos'])

    def test_dimension_configurable_y_banco(self):
        c=dict(self.c,segmentos=5,indices_mfcc=[1,2])
        self.assertEqual(extraer_audio(*senal(),c)[0].size,5*(4+6))
        B,f,n=banco_mel(c)
        self.assertEqual(B.shape,(26,257));self.assertTrue((B>=0).all())
        self.assertTrue((B.sum(axis=1)>0).all());self.assertAlmostEqual(n[0],0)
        self.assertAlmostEqual(n[-1],8000);self.assertEqual(f[-1],8000)

    def test_una_ventana_y_silencios_internos_se_informan(self):
        fs=16000;t=np.arange(1600)/fs;x=.4*np.sin(2*np.pi*400*t)
        v,d=extraer_audio(np.pad(x,(300,300)),fs,(300,1900),self.c)
        self.assertEqual(d['ventanas_por_segmento'],[1]*10)
        self.assertIn('segmento_con_una_ventana:1',d['avisos'])
        np.testing.assert_array_equal(v.reshape(10,16)[:,6::3],0)
        x,fs,lims=senal();x[5000:7500]=0
        v,d=extraer_audio(x,fs,lims,self.c)
        self.assertTrue(np.isfinite(v).all())
        self.assertTrue(any(a.startswith('segmento_casi_silencioso') for a in d['avisos']))


class Lotes(unittest.TestCase):
    def preparar(self,raiz):
        base=raiz/'datos/audio/procesados/prueba_v1';base.mkdir(parents=True)
        (raiz/'config').mkdir()
        (raiz/'config/caracteristicas_audio_v1.json').write_text(json.dumps(cargar_config()))
        actual=dict(version='prueba_v1',ruta_catalogo=(base/'catalogo_procesado.csv').relative_to(raiz).as_posix())
        (base.parent/'actual.json').write_text(json.dumps(actual))
        (base/'procedimiento.json').write_text(json.dumps(dict(firma_procedimiento='firma-test')))
        revisiones={'M2':dict(decision='conservar',motivo='revisada'),
                    'M3':dict(decision='excluir',motivo='palabra incompleta')}
        for p in [base/'revisiones_aplicadas.json',raiz/'config/revisiones_audio_v1.json']:
            p.write_text(json.dumps(revisiones))
        x,fs,(a,b)=senal();filas=[]
        for i in range(1,5):
            id_=f'M{i}';p=base/(id_+'.wav');dpath=base/(id_+'.json')
            if i!=3: # Excluido sin archivo: el extractor debe respetar la exclusión sin abrirlo.
                with wave.open(str(p),'wb') as w:
                    w.setnchannels(1);w.setsampwidth(2);w.setframerate(fs)
                    w.writeframes(np.rint(x*32768).astype('<i2').tobytes())
            digest=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else 'no-abrir'
            rev=revisiones.get(id_,{})
            r=dict(muestra_id=id_,hablante='H001',comando='reconocer',particion='sin_asignar',
                   version_procesamiento='prueba_v1',firma_procedimiento='firma-test',sha256_original='original',
                   sha256_procesado=digest,ruta_procesada=p.relative_to(raiz).as_posix(),ruta_detalle=dpath.relative_to(raiz).as_posix(),
                   estado_procesamiento='procesado',decision_revision=rev.get('decision','pendiente'),
                   motivo_revision=rev.get('motivo',''),avisos_preprocesamiento='',avisos_calidad='')
            resultado={k:r[k] for k in ['muestra_id','sha256_original','sha256_procesado','firma_procedimiento','ruta_procesada']}
            resultado['detalle']=dict(estado='procesado',avisos=[],frecuencia_procesada_hz=fs,canales_procesados=1,
                cuadros_procesados=len(x),inicio_actividad_s=a/fs,fin_actividad_s=b/fs,recorte_inicio_s=0)
            dpath.write_text(json.dumps(resultado))
            filas.append(r)
        filas[-1]['sha256_procesado']='hash-incorrecto'
        self.escribir(base,filas)
        return base,filas

    @staticmethod
    def escribir(base,filas):
        with (base/'catalogo_procesado.csv').open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(filas[0]));w.writeheader();w.writerows(filas)

    def test_decisiones_fallos_repeticion_y_filas(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root=Path(tmp);base,filas=self.preparar(root)
            a,fallos=ejecutar(root,verificar_repetibilidad=True)
            b,_=ejecutar(root)
            self.assertNotEqual(a,b);self.assertEqual(fallos,1)
            with np.load(a/'vectores.npz') as x,np.load(b/'vectores.npz') as y:
                np.testing.assert_array_equal(x['X'],y['X'])
                self.assertEqual(x['muestras'].tolist(),['M1','M2']);self.assertEqual(x['X'].shape,(2,160))
            with (a/'catalogo_caracteristicas.csv').open(encoding='utf-8-sig') as f:r=list(csv.DictReader(f))
            self.assertEqual(r[0]['revision_aprobada'],'False');self.assertEqual(r[1]['revision_aprobada'],'True')
            self.assertEqual(r[2]['estado_extraccion'],'excluida_revision');self.assertEqual(r[2]['fila_vector'],'')
            self.assertEqual(r[3]['estado_extraccion'],'error_entrada')
            self.assertEqual(r[1]['estado_para_modelado'],'pendiente:particion')

    def test_revision_desactualizada_y_ids_duplicados(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root=Path(tmp);base,filas=self.preparar(root)
            path=root/'config/revisiones_audio_v1.json';antes=path.read_text();path.write_text('{}')
            with self.assertRaises(ValueError):ejecutar(root)
            path.write_text(antes);filas.append(filas[0]);self.escribir(base,filas)
            with self.assertRaises(ValueError):ejecutar(root)

    def test_prueba_diferida_y_hablantes_no_mezclados(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root=Path(tmp);base,filas=self.preparar(root)
            for r in filas:r['particion']='prueba'
            self.escribir(base,filas)
            a,fallos=ejecutar(root);self.assertEqual(fallos,0)
            with np.load(a/'vectores.npz') as x:self.assertEqual(x['X'].shape,(0,160))
            filas[0]['particion']='entrenamiento';self.escribir(base,filas)
            with self.assertRaises(ValueError):ejecutar(root)


if __name__=='__main__':unittest.main()
