# Conjunto sintético v1: generación y preparación

## Estado y alcance

El piloto de deformaciones ya fue ejecutado en Windows 11/Python 3.14.0 por el usuario.
Sus ocho variantes coincidieron píxel por píxel con la ejecución del asistente en Linux.
Las siete bases necesarias fueron recibidas y comprobadas. piloto_01_repeticion es evidencia
de repetibilidad, no una octava identidad.

Esta entrega genera 160 muestras originales y una versión procesada por muestra. Las 320
imágenes son dos representaciones de las mismas 160 muestras, NO 320 observaciones diferentes.
No implementa extracción de características, reconocimiento, K-means, PCA ni voz.

El conjunto es sintético y específico de este trabajo. Su construcción y verificación no
certifican seguridad biométrica ni capacidad de generalización a huellas reales.

## Incorporar los archivos

Copiar el contenido de esta entrega a la raíz del repositorio existente, combinando src/,
config/ y documentos/. No crear otra carpeta de proyecto. Son archivos nuevos; si alguno ya
existe, comparar antes de reemplazar. Conservar el script original src/piloto_deformaciones.py:
el nuevo generador importa su función de deformación ya verificada. No modifica ese script.
Las dependencias son las mismas del piloto; no es necesario reinstalarlas.

Archivos principales:

- src/generar_conjunto.py
- config/conjunto_v1.json
- documentos/etapas/etapa_conjunto_v1.md
- documentos/README_propuesto.md (propuesta para integrar al README, no sustitución automática)
- documentos/historico/verificacion_asistente_conjunto_v1.json (evidencia de prueba técnica)

Las bases deben conservar las rutas ya enviadas:

| ID final | Carpeta dentro de datos/bases | Semilla | Uso | Tipo según Anguli |
|---|---|---:|---|---|
| A01 | piloto_01 | 101 | Autorizado | Right Loop |
| A02 | piloto_02 | 202 | Autorizado | Double Loop |
| A03 | autorizado_03 | 303 | Autorizado | Right Loop |
| I01 | intruso_val_01 | 404 | Intruso de validación | Arch |
| I02 | intruso_val_02 | 505 | Intruso de validación | Double Loop |
| I03 | intruso_test_01 | 606 | Intruso de prueba | Right Loop |
| I04 | intruso_test_02 | 707 | Intruso de prueba | Arch |

Se conserva la misma distribución Natural y una sola hebra de Anguli en todas las bases.
Cada identidad tiene su propia base; no se agrupan imágenes independientes arbitrariamente.
La pantalla About identifica Anguli y el Database Systems Lab del Indian Institute of
Science, pero NO muestra un número de versión. Se registra «no indicada en About». Para
completar la procedencia en el futuro, anotar paquete descargado y hash SHA-256 del ejecutable.
Eso no bloquea esta etapa: conservamos las bases, configuraciones, metadatos y sus hashes.

## Ejecutar en PowerShell desde la raíz

```powershell
.\.venv\Scripts\python.exe src/generar_conjunto.py
```

Salida esperada:

```text
OK: 160 originales y 160 procesadas.
Duplicados exactos: 0. Prueba final excluida de las comparaciones visuales.
```

Destinos:

| Ruta | Contenido |
|---|---|
| datos/originales/conjunto_v1/ | Impresiones sintéticas antes del preprocesamiento |
| datos/procesados/conjunto_v1/ | Las mismas muestras con preparación común |
| datos/metadatos.csv | 160 filas: identidad, partición, reserva, semillas, parámetros y rutas |
| resultados/conjunto_v1/ | Configuración efectiva, entorno, fuentes, verificación y comparaciones |

Dentro de originales/procesados se separan entrenamiento, validacion y prueba, y después
la identidad. No mezclar estas imágenes con las ocho muestras de desarrollo del piloto.
El generador comprueba los hashes de las bases y las semillas de sus configuraciones antes
de crear salidas. Se detiene si encuentra un destino existente; no pisa datos anteriores.
Si una ejecución se interrumpió o se necesita otra corrida, usar otro nombre:

```powershell
.\.venv\Scripts\python.exe src/generar_conjunto.py --nombre conjunto_v1_repetido
```

La corrida alternativa guarda datos/metadatos_conjunto_v1_repetido.csv y carpetas de igual
nombre. No cambiar parámetros solo para obtener resultados favorables en prueba.

