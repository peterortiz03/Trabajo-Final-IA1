# Cierre de desarrollo de la etapa 07: PCA y K-NN de audio

**Fecha:** 23/10/2026, Argentina. **Estado:** implementación de referencia y
documentación completas para continuar el proyecto; validación humana externa y
evaluación final pendientes. El cierre no certifica robustez universal.

## Objetivo y decisiones

Reconocer los comandos identificar, reconocer y salir mediante K-NN, utilizando
los vectores del extractor vigente. La clase es la palabra, no el hablante.
Se conservaron las 160 columnas, sus nombres y orden, y las revisiones previas.
No se aplicó la selección de 72 columnas utilizada en huellas al problema de voz.
No se cambiaron extractores, se eliminaron audios válidos para mejorar resultados
ni se entrenó K-means para audio. PCA se utilizó para exploración y gráficos.

La fuente de requisitos es `Trabajo Final 2026.pdf` del material del curso.
La bitácora anterior de estadísticas y el mapa persistente de hablantes aportan
el contexto. La bitácora 07 explica el método y consulta evidencia real de Windows.

## Datos y prevención de fuga

El corte revisado tiene 180 originales: 179 conservados y uno excluido previamente
por revisión, H006_S001_salir_0005. Se usaron 60 identificar, 60 reconocer y 59 salir.
Estas cantidades describen el corte; el programa las obtiene del catálogo.

`config/particiones_audio_v1.json` asigna H001–H006 a entrenamiento/desarrollo.
El catálogo histórico puede conservar sin_asignar: el mapa es la capa explícita
que debe aplicarse y verificarse. No hay voces humanas nuevas asignadas actualmente
a validación externa o prueba final. No se reasignaron voces de desarrollo para
presentarlas como prueba independiente. Nuevos hablantes requieren decisión explícita.

La validación cruzada interna deja fuera un hablante por vez (LOSO). En cada pliegue
se calcula el escalador con las otras cinco voces y se transforma la voz retenida
con esos parámetros. Las etiquetas, IDs, hablantes y particiones nunca son columnas
de entrada. La prueba final queda fuera del ajuste y del análisis de esta etapa.

## Estandarización y PCA

Por columna se aplica $z_j=(x_j-\mu_{j,train})/\sigma_{j,train}$ con ddof=0. Se
guardan medias, escalas y nombres en orden. Las columnas constantes conservarían
su posición con escala 1; el corte ejecutado no presenta columnas constantes.

PCA construye combinaciones lineales que concentran variación sin usar etiquetas.
Se ajustó con todas las características estandarizadas del entrenamiento. Las
proyecciones por palabra y por hablante usan las mismas coordenadas y permiten
inspeccionar ambos efectos. Cada punto representa una grabación.

PC1 y PC2 explican juntas 27,75 % de la varianza; 52 componentes alcanzan 95 %.
Esto no significa 27,75 % de aciertos, ni obliga a reducir a 52 dimensiones.
El solapamiento en dos dimensiones no demuestra inseparabilidad en el espacio completo.
K-NN opera sobre las 160 columnas estandarizadas, sin PCA en la clasificación.
El PCA global de visualización no interviene en LOSO ni en la selección de k.

Las cuatro figuras conservadas son PCA por palabra/hablante, varianza acumulada,
comparación de k y matriz de confusión. No se agregaron figuras que no aportaran
una interpretación distinta. Las figuras se leen de una misma corrida completa.

## K-NN y selección interna

K-NN conserva ejemplos etiquetados y busca vecinos por distancia euclidiana:
$d(z,v)=\sqrt{\sum_{j=1}^{160}(z_j-v_j)^2}$. Con k=1 devuelve la palabra del
ejemplo más cercano; no aprende centroides ni inicializa grupos.

Se compararon k=1,3,5,7 con voto uniforme y por distancia: ocho alternativas,
no ocho palabras, ocho componentes o ocho conjuntos de datos. El criterio fue
recall macro medio por hablante: igual peso a comandos dentro de cada voz y
después igual peso a cada voz. En empate dentro de 1e-12 se prefiere voto uniforme
y luego menor k. La exactitud agregada cuenta todas las muestras y es otra medida.

La mejor opción fue k=1 uniforme. Para k=1, ambas ponderaciones producen aquí
las mismas decisiones. El criterio prefijado resolvió ese empate. No se usó semilla:
se conservaron el orden de ejemplos, parámetros y versiones. Con tres clases,
k impar no garantiza evitar empates de voto. Los empates siguen las reglas de
scikit-learn y pueden depender del orden de clases o de ejemplos en el límite de
vecinos; no se interpretan como evidencia acústica.

