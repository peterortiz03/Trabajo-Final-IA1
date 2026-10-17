"""Grabador guiado por consola. Captura solo después de pulsar Enter."""
import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

from audio_archivos import (RAIZ, COMANDOS, Catalogo, ahora, bloqueo,
                            calidad_inicial, json_atomico, resumen)


def cargar_config(ruta, duracion=None):
    cfg = json.loads(ruta.read_text(encoding='utf-8'))
    if duracion is not None:
        cfg['duracion_s'] = duracion
    if not math.isfinite(cfg['duracion_s']) or cfg['duracion_s'] <= 0:
        raise ValueError('La duración debe ser un número positivo de segundos.')
    n = cfg['cuenta_regresiva_s']
    if not isinstance(n, int) or n < 0:
        raise ValueError('La cuenta regresiva debe ser un entero no negativo.')
    frecuencias = cfg['frecuencias_alternativas_hz'][:]
    if cfg['frecuencia_captura_hz'] is not None:
        frecuencias.append(cfg['frecuencia_captura_hz'])
    if any(not isinstance(f, int) or f <= 0 for f in frecuencias):
        raise ValueError('Las frecuencias deben ser enteros positivos.')
    q = cfg['calidad']
    if not math.isfinite(q['rms_bajo_dbfs']) or q['rms_bajo_dbfs'] >= 0:
        raise ValueError('El umbral RMS debe ser negativo en dBFS.')
    if not 0 < q['pico_saturacion'] <= 1 or not 0 < q['fraccion_saturada_aviso'] <= 1:
        raise ValueError('Revisar umbrales de saturación: deben estar entre 0 y 1.')
    return cfg


def seleccionar_carpeta(base, prefijo, titulo):
    """Los directorios conservan personas/sesiones aunque no guarden muestras."""
    while True:
        opciones = sorted(p.name for p in base.iterdir()
                          if p.is_dir() and re.fullmatch(prefijo + r'\d+', p.name))
        print(f'\n{titulo}: {", ".join(opciones) or "ninguna todavía"}')
        valor = input('Escribí un ID existente, N para nuevo o 0 para cerrar: ').strip().upper()
        if valor == '0':
            raise EOFError
        if valor in opciones:
            return valor
        if valor == 'N':
            if prefijo == 'H':
                print('La persona debe conocer y aceptar el uso académico de su voz.')
                print('Publicarla en Internet requiere acordar ese uso por separado.')
                if input('¿Acepta participar? Escribí SI: ').strip().upper() != 'SI':
                    continue
            numero = max((int(x[1:]) for x in opciones), default=0) + 1
            nuevo = f'{prefijo}{numero:03d}'
            carpeta = base / nuevo
            carpeta.mkdir(exist_ok=False)
            json_atomico(carpeta / 'registro.json', {
                'id': nuevo, 'creado_utc': ahora(),
                'aceptacion_uso_academico_confirmada': prefijo == 'H',
                'nota': 'Sin nombres personales. No autoriza publicación de voz.'
            })
            return nuevo
        print('Elegí uno de los identificadores mostrados o N.')


def elegir_dispositivo(sd, cfg):
    dispositivos = sd.query_devices()
    apis = sd.query_hostapis()
    entradas = [i for i, d in enumerate(dispositivos) if d['max_input_channels'] > 0]
    if not entradas:
        raise RuntimeError('No se detectó micrófono. Conectalo y revisá los permisos de Windows.')
    print('\nMicrófonos disponibles (un mismo equipo puede aparecer en varias API):')
    for i in entradas:
        d = dispositivos[i]
        print(f"{i}: {d['name']} | {apis[d['hostapi']]['name']} | frecuencia por defecto: {d['default_samplerate']:g} Hz")
    while True:
        valor = input('Número de micrófono (Q para cerrar): ').strip()
        if valor.upper() == 'Q':
            raise EOFError
        if not valor.isdigit() or int(valor) not in entradas:
            print('Ingresá un número de la lista.')
            continue
        indice = int(valor)
        d = dispositivos[indice]
        preferida = cfg['frecuencia_captura_hz']
        frecuencias = ([preferida] if preferida is not None else
                       list(dict.fromkeys([int(d['default_samplerate'])] + cfg['frecuencias_alternativas_hz'])))
        for canales in (1, 2):
            if canales > d['max_input_channels']:
                continue
            for fs in frecuencias:
                try:
                    sd.check_input_settings(device=indice, channels=canales, samplerate=fs, dtype='int16')
                except sd.PortAudioError:
                    continue
                print(f'Captura: {fs} Hz, {canales} canal(es), PCM16. Original sin transformar.')
                return indice, fs, canales, d['name'], apis[d['hostapi']]['name']
        print('Ese dispositivo no admite la configuración. Probá otra entrada o frecuencia.')


def capturar(sd, dispositivo, fs, canales, cfg, comando):
    print(f'\nPALABRA: {comando.upper()} — hablá una vez, a volumen natural.')
    input('Cuando estés listo, pulsá Enter. Esperá el cartel GRABANDO...')
    for restante in range(cfg['cuenta_regresiva_s'], 0, -1):
        print(restante, flush=True)
        time.sleep(1)
    audio = sd.rec(round(cfg['duracion_s'] * fs), samplerate=fs,
                   channels=canales, dtype='int16', device=dispositivo, blocking=False)
    print(f">>> GRABANDO ({cfg['duracion_s']:g} segundos) <<<", flush=True)
    estado = sd.wait()
    if estado:
        raise RuntimeError(f'La captura tuvo pérdidas de audio ({estado}). Repetí la toma.')
    print('CAPTURA TERMINADA')
    return audio


