# Extracción de características acústicas — hito 2

Trabajo Final IA I 2026, Ingeniería en Mecatrónica, UNCUYO. 20/10/2026.

## Objetivo y alcance

Convertir cada WAV procesado en un vector numérico de dimensión fija, como
entrada futura para K-NN. No se implementan clasificación, escucha continua,
interfaz, escalado o PCA. Huellas y audio permanecen en matrices independientes.

La referencia es Clase 10 — Percepción 2026, diapositivas 61–62: diez segmentos
y resúmenes de ZCR, amplitud y algunos MFCC. Los valores concretos son una
referencia inicial documentada, no una obligación general ni parámetros elegidos
para mejorar resultados sobre prueba. La consigna permite características
acústicas como MFCC; no prescribe una dimensión.

Se revisó el repositorio en commit `8fc2850f6cefc8fe645e2006b0cc2646f5d1161a`.
La lectura del catálogo sigue el mecanismo vigente del notebook 02:
`datos/audio/procesados/actual.json` señala `ruta_catalogo` y la versión activa.
No se busca una carpeta por fecha ni se codifica el nombre actual de la versión.
Se reutilizan `leer_wav_pcm16` y `a_flotante` del preprocesamiento existente.

No hay bibliotecas nuevas: NumPy 2.3.5, SciPy 1.17.0 y Matplotlib 3.10.8 ya
están en el proyecto. Las transformadas y ventanas se calculan con SciPy.
El pequeño banco triangular Mel se define explícitamente con NumPy, evitando
añadir una biblioteca de audio y sus dependencias únicamente para esta etapa.

## Del WAV al vector, en lenguaje simple

El WAV contiene miles de muestras de amplitud por segundo. No es práctico
comparar directamente dos palabras muestra por muestra: duran distinto y se
pronuncian a distinta velocidad. En cambio, describimos cómo evoluciona el
sonido desde el comienzo hasta el final de la palabra.

Primero observamos el audio en ventanas cortas. Cada ventana produce valores
locales de cruces por cero, amplitud y forma del espectro. Después agrupamos
esas ventanas según su posición relativa en la palabra: primer 10%, segundo
10%, etc. Finalmente resumimos cada grupo y concatenamos sus números.

Esto permite una dimensión fija sin estirar el audio. No resuelve por sí solo
las variaciones de pronunciación: dos personas pueden distribuir sílabas de
manera diferente aun después de dividir sus palabras en diez partes.

## Ventanas acústicas y segmentos relativos son cosas distintas

| Concepto | Definición de esta versión | Propósito |
|---|---|---|
| Muestra temporal | Un valor de amplitud; 16000 por segundo | Representación digital del sonido |
| Ventana acústica | 25 ms = 400 muestras | Analizar un fragmento aproximadamente estable |
| Salto | 10 ms = 160 muestras | Ubicar ventanas solapadas |
| Segmento relativo | Una décima parte del intervalo activo | Conservar la evolución temporal de la palabra |

Por ejemplo, una actividad de 0,7 s se divide en diez segmentos de 70 ms.
Se analizan aproximadamente 70 ventanas, unas siete por segmento. Para otra
palabra de 1 s hay aproximadamente 100 ventanas, pero siguen siendo diez
segmentos. Al resumir cada segmento, ambos audios producen 160 números.

### Márgenes y límites de actividad

El preprocesamiento ya guardó `inicio_actividad_s`, `fin_actividad_s` y
`recorte_inicio_s` en el `resultado.json` de cada muestra. Los dos primeros
están referidos al audio original; para obtener índices del WAV procesado:

$$a=\operatorname{round}[(t_{inicio}-t_{recorte})f_s],\quad
b=\operatorname{round}[(t_{fin}-t_{recorte})f_s].$$

Se usa el intervalo activo estimado $[a,b)$ como referencia de los diez
segmentos. Los márgenes externos conservados por el preprocesamiento sirven
como contexto de las ventanas de los extremos; no reciben segmentos propios.
No se borra ningún silencio interno, no se aplica otra detección de actividad
y no se cambia el WAV. Estos límites son una heurística de energía y pueden
incluir respiración, pausas o sonidos ajenos: todavía requieren revisión humana.

Los centros de las ventanas están en $c_k=a+\lfloor H/2\rfloor+kH$, mientras
$c_k<b$, con $H$ igual al salto. Cada ventana pertenece a un único segmento:

$$s_k=\left\lfloor\frac{(c_k-a)S}{b-a}\right\rfloor,\qquad S=10.$$

Una ventana puede atravesar un límite de segmento. Se asigna por su centro,
sin cortarla ni contarla dos veces. La superposición temporal entre ventanas
es intencional; la media de amplitudes locales no es exactamente la media de
las muestras únicas del segmento.

