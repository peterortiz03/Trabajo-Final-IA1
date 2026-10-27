# Umbral y radios de K-means

Abrir umbral_y_radios_kmeans.ipynb. Las salidas están guardadas.
Para ejecutar, abrir esta carpeta como directorio de trabajo y usar un kernel con numpy, matplotlib y scikit-learn. Mantener los cuatro archivos de datos junto al notebook. No depende de los modelos locales ni modifica el proyecto.

Puede guardarse como subcarpeta de guia_didactica. Las dos figuras PNG sirven para el informe. La figura PCA muestra proyecciones de esferas, no una regla exacta de aceptación en 2D. La vista de distancias relativas sí representa la decisión real.

Se ejecutaron las celdas de manera secuencial con Python y se guardaron sus salidas; no se probó micrófono ni se reentrenó el sistema. Se conserva el criterio d_min <= umbral.

## Actualización 3D · 27/10/2026

Se añadió PC1–PC2–PC3 desde dos ángulos con esferas de radio tau. Conservar 93,71 % de varianza no reproduce todas las distancias: 23/70 intrusas se proyectan dentro de alguna esfera y aun así se rechazan en 36 dimensiones. Los símbolos muestran la decisión real. Se conservan las vistas 2D, distancia completa y curva FAR/FRR. No se modificaron modelo ni umbral.

## Frontera exacta · actualización

El nuevo gráfico principal descompone la distancia real al centroide asignado en longitud PC1–PC2 y longitud residual de las otras 34 direcciones. No es un PCA convencional ni preserva distancias entre muestras; sí conserva exactamente la distancia de cada muestra a su centroide de referencia. Permite un arco de aceptación fiel al modelo. Se incluyen todas las consultas, incluido el falso rechazo. Los PCA originales permanecen como vistas descriptivas con sus limitaciones.

## Frontera exacta · actualización

El nuevo gráfico principal descompone la distancia real al centroide asignado en longitud PC1–PC2 y longitud residual de las otras 34 direcciones. No es un PCA convencional ni preserva distancias entre muestras; sí conserva exactamente la distancia de cada muestra a su centroide de referencia. Permite un arco de aceptación fiel al modelo. Se incluyen todas las consultas, incluido el falso rechazo. Los PCA originales permanecen como vistas descriptivas con sus limitaciones.
