# Trabajo Final — Inteligencia Artificial I · 2026

**Sistema de reconocimiento de huellas dactilares controlado por reconocimiento de voz**  
Ingeniería en Mecatrónica · Facultad de Ingeniería · Universidad Nacional de Cuyo

El proyecto desarrolla un agente de control de acceso basado en identidades de huellas sintéticas. El sistema deberá reconocer si una muestra corresponde a una identidad autorizada, identificarla y responder a los comandos de voz **Reconocer**, **Identificar** y **Salir**.

La consigna establece K-means con k = 3 para las identidades autorizadas, una distancia y un umbral de aceptación/rechazo, y K-NN para los comandos de voz. Este repositorio registra el desarrollo progresivo; los módulos pendientes todavía no están implementados.

## Estado del proyecto

| Etapa | Estado al 22/10/2026 | Resultado o siguiente tarea |
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
| Escalado y gráficos PCA | Pendiente | Ajuste sobre entrenamiento y exploración de los vectores |
| Agrupamiento de huellas con K-means | Pendiente | k = 3, correspondencia entre grupos e identidades y umbral de rechazo |
| Clasificación de comandos con K-NN | Pendiente | Entrenamiento y evaluación con separación por hablante |
| Integración del agente | Pendiente | Conexión entre comandos de voz y reconocimiento de huellas |
| Evaluación final e informe | Pendiente | Resultados con datos reservados, conclusiones y defensa |

El extractor de huellas añade acondicionamiento de contraste y cuantización a la normalización geométrica anterior. La versión actual utiliza textura en escala de grises, sin binarización ni esqueletizado.

Las comprobaciones realizadas verifican integridad, dimensiones, repetibilidad y funcionamiento del código. Todavía no se ha medido la precisión de reconocimiento ni la capacidad de generalización de los modelos.

## Lectura recomendada

1. [Bitácora de dataset y normalización](notebooks/01_bitacora_dataset_normalizacion.ipynb): decisiones, archivos, resultados y comprobaciones ejecutadas.
2. [Índice de documentación](documentos/README.md): estado vigente y antecedentes de cada etapa.
3. [Bitácora de audio](notebooks/02_dataset_audio_preprocesamiento.ipynb): captura, método, resultados y límites de la primera versión.
4. [Uso de IA generativa](documentos/uso_ia_generativa.md): tareas asistidas, ejemplos de solicitudes y verificación.

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

`ipykernel` es una dependencia adicional para ejecutar notebooks. En VS Code, seleccionar el intérprete de `.venv`, abrir la bitácora y ejecutar sus celdas. El notebook solo lee archivos. Las salidas guardadas de la bitácora de huellas permiten consultarla en GitHub sin instalar Python. La bitácora de audio se publica sin salidas y contiene un resumen textual fechado.

**El repositorio incluye las imágenes de huellas, los audios originales y procesados, y sus catálogos. Las matrices de características generadas permanecen locales y pueden reproducirse ejecutando los extractores.**

## Organización

| Ruta | Contenido |
|---|---|
| `src/` | Generación, captura, preprocesamiento y extracción de características |
| `config/` | Configuraciones de las etapas |
| `datos/bases/` | Bases de Anguli y archivos de procedencia |
| `datos/originales/` | Las 220 capturas anteriores a la normalización |
| `datos/procesados/normalizacion_final_v1/` | Representaciones finales, máscaras, catálogo y controles |
| `datos/audio/` | Audios originales y procesados, catálogos y registros publicados |
| `datos/caracteristicas/` | Ejecuciones locales de vectorización, matrices y registros de procedencia |
| `notebooks/` | Bitácoras de avances y análisis reproducibles |
| `documentos/` | Instrucciones, decisiones y registros de apoyo |

`resultados/` y `datos/procesados/conjunto_v1/` corresponden a salidas intermedias locales que no se incluyen en esta publicación. Se pueden reconstruir con los programas correspondientes; no se requieren para la verificación final del notebook.

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

Todavía no se ajustaron escaladores, PCA, K-means ni K-NN. La extracción correcta no demuestra por sí sola separación de clases o precisión de reconocimiento.

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
