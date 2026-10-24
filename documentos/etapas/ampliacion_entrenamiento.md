# Ampliación de entrenamiento: 30 originales, sin normalización

## Propósito

Añadir 10 impresiones por cada identidad autorizada, conservando las mismas bases Anguli.
No son identidades nuevas ni copias de imágenes de validación/prueba: se generan desde la
base con semillas individuales nuevas. A01/A02/A03 pasan de 20 a 30 muestras de entrenamiento.
El conjunto pasa de 160 a 190 muestras: 90 entrenamiento, 50 validación y 50 prueba.

Esta es una ampliación dirigida a condiciones de captura más variadas. No garantiza por sí
sola mejorar el reconocedor futuro. La validación/prueba existente no mide exhaustivamente
la robustez frente a las nuevas perturbaciones más amplias. No se cambian esas particiones
ni se seleccionan imágenes según el rendimiento de un modelo.

## Instalación y ejecución

Copiar el contenido del ZIP a la raíz del repositorio, combinando src/, config/ y documentos/.
No reemplaza archivos anteriores. Requiere los scripts generar_conjunto.py y
piloto_deformaciones.py, config/conjunto_v1.json, las siete bases y datos/metadatos.csv del
conjunto original ya generado. Usa las mismas dependencias instaladas.

Desde PowerShell en la raíz:

```powershell
.\.venv\Scripts\python.exe src/ampliar_entrenamiento.py
```

No volver a ejecutar generar_conjunto.py para esta ampliación. No hace falta volver a Anguli.
El programa comprueba la integridad de los originales previos y no los modifica.

Salida esperada:

```text
OK: 30 originales nuevos, 10 por autorizado. Sin normalización.
Total: 90 entrenamiento + 50 validación + 50 prueba = 190 muestras.
```

Rutas:

- datos/originales/ampliacion_train_v1/entrenamiento/A01/ (y A02, A03): M41 a M50.
- datos/metadatos_ampliacion_train_v1.csv: solamente las 30 nuevas filas.
- datos/metadatos_con_ampliacion_train_v1.csv: catálogo completo de 190 filas.
- resultados/ampliacion_train_v1/: comparación, entorno, fuentes, configuración e informe.

El CSV completo es una alternativa al CSV de 160 filas, no un archivo para concatenar con
él: hacerlo duplicaría las 160 muestras. Para el siguiente paso se usará el catálogo completo.
Los datos pueden estar en dos carpetas; el catálogo guarda la ruta de cada muestra.
No modificar manualmente los IDs: M41–M50 pertenecen a entrenamiento aunque M31–M40 fueran prueba;
la partición se lee de los metadatos, no del orden numérico del nombre.

Los destinos existentes provocan una detención antes de escribir. Para otra corrida de
verificación, usar --nombre ampliacion_train_verificacion. No sumar dos corridas de la misma
configuración como muestras independientes: sus IDs, semillas e imágenes se repiten.

## Variaciones (dos por tipo y por identidad)

| Tipo | Variación principal |
|---|---|
| Deformación mayor | Desplazamiento local máximo elegido entre 6 y 8 px, sujeto al control de gradiente |
| Posición más variable | Hasta ±7° de rotación y ±8 px de traslación |
| Contraste reducido | Intensidad de las crestas al 55–72% del contraste original |
| Captura menos nítida | Desenfoque sigma 0.55–0.8 px y ruido sigma 3–5 niveles de gris |
| Contacto parcial | Recorte lateral/superior/inferior y deformación local de 4–7 px |

El resto de las perturbaciones se mantiene moderado según config/ampliacion_train_v1.json.
Todos los casos incluyen deformación no lineal. No se aplican simultáneamente todos los máximos.
El contorno elíptico suave es una aproximación sintética, no un modelo físico de piel.

El desenfoque, ruido y contraste de esta etapa SIMULAN una captura imperfecta: no se utilizan
para corregirla ni uniformarla. No se llama a preprocesar(), no se reescala, no se centra,
no se normaliza contraste, no se binariza y no se esqueletiza la salida. El lienzo sigue siendo
275×400 porque es el tamaño nativo de las bases. Los umbrales internos usados para detectar
imágenes vacías o parecidas no alteran los PNG guardados.

## Reproducibilidad y verificación

Semillas nuevas desde 901000, 902000 y 903000, diez por identidad, sin solaparse con las usadas
antes. Se registran parámetros efectivos, entorno, hashes del código y del catálogo anterior.
Cada generación se repite internamente con su propia semilla. Hay control de duplicados exactos
contra las 160 anteriores y las otras nuevas, y cribado simple de casi duplicados de igual
identidad (ROI central, umbral 128, diferencia menor al 1.5%, sin alineación). Eso no es un
reconocedor ni garantiza ausencia de toda similitud. Las imágenes de prueba solo se leen para
integridad; no se visualizan ni se usan para elegir la intensidad de las perturbaciones.

El asistente ejecutó la ampliación en una copia de trabajo con Python 3.12.14 y las mismas
versiones fijadas en requirements.txt. Obtuvo 30 originales, sin duplicados exactos ni alertas
del cribado, repetición idéntica y aproximadamente 1.97 MiB adicionales. Revisó visualmente
una muestra de cada perfil e identidad. La ejecución local en Windows queda por verificar.
Las semillas no garantizan igualdad entre distintas versiones o entornos.

## Qué conservar y qué devolver

Conservar los originales y las versiones procesadas que ya existen. Las nuevas muestras
quedan con procesado y sha256_procesado vacíos: es deliberado. Las 160 versiones procesadas
anteriores son un resultado preliminar, NO la entrada común definitiva para un conjunto de
190 muestras. La próxima etapa definirá una normalización común desde los originales de TODAS
las muestras, con criterios elegidos usando entrenamiento/validación, sin ajustar con prueba.
Todavía no implementar esa etapa.

Abrir resultados/ampliacion_train_v1/comparacion_ampliacion.png. Muestra una de cada par,
seleccionada por número de antemano. Las otras 15 también están en las carpetas originales.
Comprimir resultados/ampliacion_train_v1 y enviarlo junto a la salida de la terminal.
No generar más ampliaciones hasta revisar si esta diversidad es suficiente para el trabajo.

Issue: `Ampliar entrenamiento con nuevas condiciones de captura`.
Cierre: 30 originales, total 190, integridad y repetición verificadas, revisión visual y
normalización no ejecutada. Commit de código: `feat: ampliar entrenamiento con capturas mas diversas`.
Commit de datos después de revisar: `data: agregar diez impresiones por identidad autorizada`.
Revisar git status y git diff; agregar rutas explícitas, sin push automático ni nuevos tags
antes de verificar el hito.

## Uso de IA

ChatGPT preparó el código y la documentación a pedido del usuario de agregar huellas de
entrenamiento más diversas sin pasar todavía a normalización. Se reutiliza la implementación
ya documentada del piloto/conjunto. La revisión de intensidad se basó en entrenamiento y no
se evaluó ningún modelo de reconocimiento. Los rangos son propuestas del proyecto, no límites
biométricos validados por bibliografía.
