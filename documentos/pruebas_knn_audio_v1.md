# Pruebas prácticas y diagnóstico de K-NN de audio

## Resultado revisado

Se revisó el ZIP `20261023T033845_362145Z.zip` ejecutado en Windows 11, Python
3.14.0. Sus 27 archivos coinciden con los hashes registrados. Conserva 160
características, k=1 uniforme y 169/179 aciertos en CV LOSO de selección.

| Palabra real | Aciertos | Confusiones |
|---|---:|---|
| identificar | 60/60 | ninguna |
| reconocer | 55/60 | 2 identificar, 3 salir |
| salir | 54/59 | 5 identificar |

H006 tiene cuatro fallos, H001 tres, H005 dos y H002 uno. Esto justifica revisar
el comportamiento por voz; no demuestra por sí solo cuál fue la causa acústica.
Los 60/60 de identificar son recall: también recibió siete audios de otras
palabras. Su precisión fue 60/67 = 89,55 %. El programa no es infalible.

Es una referencia funcional prometedora. No se considera demostrada la robustez
ante hablantes nuevos, otros micrófonos, ruido y palabras fuera de vocabulario.
La CV se usó para seleccionar k y esas voces participaron del desarrollo.
Todavía faltan validación externa y prueba final reservada.

## Qué conserva y qué agrega esta entrega

Se mantienen el extractor, las 160 columnas, el escalado, k=1 elegido, las muestras
válidas y los gráficos PCA. No se atribuye una mejora de exactitud a esta entrega:
agrega herramientas para medir y diagnosticar antes de cambiar el modelo.
No es necesario volver a ejecutar `src/knn_audio.py` si ya conservás tu corrida.

- `src/probar_knn_audio.py`: probar WAV o capturar por micrófono con el modelo fijo;
  guarda todos los audios capturados e intentos en una carpeta separada.
- `src/diagnosticar_knn_audio.py`: reproduce los errores LOSO y muestra los vecinos
  de cada palabra dentro de los cinco hablantes permitidos en cada pliegue.
- `tests/test_prueba_knn_audio.py`: tres comprobaciones de equivalencia de PCM16,
  silencio sin forzar predicción, consultas sin ajuste y conservación de fallos.

No se modifica el notebook 07: sus figuras y resultados siguen siendo la
referencia vigente. Esta nota documenta el avance; al cerrar la experimentación
se incorporará al notebook la evidencia seleccionada. Tampoco se sobrescribe el
README actual: se propone abajo el texto para añadir cuando se verifique Windows.

## Instalar y ejecutar en PowerShell

Extraer el ZIP completo. En su carpeta ejecutar el instalador Python incluido:

```powershell
& "C:\Users\Pedro Peter\Repositorios GitHub\Trabajo-Final-IA1\.venv\Scripts\python.exe" .\instalar_archivos.py --repositorio "C:\Users\Pedro Peter\Repositorios GitHub\Trabajo-Final-IA1"
```

Solo copia los archivos de esta entrega; respalda los que ya existieran. No copia
modelos antiguos ni audios de entrenamiento, no hace push ni cambia particiones.

Desde el repositorio:

```powershell
Set-Location "C:\Users\Pedro Peter\Repositorios GitHub\Trabajo-Final-IA1"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_prueba_knn_audio.py -v
```