def ejecutar(args, sd):
    ruta = Path(args.config)
    if not ruta.is_absolute():
        ruta = RAIZ / ruta
    cfg = cargar_config(ruta, args.duracion)
    cat = Catalogo()
    with bloqueo(cat.base):
        if cat.recuperar():
            print('Se completó un guardado confirmado que había quedado interrumpido.')
        filas = cat.verificar()
        print(f'Integridad: {len(filas)} originales y metadatos coherentes.')
        if args.verificar or args.resumen:
            resumen(cat)
            return
        dispositivo, fs, canales, nombre, api = elegir_dispositivo(sd, cfg)
        hablante = sesion = None
        while True:
            if hablante is None:
                resumen(cat)
                hablante = seleccionar_carpeta(cat.originales, 'H', 'Personas')
                sesion = None
            if sesion is None:
                print('Sesión = tanda de grabaciones. Continuá una existente o creá otra si cambió el día o las condiciones.')
                sesion = seleccionar_carpeta(cat.originales / hablante, 'S', 'Sesiones de ' + hablante)
            print(f'\n{hablante} / {sesion}: 1 Reconocer | 2 Identificar | 3 Salir (palabra)')
            print('4 Resumen | 5 Cambiar persona | 6 Cambiar sesión | 7 Micrófono | 0 Cerrar grabador')
            opcion = input('Opción: ').strip()
            if opcion == '0':
                return
            if opcion == '4':
                resumen(cat)
            elif opcion == '5':
                hablante = None
            elif opcion == '6':
                sesion = None
            elif opcion == '7':
                dispositivo, fs, canales, nombre, api = elegir_dispositivo(sd, cfg)
            elif opcion in ('1', '2', '3'):
                comando = COMANDOS[int(opcion)-1]
                repetir = True
                while repetir:
                    try:
                        audio = capturar(sd, dispositivo, fs, canales, cfg, comando)
                    except (sd.PortAudioError, RuntimeError) as e:
                        sd.stop()
                        print(f'No se guardó la captura: {e}')
                        break
                    q = calidad_inicial(audio, cfg['calidad'])
                    print(f"RMS: {q['rms_dbfs']} dBFS | pico: {q['pico']} | avisos: {q['avisos_calidad'] or 'ninguno'}")
                    print('Escuchá la palabra completa; estos controles no confirman presencia de voz.')
                    while True:
                        accion = input('P Reproducir | G Guardar | R Repetir | D Descartar: ').strip().upper()
                        if accion == 'P':
                            try:
                                sd.play(audio, fs, blocking=True)
                            except sd.PortAudioError as e:
                                print(f'No se pudo reproducir por la salida predeterminada: {e}')
                                print('Revisá la salida de audio de Windows; la captura sigue en memoria.')
                        elif accion == 'G':
                            if q['avisos_calidad']:
                                print('Se conservará el original con avisos para revisión; no se declara apto.')
                                if input('¿Guardar igualmente? SI: ').strip().upper() != 'SI':
                                    continue
                            fila = cat.guardar(audio, fs, hablante, sesion, comando, cfg, nombre, api)
                            print('Guardado:', fila['ruta_original'])
                            resumen(cat)
                            repetir = False
                            break
                        elif accion in ('R', 'D'):
                            print('Toma no guardada; no consume número de muestra.')
                            repetir = accion == 'R'
                            break
                        else:
                            print('Elegí P, G, R o D.')
            else:
                print('Opción no válida.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config/audio_v1.json')
    parser.add_argument('--duracion', type=float, help='Duración en segundos para esta ejecución')
    parser.add_argument('--dispositivos', action='store_true')
    parser.add_argument('--verificar', action='store_true', help='Revisar integridad sin usar el micrófono')
    parser.add_argument('--resumen', action='store_true')
    args = parser.parse_args()
    sd = None
    try:
        if not (args.verificar or args.resumen):
            import sounddevice as sd
        if args.dispositivos:
            if sd is None:
                import sounddevice as sd
            print(sd.query_devices())
        else:
            ejecutar(args, sd)
    except (KeyboardInterrupt, EOFError):
        print('\nGrabador cerrado. Una toma no confirmada no se registra.')
        print('Si se interrumpió un guardado confirmado, se verificará al reiniciar.')
    except (OSError, ValueError, RuntimeError, KeyError, ImportError) as e:
        print(f'No se puede continuar: {e}', file=sys.stderr)
        print('Conservá los archivos y copiá este mensaje para revisarlo.', file=sys.stderr)
        return 1
    except Exception as e:
        # PortAudioError no hereda de OSError. No se elimina ningún original.
        print(f'Error {type(e).__name__}: {e}', file=sys.stderr)
        print('Revisá dispositivo, permisos y dependencias. Conservá los datos.', file=sys.stderr)
        return 1
    finally:
        if sd is not None:
            sd.stop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
