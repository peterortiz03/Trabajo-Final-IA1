# Dataset de comandos de voz — captura v1

Este documento registra el primer hito. El preprocesamiento incorporado en el
segundo hito está explicado en [preprocesamiento_audio.md](preprocesamiento_audio.md).

## Objetivo y alcance

Se prepara un dataset ampliable para reconocer las palabras **reconocer**,
**identificar** y **salir**, independientemente del hablante. La consigna de 2026
(página 4) exige K-NN sobre características acústicas; no exige escucha permanente.
La activación prevista mediante tecla es compatible con lo que explicita el texto.
Este hito implementa captura guiada, conservación, metadatos y controles iniciales.
No implementa clasificación, extracción definitiva ni preprocesamiento de señales.

El código se añadió sobre el commit `141b60aab3cd15423afcae903c37eeaa3be988fb`.
No se modifican los programas, catálogos ni imágenes de huellas.

## Entorno

El proyecto registra Python 3.14.0 y NumPy 2.3.5. Para captura se conservan esas
versiones y se agregan sounddevice 0.5.3, CFFI 2.0.0 y pycparser 2.23.
PyPI publica distribuciones Windows para sounddevice y ruedas CPython 3.14 de
NumPy/CFFI. Además se descargaron correctamente las cuatro ruedas para Windows x86-64 y
CPython 3.14 con pip. Esto no acredita el funcionamiento del hardware.
El WAV se escribe con `wave`, incluido en Python; no requiere FFmpeg, librosa,
PyAudio ni SoundFile.

Desde PowerShell, situado en la raíz del repositorio:

```powershell
# Solo si todavía NO existe .venv:
py -3.14 -m venv .venv

# Utilizar el entorno existente; no es necesario activar scripts de PowerShell:
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-audio.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe src/grabar_audio.py --dispositivos
.\.venv\Scripts\python.exe src/grabar_audio.py
```

No recrear un entorno existente ni reinstalar las bibliotecas de huellas para
esta prueba. Si pip informa que no encuentra una distribución, registrar el error,
la versión de Python y su arquitectura; no cambiar de Python ni compilar paquetes
sin revisar primero la causa. En VS Code seleccionar el intérprete de `.venv`.

## Registro de personas y sesiones

El operador selecciona el micrófono de una lista, registra una persona con `N`
o elige un identificador existente (`H001`, etc.). Los IDs son anónimos en el
catálogo, pero una voz puede ser reconocible: no equivale a anonimización del audio.
Cada persona debe conocer y aceptar el uso académico antes de participar.
El registro de confirmación del operador no constituye autorización para publicar
la voz; acordar ese uso por separado. No se almacenan nombres personales.

Una sesión es una tanda realizada bajo condiciones similares. Puede retomarse
`S001` después de cerrar el programa. Crear `S002` al cambiar de día, ubicación,
micrófono o condiciones relevantes. No es una clase y no obliga a una cantidad
mínima de grabaciones. Los registros con fecha UTC permiten distinguir tandas.

El menú mantiene persona y sesión seleccionadas:

- 1, 2, 3: registrar reconocer, identificar o salir, respectivamente.
- 4: resumen por persona y palabra, incluyendo tomas con avisos.
- 5, 6, 7: cambiar persona, sesión o micrófono.
- 0: cerrar el grabador. El comando de voz **salir** se graba con 3.

Cada toma muestra la palabra, espera Enter, realiza una cuenta regresiva visual,
captura durante tres segundos y permite reproducir (`P`), guardar (`G`), repetir
(`R`) o descartar (`D`). Se recomienda reproducir cada toma. No se emiten pitidos.
Hablar una sola vez, con voz natural, dejando margen antes y después. Usar una
distancia cómoda y estable al micrófono; evitar soplar o rozarlo. El mismo micrófono
reduce variaciones de dispositivo, pero no elimina diferencias entre voces,
sesiones, ruido y volumen. La diversidad y la calidad importan además de la cantidad.

La duración se configura en JSON o por ejecución:

```powershell
.\.venv\Scripts\python.exe src/grabar_audio.py --duracion 4
```

No hay máximo de personas ni de muestras. Los ceros en H001 y 0001 son relleno
visual, no límites numéricos. Procurar que cada persona grabe los tres comandos.

## Formato y nombres

