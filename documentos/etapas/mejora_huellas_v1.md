# Mejora de correspondencia entre identidades y grupos

## Cambio implementado

Se conserva el extractor GLCM de 144 características, las bases/semillas, todas las muestras
y sus particiones. Se añade una selección de columnas para el modelo de huellas.
El extractor sigue produciendo 144 números; el modelo conserva y usa 72 en el corte actual.
No se modifica el notebook 06: queda como bitácora de la referencia completa.
El script nuevo no reemplaza modelos anteriores ni modifica archivos de audio.

La revisión remota de esta entrega encontró `main` en `9844b4a`, que ya incorpora la etapa 05.
Los extractores, configuración y catálogo de huellas no cambiaron respecto del corte anterior.
La etapa 06 usada es la entregada y ejecutada previamente por el autor.

## Fundamento

Para cada columna se reutiliza el indicador del notebook 05:

    S = suma_c n_c (media_c - media_global)^2 / suma_c suma_i (x_ic - media_c)^2

El numerador refleja diferencias entre medias de identidades. El denominador refleja
variación entre capturas de una misma identidad. Se ordena de mayor a menor S.
El indicador no cambia si una columna se expresa en otra escala lineal; no se comparan
desviaciones brutas de medidas con unidades distintas. Una DE alta por sí sola no justifica
descartar una columna. Se prioriza la relación entre separación e inestabilidad interna.
Los casos de dispersión interna nula y las constantes conservan estados explícitos.

Esta selección utiliza etiquetas de identidad de ENTRENAMIENTO: es selección supervisada.
El conjunto completo ya no debe describirse como un procedimiento puramente no supervisado.
K-means sí sigue siendo no supervisado: recibe únicamente los números seleccionados y
no recibe etiquetas ni centroides inicializados con las medias de identidad.
La correspondencia grupo-identidad se establece solo después del ajuste, con entrenamiento.

## Cómo se eligió la cantidad de columnas

Se limitó el experimento a tres variantes, definidas antes de consultar su nueva validación:

1. Todas las características (referencia).
2. La mejor mitad según S.
3. El mejor cuarto según S.

Las cantidades provienen de la dimensión real, sin fijar el número de muestras en código.
Se comparan en cinco pliegues estratificados dentro de entrenamiento. En cada pliegue se
vuelven a calcular el ranking y el escalador usando solo su subentrenamiento, se ajusta
K-means allí y se predice el pliegue retenido. No se calcula el ranking con todo entrenamiento
antes de evaluar los pliegues. Las etiquetas de la parte retenida se usan solo para evaluar.

Se elige el mayor ARI medio. Si empatan a 1e-12, se conserva la variante con más columnas,
para hacer el cambio más moderado. Después se vuelve a ajustar esa variante usando todo
entrenamiento, se guarda la decisión y se consulta la validación existente.
La variante de 36 no se evalúa luego en validación: no se elige entre 72 y 36 mirando esos datos.

Estas divisiones son un diagnóstico entre capturas sintéticas de tres bases ya conocidas.
Compartir una base por identidad es parte del problema de reconocer identidades conocidas;
NO permite afirmar generalización a nuevos dedos ni a biometría real. Los generadores de
ampliación consultados generan cada captura desde su base con semilla de muestra propia.
La validación existente ya se examinó en el desarrollo anterior y sigue siendo validación
de desarrollo. La prueba final se conserva para la evaluación posterior.

## Parámetros

Archivo `config/mejora_huellas_v1.json`. K-means mantiene k=3, k-means++, 20 inicializaciones,
300 iteraciones máximas, tolerancia 0.0001, algoritmo Lloyd y semilla 20261022.
Se informa además estabilidad con 20261022, 20261023 y 20261024; no se elige una semilla
por su mejor resultado de validación. Se estandariza por columna con ddof=0 usando
entrenamiento. PCA se ajusta con entrenamiento en las columnas elegidas y se usa para
dibujar, sin reducir las dimensiones que recibe K-means.

