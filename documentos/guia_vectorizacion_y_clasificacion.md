# De una huella o una palabra a una decisión

Trabajo Final IA I 2026, Ingeniería en Mecatrónica, UNCUYO.

Este documento conecta las dos extracciones de características con las etapas
de aprendizaje que se desarrollarán después. Describe el propósito de cada
paso y evita interpretar la vectorización como una clasificación ya resuelta.

## 1. Qué significa vectorizar

Una imagen y una grabación contienen muchos valores. Dos capturas del mismo
dedo pueden estar desplazadas o invertidas, y dos pronunciaciones de la misma
palabra pueden durar distinto. Comparar directamente sus píxeles o muestras de
audio sería sensible a esas variaciones.

La vectorización transforma cada muestra en una lista de números con dimensión
y orden fijos:

$$\mathbf{x}=[x_1,x_2,\ldots,x_d].$$

Cada posición conserva siempre el mismo significado. Los identificadores,
identidades, comandos, hablantes y particiones se guardan en catálogos aparte;
no se utilizan como características predictivas.

| Modalidad | Una fila de $X$ | Dimensión actual |
|---|---|---:|
| Huella | Descripción textural de una captura | 144 |
| Audio | Evolución acústica de una grabación | 160 |

Las matrices no se concatenan porque resuelven problemas diferentes.

## 2. Huellas: de la textura al vector

La normalización geométrica prepara la posición y el tamaño. Después se erosiona
la máscara seis píxeles para evitar el borde artificial creado por la
normalización. Las intensidades válidas se ajustan con percentiles 2–98 y se
cuantizan en 16 niveles.

La matriz de coocurrencia, o GLCM, cuenta con qué frecuencia aparece un nivel
de gris $i$ junto a otro nivel $j$ para una distancia y dirección determinadas.
Un par participa solamente si sus dos píxeles están dentro de la máscara. Así,
el fondo no domina los conteos.

Se analizan distancias 1, 3 y 5; direcciones 0°, 45°, 90° y 135°; y cuatro
medidas: contraste, homogeneidad, energía y correlación. Se usan tres bloques
espaciales: región global, suma NO+SE y suma NE+SO. La dimensión es:

$$3\text{ regiones}\times3\text{ distancias}\times4\text{ direcciones}
\times4\text{ medidas}=144.$$

Las regiones opuestas y la simetrización de los conteos hacen que el vector sea
invariante al giro de 180°. Se pierde la posibilidad de distinguir cuál de las
dos posiciones opuestas contenía cada patrón, pero no se duplica una muestra ni
se cambia su partición. Las 170 muestras de desarrollo verificadas dieron una
diferencia máxima de 0.0 al repetir la extracción tras el giro.

## 3. Audio: de la palabra al vector

Cada WAV procesado es mono y tiene una frecuencia de 16 kHz. El intervalo de
actividad guardado por el preprocesamiento se divide en diez partes relativas.
La palabra no se estira: una pronunciación larga tiene segmentos temporales más
largos que una corta.

Dentro del audio se toman ventanas acústicas de 25 ms con un salto de 10 ms.
Las ventanas permiten observar fragmentos pequeños; los diez segmentos indican
en qué parte de la palabra se encuentra cada ventana. Son dos divisiones con
funciones distintas.

En cada ventana se calculan ZCR, media del valor absoluto, máximo absoluto y
MFCC. Para cada segmento se guardan:

- ZCR: media y máximo.
- Amplitud: media y máximo.
- MFCC c1, c2, c4 y c5: media, máximo y desviación estándar.

Esto produce 16 valores por segmento y, por lo tanto:

$$10\text{ segmentos}\times16\text{ valores}=160.$$

Los MFCC resumen la forma del espectro. Se calculan con ventana Hann, FFT de
512 puntos, 26 filtros Mel, logaritmo natural y DCT. No representan directamente
una palabra ni una probabilidad.

La ejecución posterior a la revisión auditiva produjo 179 vectores de 160 componentes, todos finitos y repetibles. De las 180 grabaciones registradas, 179 tienen decisión conservar y una tiene decisión excluir. Doce muestras vectorizadas conservan avisos del extractor. Los avisos permanecen registrados y no equivalen automáticamente a un descarte.

## 4. Por qué habrá que escalar

Una característica puede variar entre 0 y 1 mientras otra toma valores mucho
mayores. Si calculamos distancias sin corregirlo, la segunda puede dominar por
su escala. El escalador aprenderá media y dispersión solamente con el conjunto
de entrenamiento y aplicará esos mismos parámetros a validación, prueba y
muestras nuevas.

Los vectores originales se conservarán. El escalador, el orden de columnas y su
configuración se guardarán para poder reproducir el sistema.

## 5. Cómo se reconocerá un comando con K-NN

K-NN conserva ejemplos de entrenamiento con su comando conocido. Para un audio
nuevo se repetirá exactamente el preprocesamiento y la vectorización, se aplicará
el escalador guardado y se buscarán sus $K$ vecinos más cercanos. El comando se
decidirá a partir de las etiquetas de esos vecinos.

Una evaluación por hablante es necesaria para comprobar que el sistema aprende
el comando y no memoriza la voz. Todas las grabaciones de una persona deben
permanecer en una sola partición. H006 se asignará a entrenamiento; la prueba
final deberá reservar personas que no se usen para elegir parámetros.

K-NN siempre puede proponer uno de los tres comandos. Si el sistema también debe
rechazar palabras distintas, habrá que evaluar una regla de rechazo con ejemplos
adecuados; la distancia por sí sola no fija un umbral confiable.

## 6. Cómo se reconocerá o rechazará una huella con K-means

K-means aprenderá centros a partir de huellas autorizadas de entrenamiento.
Después se estudiará qué identidades aparecen en cada grupo. Una huella nueva se
normalizará, vectorizará, escalará y comparará con esos centros.

El centro más cercano siempre existe, incluso para un intruso. Por eso la
distancia al centro necesita un umbral de rechazo ajustado con entrenamiento y
validación. Las huellas intrusas de validación pueden evaluar el rechazo, pero
no deben participar en el ajuste del escalador inicial. Las 50 muestras de prueba permanecen reservadas mientras se eligen y validan el descriptor, el escalado y los umbrales. El número de grupos para las identidades autorizadas queda fijado por la consigna: k = 3.

Como las huellas actuales son sintéticas, una captura de un dedo físico o de un
sensor diferente representa otro dominio. Su funcionamiento deberá comprobarse
con datos de ese dispositivo antes de afirmar que el sistema reconoce huellas
reales.

## 7. Función de PCA

PCA se ajustará después del escalado y solamente con entrenamiento. Sus primeras
dos o tres componentes permitirán representar los vectores en gráficos. Esos
gráficos ayudan a observar tendencias, superposiciones y valores atípicos, pero
no garantizan separación ni precisión.

Usar dos componentes para visualizar no obliga a entrenar los modelos con solo
dos componentes. Esa decisión se evaluará con validación y se mantendrá la
prueba final fuera de la selección.
