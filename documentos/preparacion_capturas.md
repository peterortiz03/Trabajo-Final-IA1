# Preparación de capturas sintéticas · ampliación de la etapa 08

> **Cierre actualizado · 23/10/2026:** El autor informó funcionamiento de la generación automática y las opciones avanzadas en Windows. El preparador se conserva en la muestra con el modelo combinado de 36 columnas. El diagnóstico de 170 consultas y la distancia A01 3.284720 de esta guía corresponden al modelo anterior de 72 columnas, no al combinado. Véase [cierre de la etapa 08](cierre_etapa08.md).

**Fecha:** 23/10/2026. **Base de instalación actual:** interfaz inicial y `ia1_preparar_captura_incremental.zip` ya instalados por el autor. La actualización automática se entrega en `ia1_preparacion_automatica_incremental.zip`. Esta entrega es incremental: contiene archivos completos nuevos/modificados para copiar sobre esa versión, sin sustituir modelos ni datasets.

## Objetivo y alcance

Se incorpora el desplegable **Preparar captura sintética desde una base de Anguli** en la misma ventana. Genera una consulta mediante el procedimiento existente del dataset y permite usarla en el reconocimiento sin escribir archivos. No interpreta etiquetas, semillas de identidad ni nombres de carpeta como evidencia de autorización.

La ventana anterior ya normalizaba entradas y comparaba sus características con centroides congelados. Las bases limpias se rechazaban aunque fueran el origen de una identidad autorizada. Este preparador permite recorrer **base → captura sintética → normalización e inferencia**. No resuelve ni afirma reconocimiento directo de bases limpias.

El autor compartió capturas de la versión anterior ejecutada en Windows/Python 3.14.0, con modelos disponibles y micrófono Realtek mediante MME: Reconocer autorizó A01, Identificar reveló A01, I02_M10 fue rechazado, el silencio produjo «sin comando» y Salir mostró la confirmación. El autor informó funcionamiento correcto. Son evidencias de una demostración de desarrollo, sin conteo de todos los intentos ni evaluación con personas nuevas. La ampliación del preparador se verificó en Linux; posteriormente el autor informó funcionamiento en Windows, sin registro individual de todos sus intentos.

## Funcionamiento

1. Abrir el desplegable y seleccionar una **base de Anguli en gris L8 de 275 × 400 píxeles**. No se reescala automáticamente ni se consulta su supuesta identidad. Se admite desde cualquier carpeta; la cancelación conserva el estado previo.
2. Al terminar de leer la base, se genera **automáticamente una captura**. Se sortea uniformemente uno de los cinco perfiles existentes y una semilla de captura de 32 bits, antes de generar y sin consultar el reconocedor. No es la semilla con la que Anguli generó la identidad.
3. **Generar nueva captura** vuelve a sortear perfil y semilla (distinta de la anterior). Se reutiliza `generar_conjunto.producir`, con sus deformaciones locales y simulación de contacto, calidad y ruido; no se inventa una combinación nueva de perfiles. No se clasifica durante la generación ni se eligen capturas según su autorización. **Opciones avanzadas**, cerrado inicialmente, muestra los valores utilizados. Activar **Elegir perfil y semilla manualmente** permite fijarlos para reproducir un intento; abrir el desplegable o cambiar de modo no regenera la imagen.
4. Revisar las vistas proporcionales de base y captura. La captura obtenida todavía **no está normalizada** y no tiene autorización.
5. Pulsar **Usar esta captura**. Se copia en memoria al panel de acceso, se borra cualquier autorización/identidad anterior y se cierra el desplegable para volver al recorrido principal. Se usa un identificador virtual de consulta; no se crea un PNG por esta acción.
6. Decir **Reconocer** o usar el botón manual. Se normaliza una vez, extrae GLCM, selecciona/estandariza con parámetros guardados y compara distancias con el umbral congelado. Identificar conserva su precondición habitual.

Preparar otra base o cambiar parámetros no modifica la consulta de acceso que ya estaba seleccionada: eso ocurre únicamente al pulsar Usar esta captura. En modo manual, cambiar perfil o semilla invalida el borrador del preparador y deshabilita Usar/Guardar hasta generar otra captura. Durante lectura, generación o guardado se bloquean acciones incompatibles; Salir conserva confirmación y cancelación. Los resultados tardíos utilizan los tokens de operación existentes.

`producir` también calcula una representación preliminar heredada del generador; se descarta. Se utiliza exclusivamente su salida **original**, para evitar aplicar a la consulta un procesamiento adicional diferente al del reconocimiento actual.

## Guardado opcional y reproducción

**Guardar consulta…** pide una carpeta padre y crea una subcarpeta nueva `consulta_FECHAUTC`. Si se elige la raíz del repositorio, se coloca bajo `consultas/`. Cada consulta contiene:

| Archivo | Contenido |
|---|---|
| `base.png` | Instantánea de la base utilizada, sin modificación |
| `captura.png` | Entrada sin normalizar que puede abrirse con Seleccionar huella |
| `receta.json` | Perfil, semilla de captura, parámetros efectivos, configuración, versiones y hashes |

