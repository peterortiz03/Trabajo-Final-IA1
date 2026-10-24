# Impresiones de Anguli: diagnóstico y preparación experimental

> **Cierre actualizado · 23/10/2026:** El diagnóstico está completado y fue reproducido por el autor en Windows. Después se ajustó el modelo combinado, se evaluó el control sin reajuste y se fijó la versión final de desarrollo para la muestra. La sección Cómo continuar describe el plan previo, ya realizado para la primera alternativa combinada. Véase [cierre de la etapa 08](cierre_etapa08.md).

Fecha: 23/10/2026. Esta ampliación conserva la aplicación y el modelo actuales. No implementa todavía un nuevo modelo de reconocimiento ni afirma soporte de impresiones de Anguli.

## Lote recibido y alcance

El autor generó 30 impresiones para cada una de A01, A02, A03, I01 e I02, con semillas 101, 202, 303, 404 y 505. Se verificaron las cinco bases contra las originales: son idénticas píxel por píxel. Las 150 impresiones son PNG gris L, 275 × 400; no hay duplicados exactos por píxeles. Las configuraciones conservan un hilo, distribución Natural, inicio 1, una identidad por corrida, 30 impresiones y ruido/rayaduras/rotación/traslación en cero. Las impresiones aun así no equivalen a las bases limpias. No se leyó ninguna imagen de los intrusos finales I03/I04.

Estos controles no identifican la versión exacta del ejecutable de Anguli ni garantizan independencia estadística: las impresiones comparten patrón base, configuración y corrida. Conservar el ejecutable y registrar su versión/procedencia si está disponible. Semilla conocida o nombre de carpeta son etiquetas del ensayo, nunca entradas del clasificador.

## Instalación y ejecución en Windows

Copiar los archivos de `ia1_diagnostico_anguli_incremental.zip` sobre el repositorio actual. Solo agrega un script y documentación; no reemplaza la ventana, modelos, dependencias o configuraciones.

Conservar el lote en:

`experimentos/anguli_impresiones_v1/originales/`

Dentro deben estar las cinco carpetas completas A01_autorizada_semilla101, A02_autorizada_semilla202, A03_autorizada_semilla303, I01_intrusa_desarrollo_semilla404 e I02_intrusa_desarrollo_semilla505. Cada una conserva Anguli.conf, Fingerprints, Impression_1 a Impression_30 y los metadatos existentes. No es necesario volver a generar ni mover archivos a datos/.

Desde la raíz, ejecutar en PowerShell:

```powershell
.\.venv\Scripts\python.exe src/diagnosticar_impresiones_anguli.py
```

No necesita micrófono, interfaz gráfica, notebooks ni entrenamiento. Si la carpeta está en otra ubicación:

```powershell
.\.venv\Scripts\python.exe src/diagnosticar_impresiones_anguli.py --originales "C:\ruta\a\originales"
```

La validación explica archivos ausentes, configuración incorrecta, base diferente o duplicados. Si faltan recursos del modelo, restaurarlos; no ejecutar calibración para resolverlo. Se exige el entorno científico registrado por la aplicación. El script carga una sola vez el modelo congelado y llama a los mismos módulos de normalización, extracción y decisión. Verifica hashes de los archivos del paquete de modelo antes/después. No usa el preparador ni aplica nuevas deformaciones a las impresiones.

## Salidas y separación

Cada ejecución crea una carpeta nueva `experimentos/anguli_impresiones_v1/diagnosticos/FECHAUTC/`. Nunca sobrescribe una corrida existente.

| Archivo | Contenido |
|---|---|
| manifiesto.csv | Las 150 rutas relativas, identidades de referencia, particiones y hashes |
| consultas_modelo_actual.csv | Las 125 decisiones de desarrollo; errores separados de rechazos |
| caracteristicas_desarrollo.npz | X de 125 × 144 sin escalar; nombres en orden e indices_manifiesto, base cero |
| resumen.json | Verificación de bases, resultados, entorno, hashes del modelo y del script |

Se guardan las 144 características para permitir un futuro ajuste experimental. En el diagnóstico actual se aplican únicamente las 72 seleccionadas y el escalado/centroides/umbral guardados. No se vuelve a ajustar nada. No se guardan imágenes normalizadas ni copias de originales. Un fallo de extracción deja su error en el CSV y omite ese vector; se debe revisar antes de entrenar.

| Partición | Autorizadas | Intrusas | Total |
|---|---:|---:|---:|
| ajuste_experimental | Impresiones 1–20: 60 | Ninguna | 60 |
| validacion_experimental | Impresiones 21–25: 15 | Impresiones 1–25: 50 | 65 |
| control_apartado | Impresiones 26–30: 15 | Impresiones 26–30: 10 | 25 |

