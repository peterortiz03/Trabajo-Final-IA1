# Preprocesamiento de comandos de voz — versión 1

## Objetivo y alcance

Este hito transforma cada original en una representación temporal común: WAV mono,
16 kHz, PCM16, con recorte conservador de silencios externos y amplitud controlada.
No clasifica palabras, no extrae MFCC ni implementa K-NN. No iguala la duración de
las palabras. La captura sigue activándose manualmente.

La implementación se desarrolló con H001 y H002 como hablantes de desarrollo.
No deben utilizarse como prueba final independiente después de ajustar decisiones
con sus muestras. Las particiones continúan `sin_asignar`; se asignarán mediante
un mapa persistente por hablante en una etapa posterior, reservando otras voces.
No se aprende un escalador global de este dataset: cada audio se procesa por
separado con una configuración común.

## Archivos y uso en Windows

- `src/preprocesamiento_audio.py`: funciones sin efectos de escritura, reutilizables.
- `src/preprocesar_dataset_audio.py`: ejecución incremental, versiones y catálogos.
- `config/preprocesamiento_audio_v1.json`: parámetros de señal.
- `config/revisiones_audio_v1.json`: decisiones humanas, independientes de los avisos.
- `notebooks/02_dataset_audio_preprocesamiento.ipynb`: conteos, avisos y comparación.
- `tests/test_preprocesamiento_audio.py`: casos de señal y persistencia con fixtures temporales.

Se utilizan NumPy 2.3.5 y SciPy 1.17.0, ya registrados en `requirements.txt`.
No se cambia el entorno de huellas ni se agrega una dependencia de procesamiento.
El notebook requiere Matplotlib e IPython mediante el kernel ya preparado.

Desde PowerShell, en la raíz del repositorio, cerrar primero el grabador:

```powershell
.\.venv\Scripts\python.exe -c "import numpy, scipy; print('NumPy', numpy.__version__, 'SciPy', scipy.__version__)"
.\.venv\Scripts\python.exe src/preprocesar_dataset_audio.py
.\.venv\Scripts\python.exe src/preprocesar_dataset_audio.py
.\.venv\Scripts\python.exe src/grabar_audio.py --verificar
```

La segunda ejecución debe informar cero nuevos y tantos omitidos como resultados
ya existentes y válidos. Después de capturar otra tanda, ejecutar el mismo comando.
No ejecutar captura y preprocesamiento simultáneamente: comparten un bloqueo local.

## Procedimiento matemático

### Lectura, mono y referencia de amplitud

Se valida el WAV PCM16 y se convierte `x = PCM16 / 32768` a flotantes. En estéreo,
se promedian los canales. Se registra un aviso si el promedio reduce mucho la
energía respecto del canal de mayor nivel, ya que podría haber cancelación.
Las medidas de picos y saturación se toman antes de transformar la señal.
Opcionalmente se resta la media para quitar un desplazamiento constante.
Esto no constituye un filtro de reducción de ruido.

### Remuestreo

Se usa `scipy.signal.resample_poly` con filtro FIR paso bajo y ventana Kaiser.
Para 48 kHz a 16 kHz la relación es 1/3. El filtrado antialias evita que componentes
por encima de la nueva banda se plieguen dentro de ella. Cambiar solo la frecuencia
en el encabezado del WAV alteraría la velocidad y no sería un remuestreo correcto.

### Estimación de actividad y recorte

Se mide energía RMS en ventanas de 20 ms con avance de 10 ms:

$$E_k = \sqrt{\frac{1}{N}\sum_{n=0}^{N-1}x_k[n]^2},\qquad L_k = 20\log_{10}(E_k).$$

El percentil 20 de los niveles estima un piso de energía. No es una medición
independiente del ruido ni una relación señal/ruido real. Se aplican dos umbrales:

$$T_f=\max(-42,\ P_{20}+12),\qquad T_d=\max(-48,\ P_{20}+6)\quad[\mathrm{dBFS}].$$

El umbral fuerte aporta evidencia de actividad y el débil ayuda a conservar
sonidos menos intensos. Se unen huecos de hasta 120 ms. Se conservan islas de al
menos 60 ms que contienen algún cuadro sobre el umbral fuerte; se requieren al
menos 120 ms de actividad estimada en total. Se conserva desde la primera hasta
la última isla, sin quitar silencios internos. Se agregan **150 ms de margen**
a cada extremo, limitados por el principio y el final disponibles del archivo.

El método puede confundir golpes o ruido no estacionario con voz y puede pasar
por alto sonidos débiles. Los márgenes y umbrales se revisan escuchando muestras
de desarrollo. No afirmar que un resultado sin avisos contiene la palabra correcta.
Un audio sin suficiente actividad queda `sin_salida_revisar`, sin amplificarlo ni
borrar su original. Puede tratarse de silencio, ruido o voz que el método no detectó.

### Normalización controlada

Sobre el recorte se calcula una ganancia:

