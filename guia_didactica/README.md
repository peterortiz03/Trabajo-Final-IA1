# Guía didáctica del Trabajo Final IA I

Tres notebooks para estudiar el proyecto de principio a fin y preparar el informe. Son material explicativo complementario: no reemplazan las bitácoras históricas ni modifican el reconocedor.

## Orden de lectura

1. **01_datos_preprocesamiento_y_caracteristicas.ipynb** — problema, bases y capturas, generación, particiones, normalización, GLCM, audio, MFCC y estudio estadístico.
2. **02_pca_kmeans_y_reconocimiento_huellas.ipynb** — escalado, PCA actualizado, K-means, selección 144/72/36, ampliación Anguli, distancia, umbral y resultados.
3. **03_knn_voz_interfaz_y_evaluacion.ipynb** — K-NN, LOSO, métricas, PCA histórico de audio, interfaz, preparador, reproducibilidad y evaluación pendiente.

Los `.html` son versiones de lectura con figuras y tablas incorporadas. Pueden abrirse en el navegador; el renderizado de fórmulas en HTML puede requerir acceso a MathJax. Los notebooks incluyen sus salidas y pueden leerse sin ejecutar. Las imágenes también están en `figuras/` para usar en el informe.

## Dónde ponerlos

Recomendación: copiar **la carpeta completa `guia_didactica/` en la raíz del repositorio**, como carpeta hermana de `notebooks/`, `src/` y `documentos/`. Así queda separada del material histórico. También puede guardarse fuera del repositorio: no depende de sus modelos o imágenes externas para reproducir sus figuras.

No copiar únicamente los `.ipynb` si se desea volver a ejecutar: conservar `datos/` y `figuras/` junto a ellos. Los HTML y los notebooks con salidas guardadas pueden leerse sin recalcular.

Para volver a ejecutar en VS Code, abrir **esta carpeta `guia_didactica` como carpeta de trabajo**, elegir el entorno Python del proyecto y ejecutar cada notebook de arriba hacia abajo. La primera celda considera que el directorio de trabajo contiene `datos/` y `figuras/`. Si se trabaja con otro directorio, editar solo `DATOS` y `FIGURAS` en esa celda para apuntar a esas dos carpetas.

Dependencias para las celdas: NumPy, pandas, Matplotlib y scikit-learn; IPython/ipykernel para ejecutarlas desde Jupyter/VS Code. No es necesario instalar ni entrenar los modelos de audio o huellas. No reemplazar los requirements del proyecto por los de esta guía. El archivo `entorno_guia.txt` registra versiones de referencia y una sugerencia de entorno aislado si se desea.

## Qué se calculó ahora

Se reconstruyeron 170 vectores anteriores de desarrollo con las funciones del proyecto y se combinaron con 125 vectores Anguli del diagnóstico original compartido por el autor. Se alinearon por identificador con el catálogo del modelo combinado. Las medias de las 36 columnas del entrenamiento reconstruido coincidieron exactamente con las guardadas.

Se ajustó **solo PCA**, con las 180 autorizadas de entrenamiento y el escalado congelado. Las 115 muestras de validación se proyectaron después. No se ajustaron selección, escalas, centroides, correspondencia ni umbral. No se abrieron imágenes del control Anguli ni de prueba final. El control aparece únicamente como resultados históricos publicados.

Resultado: PC1 62,64 %, PC2 19,32 %, PC1–PC2 81,96 %; cuatro componentes alcanzan 95 %. Los gráficos anteriores de audio se identifican como históricos. Los porcentajes nuevos de huellas pertenecen al espacio seleccionado de 36 columnas.

Se entregan 14 figuras nuevas, más imágenes de ejemplo, el PCA histórico de audio y evidencia publicada de interfaz. Los ejemplos de imagen y señal provienen del desarrollo; no son imágenes generadas para aparentar resultados.

## Comprobaciones realizadas fuera de los notebooks

- Reconstrucción y alineación de vectores, nombres y catálogo; entrenamiento autorizado exclusivamente.
- Concordancia del escalado guardado y resultados de validación del combinado.
- Ejecución secuencial de todas las celdas Python, captura de sus tablas/figuras y revisión visual de las figuras.
- Validación del formato de los notebooks y ausencia de salidas de error.
- No se ejecutaron pruebas de micrófono ni una ventana nueva en Windows.

La ejecución de las celdas se hizo directamente con Python y captura de sus salidas; el entorno no permitió iniciar un kernel Jupyter mediante sockets. El código entregado se ejecutó sin cambios, salvo el mecanismo de captura de display/figuras para incorporarlas al notebook. La prueba del arranque del kernel en Windows corresponde al entorno local del lector.

No hay celdas de hashes, assert, pruebas de integridad o baterías de tests en los notebooks. La información técnica mínima de procedencia está separada en `datos/procedencia.json`.

## Fuentes y límites

Fuentes principales: consigna Trabajo Final 2026 y Clase 9 — Aprendizaje 2026 dentro del ZIP del curso; código y documentación del repositorio en commit `eb97d38ab95d1f3a776734b2b2fa36ed54df37b9`. Cada cuaderno enlaza sus fuentes específicas. El detalle acústico sigue la documentación y código del proyecto; la Clase 10 citada por esa documentación no estaba dentro del ZIP consultado.

La guía conserva fallos y separa entrenamiento, calibración, control y prueba final. No presenta resultados sintéticos como validación biométrica real ni pruebas de una voz conocida como generalización a otras personas.

## Si se incorpora a Git

Desde la raíz del repositorio, luego de copiar la carpeta y revisar su contenido:

```powershell
git add guia_didactica/
git diff --cached --stat
git commit -m "Agregar guia didactica integral y PCA del modelo combinado congelado"
```

No se realizaron commits ni push automáticamente. La guía incluye un ejemplo acústico en forma de arreglo numérico tomado del dataset ya publicado; si se desea distribuir material sin datos de voz, conservar solo las salidas/HTML y retirar ese arreglo junto con la ejecución de la celda de forma de onda. No confundir un archivo NPZ de amplitudes con anonimización del sonido.
