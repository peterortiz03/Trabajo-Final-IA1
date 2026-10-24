# Registro de uso de IA generativa

## Alcance de la asistencia en este avance

Se utilizó ChatGPT como apoyo para revisar archivos de bases sintéticas, proponer la organización del proyecto, generar y revisar código Python de deformaciones, ampliaciones y normalización, preparar documentación y proponer comprobaciones de integridad. Los patrones base de las huellas se obtuvieron con Anguli; no se atribuye su creación al modelo conversacional.

La asistencia también incluyó la elaboración de la bitácora y su revisión editorial para lectura académica. La responsabilidad de comprender, revisar y defender el procedimiento corresponde al autor del trabajo. No se atribuyen al modelo resultados de reconocimiento que todavía no se han evaluado.

## Ejemplos de solicitudes utilizadas

Se conservan los siguientes fragmentos textuales de la conversación:

> bueno dame los codigos necesarios entonces y las instrucciones para ejecutarlos y que analizar

Solicitud de implementación e instrucciones para la etapa de normalización.

> ahora hay que normalizar todas las muestras que nos quedan,y tambien aplicar la rotacion necesaria si fuera necesario

Solicitud de procesamiento del conjunto completo y corrección de orientación.

> que hace cada archivo, que se guarda en cada carpeta, que se va  a utilizar, por que guardamos 3 archivos poor muestra de huella

Solicitud de documentación del avance y explicación de sus archivos derivados.

Los fragmentos contienen la escritura original. Son ejemplos del uso realizado, no una transcripción completa de las conversaciones. El registro debe ampliarse con las siguientes etapas y con las referencias exigidas en el informe final.

## Cómo se verificó la asistencia

- Ejecución de los programas en el entorno local Windows/Python registrado en los metadatos.
- Comprobación de conteos y particiones: 220 muestras, distribuidas en 120/50/50.
- Verificación SHA-256 de originales y salidas frente al catálogo.
- Comprobación de dimensiones, máscaras binarias y equivalencia exacta de la alternativa con el giro de 180°.
- Conservación en el notebook publicado de los resultados de estas comprobaciones y de paneles de desarrollo para inspección visual.
- Registro de dos avisos de borde, sin convertirlos automáticamente en errores ni descartar muestras.
- Pruebas auxiliares documentadas en los archivos históricos, distinguiendo su entorno y alcance de la ejecución local definitiva.

Estos controles comprueban el funcionamiento e integridad del flujo de datos. No sustituyen la evaluación futura de identificación, rechazo de intrusos o reconocimiento de voz. El método de orientación conserva una ambigüedad de 180° y no corrige deformaciones locales.

## Referencias y actualización

La fuente de requisitos es `Trabajo Final 2026.pdf`, Inteligencia Artificial I, Facultad de Ingeniería, UNCUYO. La consigna solicita declarar el uso de IA generativa, incluir ejemplos de prompts y explicar su verificación. Las referencias técnicas específicas se conservan en los documentos de cada etapa.

Este registro corresponde al avance de dataset y normalización de huellas del 15/10/2026. Debe completarse con las herramientas, solicitudes y validaciones utilizadas en voz, características, agrupamiento y evaluación.

## Ampliación: PCA, K-means y rechazo de huellas

Se utilizó ChatGPT como apoyo para revisar la consigna y la estructura existente, implementar
el escalado/PCA, comparar K-means con 144 y 72 columnas, preparar una selección supervisada
de características basada solo en entrenamiento y calibrar el rechazo con validación.
También se solicitó explicar las distancias, el umbral y los límites de las métricas, y
actualizar la bitácora sin presentar desarrollo como evaluación final.

Ejemplos de solicitudes de esta etapa:

> Primero debemos realizar PCA y el análisis inicial utilizando TODAS las características vectorizadas.

> verifica como mejorar la correspondencias para que se distingan mejor los grupos

> la distancia de la que se habla es la distancia euclidiana o como se calcula?

