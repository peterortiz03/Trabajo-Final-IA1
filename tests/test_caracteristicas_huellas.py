"""Pruebas del contrato numérico y de trazabilidad; no miden reconocimiento."""
import contextlib
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from caracteristicas_huellas import (cargar_config, contar_pares, extraer_huella,
    HuellaNoVectorizable, medidas_glcm, nombres_caracteristicas, preparar_huella)
from extraer_dataset_huellas import ejecutar


def ejemplo(h=91, w=85):
    y, x = np.mgrid[:h, :w]
    # Textura asimétrica y ROI no rectangular: pruebas de invariancia no triviales.
    im = np.clip(125 + 90*np.cos(.8*x + .012*y*y) + 25*np.sin(.3*y), 0, 255).astype(np.uint8)
    m = ((x - (w-1)/2)**2/((w-8)/2)**2 + (y - (h-1)/2)**2/((h-8)/2)**2 < 1)
    m[20:25, 20:30] = False
    return im, m


class Descriptor(unittest.TestCase):
    def setUp(self):
        self.cfg = cargar_config()

    def test_dimension_orden_y_determinismo(self):
        im, m = ejemplo()
        v, _ = extraer_huella(im, m, self.cfg)
        w, _ = extraer_huella(im, m, self.cfg)
        self.assertEqual(v.shape, (144,))
        self.assertTrue(np.isfinite(v).all())
        np.testing.assert_array_equal(v, w)
        names = nombres_caracteristicas(self.cfg)
        self.assertEqual(names[0], "global_d1_a0_contraste")
        self.assertEqual(names[-1], "NE_SO_d5_a135_correlacion")
        self.assertEqual(len(set(names)), len(names))

    def test_giro_180_tamanos_pares_e_impares(self):
        for h, w in [(90, 84), (91, 85), (90, 85), (91, 84)]:
            with self.subTest(shape=(h, w)):
                im, m = ejemplo(h, w)
                v, _ = extraer_huella(im, m, self.cfg)
                u, _ = extraer_huella(np.rot90(im, 2), np.rot90(m, 2), self.cfg)
                np.testing.assert_array_equal(v, u)

    def test_fondo_no_influye(self):
        im, m = ejemplo()
        otro = im.copy()
        otro[~m] = np.random.default_rng(21).integers(0, 256, (~m).sum(), dtype=np.uint8)
        np.testing.assert_array_equal(extraer_huella(im, m, self.cfg)[0],
                                      extraer_huella(otro, m, self.cfg)[0])

    def test_conteos_con_oraculo_independiente(self):
        q = np.array([[0, 1, 2, 0], [2, 2, 1, 0], [0, 2, 0, 1]])
        m = np.array([[1, 1, 0, 1], [1, 0, 1, 1], [1, 1, 1, 1]], dtype=bool)
        for dy, dx in [(0, 1), (1, 0), (1, -1), (-1, -2), (8, 0)]:
            esperado = np.zeros((3, 3), dtype=int)
            for y in range(q.shape[0]):
                for x in range(q.shape[1]):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < q.shape[0] and 0 <= xx < q.shape[1] and m[y, x] and m[yy, xx]:
                        esperado[q[y, x], q[yy, xx]] += 1
            C, n = contar_pares(q, m, dy, dx, 3)
            np.testing.assert_array_equal(C, esperado)
            self.assertEqual(n, esperado.sum())

    def test_medidas_con_solucion_manual(self):
        v, constante, P = medidas_glcm(np.array([[0, 2], [0, 0]]))
        np.testing.assert_allclose(v, [1, .5, np.sqrt(.5), -1])
        self.assertFalse(constante)
        np.testing.assert_array_equal(P, [[0, .5], [.5, 0]])
        v, constante, _ = medidas_glcm(np.array([[4, 0], [0, 0]]))
        np.testing.assert_array_equal(v, [0, 1, 1, 1])
        self.assertTrue(constante)

    def test_entradas_invalidas(self):
        im, m = ejemplo()
        for imagen, mask in [(im.astype(float), m), (im, np.zeros_like(m)),
                             (im, m[:-1]), (im, np.full(im.shape, 17)),
                             (np.full_like(im, 150), m), (im[:8, :8], m[:8, :8])]:
            with self.assertRaises(HuellaNoVectorizable):
                extraer_huella(imagen, mask, self.cfg)
        with self.assertRaises(HuellaNoVectorizable):
            extraer_huella(im, m, dict(self.cfg, min_pares_region=1000000))

    def test_cuadrante_constante_no_se_oculta(self):
        im, m = ejemplo(100, 100)
        im[:50, :50] = 0
        v, info = extraer_huella(im, m, self.cfg)
        self.assertTrue(np.isfinite(v).all())
        self.assertIn("textura_cuantizada_constante:NO", info["avisos"])

    def test_regiones_opuestas_se_intercambian(self):
        im, m = ejemplo()
        q, rs, _, _ = preparar_huella(im, m, self.cfg)
        qq, rr, _, _ = preparar_huella(np.rot90(im, 2), np.rot90(m, 2), self.cfg)
        np.testing.assert_array_equal(q, np.rot90(qq, 2))
        for a, b in [("NO", "SE"), ("NE", "SO")]:
            np.testing.assert_array_equal(rs[a], np.rot90(rr[b], 2))

    def test_config_distinta_cambia_dimension(self):
        cfg = dict(self.cfg, distancias_px=[2])
        self.assertEqual(extraer_huella(*ejemplo(), cfg)[0].size, 48)