| Resultado de desarrollo LOSO | Referencia k=5 uniforme | Selección k=1 uniforme |
|---|---:|---:|
| Exactitud agregada | 165/179 = 92,18 % | 169/179 = 94,41 % |
| Recall macro medio por hablante | 92,16 % | 94,38 % |

La selección y sus métricas usan la misma CV interna, por lo que el resultado de
la alternativa elegida puede ser optimista. Las voces también participaron en el
desarrollo del procesamiento. No se presenta como evaluación final independiente.

| Palabra real | identificar predicha | reconocer predicha | salir predicha |
|---|---:|---:|---:|
| identificar | 60 | 0 | 0 |
| reconocer | 2 | 55 | 3 |
| salir | 5 | 0 | 54 |

La diagonal suma 169. Identificar tiene recall 60/60, pero recibió siete ejemplos
de otras palabras: su precisión es 60/67 = 89,55 %. No equivale a ausencia de errores.
H001 tuvo 27/30, H002 29/30, H003 30/30, H004 30/30, H005 28/30 y H006 25/29.
Los diez errores se conservaron para investigación.

## Modelo final de desarrollo y herramientas

Después de elegir k, se ajustó un escalador con las 179 muestras de entrenamiento
y se guardaron los ejemplos etiquetados para K-NN y el PCA completo. Modelo,
parámetros, configuración, versiones y hashes permanecen en la carpeta de corrida.

| Programa | Propósito | Cambia el modelo guardado |
|---|---|---|
| src/knn_audio.py | Comparar opciones, ajustar y guardar una nueva corrida | Crea otra corrida |
| src/probar_knn_audio.py | Grabar o leer un WAV y consultar un modelo fijo | No |
| src/diagnosticar_knn_audio.py | Reproducir LOSO e inspeccionar vecinos de los errores | No |

El probador aplica el mismo preprocesamiento, redondeo a PCM16 y extracción del
dataset. La palabra esperada solo se usa para comparar la respuesta; no es entrada
de la predicción. El ID de hablante solo identifica la sesión; no restringe los
vecinos a esa persona. La consulta busca entre todas las voces del entrenamiento.
Muestra hasta cinco vecinos de diagnóstico, aunque el voto utiliza k=1.
No agrega consultas al dataset ni vuelve a elegir k para cada nueva muestra.

El diagnóstico recalcula escaladores/modelos temporales por pliegue para revisar
las voces retenidas. La salida 169/179, errores 10 confirma que reproduce el análisis
anterior: no son diez errores de las nuevas grabaciones. Sus CSV de vecinos y
aportes describen geometría de distancias; no prueban causas acústicas ni ordenan
eliminar características. El autor informó esa reproducción correcta en Windows.

## Prueba práctica con voz conocida

Sesión UTC 20261023T115814_373387Z, modelo fijo de la corrida
20261023T033845_362145Z, Windows/Python 3.14.0. El autor grabó nuevas tomas de H001,
voz ya representada en entrenamiento, con micrófono Realtek, WASAPI, 48 kHz mono PCM16.

| Entrada | Resultado |
|---|---|
| identificar | 5/5 correctas |
| reconocer | 5/5 correctas |
| salir | 5/5 correctas |
| Otra palabra | Clasificada como salir |
| Silencio | Sin vector; no se consultó K-NN |

Los 15 comandos conocidos se reconocieron correctamente. Las 17 entradas no
equivalen a 17 aciertos de un sistema con rechazo: el 100 % del resumen solo cuenta
los 15 comandos conocidos. Hay tres tomas con avisos de captura/procesamiento,
conservadas y acertadas. Los avisos técnicos no implican descarte automático.

Esta prueba comprueba que la captura y la inferencia funcionaron en Windows con
grabaciones nuevas de una voz conocida. No mide generalización a una persona nueva
ni garantiza funcionamiento con ruido, otros dispositivos o todas las pronunciaciones.
La palabra desconocida demuestra una limitación real del vocabulario cerrado.

## Ensayo exploratorio de voces sintéticas

Sesión UTC 20261023T121951_936996Z. Según aclaración posterior del autor se usaron
cuatro voces sintéticas reproducidas desde un celular. Todas quedaron registradas
como H007; ese ID no las incorporó al entrenamiento ni cambió las predicciones.
No hay correspondencia persistida entre tomas y voz sintética, por lo que no se
calculan métricas por voz, configuración regional o acento.