La asistencia propuso tres variantes acotadas (todas, mitad y cuarto de columnas), con
selección y escalado recalculados dentro de cada pliegue de entrenamiento. La selección
usa etiquetas conocidas de entrenamiento y se declara supervisada; K-means no recibe
esas etiquetas para ajustar centroides. No se cambiaron identidades ni se eliminaron
capturas válidas para mejorar las figuras.

Se verificaron las respuestas mediante ejecuciones del autor en Windows/Python 3.14.0,
compartidas como los cortes UTC 20261022T160116_346229Z (referencia),
20261023T014705_319737Z (selección) y 20261023T021746_872267Z (calibración).
Se contrastaron configuración, tablas por identidad, métricas, selección y hashes.
El asistente ejecutó comprobaciones de código en Linux: 3 pruebas de la referencia,
4 de selección y 5 de rechazo, además de comprobaciones de recarga y reutilización.
Estos controles no equivalen a una evaluación biométrica independiente.

La bitácora final consulta evidencias de esas ejecuciones reales y no vuelve a ajustar
modelos. Se conserva A02_M22 como falso rechazo. Prueba final, K-NN de voz e integración
continúan pendientes. La IA no generó nuevas mediciones ni resultados finales no ejecutados.


## Ampliación: PCA y K-NN de audio — 23/10/2026

ChatGPT asistió en la implementación de K-NN conservando 160 características,
estandarización por pliegue LOSO, PCA exploratorio y comparación acotada de ocho
alternativas. También asistió con pruebas de micrófono, diagnóstico de errores,
explicaciones teóricas y documentación de cierre. No se atribuye al modelo
conversacional la captura ni la pronunciación de los audios del dataset.

Ejemplos de solicitudes reales de esta etapa:

> que hace el programa probar_knn_audio y que hace el diagnosticar_knn_audio?

> A todas les deje el mimsom H007 porque no tenia ganas de cambiarlo.

> completar bien la documentación para ya concluir con esta etapa

El autor ejecutó el ajuste y pruebas prácticas en Windows/Python 3.14.0 y compartió
las carpetas UTC 20261023T033845_362145Z, 20261023T115814_373387Z y
20261023T121951_936996Z. Se revisaron resúmenes, predicciones, figuras y metadatos.
El registro de la conversación anterior informó tres pruebas nuevas aprobadas
en Windows y seis pruebas del software aprobadas por el asistente en Linux;
no se presentan como pruebas nuevamente ejecutadas durante este cierre editorial.

Para el cierre se recuperaron los tres paquetes originales, se verificó su
coherencia y los hashes de la corrida de entrenamiento, y se ejecutaron las celdas
de lectura del notebook sobre la evidencia seleccionada. No se ajustaron modelos,
se grabaron voces ni se evaluó prueba final. La documentación distingue el ensayo
con voz humana conocida del ensayo de voces sintéticas reproducidas por celular.
La aclaración del autor sobre la primera toma sintética se conserva como anotación,
sin alterar CSV ni resumen original. La evaluación con nuevas personas sigue pendiente.

## Ampliación: interfaz e integración · 23/10/2026

ChatGPT asistió con la revisión de la consigna y del repositorio, la elección de Tkinter, la implementación de presentación/estado/adaptadores y la documentación. Se mantuvieron los algoritmos y parámetros anteriores; la asistencia se concentró en coordinarlos y explicar sus precondiciones. No se utilizaron subagentes ni se publicaron cambios automáticamente.

Ejemplos del pedido utilizado:

> Esta etapa consiste en integrar lo existente. No rediseñes los extractores, cambies parámetros del reconocimiento ni reentrenes modelos automáticamente.

> Ambas formas de interacción deben ejecutar las mismas funciones y respetar las mismas condiciones. No dupliques la lógica de reconocimiento.

> No conviertas excepciones técnicas en rechazos biométricos.

