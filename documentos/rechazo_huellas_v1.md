# Calibración del rechazo de intrusos

## Objetivo y alcance

Se agrega una regla de aceptación/rechazo a la clasificación de huellas autorizadas.
Se reutiliza el modelo congelado de 72 características de la etapa anterior: selección,
escalador, centroides y correspondencia grupo-identidad. No se ajusta nuevamente K-means
ni PCA y no se modifica el extractor ni la bitácora 06. El audio queda para su etapa posterior.

El script usa exclusivamente las muestras de VALIDACIÓN para calibrar el umbral:
30 autorizadas y 20 intrusas (dos bases intrusas) en el corte disponible. Esas cantidades
se obtienen del catálogo; no se fijan en el código. Los metadatos de prueba se comprueban
solo para verificar que sus intrusos tengan bases distintas; no se leen ni transforman
sus imágenes/vectores ni se calculan resultados sobre prueba.

La última extracción de desarrollo ya contiene los vectores de los intrusos de validación.
No hace falta generar nuevas identidades ni volver a vectorizar si ese corte es compatible.

## Método

Para una muestra nueva se calcula el vector completo de 144 características y se toman
las 72 columnas guardadas. Se aplica el escalado de entrenamiento y se calcula:

    d_min = min_k ||z - centroide_k||_2, para k = 0, 1, 2

Se acepta si d_min <= tau. Si se acepta, la identidad corresponde al centroide más cercano
según el mapa ya aprendido. Si se rechaza, se devuelve NO AUTORIZADO e identidad vacía.
La distancia se mide en el espacio estandarizado de 72 columnas, no en el PCA dibujado.
La igualdad en el límite se acepta; un empate exacto entre centroides usa el menor índice.

El modelo y la calibración se cargan desde NPZ/JSON, sin ejecutar pickle.
El sistema no necesita conocer la identidad real de la nueva muestra para decidir.
Las etiquetas reales de validación solo se usan para elegir el umbral y medir sus errores.

## Dos tipos de error

- FAR = intrusos aceptados / intrusos de validación.
- FRR = autorizados rechazados / autorizados de validación.

Son tasas empíricas por presentación para este sistema de identificación con rechazo.
No se presentan como estimaciones certificadas de FMR/FNMR ni de seguridad biométrica real.
Las presentaciones de una misma base sintética no son personas independientes.

Un umbral pequeño suele reducir falsas aceptaciones, pero rechaza más autorizados.
Uno grande facilita la aceptación de autorizados, pero puede admitir intrusos.
Se eligió un único umbral global mediante el criterio explícito:

    BER = (FAR + FRR) / 2

Se minimiza BER en validación. Si empatan a 1e-12, se elige menor FAR y luego menor umbral.
Este criterio da el mismo peso a las tasas de ambos grupos, aunque haya 30 autorizados
y 20 intrusos. Es una referencia de desarrollo, no una política de seguridad universal.
No se fuerza FAR=0 mediante una regla oculta ni se exige que FAR=FRR.

Se consideran cero, los puntos medios entre distancias observadas consecutivas distintas
y la distancia máxima. Cada intervalo produce la misma decisión sobre las muestras actuales;
usar su punto medio evita colocar la frontera arbitrariamente sobre una muestra.
Cuando no hay una brecha limpia, se documenta el error residual sin eliminar capturas.

Fuentes generales:
- https://scikit-learn.org/stable/modules/classification_threshold.html
- https://www.nist.gov/blogs/taking-measure/tale-two-errors-measuring-biometric-algorithms

## Resultados ejecutados por el asistente

Modelo: el NPZ/JSON congelado de la ejecución del autor `20261023T014705_319737Z`.
Los vectores se reprodujeron con los mismos extractores y datos publicados.
Entorno de esta calibración: Python 3.12.14/Linux; no se afirma haber ejecutado en Windows.
La compatibilidad con los nombres, columnas y escalado del modelo se comprobó sin reajustarlos.

| Resultado de calibración | Valor |
|---|---:|
| Umbral euclidiano global | 5.292172576 |
| Autorizados aceptados | 29/30 |
| Autorizados rechazados | 1/30 |
| Intrusos aceptados | 0/20 |
| Intrusos rechazados | 20/20 |
| FAR empírica | 0 % |
| FRR empírica | 3.33 % |
| BER | 1.67 % |
| Identidades incorrectas entre los aceptados | 0 |

A01: 10/10 aceptadas; A02: 9/10; A03: 10/10. El falso rechazo es A02_M22,
perfil local_moderada. Su distancia es 10.769863515, aunque su centroide más cercano
sí corresponde a A02. La muestra sigue conservada; no se excluyó para mejorar métricas.

Esto no contradice el 30/30 anterior: ese resultado evaluaba cuál identidad autorizada
quedaba más cerca. Ahora se agrega la condición de estar suficientemente cerca.

La mayor distancia autorizada es 10.7699; la menor intrusa es 6.2230. Hay solapamiento:
ningún umbral global de esta distancia puede separar perfectamente las 50 presentaciones.
El umbral elegido está entre la mayor distancia de los otros 29 autorizados (4.3614)
y la menor distancia intrusa (6.2230). Aceptar A02_M22 con un umbral global requeriría
aceptar también las diez presentaciones intrusas que tienen distancia menor que ella.