Si el contexto de una ventana sale del archivo, solo esa parte se completa
con ceros y se registra un aviso. Eso no reconstruye un fonema cortado. No se
completa un segmento vacío copiando vecinos: ese audio se marca no vectorizable.

## Características calculadas

### Cruces por cero (ZCR)

Es la proporción de cambios de signo entre muestras consecutivas de una ventana:

$$ZCR=\frac{1}{W-1}\sum_{n=1}^{W-1}
\mathbf{1}\{\operatorname{signbit}(x_n)\ne\operatorname{signbit}(x_{n-1})\}.$$

Se calcula sobre la ventana sin Hann. Los ceros pertenecen al lado no negativo;
no se añade un umbral oculto. Por segmento se guardan la media y el máximo.
Puede aportar diferencias entre partes sonoras y ruidosas, pero es sensible al
ruido y no identifica por sí sola una consonante o palabra.

### Amplitud

Por ventana se calculan $\operatorname{mean}(|x|)$ y $\max(|x|)$, antes de Hann.
Por segmento se guarda la media de las medias absolutas y el máximo de los
máximos. Se evita usar la media con signo, que puede aproximarse a cero aunque
el sonido sea fuerte. La amplitud también depende de distancia al micrófono,
persona y ajuste previo; no es una medida exclusiva del comando.

### MFCC

Un MFCC resume la forma de la distribución de energía en frecuencia. Para cada
ventana se aplica:

1. Ventana Hann **periódica** de 400 muestras, `sym=False`, solo para el espectro.
2. FFT real de **512** puntos. Se completa la ventana con ceros para llegar a
   512; esto no estira la palabra ni crea resolución física nueva.
3. Potencia de los bins no negativos: $|FFT|^2/512$, sin duplicar los bins interiores.
4. Banco de **26 filtros triangulares** entre 0 y 8000 Hz. Nodos igualmente
   espaciados en Mel HTK: $m=2595\log_{10}(1+f/700)$. Triángulos de altura
   teórica 1 evaluados en las frecuencias FFT, sin normalizar área.
5. Logaritmo **natural**, con piso de energía de $10^{-12}$ antes del logaritmo.
6. DCT tipo II ortonormal, `norm='ortho', orthogonalize=True`.
7. Selección de **c1, c2, c4 y c5**, índices Python `[1, 2, 4, 5]`.

La selección interpreta los números de la clase como órdenes cepstrales. La
diapositiva 64 distingue c0 de c1…c12; por eso no se toma `[0,1,3,4]`. El c0
representa un promedio escalado de logenergías del banco, no necesariamente la
energía total exacta del audio. Se excluye en esta referencia.

Para cada coeficiente elegido se guardan media, máximo **con signo** y desviación
estándar poblacional (`ddof=0`) dentro de cada segmento. Si solo hay una ventana,
la desviación es cero y se registra un aviso por soporte temporal reducido.

No hay preénfasis, liftering, delta, delta-delta, normalización cepstral por
archivo ni filtro 300–5000 Hz. No se afirma equivalencia numérica con los
valores por defecto de librosa o de otra biblioteca. Estas convenciones se
guardan para que dataset y futuras entradas reciban exactamente el mismo método.

### Dimensión y orden

Por segmento: 2 ZCR + 2 amplitud + 4 MFCC × 3 estadísticas = 16.

$$\boxed{D=S\,(4+3M)=10\,(4+3\cdot4)=160}.$$

Orden: segmento 1 a 10; dentro de cada uno, `zcr_media`, `zcr_max`,
`amplitud_abs_media`, `amplitud_abs_max`, luego cada MFCC en orden `[1,2,4,5]`
con `media`, `max`, `std`. Ejemplos: `s01_zcr_media`, `s01_mfcc_c1_std`,
`s10_mfcc_c5_std`. La lista completa se exporta. Cambiar segmentos o selección
de MFCC cambia la dimensión calculada y la firma de configuración.

Ni comando, hablante, sesión, partición, avisos, duración o límites de actividad
se agregan como columnas predictivas. Los límites sirven para organizar el
cálculo temporal; se conservan como diagnóstico, fuera de X.

## Calidad, decisiones humanas y particiones

| Situación | Conducta |
|---|---|
| `excluir` | Se conserva la fila con motivo; no se abre ni vectoriza su WAV. |
| `pendiente` | Puede extraerse técnicamente; la revisión sigue pendiente. |
| `conservar` | Se respeta la aprobación humana registrada, sin borrar avisos. |
| Preprocesamiento sin salida | Se registra `no_vectorizable`, sin vector de relleno. |
| Silencio/casi cero o señal constante en actividad | No vectorizable. RMS mínimo $10^{-5}$ y variación mayor que $10^{-8}$; son controles técnicos, no reconocimiento. |
| Segmento sin ventanas | No vectorizable; no imputar, repetir ni estirar palabra. |
| Ventanas casi silenciosas internas | Se conservan y se registran; no se borra la pausa. |
| Hash, formato o detalle inconsistente | `error_entrada`, con motivo y sin índice de vector. |
| Partición `prueba` | Se difiere en este hito, sin abrir el WAV. |

