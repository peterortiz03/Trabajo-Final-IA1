# Normalización geométrica v1 — IA I

## Alcance

Este paquete procesa los 220 originales del catálogo
`datos/metadatos_con_rotaciones_train_v1.csv`: 120 de entrenamiento, 50 de
validación y 50 de prueba. Incluye las ampliaciones y rotaciones.
Requiere el entorno que ya utilizaste: NumPy, SciPy y Pillow.
No utiliza los PNG procesados preliminares.

La función realiza conversión a gris, detección de la región de huella,
eliminación de fondo fuera de la máscara, centrado, estimación del eje mayor
del contorno, giro para colocarlo vertical y centrado final en 512 × 512.
Conserva la escala en píxeles; no estira la huella. La rotación usa interpolación
lineal, por lo que puede suavizar ligeramente las crestas. No añade filtros,
binarización, ecualización, esqueletización ni extracción de características.
Los valores son uint8, negro 0 y blanco 255; no se iguala el contraste entre
capturas. Esto es una normalización GEOMÉTRICA, no fotométrica ni de resolución
física. Nuestros originales proceden de la misma escala de generación.

## Orientación y limitaciones

La orientación se calcula únicamente a partir de los píxeles de la máscara.
No se consulta la identidad, semilla, base limpia ni el ángulo de generación.
Se calcula la matriz de covarianza de las coordenadas del contorno relleno
y su eje principal. Este cálculo geométrico no entrena un modelo de reconocimiento.
La relación entre autovalores debe ser al menos 1.2; un contorno casi circular
queda marcado para revisión y no se gira automáticamente.

El eje tiene ambigüedad de 180 grados: vertical no significa siempre con la
punta hacia arriba. Se entrega una imagen principal y una alternativa girada
180 grados. Son DOS REPRESENTACIONES DE UNA SOLA MUESTRA, no dos observaciones
independientes ni nuevas identidades. La etapa de comparación posterior debe
considerar ambas orientaciones o usar características invariantes a ese giro.
No entrenar/evaluar suponiendo que la imagen principal ya tiene dirección única.

El contorno también cambia con el contacto parcial y las deformaciones: su eje
es una aproximación a la pose, no una alineación exacta de las crestas. Enderezar
el contorno no elimina deformaciones locales ni reconstruye partes recortadas.
No generalizar esta validación a otros sensores ni a huellas reales.

## Instalación

Extraer el ZIP y copiar su contenido en la raíz del repositorio. Se agregan
archivos con nombres nuevos en src, config y documentos; no se requiere
reemplazar los scripts anteriores. No copiar la carpeta contenedora entera
dentro de src. El archivo debe quedar como src/normalizar_todas.py.

Desde PowerShell, en la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe src/normalizar_todas.py
```

La ejecución verifica hashes de los originales, procesa cada muestra con la
misma configuración fija y conserva las particiones. No modifica originales
ni catálogos anteriores. Si la carpeta de salida existe, se detiene.
Para repetir sin borrar resultados:

```powershell
.\.venv\Scripts\python.exe src/normalizar_todas.py --salida normalizacion_final_v2
```

Para procesar solo desarrollo si necesitás investigar un problema:

```powershell
.\.venv\Scripts\python.exe src/normalizar_todas.py --solo-desarrollo --salida normalizacion_final_desarrollo
```

No ajustar parámetros con prueba. Si cambiás el método, validalo en desarrollo
y congelá la configuración antes de reaplicarlo al conjunto completo.

## Resultados

Todo se guarda en `datos/procesados/normalizacion_final_v1/`:

- entrenamiento, validacion, prueba: subcarpetas por identidad. Para cada
  muestra se guardan `A01_M01.png`, `A01_M01_180.png` y `A01_M01_mascara.png`.
- `catalogo_normalizado.csv`: 220 filas; columnas nuevas normalizada,
  alternativa_180, sha256_normalizada, sha256_alternativa_180 y estado_normalizacion.
  Las columnas anteriores se preservan por trazabilidad. Para las próximas
  etapas leer **normalizada** y **alternativa_180**, NO la columna procesado
  heredada del catálogo antiguo. No cargar todos los PNG indiscriminadamente:
  las máscaras no son huellas de entrenamiento.
- `resumen.json`: conteos por estado y partición.
- `detalle.json`: ángulo aplicado, eje residual, confianza geométrica,
  advertencias y datos de segmentación por muestra. bbox_mascara_xyxy y
  traslacion_x_y describen la etapa inicial de ROI; centro_bbox_salida_x_y
  corresponde al centrado final.
- `config_efectiva.json` y `entorno.json`: configuración, versiones y hashes.
- `comparaciones_desarrollo`: original, normalizada y alternativa 180 de
  ejemplos preseleccionados de entrenamiento/validación. No hay paneles de prueba.

## Qué revisar

1. Resumen: solicitadas 220; entrenamiento 120, validacion 50, prueba 50;
   errores 0. Correctas + revisar debe ser 220.
2. Comparaciones: huella vertical y centrada, sin estiramiento ni recortes
   introducidos por el giro. Revisar las crestas ampliando las imágenes.
3. Comparar especialmente A01_M51 a A01_M60 para los giros grandes.
4. Avisos: examinar los casos de desarrollo señalados. Alcanzar un borde de
   entrada es un aviso de posible recorte previo, no una orden de descartar.
5. Los avisos de prueba se conservan para auditoría; no usarlos para elegir
   parámetros, descartar selectivamente casos o mejorar resultados reportados.

La normalización geométrica de esta versión se puede dar por implementada
cuando la ejecución y revisión pasan. La ambigüedad 180 queda explícita en
el contrato con la siguiente etapa. No demuestra aún que el reconocimiento
funcione ni que dos capturas del mismo dedo deban resultar píxel a píxel iguales.

## Uso desde otro programa

Desde un script ubicado dentro de src:

```python
from PIL import Image
from normalizacion_final import normalizar_huella

with Image.open('datos/originales/mi_huella.png') as imagen:
    normalizada, info = normalizar_huella(imagen)

Image.fromarray(normalizada).save('huella_normalizada.png')
Image.fromarray(info['alternativa_180']).save('huella_normalizada_180.png')
print(info['angulo_aplicado_grados'], info['avisos'])
```

Los valores por defecto coinciden con el JSON incluido. Si se modifica el JSON,
cargarlo y pasarlo como segundo argumento también para las futuras capturas.
Manejar ValueError para imágenes vacías, ROI insuficiente o demasiado grande.
Revisar info['avisos'] y info['orientacion_estimable']; no continuar a ciegas
con una imagen no apta. La función no hace lecturas/escrituras ni necesita CSV.

## Referencia técnica

Rotación e interpolación: documentación oficial de scipy.ndimage.rotate:
https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.rotate.html