## Cantidades y reserva

| Grupo | Entrenamiento | Validación | Prueba | Total |
|---|---:|---:|---:|---:|
| A01 | 20 | 10 | 10 | 40 |
| A02 | 20 | 10 | 10 | 40 |
| A03 | 20 | 10 | 10 | 40 |
| I01 e I02 | 0 | 20 | 0 | 20 |
| I03 e I04 | 0 | 0 | 20 | 20 |
| Total | 60 | 50 | 50 | 160 |

Los intrusos de validación y prueba son identidades diferentes. Los autorizados comparten
base entre particiones porque se evaluarán nuevas impresiones de identidades conocidas.
Los intrusos no se incluyen en el entrenamiento futuro de los tres grupos autorizados.

Reservas de demostración, elegidas por posición ANTES de evaluar modelos:

- A01_M32, A01_M39; A02_M32, A02_M39; A03_M32, A03_M39.
- I03_M02, I03_M09; I04_M02, I04_M09.

Son diez muestras de prueba, no muestras adicionales. No mirarlas para ajustar parámetros,
ni seleccionarlas por saber que funcionan. Las verificaciones automáticas de integridad
incluyen todas las imágenes; los gráficos nunca incluyen prueba. La prueba se utiliza al
final con modelo y umbral fijados. No entrenar con la columna identidad, nombre de archivo,
semilla, tipo morfológico u otras etiquetas de metadatos como si fueran rasgos visuales.

## Qué transformaciones se aplican

Cada muestra usa una semilla propia. NumPy PCG64/SeedSequence separa el azar de deformación
y captura, sin depender del orden de generación. Los cinco perfiles se reparten por igual
DENTRO de cada partición e identidad: cuatro de cada perfil en entrenamiento y dos de cada
perfil en validación/prueba. Autorizados e intrusos reciben las mismas reglas.

1. Local leve: desplazamiento máximo muestreado de 2–3 px.
2. Local moderada: 4–6 px.
3. Movimiento: 2.5–4 px locales, hasta ±4° y ±4 px de movimiento global.
4. Contraste y calidad: 3–5 px locales, menor contraste y ruido/desenfoque suaves.
5. Contacto parcial: 3–5 px locales y corte de un borde de 6–12% del ancho o alto.

Todos los perfiles incluyen un contorno elíptico de contacto suave, con centro, dimensiones
y orientación variables. Se añade ruido suave y una pequeña variación de iluminación.
Es una aproximación procedimental de captura, no un modelo físico validado de presión o piel.
Las elipses no cambian la escala de las crestas; enmascaran la zona de contacto. Las imágenes
Impression_1 de Anguli siguen conservadas como origen/evidencia, pero no se usan como una
textura fija repetida en todas las variantes.

La deformación local reutiliza el campo suave del piloto. Se comprueba su Jacobiano para
rechazar mapeos excesivos. Las alteraciones de contraste se aplican antes del preprocesamiento.
El cambio de tamaño del área visible no se interpreta como cambio de escala de la huella.

## Preparación común, fijada antes de evaluar

- PNG de 8 bits, escala de grises, crestas oscuras y fondo claro.
- Resolución nativa 275×400 (ancho×alto), sin reescalar ni estirar.
- Lienzo completo como ROI de salida: evita recortar cada dedo y ampliarlo a una escala distinta.
- ROI central fija para calcular contraste: filas 50:350, columnas 35:240.
- Transformación lineal de contraste entre los percentiles 1 y 99 de esa ROI, calculados por
  imagen, con saturación a [0,255]. No estima estadísticas conjuntas usando el conjunto de prueba.
- Suavizado gaussiano común sigma=0.3 px, muy leve, para reducir ruido sin borrar crestas gruesas.
- Sin binarización ni esqueletizado por ahora. La interpolación y la simulación de captura
  generan grises útiles; binarizar prematuramente podría introducir cortes/uniones.

No se guarda una ROI segmentada ajustada a cada muestra. Si luego el método de características
requiere segmentación o esqueletizado, se definirá y validará con entrenamiento/validación,
conservando las imágenes originales y sin utilizar prueba para elegir parámetros.

## Revisar y devolver

Abrir SOLO:

- resultados/conjunto_v1/comparacion_validacion.png: cinco perfiles por identidad de validación.
- resultados/conjunto_v1/preprocesamiento_validacion.png: originales/procesadas de A01 en los cinco perfiles.
- resultados/conjunto_v1/verificacion.json: cantidades, duplicados, reservas y tamaño.