Se reutilizan las dependencias existentes. El micrófono requiere sounddevice
0.5.3, ya usado por el grabador. Si falta:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-audio.txt
```

### Primera prueba: menú libre

Usar el ID que realmente corresponde a tu voz; H001 es solo un ejemplo.

```powershell
.\.venv\Scripts\python.exe src/probar_knn_audio.py --modelo "resultados/knn_audio/20261023T033845_362145Z" --hablante H001
```

Elegir el micrófono de la lista. El programa pregunta qué vas a decir ANTES de
grabar. Después pulsás Enter, esperás la cuenta regresiva y el cartel GRABANDO.
Decí una palabra completa, a volumen natural, dejando silencio al principio y
al final. La etiqueta esperada se usa para comparar después: no entra en la
función de predicción ni en el vector.

`salir` es una palabra del vocabulario. Para cerrar el programa se usa Q.
También se puede elegir otra palabra o silencio para explorar sus limitaciones.
El resultado de esas entradas no es una prueba de rechazo calibrado.

### Tanda comparable: cinco repeticiones de cada palabra

```powershell
.\.venv\Scripts\python.exe src/probar_knn_audio.py --modelo "resultados/knn_audio/20261023T033845_362145Z" --hablante H001 --rondas 5
```

Son 15 capturas, alternando identificar/reconocer/salir. Se conservan aciertos,
fallos y audios sin vector. Estos últimos cuentan como fallo en los comandos
esperados; no se eliminan del denominador para mejorar el porcentaje.
La sesión guarda después de cada intento, aunque se interrumpa más adelante.
Si falla la captura del dispositivo, se informa el error; no equivale a una
predicción válida del modelo. Conservar también ese mensaje para revisar el equipo.

Primero probar tu voz conocida. Luego, si hay participantes disponibles, repetir
con otras dos o tres personas y sus IDs anónimos, manteniendo el mismo modelo.
No usar voces o muestras reservadas para prueba final. Una voz nueva usada para
corregir el sistema pasa a ser parte de su desarrollo/validación, no una futura
prueba intacta. Que el ID sea nuevo no verifica quién habló.

No repetir cada toma hasta acertar reemplazando sus fallos. Si se quiere estudiar
un cambio de distancia al micrófono, iniciar otra sesión y anotar la condición.
El programa reutiliza las preferencias de captura de `config/audio_v1.json`.

### Probar un WAV ya guardado

```powershell
.\.venv\Scripts\python.exe src/probar_knn_audio.py --modelo "resultados/knn_audio/20261023T033845_362145Z" --hablante H001 --wav "C:\ruta\audio.wav" --esperada reconocer
```

Debe ser WAV PCM16 como el grabador, no MP3. No usar audios de prueba reservada.
Si el WAV ya pertenecía al entrenamiento, la respuesta demuestra funcionamiento
de la ruta de inferencia, no generalización ni evaluación independiente.

### Diagnóstico de los diez errores actuales

```powershell
.\.venv\Scripts\python.exe src/diagnosticar_knn_audio.py --modelo "resultados/knn_audio/20261023T033845_362145Z"
```

Requiere conservar la extracción de origen. Verifica que ids y vectores coincidan
con el modelo, y reproduce la misma exactitud antes de guardar el diagnóstico.
Si falta o cambió el origen, se detiene: no sustituir el manifiesto por otro para
forzar la ejecución. Compartir el error si aparece.

`errores_vecinos_loso.csv` muestra para cada fallo el ejemplo más cercano de cada
palabra, su hablante, distancia y ruta del WAV. Esos vecinos se buscan únicamente
entre las voces de ajuste; la voz retenida nunca se busca a sí misma.
Escuchar el original confundido y sus vecinos, revisar etiqueta, ruido, recorte
y palabra completa. Las rutas se abren desde la raíz del repositorio con el
Explorador de Windows; los originales no se alteran.

`aportes_geometricos.csv` muestra diez columnas que más favorecen al vecino de la
palabra confundida frente al vecino de la correcta. Para cada columna calcula
$(z_j-v_{correcto,j})^2-(z_j-v_{confundido,j})^2$: un valor positivo favorece al
segundo. Se trabaja en escala estandarizada. Esto describe la distancia, no prueba
que una característica sea mala ni autoriza eliminarla. Para k>1, estos vecinos
son solo una parte del voto, no explican por sí solos toda la decisión.

Ejemplo reproducido: H001_S001_salir_0002 queda a 12,79 del vecino identificar y
a 13,04 del vecino salir, usando el escalado de su pliegue. Con k=1 gana el primero.
La cercanía entre distancias ayuda a entender esa decisión; no calibra confianza.

## Qué hace el método y por qué puede confundirse

Trayecto: audio original -> preprocesamiento vigente -> redondeo PCM16 igual al
dataset -> 160 características -> escalado guardado -> K-NN -> palabra predicha.
PCA queda en una rama de visualización: no interviene en la predicción actual.
No se ejecutan PCA, selección de k ni ajuste del escalador para cada consulta.

K-NN es supervisado: guarda ejemplos con etiquetas. Con k=1, el comando predicho
es el del ejemplo más cercano. La distancia euclidiana compara todas las columnas
estandarizadas. Con más vecinos se vota, pero aumentar k no garantiza mejorar:
en la comparación realizada k=3,5,7 dieron resultados inferiores a k=1.

Una pronunciación nueva puede parecerse más a otro comando en esta representación.
Cambios de timbre, ritmo, volumen, micrófono, ruido y detección del intervalo activo
pueden influir. El extractor resume segmentos mediante amplitud, cruces por cero
y coeficientes acústicos MFCC; ese resumen no retiene toda la información temporal
de la voz. Son hipótesis a comprobar, no causas demostradas por la matriz.

En PCA se ven dos combinaciones de las 160 columnas: PC1 y PC2 conservan solo
27,75 % de varianza. El resto queda fuera del dibujo. PCA busca variación, no
separación de comandos. Huellas y audio son datos/representaciones diferentes,
por lo que no es válido exigir la misma apariencia. La separación de los colores
en un gráfico no sustituye a las métricas fuera de entrenamiento.
Se podrían estudiar otras componentes o PCA en clasificación; eso cambiaría la
representación y necesitaría compararse dentro de cada pliegue. No dibujar grupos
artificialmente separados ni reducir a la mitad por costumbre.

## Mejoras recomendadas, en orden

1. Conservar la referencia y audios válidos. Escuchar los errores y sus vecinos.
   Corregir una etiqueta o excluir por defecto real solo con evidencia y motivo
   registrado; conservar el original y volver a ejecutar el pipeline si cambia
   una revisión. No borrar por el mero hecho de que K-NN se equivoque.
2. Medir captura real: voz conocida primero, nuevas voces después. Mantener
   modelo y condiciones documentados. Buscar si los fallos dependen de palabra,
   voz, sesión o micrófono.
3. Si faltan ejemplos representativos, recoger más con `src/grabar_audio.py`.
   Ese es el grabador de dataset: requiere revisión, asignación de particiones,
   preprocesamiento y extracción antes de un nuevo ajuste. Las pruebas prácticas
   de este ZIP no se agregan automáticamente, para evitar aprender de las consultas.
4. Solo si la evidencia lo requiere, comparar una variante pequeña del vector
   con la referencia: por ejemplo, revisar el peso de amplitud o los máximos por
   segmento frente a resúmenes más estables, o PCA de clasificación. Cada variante
   debe ajustarse dentro de LOSO, medirse por hablante/comando y comprobarse en
   validación. No seleccionar columnas ni umbrales usando prueba final.
5. Si la aplicación debe reaccionar solo a comandos válidos, diseñar después un
   rechazo con ejemplos de ruido, silencio y otras palabras. No improvisar un
   umbral con las distancias mostradas ni reutilizar el de huellas.

La actividad por energía puede evitar vectorizar silencio puro. No es un detector
completo de voz y puede admitir ruido; una salida sin avisos tampoco garantiza
palabra correcta. K-NN sigue siendo de vocabulario cerrado: devuelve una de tres
palabras cuando recibe un vector válido, incluso si la entrada es desconocida.
Con k=1, una salida de probabilidad 1 no demostraría certeza. Por eso no se muestra
un porcentaje de confianza ni se dispara ninguna acción externa.

## Verificación realizada y qué falta

En Linux/Python 3.12.14 pasaron las tres pruebas nuevas. Se reprodujeron los diez
errores LOSO. Se recalcularon los vectores de los 179 WAV originales conservados
con el camino nuevo: coinciden con el dataset dentro de tolerancia 1e-12
(diferencia máxima observada 7,99e-15 por redondeo numérico). El NPZ que enviaste
desde Windows se recargó y produjo las mismas decisiones sobre los mismos
vectores; el camino nuevo también conserva esas decisiones. Son verificaciones
de implementación, no nuevos resultados de acierto.
No se probó un micrófono físico ni la captura en Windows desde este entorno.

Compartir de `resultados/prueba_audio/FECHA/`: `sesion.json`, `intentos.csv`,
`resumen_prueba.json` y los JSON de las tomas fallidas. Para escuchar, adjuntar
los WAV fallidos y un par acertados, si sus participantes autorizaron compartirlos.
Del diagnóstico: `resumen.json`, `errores_vecinos_loso.csv` y
`aportes_geometricos.csv`. No hace falta enviar otra vez todo el entrenamiento.

## README y commits pequeños

Después de verificar en Windows se puede añadir al README:

> Pruebas prácticas de comandos: `src/probar_knn_audio.py` reutiliza el K-NN de
> 160 características sin reentrenar y registra todos los intentos por sesión.
> `src/diagnosticar_knn_audio.py` inspecciona los errores LOSO y sus vecinos.
> Instrucciones y límites en `documentos/pruebas_knn_audio_v1.md`.
> La robustez con nuevas voces y el rechazo de entradas desconocidas siguen pendientes.

Agregar `/resultados/prueba_audio/` y `/resultados/diagnostico_knn_audio/` a
`.gitignore` si faltan, sin reemplazar sus otras reglas. No subir sesiones con
WAV por defecto. Para un informe, seleccionar tablas anonimizadas en documentos/.

```powershell
git add src/probar_knn_audio.py tests/test_prueba_knn_audio.py
git commit -m "Agregar prueba de audio con modelo fijo y registro de todos los intentos"
git add src/diagnosticar_knn_audio.py documentos/pruebas_knn_audio_v1.md
git commit -m "Documentar errores KNN y diagnosticar vecinos sin excluir muestras"
```

Revisar `git diff --cached` antes de confirmar. El README y `.gitignore` pueden
ir en otro commit cuando se incorporen esas dos actualizaciones. No se hace push
automático ni se afirma que esta herramienta ya haya mejorado la exactitud.
