# Reorganización v1 · 24/10/2026

Aplicar sobre la versión del repositorio que incluye el cierre 08 y el modelo combinado, ya confirmada en Git. Esta entrega contiene una herramienta de migración; copiarla no mueve archivos. No incluye modelos, datasets ni paquetes nuevos. La herramienta usa solamente la biblioteca estándar de Python.

## Alcance

- Documentos agrupados en guias/, etapas/, evidencias/ e historico/; enlaces y referencias activas actualizados.
- Paquetes operativos en modelos/huellas/combinado_v1 y referencia_v1. Se copian parámetros sin alterarlos. Las instantáneas originales de evidencia se conservan para no falsear procedencia o romper hashes.
- config/aplicacion.json es el combinado principal; aplicacion_respaldo.json conserva el anterior. Ventana y servicios usan ahora aplicacion.json por defecto. Los dos nombres antiguos de configuración se conservan como compatibilidad; usar los nombres nuevos en adelante.
- iniciar.ps1 abre el combinado desde la raíz correcta.
- Se retiran LEEME_HITO1_HUELLAS.md y LEEME_HITO2_AUDIO.md; quedan recuperables en el respaldo externo y Git.
- Índice descriptivo de ejecuciones locales existentes en documentos/guias/indice_ejecuciones.csv. Las corridas con fechas no se renombran.
- Se conservan src/ y datos/ en sus lugares; no se renombran módulos científicos, no se modifica su contenido, no se entrena y no se consulta prueba final.
- Audio local no se mueve: conserva sus rutas y contratos. No se borran matrices, grabaciones, consultas, experimentos, entornos o archivos no versionados.
- Los duplicados de evidencia se conservan en esta fase: algunos son instantáneas de procedencia o forman parte de manifiestos de integridad. No se eliminan por semejanza de nombre.

## Comandos PowerShell

Cerrar aplicación, terminales de ejecución y notebooks en ejecución. Desde la raíz del repositorio:

```powershell
git status --short
```

Antes de seguir, confirmar en Git los cambios pendientes que se deseen conservar. La migración exige que no haya cambios versionados sin registrar. No usar git reset --hard ni git clean. Los datos locales ignorados se conservan.

Crear una rama:

```powershell
git switch -c mantenimiento/ordenar-proyecto-v1
```

Extraer el ZIP de esta entrega en la raíz. Deben aparecer herramientas/reorganizar_proyecto.py y esta guía. Revisar el plan (no modifica nada):

```powershell
.\.venv\Scripts\python.exe herramientas/reorganizar_proyecto.py
```

Aplicar:

```powershell
.\.venv\Scripts\python.exe herramientas/reorganizar_proyecto.py --aplicar
```

Se crea un ZIP de respaldo de TODOS los archivos versionados afectados, fuera del repositorio, en su carpeta padre. También guarda la lista y hashes de cambios para restaurar. No es una copia completa de .venv o datos ignorados, que no se modifican. Se imprime su ruta y queda registrada en documentos/guias/migracion_organizacion_v1.json. No repetir --aplicar: el marcador impide aplicar dos veces.

Si falla antes de aplicar, leer el mensaje y resolver la causa; no borrar destinos a ciegas. Si un destino ya existe como archivo local no versionado, la herramienta se detiene para evitar sobrescribirlo.

## Verificar antes de confirmar

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_modelo_anguli.py" -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_interfaz_integracion.py" -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_preparar_captura.py" -v
.\.venv\Scripts\python.exe src/interfaz_servicios.py
.\.venv\Scripts\python.exe src/interfaz.py
```

Se esperan 4 + 10 + 6 pruebas aprobadas. Servicios debe cargar huellas 20261023T222326_850333Z y el modelo local de voz anterior. La ventana sin --config debe mostrar 36/144 columnas en Detalles técnicos.

Alternativamente:

```powershell
.\iniciar.ps1
```

Si PowerShell impide ejecutar el lanzador, el comando Python anterior cumple la misma función; no es necesario cambiar políticas para completar la comprobación.

Verificación manual breve: impresión Anguli A01 autorizada e identificada; intrusa rechazada; Preparar captura y Usar funcionan; micrófono conserva su dispositivo y reconoce comandos; Salir permite Cancelar/Cerrar. Abrir el notebook 08 y comprobar lectura de tablas/imágenes; para otras bitácoras, verificar lectura sin volver a entrenar.

Respaldo anterior:

```powershell
.\.venv\Scripts\python.exe src/interfaz.py --config config/aplicacion_respaldo.json
```

No repetir control o entrenamiento solo para comprobar nombres de carpetas. Los valores aprendidos y el fallo conocido A03/Impression_26 permanecen intactos.

## Confirmar y subir

Solo después de las comprobaciones:

```powershell
git status --short
git diff --check
git add -A -- README.md LEEME_HITO1_HUELLAS.md LEEME_HITO2_AUDIO.md config src tests documentos notebooks modelos iniciar.ps1 herramientas/reorganizar_proyecto.py herramientas/GUIA_REORGANIZACION.md
git diff --cached --stat
git diff --cached --name-status
git commit -m "Ordenar documentacion y modelos, y usar el combinado por defecto"
git push -u origin mantenimiento/ordenar-proyecto-v1
```

Git detectará muchos renombrados como R; otros aparecerán como borrado/alta por cambio de contenido. No se añaden datos/, experimentos/, resultados/, consultas/ o .venv. Revisar que tampoco se hayan añadido otros archivos personales en los directorios seleccionados. Esta migración produce un cambio coordinado de rutas: se confirma en un único commit para no dejar estados intermedios incompatibles. La rama principal permanece como estaba hasta integrar el cambio.

## Restaurar antes de confirmar si algo no funciona

Cerrar la aplicación. Sustituir la ruta de ejemplo por la del respaldo impreso:

```powershell
.\.venv\Scripts\python.exe herramientas/reorganizar_proyecto.py --restaurar "C:\ruta\Trabajo-Final-IA1_respaldo_organizacion_FECHA.zip"
```

Restaura las rutas/contenidos anteriores y elimina solo archivos nuevos registrados por la migración. Comprueba sus hashes antes de actuar; si se editaron después, se detiene para no perder esas ediciones. Las carpetas vacías pueden permanecer. No cambia índice, ramas, commits o datos ignorados de Git. No se requiere force push.

## Qué se verificó aquí

Se ejecutaron revisión, aplicación, restauración y reaplicación en una copia Linux del commit 3609d13. La restauración devolvió todos los archivos versionados a HEAD sin diferencias. Después de la migración definitiva aprobaron 20 pruebas (4 del combinado, 10 de integración, 6 de preparador). Se comprobó que los módulos de extracción/normalización conservan sus bytes; se revisaron enlaces locales y sintaxis/formato de las ocho bitácoras. No se ejecutaron de nuevo todas las celdas de los notebooks ni se entrenaron modelos. No se dispuso del audio local ni se ejecutó Windows/PowerShell en este entorno; las comprobaciones anteriores completan ese alcance.
