# Última ampliación: rotaciones de entrenamiento

Agregar 10 originales por autorizado (30 en total), sin modificar entrenamiento previo,
validación, prueba ni reservas de demostración. Cada muestra se genera desde su base con una
semilla nueva; no se rotan imágenes de prueba. Se conserva deformación local suave de 2–4 px,
contraste y calidad moderados. La variación principal es el ángulo final.

Ángulos por identidad: −90°, −60°, −45°, −30°, −15°, +15°, +30°, +45°, +60°, +90°.
Positivo significa antihorario. ±90° son extremos de esta simulación elegidos por el proyecto,
no un límite universal comprobado para sensores. No hay reflejos ni cambios de identidad.
Una rotación sola es una transformación geométrica lineal; la deformación local previa sigue
aportando la transformación no lineal requerida.

## Ejecutar

Copiar src/ y documentos/ a la raíz del repositorio existente. Conservar los tres scripts
anteriores. Se requiere haber generado la ampliación anterior y su catálogo de 190 filas:
datos/metadatos_con_ampliacion_train_v1.csv. No se instalan dependencias nuevas.

```powershell
.\.venv\Scripts\python.exe src/ampliar_rotaciones.py
```

Salida esperada: 30 originales nuevos. Total 220 muestras: 120 entrenamiento, 50 validación,
50 prueba. Cada autorizado tiene 40 de entrenamiento, 10 de validación y 10 de prueba.
Los intrusos siguen sumando 40 muestras. No volver a ejecutar los generadores anteriores.

Destinos:

- datos/originales/rotaciones_train_v1/entrenamiento/A01/ (y A02, A03): M51–M60.
- datos/metadatos_rotaciones_train_v1.csv: solamente 30 filas nuevas.
- datos/metadatos_con_rotaciones_train_v1.csv: catálogo completo de 220 filas.
- resultados/rotaciones_train_v1/: tres comparaciones por identidad, entorno, configuración,
  fuentes y verificacion.json.

El catálogo de 220 filas REEMPLAZA como referencia al de 190: no concatenarlos entre sí.
Los archivos anteriores se conservan intactos. Los destinos existentes provocan una detención;
para una corrida de comprobación usar --nombre rotaciones_repeticion. No contar esa repetición
como datos adicionales: reproduce IDs, semillas e imágenes.

## Dimensiones y escala

Los originales anteriores miden 275×400. Rotar 90° dentro de ese mismo marco recortaría la
huella. Las nuevas capturas se colocan sobre un fondo blanco de 512×512 y se rotan allí.
La diagonal de 275×400 es aproximadamente 485.4 píxeles: el nuevo lienzo permite las rotaciones
sin cortar el rectángulo original. NO se amplía ni comprime la huella: la escala de las crestas
se conserva. Para ±90° se usa np.rot90, sin interpolación; para el resto se utiliza interpolación
lineal. La colocación en el lienzo es parte de la simulación de captura, no una normalización
orientada a eliminar el ángulo ni a preparar características.

Todas las nuevas imágenes conservan sus ángulos. No se normaliza, binariza, esqueletiza ni
reescalan los archivos. El tamaño distinto es deliberado y queda documentado. En la siguiente
etapa se deberá definir una representación común para TODOS los originales sin convertir
cada tamaño de lienzo en una escala diferente de huella. No mezclar ahora matrices crudas de
275×400 y 512×512 como si ya fueran características de igual dimensión.

## Controles y límites

Semillas nuevas desde 1901000, 1902000 y 1903000; parámetros y hash de cada original registrados.
Se comprueba integridad de las 190 imágenes previas, repetición por muestra, contenido no vacío,
marco sin crestas cortadas y ausencia de duplicados exactos entre las nuevas. Las imágenes
previas son de otro tamaño y no pueden ser duplicados exactos de las nuevas; no se hace un
chequeo de casi duplicados con alineación geométrica. La revisión visual sigue siendo necesaria.
Los ángulos y semillas se fijan de antemano y no se seleccionan según un reconocedor.

El asistente lo probó con las bases entregadas en Linux/Python 3.12.14 y las mismas dependencias
del proyecto. La ejecución local de este nuevo script en Windows queda por verificar.
No se garantiza igualdad de resultados entre versiones o entornos distintos.

Ampliar entrenamiento hasta ±90° no demuestra por sí solo robustez a esos ángulos. La prueba
final existente conserva su distribución anterior, principalmente de ángulos pequeños. Más
adelante se podrá diseñar un ensayo de robustez separado, fijado antes de evaluar, sin reemplazar
ni ajustar la prueba final para obtener resultados favorables.

## Revisión y seguimiento

Abrir rotaciones_A01.png, rotaciones_A02.png y rotaciones_A03.png en resultados/rotaciones_train_v1.
Enviar esa carpeta comprimida y el resultado de la terminal. Esta será la última ampliación
antes de estudiar normalización; conservar originales y los resultados procesados previos.
Los nuevos campos procesado/sha256_procesado quedan vacíos a propósito.

Issue sugerida: `Ampliar entrenamiento con orientaciones de hasta 90 grados`.
Cierre: 30 originales, 220 IDs únicos en el catálogo, rotaciones sin recorte de crestas,
repetición verificada y revisión visual. Commit sugerido:
`feat: agregar orientaciones de entrenamiento sin recortar las huellas`.
No se hace push ni se modifica el repositorio remoto desde el asistente.

Uso de IA: ChatGPT preparó código, documentación y pruebas a pedido de incorporar diez nuevas
impresiones por identidad con rotaciones de hasta 90°, manteniendo pendiente la normalización.
Los rangos de ángulo son decisiones de esta simulación, no especificaciones de un sensor real.
