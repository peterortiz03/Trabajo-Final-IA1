# Extracción de características de huellas — hito 1

Trabajo Final IA I 2026, Ingeniería en Mecatrónica, UNCUYO. Corte: 20/10/2026.

## Objetivo y fuentes

Representar cada captura sintética mediante un vector de dimensión fija. Este
hito implementa extracción, trazabilidad y controles; no entrena K-means, no
establece umbrales, no ajusta escaladores/PCA y no evalúa precisión.

Fuentes revisadas, por prioridad:

1. `Trabajo Final 2026.pdf`, extraído de `ia1_material_15_10.zip`, 4 páginas.
   Exige vectores discriminantes, K-means k=3 para autorizados, rechazo por
   distancia, K-NN para voz, PCA e informe. No obliga a este descriptor ni a
   una dimensión particular. El preprocesamiento debe responder al descriptor.
2. `Clase 10- Percepción 2026(1).pdf`, especialmente diapositivas 45–49.
   La 45 muestra GLCM, contraste, energía, correlación y homogeneidad, además
   de otros métodos. Las diapositivas 61–64 quedan como guía para el próximo hito.
3. Repositorio `https://github.com/peterortiz03/Trabajo-Final-IA1`, commit
   `8fc2850f6cefc8fe645e2006b0cc2646f5d1161a`, 20/10/2026 a las 09:13:28 -03:00.
   Se revisaron README, dependencias, configuración y código de normalización,
   catálogo vigente, procedencia y notebooks 01/02.
4. Definición de GLCM y medidas: documentación oficial de scikit-image:
   https://scikit-image.org/docs/stable/api/skimage.feature.html#skimage.feature.graycomatrix
   https://scikit-image.org/docs/stable/api/skimage.feature.html#skimage.feature.graycoprops

No se añadió scikit-image: su función GLCM no recibe una máscara de pares.
Se implementa ese conteo con `numpy.bincount`, y las cuatro fórmulas explícitas.
NumPy, SciPy (erosión) y Pillow (lectura) ya están en el proyecto. Matplotlib,
también existente, permite inspeccionar el procedimiento en el notebook.

**Cambio observado en el repositorio:** el último commit incluye WAV y catálogos
de audio y eliminó la exclusión de `datos/audio/`. El README aún dice que son
locales. Es una inconsistencia documental a resolver en el hito de audio. Este
paquete no modifica ni publica audios, derivados o políticas de audio.

## Primer descriptor: GLCM con regiones opuestas

Las crestas y valles forman una textura orientada. Las frecuencias de pares
claro/oscuro cambian con la separación y la dirección, por lo que una GLCM puede
resumir estructura de crestas. Esto justifica probarla como referencia inicial;
no demuestra que distinga dedos. Diferentes identidades pueden compartir textura
y las deformaciones, desenfoque o contacto parcial pueden alterar las medidas.
No identifica minucias ni reconstruye correspondencias entre crestas.

### Entrada y acondicionamiento por muestra

- Imagen gris `uint8`, columna **normalizada** del catálogo vigente. Se conserva
  escala; no se redimensiona ni se utiliza la columna heredada `procesado`.
- Máscara binaria de igual tamaño, derivada mediante la convención del código
  publicado: `A01_M01.png` → `A01_M01_mascara.png`. No es una máscara de crestas:
  delimita la región en la que crestas y valles son datos válidos.
- Erosión con disco de radio **6 píxeles**: la configuración geométrica anterior
  agregó un margen de 6 píxeles. Retirarlo reduce la contribución de su borde
  claro. Es una decisión inicial fija; no garantiza eliminar todo fondo interno
  ni sustituye la inspección de segmentación. Puede perder crestas periféricas.
- Recorte al rectángulo mínimo de la máscara erosionada. Define regiones en
  coordenadas relativas a la ROI; no aprende un alineamiento entre identidades.
- Contraste por imagen con percentiles **2 y 98**, calculados solo dentro de
  esa máscara. Se recorta la intensidad fuera de esos percentiles y se lleva a
  [0,1]. El rango debe ser al menos **20 niveles originales**: no se amplifica
  una imagen casi constante para convertir ruido en textura. Son valores
  iniciales de acondicionamiento y control, no umbrales de reconocimiento.
- Sin filtros espaciales adicionales, CLAHE, binarización o esqueletizado en
  esta referencia. Las GLCM aprovechan grises y otro suavizado cambiaría las
  transiciones que se desea medir. La necesidad de otro filtro se estudiará en
  desarrollo si aparecen fallas concretas.
- Cuantización uniforme a **16 niveles**, numerados 0–15. Reduce sensibilidad a
  pequeñas variaciones y evita matrices 256×256 muy dispersas. También pierde
  detalle tonal. No es un vocabulario aprendido de todas las imágenes.

