# Trabajo Final — Inteligencia Artificial I · 2026

**Sistema de reconocimiento de huellas dactilares controlado por reconocimiento de voz**  
Ingeniería en Mecatrónica · Facultad de Ingeniería · Universidad Nacional de Cuyo

El proyecto desarrolla un agente de control de acceso basado en identidades de huellas sintéticas. El sistema deberá reconocer si una muestra corresponde a una identidad autorizada, identificarla y responder a los comandos de voz **Reconocer**, **Identificar** y **Salir**.

La consigna establece K-means con k = 3 para las identidades autorizadas, una distancia y un umbral de aceptación/rechazo, y K-NN para los comandos de voz. Este repositorio registra el desarrollo progresivo; los módulos pendientes todavía no están implementados.

## Estado del proyecto

| Etapa | Estado al 23/10/2026 | Resultado o siguiente tarea |
|---|---|---|
| Dataset de huellas sintéticas | Implementado | 220 capturas con procedencia, semillas y parámetros |
| Normalización geométrica de huellas | Implementada | Región de interés, centrado, orientación y máscaras |
| Extracción de características de huellas | Implementada y verificada | Descriptor GLCM de 144 componentes; 170 muestras de desarrollo vectorizadas y 50 de prueba reservadas |
| Dataset de comandos de voz | Disponible y ampliable | 180 grabaciones de seis hablantes |
| Preprocesamiento de audio | Implementado | 180 grabaciones procesadas: 152 sin avisos y 28 con avisos |
| Revisión auditiva registrada | Completada para el corte actual | 179 muestras con decisión conservar y una con decisión excluir |
| Extracción de características de audio | Implementada y verificada | 179 vectores de 160 componentes |
| Particiones de audio | Mapa de desarrollo definido | Seis hablantes actuales a entrenamiento; nuevas voces requieren asignación explícita |
| Verificación estadística | Implementada | Notebook 05: medias y DE por clase, separación y revisión por hablante; prueba reservada |
| Escalado y gráficos PCA | Implementados | Referencia con todas las características; PCA de huellas y audio ajustado solo con entrenamiento |
| Agrupamiento de huellas con K-means | Versión de desarrollo verificada | k = 3 sobre 72 columnas seleccionadas de 144; identificación 120/120 en entrenamiento y 30/30 en validación autorizada |
| Aceptación y rechazo de huellas | Calibrados con validación | Umbral euclidiano global 5.292172576: 29/30 autorizadas aceptadas y 0/20 intrusos aceptados; prueba reservada |
| Clasificación de comandos con K-NN | Desarrollo implementado y documentado | 160 columnas; k=1; CV LOSO de selección 169/179; validación con nuevas personas pendiente |
| Prueba práctica de voz | Ejecutada en Windows | Voz conocida: 15/15 comandos; ensayo sintético adicional documentado por separado |
| Integración del agente | Pendiente | Conexión entre comandos de voz y reconocimiento de huellas |
| Evaluación final e informe | Pendiente | Resultados con datos reservados, conclusiones y defensa |

El extractor de huellas añade acondicionamiento de contraste y cuantización a la normalización geométrica anterior. La versión actual utiliza textura en escala de grises, sin binarización ni esqueletizado.

Se verificaron integridad, dimensiones, repetibilidad y funcionamiento del código, y se midieron identificación y rechazo en desarrollo. La calibración usa la misma validación con la que se informa su resultado; todavía no se realizó una evaluación final independiente. Las variantes de unas pocas bases sintéticas no prueban generalización a huellas reales.

## Lectura recomendada