No se ensayaron umbrales por identidad ni otros criterios hasta obtener un resultado perfecto.
Esa alternativa requeriría un experimento separado y más evidencia, especialmente porque
la cantidad de bases intrusas actuales es pequeña. Por ahora se documenta esta referencia.

## Ejecución en Windows / PowerShell

Copiar el contenido de `archivos/` del ZIP dentro de la raíz de Trabajo-Final-IA1,
conservando subcarpetas. Son cuatro archivos nuevos. No hay instalador PowerShell.
No es necesario copiar `referencia_ejecutada/`: documenta la ejecución del asistente.

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_rechazo_huellas.py -v
.\.venv\Scripts\python.exe src/calibrar_rechazo_huellas.py
```

No hay dependencias nuevas. El comando reutiliza la última ejecución de mejora_huellas.
Para elegir explícitamente el modelo que ya verificamos:

```powershell
.\.venv\Scripts\python.exe src/calibrar_rechazo_huellas.py --modelo "resultados/mejora_huellas/20261023T014705_319737Z"
```

Usar la carpeta de la ejecución completa, no la subcarpeta `seleccionada`.
No volver a ejecutar mejorar_clusterizacion_huellas.py para esta calibración.
Si el cargador informa ausencia de una extracción compatible, regenerar solo desarrollo:

```powershell
.\.venv\Scripts\python.exe src/extraer_dataset_huellas.py
.\.venv\Scripts\python.exe src/calibrar_rechazo_huellas.py --modelo "resultados/mejora_huellas/20261023T014705_319737Z"
```

No utilizar `--incluir-prueba`. Si cambian las muestras de entrenamiento, sus imágenes
o las columnas, el programa detiene la calibración en vez de mezclar modelos y datos.

## Salidas y gráficos

Se crea una carpeta nueva en `resultados/rechazo_huellas/FECHA/`:

- `resumen.json`: procedencia, cantidades y métricas, con prueba_evaluada=false.
- `umbral.json`: umbral, regla y criterio; mantenerlo junto al modelo congelado.
- `modelo_congelado.npz` y `correspondencia_congelada.json`: copia exacta de los parámetros usados.
- `decisiones_validacion.csv`: distancia, grupo cercano, decisión e identidad visible por muestra.
- `errores_validacion.csv`: errores explícitos, incluida A02_M22.
- `matriz_acceso.csv` y `resultados_por_identidad.csv`: resultados por condición e identidad.
- `tasas_por_umbral.csv`: todos los candidatos evaluados; permite auditar la selección.
- `catalogo_uso.csv`: registra calibración, entrenamiento usado solo como control de compatibilidad,
  y la reserva de prueba.
- `distancias_validacion.png`: cada punto es una muestra; la línea vertical marca el umbral.
  A la izquierda se acepta y a la derecha se rechaza. Azul: autorizados; rojo: intrusos.
- `tasas_por_umbral.png`: FAR y FRR en función del umbral. Las curvas son escalonadas
  porque las decisiones cambian al atravesar distancias observadas.

La calibración no produce nuevos gráficos PCA porque la decisión se hace por distancia
en 72 dimensiones. El notebook 06 se conserva y se actualizará al cerrar la documentación.

## Usar el sistema con futuros vectores

```python
from calibrar_rechazo_huellas import cargar_sistema, decidir_acceso

modelo, umbral = cargar_sistema(r"resultados/rechazo_huellas/FECHA")
# X_nuevas: matriz (n, 144) del extractor vigente, sin escalar manualmente.
# nombres: las 144 etiquetas de columnas en su orden original.
decisiones = decidir_acceso(X_nuevas, nombres, modelo, umbral)
for decision in decisiones:
    print(decision["estado"], decision["identidad"], decision["distancia"])
```

Esta función no usa etiquetas reales ni vuelve a ajustar parámetros. Un error de formato
o un vector no finito produce un error de entrada, no se confunde con una huella intrusa.
La captura/interfaz y la conexión con los comandos de voz siguen pendientes.

## Límites y continuación

Estas métricas provienen de los mismos datos usados para calibrar el umbral.
No constituyen una evaluación final independiente. Un FAR observado de 0/20 no garantiza
rechazar cualquier intruso: solo se analizaron dos bases intrusas con variantes sintéticas.
La prueba reservada mantiene sus imágenes/vectores sin evaluar.

Compartir la carpeta de calibración comprimida para verificar el resultado local. Una vez
confirmada la regla, se podrá congelar y diseñar la evaluación final. Si se utiliza prueba,
no deberá usarse luego para reajustar el umbral conservando la etiqueta de evaluación final.
Mientras tanto, puede avanzarse con K-NN de audio e integración.

Cinco pruebas específicas verifican separación limpia, solapamiento y desempate,
distancias idénticas, igualdad en el umbral, identidad oculta al rechazar, ausencia
de reajuste y exclusión de entrenamiento/prueba de la calibración.
La asistencia de IA y estos controles se documentarán en la bitácora final.

## Commits sugeridos

```powershell
git status --short
git add config/rechazo_huellas_v1.json src/calibrar_rechazo_huellas.py tests/test_rechazo_huellas.py
git commit -m "Calibrar rechazo de huellas con validacion sin reajustar el modelo"
git add documentos/rechazo_huellas_v1.md
git commit -m "Documentar falsas aceptaciones y rechazos de la calibracion"
```

Revisar git diff --cached antes de confirmar. No usar git add . para evitar incorporar
todos los modelos/resultados locales. No hubo push automático.
