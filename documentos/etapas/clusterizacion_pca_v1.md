# Clusterización y PCA: implementación y ejecución

## Fuentes y alcance comprobado

Revisado `main` en commit `6505a6c` (README, configuración, extractores, revisiones y catálogos).
Leídas la consigna Trabajo Final 2026, páginas 1, 3–4, y Clase 9 - Aprendizaje 2026,
sección de aprendizaje no supervisado/K-means, del ZIP de material entregado.
La extracción de texto de la consigna produjo avisos de compresión en objetos gráficos;
los requisitos textuales fueron legibles. La presentación no desarrolla PCA en el texto extraído.

La etapa 05 no estaba en ese commit. Se consultaron el notebook 05 compartido y su ZIP de
resultados 20261022T141121_625126Z; de allí se recuperaron, sin alterar su contenido,
el módulo estadístico y el mapa de particiones. Se reutilizan su cargador, controles,
medias/desviaciones y razón de separación. El paquete incluye esas dos dependencias en
`antecedentes_si_faltan/`: copiar solo si no existen. No sobrescribir versiones locales nuevas.

El mapa destina H001–H006 a entrenamiento. No hay validación ni prueba independiente de audio
actuales. Agregar futuras voces al mapa con `particion: validacion` o `particion: prueba`
antes de usarlas; no repartir grabaciones de una misma persona entre particiones.
Las personas usadas para ajustes no deben pasar luego a prueba independiente.
La capa de particiones no modifica catálogos anteriores. El extractor de audio original no conoce
esta capa: para futuras voces de prueba, asignar también su partición persistente en el flujo de
captura/catálogo antes de extraer; en esta etapa sus filas quedan fuera de todo ajuste y gráfico.

La única exclusión publicada era H006_S001_salir_0005 (ruido de fondo).
Posibles exclusiones posteriores no estaban en main ni en ese corte compartido.
Se respeta la configuración local vigente: si cambió, el cargador exige actualizar catálogo y
extracción. No se descartan automáticamente los 12 avisos del extractor ni los avisos previos;
la decisión humana publicada conserva esas muestras. No se realizó una nueva escucha.

## Archivos y parámetros

- `src/clusterizacion_pca.py`: carga, selección de desarrollo, escalado, PCA, diagnóstico y K-means.
- `config/clusterizacion_pca_v1.json`: semilla, 20 inicializaciones, k=3, PCA completo y vistas.
- `notebooks/06_clusterizacion_pca.ipynb`: explicación, ejecución, tablas y figuras.
- `requirements-clusterizacion.txt`: dependencias existentes + scikit-learn 1.8.0.
- `tests/test_clusterizacion_pca.py`: fuga, columnas constantes, recarga y exclusión de prueba/intrusos.

Scikit-learn 1.8 admite Python 3.11–3.14, por lo que es compatible con Python 3.14.0 documentado
por el proyecto. Se comprobó ejecución aquí con Python 3.12.14/Linux, NumPy 2.3.5, SciPy 1.17.0,
Pillow 12.3.0 y Matplotlib 3.10.8. No se afirma haber instalado ni ejecutado en Windows.
Fuente oficial: https://scikit-learn.org/1.8/whats_new/v1.8.html
La instalación binaria y `pip check` siguientes verifican el entorno real del usuario.

## Instalación en PowerShell

