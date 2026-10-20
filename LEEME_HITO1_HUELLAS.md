# Hito 1: características de huellas

1. Extraer este ZIP en una carpeta temporal. Copiar sus carpetas `src`, `config`, `tests`, `notebooks`, `documentos` y `datos` a la raíz de Trabajo-Final-IA1. Son archivos nuevos; no borrar ni reemplazar carpetas completas del proyecto.
2. Desde PowerShell en la raíz, usando el entorno existente:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_caracteristicas_huellas.py" -v
.\.venv\Scripts\python.exe src/extraer_dataset_huellas.py --verificar-180
```

No hay bibliotecas nuevas que instalar. No usar --incluir-prueba en este primer ensayo.

3. Abrir `notebooks/03_caracteristicas_huellas.ipynb`, seleccionar el kernel de `.venv` y ejecutar todas las celdas. Explica el procedimiento y muestra imágenes, regiones, una GLCM y el vector.
4. Leer `documentos/caracteristicas_huellas_hito1.md` para las decisiones, fórmulas y límites.
5. Devolver el resumen de consola (o `resumen.json`), el resultado de las pruebas y una captura de los paneles del notebook. Si hay errores o avisos nuevos, añadir `catalogo_caracteristicas.csv` y `manifiesto.json` de esa ejecución.

Resultado de referencia observado por el asistente: 170×144; 120 entrenamiento, 50 validación, 50 prueba diferida; sin errores; invariancia 180° exacta en desarrollo; dos avisos previos de normalización conservados. No es un resultado de reconocimiento.

Las salidas se crean bajo `datos/caracteristicas/huellas/`, en carpetas por firma de extractor y fecha. Se mantienen locales mediante el `.gitignore` de esa carpeta. Repetir el comando crea una nueva ejecución, sin borrar la anterior. Los vectores no vienen en el ZIP: se generan con tus archivos.

Este paquete no toca el README, los módulos anteriores, los datos de audio, ni el `.gitignore` raíz. No se hizo commit ni push. Antes de versionar, revisar `git status --short` y seleccionar expresamente los archivos de este hito.