No se guarda resultado, identidad verdadera ni decisión de acceso en la receta. Se conserva la base para reproducir sin depender de una ruta de otra computadora. Los hashes de píxeles permiten comprobar la imagen en memoria y los hashes de archivos verifican los PNG guardados. La receta incluye hashes del código, normalizados a LF para Windows/Linux. La reproducción exacta se comprobó en el entorno de verificación; otras versiones deben revisarse antes de afirmar igualdad.

El guardado usa una carpeta temporal hermana y la renombra al completarse. No sobrescribe consultas ni permite destinos dentro de datos/config/src/tests/notebooks/documentos del proyecto. No se escribe nada al iniciar, generar, usar o cancelar un diálogo. `consultas/` y `resultados/diagnostico_preparacion/` están excluidos de Git.

Para reconocer una consulta guardada, seleccionar **captura.png**, no base.png. Se volverá a normalizar desde la captura original, reproduciendo el recorrido en memoria. La lectura del PNG no carga automáticamente etiquetas o resultados desde la receta.

## Diagnóstico previo con modelo congelado

Se fijaron tres semillas de captura —2026102301, 2026102302 y 2026102303— y los cinco perfiles existentes **antes de consultar resultados**. Se utilizaron A01–A03 e I01–I02, sin leer imágenes de I03/I04 ni de prueba final. No se eligieron semillas o perfiles según el resultado.

Se realizaron 170 consultas de diagnóstico, sin reajustar escalado, selección, centroides o umbral. Los archivos del modelo conservaron sus hashes.

| Condición | Autorizadas aceptadas e identificadas correctamente | Intrusos rechazados |
|---|---:|---:|
| Base limpia | 0/3 | 2/2 |
| Solo contorno de contacto | 0/9 | 6/6 |
| Contacto y calidad, sin deformación geométrica previa | 3/45 | 30/30 |
| Procedimiento completo existente | 45/45 | 30/30 |

No hubo errores de procesamiento en estas consultas. La cadena completa resultó adecuada para esta demostración. El ensayo no aísla la deformación no lineal de su interpolación y de sus interacciones con contacto/calidad; no se atribuye toda la diferencia a una única causa. Las muestras provienen de cinco bases ya usadas en desarrollo y están correlacionadas. Estos resultados no son evaluación final ni garantía para todas las semillas, perfiles o identidades nuevas.

Los CSV, resumen, hashes y registros de pruebas se publican en [resultados de preparación](resultados_preparacion_capturas/verificacion.md). El umbral sigue siendo 5.292172575840761. Para la base A01, perfil leve y semilla 2026102301, se obtuvo distancia **3.284719866642**, autorización e identidad A01 al solicitarla.

## Código y dependencias

| Archivo | Cambio |
|---|---|
| `src/preparar_captura.py` | Preparación en memoria, validación de base/semilla, receta y guardado explícito |
| `src/verificar_preparacion_capturas.py` | Diagnóstico con plan fijo, únicamente desarrollo y modelo congelado |
| `config/preparar_captura_v1.json` | Configuración del generador, perfil/semilla iniciales y plan de diagnóstico |
| `src/interfaz.py` | Desplegable, vistas comparadas, transferencia de consulta y mensajes |
| `src/interfaz_servicios.py` | Carga independiente del preparador, sin condicionar huellas/voz a su disponibilidad |
| `tests/test_preparar_captura*.py` | Contratos, concordancia real, guardado y recorrido gráfico |
| `.gitignore` | Exclusión de consultas y diagnósticos locales |

No se agregan dependencias. Se conservan los archivos científicos y de modelos ya instalados. El preparador solo toma perfiles y configuración del generador; no recibe las identidades de `conjunto_v1.json`. El diagnóstico sí utiliza etiquetas de desarrollo para comparar resultados, separadamente de la generación y la inferencia.

## Instalación y verificaciones en PowerShell

