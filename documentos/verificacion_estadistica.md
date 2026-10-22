# Verificación estadística previa a PCA y agrupamiento

## Alcance y decisión sobre audio

El objetivo es reconocer **palabras de cualquier hablante**, no identificar voces.
Vectorizar es describir una grabación con reglas fijas. Entrenar K-NN será conservar
vectores etiquetados para decidir el comando de una grabación nueva. La grabación en
vivo también se vectorizará, pero no se añadirá automáticamente al entrenamiento.

Se adopta para este avance el uso de los seis hablantes actuales en entrenamiento y
diagnóstico. H001/H002 participaron del desarrollo del preprocesamiento y H006 ya estaba
previsto para entrenamiento. H003–H005 se incorporan al desarrollo sin afirmar que sean
prueba independiente. No hace falta conocer su historial para destinarlos a desarrollo.

Esto permite aprovechar las 179 grabaciones conservadas; no significa que se haya
verificado reconocimiento en una persona nueva. La validación por hablante comprueba
ese objetivo, no impide que una persona nueva utilice el sistema. Se deberán conseguir
voces nuevas para validación y otras para prueba final, documentar su historial y fijar
las asignaciones **antes** de mirar resultados para elegir parámetros. Si no se consiguen,
se podrá estudiar validación de desarrollo dejando hablantes fuera del ajuste en cada
ronda, pero no se presentará como prueba final independiente del diseño del descriptor.
Aquí todavía no se implementa ninguna de esas evaluaciones.

El mapa persistente es `config/particiones_audio_v1.json`. El notebook aplica una capa
`particion_analisis`, conservando el catálogo de extracción y sus hashes. Las siguientes
etapas deben usar este mapa. Una asignación previa incompatible o un hablante nuevo
produce un error. Nuevas muestras de un hablante ya asignado conservan su destino;
ninguna incorporación reasigna personas anteriores. Esta versión no cambia los
programas de captura/preprocesamiento ni sus catálogos históricos.

La voz del autor, del profesor o de la profesora puede participar en una demostración.
Si ya se utilizó en desarrollo o entrenamiento, esa demostración no prueba generalización
a una voz desconocida. Para probar esa capacidad, la persona reservada no debe aportar
muestras ni resultados al ajuste del método. Tras evaluar y documentar una versión,
se puede preparar otra versión con más voces de entrenamiento; necesitará otra prueba
si se desea volver a afirmar independencia.

## Método e interpretación

El notebook `05_verificacion_estadistica.ipynb` reutiliza las matrices NPZ, sus nombres y
catálogos. Comprueba el contrato, hashes, configuración, dependencias y correspondencia
`fila_vector`–ID. Selecciona una extracción compatible y registra su ruta exacta; se puede
indicar otra ruta explícitamente. Las cantidades se calculan, no se fijan en código.

Por cada clase y columna se exportan cantidad, media y desviación muestral (`ddof=1`).
Para n=1 se conserva la media y la DE queda vacía con estado explícito; una clase sin
muestras no tiene estadística y se debe revisar en el catálogo y las cantidades. No se
mezclan componentes de un vector. La DE entre audios de una característica MFCC no es
la DE entre ventanas que ya integra el vector del extractor (`ddof=0`).

Se usa un solo indicador de orden: `S = suma_c n_c(media_c-media_global)^2 /
suma_c suma_i(x_i-media_c)^2`. Es una razón entre dispersión entre clases e interna,
invariante a escala lineal por característica, sin umbral universal ni p-valor.
Un denominador cero con numerador positivo tiene estado de separación infinita;
un 0/0 constante queda indefinido. Se exportan ambas sumas y el estado. No se añade
un epsilon arbitrario para esconder estos casos ni se eliminan columnas.

Cada modalidad tiene una figura grande de tres paneles: menor, mediana y mayor
separación entre columnas no constantes. El desempate es alfabético; no se eligen
los ejemplos manualmente después de ver los resultados. Todos los datos individuales
del análisis aparecen junto a media ± DE, en la escala original de cada panel.
Estas barras no son intervalos de confianza y no contienen necesariamente todos los datos.
No se comparan medias o DE brutas entre características con unidades diferentes.

En audio se calculan también medias y DE por hablante y por hablante/palabra, y el mismo
indicador para palabras dentro de cada voz y voces dentro de cada palabra. Sirve para
observar sensibilidad al hablante. No se comparan automáticamente esas cifras como si
las agrupaciones de tres palabras y seis hablantes fueran equivalentes ni se afirma
una dominancia global por una sola columna. Los colores ayudan a examinar las voces.

Los no finitos se exportan y detienen el análisis, sin imputar ni eliminar filas.
Las constantes globales y por clase se informan. Las muestras fallidas o pendientes
de entrenamiento detienen su análisis; las exclusiones humanas explícitas se respetan.
Los avisos previos y de extracción permanecen en los catálogos de uso.

## Verificado por el asistente el 22/10/2026

