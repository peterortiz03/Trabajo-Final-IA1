# Índice de documentación

## Documentación vigente

- [Verificación estadística](verificacion_estadistica.md): notebook 05, partición de desarrollo de audio y diagnóstico previo a PCA.

- [README del repositorio](../README.md): objetivo completo, estado de etapas e instrucciones de consulta.
- [Bitácora de huellas](../notebooks/01_bitacora_dataset_normalizacion.ipynb): explicación del avance y resultados ejecutados.
- [Normalización final](normalizacion_final.md): contrato de la función reutilizable y salidas.
- [Uso de IA generativa](uso_ia_generativa.md): asistencia, solicitudes y controles realizados.
- [Resumen de ejecución publicado](../datos/procesados/normalizacion_final_v1/resumen.json) y [detalle](../datos/procesados/normalizacion_final_v1/detalle.json): evidencia del lote definitivo.

## Antecedentes conservados

| Documento | Etapa documentada |
|---|---|
| `piloto_decisiones_y_fuentes.md` | Selección inicial de bases y ensayo de deformaciones |
| `etapa_conjunto_v1.md` | Generación del conjunto inicial de 160 muestras |
| `ampliacion_entrenamiento.md` | Ampliación a 190 muestras |
| `rotaciones_entrenamiento.md` | Ampliación a 220 muestras |
| `normalizacion_etapa1.md` | Ensayo de región y centrado, anterior a la corrección de orientación |
| `verificacion_asistente_conjunto_v1.json` | Comprobación auxiliar del conjunto inicial |
| `verificacion.txt` | Comprobación auxiliar de la normalización final |
| `guia_commit_github.md` | Instrucciones operativas usadas para la primera publicación |

Estos documentos conservan su contexto histórico. Frases como «validación local pendiente» describen el estado de aquella entrega, no el estado vigente. Los registros de pruebas auxiliares no se reescriben para presentarlos como resultados de una ejecución posterior. El estado actual se consulta en la bitácora y en los controles del lote final.

Algunos documentos históricos enumeran archivos de los paquetes de entrega, como propuestas de README, que fueron integrados y no forman parte de la publicación final. Esto no indica una dependencia faltante del programa. Las instrucciones antiguas de instalación por ZIP se conservan como antecedentes; para una clonación actual corresponde seguir el README principal.

## Continuidad del proyecto

Conservar `01_bitacora_dataset_normalizacion.ipynb` como registro de esta etapa. Crear nuevos notebooks numerados para avances posteriores, con nombre descriptivo; por ejemplo, `02_dataset_voz.ipynb` si el siguiente avance corresponde a voz. La numeración refleja el orden real del trabajo y no fija una arquitectura.

Cada nueva bitácora debería registrar objetivo, entradas, método, decisiones, código reutilizable, resultados, limitaciones y estado final. Actualizar la tabla de etapas del README con cada hito. En el reconocimiento de huellas deben documentarse características, K-means con k = 3, correspondencia entre grupos e identidades y umbral de rechazo; en voz, el dataset, las características acústicas y K-NN. Los parámetros se seleccionan con desarrollo, manteniendo la prueba reservada.

No es necesario reorganizar ahora las rutas de huellas: están registradas en configuraciones y catálogos. Incorporar rutas propias para voz cuando se diseñe ese módulo, evitando cambios de ubicación sin actualizar las referencias.