Se verificaron contratos de estados, recursos ausentes, bloqueo de operaciones y concordancia del recorrido de huellas con módulos y distancias publicadas de desarrollo. También se ejecutó la ventana en un escritorio virtual Linux y se recorrieron selección, cancelaciones, autorización, rechazo, identidad y error. La coordinación de voz y PortAudio se simularon de manera explícita en pruebas de software; no se presentaron como reconocimiento acústico real. El silencio controlado se procesó con el procedimiento existente.

El modelo local de voz y su extracción no estaban disponibles en el clon. No se generó un reemplazo ni se entrenó para ocultar esa ausencia. La aplicación lo informa y conserva el modo manual. Permanecen pendientes las pruebas reales con micrófono y modelo del autor en Windows, personas nuevas y evaluación final. El registro detallado de esta verificación está en `documentos/evidencias/08_integracion/verificacion.md`.

## Ampliación: preparación de consultas sintéticas · 23/10/2026

ChatGPT asistió con el diagnóstico del rechazo de bases limpias, la separación entre generación de capturas e inferencia, y la implementación de un preparador en la ventana existente. El pedido se apoyó en esta decisión del autor:

> lo ultimo que tengo implementado es el ultimo zip que me mandaste, para que tengas en cuenta y me envies el zip correspondiente y las instrucciones de verificacion

Se reutilizó `generar_conjunto.producir`, sin copiar sus algoritmos dentro de la interfaz. Antes de construir los controles se fijaron tres semillas y los cinco perfiles existentes y se compararon cuatro condiciones con las cinco bases de desarrollo. Se conservaron los 170 resultados, sin seleccionar semillas para conseguir acceso. La evidencia indica 45/45 capturas autorizadas correctas y 30/30 intrusas rechazadas para el procedimiento completo; no equivale a una evaluación independiente o reconocimiento directo de bases limpias.

Se verificaron equivalencia con el generador original, reproducción de consultas guardadas, inferencia real de huellas y recorrido de la ventana en Linux. La etapa anterior fue demostrada por el autor en Windows con voz; no se atribuye esa ejecución a este nuevo preparador. La ampliación queda pendiente de comprobación Windows y la evaluación con personas nuevas sigue pendiente. No se cambiaron datasets, modelos, selección de características o umbral.

## Ajuste del flujo automático · 23/10/2026

A pedido del autor, ChatGPT ajustó la selección de base para generar automáticamente una captura con perfil existente y semilla aleatorios. Se mantuvo la elección manual en Opciones avanzadas para reproducción. No se combinan perfiles nuevos ni se consulta la autorización para elegir parámetros. Se ejecutaron 20 pruebas de software en Linux y se inspeccionó la ventana con sorteo y generador reales. Una prueba controla explícitamente el sorteo para verificar la coordinación. No constituye una nueva evaluación estadística ni validación acústica en Windows. Se conservaron modelos, umbrales y datasets.

## Cierre de interfaz y modelo combinado · 23/10/2026

A pedido del autor se prepararon diagnóstico, ajuste separado del módulo de huellas y documentación de cierre. Se reutilizaron normalización, extractor GLCM, selección, K-means y calibración existentes. El usuario generó las 150 impresiones en Anguli y ejecutó las herramientas en su Windows; el asistente trabajó sobre archivos recibidos y una copia del repositorio, sin acceso a su computadora.

La selección 144/72/36 se decidió con entrenamiento; se conservaron 36 columnas. Se congeló el modelo antes de evaluar el control 26–30. No se modificó después del falso rechazo A03/Impression_26. Se conservan pruebas Linux y archivos del control Windows por separado. La coincidencia Windows/Linux es reproducción del mismo ensayo, no aumento de la muestra independiente. La bitácora 08 solo lee configuraciones, hashes y evidencias; no entrena ni graba.

Se documenta el modelo como final de desarrollo para la muestra, conservando límites de fuentes/configuraciones, pruebas con personas nuevas y evaluación final pendientes. No se usaron subagentes, no se hizo push ni se reorganizaron archivos durante este cierre.
