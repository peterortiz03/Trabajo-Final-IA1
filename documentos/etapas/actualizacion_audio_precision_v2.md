# Actualización de voz: k=5 y desempate por cercanía

## Resultado y alcance

Se compararon k=5 y k=7 con voto uniforme usando precisión macro media por hablante de LOSO. k=1 y k=3 solo se recalcularon como diagnóstico. Cada pliegue ajusta escalado con las otras cinco voces. No se usó prueba final.

| Configuración nueva | Precisión macro media por voz | Recall macro medio por voz |
|---|---:|---:|
| k=5 uniforme, desempate cercano | 94,51 % | 92,72 % |
| k=7 uniforme, desempate cercano | 94,01 % | 92,10 % |

Ganó k=5. Exactitud agregada: 166/179 = 92,74 %. La precisión macro media es el promedio de la precisión de las tres palabras y luego de las seis voces, con zero_division=0. No equivale a precisión global agregada. Empate de selección a 1e-12: menor k.

El k=1 sigue siendo mejor en este corte (169/179; precisión macro media por voz recalculada 95,27 %). El cambio se adopta por la recomendación docente de usar más vecinos y la comparación acordada; no demuestra que el ruido haya disminuido ni que el reconocimiento haya mejorado. La diferencia con el antiguo k=5 de 165/179 se debe al nuevo desempate: no se reescribe aquel resultado.

El voto es mayoría uniforme. En empate, solo participan las clases con frecuencia máxima y gana la de su vecino más cercano. Si también hay igualdad exacta de distancia, gana el menor índice guardado de entrenamiento. Esa misma prioridad define los k vecinos si empatan el quinto y sexto. No se usan etiquetas alfabéticas ni redondeo para desempatar. No se añadió rechazo de desconocidos.

## Instalación

1. Cerrar la aplicación y revisar que el repositorio local esté en el estado esperado. Este paquete se preparó sobre el commit c0ead406b330ced49c2fb208508aabb959e4f22e.
2. Descomprimir el ZIP en una carpeta temporal.
3. Copiar **el contenido de `archivos/` a la raíz del repositorio**, combinando subcarpetas y reemplazando los archivos del mismo nombre. No copiar la carpeta contenedora como otra capa dentro del proyecto.
4. Si modificaste localmente `config/aplicacion.json`, `src/probar_knn_audio.py` o los dos notebooks desde esa versión, conservar una copia y comparar esos archivos antes de reemplazarlos. El paquete no requiere tocar huellas ni datasets.
5. Mantener completo `modelos/audio/precision_v2/`. El paquete es autocontenido y no requiere el manifiesto local de extracción del modelo histórico.

No requiere dependencias nuevas del programa. Usa las versiones científicas existentes: NumPy 2.3.5, SciPy 1.17.0 y scikit-learn 1.8.0. Las celdas de guía 03 también requieren pandas e IPython como antes.