Si $a,b$ son los percentiles por imagen:

$$u=\mathrm{clip}\left(\frac{I-a}{b-a},0,1\right),\qquad
q=\min(\lfloor16u\rfloor,15).$$

### Pares, distancias y direcciones

Distancias nominales euclídeas: **1, 3 y 5 píxeles**. Direcciones: **0°, 45°,
90° y 135°**. Son separaciones locales de distintas escalas; no se presume que
5 sea el período exacto de las crestas. No se seleccionaron por precisión ni
mirando prueba. Las filas de imagen crecen hacia abajo, de modo que 45° apunta
abajo-derecha y 135° abajo-izquierda.

Se redondean los desplazamientos al entero más cercano:

| d nominal | 0° (dy,dx) | 45° | 90° | 135° | Distancia efectiva diagonal |
|---:|---|---|---|---|---:|
| 1 | (0,1) | (1,1) | (1,0) | (1,-1) | √2 ≈ 1,41 |
| 3 | (0,3) | (2,2) | (3,0) | (2,-2) | √8 ≈ 2,83 |
| 5 | (0,5) | (4,4) | (5,0) | (4,-4) | √32 ≈ 5,66 |

Un par se cuenta **solo si ambos píxeles están dentro de la máscara y de la
misma región de conteo**. No se pinta el exterior y se calcula sobre todo el
lienzo. No se utiliza `np.roll`, que conectaría bordes opuestos. Para cada
desplazamiento se guarda la cantidad de pares antes de simetrizar.

### Información espacial y ambigüedad de 180°

Se divide el rectángulo de la ROI en cuadrantes NO, NE, SO y SE. Si una dimensión
es impar, su fila o columna central se deja fuera de los cuadrantes y se usa
solo en la matriz global. Así las regiones se intercambian exactamente al girar.

Se construyen **tres bloques**, con este orden:

1. Global: todos los pares válidos en la ROI, incluso a través del centro.
2. NO_SE: suma de conteos internos de NO y de SE.
3. NE_SO: suma de conteos internos de NE y de SO.

Los dos cuadrantes de cada pareja se cuentan por separado: no se crean pares
que conecten regiones distintas. Se suman **conteos**, no se promedian los
descriptores. Esto pondera cada cuadrante según sus pares válidos.

Para cada bloque se obtiene una matriz simétrica de probabilidades:

$$P=\frac{C+C^T}{\sum_{i,j}(C+C^T)_{ij}}.$$

Un giro exacto de 180° intercambia NO↔SE y NE↔SO; además invierte el sentido del
desplazamiento, transponiendo la matriz dirigida. La suma de regiones opuestas y
la simetrización eliminan ambos cambios. Por ello se obtiene **un vector por
muestra**, invariante a ese giro cuando se gira también su máscara.

Se pierde qué esquina opuesta contenía cada textura, el orden claro→oscuro de
los pares y parte del detalle espacial. La simetrización por sí sola NO habría
hecho invariante una concatenación NO, NE, SO, SE. Tampoco se afirma invariancia
a 90°, rotaciones arbitrarias, deformación o recorte. La máscara usada con la
alternativa debe girarse: no se reutiliza sin girar.

### Medidas y orden del vector

| Medida | Fórmula sobre P | Lectura |
|---|---|---|
| Contraste | $\sum P_{ij}(i-j)^2/(L-1)^2$ | Diferencia de intensidades entre vecinos; aquí se normaliza por el rango de niveles. |
| Homogeneidad | $\sum P_{ij}/(1+(i-j)^2)$ | Qué tan concentrados están los pares cerca de igual intensidad. |
| Energía | $\sqrt{\sum P_{ij}^2}$ | Concentración del histograma de pares; no es energía física. |
| Correlación | $\sum P_{ij}(i-\mu_i)(j-\mu_j)/(\sigma_i\sigma_j)$ | Dependencia lineal de intensidades entre extremos de los pares. |

Orden: **bloque → distancia → ángulo → medida**, con los órdenes indicados.
Ejemplos: `global_d1_a0_contraste`, `global_d1_a0_homogeneidad`,
`global_d1_a0_energia`, `global_d1_a0_correlacion`, …,
`NE_SO_d5_a135_correlacion`.

$$\boxed{D=3\ \text{bloques}\times3\ \text{distancias}\times4\ \text{direcciones}
\times4\ \text{medidas}=144}.$$

`nombres_caracteristicas.json` conserva la lista completa. No se agregan etiquetas,
semillas, particiones, identidad, tipo morfológico o cantidades de pares al vector.
La matriz contiene solo números del descriptor. Los bloques se solapan y algunas
columnas pueden estar correlacionadas; la dimensión 144 no implica 144 fuentes
independientes de información. No hay selección por clase en este hito.

### Casos límite

