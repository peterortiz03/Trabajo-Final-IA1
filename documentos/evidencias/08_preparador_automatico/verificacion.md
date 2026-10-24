# Verificación de preparación automática · 23/10/2026

Se cambió la coordinación del preparador, sin modificar algoritmos, perfiles, modelos ni datos. Esta entrega incremental se aplica sobre interfaz inicial + preparador anterior.

| Comprobación | Resultado | Registro |
|---|---|---|
| Preparador, validación, sorteo y reproducción real | 6 aprobadas | [Backend](pruebas_backend.txt) |
| Selección automática, modo manual, cancelación y uso | 2 aprobadas | [Ventana del preparador](ventana_preparador.txt) |
| Regresión de ventana anterior | 2 aprobadas | [Ventana](regresion_ventana.txt) |
| Estados, recursos e inferencia real de huellas | 10 aprobadas | [Integración](regresion_integracion.txt) |

Entorno: Linux, Python 3.12, Tk 8.6.14 mediante escritorio virtual; NumPy 2.3.5, SciPy 1.17.0, Pillow 12.3.0 y scikit-learn 1.8.0. Captura de audio real no disponible aquí; no se simula un modelo operativo en la aplicación. El modelo de voz local del autor no está en el clon público.

Los ensayos del preparador usan el generador real y bases de desarrollo, sin imágenes de prueba final. Una prueba controla el selector aleatorio para verificar un recorrido determinista; la generación y la inferencia conservan sus módulos reales. Abrir opciones avanzadas o cancelar el selector no vuelve a generar. En modo automático no se consulta el reconocedor ni se busca una semilla favorable.

Se inspeccionaron [vista automática](automatico.png), [opciones avanzadas](avanzadas.png) y [ventana estrecha](estrecha.png). No se observaron superposiciones; la ventana usa desplazamiento cuando falta altura. La captura ilustrada utiliza un sorteo real (perfil movimiento, semilla 1488380000), sin clasificación durante esta inspección. El aviso de funciones limitadas corresponde a la voz ausente en este entorno.

No se repitieron las 170 consultas históricas, ni se midió una precisión nueva. Siguen pendientes Windows/Python 3.14, escalado de pantalla, micrófono local y evaluación independiente. Las impresiones de Anguli no están incorporadas como un nuevo dominio soportado.

En Windows ejecutar desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_preparar_captura*.py" -v
.\.venv\Scripts\python.exe src/interfaz.py
```

Se esperan ocho pruebas. Verificar selección automática, nueva captura, apertura de opciones avanzadas sin regeneración, reproducción manual y Usar esta captura con resultado pendiente. Compartir salida de pruebas, captura del preparador y errores si aparecen. No reenviar grabaciones ni datasets.
