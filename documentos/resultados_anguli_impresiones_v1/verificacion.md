# Evidencia: impresiones de Anguli v1

Ejecución real en Linux, 23/10/2026, sin reentrenamiento. Lote aportado por el autor: anguli_impresiones_v1_originales.zip, SHA256 `6b45ec85ad3887b7e83a105ba3394d0062e333b875202241ce2f036af793b165`.

- [Resumen completo](resumen.json): cinco bases coincidentes, 150 imágenes sin duplicados exactos, hashes y resultados por identidad.
- [Consultas de desarrollo](consultas_modelo_actual.csv): las 125 consultas individuales, sin errores ni avisos. No contiene decisiones de las 25 imágenes de control.
- [Salida del programa](ejecucion_final.txt).
- [Comprobaciones de integración](verificacion_script.txt): particiones, formato de matriz, diez concordancias con el adaptador de la interfaz y tres fallos deliberados en copias temporales bloqueados correctamente.

Las comprobaciones usaron los módulos y el modelo reales. No se sustituyó inferencia por simulaciones. El control se leyó solo para verificar integridad/formato y duplicados. No se normalizó ni se extrajeron características o decisiones del control. Las verificaciones no estiman generalización a nuevas identidades ni constituyen la evaluación final del proyecto.

La matriz completa y el manifiesto se regeneran con el script; no se incluyen imágenes ni modelos en esta entrega. Windows/Python 3.14 queda pendiente para el script nuevo. La aplicación anterior no se modifica.
