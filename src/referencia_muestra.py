"""Compara una decisión terminada con su referencia; no interviene en inferencia."""


def comparar_referencia(receta, resultado):
    referencia = (receta or {}).get('origen_sorteo') or {}
    identidad = referencia.get('base_id')
    grupo = referencia.get('grupo_referencia')
    if not identidad or grupo not in ('autorizado', 'intruso'):
        return dict(estado='desconocido', codigo='referencia_desconocida', texto=(
            'Referencia desconocida. No se puede comprobar automáticamente el acierto.\n'
            'Esta captura no tiene una referencia registrada por la generación automática.'))
    aceptada = bool(resultado['aceptada'])
    predicha = resultado.get('identidad')
    if grupo == 'intruso':
        codigo, titulo = ('falsa_aceptacion', 'Falsa aceptación') if aceptada else ('rechazo_correcto', 'Rechazo correcto')
    elif not aceptada:
        codigo, titulo = 'falso_rechazo', 'Falso rechazo'
    elif predicha == identidad:
        codigo, titulo = 'identificacion_correcta', 'Identificación correcta'
    else:
        codigo, titulo = 'identidad_incorrecta', 'Identidad incorrecta'
    correcto = codigo in ('rechazo_correcto', 'identificacion_correcta')
    decision = f'Aceptada como {predicha}' if aceptada else 'Rechazada'
    origen = 'autorizada' if grupo == 'autorizado' else 'intrusa'
    texto = (f'{titulo}\nReferencia: {identidad} · {origen}.\nDecisión del sistema: {decision}.\n'
             'La referencia se usa solo para esta comparación; el modelo evalúa la imagen.')
    return dict(estado='correcto' if correcto else 'error', codigo=codigo, texto=texto)