Se revisaron README, notebooks 01–04, extractores, configuraciones, documentación y
catálogos del commit `6505a6c`. La consulta remota de HEAD coincidió con ese commit.
Las matrices no estaban publicadas: se regeneraron con los dos extractores existentes.
Se ejecutaron todas las celdas Python del notebook 05, en orden, en un proceso con
Matplotlib Agg. Se revisaron visualmente ambas figuras. El notebook se entrega sin
salidas incrustadas para distinguirlo de la ejecución posterior en Windows.
No se verificaron micrófono, reproducción ni reconocimiento en vivo en la PC del autor.
No se volvió a escuchar el conjunto: se respetaron sus revisiones registradas.

| Datos del análisis | Resultado |
|---|---:|
| Huellas autorizadas de entrenamiento | 120: 40 de A01, A02 y A03 |
| Columnas de huellas | 144 |
| Audios conservados | 179: reconocer 60, identificar 60, salir 59 |
| Columnas de audio | 160 |
| Hablantes utilizados | H001–H006 |
| Excluida por revisión humana | H006_S001_salir_0005 |
| No finitos / columnas globalmente constantes | 0 / 0 en ambas modalidades |
| Pruebas automáticas | 57 aprobadas, incluidas 6 nuevas |
| PCA, K-means, K-NN o escalador ajustados | Ninguno |

Huellas: la energía `NO_SE_d1_a90_energia` presenta medias muy parecidas (aproximadamente
0,296; 0,291; 0,293) respecto de DE entre 0,036 y 0,042: poca separación individual.
La homogeneidad mediana muestra una tendencia entre identidades con solapamiento.
La correlación `NO_SE_d5_a45_correlacion` separa claramente A02 de las otras en estas
muestras; A01 y A03 todavía presentan algunos puntos solapados. No permite afirmar
reconocimiento correcto ni generalización a huellas reales. Las ampliaciones provienen
de las mismas bases sintéticas y no son dedos independientes.

Audio: `s10_mfcc_c4_max` tiene medias alrededor de 2,1–2,3 y DE de 2,2–2,5, con fuerte
solapamiento. `s02_mfcc_c2_media` muestra diferencias por palabra, pero mucha variación
entre voces: por ejemplo, dentro de «identificar» el indicador por hablante es cercano
a 5,12. Esto señala sensibilidad a la voz en esa columna, no prueba dominancia en todo
el descriptor. El máximo ZCR del primer segmento (`s01_zcr_max`) es prometedor para
«salir»: media 0,578 ± 0,188 frente a 0,166 ± 0,083 en «identificar» y
0,148 ± 0,094 en «reconocer». Estas dos últimas palabras se mezclan mucho en esa columna;
incluso «salir» tiene puntos solapados. No alcanza para afirmar separación de los tres
comandos ni precisión ante una voz nueva.

Una columna solapada puede aportar información en combinación con otras. Ni una
columna excelente garantiza reconocimiento ni una mala invalida todo el descriptor.
Estos resultados son descriptivos de entrenamiento, sin estimación de exactitud.

## Ejecutar en Windows

Copiar los archivos del paquete respetando rutas, en la raíz del repositorio. Los
notebooks 01–04 y los extractores previos se conservan. Las versiones de README y
`.gitignore` están basadas en el commit revisado: si se modificaron localmente después,
integrar sus diferencias en lugar de reemplazar esos cambios.

En PowerShell, desde la raíz:

```powershell
.\.venv\Scripts\python.exe src/extraer_dataset_huellas.py
.\.venv\Scripts\python.exe src/extraer_dataset_audio.py
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

No hace falta regenerar matrices si existen extracciones compatibles. Abrir
`notebooks/05_verificacion_estadistica.ipynb`, seleccionar el kernel `.venv` y ejecutar
todas las celdas. No ejecutar con `--incluir-prueba`. No hay dependencias nuevas.
La salida es `resultados/verificacion_estadistica/<fecha_UTC>/`, una carpeta por ejecución.
El código genera CSV UTF-8 con BOM y separador coma, que puede importarse en Excel.

Revisar `catalogo_uso_*.csv`, las cantidades por clase/hablante, `no_finitos.csv`,
`constantes.csv`, `medias_desviaciones.csv` y las dos figuras `distribuciones.png`.
Las tablas completas incluyen todas las columnas, no solo las mostradas.
La revisión por voz está en `medias_desviaciones_condicionales.csv` y
`separacion_condicional.csv`. Cada ejecución registra configuración, hashes y muestras
usadas en `resumen.json`; el código exacto también se copia en la salida.

Para interpretar la ejecución local, compartir `resumen.json`, ambas figuras y
`audio/separacion_condicional.csv`. Si se detiene, compartir el error y los CSV de
controles generados; no editar los vectores a mano. Los resultados del asistente se
entregan separados bajo `resultados_asistente/` en el ZIP. No son una ejecución en Windows.

Commit sugerido:

```text
Agrega diagnóstico por característica y mapa de desarrollo de audio para revisar separación antes de PCA
```

Versionar notebook, módulo, mapa, pruebas y documentación. Mantener las matrices y los
resultados locales bajo sus reglas de exclusión. No se realiza commit ni push automático.
