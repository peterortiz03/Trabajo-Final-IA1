# Publicar el avance en el repositorio existente

Ejecutar por bloques en PowerShell desde VS Code. Esta guía no ejecuta comandos ni sube nada automáticamente. No hace falta clonar de nuevo ni ejecutar git init.

## 1. Incorporar la documentación

Copiar `notebooks/01_bitacora_dataset_normalizacion.ipynb` y los documentos de este paquete a sus carpetas homónimas en el repositorio.

Abrir el notebook y seleccionar el intérprete `.venv`. Si VS Code solicita ipykernel:

```powershell
.\.venv\Scripts\python.exe -m pip install ipykernel
```

Ejecutar las celdas, comprobar las salidas y guardar. El notebook no modifica el dataset. Si usaste un nombre de salida diferente, actualizar NOMBRE_SALIDA en la primera celda de código.

Integrar `documentos/README_avance_para_integrar.md` en README.md. Se proporciona por separado para no reemplazar un README que hayas ampliado. Si tu README sigue teniendo solo el título y la descripción inicial, podés reemplazar su contenido por este texto.

Agregar las líneas de `documentos/gitignore_agregar.txt` al .gitignore existente, sin borrar reglas propias. No ignorar globalmente datos/, *.png, *.csv o *.json: necesitamos las bases, capturas y metadatos. .gitignore no deja de rastrear archivos que ya fueron añadidos en un commit anterior.

Conservar requirements.txt con las dependencias ya utilizadas; en los paquetes entregados fueron NumPy 2.3.5, SciPy 1.17.0, Pillow 12.3.0 y Matplotlib 3.10.8. No hacer pip freeze sobre un entorno ajeno. Se puede documentar ipykernel por separado como dependencia de desarrollo.

## 2. Comprobar ubicación y remoto

```powershell
Get-Location
git rev-parse --show-toplevel
git status --short
git remote -v
git branch --show-current
```

Verificar que sea Trabajo-Final-IA1 y que origin corresponda a https://github.com/peterortiz03/Trabajo-Final-IA1 (también puede estar expresado mediante SSH). No cambiar el remoto si ya es correcto. Si no aparece origin, agregarlo solamente en ese caso:

```powershell
git remote add origin https://github.com/peterortiz03/Trabajo-Final-IA1.git
```

La rama debe tener nombre; si el comando no devuelve nada, detenerse y revisar el estado antes de publicar. No asumir que se llama main.

## 3. Qué subir

Subir código, configuraciones, requirements, documentación, bases pequeñas de Anguli con su procedencia, las tres carpetas definitivas de originales, los cinco CSV de generación y la carpeta de normalización final. Esta elección conserva una instantánea utilizable del dataset académico. En la copia comprobada, esos datos ocupan alrededor de 48 MiB en total; medir tu propia copia.

No incluir .venv, caches, ZIP duplicados ni el instalador/ejecutable de Anguli. Los resultados de pruebas intermedias y los procesados preliminares pueden permanecer locales; no se requieren para usar las salidas finales. No se borran.

## 4. Commit de código y configuración

Primero comprobar que no haya cambios previamente preparados que correspondan a otro trabajo:

```powershell
git diff --cached --name-only
```

Si hay archivos de otra tarea, resolver esa selección antes de seguir. Preparar:

```powershell
git add -- .gitignore requirements.txt src config
git diff --cached --stat
git diff --cached --name-only
git diff --cached --check
```

Revisar que la selección solo contenga lo esperado; después:

```powershell
git commit -m "feat: generar huellas reproducibles y unificar su preparacion geometrica"
```

Si Git indica que falta configurar nombre/correo, usar los datos propios con `git config user.name` y `git config user.email` para este repositorio y repetir el commit. Si indica que no hay cambios, puede que esa parte ya esté comprometida: comprobar `git log -3 --oneline` y continuar con los cambios pendientes.

## 5. Commit del dataset y sus resultados finales

