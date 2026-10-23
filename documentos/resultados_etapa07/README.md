# Evidencia seleccionada del cierre de audio

| Carpeta | Origen Windows | Alcance |
|---|---|---|
| 01_loso | 20261023T033845_362145Z | PCA y comparación K-NN; 169/179 en CV usada para seleccionar |
| 02_microfono_conocida | 20261023T115814_373387Z | 15/15 comandos nuevos de H001; otra palabra y silencio por separado |
| 03_sinteticas | 20261023T121951_936996Z | Cuatro voces sintéticas por celular; mismo ID; ensayo exploratorio |

Los archivos se seleccionaron de los ZIP compartidos por el autor. CSV, resúmenes
y detalles de tomas se conservan sin corregir sus resultados. contexto.json
selecciona metadatos de sesion.json y omite la ruta personal absoluta del modelo.
La aclaración posterior sobre la primera toma sintética está en
03_sinteticas/observaciones_autor.json. No se sobrescribió el recuento original.

procedencia.json registra los archivos de origen y hashes de los paquetes.
integridad.json verifica los archivos de evidencia presentes. El resumen original
de 01_loso conserva su manifiesto completo; varios archivos de aquella corrida,
como el modelo NPZ, no forman parte de esta selección. Eso está declarado, no
constituye un hash fallido. Las cuatro figuras son las originales de Windows.

No se publican WAV de las consultas nuevas, sus vectores ni el modelo NPZ.
Los archivos completos deben conservarse localmente para inferencia y reproducción.
No hay validación humana externa ni prueba final en estas carpetas.

Consultar la [bitácora](../../notebooks/07_pca_knn_audio.ipynb) y el
[cierre de etapa](../cierre_etapa07.md).