## Prueba en PowerShell, desde la raíz del repositorio

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_knn_audio_precision.py" -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test*knn_audio.py" -v
.\.venv\Scripts\python.exe src/interfaz_servicios.py
.\.venv\Scripts\python.exe src/interfaz.py
```

Se esperan cinco pruebas nuevas y las seis pruebas históricas de audio aprobadas en esta revisión. El diagnóstico debe mostrar voz disponible con paquete `precision_v2`. En Detalles técnicos de la ventana debe verse **k=5, uniform y mayoria_vecino_cercano_v1**. El lanzamiento normal utiliza config/aplicacion.json, actualizado para el paquete nuevo. Una configuración antigua pasada mediante --config sigue apuntando al modelo que tenga escrito; no se cambia silenciosamente.

En la ventana probar Reconocer, Identificar y Salir con al menos cinco tomas de cada uno. Probar silencio, cancelación del cierre y una palabra desconocida, anotando lo observado. Silencio puede no producir vector; una palabra desconocida puede convertirse en un comando. No se garantiza que las 15 tomas sean correctas. El número de aciertos debe registrarse después de ejecutar, sin reemplazar los resultados históricos.

Para una prueba guiada solo de micrófono:

```powershell
.\.venv\Scripts\python.exe src/probar_knn_audio.py --modelo "modelos/audio/precision_v2" --hablante H001 --rondas 5
```

Esto registra las 15 tomas nuevas y sus resultados en una carpeta nueva bajo resultados/prueba_audio. No incorpora muestras al entrenamiento. Compartir intentos.csv, resumen_prueba.json y una captura de Detalles técnicos de la interfaz.

Para comprobar el trayecto con un WAV publicado, sin micrófono:

```powershell
.\.venv\Scripts\python.exe src/probar_knn_audio.py --modelo "modelos/audio/precision_v2" --wav "datos/audio/originales/H001/S001/H001_S001_reconocer_0001.wav" --esperada reconocer --hablante H001
```

Ese WAV ya participa en entrenamiento: es una prueba de funcionamiento y compatibilidad del recorrido, no una medida de generalización.

## Volver temporalmente a k=1

El modelo anterior permanece intacto. Si sus recursos locales siguen disponibles:

```powershell
.\.venv\Scripts\python.exe src/interfaz.py --config config/aplicacion_audio_k1_respaldo.json
```

Esto no cambia config/aplicacion.json. Para volver a la versión nueva, iniciar normalmente.

## Notebooks y figuras

- `notebooks/07_pca_knn_audio.ipynb`: preserva la bitácora de k=1 y sus sesiones históricas, identifica ese contenido como antecedente y agrega el apartado actual con precisión, recall y matriz de k=5.
- `guia_didactica/03_knn_voz_interfaz_y_evaluacion.ipynb`: conserva teoría e historia y agrega la explicación del modelo actual con los tres gráficos nuevos, ya visibles. Las entradas necesarias se incluyen junto al notebook. Leer desde el comienzo y el apartado nuevo al final.
- No se atribuyen a k=5 los 15/15 de voz conocida ni las voces sintéticas de k=1. No se altera el PCA ni los modelos de huellas.

Los archivos HTML de una guía anterior no se actualizan por abrir un notebook. Si se incluye HTML actualizado en este paquete, reemplazar también ese archivo. Para ejecutar guía 03, abrir guia_didactica como carpeta de trabajo, como en la entrega anterior.

## Reproducción de la comparación, opcional

El paquete de modelo ya está listo. No hace falta repetir ajustes para utilizarlo. Para repetir las tablas de LOSO desde los vectores incluidos:

```powershell
.\.venv\Scripts\python.exe src/knn_audio_precision.py --salida "resultados/comparacion_audio_precision_repeticion"
```

La carpeta de salida debe ser nueva. Se esperan k=5 y las mismas métricas salvo tolerancias numéricas. Este comando solo escribe tablas y parámetros elegidos para revisión; no reemplaza el paquete ni cambia la configuración de la interfaz. El `src/knn_audio.py` histórico sigue siendo la herramienta de reproducción de la etapa original: no ejecutarlo esperando actualizar esta versión.

## Comprobaciones realizadas

- Extracción real de las 179 grabaciones procesadas conservadas con el código actual y reproducción de la varianza PCA histórica.
- Seis pliegues LOSO para k=1,3,5,7, con escalado separado por voz retenida y nuevo desempate.
- Cinco pruebas nuevas de mayoría, desempate restringido, distancias iguales, corte de vecinos y recarga.
- Seis pruebas históricas de audio aprobadas.
- Carga real del servicio de interfaz: paquete nuevo disponible y k=5.
- Consulta real por la consola con WAV de desarrollo: reconocer, vector de 160 dimensiones.
- Guía 03 ejecutada secuencialmente con captura de figuras y tablas. Notebook 07 conserva su evidencia previa e incluye las salidas gráficas nuevas.
- No se ejecutó micrófono real ni una ventana nueva en Windows. Las métricas son desarrollo en Linux con las dependencias registradas.

No se hizo commit ni push. Revisar los cambios y las pruebas locales antes de subirlos.