- Máscara vacía, formato incompatible, contraste insuficiente, menos de 256
  píxeles en cualquiera de las cinco regiones de conteo, o menos de 64 pares en
  un desplazamiento de cualquiera de ellas: `no_vectorizable` y motivo. No se
  completa el vector con ceros ni se imputa información artificial.
- Textura cuantizada constante en un cuadrante: se guarda un aviso explícito.
  Las otras regiones todavía pueden contener información.
- GLCM de varianza cero: contraste=0, homogeneidad=1, energía=1 y correlación=1
  **por convenio**, con aviso de que la correlación no es estimable. No se genera
  NaN. Una imagen totalmente constante ya fue detenida antes, por contraste.
- Archivo ausente, hash incorrecto o alternativa que no sea el giro exacto:
  `error_entrada` con motivo. Se preserva la fila, sin asignarle vector.
- No vectorizable NO significa intruso. La decisión sobre calidad y la decisión
  de autorización son problemas distintos; no se cambia una etiqueta por fallar.
- Los avisos de normalización se preservan incluso si el descriptor es finito.
  `vectorizada` es un estado técnico, no aprobación humana para modelado.

## Archivos y ejecución en Windows

Copiar los archivos del paquete respetando las carpetas en la raíz del repositorio.
Todos tienen nombres nuevos; no reemplazan etapas anteriores ni `requirements.txt`.
No es necesario crear otro entorno ni instalar bibliotecas nuevas.

Desde PowerShell, en la raíz:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_caracteristicas_huellas.py" -v
.\.venv\Scripts\python.exe src/extraer_dataset_huellas.py --verificar-180
```

Se usa `unittest` de Python: no requiere pytest. El entorno del proyecto registra
Python 3.14; la ejecución del asistente fue con Python 3.12.14 en Linux, usando
las mismas versiones NumPy 2.3.5, SciPy 1.17.0, Pillow 12.3.0 y Matplotlib 3.10.8.
No se afirma haber ejecutado en Windows ni en el Python local del estudiante.
La comprobación final de ese entorno son los comandos anteriores.

Luego abrir `notebooks/03_caracteristicas_huellas.ipynb`, seleccionar `.venv`
en VS Code y ejecutar todas las celdas. No requiere pandas o scikit-learn.
Si no hay kernel y VS Code lo solicita, instalar `ipykernel` como ya indica el
README existente; no es una dependencia del extractor.

La ejecución predeterminada procesa entrenamiento y validación. Registra las
filas de prueba como `diferida_prueba`, sin leer sus PNG. Más adelante, con el
método congelado, `--incluir-prueba` permite generar otra ejecución completa.
No es necesario ni conveniente usar esa opción en este primer ensayo.

### Salidas

Cada invocación crea una carpeta nueva:

`datos/caracteristicas/huellas/<id_extractor>/ejecucion_<fecha_UTC>/`

El identificador incluye una firma de configuración, código, dependencias y
configuración de normalización. No se mezclan resultados de contratos distintos.
No hay cantidades fijas de muestras o identidades. Al incorporar muestras,
actualizar el catálogo por el procedimiento existente y ejecutar otra vez:
esta versión sencilla **recalcula el lote de desarrollo** en una nueva carpeta,
sin sobrescribir las anteriores. No es una caché incremental.

| Salida | Uso |
|---|---|
| `vectores.npz` | `X` float64 N×D, `muestras` y `nombres` como arrays separados; cargar con `allow_pickle=False`. |
| `vectores.csv` | Vista legible; `muestra` es metadato, no una característica. No entregar todas las columnas ciegamente a un modelo. |
| `catalogo_caracteristicas.csv` | Todas las filas fuente, con estado, motivo, avisos, hashes y `fila_vector` (índice desde 0). Filas fallidas/diferidas no tienen índice. |
| `detalle_extraccion.json` | Percentiles por muestra, áreas, conteos de pares, avisos y error de invariancia cuando se solicita. |
| `config_efectiva.json`, `nombres_caracteristicas.json` | Configuración exacta y contrato de columnas. |
| `manifiesto.json` | Procedencia, entorno, código, hashes, dimensiones y desplazamientos efectivos. |
| `resumen.json` | Conteos y comprobaciones mecánicas. |
| `catalogo_origen.csv`, `normalizacion_*.json`, `fuente_*.py` | Copias de procedencia y código de esa ejecución. |

Los resultados se escriben primero en una carpeta `.parcial` y se renombran al
completar. Una interrupción puede dejarla para inspección; el notebook la ignora.
Si hay filas no vectorizables o errores de entrada, el lote conserva los motivos
y termina con código 2. No ocultar esos casos: revisarlos antes de modelar.

El notebook elige la ejecución más reciente compatible con configuración, código
y dependencias actuales, o permite indicar una ruta explícita. Nunca concatena
ejecuciones automáticamente. La correspondencia se basa en IDs e índices, no
en suponer que la fila CSV siempre coincide con la fila de X.

## Uso posterior con una muestra nueva

En un script dentro de `src/`, usando el mismo JSON de geometría que el lote:

```python
import json
from pathlib import Path
from normalizacion_final import normalizar_huella
from caracteristicas_huellas import cargar_config, extraer_huella

