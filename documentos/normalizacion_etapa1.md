# Normalización — etapa 1: región de interés y centrado

## Alcance

Función reutilizable para una imagen, más ejecutable que la llama sobre desarrollo.
No implementa orientación, reescala, corrección de deformación, normalización de contraste,
binarización de crestas, esqueletizado ni reconocimiento. Son salidas intermedias, no la
normalización final. Una huella horizontal debe seguir horizontal en este paso.

Copiar src/, config/ y documentos/ a la raíz del repositorio existente. Los archivos son
nuevos: no reemplazar otros sin revisar. No se requieren paquetes adicionales a requirements.txt.
Los dos scripts son independientes de los generadores. La función solo necesita NumPy,
Pillow y SciPy; el ejecutable agrega Matplotlib para comparaciones.

## Primera ejecución: 20 muestras seleccionadas de antemano

Desde PowerShell en la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe src/normalizar_dataset.py
```

Lee datos/metadatos_con_rotaciones_train_v1.csv (catálogo de 220), pero procesa solo:
A01/A02/A03 M21, M41, M45, M47, M51 y M55, más I01_M01 e I02_M01.
Son 20 casos de desarrollo que cubren contraste, desenfoque, deformación, tamaños distintos
y rotación de −90° y −15°. No se seleccionan por éxito y no se usa la prueba final.

Salida de referencia comprobada por el asistente:
solicitadas=20, correctas=20, revisar=0, errores=0.
normalizacion_completa=false es ESPERADO: faltan las siguientes etapas.

Todo se guarda bajo resultados/normalizacion_etapa1/:

- imagenes/: 20 PNG centrados, 512×512, en escala de grises.
- mascaras/: máscara en coordenadas de entrada y máscara desplazada a la salida.
- comparaciones/: cuatro páginas, cinco muestras por página, tres columnas.
- detalle.json: coordenadas, cobertura, desplazamiento, avisos, hashes y rutas.
- resumen.json, config_efectiva.json y entorno.json.

No se escriben datos/procesados ni los catálogos maestros. No se modifica ninguna imagen
original. Si la carpeta ya existe se detiene antes de escribir. Para repetir con otro destino:

```powershell
.\.venv\Scripts\python.exe src/normalizar_dataset.py --salida normalizacion_etapa1_repeticion
```

Después de revisar las primeras 20 se puede ejecutar sobre TODO desarrollo:

```powershell
.\.venv\Scripts\python.exe src/normalizar_dataset.py --todas-desarrollo --salida normalizacion_etapa1_desarrollo
```

Ese comando procesa 170: 120 entrenamiento + 50 validación. Nunca procesa prueba ni reservas.
En el control del asistente produjo 168 casos sin aviso y dos a revisar (A01_M43, A02_M44),
ambos por llegar la región a un borde de entrada. Cero errores. Las comparaciones siguen
mostrando las mismas 20 preseleccionadas; revisar también los dos casos avisados abriendo
su original (ruta en detalle.json), máscara y salida. Un aviso no implica por sí solo descarte.
No abrir la prueba final para decidir cambios en estos parámetros.

## Qué hace la función

1. Convierte a escala de grises de 8 bits (y compone transparencias sobre blanco si existen).
2. Estima fondo y contraste desde la propia imagen: percentiles 98 y 2.
3. Suaviza una copia con sigma=2 px SOLO para detectar la región; no suaviza la imagen de salida.
4. Detecta zonas más oscuras que el fondo usando un umbral relativo al contraste.
5. Aplica cierre morfológico a la máscara para unir huecos pequeños, elige la mayor región
   conectada y rellena sus huecos para representar el área del dedo, no cada cresta por separado.
6. Amplía la máscara 6 px como margen conservador; añade un margen de recorte de 8 px.
7. Reemplaza por blanco lo que queda fuera de la máscara.
8. Traslada la región a un lienzo blanco de 512×512, centrando su rectángulo envolvente.

La máscara es binaria; la huella de salida NO lo es. Las operaciones morfológicas se aplican
solo a la máscara, nunca a las crestas. Se conservan exactamente los valores de gris de los
píxeles que pertenecen a la máscara, moviéndolos un número entero de píxeles.

El centro usado es el centro del rectángulo que contiene la región, no el núcleo de la huella,
ni su centro anatómico ni un punto de minucias. El error de colocación del centro del rectángulo
es como máximo medio píxel por eje. Es una alineación inicial; no garantiza registro fino entre
impresiones con recortes/deformaciones distintos.

No se usa identidad, etiqueta de autorizado/intruso, semilla, base ni ángulo de generación.
El ejecutable utiliza los metadatos solo para elegir desarrollo, localizar los originales y
comprobar sus hashes. No aprende estadísticas conjuntas de los archivos de validación/prueba.

## Cómo llamarla desde otro programa

Desde otro .py ubicado dentro de src/:

```python
import json
from pathlib import Path
from PIL import Image
from normalizacion import normalizar_huella

