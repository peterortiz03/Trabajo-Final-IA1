# Etapa 07: PCA exploratorio y K-NN para audio

## Qué se implementó

Clasificar **palabras**, no hablantes: `identificar`, `reconocer`, `salir`.
Se conservan las **160 características** del extractor vigente y las revisiones
actuales. No se modifican extractores, particiones ni la etapa de huellas.
No se agregan K-means, rechazo de audio desconocido ni reducción de columnas.

La consigna `Trabajo Final 2026.pdf`, dentro del material `ia1_material_15_10.zip`,
pide K-NN para comandos y gráficos PCA. Esta etapa usa esos métodos. La entrega
se preparó contra `origin/main` `60e1fdf`; no hace falta volver a instalar la etapa 06.

## Ejecución en Windows / PowerShell

Desde la raíz del repositorio, con el entorno de las etapas anteriores:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_knn_audio.py -v
.\.venv\Scripts\python.exe src/knn_audio.py
```

No requiere dependencias nuevas: reutiliza `requirements-clusterizacion.txt`
(scikit-learn 1.8.0) y sus dependencias. Si el entorno aún no tiene esas versiones:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-clusterizacion.txt
```

La ejecución busca una extracción compatible y comprueba su vigencia. Si informa
que falta, ejecutar primero `src/extraer_dataset_audio.py`, como en la etapa 04,
y atender cualquier revisión pendiente. No excluir muestras para mejorar métricas.
Si existen varias extracciones, puede indicarse una carpeta relativa exacta:

```powershell
.\.venv\Scripts\python.exe src/knn_audio.py --extraccion "datos/caracteristicas/audio/CARPETA/EJECUCION"
```

Luego abrir `notebooks/07_pca_knn_audio.ipynb` en VS Code, seleccionar el kernel
`.venv` y ejecutar todas las celdas. El notebook lee la última ejecución completa:
no vuelve a entrenar ni mezcla resultados de distintas carpetas. Se puede fijar
la ruta en `EJECUCION`. Sus salidas incluidas corresponden a una ejecución real
en Linux; al ejecutarlo en Windows pasan a mostrar tu propia corrida.

## Cómo funciona, en palabras sencillas

Cada audio es un punto con 160 coordenadas. Estandarizar significa restar a cada
columna su media de entrenamiento y dividir por su desviación estándar de
entrenamiento (`ddof=0`). Una columna constante se conserva: su escala se fija en
1, sin dividir por cero. Se exportan nombres, orden, medias y escalas.

PCA construye combinaciones de esas características para representar la mayor
variación posible. Cada punto del gráfico es una grabación. Las dos vistas
usan las mismas coordenadas: una colorea palabras y la otra hablantes.
PCA no usa esas etiquetas para encontrar direcciones. Un solapamiento en PC1–PC2
no demuestra que los comandos sean inseparables en 160 dimensiones.
La varianza acumulada indica cuánto representa la proyección; no mide aciertos.
**PCA se usa solamente para gráficos. K-NN recibe las 160 columnas estandarizadas.**

K-NN guarda ejemplos etiquetados. Ante otro vector calcula distancias euclidianas
en el espacio estandarizado, busca los `k` ejemplos más próximos y vota su palabra.
No tiene centroides, no forma grupos ni usa semillas aleatorias. El voto uniforme
cuenta vecinos; el ponderado da más peso al más cercano (inverso de la distancia;
los casos de distancia cero reciben el tratamiento de scikit-learn).

Se comparan ocho opciones: k=1,3,5,7 con ambos tipos de voto. Un k impar no
garantiza ausencia de empate con tres clases. Scikit-learn resuelve un empate
de votos por el orden interno de clases; si hay empates de distancia justo en el
límite de los k vecinos, puede influir el orden de ejemplos. Se conserva el orden
de extracción. No se presenta ese desempate como evidencia acústica.

## Por qué evaluamos por hablante

El mapa actual destina H001–H006 a entrenamiento/desarrollo. Hay 179 muestras
conservadas; una grabación fue excluida previamente por revisión de ruido. Las
cantidades se obtienen del catálogo, no están fijadas en el código.
No hay todavía voces asignadas a validación externa ni a prueba final.

LOSO significa dejar un hablante fuera por vez: entrenar con los otros cinco,
evaluar con ese hablante y repetir para los seis. **Cada repetición ajusta su propio
escalador usando únicamente los cinco hablantes de ajuste.** Así no se mezcla la
voz evaluada con sus ejemplos de entrenamiento.

Se elige el mayor recall macro medio por hablante. Recall de una palabra es la
fracción de sus muestras reconocidas correctamente; el promedio macro da igual
peso a las tres palabras y después a cada hablante. En empate de candidatos
(tolerancia 1e-12), se prefiere voto uniforme y luego menor k.
También se conserva k=5 uniforme como referencia fija en los mismos pliegues.

Esta CV sirve para **seleccionar y diagnosticar**: al elegir la mejor alternativa
con esos resultados, su porcentaje puede ser optimista. Además, estas voces ya
participaron en el desarrollo previo. No equivale a una prueba independiente.
No se usa el acierto del modelo sobre sus propios ejemplos como evaluación.

