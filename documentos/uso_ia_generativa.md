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