raiz = Path(__file__).resolve().parents[1]
config = json.loads((raiz / 'config/normalizacion_etapa1.json').read_text(encoding='utf-8'))
with Image.open(raiz / 'datos/originales/conjunto_v1/validacion/A01/A01_M21.png') as imagen:
    normalizada, info = normalizar_huella(imagen, config)

print(normalizada.shape)  # (512, 512)
print(info['avisos'])
# normalizada queda disponible para la siguiente etapa, todavía no implementada.
```

Acepta PIL.Image o array NumPy uint8 en gris/RGB/RGBA. Devuelve imagen NumPy uint8 e información.
El diccionario info contiene dos arrays booleanos (mascara_original y mascara_normalizada);
el resto es serializable en JSON. El ejecutable guarda las máscaras aparte y los números en JSON.
Importar normalizacion no procesa archivos ni escribe resultados. Ante una entrada vacía,
contraste insuficiente, región demasiado pequeña o que no cabe, se lanza ValueError. El programa
que la use debe comunicar ese fallo en lugar de enviar una falsa huella normalizada al reconocedor.

## Qué analizar en cada página

| Columna | Interpretación | Señal de problema |
|---|---|---|
| Original + contorno azul | Imagen de entrada y límite detectado | Contorno corta crestas o encierra mucho fondo |
| Máscara | Blanco: región conservada; negro: fondo descartado | Fragmentación, agujeros grandes o región equivocada |
| Centrada | Resultado y líneas guía del centro del lienzo | Corte nuevo, deformación o cambio de tamaño de las crestas |

Las tres columnas se dibujan con la MISMA escala de píxeles (ejes de 0 a 512), para evitar que
Matplotlib amplíe cada recorte por separado. En las entradas 275×400 queda espacio blanco porque
se muestran sobre los mismos límites; el tamaño de los píxeles de imagen no se ha cambiado.
Las líneas de centro y el contorno azul aparecen solo en los gráficos, no en los PNG de salida.

Revisar en especial:

- M45: huella tenue, la máscara no debe perder regiones por menor contraste.
- M47: huella borrosa, no debemos añadir desenfoque a la salida.
- M51: huella horizontal, debe seguir horizontal y completa.
- M55: inclinada, debe mantener esa inclinación hasta la etapa de orientación.
- I01/I02: el procedimiento también debe funcionar sin saber que son intrusos.

En detalle.json, cobertura_tinta es la fracción de píxeles suficientemente oscuros contenidos
por la máscara; 1 equivale a 100%. No certifica conservación de todas las crestas débiles ni
calidad biométrica. La cercanía a los bordes puede deberse al margen o a un recorte ya presente.
El centrado no reconstruye lo que falta en el original. No descartar automáticamente avisos.

## Supuestos, pruebas y siguiente paso

Este primer algoritmo está dirigido al conjunto sintético actual: una huella oscura sobre
fondo claro, mayor región conectada. No se afirma que funcione para huellas claras sobre fondo
oscuro, múltiples dedos, manchas dominantes o sensores arbitrarios. La escala se preserva en
píxeles; no se ha calibrado una escala física en DPI para futuros dispositivos.

Pruebas del asistente: ejecución sobre las 20 seleccionadas y las 170 de desarrollo, conservación
exacta de los píxeles dentro de máscara, entrada no modificada, conversión RGB equivalente,
centrado de hasta 0.5 px y rechazo de imagen blanca. Se inspeccionó visualmente una página de
rotaciones. Cobertura de tinta del control de desarrollo: 1.0 en todos los casos. Entorno:
Linux/Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, Pillow 12.3.0, Matplotlib 3.10.8.
La ejecución local de este código nuevo en Windows queda pendiente de comprobar.

Primero revisar esta etapa. Luego se desarrollará orientación desde la imagen, sin consultar
los ángulos de generación. No usar todavía estas salidas como normalización final ni iniciar
el reconocedor; no corregir orientación con los metadatos.

Enviar un ZIP de resultados/normalizacion_etapa1 y la salida de la terminal, indicando si se
observan cortes, máscaras incorrectas o cambios de escala. Conservamos originales y todas las
versiones procesadas anteriores como evidencia, sin sustituirlas.

Issue: `Validar deteccion de ROI y centrado sin reescala`.
Cierre: ejecución local, revisión de las 20 muestras, explicación de avisos y verificación de
conservación de estructura. Commits pequeños sugeridos: `feat: detectar ROI y centrar sin reescalar`
y `docs: registrar revision de normalizacion etapa 1`. Sin push automático.

Fuentes primarias de las operaciones de máscara:
https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.binary_closing.html
https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.binary_fill_holes.html
Los umbrales, márgenes y selección de muestras son decisiones de este proyecto, no especificaciones
de esas fuentes. ChatGPT generó el código y las pruebas en respuesta al pedido de archivos,
instrucciones y criterios de análisis; el usuario debe validar los resultados en su entorno.