Extraer el paquete fuera del repositorio y ejecutar `instalar_archivos.ps1 -Repositorio "ruta"`.
El script copia solo archivos nuevos; si encuentra una versión distinta de un archivo nuevo,
se detiene para no sobrescribir trabajo. Los antecedentes existentes se conservan.
Después, desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-clusterizacion.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip install ipykernel
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_clusterizacion_pca.py -v
```

Abrir `notebooks/06_clusterizacion_pca.ipynb`, seleccionar `.venv` y ejecutar todo.
Si falta una extracción compatible, ejecutar:

```powershell
.\.venv\Scripts\python.exe src/extraer_dataset_huellas.py
.\.venv\Scripts\python.exe src/extraer_dataset_audio.py
```

Si cambiaste revisiones de audio, primero actualizar el catálogo:

```powershell
.\.venv\Scripts\python.exe src/preprocesar_dataset_audio.py
.\.venv\Scripts\python.exe src/extraer_dataset_audio.py
```

No usar `--incluir-prueba`. No regenerar datos sintéticos ni normalización.
La extracción de desarrollo no ajusta modelos. Si se incorporan nuevas voces, decidir primero
su partición explícita. Un conflicto detiene el análisis con un mensaje; no se reasigna al azar.
Alternativa al notebook, con los mismos resultados:

```powershell
.\.venv\Scripts\python.exe src/clusterizacion_pca.py
```

## Método y lectura de los resultados

StandardScaler aprende una media y una desviación por columna con ddof=0, solo entrenamiento.
Las columnas constantes se conservan, con escala 1. PCA usa todas las columnas y SVD completa,
sin whitening. Validación se transforma con el mismo escalador y PCA. Con menos muestras que
columnas, el número de direcciones no nulas está limitado por n-1; no significa haber eliminado
columnas originales. El modelo conserva el orden de entrada para muestras futuras.

K-means se ajusta en las 144 características estandarizadas de huellas autorizadas; PCA solo
proyecta los puntos y centroides. La correspondencia grupo-identidad se calcula uno a uno
maximizando coincidencias de entrenamiento; se congela para validación. ARI no depende de los
nombres de grupo. No se calcula un umbral de acceso ni se evalúan intrusos en esta etapa.

La tabla de dispersión usa el mismo indicador entre/dentro del notebook 05 y añade RMS interno
estandarizado. DE alta en unidades originales no implica mala característica. La variación entre
clases puede ser útil; la variación interna puede dificultar la separación. Se ordena por el
indicador estandarizado para evitar comparar directamente MFCC, energía y otras escalas.
No se eliminan columnas, no se consultan resultados de prueba ni se borran muestras válidas.

Los gráficos por clase y por hablante de audio representan las mismas coordenadas. Comparar ambos
para distinguir palabra y voz; las tablas condicionales separan palabras dentro de cada hablante
y hablantes dentro de cada palabra. Son diagnósticos, no evidencia de generalización a voces nuevas.

## Referencia ejecutada por el asistente

Corte publicado + mapa recuperado de etapa 05, sin exclusiones locales posteriores:

| Resultado | Huellas | Audio |
|---|---:|---:|
| Entrenamiento utilizado | 120 autorizadas | 179 conservados |
| Validación utilizada | 30 autorizadas | 0 |
| Características de entrada | 144 | 160 |
| Constantes en entrenamiento | 0 | 0 |
| Varianza PC1–PC2 | 80.84 % | 27.75 % |
| Componentes para 95 % | 3 | 52 |
| ARI entrenamiento | 0.4477 | No corresponde |
| ARI validación | 0.5436 | No disponible |

El catálogo de huellas tiene además 20 intrusas de validación y 50 muestras de prueba: no se usan
en los modelos ni en los gráficos. K-means agrupa principalmente A02 en G1, pero mezcla A01/A03
en G0. En entrenamiento: A01=(27,0,13), A02=(0,37,3), A03=(29,0,11), columnas G0/G1/G2.
En validación: A01=(9,0,1), A02=(0,10,0), A03=(10,0,0).
Correspondencia entrenada: G0→A03, G1→A02, G2→A01. Coincidencia: 65.83 % entrenamiento,
70 % validación. No representan aceptación/rechazo de acceso.
PC3 de huellas aporta 14.48 %, por eso se agrega una vista PC1–PC3. No altera el agrupamiento.

No hay evidencia para asegurar que el agrupamiento represente correctamente las tres identidades.
Las variantes sintéticas de una misma base tampoco prueban generalización a huellas reales.
En audio, la proyección 2D omite aproximadamente 72.25 % de variación: su solapamiento no demuestra
inseparabilidad en 160 dimensiones. La evaluación independiente queda pendiente.

## Próximas mejoras: solo después de esta referencia

Revisar primero relación con rotación/calidad y variación interna en entrenamiento. Ejemplos
para investigar por baja separación: NO_SE_d1_a90_energia, global_d5_a0_energia y
global_d1_a90_energia. No se afirma que quitarlas mejore K-means.
Probar después una lista pequeña definida desde entrenamiento, volver a ajustar todo en
entrenamiento y comparar ARI, tabla por identidad y estabilidad en validación frente a la
referencia, sin tocar prueba. Conservar solo mejoras consistentes, sin perjudicar una identidad.
No recorrer muchas variantes hasta que validación dé el resultado deseado.
Audio: s10_mfcc_c4_max es un ejemplo débil individualmente; revisar efecto de hablante antes de
modificar el descriptor. Hacen falta nuevas voces de validación para comparar generalización.

## Qué se guarda y qué compartir

Cada ejecución escribe `resultados/clusterizacion_pca/FECHA/` con:
- `resumen.json`: corte, configuración, versiones, entradas y hashes de archivos generados.
- Por modalidad: modelos.pkl, parametros.npz, nombres/medias/escalas, varianza explicada,
  proyecciones, catálogo de uso, cantidades, diagnóstico y gráficos.
- En huellas: tablas identidad-grupo de entrenamiento y validación.
- En audio: separación condicional por palabra/hablante.

Enviar la carpeta comprimida o, como mínimo, resumen.json, tablas identidad/grupo, pca_clases.png,
pca_grupos.png, pca_hablantes.png y varianza_acumulada.png. Si falla: traceback completo,
`python --version` y `pip check`. No hacen falta nuevos WAV para interpretar las tablas.
Los modelos pickle solo deben cargarse desde archivos propios/confiables y en el entorno registrado.
Las nuevas muestras se procesan con `transformar_nuevas` sin fit; asignar grupo no autoriza acceso.

## Commits sugeridos (revisar git diff antes de confirmar)

Si la etapa 05 ya está guardada, omitir el primer commit. No incluir revisiones locales sin revisarlas.

```powershell
git status --short
git add src/verificacion_estadistica.py config/particiones_audio_v1.json
git commit -m "Conservar el diagnostico estadistico y la particion por hablante"
git add requirements-clusterizacion.txt config/clusterizacion_pca_v1.json src/clusterizacion_pca.py tests/test_clusterizacion_pca.py
git commit -m "Agregar PCA y K-means sin usar validacion para ajustar parametros"
git add notebooks/06_clusterizacion_pca.ipynb documentos/etapas/clusterizacion_pca_v1.md
git commit -m "Documentar la referencia completa y sus limites de separacion"
```

No usar `git add .` para evitar publicar todos los modelos o resultados sin revisión.
Opcional: añadir `/resultados/clusterizacion_pca/` a .gitignore para conservar modelos locales;
el notebook ejecutado y un resumen seleccionado bastan para mostrar el avance. No hubo push.
Registrar la ayuda de IA en `documentos/uso_ia_generativa.md` con el prompt y controles ejecutados.