raiz = Path(__file__).resolve().parents[1]
cfg_roi = json.loads((raiz / 'config/roi_normalizacion_v1.json').read_text())
# imagen_pil: imagen original ya leída con Pillow.
normalizada, info = normalizar_huella(imagen_pil, cfg_roi)
vector, diagnostico = extraer_huella(normalizada, info['mascara_normalizada'], cargar_config())
# Revisar info['avisos'] y diagnostico['avisos']; capturar ValueError.
```

No requiere identidad ni catálogo. Cuando exista un modelo, además deberá
verificarse que su firma y nombres de columnas coincidan, y aplicarse el
escalador entrenado guardado. Hoy no hay ningún escalador ajustado.

## Pruebas y resultados realmente obtenidos

Sobre el commit indicado, la primera ejecución de desarrollo obtuvo:

| Control | Resultado |
|---|---:|
| Filas del catálogo | 220 |
| Vectores de entrenamiento | 120 |
| Vectores de validación | 50 |
| Prueba diferida (sin lectura de PNG) | 50 |
| Forma de X | 170×144 |
| Errores / no vectorizables | 0 / 0 |
| Muestras con avisos nuevos del extractor | 0 |
| Avisos previos de normalización conservados | 2 |
| Vectores comprobados frente al giro 180° | 170 |
| Diferencia absoluta máxima observada | 0 |

Los dos avisos previos corresponden a A01_M43 y A02_M44. No se borraron ni se
convirtieron en descartes. No se ha aprobado automáticamente su uso en un modelo.

Pasaron 11 pruebas automatizadas: dimensión y orden, determinismo, invariancia
en tamaños pares/impares, irrelevancia del fondo, conteo contra un recorrido
independiente de píxeles, medidas con solución manual, entradas inválidas,
regiones constantes, intercambio espacial, configuración de distinta dimensión
y pruebas de lote. Estas últimas verifican filas fallidas, hashes, duplicados,
ampliación del catálogo, ejecuciones separadas y que la prueba no se abra.
Varios controles se agrupan dentro de una misma prueba.

El registro del asistente se guarda en
`documentos/historico/verificacion_caracteristicas_huellas_asistente.json`. Es evidencia
del entorno indicado, no una ejecución del estudiante. El notebook se entrega
sin salidas para que se documenten los resultados locales.

**Pendiente:** comprobar ejecución en Windows/Python 3.14 y revisar las figuras
de desarrollo. Ninguna de estas verificaciones demuestra separación de
identidades. Si GLCM resulta insuficiente al evaluar desarrollo más adelante,
se comparará de manera acotada con una alternativa como Gabor u orientación
local, manteniendo fijas las particiones. Hu no se añade en este hito: medir
solo la silueta no describe la distribución interna de crestas.

## Versionado y próximos hitos

Conviene versionar los dos módulos nuevos, configuración, pruebas, notebook,
esta documentación, registro de verificación y el `.gitignore` específico de
las salidas de huellas. Las matrices y ejecuciones permanecen locales por
defecto; un corte revisado podrá publicarse explícitamente más adelante. No
usar `git add .` para incorporar sin revisión otros archivos pendientes.

Este paquete no cambia `.gitignore` raíz ni decide políticas de audio. Antes de
cualquier commit, revisar `git status --short`; no publicar automáticamente
datos de voz o sus derivados. README e índice general se pueden consolidar al
aprobar el hito, corrigiendo también la contradicción documental de audio.

El próximo hito será audio: función por muestra, catálogo procesado activo,
avisos/decisiones humanas y segmentos temporales. El tercero será escalado/PCA:
huellas con entrenamiento autorizado; audio solo después de fijar un mapa
persistente por hablante. H001/H002 ya se usaron en desarrollo y no serán prueba
final independiente. No se presupone que H003–H005 sean independientes sin
revisar su uso previo. Nada de eso se ajusta o implementa aquí.

## Uso de IA generativa

Se utilizó ChatGPT para revisar las fuentes, proponer esta primera representación,
redactar los módulos, pruebas y explicación. Solicitud de referencia: extracción
GLCM con máscara, un vector invariante a 180°, sin incorporar etiquetas, sin
ajustar decisiones con prueba y manteniendo trazabilidad. Las respuestas se
verificaron con conteos manuales, casos sintéticos, revisión del código y
ejecución en desarrollo. El estudiante debe comprobar y comprender el método;
la asistencia no sustituye la justificación ni la defensa individual del trabajo.
