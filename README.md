# Trabajo Final — Inteligencia Artificial I

Proyecto académico de comparación de huellas dactilares sintéticas. Estado al 15/10/2026: dataset generado y normalización geométrica v1 implementada. Reconocimiento y evaluación del modelo pendientes.

## Datos

Se utilizan siete identidades sintéticas de Anguli: tres autorizados y cuatro intrusos. El conjunto contiene 220 capturas: 120 de entrenamiento, 50 de validación y 50 de prueba. Las ampliaciones de entrenamiento incorporan deformaciones locales y rotaciones hasta ±90°. Semillas, parámetros y hashes documentan la procedencia. No se utilizan huellas reales.

## Entorno

Python y un entorno virtual local. Dependencias de los programas en `requirements.txt`:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si el entorno ya existe y funciona, conservarlo. Para ejecutar los notebooks desde VS Code instalar también `ipykernel` en ese entorno:

```powershell
.\.venv\Scripts\python.exe -m pip install ipykernel
```

## Recorrido del proyecto

- `src/`: programas y funciones reutilizables.
- `config/`: configuraciones de generación y normalización.
- `datos/bases/`: patrones de Anguli y procedencia.
- `datos/originales/`: capturas sintéticas antes de normalizar.
- `datos/procesados/normalizacion_final_v1/`: resultados finales y catálogo.
- `notebooks/01_bitacora_dataset_normalizacion.ipynb`: explicación del avance y comprobaciones.
- `documentos/`: decisiones e instrucciones.
- `resultados/`: evidencia de ensayos anteriores.

## Uso de la normalización

Si los originales ya existen:

```powershell
.\.venv\Scripts\python.exe src/normalizar_todas.py
```

La ejecución no reemplaza carpetas existentes. No es necesario repetirla si ya se generaron las 220 salidas correctamente.

El catálogo de entrada es `datos/metadatos_con_rotaciones_train_v1.csv`. Para las siguientes etapas se utiliza `datos/procesados/normalizacion_final_v1/catalogo_normalizado.csv`, leyendo las columnas `normalizada` y `alternativa_180`.

Por muestra se guardan tres PNG: representación principal, alternativa girada 180° y máscara de región. Son 220 muestras, no 660. La orientación del eje es ambigua en 180°; el futuro método de comparación deberá contemplarlo. La versión actual centra y gira, sin igualar contraste, corregir deformación elástica ni normalizar resolución física.

## Reproducción desde las bases

En una copia de trabajo sin salidas generadas, ejecutar en orden:

```powershell
.\.venv\Scripts\python.exe src/generar_conjunto.py
.\.venv\Scripts\python.exe src/ampliar_entrenamiento.py
.\.venv\Scripts\python.exe src/ampliar_rotaciones.py
.\.venv\Scripts\python.exe src/normalizar_todas.py
```

Conservar todos los módulos de `src/`, incluidos los del piloto, porque los generadores reutilizan funciones anteriores. Las bases y sus configuraciones deben estar en las rutas registradas. No cambiar las particiones al regenerar.

## Alcance

Este dataset sirve para el escenario académico definido, con diversidad limitada a siete bases. No demuestra generalización a huellas reales. La prueba se reserva para evaluación final; las imágenes de inspección del notebook pertenecen a desarrollo.
