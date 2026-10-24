# Cierre de desarrollo: PCA, K-means y rechazo

## Qué queda terminado

La referencia con 144 características, la mejora que conserva 72 y la calibración del
rechazo están implementadas y verificadas en los cortes de desarrollo compartidos.
Se conserva k=3 y las mismas identidades y capturas. La versión se registra sin purgar
muestras ni continuar probando opciones hasta obtener cero errores en validación.
La evaluación final independiente, K-NN de audio e integración siguen pendientes.

El notebook 06 actualizado es una bitácora de SOLO LECTURA: muestra evidencia publicada
y recalcula verificaciones aritméticas sencillas a partir de las tablas guardadas.
No ejecuta ajustar/fit, no calibra un nuevo umbral, no transforma prueba y no genera
carpetas de modelos al abrirlo. Sus salidas están guardadas para lectura en GitHub.

## Distancia utilizada

Una imagen se vectoriza a 144 componentes, se toman las 72 columnas guardadas y se
estandarizan con las medias y escalas aprendidas en entrenamiento. Para cada centroide:

    d_k = sqrt(sum_j (z_j - centroide_kj)^2), j = 1,...,72
    d_min = min(d_0, d_1, d_2)

Es distancia euclidiana en 72 dimensiones estandarizadas. No es porcentaje de parecido,
distancia entre píxeles ni distancia medida en el plano PC1-PC2. Los centroides quedan
fijos al evaluar muestras. Un empate exacto usa el centroide de menor índice.

## De dónde salen 51 candidatos

En la calibración hay 30 autorizados y 20 intrusos de validación: 50 distancias mínimas.
En este corte las 50 son distintas. Ordenándolas de menor a mayor t1,...,t50, se probaron:

    0,
    (t1+t2)/2, (t2+t3)/2, ... , (t49+t50)/2,
    t50

Hay 1 + 49 + 1 = 51 UMBRALES candidatos. No son grupos, columnas, centroides ni muestras
adicionales. El cero y el máximo cubren los extremos de decisión para estas distancias;
entre dos distancias consecutivas las decisiones sobre las muestras actuales no cambian.
Si hubiera distancias repetidas, se usa la cantidad de valores distintos: u+1 candidatos
cuando u>1 y el mínimo es positivo. No es una cantidad fija programada como 51.

Para cada candidato se calcula FAR (intrusos aceptados / total intrusos) y FRR
(autorizados rechazados / total autorizados). Se minimiza (FAR+FRR)/2. En un empate
se prefiere menor FAR y después menor umbral. Esta es una política de desarrollo con
igual peso para ambas tasas, no un requisito universal de seguridad.

El resultado fue tau=5.292172575840761: 29/30 autorizados aceptados, 0/20 intrusos
aceptados, FAR=0 %, FRR=3.33 %. A02_M22 es un falso rechazo conservado.
Los otros 29 autorizados llegan a distancia 4.3614 y el intruso más cercano a 6.2230;
el punto medio entre esos valores produce el umbral elegido. A02_M22 llega a 10.7699.

## Por qué se usan 30 autorizadas y no las 120 de entrenamiento

Las 120 de entrenamiento se usaron para seleccionar columnas, estimar el escalado y
ajustar los tres centroides. También para establecer su correspondencia con identidades.
Como los centroides se adaptaron a ellas, usarlas para comprobar aceptación podría
dar una impresión optimista. Las 30 autorizadas de validación permiten medir la distancia
de capturas que no movieron los centroides. Se agregan 20 intrusos de validación para
estudiar falsas aceptaciones.

La elección del umbral ES un ajuste de un parámetro, aunque no vuelva a entrenar K-means.
Por ello se reportan métricas de calibración, no de prueba final independiente.
La selección de 72 columnas se eligió con CV interna SOLO de entrenamiento. Los resultados
de validación se usaron para comprobar esa versión y luego para calibrar el rechazo.

## Probar una sola huella

El umbral no se define a partir de esa única huella. Se reutilizan el modelo y el umbral
guardados durante desarrollo. La captura no necesita etiqueta real para decidir:

    imagen -> vector 144 -> selección 72 -> escalado guardado -> distancias a 3 centros
           -> d_min <= tau: AUTORIZADO e identidad; en otro caso: NO AUTORIZADO

Para el sistema calibrado localmente, ver cargar_sistema y decidir_acceso en
src/calibrar_rechazo_huellas.py. La carpeta de calibración contiene todo lo necesario
para las distancias. La evidencia publicada incluye el NPZ/JSON exacto de Windows
y permite probar vectores nuevos sin depender de carpetas locales históricas:

```python
from calibrar_rechazo_huellas import cargar_sistema, decidir_acceso

modelo, tau = cargar_sistema("documentos/evidencias/06_huellas_referencia/03_rechazo")
# X_nueva: matriz (1, 144) del extractor vigente; nombres: las 144 columnas en orden.
decision = decidir_acceso(X_nueva, nombres, modelo, tau)[0]
print(decision["estado"], decision["identidad"], decision["distancia"])
```

No ejecutar fit con la nueva huella ni reemplazar tau por su distancia: así se alteraría
la regla antes de decidir. La interfaz/captura de imágenes aún no está integrada.

## Qué copiar y ejecutar

Copiar el contenido de `archivos/` del paquete dentro de la raíz del repositorio.
Se actualizan README, índice, registro de IA, .gitignore y notebook 06; se incluyen
los módulos/configuraciones/documentos/tests completos de esta etapa, iguales a las
versiones verificadas, para que no falte código al publicarlo.

El paquete parte del README de main en 9844b4a, que llegaba a la etapa 05. Si se
modificaron esos documentos localmente después, conservar una copia y comparar antes
de reemplazar. No se modifican datos, extractores ni revisiones de audio.

En VS Code, seleccionar .venv y ejecutar todas las celdas del notebook 06. Solo consulta
documentos/evidencias/06_huellas_referencia y no requiere matrices locales ni cargar pickle.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_clusterizacion_pca.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_mejora_huellas.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_rechazo_huellas.py -v
```

Las instrucciones de reproducción del análisis completo se conservan en los documentos
de las tres etapas. No es necesario repetirlas para cerrar la bitácora ni subir a Git.

## Publicación y alcance

Las carpetas completas de ejecución siguen locales bajo resultados/. Se publica una
selección de tablas, gráficos y resúmenes, más el modelo NPZ y el umbral congelados de
Windows. No se publica pickle. El manifiesto de evidencias conserva los hashes y el
nombre del ZIP fuente para cada archivo seleccionado. Los resúmenes originales pueden
referenciar otros archivos de las ejecuciones completas que no se publican aquí.

No se presenta el 100 % de identificación como 100 % de control de acceso. El 0/20 de
intrusos aceptados corresponde a dos bases sintéticas y no garantiza FAR real igual a cero.
La muestra A02_M22 no se elimina. Prueba final continúa reservada; no se debe usar para
reajustar la versión y luego conservar la etiqueta de evaluación independiente.