$$g=\min\left(\frac{0.8}{\max|x|},\ 10^{6/20}\right),\qquad y=gx.$$

El pico objetivo es 0.8 de escala completa; la amplificación máxima es +6 dB
(aproximadamente multiplicar por 2). Si esa ganancia no alcanza el objetivo se
registra `amplificacion_limitada`; no es automáticamente un error. La atenuación
sí puede superar 6 dB si hace falta. La normalización se aplica solo después de
la estimación de actividad y no repara saturación del original.

## Estados y decisiones de revisión

| Estado | Interpretación |
|---|---|
| `procesado` | Se generó un WAV sin avisos automáticos nuevos. No certifica aptitud para entrenamiento. |
| `procesado_con_avisos` | Se generó un WAV que requiere atención a los avisos. |
| `sin_salida_revisar` | No hubo suficiente actividad según la heurística; original conservado, sin WAV procesado. |
| `error` | Falló una comprobación de procesamiento; motivo en el detalle. |

Los problemas de integridad del catálogo/originales se detectan antes del lote
y detienen la ejecución para evitar procesar datos incoherentes.

Los picos cercanos a la escala completa, posible saturación, actividad próxima a
los bordes o ganancia limitada no provocan descarte automático. Un archivo con
actividad en el borde puede contener una palabra completa. La configuración de
revisiones incluye `H002_S001_identificar_0009` con decisión `conservar`, basada en
la escucha confirmada por el autor el 17/10/2026. El aviso automático se mantiene.

Para otra decisión, agregar el ID exacto en `config/revisiones_audio_v1.json` con
`decision` (`conservar`, `excluir` o `pendiente`) y `motivo`. Volver a ejecutar el
lote actualiza esa revisión sin recalcular WAV. `excluir` registra una decisión para
la futura selección de entrenamiento; no elimina originales ni procesados.
El programa de entrenamiento futuro deberá respetar esas decisiones. En este hito
no se entrena ni se considera apta automáticamente ninguna toma.

## Versiones y ejecución incremental

Cada configuración, código de procesamiento/ejecución y versión de NumPy/SciPy
produce una firma. La salida se organiza en:

- `datos/audio/procesados/audio_preprocesamiento_v1_<firma>/procedimiento.json`
- `.../muestras/<muestra_id>/audio.wav`
- `.../muestras/<muestra_id>/resultado.json`
- `.../catalogo_procesado.csv`
- `.../resumen.json`
- `.../revisiones_aplicadas.json`

`datos/audio/procesados/actual.json` identifica el catálogo activo para el notebook.
Cambiar parámetros, código o versiones de bibliotecas genera otra carpeta; no
mezcla procesados viejos con nuevos ni reemplaza versiones anteriores. Se informa
al iniciar. La normalización CRLF/LF del código no altera la firma.

Si un resultado ya existe, se comprueban su referencia al original y el hash y
formato del WAV antes de omitirlo. Un resultado alterado detiene el lote y se
conserva para revisión. No se repara sobreescribiéndolo silenciosamente.

Cada muestra se prepara en una carpeta temporal y se confirma con un renombrado.
Los catálogos agregados se reconstruyen desde los resultados confirmados. Si se
interrumpe una tanda, repetir el comando reconstruye los temporales y consolida
los catálogos sin duplicar resultados. La carpeta de trabajo debe ser local;
no operar sobre ella con varios equipos o sincronizaciones simultáneas.

## Metadatos y compatibilidad con captura

En `datos/audio/metadatos.csv` solo se actualizan `ruta_procesada` y
`estado_procesamiento`. Los campos de frecuencia, canales, duración, avisos,
configuración y hash siguen describiendo el **original**. No se cambian etiquetas,
hablantes, sesiones o particiones. Esto mantiene la compatibilidad del grabador.

El catálogo por versión amplía esos registros con frecuencia/duración procesadas,
límites de recorte, ganancia, hash de salida, firma, avisos nuevos y revisión humana.
El JSON individual conserva el detalle y el entorno de ejecución. La revisión
humana es un registro aparte y nunca borra la evidencia automática.

## Antecedente de verificación — piloto de 60 muestras

Pruebas realizadas en el entorno del asistente el 17/10/2026:

- Linux, Python 3.12.14, NumPy 2.3.5 y SciPy 1.17.0.
- 27 pruebas aprobadas: 11 del grabador y 16 nuevas de señal/incrementalidad.
- Casos de silencio, ruido estacionario, impulso, estéreo/cancelación, datos no
  finitos, conservación de frecuencia, antialias, recorte, bordes y ganancia.
- Pruebas de nueva captura después de procesar, omisión sin reescritura, cambio
  de configuración, interrupciones y detección de procesados modificados.
- En una copia de los 60 originales: 60 WAV procesados mono/16 kHz/PCM16;
  52 sin avisos y 8 con avisos. Ningún original modificado ni eliminado.