1. [Bitácora de dataset y normalización](notebooks/01_bitacora_dataset_normalizacion.ipynb): decisiones, archivos, resultados y comprobaciones ejecutadas.
2. [Índice de documentación](documentos/README.md): estado vigente y antecedentes de cada etapa.
3. [Bitácora de audio](notebooks/02_dataset_audio_preprocesamiento.ipynb): captura, método, resultados y límites de la primera versión.
4. [Uso de IA generativa](documentos/uso_ia_generativa.md): tareas asistidas, ejemplos de solicitudes y verificación.
5. [Bitácora de PCA, K-means y rechazo](notebooks/06_clusterizacion_pca.ipynb): referencia de 144 columnas, mejora a 72 y calibración; consulta de solo lectura con evidencias incluidas.
6. [Bitácora de PCA y K-NN de audio](notebooks/07_pca_knn_audio.ipynb): método, evaluación por hablante, pruebas con micrófono y cierre de desarrollo; lectura sin entrenar ni grabar.

## Dataset de huellas

Se utilizan siete bases de Anguli: tres identidades autorizadas y cuatro intrusas. El conjunto contiene **220 capturas: 120 de entrenamiento, 50 de validación y 50 de prueba**. Las ampliaciones incorporan deformaciones locales, cambios de calidad y rotaciones hasta ±90°. No se utilizan huellas reales.

Las identidades autorizadas comparten sus bases entre particiones para representar capturas distintas de dedos conocidos. Los intrusos de validación y prueba son identidades distintas. La diversidad se limita a siete bases; no se afirma generalización a datos reales.

## Entorno y consulta de resultados

El entorno registrado para la normalización publicada es Python 3.14.0. Las versiones de las bibliotecas están en `requirements.txt` y en el registro de ejecución.

Desde PowerShell, en la raíz del repositorio, si aún no existe un entorno virtual:

```powershell
py -3.14 -m venv .venv
```

