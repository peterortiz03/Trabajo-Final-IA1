# Verificación del cierre documental · 23/10/2026

Se actualizó documentación vigente y se agregó la bitácora 08, sin modificar código de aplicación, modelos, configuraciones, datasets o particiones. La versión principal para la muestra conserva el comando explícito con --config; el inicio predeterminado mantiene el respaldo anterior.

Se incorporaron los dos archivos originales del control ejecutado por el autor en Windows: 25 filas, sin errores, decisiones/identidades coincidentes y diferencias de distancia inferiores a 1e-12 respecto del mismo control Linux. No representan observaciones independientes adicionales. Se conserva el falso rechazo A03/Impression_26.

La bitácora contiene 17 celdas, ocho de código. Se ejecutaron secuencialmente con IPython en Linux/Python 3.12 y se guardaron salidas reales: modelos/configuraciones, particiones, selección CV, integridad NPZ/JSON, resultados y comparación Windows/Linux. El formato se validó con nbformat. No inicia entrenamientos, captura, generación, inferencia sobre prueba final o ventanas. No necesita datos del experimento ni modelo de voz local para consultarse.

El kernel externo de Jupyter no pudo iniciarse por restricciones de red del entorno. Se verificó el código con IPython en el mismo proceso; eso no equivale a una ejecución de VS Code/Windows. La comprobación de lectura y ejecución del notebook en ese entorno queda a cargo del autor. La evidencia gráfica incluida pertenece a la revisión Tk Linux previa, no a una nueva captura Windows.

Se revisaron enlaces locales de documentos modificados y de la nueva bitácora. No se reescribieron los logs históricos o los parámetros. Las pruebas de inferencia del paquete previo ya estaban aprobadas; no se repitió entrenamiento o control al cambiar únicamente documentación.