Si tu salida tiene otro nombre, ajustar su ruta antes de ejecutar:

```powershell
git add -- datos/bases datos/originales/conjunto_v1 datos/originales/ampliacion_train_v1 datos/originales/rotaciones_train_v1
git add -- datos/metadatos.csv datos/metadatos_ampliacion_train_v1.csv datos/metadatos_con_ampliacion_train_v1.csv datos/metadatos_rotaciones_train_v1.csv datos/metadatos_con_rotaciones_train_v1.csv
git add -- datos/procesados/normalizacion_final_v1
git diff --cached --stat
git diff --cached --name-only
```

Son cinco CSV de generación enumerados aquí: uno inicial, dos de la primera ampliación y dos de las rotaciones. El sexto catálogo, el normalizado, queda incluido dentro de la carpeta final.

Revisar el tamaño de los archivos preparados (sin recorrer .venv):

```powershell
$archivosPreparados = @(git -c core.quotePath=false diff --cached --name-only --diff-filter=ACMR)
$infoPreparada = @($archivosPreparados | ForEach-Object { Get-Item -LiteralPath $_ })
$infoPreparada | Sort-Object Length -Descending | Select-Object -First 10 Name, Length
"Total preparado: {0:N2} MiB" -f (($infoPreparada | Measure-Object Length -Sum).Sum / 1MB)
$infoPreparada | Where-Object { $_.Length -gt 100MB } | Select-Object FullName, Length
```

La última consulta no debería devolver archivos. GitHub bloquea archivos de más de 100 MiB con Git normal; si aparece uno, revisar qué es antes de hacer commit. No se espera ese tamaño para los PNG de este conjunto.

```powershell
git commit -m "data: conservar 220 capturas y sus representaciones normalizadas"
```

Si git add informa que una ruta está ignorada, averiguar la regla con `git check-ignore -v RUTA` y corregirla si corresponde. No usar -f indiscriminadamente. Si informa que una ruta no existe, verificar el nombre real; no crear una carpeta vacía para ocultar el problema.

## 6. Commit de documentación

```powershell
git add -- README.md notebooks/01_bitacora_dataset_normalizacion.ipynb documentos
git diff --cached --stat
git diff --cached --name-only
git diff --cached --check
git commit -m "docs: explicar el dataset y los limites de la normalizacion"
```

Revisar especialmente que documentos/ no incluya el ZIP del material de la cátedra ni archivos ajenos al proyecto. La selección puede ajustarse por archivo antes de confirmar el commit. Para retirar un archivo del área preparada sin borrarlo: `git restore --staged -- RUTA`.

## 7. Publicar

```powershell
git log -3 --oneline
git status --short
git fetch origin
```

Si fetch termina correctamente:

```powershell
$ramaActual = git branch --show-current
if ([string]::IsNullOrWhiteSpace($ramaActual)) { throw "No hay una rama activa con nombre." }
git push -u origin $ramaActual
```

Completar la autenticación de GitHub si la solicita. Si push es rechazado porque existen commits remotos nuevos, no usar --force: revisar la divergencia antes de integrar cambios. La guía no asume que tu copia remota no haya cambiado.

Los commits quedan locales hasta que push finaliza correctamente. `git status --short` puede seguir mostrando resultados intermedios no incluidos deliberadamente; no hay que añadirlos solo para que quede vacío.

## 8. Hito opcional

Después del push correcto, marcar el cierre con una etiqueta si todavía no existe:

```powershell
git tag -l "v0.1-dataset-normalizado"
git tag -a v0.1-dataset-normalizado -m "Dataset sintetico y normalizacion geometrica v1"
git push origin v0.1-dataset-normalizado
```

Si la primera consulta devuelve esa etiqueta, no recrearla. Finalmente abrir GitHub y comprobar los tres commits, el notebook y el catálogo final. Esto cierra el avance; no implica que el reconocimiento esté terminado.

Referencias oficiales:
- https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github
- https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