Fuentes técnicas oficiales:
- https://scikit-learn.org/stable/common_pitfalls.html
- https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedKFold.html
- https://scikit-learn.org/stable/modules/clustering.html

## Resultados realmente ejecutados

Entorno del asistente: Python 3.12.14/Linux, NumPy 2.3.5, SciPy 1.17.0, Pillow 12.3.0,
Matplotlib 3.10.8 y scikit-learn 1.8.0. Reutiliza el mismo contenido de imágenes y método de
extracción del corte que el autor ejecutó en Windows. No se afirma ejecución de esta mejora
en su computadora. Cambios de formato de código entre plataformas pueden cambiar el ID
de extracción sin cambiar el método; se conservan manifiesto y configuración efectivos.

| Variante | ARI medio CV interna | Coincidencia media CV interna |
|---|---:|---:|
| 144 columnas | 0.4161 | 60 % |
| Mejor mitad: 72 | 1.0000 | 100 % |
| Mejor cuarto: 36 | 1.0000 | 100 % |

Se eligieron 72 por empate. Ninguna captura se eliminó.

| Resultado final del desarrollo | Referencia 144 | Selección 72 |
|---|---:|---:|
| ARI entrenamiento, 120 muestras | 0.4477 | 1.0000 |
| Identificación entrenamiento | 79/120 = 65.83 % | 120/120 = 100 % |
| ARI validación, 30 autorizadas | 0.5436 | 1.0000 |
| Identificación validación | 21/30 = 70 % | 30/30 = 100 % |

En validación la variante obtuvo A01: 10/10; A02: 10/10; A03: 10/10. Las tres semillas
prefijadas produjeron ARI=1 y coincidencia=100 % para la selección, tanto en entrenamiento
como en validación. La referencia mantuvo su resultado anterior con las tres semillas.
Los perfiles de rotación y menor nitidez de entrenamiento se conservaron y se identificaron
correctamente en la variante. El detalle por perfil está en `resultados_por_perfil.csv`.

Se seleccionaron 32 medidas de correlación, 21 de contraste y 19 de homogeneidad.
Ninguna de las 36 de energía quedó en la mejor mitad, por su posición en ESTE ranking.
No se programó excluir energía ni se concluye que sea una medida inútil en otros datasets.
Las 72 exclusiones son columnas de entrada al modelo, no capturas ni identidades.
La lista exacta y sus razones están en `ranking_y_seleccion.csv`.

## Cómo leer las dos figuras

`comparacion_grupos.png`: utiliza el MISMO PCA de las 144 columnas de referencia en todos
los paneles. Arriba aparecen los grupos anteriores; abajo, los de la selección. Las posiciones
de los puntos no cambian: cambia su asignación. La numeración de grupos es arbitraria.
Que dos colores se acerquen en este plano no implica confusión del nuevo modelo en 72D.

`pca_seleccionada.png`: PCA nuevo ajustado en las 72 columnas de entrenamiento. Arriba
colorea por identidad real; abajo, por grupo predicho. Columnas: entrenamiento y validación.
Los centroides se proyectan con ese mismo PCA. Las posiciones se recalculan y no deben
compararse coordenada a coordenada con el PCA anterior. PC1 y PC2 conservan el 80.85 % de
la variación del espacio seleccionado, que es distinto del espacio original.
La mejora se respalda con ARI y correspondencia, no solo con la apariencia de las figuras.

## Ejecución en Windows / PowerShell