- Los 8 avisos por muestra corresponden a seis picos cercanos al límite original,
  una amplificación limitada (H002 identificar 0006) y una actividad cercana al
  final (H002 identificar 0009). No son ocho rechazos.
- Duraciones procesadas entre 0.69 y 1.96 s, sin estirar el contenido.
- Segunda ejecución: 0 nuevos y 60 omitidos; integridad de los originales verificada.

Las pruebas de señal no son datos de entrenamiento. Los controles de archivos no
sustituyen escuchar el antes y después. La ejecución posterior en Windows amplió el conjunto a cinco personas, como
se registra a continuación. La validación auditiva individual se documenta por
separado. No se midió precisión de reconocimiento.

## Registro de avance — 20/10/2026

La primera versión documentada reúne **150 tomas de cinco hablantes (H001–H005)**:
10 por comando y persona, 30 por persona y 50 por clase. La recolección permanece
abierta; la meta inicial es incorporar al menos ocho personas, sin establecer un
máximo ni suponer que esa cantidad garantiza precisión de reconocimiento.

| Hablante | Reconocer | Identificar | Salir | Total | Con avisos en captura |
|---|---:|---:|---:|---:|---:|
| H001 | 10 | 10 | 10 | 30 | 2 |
| H002 | 10 | 10 | 10 | 30 | 4 |
| H003 | 10 | 10 | 10 | 30 | 4 |
| H004 | 10 | 10 | 10 | 30 | 3 |
| H005 | 10 | 10 | 10 | 30 | 2 |
| **Total** | **50** | **50** | **50** | **150** | **15** |

El CSV entregado contiene 150 identificadores únicos y 150 hashes originales
distintos. Las 150 filas tienen ruta procesada y permanecen `sin_asignar`.
La ejecución local en Windows informó **150 originales y metadatos coherentes**.
Esta evidencia proviene del catálogo y de la salida de terminal aportada por el
autor; la revisión documental no volvió a calcular hashes sobre los WAV.

El procedimiento activo es `audio_preprocesamiento_v1_3f3a7a105289`:

| Resultado de la ejecución local | Cantidad |
|---|---:|
| Procesados sin avisos | 127 |
| Procesados con avisos | 23 |
| Nuevos en la repetición del lote | 0 |
| Resultados existentes verificados y omitidos | 150 |

La terminal registró 15 avisos `picos_cercanos_al_limite_original`, 6
`amplificacion_limitada` y 2 `actividad_cerca_del_final`. Los avisos de captura
(15 tomas) y los de procesamiento (23 tomas) corresponden a controles diferentes;
no se suman como si fueran muestras distintas. Los tipos de aviso pueden
coexistir en una misma toma en futuras ejecuciones.

Estos conteos verifican el avance de captura y procesamiento; no son tasas de
acierto ni certifican que las 150 tomas sean aptas para entrenar. La configuración
de revisión recibida registra explícitamente la conservación de
`H002_S001_identificar_0009`, cuya palabra fue confirmada completa por escucha.
Conservar otras tomas al grabarlas no equivale a registrar la revisión de su
recorte procesado. No se declara terminada la revisión auditiva individual de
los 23 resultados con avisos.

## Revisión local y siguiente paso

Abrir el notebook con el kernel del proyecto y ejecutar las celdas. Revisar al
menos una muestra de cada comando de cada persona y las muestras con avisos.
Escuchar especialmente consonantes iniciales/finales, ausencia de cambios de
velocidad, volumen cómodo y márgenes. No modificar parámetros solo para reducir
el número de avisos. Si se modifica el método, revisar otra vez el conjunto de
desarrollo con la nueva versión.

Continuar capturando otras personas y volver a ejecutar el mismo comando cuando
haya nuevas tandas. La prueba final usará hablantes reservados: aplicar el método
ya fijado y no usar esos datos para elegir umbrales o características. La futura
extracción acústica y K-NN tendrán otro hito.

Los audios y catálogos permanecen ignorados por Git. Hacer copia local de
`datos/audio/`. Un notebook ejecutado puede incrustar audio en las salidas:
limpiarlas antes de publicarlo. El notebook se distribuye con
`REPRODUCIR_AUDIO=False`; habilitarlo solo para la revisión local y limpiar después
las salidas. El cierre de documentación no supone una partición definitiva ni
una aprobación automática del dataset para entrenamiento.

## Referencias y uso de IA

- SciPy 1.17.0, `resample_poly`: https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.signal.resample_poly.html
- Consigna Trabajo Final 2026, módulo de voz mediante K-NN, página 4.
- Separación de ajuste y evaluación: https://scikit-learn.org/stable/common_pitfalls.html#data-leakage

Diseño e implementación asistidos por IA generativa. La verificación incluye
pruebas de casos conocidos y análisis de los originales de desarrollo. La escucha
humana confirmada y las pruebas del asistente se registran por separado. Los
umbrales son decisiones iniciales de este proyecto, no valores universales.
