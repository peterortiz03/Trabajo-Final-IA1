"""Estado del ciclo, independiente de Tk, del micrófono y de los modelos."""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class EstadoHuella(str, Enum):
    SIN_IMAGEN = 'sin_imagen'
    PENDIENTE = 'pendiente'
    AUTORIZADA = 'autorizada'
    RECHAZADA = 'rechazada'
    ERROR = 'error'


@dataclass
class Sesion:
    imagen: Path | None = None
    estado: EstadoHuella = EstadoHuella.SIN_IMAGEN
    identidad_visible: str = ''
    resultado: dict | None = field(default=None, repr=False)
    operacion: str = ''
    revision: int = 0
    secuencia: int = 0
    cerrada: bool = False

    def seleccionar(self, ruta):
        if ruta is None:  # Cancelar conserva exactamente el ciclo vigente.
            return
        self._libre()
        self.imagen = Path(ruta)
        self.revision += 1
        self.limpiar()

    def limpiar(self):
        self.resultado = None
        self.identidad_visible = ''
        self.estado = EstadoHuella.PENDIENTE if self.imagen else EstadoHuella.SIN_IMAGEN

    def _libre(self):
        if self.cerrada or self.operacion:
            raise ValueError('Esperá a que termine la operación actual.')

    def iniciar(self, operacion):
        self._libre()
        self.secuencia += 1
        self.operacion = operacion
        return self.secuencia, self.revision

    def vigente(self, token):
        return not self.cerrada and token == (self.secuencia, self.revision) and bool(self.operacion)

    def terminar(self, token):
        if not self.vigente(token):
            return False
        self.operacion = ''
        return True

    def reconocer(self):
        self._libre()
        if self.imagen is None:
            raise ValueError('Seleccioná una huella para comenzar.')
        self.limpiar()  # Un intento nuevo invalida la autorización anterior.
        return self.iniciar('huella')

    def evaluada(self, token, resultado=None, error=None):
        if not self.terminar(token):
            return False
        self.identidad_visible = ''
        self.resultado = resultado if error is None else None
        self.estado = (EstadoHuella.ERROR if error is not None else
                       EstadoHuella.AUTORIZADA if resultado['aceptada'] else EstadoHuella.RECHAZADA)
        return True

    def identificar(self):
        self._libre()
        if self.estado != EstadoHuella.AUTORIZADA or not self.resultado:
            raise ValueError('Primero reconocé la huella seleccionada y obtené una autorización.')
        self.identidad_visible = self.resultado['identidad']
        return self.identidad_visible

    def cerrar(self):
        self.cerrada = True
        self.secuencia += 1  # Invalida cualquier respuesta que llegue tarde.