Copiar el contenido de `archivos/` del ZIP dentro de la raíz del proyecto, conservando
sus subcarpetas. Son cuatro archivos nuevos; no hay un instalador PowerShell ni cambios
al notebook. El directorio `referencia_ejecutada/` es evidencia del asistente: no es necesario
copiarlo al proyecto, porque la ejecución local generará su propia carpeta de resultados.

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_mejora_huellas.py -v
.\.venv\Scripts\python.exe src/mejorar_clusterizacion_huellas.py
```

No hay dependencias nuevas respecto de la etapa 06. Si falta scikit-learn, utilizar el
archivo `requirements-clusterizacion.txt` de esa etapa. Si el cargador informa que no hay
extracción de huellas compatible, regenerar únicamente la extracción de desarrollo:

```powershell
.\.venv\Scripts\python.exe src/extraer_dataset_huellas.py
.\.venv\Scripts\python.exe src/mejorar_clusterizacion_huellas.py
```

No ejecutar `--incluir-prueba`. No regenerar bases ni modificar particiones.
Se requiere `src/clusterizacion_pca.py` de la entrega anterior y el módulo de etapa 05.
La extracción se elige por compatibilidad con configuración, código y catálogo vigentes;
es posible indicar `--extraccion "datos/caracteristicas/huellas/.../ejecucion_..."`.

El comando imprime la carpeta creada en `resultados/mejora_huellas/FECHA/`, las cantidades
seleccionadas, CV interna y los resultados por partición e identidad. Si no hay validación,
solo se documentará entrenamiento y no se afirmará confirmación en validación.

## Reutilización con nuevas muestras

El futuro flujo sigue extrayendo las 144 características en su orden original.
La función `transformar` aplica índices guardados, escalado y modelo sin reajustar nada.

```python
import pickle
from mejorar_clusterizacion_huellas import transformar

# Ruta real de la ejecución elegida. Cargar solo modelos propios y con el entorno registrado.
with open(r"resultados/mejora_huellas/FECHA/seleccionada/modelo.pkl", "rb") as f:
    modelo = pickle.load(f)

# X_nuevas: matriz (n, 144) obtenida con el extractor vigente.
# nombres: las 144 etiquetas de columnas en su orden original.
resultado = transformar(X_nuevas, nombres, modelo)
print(resultado["grupos"], resultado["identidades"])
```

El modelo se guarda también en `parametros.npz` (índices, nombres, medias, escalas,
centroides y componentes PCA) y `correspondencia.json`. Las etiquetas no se necesitan
para transformar una nueva muestra. La identidad asignada NO autoriza acceso.

## Límites y próximo paso

El 100 % corresponde únicamente a las muestras autorizadas del desarrollo actual.
No se analizaron intrusos ni prueba, y no se ha calibrado un umbral de aceptación.
La selección puede reducir discriminación frente a intrusos que aún no se evaluaron;
habrá que comprobarlo durante calibración con los intrusos de validación.
La lista elegida debe congelarse para esa siguiente etapa, documentando cualquier cambio.
No seguir reduciendo hasta lograr gráficos más bonitos: la variante de 72 ya cumple
el objetivo actual de correspondencia en el desarrollo disponible.

Compartir la carpeta local comprimida o, como mínimo, `resumen.json`,
`comparacion_cv_train.csv`, `estabilidad.csv` y las dos figuras.
En el notebook final se documentarán referencia, motivo del cambio y resultado de la mejora;
no se borrará el antecedente de 144 columnas.

Pruebas automatizadas: invariancia del ranking frente a unidades, tratamiento de constantes,
selección/escalado dentro de cada pliegue, ausencia de etiquetas en K-means cuando no hay
selección, recarga de modelos, orden de columnas y transformación sin reajuste.
Se utilizó asistencia de IA para implementación y explicación; incorporar esta intervención
y los controles ejecutados a `documentos/uso_ia_generativa.md` al cerrar la bitácora.

## Commits pequeños sugeridos

```powershell
git status --short
git add config/mejora_huellas_v1.json src/mejorar_clusterizacion_huellas.py tests/test_mejora_huellas.py
git commit -m "Seleccionar caracteristicas de huellas solo con entrenamiento para mejorar K-means"
git add documentos/etapas/mejora_huellas_v1.md
git commit -m "Documentar la comparacion con 144 columnas y los limites de la mejora"
```

La etapa 06 previa debe versionarse por separado si todavía está sin guardar.
Revisar `git diff --cached` antes de confirmar. Evitar `git add .` para no añadir todos
los resultados/modelos locales. No hubo push automático.
