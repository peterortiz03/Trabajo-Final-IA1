"""Migración de organización v1. Por defecto solo muestra el plan. Python estándar."""
import argparse
from datetime import datetime,timezone
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile

EVIDENCIAS={
 'resultados_etapa06':'06_huellas_referencia',
 'resultados_etapa07':'07_comandos_voz',
 'resultados_etapa08':'08_integracion',
 'resultados_preparacion_capturas':'08_preparador_diagnostico',
 'resultados_preparacion_automatica':'08_preparador_automatico',
 'resultados_anguli_impresiones_v1':'08_anguli_diagnostico',
 'resultados_adaptacion_anguli_v1':'08_huellas_combinadas',
}
GUIAS={'interfaz_integracion.md','preparacion_capturas.md','modelo_combinado_anguli_v1.md','guia_vectorizacion_y_clasificacion.md'}
HISTORICO={'guia_commit_github.md','verificacion.txt','verificacion_asistente_conjunto_v1.json','verificacion_caracteristicas_audio_180.json','verificacion_caracteristicas_huellas_asistente.json'}
BORRAR={'LEEME_HITO1_HUELLAS.md','LEEME_HITO2_AUDIO.md'}
MARCADOR='documentos/guias/migracion_organizacion_v1.json'

def sha(b):return hashlib.sha256(b).hexdigest()
def dump(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def json_bytes(b):return json.loads(b.decode('utf-8-sig'))

def destino(n):
 for antiguo,nuevo in EVIDENCIAS.items():
  pref='documentos/'+antiguo+'/'
  if n.startswith(pref):return 'documentos/evidencias/'+nuevo+'/'+n[len(pref):]
 p=Path(n)
 if p.parent.as_posix()=='documentos' and p.name not in ('README.md','uso_ia_generativa.md'):
  area='guias' if p.name in GUIAS else 'historico' if p.name in HISTORICO else 'etapas'
  return f'documentos/{area}/{p.name}'
 return n

def planificar(root):
 if (root/MARCADOR).exists():raise ValueError('Esta migración ya fue aplicada; no se repite.')
 nombres=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
 originales={n:(root/n).read_bytes() for n in nombres if n and (root/n).is_file()}
 for n in ['config/interfaz_v1.json','config/interfaz_anguli_experimental_v1.json','src/interfaz.py',
           'src/adaptar_modelo_anguli.py','documentos/resultados_adaptacion_anguli_v1/modelo/modelo_congelado.npz']:
  if n not in originales:raise ValueError('Falta un recurso de la versión esperada: '+n)
 salidas={};mapa={n:destino(n) for n in originales if n not in BORRAR}
 prefijos={'documentos/'+k:'documentos/evidencias/'+v for k,v in EVIDENCIAS.items()}
 prefijos.update({n:mapa[n] for n in mapa if Path(n).parent.as_posix()=='documentos' and n!=mapa[n]})
 def rutas(texto):
  texto=texto.replace('**El comando sin --config sigue abriendo el modelo anterior** (72 columnas), conservado como respaldo.', '**El inicio sin argumentos abre ahora el combinado**. El respaldo se elige con config/aplicacion_respaldo.json.')
  texto=texto.replace('El comando sin `--config` abre el respaldo anterior de 72 columnas.', 'El comando sin `--config` abre ahora el combinado; el respaldo se elige con config/aplicacion_respaldo.json.')
  texto=texto.replace('El lanzamiento normal sigue usando el modelo anterior; el experimental se elige explícitamente con --config.', 'El lanzamiento normal usa el combinado mediante la configuración principal; el modelo anterior se elige con config/aplicacion_respaldo.json.')
  for old,new in sorted(prefijos.items(),key=lambda t:-len(t[0])):texto=texto.replace(old,new)
  return texto
 def enlaces(texto,viejo,nuevo):
  def cambio(m):
   link=m.group(1)
   if ':' in link or link.startswith('#'):return m.group(0)
   parte,sep,ancla=link.partition('#')
   res=(root/Path(viejo).parent/parte).resolve()
   try:rel=res.relative_to(root).as_posix()
   except ValueError:return m.group(0)
   if rel not in mapa:return m.group(0)
   target=os.path.relpath(root/mapa[rel],root/Path(nuevo).parent).replace('\\','/')
   return ']('+target+(sep+ancla if sep else '')+')'
  return re.sub(r'\]\(([^)]+)\)',cambio,texto)
 for old,b in originales.items():
  if old in BORRAR:continue
  new=mapa[old];p=Path(old)
  # JSON/CSV/PNG/NPZ de evidencia se conservan byte a byte.
  if p.suffix=='.md':
   t=enlaces(b.decode('utf-8-sig'),old,new)
   # Referencias de ejecución en código del texto, tras corregir los enlaces.
   t=rutas(t)
   b=t.encode('utf-8')
  elif p.suffix=='.py' and (p.parts[0]=='tests' or (p.parts[0]=='src' and p.name in {'interfaz.py','interfaz_servicios.py','adaptar_modelo_anguli.py','diagnosticar_impresiones_anguli.py','verificar_preparacion_capturas.py','probar_modelo_anguli.py'})):
   t=rutas(b.decode('utf-8-sig'))
   if p.name in ('interfaz.py','interfaz_servicios.py'):
    t=t.replace('config/interfaz_v1.json','config/aplicacion.json')
   # Diagnósticos y regresiones científicas mantienen su modelo de referencia.
   if p.parts[0]=='tests' or p.name in ('adaptar_modelo_anguli.py','diagnosticar_impresiones_anguli.py','verificar_preparacion_capturas.py'):
    t=t.replace('config/interfaz_v1.json','config/aplicacion_respaldo.json')
   if p.name=='probar_modelo_anguli.py':
    t=t.replace("RAIZ/'documentos/evidencias/08_huellas_combinadas/config_interfaz_experimental.json'","RAIZ/'config/aplicacion.json'")
   if p.name=='test_modelo_anguli.py':
    t=t.replace("leer_json(PAQUETE/'config_interfaz_experimental.json')","leer_json(RAIZ/'config/aplicacion.json')")
   b=t.encode('utf-8')
  elif p.suffix=='.ipynb':
   nb=json_bytes(b)
   for cell in nb['cells']:
    t=''.join(cell['source'])
    if cell['cell_type']=='markdown':t=enlaces(t,old,new)
    t=rutas(t)
    cell['source']=t.splitlines(keepends=True)
    # Las salidas previas conservan su valor histórico; no se simulan ejecuciones.
   b=dump(nb)
  elif p.parts[0]=='config' and p.suffix=='.json':
   b=rutas(b.decode('utf-8-sig')).encode('utf-8')
  salidas[new]=b
 # Paquetes operativos: copias exactas de parámetros; evidencia histórica permanece intacta.
 for n,b in originales.items():
  pref='documentos/resultados_etapa06/03_rechazo/'
  if n.startswith(pref):salidas['modelos/huellas/referencia_v1/'+n[len(pref):]]=b
  pref='documentos/resultados_adaptacion_anguli_v1/modelo/'
  if n.startswith(pref):salidas['modelos/huellas/combinado_v1/'+n[len(pref):]]=b
 salidas['modelos/huellas/combinado_v1/seleccion.json']=originales['documentos/resultados_adaptacion_anguli_v1/seleccion.json']
 salidas['modelos/huellas/referencia_v1/seleccion.json']=originales['documentos/resultados_etapa06/02_seleccion/resumen.json']
 principal=json_bytes(originales['config/interfaz_anguli_experimental_v1.json'])
 respaldo=json_bytes(originales['config/interfaz_v1.json'])
 for cfg,nombre in [(principal,'combinado'),(respaldo,'referencia')]:
  cfg['huellas']['modelo']=f'modelos/huellas/{nombre}_v1'
  cfg['huellas']['seleccion']=f'modelos/huellas/{nombre}_v1/seleccion.json'
 for n,cfg in [('aplicacion.json',principal),('aplicacion_respaldo.json',respaldo),('interfaz_v1.json',principal),('interfaz_anguli_experimental_v1.json',principal)]:salidas['config/'+n]=dump(cfg)
 salidas['iniciar.ps1']=('''$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    & "$PSScriptRoot\\.venv\\Scripts\\python.exe" "$PSScriptRoot\\src\\interfaz.py" --config "$PSScriptRoot\\config\\aplicacion.json"
    $codigoSalida = $LASTEXITCODE
} finally { Pop-Location }
exit $codigoSalida
''').encode()
 salidas['modelos/README.md']='''# Modelos operativos

Principal: huellas/combinado_v1, 36/144 columnas, modelo 20261023T222326_850333Z. Respaldo: huellas/referencia_v1, 72/144. Parámetros copiados sin reajuste. Las copias originales en documentos/evidencias son instantáneas de procedencia, no otra configuración operativa.

El audio conserva la ruta local anterior de config/aplicacion.json y sus contratos de extracción. No se mueve ni publica desde esta migración: no está disponible en el clon público. Moverlo requiere inventariar su paquete completo en Windows.
'''.encode()
 salidas['documentos/README.md']=('''# Documentación del proyecto

- [Guías de uso e instalación](guias/README.md).
- [Cierre de desarrollo](etapas/cierre_etapa08.md).
- [Bitácora 08](../notebooks/08_interfaz_integracion_ampliacion_anguli.ipynb).
- [Asistencia de IA](uso_ia_generativa.md).

Etapas: desarrollo y cierres en etapas/. Evidencias: registros originales en evidencias/. Histórico: verificaciones e instrucciones antiguas en historico/. Los resúmenes originales pueden contener rutas de su ejecución de origen; no se reescribieron ni se alteraron sus hashes. La configuración operativa está en config/aplicacion.json.
''').encode()
 salidas['documentos/guias/README.md']=('''# Uso de la versión para la muestra

Iniciar desde PowerShell en la raíz:

```powershell
.\\iniciar.ps1
```

También: `.\\.venv\\Scripts\\python.exe src/interfaz.py` (ahora abre el combinado).

Respaldo anterior: `.\\.venv\\Scripts\\python.exe src/interfaz.py --config config/aplicacion_respaldo.json`.

No entrenar para iniciar. Modelo principal 20261023T222326_850333Z, 36/144 columnas; audio conserva sus recursos locales. Las guías de etapas conservan comandos históricos; para ejecución actual prevalecen estos comandos.

- [Interfaz](interfaz_integracion.md)
- [Preparador](preparacion_capturas.md)
- [Modelo combinado](modelo_combinado_anguli_v1.md)
- [Índice de ejecuciones](indice_ejecuciones.csv)

No se renombraron corridas fechadas, src/ o datos/. Los LEEME_HITO1/2 de instalación de ZIP se retiraron de la raíz y están en el respaldo de migración.
''').encode()
 intro='''> **Organización actualizada:** iniciar con `iniciar.ps1` o `python src/interfaz.py`. Ambos usan el modelo combinado. Configuración principal: `config/aplicacion.json`; respaldo: `config/aplicacion_respaldo.json`. Los comandos posteriores que describen versiones previas conservan contexto histórico. Consultar [guía actual](documentos/guias/README.md).

'''
 salidas['README.md']=intro.encode()+salidas['README.md']
 # Índice descriptivo, sin cambiar identificadores/rutas originales.
 registros=[('20261023T222326_850333Z','modelo_huellas_combinado','modelos/huellas/combinado_v1'),('20261023T021746_872267Z','modelo_huellas_referencia','modelos/huellas/referencia_v1')]
 for carpeta in ('resultados','experimentos'):
  if (root/carpeta).exists():
   for p in sorted((root/carpeta).rglob('*')):
    if p.is_dir() and re.fullmatch(r'\d{8}T\d{6}(?:_\d+)?Z',p.name):registros.append((p.name,p.parent.name,p.relative_to(root).as_posix()))
 import io
 f=io.StringIO(newline='');w=csv.writer(f);w.writerow(['identificador','tarea_o_contenedor','ruta']);w.writerows(registros)
 salidas['documentos/guias/indice_ejecuciones.csv']=f.getvalue().encode('utf-8-sig')
 # Evitar una mudanza sobre contenido local que Git no conoce.
 for n in salidas:
  if (root/n).exists() and n not in originales:raise ValueError('Destino local ya existente, revisar: '+n)
 return originales,salidas,mapa


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--raiz',type=Path,default=Path.cwd())
 p.add_argument('--aplicar',action='store_true')
 p.add_argument('--restaurar',type=Path,help='Restaurar un respaldo creado por esta herramienta.')
 a=p.parse_args();root=a.raiz.resolve()
 if a.restaurar:
  with zipfile.ZipFile(a.restaurar) as z:
   registro=json.loads(z.read('__migracion__.json'))
   # No sobrescribir ediciones posteriores sin revisión.
   for n,h in registro['posteriores'].items():
    if not (root/n).is_file() or sha((root/n).read_bytes())!=h:raise ValueError('Archivo editado después de migrar: '+n)
   for n in registro['posteriores']:
    if n not in registro['anteriores']:(root/n).unlink()
   for n in registro['anteriores']:
    dest=root/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(n))
  print('Restaurados archivos anteriores; carpetas vacías pueden permanecer. Git no fue modificado.');return
 old,new,mapa=planificar(root)
 borrar=[n for n in old if n not in new]
 escribir={n:b for n,b in new.items() if old.get(n)!=b}
 print(f'Plan: {len(escribir)} archivos nuevos/modificados; {len(borrar)} rutas retiradas o trasladadas.')
 print('Se conservan src/, datos/, parámetros aprendidos, audio local y corridas fechadas.')
 for n in sorted(borrar):print('RETIRAR/TRASLADAR',n,'->',mapa.get(n,'respaldo de migración'))
 if not a.aplicar:
  print('Solo revisión. Para ejecutar: añadir --aplicar. No se modificó ningún archivo.');return
 if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root).strip():raise ValueError('Hay cambios versionados sin registrar. Confirmarlos antes de aplicar.')
 fecha=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
 backup=root.parent/f'{root.name}_respaldo_organizacion_{fecha}.zip'
 afectados={n:old[n] for n in set(borrar)|set(escribir) if n in old}
 reporte={'fecha_utc':fecha,'anteriores':list(afectados),'posteriores':{n:sha(b) for n,b in escribir.items()}}
 # El marcador también queda incluido para permitir restauración.
 marcador=dump({'fecha_utc':fecha,'respaldo':str(backup),'nota':'No se cambiaron algoritmos o datasets. Índice de rutas en este respaldo.'})
 escribir[MARCADOR]=marcador;reporte['posteriores'][MARCADOR]=sha(marcador)
 with zipfile.ZipFile(backup,'x',zipfile.ZIP_DEFLATED) as z:
  for n,b in afectados.items():z.writestr(n,b)
  z.writestr('__migracion__.json',dump(reporte))
 try:
  for n in borrar:(root/n).unlink()
  for n,b in escribir.items():
   dest=root/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
 except Exception:
  print('Error durante migración. Respaldo completo de archivos afectados:',backup);raise
 print('Migración aplicada. Respaldo:',backup)
 print('No se hizo git add, commit o push. Revisar y probar antes de confirmar.')

if __name__=='__main__':
 try:main()
 except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as e:raise SystemExit('No se completó la operación: '+str(e))