Finalmente se ajusta un escalador con todo entrenamiento y se guardan los
ejemplos de ese conjunto para K-NN. El PCA se ajusta con ese mismo entrenamiento.
Cuando existan hablantes de validación explícitos, se transformarán sin ajustar
nuevamente y se evaluarán por separado. La partición `prueba` queda fuera de
PCA, comparación, escalado, predicciones y métricas de esta etapa.

## Referencia ejecutada aquí (Linux, Python 3.12.14)

| Resultado de desarrollo LOSO | Valor |
|---|---:|
| Dimensión de entrada | 160, sin eliminar columnas |
| Referencia k=5 uniforme | 165/179 = 92,18 % de exactitud |
| Selección interna | k=1, voto uniforme |
| Exactitud agregada de la selección | 169/179 = 94,41 % |
| Recall macro medio por hablante, criterio de selección | 94,38 % |
| PC1+PC2 | 27,75 % de varianza |
| Componentes para 95 % | 52 |
| Validación con nuevas voces y prueba final | Pendientes |

Los diez errores aparecen en `errores_cv_seleccion.csv`. H006 tiene 25/29 aciertos
y H001 27/30; H003 y H004 tienen 30/30. Esto orienta la revisión del efecto de
hablante y de las confusiones `reconocer`/`salir`, sin eliminar audios válidos.
No hace falta reducir a 80 componentes para comenzar: esta referencia ya permite
medir el comportamiento con todas las características. Cualquier variante futura
debe compararse con el mismo protocolo y sin mirar prueba final.

En este entorno pasaron tres pruebas de contratos: separación de voces y escalado
por pliegue, exclusión de prueba y bloqueo de revisión pendiente, y recarga de
modelo con control de orden de columnas. El notebook también se ejecutó completo.
Windows no fue ejecutado aquí: hay que confirmar allí las salidas.

## Resultados que se guardan

Cada ejecución crea `resultados/knn_audio/FECHA_UTC/`, con:

- `resumen.json`, configuración efectiva, versiones y hashes de archivos.
- Comparación de ocho opciones y resultados por palabra y por hablante.
- Predicciones fuera del pliegue y lista de errores; matrices de confusión.
- Cuatro figuras: PCA por palabra/hablante, varianza acumulada, comparación de k
  y matriz de confusión de CV de selección.
- Contratos por pliegue con voces, ids y parámetros de escalado para auditar fuga.
- `modelo.npz`: nombres y orden, escalado, ejemplos etiquetados de entrenamiento,
  PCA completo; `parametros_elegidos.json`: k y votos.
- Copias del código y configuraciones que produjeron esa corrida.

El ZIP incluye evidencia de referencia en `referencia_ejecutada/`, para comparar;
el modelo reutilizable lo genera tu ejecución local. El notebook busca primero
resultados locales y, si aún no existen, esa evidencia en `documentos/evidencias/07_comandos_voz/`.
Los resultados locales no deben subirse completos por defecto. Si se versionan
figuras/resúmenes para el informe, seleccionar esa evidencia en `documentos/`.

Para predecir **un vector extraído con el mismo extractor y preprocesamiento**:

```python
from knn_audio import cargar_modelo, predecir_vectores  # src debe estar en sys.path
modelo = cargar_modelo("resultados/knn_audio/TU_EJECUCION")
palabra = predecir_vectores(vector_160, nombres_en_orden, modelo)[0]
```

La recarga reconstruye el índice K-NN con ejemplos YA guardados: no vuelve a
aprender el escalado ni incorpora el audio consultado. En una consulta se usa
siempre ese mismo modelo. No hace falta volver a comparar k cada vez.
Es un clasificador de vocabulario cerrado: siempre elige una de tres palabras.
Silencio, ruido y comandos desconocidos necesitan un diseño de rechazo posterior;
no se reutiliza el umbral de huellas ni se interpreta un voto como confianza calibrada.
La captura de micrófono e integración en la aplicación quedan para otra etapa.

## Qué compartir y cómo continuar

Compartir `resumen.json`, `comparacion_cv.csv`, `metricas_hablante_cv_seleccion.csv`,
`errores_cv_seleccion.csv`, las cuatro figuras y cualquier error de consola.
Luego registrar nuevos hablantes con los tres comandos y acordar su asignación
explícita a validación y a prueba ANTES de mirar resultados. No cambiar el mapa
actual para presentar voces ya usadas como si fueran nuevas. Su incorporación
requiere actualizar catálogo/revisiones, extraer y registrar el mapa coherentemente.

## Commits propuestos (después de verificar en Windows)

```powershell
git add config/knn_audio_v1.json src/knn_audio.py tests/test_knn_audio.py
git commit -m "Agregar referencia KNN de audio con evaluacion por hablante sin fuga"
git add notebooks/07_pca_knn_audio.ipynb documentos/etapas/knn_audio_v1.md documentos/evidencias/07_comandos_voz
git commit -m "Documentar PCA y resultados internos de KNN de comandos"
```

Antes de subir, revisar `git diff --cached` y las salidas guardadas. Para excluir
corridas locales sin sobrescribir tu `.gitignore`, agregar `/resultados/knn_audio/`
si no está ya presente y guardar ese cambio en un commit pequeño. La etapa 06
y su notebook conservan la documentación de huellas.