class Lote(unittest.TestCase):
    def preparar(self, raiz):
        pre = raiz / "datos/procesados/normalizacion_final_v1"
        pre.mkdir(parents=True)
        (raiz / "config").mkdir()
        (raiz / "config/caracteristicas_huellas_glcm_v1.json").write_text(json.dumps(cargar_config()))
        im, m = ejemplo()
        filas, detalles = [], []
        for nombre, particion in [("M1", "entrenamiento"), ("M2", "validacion"), ("M3", "prueba")]:
            path = pre / (nombre + ".png")
            alt = pre / (nombre + "_180.png")
            if particion != "prueba":  # Prueba inaccesible: por defecto ni intenta leerla.
                Image.fromarray(im).save(path)
                Image.fromarray(np.rot90(im, 2)).save(alt)
                Image.fromarray(m.astype(np.uint8)*255).save(pre / (nombre + "_mascara.png"))
            filas.append(dict(muestra=nombre, identidad="A", grupo="autorizado", particion=particion,
                normalizada=path.relative_to(raiz).as_posix(), alternativa_180=alt.relative_to(raiz).as_posix(),
                sha256_normalizada=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "x",
                sha256_alternativa_180=hashlib.sha256(alt.read_bytes()).hexdigest() if alt.exists() else "x",
                estado_normalizacion="ok"))
            detalles.append(dict(muestra=nombre, version="geometrica-prueba", avisos=[]))
        (pre / "detalle.json").write_text(json.dumps(detalles))
        for n in ["config_efectiva.json", "entorno.json"]:
            (pre / n).write_text("{}")
        self.escribir(pre, filas)
        return pre, filas

    @staticmethod
    def escribir(pre, filas):
        with (pre / "catalogo_normalizado.csv").open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)

    def test_lote_repetible_trazable_y_prueba_diferida(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            raiz = Path(tmp)
            pre, filas = self.preparar(raiz)
            a, fallos = ejecutar(raiz, verificar_180=True)
            b, _ = ejecutar(raiz, verificar_180=True)
            self.assertEqual(fallos, 0)
            self.assertNotEqual(a, b)
            with np.load(a / "vectores.npz", allow_pickle=False) as x, np.load(b / "vectores.npz", allow_pickle=False) as y:
                np.testing.assert_array_equal(x["X"], y["X"])
                self.assertEqual(x["muestras"].tolist(), ["M1", "M2"])
                self.assertEqual(x["X"].shape, (2, 144))
            with (a / "catalogo_caracteristicas.csv").open(encoding="utf-8-sig") as f:
                r = list(csv.DictReader(f))
            self.assertEqual(r[-1]["estado_extraccion"], "diferida_prueba")
            self.assertEqual(r[-1]["fila_vector"], "")
            self.assertEqual(r[1]["fila_vector"], "1")
            self.assertEqual([x["particion"] for x in r], [x["particion"] for x in filas])
            # La ampliación crea otra ejecución y mantiene intactas las anteriores.
            nueva = dict(filas[0], muestra="M4")
            filas.append(nueva)
            ds = json.loads((pre / "detalle.json").read_text())
            ds.append(dict(muestra="M4", version="geometrica-prueba", avisos=[]))
            (pre / "detalle.json").write_text(json.dumps(ds))
            self.escribir(pre, filas)
            c, _ = ejecutar(raiz)
            with np.load(c / "vectores.npz") as z:
                self.assertEqual(z["X"].shape, (3, 144))
            with np.load(a / "vectores.npz") as z:
                self.assertEqual(z["X"].shape, (2, 144))

    def test_error_hash_sin_desalinear_filas_y_duplicados(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            raiz = Path(tmp)
            pre, filas = self.preparar(raiz)
            filas[0]["sha256_normalizada"] = "incorrecto"
            self.escribir(pre, filas)
            a, fallos = ejecutar(raiz)
            self.assertEqual(fallos, 1)
            with np.load(a / "vectores.npz") as z:
                self.assertEqual(z["muestras"].tolist(), ["M2"])
            with (a / "catalogo_caracteristicas.csv").open(encoding="utf-8-sig") as f:
                r = list(csv.DictReader(f))
            self.assertEqual(r[0]["estado_extraccion"], "error_entrada")
            self.assertEqual(r[1]["fila_vector"], "0")
            filas.append(filas[1])
            self.escribir(pre, filas)
            with self.assertRaises(ValueError):
                ejecutar(raiz)


if __name__ == "__main__":
    unittest.main()