Las revisiones del catálogo deben coincidir con `revisiones_aplicadas.json`.
Si `config/revisiones_audio_v1.json` cambió desde el último procesamiento, se
detiene el lote con una instrucción para actualizar el catálogo mediante el
programa existente. No se ignoran exclusiones nuevas por usar un catálogo viejo.

`revision_aprobada=True` solo refleja una decisión `conservar`; no significa
que todo el dataset esté aprobado. `estado_para_modelado` informa si faltan
revisión, tratamiento de avisos nuevos o partición. Este hito nunca declara
automáticamente un dataset listo para entrenar.

Las 150 grabaciones actuales siguen `sin_asignar`. No se ajusta nada sobre
todas ellas. Antes del hito de escalado se fijará un mapa persistente por
hablante; no se mezclarán grabaciones de una persona entre particiones ni se
reasignarán al incorporar audios.

Propuesta para discutir en ese momento: H001/H002 para entrenamiento; sumar
H003 a entrenamiento y H004/H005 a validación de desarrollo, si su historial
de uso lo permite. Reservar hablantes nuevos para prueba final independiente.
H001/H002 ya intervinieron en desarrollo. No se declara independencia de
H003–H005 porque aún falta confirmar cómo se utilizaron. Verificar forma,
integridad y finitud no equivale a usar esos hablantes para elegir parámetros
de clasificación. El mapa todavía NO se crea ni modifica en este hito.

## Archivos guardados y ampliación

`datos/caracteristicas/audio/<firma>/ejecucion_<fecha_UTC>/` contiene:

- `vectores.npz`: matriz X float64, IDs y nombres como arrays separados.
- `vectores.csv`: vista legible con ID en la primera columna; ese ID NO entra
  en el clasificador. Una fila por muestra que pudo vectorizarse.
- `catalogo_caracteristicas.csv`: todas las filas fuente, decisiones/avisos,
  estados, motivos y `fila_vector` desde cero. Fallidas/excluidas/diferidas no
  tienen índice. No emparejar matrices y catálogo por posición sin consultar ID.
- `detalle_extraccion.json`: límites, centros, segmentos, cantidades de ventanas,
  avisos y control de repetibilidad. No contiene copias de ondas de audio.
- Configuración efectiva, nombres de columnas, manifiesto, resumen, catálogo y
  revisiones de origen, procedimiento previo y copias del código utilizado.

La firma incluye configuración, código normalizado a LF, NumPy/SciPy y versión
del preprocesamiento. Cambiar método crea otra firma. Las decisiones humanas
quedan en el corte, sin convertirse en características. Repetir el comando
recalcula el catálogo en otra carpeta, preservando las ejecuciones anteriores.
No se fijan cantidades máximas de personas, sesiones o grabaciones.

Al añadir audios: capturar con el programa existente, ejecutar su preprocesado
para actualizar `actual.json` y luego volver a extraer. No hace falta llegar a
240 grabaciones. Un lote interrumpido puede dejar `.parcial`; el notebook no
lo toma como completo.

## Ejecución en Windows

Copiar los archivos del ZIP respetando las carpetas. No sustituir carpetas
completas del proyecto ni modificar los módulos anteriores.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_caracteristicas_audio.py" -v
.\.venv\Scripts\python.exe src/extraer_dataset_audio.py --verificar-repetibilidad
```

No se requiere instalación adicional ni cambio de entorno. Abrir después
`notebooks/04_caracteristicas_audio.ipynb`, seleccionar `.venv` y ejecutar sus
celdas. El notebook muestra señal y diez segmentos, ventanas, MFCC locales y
los 160 componentes. No reproduce ni incrusta WAV; se entrega sin salidas.
Antes de publicar el notebook conviene limpiar sus salidas, que sí pueden
contener gráficas derivadas de las voces.

El `.gitignore` dentro de `datos/caracteristicas/audio/` mantiene locales estas
ejecuciones. Se pueden versionar código, configuración, pruebas, notebooks y
documentación. Los vectores completos y demás derivados permanecen locales.

## Una muestra nueva utilizará la misma función

Dentro de un futuro script en `src/`, tras obtener `audio_original` y `fs_original`:

```python
import json
from pathlib import Path
import numpy as np
from preprocesamiento_audio import preprocesar_audio
from caracteristicas_audio import cargar_config, limites_desde_detalle, extraer_audio

