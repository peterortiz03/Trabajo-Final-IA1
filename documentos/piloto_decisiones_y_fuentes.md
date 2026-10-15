# Registro del piloto — 15/10/2026

## Evidencia de Anguli

Se compararon los ZIP aportados por el usuario, no una instalación de Anguli del asistente.
Base e impresión de piloto_01 (semilla 101) son idénticas a las de piloto_01_repeticion:
0 píxeles diferentes y SHA-256 de archivo idéntico en ambos casos. La segunda base (202)
es diferente. Esta evidencia corresponde a dos ejecuciones del entorno del usuario;
no garantiza repetibilidad universal entre versiones, máquinas o números de hilos.

| Imagen | SHA-256 |
|---|---|
| Base 101 y repetición | f3c10c83760a1f1bc52e01db07c6d21326863a277217948f5ebf98c19ec2c91b |
| Impresión 101 y repetición | bf34b49f021f3cfecba366170bfd6feb5e04e9dc985c4f83127f316621ffc24a |
| Base 202 | 88dd8cb903a1b80254e6aa30c9617b30a4aa3d4cf756dc955012175e17d33a6b |
| Impresión 202 | 3b01ddfadae983fea886527e47e243f78f3816bffd7bdb9069921c05e83b1c84 |

Ambas bases: PNG L8 275×400, valores 0 y 255. Metadatos: Right Loop para 101,
Double Loop para 202. Cada configuración indica 1 huella, 1 impresión, 1 hilo, semilla
personalizada y rotación/traslación/ruido/rayaduras en cero. Las impresiones presentan
contorno de contacto e interrupciones aun con esos controles en cero.

La versión del ejecutable de Anguli no está identificada en los archivos recibidos: queda
pendiente registrar About, distribución descargada y, preferiblemente, hash del ejecutable.
No se inventó una versión. Los OutDir de las dos ejecuciones nuevas contienen nombres
anteriores de carpeta; se conservan sin editar como evidencia de procedencia.

## Decisiones

- Se usan las bases limpias para aislar el efecto de la deformación. El realismo de contacto,
  presión, cortes parciales y preprocesamiento final quedan pendientes.
- Dos identidades y cuatro muestras por identidad; no entrenar ni evaluar clasificadores.
- Los tipos morfológicos distintos son accidentales en este piloto. En el conjunto final
  evitar que la morfología se convierta en una etiqueta exclusiva de identidad/autorización.
- Cinco desplazamientos gaussianos aleatorios forman un campo suave. Se atenúa en bordes
  y se normaliza a 2.5 px (leve) o 5 px (moderada), reduciéndolo si el gradiente es excesivo.
- Los perfiles son propuestas iniciales conservadoras, no parámetros óptimos medidos.
- M01: local leve. M02: local moderada. M03: local leve + rotación hasta ±2° y traslación
  hasta ±2 px por eje. M04: local moderada + desenfoque sigma 0.35 px y ruido sigma 1.5/255.
- El muestreo inverso usa coordenadas variables con la posición y una interpolación lineal.
  Por ello se comprimen o estiran zonas de manera desigual. No equivale a una escala global.
- Se controla el determinante del Jacobiano del mapeo de muestreo. Es una comprobación
  numérica geométrica, no una certificación de conservación de todas las minucias tras
  discretizar. La revisión visual sigue siendo necesaria.
- Preparación mínima: escala de grises de 8 bits y tamaño nativo; sin ROI, normalización
  de contraste, filtrado común, binarización nueva ni esqueletizado en esta etapa.
- Semillas PCG64 independientes por muestra. Se registra código, configuración, parámetros
  efectivos y entorno. Un campo procesado vacío significa que esa etapa no se ejecutó.
- Se comprueba duplicación exacta; aún no hay particiones ni un análisis de casi duplicados.

## Fuentes técnicas primarias

- Anguli, guía oficial: https://dsl.cds.iisc.ac.in/projects/Anguli/userguide.html
- SciPy, map_coordinates: https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.map_coordinates.html
- Paquetes de las versiones usadas, consultados el 15/10/2026:
  https://pypi.org/project/numpy/2.3.5/
  https://pypi.org/project/scipy/1.17.0/
  https://pypi.org/project/pillow/12.3.0/
  https://pypi.org/project/matplotlib/3.10.8/

## Uso de IA y verificaciones

ChatGPT asistió en la revisión de archivos, propuesta del piloto, generación del código,
documentación y pruebas. Pedido del usuario: «te subo las nuevaas 2 carpetas, como continuo?».
El contexto previo exigió bases especializadas, deformaciones no lineales, semillas por
muestra, conservación de originales y avance por hitos, sin implementar reconocimiento.

Se ejecutó el programa con copias de las dos bases en Linux/Python 3.12.14, NumPy 2.3.5,
SciPy 1.17.0, Pillow 12.3.0 y Matplotlib 3.10.8. Se obtuvieron ocho variantes distintas,
repetición exacta dentro del proceso y regeneración de P01_M02 en un proceso independiente
idéntica byte a byte a su salida en lote. Determinantes mínimos/máximos globales observados:
0.87626 y 1.12538. Se inspeccionó la comparación visual: estructura general conservada y
variación local suave. La validación local en Windows y la aceptación visual del usuario
siguen pendientes. No se generó el conjunto completo ni se probó ningún reconocedor.
