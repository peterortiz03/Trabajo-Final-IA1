# Comprobación del resultado de una muestra

Después de Reconocer se habilita «Mostrar referencia de la muestra». El panel compara la decisión del sistema con la identidad de origen guardada al generar automáticamente la captura. Puede ocultarse con el mismo botón.

Verde significa identificación correcta o rechazo correcto. Rojo significa falso rechazo, falsa aceptación o identidad incorrecta. Gris indica referencia desconocida. Una aceptación con identidad equivocada es un error aunque el acceso haya sido autorizado.

La referencia es un dato de la simulación. No se entrega al normalizador, al descriptor, a K-means ni a la decisión por umbral. No cambia el modelo ni la decisión. No representa una certificación independiente de identidad: permite evaluar una muestra sintética de origen conocido.

Al cambiar de captura o iniciar otro reconocimiento, la referencia vuelve a ocultarse. Durante una operación el botón queda deshabilitado. Un fallo de procesamiento no cuenta como rechazo y no habilita la comparación.

Para imágenes seleccionadas desde archivo y capturas preparadas manualmente, esta versión muestra «Referencia desconocida»: no deduce identidades de nombres, carpetas o predicciones. La referencia automática solo está disponible para las capturas generadas con el selector Aleatoria/Autorizada/Intrusa de esta sesión. Abrir después una captura guardada como imagen tampoco carga su receta automáticamente.

La comprobación se habilita al terminar Reconocer; muestra también la identidad predicha para compararla con la referencia. Es una ayuda para la demostración y no sustituye el comando Identificar del flujo normal. Si se desea probar sin conocer la respuesta, mantener el panel cerrado hasta terminar Identificar.

## Prueba manual

1. Generar una muestra Autorizada. Antes de reconocer, el botón está deshabilitado.
2. Ejecutar Reconocer y luego Identificar si la huella fue aceptada.
3. Mostrar referencia y comparar origen y predicción. Si el modelo falla, el panel debe informarlo sin corregir su decisión.
4. Ocultar y volver a mostrar la referencia.
5. Generar una Intrusa: la referencia anterior desaparece. Reconocer y mostrar la nueva comparación.
6. Seleccionar una imagen desde archivo, reconocerla y mostrar referencia: aparece desconocida.

## Validación

Pruebas automáticas de los cinco casos, referencia desconocida, conservación de la decisión y bloqueo del botón. Pruebas existentes de integración y generación. La prueba visual necesita ejecutarse en un equipo con escritorio.