El original se conserva en WAV PCM16 a la frecuencia aceptada por la API del
micrófono. Con frecuencia explícita `null` se prueba primero la predeterminada
del dispositivo; después 48000, 44100 y 16000 Hz. Se intenta mono, y estéreo si
el dispositivo no admite mono. `check_input_settings` verifica que la API acepta
esa combinación; no demuestra la frecuencia física del conversor del equipo.
No se remuestrea, recorta ni normaliza el original.

Ejemplo: `datos/audio/originales/H001/S001/H001_S001_reconocer_0001.wav`.
El contador es por **hablante + sesión + comando** y continúa desde el máximo
existente más uno. Repetir y descartar no consumen número. Una sesión nueva puede
empezar en 0001 porque el nombre completo sigue siendo único.

## Persistencia e integridad

`src/audio_archivos.py` contiene las funciones de archivos y métricas; el menú
está en `src/grabar_audio.py`. Se admite una instancia del grabador por proyecto.
El bloqueo se libera mediante el sistema operativo si el proceso termina.
No editar el CSV ni mover WAV mientras el grabador esté abierto.

La captura permanece en memoria hasta elegir guardar. Se escribe primero un WAV
temporal completo, se verifica y se registra una pequeña operación pendiente.
El original se incorpora sin reemplazar archivos existentes y el CSV se sustituye
atómicamente. Si el proceso se interrumpe en ese punto, el siguiente inicio
completa el guardado confirmado sin duplicar la fila. La incorporación usa enlaces
duros temporales: trabajar en el disco local NTFS habitual de Windows, no en FAT,
un recurso de red o una carpeta con sincronización simultánea. Si el sistema no
lo permite, el programa informa el error y conserva los temporales para revisión.

Un corte durante la captura no crea una muestra válida. Un corte antes de registrar
la operación puede dejar un temporal, pero este no entra en el catálogo. Los WAV
completos sin metadatos, originales modificados o archivos truncados provocan un
aviso y detienen nuevas escrituras; no se borran silenciosamente. No se garantiza
una transacción frente a cualquier avería física del disco. Mantener copia de
seguridad local de toda la carpeta `datos/audio/` después de cada tanda.

```powershell
.\.venv\Scripts\python.exe src/grabar_audio.py --verificar
.\.venv\Scripts\python.exe src/grabar_audio.py --resumen
```

La verificación revisa encabezado CSV, identificadores, rutas, estructura WAV,
número de cuadros, huellas SHA-256 y copias de configuración. También recupera
un guardado confirmado pendiente antes de verificar. No necesita micrófono.
No determina si se dijo la palabra correcta.

## Metadatos

`datos/audio/metadatos.csv` contiene una fila por toma guardada. Campos:

| Grupo | Campos |
|---|---|
| Identidad | muestra_id, hablante, sesion, comando |
| Ubicación | ruta_original, ruta_procesada |
| Formato original | frecuencia_hz, canales, duracion_s, cuadros |
| Estado | estado_procesamiento, avisos_calidad, particion |
| Mediciones | rms_dbfs, pico, fraccion_saturada |
| Procedencia | configuracion_ref, fecha_utc, dispositivo, api_audio, sha256_original |

En este hito `estado_procesamiento=pendiente`, `particion=sin_asignar` y
`ruta_procesada` está vacía. Una muestra guardada no se declara automáticamente
apta para entrenar. La configuración efectiva se conserva en
`datos/audio/configuraciones/<sha256>.json`; incluye cambios de duración por consola.
El SHA-256 del original detecta cambios en sus bytes. Una grabación humana se
conserva, no se reproduce con una semilla.

## Controles iniciales y límites

Los cálculos usan `x = PCM16 / 32768` y RMS por canal. Se registra el máximo entre
canales para no ocultar un problema de nivel. `RMS_dBFS = 20 log10(RMS)`; 0 dBFS
es el nivel de referencia de escala completa. Para RMS cero se registra un piso
numérico de -240 dBFS y el aviso explícito `captura_nula`.

- RMS menor que -45 dBFS: nivel bajo o posible silencio.
- Pico absoluto desde 0.999: picos cercanos al límite.
- Fracción de muestras desde ese pico mayor o igual a 0.001: posible saturación.

Son umbrales iniciales configurables, no fronteras universales. El RMS incluye
silencios y depende de la duración de captura. El ruido puede superar el umbral
sin contener voz; un limitador del micrófono puede distorsionar antes de llegar a
la escala completa. Escuchar siempre. Guardar con avisos requiere confirmación y
conserva el motivo. El programa no amplifica ruido ni intenta reparar saturación.
Si PortAudio informa pérdidas durante la captura, la toma no se ofrece para guardar.

