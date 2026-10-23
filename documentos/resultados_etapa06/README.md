# Evidencias publicadas de la etapa 06

Esta carpeta conserva una selección de resultados reales del autor en Windows/Python 3.14.0.
Permite revisar o ejecutar la bitácora sin acceso a las matrices locales ni cargar pickle.

| Carpeta | Ejecución original UTC | Contenido |
|---|---|---|
| `01_referencia` | 20261022T160116_346229Z | PCA de huellas/audio y K-means con 144 características |
| `02_seleccion` | 20261023T014705_319737Z | Comparación interna, selección de 72 y correspondencia mejorada |
| `03_rechazo` | 20261023T021746_872267Z | Umbral calibrado, decisiones, errores y parámetros congelados |

`procedencia.json` conserva el ZIP fuente y SHA-256 de cada archivo seleccionado.
Los resúmenes originales no se reescriben; pueden mencionar otros archivos del corte
completo que siguen locales y no se publican aquí. El notebook verifica únicamente
los archivos incluidos mediante el manifiesto de esta carpeta.

En `03_rechazo` se publican `modelo_congelado.npz`, `correspondencia_congelada.json`
y `umbral.json`, exactamente como quedaron en la ejecución Windows. No se publica
pickle ni se incluyen vectores/imágenes de prueba. La función cargar_sistema de
src/calibrar_rechazo_huellas.py permite reutilizar esos parámetros con vectores nuevos.

Son resultados de desarrollo y calibración. Se mantiene el falso rechazo A02_M22.
El 0/20 de intrusos aceptados no garantiza una FAR futura nula; se utilizaron dos bases
intrusas sintéticas. La prueba final independiente sigue pendiente.