No abrir las carpetas prueba para decidir cambios. Para revisar juntos, comprimir únicamente
resultados/conjunto_v1 y adjuntarlo. Si aparece una alerta o error, adjuntar su texto completo.
No hace falta enviar las 320 imágenes en esta revisión.

## Reproducir una muestra aislada

```powershell
.\.venv\Scripts\python.exe src/generar_conjunto.py --muestra A01_M21 --nombre verificacion_aislada
Get-FileHash -Algorithm SHA256 datos/originales/conjunto_v1/validacion/A01/A01_M21.png
Get-FileHash -Algorithm SHA256 datos/originales/verificacion_aislada/validacion/A01/A01_M21.png
```

Los hashes deben coincidir con igual base, configuración, código y entorno. Cada muestra
registra su semilla, la semilla derivada del campo, los parámetros efectivos y ambos hashes.
Las versiones y el hash de los dos scripts quedan registrados. No se garantiza reproducción
exacta al cambiar versiones o plataformas: las pruebas actuales son evidencia limitada.

## Controles y límites de esta entrega

Se validan cantidades, semillas diferentes, bases distintas, separación de intrusos,
contenido no vacío, hashes y duplicados exactos. Además se buscan candidatos casi duplicados
entre particiones de una misma identidad: menos del 1.5% de píxeles binarios diferentes en
una región central fija. Ese chequeo NO alinea las huellas ni es un algoritmo biométrico;
no prueba ausencia de toda similitud indebida. No se descartan ni regeneran pruebas según
rendimiento de un modelo. La revisión visual usa únicamente validación.

Los tipos morfológicos se solapan entre autorizados e intrusos: existe un intruso de
validación Double Loop y uno de prueba Right Loop. Los arcos no aparecen entre autorizados,
por lo que algunos intrusos podrían resultar más fáciles. La evaluación futura deberá
explicar esta limitación y no atribuir todo rechazo correcto a identificación individual.
Dos intrusos por partición son suficientes para el alcance propuesto, no para generalizar
métricas de seguridad a una población.

## Git y documentación

Issue sugerida: `Construir y verificar el conjunto sintético v1`.
Cierre: 160 muestras locales; particiones correctas; integridad verificada; revisión visual
de validación; regeneración aislada comprobada; tamaño medido; documentación actualizada.
El tag `datos-v1` se reserva para ese cierre, no para antes de la ejecución local.

Mensajes de commits pequeños, revisando cada grupo de cambios:

- `data: conservar bases sinteticas con semillas y procedencia`
- `feat: generar impresiones comparables para autorizados e intrusos`
- `feat: separar particiones y aplicar preparacion comun`
- `docs: registrar controles y limites del conjunto sintetico`
- Tras revisión local: `data: incorporar conjunto sintetico verificado`

Antes de cada commit: git status --short y git diff. Agregar rutas explícitas; no usar git add .
sin revisar. No incluir .venv, instaladores ni material de la materia. El tamaño medido de las
320 imágenes en la prueba del asistente es aproximadamente 19.47 MiB, proporcionado para este
repositorio. Se debe comprobar el tamaño local antes de incorporar los datos. No se hizo push.

## Uso de IA y fuentes

ChatGPT revisó los ZIP aportados, interpretó About, propuso el procedimiento y generó el
código/documentación. Petición del usuario: «ahi te mando la carpeta con todas las bases y
una captura de About ya que me lapedias», en continuidad con la generación del conjunto.
El usuario ejecutó Anguli y el piloto en su equipo. No se consultó el material de la materia
en este paso; se siguieron los requisitos y decisiones ya discutidos en la conversación.

Fuentes primarias usadas para el piloto y la implementación:

- https://dsl.cds.iisc.ac.in/projects/Anguli/userguide.html
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.map_coordinates.html
- https://pypi.org/project/numpy/2.3.5/
- https://pypi.org/project/scipy/1.17.0/
- https://pypi.org/project/pillow/12.3.0/
- https://pypi.org/project/matplotlib/3.10.8/

Las cantidades, semillas, particiones, ROI y parámetros de captura son decisiones del proyecto,
no valores atribuidos a esas fuentes. Los archivos recibidos son la evidencia de las bases.