Los intrusos no deben incorporarse como identidades a los tres centroides autorizados. La partición de desarrollo es exploratoria: el modelo actual se diagnosticó en sus 125 entradas. Las 25 de control solo se leen para integridad/formato y duplicados: no se normalizan, vectorizan ni clasifican. La separación se hace por manifiesto sin mover imágenes. No equivale a una prueba final con nuevas identidades. Duplicados aproximados y dependencia por base siguen siendo limitaciones.

## Resultado con el modelo actual

Modelo: 20261023T021746_872267Z. Umbral: 5.292172575840761. Se ejecutaron 125 consultas, sin errores ni avisos.

| Identidad | Consultas | Aceptadas | Distancia mínima | Distancia máxima |
|---|---:|---:|---:|---:|
| A01 | 25 | 0 | 10.928469 | 16.612923 |
| A02 | 25 | 0 | 8.957638 | 14.313403 |
| A03 | 25 | 0 | 10.187601 | 16.562476 |
| I01 | 25 | 0 | 20.625600 | 23.218235 |
| I02 | 25 | 0 | 10.467816 | 18.359254 |

Las 75 autorizadas fueron rechazadas y las 50 intrusas rechazadas correctamente. No se presenta un porcentaje global que oculte la incapacidad de aceptar autorizadas. Las distancias no son probabilidades. La diferencia de textura observada es compatible con una diferencia de distribución; no demuestra que una única deformación explique los rechazos. Subir el umbral no asegura una identidad correcta y puede aceptar intrusos.

## Verificado y pendiente

Se ejecutó el script completo en Linux/Python 3.12 con las dependencias científicas del proyecto. Se verificaron los 150 archivos, particiones 60/65/25, matriz (125,144) y exclusión del control de vectores/decisiones. En diez entradas se contrastó contra evaluar_huella de la interfaz con distancia idéntica a tolerancia 1e-12. Se introdujeron errores deliberados en copias temporales: duplicado desarrollo/control, semilla incorrecta y base distinta; los tres se bloquearon. Las entradas originales permanecieron intactas. Los registros están en [resultados del diagnóstico](resultados_anguli_impresiones_v1/verificacion.md).

Esta versión del script no se ejecutó en Windows aquí. El autor ya verificó la aplicación anterior y cinco consultas en Windows; eso no valida automáticamente este script nuevo.

## Cómo continuar después de reproducir

1. Revisar que Windows produzca 125 consultas sin errores, la matriz esperada y las mismas distancias. Compartir resumen.json y cualquier error; no reenviar las 150 imágenes.
2. Implementar un entrenamiento **experimental separado**, reutilizando funciones existentes. Comparar un modelo con capturas anteriores y nuevas impresiones; escalador y selección solo se ajustan con entrenamiento. Documentar las ponderaciones para que un procedimiento no domine por cantidad de muestras. Fijar criterios antes de comparar alternativas.
3. Revisar identificación por grupo y rechazo en validación; conservar casos fallidos. Las imágenes intrusas sirven para el rechazo, no para aprender centroides autorizados. No reajustar con las 25 de control.
4. Una vez fijada una alternativa, evaluar el control apartado y las entradas anteriores. Si no mejora o pierde seguridad, conservar el modelo actual. La prueba final original sigue reservada.
5. Integrar una nueva configuración únicamente si hay evidencia suficiente. El modelo de voz y la ventana no requieren rediseño.

No ejecutar ahora generar_conjunto.py, extraer_dataset_huellas.py, mejorar_clusterizacion_huellas.py ni calibrar_rechazo_huellas.py sobre las salidas anteriores. Este paquete no contiene entrenamiento automático.

## Registro en Git

Mantener `/experimentos/anguli_impresiones_v1/` en .gitignore. Los resultados locales y las imágenes no se agregan por defecto. Solo se propone versionar herramienta y evidencia seleccionada:

```powershell
git add src/diagnosticar_impresiones_anguli.py documentos/experimento_anguli_impresiones_v1.md documentos/resultados_anguli_impresiones_v1/
git diff --cached --stat
git commit -m "Diagnosticar impresiones de Anguli sin alterar el modelo de acceso"
```

Si aún falta la exclusión, agregar su línea a .gitignore y revisar ese cambio antes de incluirlo. No se publica ni se hace push automáticamente. La herramienta y esta documentación fueron preparadas con asistencia de IA; las imágenes provienen del lote generado por el autor en Anguli y la inferencia utiliza los módulos reales del proyecto.