## Prueba local de aceptación

La siguiente prueba comprueba el programa, no define el tamaño del dataset:

1. Registrar H001, sesión S001 y una toma de cada comando. Reproducir antes de guardar.
2. Grabar otra toma de reconocer y descartarla; grabar la siguiente y guardarla.
   Debe llamarse `H001_S001_reconocer_0002.wav`.
3. Cerrar, abrir y seleccionar H001/S001. Guardar otra toma de reconocer: debe ser 0003.
4. Realizar una toma en silencio y revisar el aviso. Descartarla si solo es una prueba;
   si se guarda deliberadamente, quedará pendiente y con aviso cuando se detecte.
5. Interrumpir una captura con Ctrl+C; reiniciar y ejecutar `--verificar`.
   No debe aparecer una fila nueva por la toma interrumpida.
6. Comprobar el resumen y las rutas del CSV. La palabra **salir** no cierra el grabador.

Resultados pendientes de registrar: versión e instalación en Windows, dispositivo,
formato elegido, reproducción, numeración tras reinicio, aviso de silencio y prueba
de interrupción. No se presume que estos controles ya fueron ejecutados por el autor.

## Secuencia prevista al cierre de captura

El hito 2 que sigue ya cuenta con implementación; consultar su documento específico.

Hito 2: funciones reutilizables de lectura, validación, conversión a mono, remuestreo
con antialias a 16 kHz, detección aproximada de actividad, recorte con márgenes y
normalización limitada. Conservar originales, registrar rechazos y avisos, guardar
WAV mono PCM16 procesados por separado y revisar ejemplos escuchados. No estirar
palabras para igualar duración, ni aplicar filtros agresivos sin evidencia.

Hito 3: revisión de distribución y asignación reproducible **por hablante** en un
archivo de mapa versionado. Mientras tanto todo permanece sin asignar. Todas las
sesiones de una misma persona deben permanecer en una sola partición. Congelar el
mapa al fijar la evaluación; nuevas personas requieren una decisión explícita,
sin recalcular silenciosamente particiones anteriores. Reservar personas para prueba
y demostración; no usar la prueba final para elegir umbrales. Los futuros aumentos,
si se justifican, serán solo de entrenamiento y mantendrán el ID de origen.

La representación de tamaño fijo y K-NN corresponden a una etapa posterior.
Silencio, ruido y palabras desconocidas deberán poder rechazarse en el sistema
final; este hito no agrega una cuarta clase. La escucha continua queda fuera de alcance.

## Trazabilidad y fuentes

La implementación inicial fue asistida por IA generativa a partir de requisitos de
captura incremental, conservación y evaluación por hablante. Se revisó el código
y se probaron archivos temporales sin micrófono; las pruebas no incorporan audio
sintético al dataset. El informe final debe distinguir estas verificaciones de
las pruebas de hardware y datos realizadas por el autor.

- Consigna `Trabajo Final 2026.pdf`, pp. 1–4, archivo provisto por la cátedra, con anotaciones.
- https://pypi.org/project/sounddevice/0.5.3/
- https://pypi.org/project/cffi/2.0.0/
- https://pypi.org/project/numpy/2.3.5/
- https://python-sounddevice.readthedocs.io/en/latest/installation.html
- https://python-sounddevice.readthedocs.io/en/latest/api/checking-hardware.html

## Verificación de esta entrega en el entorno de desarrollo

Fecha: 17/10/2026. Entorno de las pruebas: Linux, Python 3.12.14, NumPy 2.3.5.
No se ejecutó Windows ni se tuvo acceso a un micrófono humano.

- 11 pruebas de archivos aprobadas con `python -m unittest discover -s tests -v`.
- Menú probado con entrada/salida de audio simulada: reproducción, repetición,
  descarte, guardado de la palabra salir, conservación de selección e interrupción.
- Notebook validado y celdas ejecutadas con catálogo vacío y con una señal
  temporal de prueba. Se entrega sin salidas ni audios incrustados.
- Dependencias resueltas y descargadas para Windows x86-64 / CPython 3.14.
- Ninguna señal de las pruebas se incorpora al dataset del proyecto.

Estos resultados verifican lógica de archivos e interacción simulada. La calidad
de voz, latencia, controladores y reproducción real siguen pendientes en Windows.
