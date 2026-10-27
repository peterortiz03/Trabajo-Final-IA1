# Audio: PCA 3D y K-NN

Abrir audio_pca_3d_y_knn.ipynb. Contiene todas las salidas guardadas y seis figuras PNG. Se puede copiar esta carpeta junto a la guía didáctica, o conservarla aparte.

Para ejecutar, abrir esta carpeta como directorio de trabajo y seleccionar el entorno Python del proyecto. Se requieren numpy, matplotlib, scikit-learn e ipykernel para Jupyter/VS Code. Conservar datos/ junto al notebook. No requiere acceso al micrófono ni reentrenar el sistema. Las celdas no contienen asserts ni auditorías de archivos.

PCA nuevo con las 179 grabaciones de desarrollo conservadas; resultados LOSO históricos. No hay selección visual de muestras ni esferas artificiales. El ejemplo de empate es sintético y está separado de los resultados reales.

Las celdas se ejecutaron secuencialmente con Python y se guardaron las figuras y textos; no se ejecutó una nueva evaluación por micrófono ni Windows. El entorno de ensayo usa scikit-learn 1.8.0. La elección entre vecinos exactamente equidistantes no debe tratarse como una regla estable entre versiones.
