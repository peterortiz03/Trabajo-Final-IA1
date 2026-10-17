# Trabajo Final — Inteligencia Artificial I · 2026

**Sistema de reconocimiento de huellas dactilares controlado por reconocimiento de voz**  
Ingeniería en Mecatrónica · Facultad de Ingeniería · Universidad Nacional de Cuyo

El proyecto desarrolla un agente de control de acceso basado en identidades de huellas sintéticas. El sistema deberá reconocer si una muestra corresponde a una identidad autorizada, identificarla y responder a los comandos de voz **Reconocer**, **Identificar** y **Salir**.

La consigna establece K-means con k = 3 para las identidades autorizadas, una distancia y un umbral de aceptación/rechazo, y K-NN para los comandos de voz. Este repositorio registra el desarrollo progresivo; los módulos pendientes todavía no están implementados.

## Estado del proyecto

| Etapa | Estado al 15/10/2026 | Evidencia o siguiente tarea |
|---|---|---|
| Dataset de huellas sintéticas | Completada, versión 1 | 220 muestras, semillas, parámetros y catálogos |
| Normalización geométrica de huellas | Implementada, versión 1 | Región de interés, centrado, orientación y máscaras |
| Acondicionamiento adicional de imágenes | Pendiente de definir y validar | Contraste y filtrado según la representación de características |
| Características de huellas, K-means y umbral | Pendiente | Vectores discriminantes, k = 3 y rechazo de intrusos |
| Dataset de comandos de voz | Capturador v1 preparado; prueba de micrófono pendiente | [Captura y controles](documentos/dataset_audio.md) |
| Preprocesamiento de comandos de voz | Implementado v1; revisión local por escucha pendiente | [Método e incrementalidad](documentos/preprocesamiento_audio.md) |
| Características acústicas de voz | Pendiente | Representación de tamaño fijo para K-NN |
| Clasificación de comandos con K-NN | Pendiente | Entrenamiento y evaluación del módulo de voz |
| Integración del agente | Pendiente | Flujo de interacción y control de acceso |
| Evaluación, PCA e informe final | Pendiente | Métricas, visualización, conclusiones y defensa |

La normalización geométrica v1 no equivale a haber completado todo el preprocesamiento mencionado en la consigna. La normalización de contraste y el filtrado deberán definirse al elegir y validar las características; no se anticipa que todas las técnicas posibles sean necesarias.

## Lectura recomendada

1. [Bitácora de dataset y normalización](notebooks/01_bitacora_dataset_normalizacion.ipynb): decisiones, archivos, resultados y comprobaciones ejecutadas.
2. [Índice de documentación](documentos/README.md): estado vigente y antecedentes de cada etapa.
3. [Uso de IA generativa](documentos/uso_ia_generativa.md): tareas asistidas, ejemplos de solicitudes y verificación.

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

`ipykernel` es una dependencia adicional para ejecutar notebooks. En VS Code, seleccionar el intérprete de `.venv`, abrir la bitácora y ejecutar sus celdas. El notebook solo lee archivos. Las salidas guardadas permiten consultarlo en GitHub sin instalar Python.

**Una clonación ya contiene los datos y resultados finales: no es necesario regenerarlos para consultar o verificar el avance.**

## Organización

| Ruta | Contenido |
|---|---|
| `src/` | Programas y funciones de generación y normalización |
| `config/` | Configuraciones de las etapas |
| `datos/bases/` | Bases de Anguli y archivos de procedencia |
| `datos/originales/` | Las 220 capturas anteriores a la normalización |
| `datos/procesados/normalizacion_final_v1/` | Representaciones finales, máscaras, catálogo y controles |
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
las capturas cuando existen; no contiene resultados humanos precargados.
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
procesamiento automático de 60 muestras se verificó en el entorno del asistente;
la escucha de los recortes en Windows queda pendiente. H001/H002 se utilizan para
desarrollo; otras personas deberán reservarse para la evaluación final.