Cerrar la aplicación. Desde la raíz del repositorio, revisar `git status --short` y extraer el ZIP incremental sobre la instalación anterior conservando sus modelos locales. Si no se modificaron dependencias desde la primera entrega, no hace falta volver a instalarlas.

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_preparar_captura*.py" -v
.\.venv\Scripts\python.exe src/interfaz.py
```

Se esperan **ocho pruebas aprobadas** (seis del preparador y dos gráficas). La prueba gráfica abre ventanas temporales, usa el generador y modelo de huellas reales y controla los diálogos por código; no graba por micrófono.

Prueba guiada:

1. Abrir Preparar captura y elegir `datos/bases/piloto_01/Fingerprints/fp_1/1.png` —o la base idéntica de semilla Anguli 101 regenerada por el autor—.
2. Sin pulsar Generar, deben aparecer base y captura. El panel avanzado comienza cerrado. Generar nueva captura debe producir otra semilla, sin autorizar ni cambiar la consulta activa. No hay una distancia esperada para parámetros aleatorios; conservar también los intentos rechazados.
3. Abrir Opciones avanzadas: muestra los últimos parámetros, sin cambiar la captura. Activar la elección manual, elegir **Deformación leve** y **2026102301**, y pulsar Generar nueva captura. Pulsar Usar esta captura: el panel se cierra y el resultado queda pendiente. Reconocer y luego Identificar: para la base A01 del diagnóstico se espera A01 y distancia cercana a 3.284720. Esta reproducción usa parámetros fijados previamente, no una búsqueda para conseguir acceso.
4. Repetir con `datos/bases/intruso_val_01/Fingerprints/fp_1/1.png`, el mismo perfil y semilla manual: se espera NO AUTORIZADO e identidad no visible. No utilizar los intrusos reservados de prueba. Las bases admitidas son las imágenes maestras de Fingerprints; las impresiones de Impression_1 siguen fuera del alcance verificado. No deben considerarse inválidas únicamente por su carpeta.
5. Cambiar la semilla manual debe deshabilitar Usar/Guardar hasta generar nuevamente. Cancelar la selección de base conserva el borrador. Desactivar elección manual y generar nuevamente vuelve al sorteo; el modo manual sigue activo hasta desmarcarlo o cerrar la aplicación.
6. Generar una captura y elegir Guardar consulta. Seleccionar la raíz del repositorio y comprobar `consultas/consulta_FECHAUTC/`. Abrir después su captura.png con Seleccionar huella: debe dar la misma decisión y distancia que la consulta en memoria. Cancelar el diálogo de guardado no debe crear carpetas.
7. Comprobar que durante generación no se pueden iniciar voz, otra generación o cambiar entradas. Salir/Cancelar conserva la sesión. La voz y los controles manuales anteriores deben seguir funcionando.

Compartir la salida de las ocho pruebas, una captura del preparador con ambas imágenes, la consulta preparada autorizada/identificada, el intruso rechazado y cualquier error. Abrir Detalles técnicos para ver perfil, semilla y procedencia de la consulta activa. La ampliación no necesita que se suba otra vez el paquete de audio.

El diagnóstico completo es opcional y escribe una carpeta nueva de resultados:

```powershell
.\.venv\Scripts\python.exe src/verificar_preparacion_capturas.py
```

Debe informar 170 consultas y el resumen de las cuatro condiciones. No se debe interpretar como prueba independiente ni utilizar una eventual diferencia para ajustar automáticamente el modelo.

## Commits pequeños propuestos

```powershell
git add src/preparar_captura.py src/verificar_preparacion_capturas.py config/preparar_captura_v1.json .gitignore
git commit -m "Reutilizar el generador para preparar consultas sinteticas reproducibles"

git add src/interfaz.py src/interfaz_servicios.py tests/test_preparar_captura.py tests/test_preparar_captura_ventana.py
git commit -m "Integrar preparacion, uso y guardado opcional de capturas en la ventana"

git add README.md documentos/README.md documentos/interfaz_integracion.md documentos/preparacion_capturas.md documentos/resultados_preparacion_capturas documentos/uso_ia_generativa.md
git commit -m "Registrar diagnostico congelado y verificaciones del preparador"
```

Si la primera entrega aún no está en commits, registrar primero sus cambios siguiendo su guía; estos comandos pueden incluir el contenido completo de archivos modificados de aquella versión. Revisar `git diff --cached --stat` antes de confirmar. No se hace push automático.

## Actualización: generación automática y opciones avanzadas

La configuración y los cinco perfiles existentes no cambian. El perfil/semilla iniciales del JSON siguen siendo valores de arranque para los controles; el modo automático los sustituye por el sorteo al generar. La receta agrega `eleccion_parametros` (`automatica` o `manual`) y conserva los valores efectivos para repetir el intento. No se añade una dependencia ni se modifica la inferencia.

Se ejecutaron **20 pruebas de software en Linux**, incluidas generación real, reproducción, concordancia de huellas, controles y recorridos gráficos. El sorteo se controló explícitamente en una prueba gráfica para comprobar la coordinación; no reemplazó al generador ni al reconocedor. Además se inspeccionó visualmente una generación con sorteo real. Véase [evidencia de la actualización](resultados_preparacion_automatica/verificacion.md). No se repitió el diagnóstico estadístico ni se atribuye una nueva precisión al modo aleatorio. El autor posteriormente informó funcionamiento Windows; no se cuenta con una evaluación controlada de todos los factores de escalado y audio de esa actualización.

Commits propuestos para esta actualización (si las entregas anteriores ya están registradas):

```powershell
git add src/preparar_captura.py src/interfaz.py tests/test_preparar_captura.py tests/test_preparar_captura_ventana.py
git commit -m "Generar capturas al seleccionar base y reservar parametros para opciones avanzadas"
git add README.md documentos/README.md documentos/preparacion_capturas.md documentos/uso_ia_generativa.md documentos/resultados_preparacion_automatica
git commit -m "Documentar flujo automatico y registrar verificaciones de integracion"
```
