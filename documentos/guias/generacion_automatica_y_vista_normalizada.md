# Interfaz: generación automática y vista normalizada

## Archivos de la modificación

| Archivo | Cambio |
|---|---|
| src/interfaz.py | Selector Aleatoria/Autorizada/Intrusa, botón Generar muestra, original y normalizada, vista de máscara, limpieza del estado |
| src/interfaz_servicios.py | Opción para devolver copias de la normalizada y máscara usadas por el extractor, sin normalizar dos veces |
| src/generacion_muestra.py | Elige una base de desarrollo y genera una sola captura en memoria |
| config/generacion_interfaz_v1.json | Lista explícita de bases de desarrollo permitidas |
| tests/test_generacion_interfaz.py | Filtros, generación, normalización y recorrido gráfico |

No se reemplaza config/aplicacion.json ni ningún modelo. El k=5 instalado en la actualización anterior se conserva. No cambia el preprocesamiento de audio, el umbral ni el K-means.

## Instalación

1. Cerrar el programa.
2. Descomprimir el ZIP en una carpeta temporal.
3. Copiar **el contenido de archivos/** sobre la raíz de Trabajo-Final-IA1, combinando carpetas y reemplazando los archivos del mismo nombre. No poner la carpeta contenedora dentro de src/.
4. Mantener las bases existentes en datos/bases y la configuración conjunto_v1.json. No hay que generar nuevamente el dataset ni ejecutar Anguli.

No requiere instalar dependencias nuevas. Antes de reemplazar, conservar una copia si se hicieron otros cambios personales a interfaz.py o interfaz_servicios.py desde la versión publicada usada para este paquete.

## Uso

En el panel izquierdo elegir Aleatoria, Autorizada o Intrusa y pulsar **Generar muestra**. Se elige una base permitida y luego perfil/semilla aleatorios. Aleatoria sortea entre las cinco bases: no implica 50/50 entre grupos (hay tres autorizadas y dos intrusas). Cada una tiene igual probabilidad.

Se genera UNA captura y pasa directamente a la consulta activa. La selección de grupo solo controla la base de origen, no determina la predicción ni garantiza aceptación. No se vuelve a sortear buscando un acierto. Las intrusas I03/I04 y las imágenes de prueba final no se usan.

Generar no reconoce. Después decir Reconocer o usar el botón manual. La normalizada aparece únicamente tras una evaluación completada, junto a la captura de entrada. Es una copia de la imagen usada por el extractor; no se normaliza otra vez para dibujar. El control Ver máscara permite alternar esa segunda vista.

Cambiar de imagen limpia el resultado, identidad y normalizada anteriores. Una generación fallida conserva la consulta anterior y muestra un aviso. Durante una operación se bloquean las acciones incompatibles.

Las opciones avanzadas conservan selección de base desde archivo, perfil/semilla manuales y guardado. El botón principal Generar muestra siempre usa parámetros aleatorios: las opciones manuales solo se aplican a Generar nueva captura del preparador avanzado. Seleccionar desde archivo sigue disponible.

La referencia de base elegida se conserva en la receta para trazabilidad y no se muestra como identidad reconocida. El módulo de reconocimiento solo recibe la imagen. No se guarda nada ni se agrega al entrenamiento automáticamente.

## Pruebas desde PowerShell, en la raíz del proyecto

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_generacion_interfaz.py" -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_interfaz_integracion.py" -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_preparar_captura.py" -v
.\.venv\Scripts\python.exe src/interfaz.py
```

El archivo nuevo contiene cinco pruebas: cuatro sin pantalla y una gráfica. En Windows con escritorio debe ejecutarse también la gráfica; aquí se omitió por ausencia de pantalla.

Comprobar visualmente:

1. Aleatoria → Generar muestra: debe aparecer una captura y quedar pendiente.
2. Autorizada → Generar muestra → Reconocer: debe aparecer la normalizada si se completa el procesamiento; la aceptación depende del modelo. Identificar solo funciona si se autoriza.
3. Activar Ver máscara: debe cambiar solo la segunda vista, sin alterar distancia o decisión.
4. Intrusa → Generar muestra: deben borrarse el resultado, identidad y normalizada anteriores. Reconocer debe evaluar realmente; conservar cualquier falsa aceptación o rechazo observado, sin regenerar para ocultarlo.
5. Abrir opciones avanzadas y comprobar selección manual, generación, usar y guardar.
6. Seleccionar una imagen desde archivo, cancelar otra selección y comprobar que el estado se conserva.
7. Probar voz y controles manuales; en Detalles técnicos debe seguir apareciendo k=5 si está instalada la actualización anterior.
8. Reducir la ventana y usar el escalado habitual de Windows. Verificar que se lean ambos paneles y pueda desplazarse el contenido.

Compartir la salida de las pruebas y una captura de la ventana después de reconocer con original/normalizada visibles. Si aparece cualquier fallo de generación o superposición visual, conservar el mensaje y la receta disponible.

## Validación realizada

Se ejecutaron cuatro pruebas nuevas sin pantalla, las diez de integración y las pruebas del preparador. Se comprobó igualdad píxel a píxel entre la vista normalizada retornada y la normalización real, y coincidencia de decisión/distancia con y sin imágenes de vista. Se generó una captura real con parámetros fijos en el test; no se simuló la inferencia.

La prueba gráfica queda incluida para Windows, pero no se ejecutó aquí por ausencia de escritorio/Xvfb. No se afirma una inspección visual nueva de la ventana ni una prueba nueva de micrófono. El código Python fue compilado sin errores.

No se modificó el repositorio remoto, no se hicieron commits ni push. La documentación de la ampliación está en documentos/guias/generacion_automatica_y_vista_normalizada.md.