raiz = Path(__file__).resolve().parents[1]
cfg_pp = json.loads((raiz/'config/preprocesamiento_audio_v1.json').read_text())
procesado, detalle = preprocesar_audio(audio_original, fs_original, cfg_pp)
if procesado is None:
    raise ValueError(detalle.get('motivo', 'Preprocesamiento sin salida utilizable'))
# Igual cuantización PCM16 que el guardado del dataset, sin alterar su método.
pcm = np.rint(procesado * 32768).astype(np.int16)
fs = detalle['frecuencia_procesada_hz']
limites = limites_desde_detalle(detalle, fs, len(pcm))
vector, diagnostico = extraer_audio(pcm, fs, limites, cargar_config())
# Revisar avisos de ambas etapas. El escalador/K-NN vendrán después.
```

Dataset y muestra nueva deben compartir firma del preprocesamiento, configuración
del extractor, orden de columnas y futuro escalador. No se ajustará un escalador
nuevo usando solo la muestra consultada.

## Verificación realizada en Windows y límites

El estudiante ejecutó las 13 pruebas automáticas en Windows 11 con Python
3.14.0; todas finalizaron correctamente. Luego ejecutó la extracción con
repetibilidad sobre el catálogo actualizado de 180 grabaciones. El sexto
hablante aportó 30 muestras nuevas: diez por cada comando.

La ejecución `ejecucion_20261020T191828_653873Z`, correspondiente al extractor
`audio_segmentos_v1_1caab0e82325`, produjo una matriz **180×160**. Los 28.800
valores fueron finitos y una segunda extracción por muestra produjo diferencia
máxima 0.0. Los hashes del manifiesto coinciden con todos los archivos, los IDs
y nombres están alineados y `vectores.csv` coincide exactamente con
`vectores.npz`. No aparecieron columnas constantes.

El catálogo quedó equilibrado: seis hablantes y 60 ejemplos de cada comando.
Las 180 muestras se vectorizaron, aunque 179 decisiones humanas siguen
`pendiente`, una está marcada `conservar` y todas continúan `sin_asignar`.
Vectorizar demuestra que se obtuvo un número válido; todavía no habilita la
muestra para entrenar.

Trece muestras produjeron avisos del extractor. Doce contienen entre una y 24
ventanas casi silenciosas. Esto puede corresponder a pausas internas o partes
muy débiles y se conserva para no modificar temporalmente la palabra. La muestra
`H002_S001_identificar_0009` necesitó completar con ceros una parte de una
ventana de borde. Tres de esas trece muestras también tenían avisos previos, por
lo que 13 y 28 no se suman como grupos independientes.

Los avisos no son errores y no fueron ocultados: las 13 muestras conservan un
vector y sus motivos quedan registrados. La revisión detallada está en
`documentos/verificacion_caracteristicas_audio_180.json`. No se escucharon los
WAV durante esta auditoría y no se afirma que la transcripción o calidad
auditiva sea correcta.

El estudiante decidió utilizar H006 para entrenamiento porque prevé conseguir
personas nuevas para la evaluación final. Esa decisión se aplicará mediante el
mapa persistente del hito 3, junto con las asignaciones de los demás hablantes.
No se cambió silenciosamente la columna `particion` en esta extracción.

Las pruebas verifican dimensión, orden, repetibilidad, DCT mediante una fórmula
independiente, ZCR/amplitud manuales, estadísticos por segmento, manejo de
márgenes, silencio, entradas inválidas, decisiones, hashes, filas, versiones y
reserva de prueba. El resultado de esas pruebas y de la ejecución está en
`verificacion_caracteristicas_audio_asistente.json`.

Todavía no se midió exactitud de K-NN ni capacidad de generalizar a hablantes
nuevos. Los resultados de este apartado validan extracción, trazabilidad y
repetibilidad.

## Referencias y uso de IA generativa

- Consigna `Trabajo Final 2026.pdf`, p. 4, y Clase 10, diapositivas 61–64.
- SciPy, FFT real: https://docs.scipy.org/doc/scipy/reference/generated/scipy.fft.rfft.html
- SciPy, Hann: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.windows.hann.html
- SciPy, DCT: https://docs.scipy.org/doc/scipy/reference/generated/scipy.fft.dct.html

Se utilizó ChatGPT para revisar la integración, proponer convenciones explícitas,
redactar código, pruebas y explicación. Solicitud de referencia: mantener diez
segmentos relativos con ZCR, amplitud absoluta y MFCC, respetar preprocesamiento
y revisiones, y separar vectorización de entrenamiento. Se verificaron fórmulas
con ejemplos independientes, casos límite y ejecución real sin ajustar métodos
por resultados de clasificación. El estudiante conserva la responsabilidad de
comprender y defender las decisiones del trabajo individual.