Instalar dependencias en ese entorno:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install ipykernel
```

`ipykernel` es una dependencia adicional para ejecutar notebooks. En VS Code, seleccionar el intérprete de `.venv`, abrir la bitácora y ejecutar sus celdas. El notebook solo lee archivos. Las salidas guardadas de la bitácora de huellas permiten consultarla en GitHub sin instalar Python. El notebook 02 conserva su corte histórico. La bitácora 07 incluye salidas verificadas y figuras de las ejecuciones Windows de voz.

**El repositorio incluye las imágenes de huellas, los audios originales y procesados, y sus catálogos. Las matrices de características generadas permanecen locales y pueden reproducirse ejecutando los extractores.**

## Organización

| Ruta | Contenido |
|---|---|
| `src/` | Generación, captura, preprocesamiento, extracción y modelos de desarrollo |
| `config/` | Configuraciones de las etapas |
| `datos/bases/` | Bases de Anguli y archivos de procedencia |
| `datos/originales/` | Las 220 capturas anteriores a la normalización |
| `datos/procesados/normalizacion_final_v1/` | Representaciones finales, máscaras, catálogo y controles |
| `datos/audio/` | Audios originales y procesados, catálogos y registros publicados |
| `datos/caracteristicas/` | Ejecuciones locales de vectorización, matrices y registros de procedencia |
| `notebooks/` | Bitácoras de avances y análisis reproducibles |
| `documentos/` | Instrucciones, decisiones y registros de apoyo |

`resultados/` y `datos/procesados/conjunto_v1/` corresponden a salidas intermedias locales que no se incluyen en esta publicación. Se pueden reconstruir con los programas correspondientes; no se requieren para la verificación final del notebook.

Los modelos y ejecuciones completas de PCA, mejora y rechazo permanecen locales bajo `resultados/`. Una selección de tablas, resúmenes y gráficos de las ejecuciones reales de Windows se publica en [`documentos/resultados_etapa06/`](documentos/resultados_etapa06/) para consultar el notebook 06 sin regenerar modelos. Se conservan también los parámetros NPZ/JSON congelados de rechazo en ese registro; son los usados en la calibración, no resultados de prueba.

El catálogo vigente es [`catalogo_normalizado.csv`](datos/procesados/normalizacion_final_v1/catalogo_normalizado.csv). Para las siguientes etapas se utilizan las columnas **normalizada** y **alternativa_180**. La columna heredada `procesado` conserva rutas del procesamiento preliminar; esas imágenes no se distribuyen en esta versión.

Por muestra se guardan tres PNG: imagen normalizada, alternativa a 180° y máscara de región. Representan **una sola muestra**. La dirección del eje es ambigua en 180°; el futuro comparador deberá contemplar ambas orientaciones o ser invariante a ese giro.

## Normalización de nuevas ejecuciones

La función reutilizable está en `src/normalizacion_final.py`. Para aplicar el procedimiento a los originales publicados y escribir una salida nueva:

```powershell
.\.venv\Scripts\python.exe src/normalizar_todas.py --salida normalizacion_verificacion
```

La carpeta indicada no debe existir. Los originales se conservan. Para que el notebook revise una salida alternativa se debe ajustar su variable `NOMBRE_SALIDA`.

## Reproducción completa desde las bases

En una copia de trabajo independiente que contenga `src/`, `config/`, las dependencias y `datos/bases/`, pero sin catálogos ni salidas generadas:

```powershell
.\.venv\Scripts\python.exe src/generar_conjunto.py
.\.venv\Scripts\python.exe src/ampliar_entrenamiento.py
.\.venv\Scripts\python.exe src/ampliar_rotaciones.py
.\.venv\Scripts\python.exe src/normalizar_todas.py
```

La ejecución sigue ese orden. Los generadores reutilizan funciones del piloto, por lo que deben conservarse todos los módulos de `src/`. No ejecutar la secuencia sobre las salidas publicadas: los programas rechazan carpetas existentes. La reproducción desde las bases PNG no requiere instalar Anguli; generar nuevamente las bases sí requiere su generador y configuración.

## Resultados del avance y límites

La ejecución publicada procesó 220 muestras: 218 sin avisos, 2 para revisión y 0 errores. Los avisos de A01_M43 y A02_M44 corresponden a regiones que alcanzan un borde del original. El notebook verifica integridad, particiones, dimensiones y la alternativa de 180°; estos controles no miden la precisión de reconocimiento.

La normalización actual conserva la escala en píxeles, sin igualar contraste, corregir deformaciones elásticas ni establecer una dirección anatómica única. El conjunto de prueba se reserva para evaluación final. La bitácora documenta el desarrollo; no sustituye el informe final en PDF exigido por la consigna.

## Captura de comandos de voz — primer hito (17/10/2026)

Se incorpora un grabador de consola para **reconocer**, **identificar** y **salir**.
Las clases son las palabras; H001, H002, etc. identifican hablantes para organizar
la futura evaluación por persona. No hay cantidades fijas de participantes o muestras.

Desde PowerShell, en la raíz del proyecto y usando el entorno existente:

```powershell
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-audio.txt
.\.venv\Scripts\python.exe src/grabar_audio.py
```

Las dependencias de captura están separadas en `requirements-audio.txt`; se mantiene
el NumPy de huellas y no se modifica `requirements.txt`. Los datos se crean en
`datos/audio/`, excluido de Git por defecto. La configuración está en
`config/audio_v1.json`. No se capturan datos antes de confirmar y finalizar la
cuenta regresiva. El programa no implementa K-NN ni escucha continua.

La [documentación de audio](documentos/dataset_audio.md) explica flujo, numeración,
metadatos, limitaciones y prueba local. El
[notebook de revisión](notebooks/02_dataset_audio_preprocesamiento.ipynb) lee
las capturas cuando existen y presenta un resumen textual del corte de 150 muestras.
No incorpora voces ni salidas de ejecución; la reproducción local es opcional.
Las pruebas automáticas de archivos no sustituyen la verificación de micrófono
y reproducción en Windows.

## Preprocesamiento de audio — segundo hito (17/10/2026)

La etapa conserva originales y genera WAV mono a 16 kHz con recorte de silencios
externos y amplitud controlada. No implementa características acústicas ni K-NN.
Usa NumPy y SciPy del entorno registrado, sin dependencias nuevas.

```powershell
.\.venv\Scripts\python.exe src/preprocesar_dataset_audio.py
```

Repetir el comando procesa nuevas muestras y verifica/omite resultados existentes
de la misma versión. La configuración está en `config/preprocesamiento_audio_v1.json`.
Las decisiones humanas se registran en `config/revisiones_audio_v1.json` y no borran
avisos. Los cambios de método generan otra carpeta versionada conservando las anteriores.

La [documentación del hito](documentos/preprocesamiento_audio.md) explica método,
metadatos y límites. El notebook 02 compara los originales y procesados. El
procesamiento local en Windows quedó registrado con 150 muestras de H001–H005:
127 sin avisos y 23 con avisos. Repetir el lote verificó y omitió los 150 resultados,
sin nuevas salidas; la verificación de originales informó integridad coherente.
La revisión auditiva individual se registra por separado y no se presume completa.

Este corte cierra la documentación de captura y preprocesamiento v1 y permite
iniciar la extracción de características. La recolección continúa hasta incorporar
al menos ocho hablantes como meta inicial, sin cupos máximos. Las 150 muestras siguen
`sin_asignar`: antes de entrenar y evaluar se fijará un mapa persistente por hablante.
H001/H002 se utilizaron en el desarrollo; las voces usadas para elegir parámetros
no deberán considerarse prueba final independiente. Se reservarán personas nuevas
para la evaluación final y se documentarán por separado las demostraciones.

Los 15 avisos en captura describen los originales. En procesamiento se informaron
15 picos cercanos al límite original, 6 amplificaciones limitadas y 2 actividades
cercanas al final. Un aviso no implica descarte automático. El detalle y los límites
se registran en la documentación y en el notebook.

Antes de publicar un notebook, revisar sus salidas. La opción `REPRODUCIR_AUDIO=False` evita incrustar reproducciones durante la ejecución habitual. Los audios y catálogos están versionados en el repositorio; las ejecuciones de características permanecen locales según sus reglas de exclusión. Mantener también una copia de respaldo del trabajo local.

## Cierre de extracción de características — 20/10/2026

Los apartados anteriores de captura y preprocesamiento conservan los resultados históricos de sus primeras ejecuciones. El estado vigente incorpora 180 grabaciones de seis hablantes y la revisión auditiva registrada.

### Huellas

El extractor genera un vector de 144 características mediante matrices de coocurrencia con máscara. Combina tres bloques espaciales, tres distancias, cuatro direcciones y cuatro medidas de textura.

La extracción de desarrollo produce una matriz de **170 × 144**: 120 muestras de entrenamiento y 50 de validación. Las otras 50 muestras permanecen reservadas para prueba. La comparación entre cada imagen y su giro exacto de 180°, girando también la máscara, produjo una diferencia máxima de 0.

### Audio

El extractor describe cada palabra mediante diez segmentos relativos, con medidas de cruces por cero, amplitud absoluta y MFCC. Produce 160 características por grabación.

Las revisiones registran **179 muestras conservadas y una excluida**, `H006_S001_salir_0005`. La matriz vigente contiene **179 × 160** valores: 60 ejemplos de reconocer, 60 de identificar y 59 de salir. Las 180 filas del catálogo siguen sin partición asignada.

La repetición de la extracción produjo una diferencia máxima de 0. Los avisos técnicos se conservan aunque una muestra tenga decisión humana de conservar.

### Verificación y alcance

En una copia del repositorio, el asistente ejecutó las 51 pruebas automáticas existentes y regeneró ambos conjuntos de vectores. Todas las pruebas aprobaron y todos los valores generados fueron finitos. Esta comprobación no incluyó una nueva escucha de las grabaciones; las decisiones auditivas corresponden a la revisión registrada por el autor.

Al cerrar ese hito de extracción del 20/10 todavía no se habían ajustado escaladores, PCA, K-means ni K-NN. Los avances posteriores de PCA, K-means y rechazo se registran en el cierre de desarrollo de esta misma página. La extracción correcta, por sí sola, no demuestra separación de clases ni precisión de reconocimiento.

### Documentación de esta etapa

- [Características de huellas](documentos/caracteristicas_huellas_hito1.md).
- [Características de audio](documentos/caracteristicas_audio_hito2.md).
- [Guía de vectorización y clasificación](documentos/guia_vectorizacion_y_clasificacion.md).
- [Notebook de huellas](notebooks/03_caracteristicas_huellas.ipynb).
- [Notebook de audio](notebooks/04_caracteristicas_audio.ipynb).

## Verificación estadística antes de PCA — 22/10/2026

El [notebook 05](notebooks/05_verificacion_estadistica.ipynb) compara **cada columna**
entre muestras de una clase: identidad en huellas y palabra en audio. Exporta cantidades,
medias, desviaciones muestrales (`ddof=1`), controles e indicador de separación,
y muestra valores individuales y media ± DE para columnas con separación baja,
mediana y alta. No ajusta modelos ni selecciona automáticamente características.

El análisis principal de huellas utiliza únicamente entrenamiento autorizado.
El [mapa de audio](config/particiones_audio_v1.json) destina H001–H006 a entrenamiento
para aprovechar el corte actual en desarrollo. La partición se aplica como una capa
explícita en el notebook: el catálogo histórico conserva `sin_asignar`. Las futuras
etapas deben reutilizar el mapa, sin interpretar el catálogo histórico como asignación
vigente. Un hablante nuevo o una contradicción bloquean el uso hasta una decisión explícita.

La clase de voz es el comando, no la persona. El objetivo sigue siendo reconocer las
palabras de voces nuevas. Se reservarán personas nuevas para validación y prueba final;
actualmente no hay prueba independiente de audio. La demostración con una voz ya usada
no mide generalización a hablantes desconocidos. H001/H002 participaron en desarrollo.

Las matrices pueden regenerarse con los extractores existentes. Abrir el notebook 05
con el kernel `.venv` y ejecutar sus celdas. Las salidas se guardan en una carpeta nueva
bajo `resultados/verificacion_estadistica/`. Las cantidades no están fijadas en código.
Ver [método, instrucciones y resultados del asistente](documentos/verificacion_estadistica.md).
Los párrafos anteriores conservan sus cortes históricos.

## Cierre de desarrollo: PCA, K-means y rechazo — 22/10/2026

La [bitácora 06](notebooks/06_clusterizacion_pca.ipynb) documenta el recorrido completo,
incluyendo la referencia inicial que mezclaba A01/A03. Los identificadores de ejecución
están en UTC: algunos comienzan con 20261023 aunque el trabajo se realizó el 22/10 en Argentina.

| Medida de desarrollo | Referencia 144 columnas | Selección 72 columnas |
|---|---:|---:|
| Identificación sin rechazo en entrenamiento | 79/120 | 120/120 |
| Identificación sin rechazo en validación autorizada | 21/30 | 30/30 |
| ARI de validación autorizada | 0.5436 | 1.0000 |

La selección conserva la mejor mitad según separación entre identidades respecto de
variación interna. Se eligió entre tres variantes mediante CV interna de entrenamiento,
recalculando selección y escalado dentro de cada pliegue. Esa selección es supervisada;
K-means recibe solo los vectores y mantiene k=3. No se cambiaron las bases ni se descartaron capturas.

El modelo congelado usa distancia euclidiana en 72 columnas estandarizadas. El umbral
global, calibrado con 30 autorizados y 20 intrusos de validación, es **5.292172576**:
acepta 29/30 autorizados y 0/20 intrusos. A02_M22 es el falso rechazo conservado.
FAR observada=0 %, FRR=3.33 %; son resultados de la misma calibración y no de prueba final.
Los intrusos analizados provienen de dos bases; no se afirma seguridad biométrica real.

La bitácora lee [evidencias de las ejecuciones Windows](documentos/resultados_etapa06/README.md)
y puede ejecutarse sin regenerar matrices o modelos. Para reproducir los análisis completos:

```powershell
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-clusterizacion.txt
.\.venv\Scripts\python.exe src/extraer_dataset_huellas.py
.\.venv\Scripts\python.exe src/extraer_dataset_audio.py
.\.venv\Scripts\python.exe src/clusterizacion_pca.py
.\.venv\Scripts\python.exe src/mejorar_clusterizacion_huellas.py
.\.venv\Scripts\python.exe src/calibrar_rechazo_huellas.py
```

Esta secuencia crea cortes nuevos: no hace falta repetirla para leer la bitácora o
reutilizar el modelo publicado. No utilizar `--incluir-prueba` durante desarrollo.
La inferencia de un vector nuevo con el modelo y umbral congelados está documentada en
[cierre_etapa06.md](documentos/cierre_etapa06.md). Las 51 candidatas son valores de umbral,
no muestras ni grupos; la cantidad se deriva de las distancias observadas.

Se conserva esta versión de desarrollo para continuar con voz, integración y planificación
de la evaluación final. No se sigue ajustando para forzar cero errores en validación.


## Cierre de desarrollo: PCA y K-NN de audio — 23/10/2026

La [bitácora 07](notebooks/07_pca_knn_audio.ipynb) conserva las 160 características
originales. StandardScaler y PCA se ajustan con entrenamiento; PCA solo visualiza,
sin intervenir en K-NN. PC1+PC2 explican 27,75 % de varianza; 52 componentes alcanzan
95 %. No se reduce a la mitad el vector ni se utiliza K-means para audio.

Se compararon k=1,3,5,7 con voto uniforme o por distancia, dejando fuera un
hablante por vez (LOSO) y ajustando el escalador dentro de cada pliegue. La mejor
opción fue k=1 uniforme: 169/179 aciertos (94,41 %), frente a 165/179 con k=5
uniforme. Son métricas de selección interna, no prueba final independiente.
Se conservan los diez errores y las revisiones vigentes, sin eliminar audios válidos.

El modelo fijo se probó en Windows con 15 comandos nuevos de H001: 15/15 aciertos.
Una palabra desconocida se interpretó como salir; un intento de silencio no generó
vector. Es una demostración con voz conocida, no generalización a personas nuevas.
El ensayo adicional de cuatro voces sintéticas reproducidas desde un celular
se documenta como exploración: 14/17 intentos; 14/16 audios efectivamente reproducidos
tras aclarar un inicio fuera de tiempo. No sustituye validación humana.

La documentación y evidencia seleccionada están en
[cierre_etapa07.md](documentos/cierre_etapa07.md) y
[resultados_etapa07/README.md](documentos/resultados_etapa07/README.md).
El notebook puede consultarse sin WAV ni matrices locales y no vuelve a entrenar.
Para reproducir el ajuste o realizar otra prueba con las herramientas ya instaladas:

```powershell
.\.venv\Scripts\python.exe src/knn_audio.py
.\.venv\Scripts\python.exe src/probar_knn_audio.py --hablante H001
.\.venv\Scripts\python.exe src/diagnosticar_knn_audio.py
```

Cada programa tiene un propósito distinto: ajustar el modelo, consultar el modelo
guardado o diagnosticar los errores LOSO. Las consultas no se agregan al entrenamiento.
Para reutilizar una corrida determinada, pasar `--modelo "resultados/knn_audio/FECHA"`
a los dos últimos. No ejecutar nuevamente el ajuste para cada consulta.

Se cierra la implementación y documentación de desarrollo de esta etapa. Quedan
pendientes validación con personas nuevas, rechazo de palabras desconocidas si se
requiere en la aplicación, integración del agente y evaluación final reservada.
Las fechas de carpetas están en UTC; la primera corrida K-NN 20261023T033845Z
corresponde al 23/10/2026 00:38 en Argentina.