El registro automático original se conserva: 17 intentos, 14 aciertos, una toma
sin vector, 82,35 % por intento. El autor aclaró que en toma_001 la reproducción
no comenzó a tiempo. Se anota como incidente de ejecución, sin borrar ni reescribir
esa fila. Entre los 16 audios efectivamente reproducidos hubo 14 aciertos (87,5 %).
Las tomas 014 y 015 de salir se clasificaron como reconocer.

Este ensayo combina voz sintética, parlante, ambiente y micrófono. El autor observó
mejor reconocimiento en voces configuradas como español argentino, pero el registro
no permite atribuir causalmente los fallos al acento ni comparar regiones con rigor.
No sustituye validación con personas reales y recibe un papel secundario en el cierre.

## Verificación, procedencia y límites

El ajuste y las sesiones prácticas corresponden a ejecuciones reales del autor
en Windows, compartidas como ZIP. Se verificaron los hashes del lote de ajuste,
coherencia de cantidades, coincidencia de modelo entre sesiones y tablas de intentos.
Los paquetes originales se conservan localmente. La evidencia seleccionada mantiene
CSV/JSON originales; contexto.json omite la ruta personal absoluta de Windows.

Durante este cierre documental se ejecutaron en Linux las celdas de lectura del
notebook y sus controles de evidencia. No se entrenó otro modelo ni se capturó audio.
Las pruebas de software aprobadas previamente se describen como antecedentes,
sin atribuirles una ejecución nueva. No se realizó una escucha auditiva nueva.

Limitaciones principales: solo seis voces en desarrollo, CV usada para selección,
una demostración humana conocida, ensayo sintético pequeño sin separación por voz,
ausencia de validación humana externa y de rechazo calibrado de desconocidos.
La heurística de actividad puede impedir vectorizar silencio puro, pero no certifica
voz ni rechaza todo ruido. Una distancia pequeña o un voto de k=1 no son confianza
calibrada ni aceptación de un comando válido.

## Reproducción, consulta y conservación local

Para leer la bitácora no hace falta volver a generar datos: abrir
notebooks/07_pca_knn_audio.ipynb con el kernel .venv y ejecutar todas sus celdas.
Lee documentos/resultados_etapa07 con integridad verificada, sin buscar la última
corrida local. Así su contenido permanece estable al producir nuevas sesiones.

Para reproducir una nueva corrida con los programas ya instalados:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test*knn_audio.py" -v
.\.venv\Scripts\python.exe src/knn_audio.py
```

Las dependencias siguen en requirements-clusterizacion.txt y requirements-audio.txt.
Si falta una extracción vigente, usar los extractores existentes y resolver los
avisos del contrato sin forzar hashes ni excluir muestras automáticamente.

Para probar el modelo existente, sin ejecutar de nuevo el entrenamiento:

```powershell
.\.venv\Scripts\python.exe src/probar_knn_audio.py --modelo "resultados/knn_audio/20261023T033845_362145Z" --hablante H001
.\.venv\Scripts\python.exe src/diagnosticar_knn_audio.py --modelo "resultados/knn_audio/20261023T033845_362145Z"
```

Conservar localmente la carpeta completa del modelo y su extracción de origen,
incluidos modelo.npz, parametros_elegidos.json y resumen.json; las herramientas
comprueban el contrato. El modelo contiene ejemplos de entrenamiento, medias,
escalas, orden de columnas y PCA. La evidencia publicada no incluye el NPZ ni WAV
de sesiones prácticas; sirve para leer/auditar resultados, no para inferir por sí sola.
Desde otra computadora se reproduce el ajuste o se transfiere el paquete local
completo con sus dependencias. No borrar los resultados ignorados por Git.

## Cierre y trabajo pendiente

Se conserva esta versión de desarrollo. No se persiguen cero errores cambiando
datos válidos ni se incorporan voces sintéticas al entrenamiento por estos resultados.
El sistema puede continuar hacia integración, documentando sus limitaciones.

Cuando haya personas disponibles: asignar un ID real distinto a cada participante
nuevo, fijar el modelo, registrar una cantidad equilibrada por palabra y conservar
todos los intentos. Usar esas voces para validación si se toman decisiones con
sus resultados; reservar otras personas para la prueba final. Cambiar solo el ID
de una voz ya conocida no la convierte en desconocida.

Si aparece una dificultad consistente, investigar captura, actividad, variación
entre voces y representación. Evaluar una ampliación o variante frente a la referencia
con ajuste interno correcto y validación; nunca seleccionar usando prueba final.
El rechazo de comandos desconocidos requiere un diseño y una calibración posterior.
La aplicación de micrófono todavía no acciona huellas ni implementa escucha continua.
