# Hito 2 — características de audio

Este paquete incorpora la extracción reproducible de un vector de 160
características por grabación procesada. No entrena K-NN, no ajusta un
escalador y no modifica los WAV.

La ejecución revisada del 20/10/2026 procesó 180 grabaciones de seis hablantes
y produjo una matriz 180×160, sin valores no finitos y con repetibilidad exacta.
El detalle está en `documentos/caracteristicas_audio_hito2.md`.

El ZIP tiene rutas relativas a la raíz del proyecto. Puede extraerse sobre una
copia del repositorio y aceptar el reemplazo de los archivos de este hito. No
contiene WAV ni reemplaza catálogos de captura o preprocesamiento.

## Instalación

No requiere bibliotecas nuevas. Utiliza NumPy, SciPy y Matplotlib del entorno
del proyecto.

## Comprobación

Desde la raíz del repositorio, en PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_caracteristicas_audio.py" -v
```

## Extracción

```powershell
.\.venv\Scripts\python.exe src/extraer_dataset_audio.py --verificar-repetibilidad
```

El programa lee el catálogo procesado activo mediante
`datos/audio/procesados/actual.json`. Cada ejecución crea una carpeta nueva en
`datos/caracteristicas/audio/`; no sobrescribe resultados anteriores.

## Notebook

Abrir `notebooks/04_caracteristicas_audio.ipynb`, elegir como kernel el entorno
`.venv` y ejecutar las celdas en orden. El notebook explica ventanas,
segmentos, ZCR, amplitud, MFCC, orden del vector, avisos y relación futura con
K-NN.

Los resultados derivados permanecen locales por medio del `.gitignore` de la
carpeta de características. Conviene versionar el código, la configuración,
las pruebas, el notebook y la documentación.
