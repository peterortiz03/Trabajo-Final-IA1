"""Ventana única de control de acceso. Ejecutar: python src/interfaz.py.

Tk se usa exclusivamente desde el hilo principal. Los trabajadores solo devuelven
mensajes a una cola; cada respuesta lleva un token de operación y de imagen.
"""
import argparse
import ctypes
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
import time
import tkinter as tk
from tkinter import filedialog, ttk

from PIL import Image, ImageTk

from interfaz_estado import EstadoHuella, Sesion
from referencia_muestra import comparar_referencia
from interfaz_servicios import RAIZ, Servicios, abrir_imagen, evaluar_huella

FONDO = '#F3F7FC'
TITULO = '#16324F'
AZUL = '#2563EB'
GRIS = '#52657A'
COLORES = {
    EstadoHuella.SIN_IMAGEN: ('#EEF3F9', TITULO, 'Sin imagen'),
    EstadoHuella.PENDIENTE: ('#EEF3F9', TITULO, 'Pendiente de evaluación'),
    EstadoHuella.AUTORIZADA: ('#E7F5EC', '#166534', 'AUTORIZADO'),
    EstadoHuella.RECHAZADA: ('#FDECEE', '#991B1B', 'NO AUTORIZADO'),
    EstadoHuella.ERROR: ('#FFF5DE', '#854D0E', 'No se pudo evaluar'),
}


class Aplicacion:
    def __init__(self, raiz, config):
        self.raiz = raiz
        self.config = config
        self.sesion = Sesion()
        self.servicios = None
        self.entradas = []
        self.formato = None
        self.imagen = None
        self.foto = None
        self.normalizada = self.mascara = self.foto_normal = None
        self.base_preparacion = None
        self.captura_preparada = None
        self.receta_preparada = None
        self.receta_entrada = None
        self.referencia_visible = False
        self.fotos_preparacion = {}
        self.ultimo_guardado = ''
        self.cola = Queue()
        self.cancelar = Event()
        self.trabajador = None
        self.dialogo = None
        self.fase = ''
        self.ultimo_error = ''
        self.ultimo_audio = None
        self.accion = 'Todavía no se ejecutaron acciones.'
        self.estado_general = tk.StringVar(value='INICIANDO')
        self.instruccion = tk.StringVar(value='Preparando el sistema…')
        self.aviso = tk.StringVar(value='Cargando los recursos disponibles.')
        self.ultimo_comando = tk.StringVar(value='Último comando de voz: —')
        self.nombre_archivo = tk.StringVar(value='Todavía no hay una imagen seleccionada.')
        self.microfono = tk.StringVar(value='Buscando micrófonos…')
        self.tipo_muestra = tk.StringVar(value='Aleatoria')
        self.ver_mascara = tk.BooleanVar(value=False)
        self.manual_visible = tk.BooleanVar(value=False)
        self.detalles_visibles = tk.BooleanVar(value=False)
        self.preparacion_visible = tk.BooleanVar(value=False)
        self.avanzadas_preparacion = tk.BooleanVar(value=False)
        self.parametros_manuales = tk.BooleanVar(value=False)
        self.actualizando_parametros = False
        self.nombre_base = tk.StringVar(value='Todavía no seleccionaste una base.')
        self.perfil_preparacion = tk.StringVar(value='')
        self.semilla_preparacion = tk.StringVar(value='')
        self.preparacion_mensaje = tk.StringVar(value='Seleccioná una base: se generará una captura automáticamente. La consulta de acceso cambia solo al pulsar Usar esta captura.')
        self._construir()
        self.semilla_preparacion.trace_add('write', lambda *_: self._invalidar_captura())
        self.raiz.protocol('WM_DELETE_WINDOW', lambda: self.confirmar_salida('ventana'))
        self.raiz.after(50, self._recibir)
        token = self.sesion.iniciar('inicio')
        self._enviar(token, 'inicio', self._cargar)

    def _construir(self):
        r = self.raiz
        r.title('Acceso por huella · Inteligencia Artificial I')
        r.configure(bg=FONDO)
        self.escala = max(.8, r.winfo_fpixels('1i') / 96)
        ancho = min(self.px(1080), r.winfo_screenwidth() - self.px(40))
        alto = min(self.px(820), r.winfo_screenheight() - self.px(80))
        r.geometry(f'{ancho}x{alto}')
        r.minsize(min(self.px(620), ancho), min(self.px(510), alto))
        estilo = ttk.Style(r)
        estilo.theme_use('clam')
        estilo.configure('.', font=('Segoe UI', 10))
        estilo.configure('TFrame', background=FONDO)
        estilo.configure('TButton', padding=(14, 9), background='#E7EEF8', foreground=TITULO, borderwidth=0)
        estilo.map('TButton', background=[('disabled', '#E8EDF3'), ('active', '#D7E5FA')],
                   foreground=[('disabled', '#738297')])
        estilo.configure('Principal.TButton', background=AZUL, foreground='white', font=('Segoe UI', 12, 'bold'), padding=(20, 12))
        estilo.map('Principal.TButton', background=[('disabled', '#DCE6F5'), ('active', '#1D4ED8')],
                   foreground=[('disabled', '#64748B')])
        estilo.configure('TCheckbutton', background=FONDO, foreground=TITULO, padding=6)
        estilo.configure('TCombobox', padding=6)
        estilo.configure('Horizontal.TProgressbar', background=AZUL, troughcolor='#E8EFF9',
                         borderwidth=0, thickness=self.px(6))

        encabezado = tk.Frame(r, bg=TITULO, padx=self.px(24), pady=self.px(18))
        encabezado.pack(fill='x')
        self.etiqueta(encabezado, 'Acceso por huella', 22, True, bg=TITULO, fg='white').pack(anchor='w')
        self.etiqueta(encabezado, 'Identidades sintéticas · Inteligencia Artificial I · UNCUYO', 10,
                      bg=TITULO, fg='#CADAF0').pack(anchor='w', pady=(5, 0))
        self.etiqueta(encabezado, variable=self.estado_general, tamano=10, negrita=True,
                      bg=TITULO, fg='#DBEAFE').pack(anchor='w', pady=(10, 0))

        # El área se desplaza cuando el escalado o los desplegables necesitan espacio.
        envoltura = tk.Frame(r, bg=FONDO)
        envoltura.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(envoltura, bg=FONDO, highlightthickness=0)
        barra = ttk.Scrollbar(envoltura, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=barra.set)
        barra.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.contenido = tk.Frame(self.canvas, bg=FONDO, padx=self.px(20), pady=self.px(18))
        self.ventana_canvas = self.canvas.create_window((0, 0), window=self.contenido, anchor='nw')
        self.contenido.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', self._distribuir)
        r.bind_all('<MouseWheel>', self._rueda)
        r.bind_all('<Button-4>', lambda e: self.canvas.yview_scroll(-3, 'units'))
        r.bind_all('<Button-5>', lambda e: self.canvas.yview_scroll(3, 'units'))

        self.preparacion_control = ttk.Checkbutton(self.contenido, text='Opciones avanzadas · elegir base, parámetros y guardar captura',
            variable=self.preparacion_visible, command=self._desplegar)
        self.preparacion_control.pack(anchor='w', pady=(0,8))
        self.preparacion_panel = self.tarjeta(self.contenido)
        self._construir_preparacion()
        self.paneles = tk.Frame(self.contenido, bg=FONDO)
        self.paneles.pack(fill='x')
        self.izquierdo = self.tarjeta(self.paneles)
        self.derecho = self.tarjeta(self.paneles)
        self.etiqueta(self.izquierdo, '01  Huella seleccionada', 13, True).pack(anchor='w')
        self.etiqueta(self.izquierdo, 'Generá una muestra o seleccioná una captura desde archivo.', 10, fg=GRIS).pack(anchor='w', pady=(5, 12))
        fila_generar = tk.Frame(self.izquierdo, bg='white')
        fila_generar.pack(fill='x', pady=(0,12))
        self.tipo_combo = ttk.Combobox(fila_generar, textvariable=self.tipo_muestra,
            values=['Aleatoria','Autorizada','Intrusa'], state='readonly', width=13)
        self.tipo_combo.pack(side='left', padx=(0,8))
        self.automatica_boton = ttk.Button(fila_generar, text='Generar muestra',
            style='Principal.TButton', command=self.generar_muestra_automatica)
        self.automatica_boton.pack(side='left', fill='x', expand=True)
        self.vistas_entrada = tk.Frame(self.izquierdo, bg='white')
        self.vistas_entrada.pack(fill='x')
        for col in (0,1): self.vistas_entrada.columnconfigure(col,weight=1,uniform='entrada')
        self.etiqueta(self.vistas_entrada,'Captura de entrada',10,True).grid(row=0,column=0,sticky='w')
        self.titulo_normal = self.etiqueta(self.vistas_entrada,'Huella normalizada',10,True)
        self.titulo_normal.grid(row=0,column=1,sticky='w')
        self.previa = tk.Canvas(self.vistas_entrada, height=self.px(240), width=self.px(150), bg=FONDO, highlightthickness=0)
        self.previa.grid(row=1,column=0,sticky='ew',padx=(0,5),pady=(6,0))
        self.normal_previa = tk.Canvas(self.vistas_entrada,height=self.px(240),width=self.px(150),bg=FONDO,highlightthickness=0)
        self.normal_previa.grid(row=1,column=1,sticky='ew',padx=(5,0),pady=(6,0))
        self.normal_previa.bind('<Configure>',lambda e:self._dibujar_normal())
        ttk.Checkbutton(self.izquierdo,text='Ver máscara en la vista procesada',
            variable=self.ver_mascara,command=self._dibujar_normal).pack(anchor='w',pady=(6,0))
        self.previa.bind('<Configure>', lambda e: self._dibujar_previa())
        self.seleccionar_boton = ttk.Button(self.izquierdo, text='Seleccionar desde archivo', command=self.seleccionar)
        self.seleccionar_boton.pack(fill='x', pady=(14, 8))
        self.archivo_label = self.etiqueta(self.izquierdo, variable=self.nombre_archivo, tamano=10, fg=GRIS)
        self.archivo_label.pack(fill='x')
        self.archivo_label.bind('<Configure>', lambda e: self.archivo_label.configure(wraplength=max(100, e.width)))

        self.etiqueta(self.derecho, '02  Control y resultado', 13, True).pack(anchor='w')
        self.instruccion_label = self.etiqueta(self.derecho, variable=self.instruccion, tamano=11)
        self.instruccion_label.pack(fill='x', pady=(10, 12))
        self.hablar_boton = ttk.Button(self.derecho, text='Hablar', style='Principal.TButton', command=self.hablar)
        self.hablar_boton.pack(fill='x')
        self.indicador = self.etiqueta(self.derecho, 'Esperá la señal visual para hablar.', 11, True, fg=AZUL)
        self.indicador.pack(fill='x', pady=(10, 6))
        self.progreso = ttk.Progressbar(self.derecho, mode='determinate', value=0)
        self.progreso.pack(fill='x', pady=(0, 12))
        self.etiqueta(self.derecho, variable=self.ultimo_comando, tamano=10, fg=GRIS).pack(anchor='w', pady=(0, 12))
        self.resultado_marco = tk.Frame(self.derecho, bg='#EEF3F9', padx=self.px(16), pady=self.px(16))
        self.resultado_marco.pack(fill='x')
        self.resultado_titulo = self.etiqueta(self.resultado_marco, 'Sin imagen', 20, True, bg='#EEF3F9')
        self.resultado_titulo.pack(fill='x')
        self.resultado_texto = self.etiqueta(self.resultado_marco, 'Generá una muestra o seleccioná una captura para comenzar.', 11, bg='#EEF3F9')
        self.resultado_texto.pack(fill='x', pady=(8, 0))
        self.identidad_marco = tk.Frame(self.derecho, bg='#EAF2FF', padx=self.px(14), pady=self.px(12))
        self.identidad_label = self.etiqueta(self.identidad_marco, '', 14, True, bg='#EAF2FF')
        self.identidad_label.pack(fill='x')
        self.referencia_boton = ttk.Button(self.derecho, text='Mostrar referencia de la muestra',
                                           command=self.mostrar_referencia)
        self.referencia_boton.pack(fill='x', pady=(10, 0))
        self.referencia_marco = tk.Frame(self.derecho, bg='#EEF3F9', padx=self.px(14), pady=self.px(12))
        self.referencia_label = self.etiqueta(self.referencia_marco, '', 11, bg='#EEF3F9')
        self.referencia_label.pack(fill='x')
        self.referencia_label.bind('<Configure>', lambda e: self.referencia_label.configure(wraplength=max(80, e.width)))
        self.origen_label = self.etiqueta(self.derecho, self.accion, 9, fg=GRIS)
        self.origen_label.pack(fill='x', pady=(10, 0))
        for label in (self.instruccion_label, self.resultado_titulo, self.resultado_texto,
                      self.identidad_label, self.origen_label, self.indicador):
            label.bind('<Configure>', lambda e, w=label: w.configure(wraplength=max(80, e.width)))

        pie = tk.Frame(self.contenido, bg=FONDO)
        pie.pack(fill='x', pady=(16, 0))
        self.aviso_label = self.etiqueta(pie, variable=self.aviso, tamano=10, fg='#854D0E', bg=FONDO)
        self.aviso_label.pack(fill='x', pady=(0, 12))
        self.aviso_label.bind('<Configure>', lambda e: self.aviso_label.configure(wraplength=max(100, e.width)))
        self.etiqueta(pie, 'Micrófono', 10, True, bg=FONDO).pack(anchor='w')
        fila_microfono = tk.Frame(pie, bg=FONDO)
        fila_microfono.pack(fill='x', pady=(5, 8))
        self.combo = ttk.Combobox(fila_microfono, textvariable=self.microfono, state='disabled', width=24)
        self.combo.pack(side='left', fill='x', expand=True)
        self.combo.bind('<<ComboboxSelected>>', self.cambiar_microfono)
        self.actualizar_boton = ttk.Button(fila_microfono, text='Actualizar', command=self.actualizar_microfonos)
        self.actualizar_boton.pack(side='left', padx=(8, 0))
        ayuda = self.etiqueta(pie, 'Reconocer evalúa la huella. Identificar revela la identidad autorizada. Salir pide confirmación.\n'
            'Vocabulario limitado a esas tres palabras: otra palabra podría activar cualquiera de los comandos.', 10, fg=GRIS, bg=FONDO)
        ayuda.pack(fill='x', pady=(0, 8))
        ayuda.bind('<Configure>', lambda e: ayuda.configure(wraplength=max(100, e.width)))
        ttk.Checkbutton(pie, text='Controles manuales', variable=self.manual_visible, command=self._desplegar).pack(anchor='w')
        self.manual_panel = tk.Frame(pie, bg=FONDO, pady=self.px(8))
        self.botones_manuales = []
        for columna, comando in enumerate(('reconocer', 'identificar', 'salir')):
            b = ttk.Button(self.manual_panel, text=comando.capitalize(), command=lambda c=comando: self.ejecutar(c, 'manual'))
            b.grid(row=0, column=columna, padx=(0, 8), sticky='ew')
            self.manual_panel.columnconfigure(columna, weight=1)
            self.botones_manuales.append(b)
        self.detalles_control = ttk.Checkbutton(pie, text='Detalles técnicos', variable=self.detalles_visibles, command=self._desplegar)
        self.detalles_control.pack(anchor='w')
        self.tecnico = tk.Text(pie, height=9, wrap='word', bg='#EAF0F8', fg=TITULO, relief='flat',
                               font=('Consolas', 9), padx=12, pady=10, state='disabled')
        self._controles()

    def px(self, numero):
        return round(numero * self.escala)

    def etiqueta(self, padre, texto='', tamano=10, negrita=False, bg='white', fg=TITULO, variable=None):
        return tk.Label(padre, text=texto, textvariable=variable, bg=bg, fg=fg, justify='left', anchor='w',
                        font=('Segoe UI', tamano, 'bold' if negrita else 'normal'))

    def tarjeta(self, padre):
        return tk.Frame(padre, bg='white', padx=self.px(20), pady=self.px(20),
                        highlightthickness=1, highlightbackground='#DFE8F3')

    def _construir_preparacion(self):
        panel = self.preparacion_panel
        self.etiqueta(panel, 'Preparar una captura sintética', 14, True).pack(anchor='w')
        texto = self.etiqueta(panel, 'Seleccioná una base de Anguli en gris, de 275 × 400 píxeles: '
            'se generará una captura con variaciones aleatorias. Generar no autoriza ni reconoce.', 10, fg=GRIS)
        texto.pack(fill='x', pady=(5,10))
        texto.bind('<Configure>', lambda e: texto.configure(wraplength=max(100,e.width)))
        fila = tk.Frame(panel,bg='white')
        fila.pack(fill='x')
        self.base_boton = ttk.Button(fila,text='Seleccionar base',command=self.seleccionar_base)
        self.base_boton.pack(side='left')
        etiqueta = self.etiqueta(fila,variable=self.nombre_base,tamano=10,fg=GRIS)
        etiqueta.pack(side='left',fill='x',expand=True,padx=(12,0))
        etiqueta.bind('<Configure>',lambda e: etiqueta.configure(wraplength=max(80,e.width)))
        vistas = tk.Frame(panel,bg='white')
        vistas.pack(fill='x',pady=(12,10))
        self.vistas_preparacion = {}
        for col,(clave,titulo) in enumerate((('base','Base de Anguli'),('captura','Captura generada · sin normalizar'))):
            vistas.columnconfigure(col,weight=1,uniform='previas')
            self.etiqueta(vistas,titulo,10,True).grid(row=0,column=col,sticky='w',pady=(0,6))
            vista = tk.Canvas(vistas,height=self.px(180),width=self.px(180),bg=FONDO,highlightthickness=0)
            vista.grid(row=1,column=col,sticky='ew',padx=(0,self.px(10) if col==0 else 0))
            vista.bind('<Configure>',lambda e: self._dibujar_preparacion())
            self.vistas_preparacion[clave] = vista
        self.avanzadas_control = ttk.Checkbutton(panel,text='Opciones avanzadas',
            variable=self.avanzadas_preparacion,command=self._mostrar_avanzadas)
        self.avanzadas_control.pack(anchor='w',pady=(0,8))
        self.avanzadas_panel = tk.Frame(panel,bg='white')
        self.parametros_manuales_boton = ttk.Checkbutton(self.avanzadas_panel,
            text='Elegir perfil y semilla manualmente',variable=self.parametros_manuales,
            command=self._cambiar_modo_captura)
        self.parametros_manuales_boton.pack(anchor='w',pady=(0,8))
        opciones = tk.Frame(self.avanzadas_panel,bg='white')
        opciones.pack(fill='x')
        opciones.columnconfigure(0,weight=2)
        opciones.columnconfigure(1,weight=1)
        self.etiqueta(opciones,'Perfil de captura',10,True).grid(row=0,column=0,sticky='w')
        self.etiqueta(opciones,'Semilla de captura',10,True).grid(row=0,column=1,sticky='w')
        self.perfil_combo = ttk.Combobox(opciones,textvariable=self.perfil_preparacion,state='disabled',width=23)
        self.perfil_combo.grid(row=1,column=0,sticky='ew',padx=(0,12),pady=(5,8))
        self.perfil_combo.bind('<<ComboboxSelected>>',lambda e:self._invalidar_captura())
        self.semilla_entrada = ttk.Entry(opciones,textvariable=self.semilla_preparacion,width=15)
        self.semilla_entrada.grid(row=1,column=1,sticky='ew',pady=(5,8))
        nota = self.etiqueta(self.avanzadas_panel,'En automático se muestran los últimos valores elegidos. '
            'Activá la elección manual para repetir una captura. La semilla de captura no es la de Anguli.',9,fg=GRIS)
        nota.pack(fill='x',pady=(0,10))
        nota.bind('<Configure>',lambda e:nota.configure(wraplength=max(100,e.width)))
        self.botones_preparacion = tk.Frame(panel,bg='white')
        botones = self.botones_preparacion
        botones.pack(fill='x')
        self.generar_boton = ttk.Button(botones,text='Generar nueva captura',command=self.generar_captura)
        self.usar_boton = ttk.Button(botones,text='Usar esta captura',command=self.usar_captura)
        self.guardar_boton = ttk.Button(botones,text='Guardar consulta…',command=self.guardar_captura)
        for col,b in enumerate((self.generar_boton,self.usar_boton,self.guardar_boton)):
            botones.columnconfigure(col,weight=1)
            b.grid(row=0,column=col,sticky='ew',padx=(0,8 if col<2 else 0))
        estado = self.etiqueta(panel,variable=self.preparacion_mensaje,tamano=10,fg=GRIS)
        estado.pack(fill='x',pady=(10,0))
        estado.bind('<Configure>',lambda e:estado.configure(wraplength=max(100,e.width)))

    def _configurar_preparador(self):
        from preparar_captura import ETIQUETAS
        p = self.servicios.preparador
        if p is None:
            self.preparacion_mensaje.set('Preparador no disponible. Consultá Detalles técnicos. Podés cargar una captura original directamente.')
            return
        self.perfiles_preparacion = [r['nombre'] for r in p['generador']['perfiles']]
        self.perfil_combo.configure(values=[ETIQUETAS.get(n,n) for n in self.perfiles_preparacion])
        self.perfil_combo.current(self.perfiles_preparacion.index(p['config']['perfil_inicial']))
        self.semilla_preparacion.set(str(p['config']['semilla_inicial']))

    def _dibujar_preparacion(self):
        if self.sesion.cerrada:
            return
        for clave,im in (('base',self.base_preparacion),('captura',self.captura_preparada)):
            c = self.vistas_preparacion[clave]
            c.delete('all')
            w,h = c.winfo_width(),c.winfo_height()
            if im is None:
                c.create_text(w/2,h/2,text='Seleccioná una base' if clave=='base' else 'La captura aparecerá acá',
                    width=max(60,w-20),fill=GRIS,justify='center',font=('Segoe UI',10))
                continue
            mini = im.copy()
            mini.thumbnail((max(1,w-16),max(1,h-16)),Image.Resampling.LANCZOS)
            self.fotos_preparacion[clave] = ImageTk.PhotoImage(mini)
            c.create_image(w/2,h/2,image=self.fotos_preparacion[clave])

    def _invalidar_captura(self):
        if self.actualizando_parametros:
            return
        if self.captura_preparada is not None:
            self.captura_preparada = self.receta_preparada = None
            self.preparacion_mensaje.set('Cambiaste los parámetros. Generá otra captura antes de usarla o guardarla. La consulta de acceso sigue igual.')
            self._dibujar_preparacion()
        self._controles()

    def _mostrar_avanzadas(self):
        self.avanzadas_panel.pack_forget()
        if self.avanzadas_preparacion.get():
            self.avanzadas_panel.pack(fill='x',before=self.botones_preparacion,pady=(0,10))

    def _cambiar_modo_captura(self):
        # Cambiar de modo no genera ni descarta una captura existente. Los campos
        # mantienen sus valores; editarlos sí invalida el borrador como antes.
        self._controles()

    def mostrar_referencia(self):
        if self.sesion.operacion or self.sesion.cerrada or not self.sesion.resultado:
            return
        self.referencia_visible = not self.referencia_visible
        self._actualizar_referencia()

    def _actualizar_referencia(self):
        self.referencia_marco.pack_forget()
        visible = self.referencia_visible and bool(self.sesion.resultado)
        self.referencia_boton.configure(text='Ocultar referencia de la muestra' if visible else 'Mostrar referencia de la muestra')
        if not visible:
            return
        evaluacion = comparar_referencia(self.receta_entrada, self.sesion.resultado)
        bg, fg = {'correcto': ('#E7F5EC', '#166534'),
                  'error': ('#FDECEE', '#991B1B'),
                  'desconocido': ('#EEF3F9', GRIS)}[evaluacion['estado']]
        self.referencia_marco.configure(bg=bg)
        self.referencia_label.configure(text=evaluacion['texto'], bg=bg, fg=fg)
        self.referencia_marco.pack(fill='x', pady=(10, 0), before=self.origen_label)

    def _limpiar_normal(self):
        self.referencia_visible = False
        self._actualizar_referencia()
        self.normalizada = self.mascara = self.foto_normal = None
        self._dibujar_normal()

    def _dibujar_normal(self):
        if self.sesion.cerrada:
            return
        self.normal_previa.delete('all')
        w,h=self.normal_previa.winfo_width(),self.normal_previa.winfo_height()
        mascara=self.ver_mascara.get()
        self.titulo_normal.configure(text='Máscara de la huella' if mascara else 'Huella normalizada')
        imagen=self.mascara if mascara else self.normalizada
        if imagen is None:
            self.normal_previa.create_text(w/2,h/2,text='Se mostrará después\nde Reconocer',
                width=max(50,w-20),justify='center',fill=GRIS,font=('Segoe UI',10))
            return
        mini=imagen.copy()
        mini.thumbnail((max(1,w-12),max(1,h-12)),Image.Resampling.LANCZOS)
        self.foto_normal=ImageTk.PhotoImage(mini)
        self.normal_previa.create_image(w/2,h/2,image=self.foto_normal)

    def generar_muestra_automatica(self):
        if self.sesion.operacion or self.sesion.cerrada or not self.servicios or not self.servicios.preparador:
            return
        from generacion_muestra import generar_muestra
        tipo=self.tipo_muestra.get()
        token=self.sesion.iniciar('generacion_automatica')
        self.estado_general.set('PROCESANDO')
        self.instruccion.set('Generando una muestra sintética…')
        self.aviso.set('Se sortea una base de desarrollo y se genera una captura, sin evaluarla.')
        self._enviar(token,'generacion_automatica',
            lambda:generar_muestra(tipo,self.servicios.preparador,RAIZ))

    def seleccionar_base(self):
        if self.sesion.operacion or self.sesion.cerrada or not self.servicios or not self.servicios.preparador:
            return
        ruta = filedialog.askopenfilename(parent=self.raiz,title='Seleccioná una base de Anguli',
            initialdir=RAIZ/'datos/bases',filetypes=[('Imágenes PNG','*.png'),('Todos los archivos','*.*')])
        if not ruta:
            return
        from preparar_captura import abrir_base
        self.base_preparacion = self.captura_preparada = self.receta_preparada = None
        self.nombre_base.set(Path(ruta).name)
        self._dibujar_preparacion()
        token = self.sesion.iniciar('base_preparacion')
        self.estado_general.set('PROCESANDO')
        self.preparacion_mensaje.set('Abriendo base…')
        self._enviar(token,'base_preparacion',lambda:abrir_base(ruta))

    def generar_captura(self):
        if self.sesion.operacion or self.sesion.cerrada or self.base_preparacion is None:
            return
        from preparar_captura import preparar_captura, validar_semilla, elegir_parametros_aleatorios
        try:
            manual = self.parametros_manuales.get()
            if manual:
                semilla = validar_semilla(self.semilla_preparacion.get())
                indice = self.perfil_combo.current()
                if indice<0:
                    raise ValueError('Elegí un perfil de captura.')
                perfil = self.perfiles_preparacion[indice]
            else:
                anterior = self.receta_preparada['semilla_captura'] if self.receta_preparada else None
                perfil,semilla = elegir_parametros_aleatorios(self.servicios.preparador,anterior)
                self.actualizando_parametros = True
                try:
                    self.perfil_combo.current(self.perfiles_preparacion.index(perfil))
                    self.semilla_preparacion.set(str(semilla))
                finally:
                    self.actualizando_parametros = False
        except ValueError as e:
            self.preparacion_mensaje.set(str(e))
            return
        base = self.base_preparacion.copy()
        self.captura_preparada = self.receta_preparada = None
        self._dibujar_preparacion()
        token = self.sesion.iniciar('preparar_captura')
        self.estado_general.set('PROCESANDO')
        self.preparacion_mensaje.set('Generando una captura en memoria…')
        def generar():
            imagen,receta = preparar_captura(base,perfil,semilla,self.servicios.preparador)
            receta['eleccion_parametros'] = 'manual' if manual else 'automatica'
            return imagen,receta
        self._enviar(token,'preparar_captura',generar)

    def usar_captura(self):
        if self.sesion.operacion or self.sesion.cerrada or self.captura_preparada is None:
            return
        r = self.receta_preparada
        # Identificador virtual: no se crea un archivo al usar la captura.
        nombre = f"captura_{r['perfil']}_{r['semilla_captura']}.png"
        self.sesion.seleccionar(nombre)
        self.imagen = self.captura_preparada.copy()
        self._limpiar_normal()
        self.receta_entrada = deepcopy(r)
        self.nombre_archivo.set('Captura sintética preparada')
        self.ultimo_error = ''
        self._dibujar_previa()
        self._actualizar()
        self.aviso.set('Captura seleccionada y pendiente de evaluación. Pulsá Hablar y decí Reconocer, o usá el control manual.')
        self.preparacion_mensaje.set('La captura pasó al panel de acceso. Se normalizará al reconocer. No se incorporó al entrenamiento.')
        self.preparacion_visible.set(False)
        self._desplegar()
        self.canvas.yview_moveto(0)

    def guardar_captura(self):
        if self.sesion.operacion or self.sesion.cerrada or self.captura_preparada is None:
            return
        padre = filedialog.askdirectory(parent=self.raiz,title='Elegí dónde crear una carpeta nueva para la consulta',
            initialdir=RAIZ/'consultas' if (RAIZ/'consultas').exists() else RAIZ,mustexist=True)
        if not padre:
            return
        from preparar_captura import guardar_consulta
        padre = Path(padre).resolve()
        if padre==RAIZ:
            padre = RAIZ/'consultas'
        nombre = 'consulta_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        imagen,base,receta = self.captura_preparada.copy(),self.base_preparacion.copy(),deepcopy(self.receta_preparada)
        token = self.sesion.iniciar('guardar_captura')
        self.estado_general.set('PROCESANDO')
        self.preparacion_mensaje.set('Guardando base, captura y receta…')
        self._enviar(token,'guardar_captura',lambda:guardar_consulta(imagen,base,receta,padre/nombre))

    def _distribuir(self, evento):
        self.canvas.itemconfigure(self.ventana_canvas, width=evento.width)
        apilado = evento.width < self.px(820)
        if getattr(self, '_apilado', None) != apilado:
            self._apilado = apilado
            self.izquierdo.grid_forget()
            self.derecho.grid_forget()
            self.paneles.columnconfigure(0, weight=1, uniform='' if apilado else 'panel')
            self.paneles.columnconfigure(1, weight=0 if apilado else 1, uniform='' if apilado else 'panel')
            self.izquierdo.grid(row=0, column=0, sticky='nsew', padx=(0, 0 if apilado else self.px(14)))
            self.derecho.grid(row=1 if apilado else 0, column=0 if apilado else 1, sticky='nsew',
                              pady=(self.px(14) if apilado else 0, 0))
        self.raiz.after_idle(self._dibujar_previa)
        self.raiz.after_idle(self._dibujar_normal)

    def _rueda(self, evento):
        if self.dialogo is None and not isinstance(evento.widget, (tk.Text, ttk.Combobox)):
            self.canvas.yview_scroll(-int(evento.delta / 120), 'units')

    def _dibujar_previa(self):
        if self.sesion.cerrada:
            return
        self.previa.delete('all')
        w, h = self.previa.winfo_width(), self.previa.winfo_height()
        if self.imagen is None:
            self.previa.create_text(w/2, h/2, text='La huella aparecerá acá\ncuando selecciones una imagen.',
                                    width=max(50, w-30), justify='center', fill=GRIS, font=('Segoe UI', 11))
            return
        # Solo se reduce esta copia. La inferencia recibe la imagen completa.
        miniatura = self.imagen.copy()
        miniatura.thumbnail((max(1, w-self.px(24)), max(1, h-self.px(24))), Image.Resampling.LANCZOS)
        self.foto = ImageTk.PhotoImage(miniatura)
        self.previa.create_image(w/2, h/2, image=self.foto)

    def _desplegar(self):
        self.preparacion_panel.pack_forget()
        if self.preparacion_visible.get():
            self.preparacion_panel.pack(fill='x', before=self.paneles, pady=(0,self.px(14)))
            self.raiz.after_idle(self._dibujar_preparacion)
        self.manual_panel.pack_forget()
        self.tecnico.pack_forget()
        if self.manual_visible.get():
            self.manual_panel.pack(fill='x', before=self.detalles_control)
        if self.detalles_visibles.get():
            self._detalles()
            self.tecnico.pack(fill='x', pady=(4, 0))

    def _enviar(self, token, tipo, funcion):
        def trabajo():
            try:
                valor = funcion()
                self.cola.put((token, tipo, valor, None))
            except Exception as e:
                self.cola.put((token, tipo, None, e))
        self._controles()
        self.trabajador = Thread(target=trabajo, name='inferencia-ia1', daemon=True)
        self.trabajador.start()

    def _cargar(self):
        servicios = Servicios.cargar(self.config)
        entradas, formato, problema = [], None, ''
        try:
            entradas = servicios.microfonos()
            predeterminado = servicios.sd.default.device[0]
            indice = predeterminado if predeterminado in dict(entradas) else entradas[0][0]
            formato = servicios.formato(indice)
        except Exception as e:
            problema = str(e)
        return servicios, entradas, formato, problema

    def _recibir(self):
        if self.sesion.cerrada:
            return
        if self.dialogo is None:
            while True:
                try:
                    token, tipo, valor, error = self.cola.get_nowait()
                except Empty:
                    break
                if not self.sesion.vigente(token):
                    continue
                if tipo == 'fase':
                    self.fase = valor
                    self.estado_general.set('GRABANDO' if valor == 'grabando' else 'PROCESANDO')
                    self.indicador.configure(text=('GRABANDO · Decí el comando.' if valor == 'grabando' else
                                                  'Captura terminada · Procesando audio…'))
                    continue
                if tipo == 'huella':
                    if error is None:
                        self.normalizada = valor.pop('_vista_normalizada',None)
                        self.mascara = valor.pop('_vista_mascara',None)
                        self._dibujar_normal()
                    self.sesion.evaluada(token, valor, error)
                else:
                    self.sesion.terminar(token)
                self.progreso.stop()
                self.fase = ''
                if error is not None:
                    self._error_operacion(tipo, error)
                elif tipo == 'inicio':
                    self.servicios, self.entradas, self.formato, problema = valor
                    self._configurar_preparador()
                    self._mostrar_microfonos(problema)
                    self._disponibilidad()
                elif tipo == 'generacion_automatica':
                    self.base_preparacion,self.captura_preparada,self.receta_preparada=valor
                    self.nombre_base.set('Base sorteada · referencia guardada en la receta')
                    self._dibujar_preparacion()
                    self.usar_captura()
                elif tipo == 'imagen':
                    self.imagen = valor
                    self._dibujar_previa()
                    self.aviso.set('Imagen lista. Pulsá Hablar o abrí los controles manuales.')
                elif tipo == 'base_preparacion':
                    self.base_preparacion = valor
                    self._dibujar_preparacion()
                    self.generar_captura()
                elif tipo == 'preparar_captura':
                    self.captura_preparada, self.receta_preparada = valor
                    self.preparacion_mensaje.set('Captura generada, todavía sin evaluar. Pulsá Usar esta captura para enviarla al reconocimiento.')
                    self._dibujar_preparacion()
                elif tipo == 'guardar_captura':
                    self.ultimo_guardado = str(valor)
                    self.preparacion_mensaje.set('Consulta guardada en ' + str(valor) + '. Incluye base.png, captura.png y receta.json.')
                elif tipo == 'microfonos':
                    self.entradas = valor
                    self.formato = None
                    self._mostrar_microfonos('Elegí una entrada para habilitar la captura.')
                elif tipo == 'formato':
                    self.formato = valor
                    self._mostrar_microfonos('')
                    self.aviso.set('Micrófono listo. Esperá el cartel GRABANDO para hablar.')
                elif tipo == 'voz':
                    self.ultimo_audio = valor
                    comando = valor.get('prediccion')
                    self.ultimo_comando.set('Último comando de voz: ' + (comando.capitalize() if comando else 'sin comando'))
                    if comando:
                        self._controles()
                        self.ejecutar(comando, 'voz')
                    else:
                        self.aviso.set('No se detectó voz útil. Intentá nuevamente. Revisá el motivo en Detalles técnicos.')
                elif tipo == 'huella':
                    self.aviso.set('Evaluación completada.' + (' Hay avisos: consultá Detalles técnicos.' if valor['avisos'] else ''))
                self._actualizar()
                if self.dialogo is not None:
                    break
        self.raiz.after(50, self._recibir)

    def _disponibilidad(self):
        if self.servicios.huellas is None:
            self.aviso.set('El módulo de huellas no está disponible. Revisá los archivos indicados en Detalles técnicos y reiniciá.')
        elif self.servicios.voz is None:
            self.aviso.set('Voz no disponible: faltan recursos o hay una incompatibilidad. Podés usar los controles manuales.')
        elif self.formato is None:
            self.aviso.set('No hay un micrófono listo. Podés cambiarlo, actualizar la lista o usar los controles manuales.')
        else:
            self.aviso.set('Sistema listo. Seleccioná una huella para comenzar.')

    def _mostrar_microfonos(self, problema):
        self.combo.configure(values=[texto for _, texto in self.entradas])
        if self.formato is not None:
            indice = next(i for i, (n, _) in enumerate(self.entradas) if n == self.formato[0])
            self.combo.current(indice)
        elif self.entradas:
            self.microfono.set('Seleccioná un micrófono…')
        else:
            self.microfono.set('Sin micrófono disponible')
        if problema:
            self.ultimo_error = 'Micrófono: ' + problema
            self.aviso.set(problema + ' Los controles manuales siguen disponibles.')

    def _error_operacion(self, tipo, error):
        self.ultimo_error = f'{tipo}: {type(error).__name__}: {error}'
        if tipo == 'generacion_automatica':
            self.aviso.set('No se pudo generar la muestra: ' + str(error) + ' La consulta anterior se conserva.')
            return
        if tipo in ('base_preparacion','preparar_captura','guardar_captura'):
            self.preparacion_mensaje.set('No se pudo completar la preparación: ' + str(error))
            if tipo == 'base_preparacion':
                self.base_preparacion = None
                self._dibujar_preparacion()
            self.aviso.set('La preparación no cambió la huella seleccionada para acceso. Revisá el mensaje del preparador.')
            return
        if tipo == 'imagen':
            self.imagen = None
            self.sesion.estado = EstadoHuella.ERROR
            self._dibujar_previa()
            self.aviso.set('No se pudo abrir la imagen. Elegí otro archivo compatible.')
        elif tipo == 'huella':
            self.aviso.set('No se pudo evaluar la imagen: ' + str(error))
        elif tipo in ('voz', 'formato', 'microfonos'):
            if tipo != 'voz':
                self.formato = None
            else:
                self.ultimo_audio = None
                self.ultimo_comando.set('Último comando de voz: captura o procesamiento fallido')
            self.aviso.set('No se pudo completar el audio: ' + str(error) + ' Podés usar los controles manuales.')
        else:
            self.aviso.set('No se pudo iniciar el sistema. Revisá Detalles técnicos y reiniciá.')

    def _actualizar(self):
        estado = self.sesion.estado
        bg, fg, texto = COLORES[estado]
        self.resultado_marco.configure(bg=bg)
        self.resultado_titulo.configure(bg=bg, fg=fg, text=texto)
        mensajes = {
            EstadoHuella.SIN_IMAGEN: 'Generá una muestra o seleccioná una captura para comenzar.',
            EstadoHuella.PENDIENTE: 'Esta imagen todavía no tiene una autorización vigente.',
            EstadoHuella.AUTORIZADA: 'Huella autorizada. Podés decir Identificar para conocer la identidad.',
            EstadoHuella.RECHAZADA: 'La huella no corresponde a una identidad autorizada.',
            EstadoHuella.ERROR: 'Hubo un problema de lectura o procesamiento. Podés volver a intentarlo.',
        }
        voz_lista = bool(self.servicios and self.servicios.voz and self.formato)
        if estado == EstadoHuella.AUTORIZADA and not voz_lista:
            mensajes[estado] = 'Huella autorizada. En Controles manuales podés elegir Identificar.'
        self.resultado_texto.configure(bg=bg, fg=fg, text=mensajes[estado])
        self.identidad_marco.pack_forget()
        if self.sesion.identidad_visible:
            self.identidad_label.configure(text='Identidad sintética · ' + self.sesion.identidad_visible)
            self.identidad_marco.pack(fill='x', pady=(10, 0), before=self.origen_label)
        self.origen_label.configure(text=self.accion)
        if not self.sesion.operacion:
            completa = self.servicios and self.servicios.huellas and self.servicios.voz and self.formato
            problema = self.servicios is None or self.servicios.huellas is None
            self.estado_general.set('CON UN PROBLEMA' if problema else 'LISTO' if completa else 'LISTO · FUNCIONES LIMITADAS')
            self.progreso.configure(mode='determinate', value=0)
            self.indicador.configure(text='Esperá la señal visual para hablar.' if voz_lista else 'Control manual disponible.' if not problema else 'Revisá Detalles técnicos.')
            if estado == EstadoHuella.SIN_IMAGEN:
                self.instruccion.set('Generá una muestra o seleccioná una captura para comenzar.')
            elif estado == EstadoHuella.AUTORIZADA:
                self.instruccion.set('Pulsá Hablar y decí Identificar después de la cuenta regresiva.')
            else:
                self.instruccion.set('Pulsá Hablar y, después de la cuenta regresiva, decí Reconocer.')
            if self.servicios and not self.servicios.huellas:
                self.instruccion.set('No se pudo cargar el módulo de huellas. Revisá Detalles técnicos.')
            elif self.servicios and (not self.servicios.voz or not self.formato):
                self.instruccion.set('Usá el panel Controles manuales para continuar con la huella.')
        self._actualizar_referencia()
        self._controles()
        self._detalles()

    def _controles(self):
        libre = not self.sesion.operacion and not self.sesion.cerrada
        self.referencia_boton.configure(state='normal' if libre and self.sesion.resultado else 'disabled')
        huellas = bool(self.servicios and self.servicios.huellas)
        voz = bool(self.servicios and self.servicios.voz and self.formato)
        self.seleccionar_boton.configure(state='normal' if libre else 'disabled')
        self.hablar_boton.configure(state='normal' if libre and voz else 'disabled')
        for b in self.botones_manuales[:2]:
            b.configure(state='normal' if libre and huellas else 'disabled')
        self.botones_manuales[2].configure(state='normal' if not self.sesion.cerrada else 'disabled')
        self.combo.configure(state='readonly' if libre and self.entradas else 'disabled')
        self.actualizar_boton.configure(state='normal' if libre and self.servicios and self.servicios.sd else 'disabled')
        preparador = bool(self.servicios and self.servicios.preparador)
        manual = self.parametros_manuales.get()
        self.automatica_boton.configure(state='normal' if libre and preparador else 'disabled')
        self.tipo_combo.configure(state='readonly' if libre and preparador else 'disabled')
        self.base_boton.configure(state='normal' if libre and preparador else 'disabled')
        self.parametros_manuales_boton.configure(state='normal' if libre and preparador else 'disabled')
        self.perfil_combo.configure(state='readonly' if libre and preparador and manual else 'disabled')
        self.semilla_entrada.configure(state='normal' if libre and preparador and manual else 'disabled')
        self.generar_boton.configure(state='normal' if libre and preparador and self.base_preparacion is not None else 'disabled')
        for boton in (self.usar_boton,self.guardar_boton):
            boton.configure(state='normal' if libre and self.captura_preparada is not None else 'disabled')

    def _detalles(self):
        lineas = [self.accion]
        if self.servicios:
            if self.servicios.huellas:
                h = self.servicios.huellas
                lineas.append(f"Huellas: {h['identificador']} · {len(h['modelo']['indices'])}/{len(h['modelo']['nombres'])} columnas · sin PCA")
            if self.servicios.voz:
                v = self.servicios.voz
                lineas.append(f"Voz: {v['carpeta'].name} · {len(v['modelo']['nombres'])} columnas · K-NN {v['resumen']['parametros']} · sin PCA")
            lineas.extend(f'Recurso {k}: {v}' for k, v in self.servicios.errores.items())
        if self.formato:
            lineas.append(f'Captura: {self.formato[1]} Hz · {self.formato[2]} canal(es) · PCM16')
        if self.sesion.resultado:
            r = self.sesion.resultado
            lineas.append(f"Distancia euclidiana: {r['distancia']:.9g} · umbral: {r['umbral']:.9g}. No son probabilidades.")
            lineas.append('Avisos de huella: ' + (', '.join(r['avisos']) or 'ninguno'))
        if self.ultimo_audio:
            a = self.ultimo_audio
            lineas.append('Comando predicho: ' + str(a.get('prediccion')))
            lineas.append('Avisos de audio: ' + (', '.join(a.get('avisos', [])) or 'ninguno'))
            if not a.get('prediccion'):
                lineas.append('Motivo: ' + str(a.get('extraccion') or a.get('detalle')))
        if self.ultimo_error:
            lineas.append('Último problema: ' + self.ultimo_error)
        if self.receta_entrada:
            r = self.receta_entrada
            lineas.append(f"Entrada: captura sintética preparada · perfil {r['perfil']} · semilla de captura {r['semilla_captura']} · sin normalización previa")
            lineas.append('SHA-256 de píxeles de base: ' + r['base']['sha256_pixeles'])
        if self.ultimo_guardado:
            lineas.append('Última consulta guardada: ' + self.ultimo_guardado)
        self.tecnico.configure(state='normal')
        self.tecnico.delete('1.0', 'end')
        self.tecnico.insert('1.0', '\n'.join(lineas))
        self.tecnico.configure(state='disabled')

    def seleccionar(self):
        if self.sesion.operacion or self.sesion.cerrada:
            return
        ruta = filedialog.askopenfilename(parent=self.raiz, title='Seleccioná una huella sintética original',
            initialdir=RAIZ / 'datos/originales', filetypes=[('Imágenes', '*.png *.jpg *.jpeg *.bmp *.tif *.tiff'), ('Todos los archivos', '*.*')])
        if not ruta:
            return
        self.sesion.seleccionar(ruta)
        self.receta_entrada = None
        self.nombre_archivo.set(Path(ruta).name)
        self.imagen = self.foto = None
        self._limpiar_normal()
        self.ultimo_error = ''
        self._dibujar_previa()
        self._actualizar()
        token = self.sesion.iniciar('imagen')
        self.estado_general.set('PROCESANDO')
        self.instruccion.set('Abriendo imagen…')
        self._enviar(token, 'imagen', lambda: abrir_imagen(ruta))

    def ejecutar(self, comando, origen):
        if self.sesion.cerrada:
            return
        if comando == 'salir':
            self.confirmar_salida(origen)
            return
        self.accion = f'Acción solicitada: {comando.capitalize()} · origen: {origen}'
        try:
            if comando == 'reconocer':
                if not self.servicios or not self.servicios.huellas:
                    raise ValueError('El módulo de huellas no está disponible. Revisá Detalles técnicos.')
                if self.imagen is None and self.sesion.imagen is not None:
                    raise ValueError('No se pudo abrir la imagen. Seleccioná otro archivo.')
                token = self.sesion.reconocer()
                self._limpiar_normal()
                imagen = self.imagen  # Instantánea de la entrada, nunca la miniatura.
                self.ultimo_error = ''
                self._actualizar()
                self.estado_general.set('PROCESANDO')
                self.instruccion.set('Evaluando huella…')
                self.indicador.configure(text='Evaluando huella…')
                self.progreso.configure(mode='indeterminate')
                self.progreso.start(15)
                self._enviar(token, 'huella', lambda: evaluar_huella(imagen, self.servicios.huellas, incluir_vistas=True))
            elif comando == 'identificar':
                self.sesion.identificar()
                self.aviso.set('Identificación completada para la huella autorizada actual.')
                self._actualizar()
            else:
                raise ValueError('Comando fuera del vocabulario admitido.')
        except ValueError as e:
            self.aviso.set(str(e))
            self._actualizar()

    def hablar(self):
        if self.sesion.operacion or not self.servicios or not self.servicios.voz or not self.formato:
            return
        token = self.sesion.iniciar('voz')
        self.ultimo_audio = None
        self.ultimo_error = ''
        self.ultimo_comando.set('Último comando de voz: esperando una nueva captura…')
        self._controles()
        self.aviso.set('Preparáte. Hablá solo cuando aparezca GRABANDO.')
        self._cuenta(token, self.servicios.cfg_captura['cuenta_regresiva_s'])

    def _cuenta(self, token, restante):
        if not self.sesion.vigente(token):
            return
        if self.dialogo is not None:
            self.raiz.after(100, lambda: self._cuenta(token, restante))
            return
        if restante:
            self.estado_general.set('PREPARANDO CAPTURA')
            self.indicador.configure(text=f'Empezamos en {restante}…')
            self.raiz.after(1000, lambda: self._cuenta(token, restante - 1))
        else:
            self.indicador.configure(text='Abriendo micrófono…')
            self.progreso.configure(mode='indeterminate')
            self.progreso.start(15)
            formato = self.formato
            self._enviar(token, 'voz', lambda: self.servicios.escuchar(formato,
                lambda: self.cola.put((token, 'fase', 'grabando', None)),
                lambda: self.cola.put((token, 'fase', 'procesando', None)), self.cancelar))

    def actualizar_microfonos(self):
        if self.sesion.operacion or not self.servicios or not self.servicios.sd:
            return
        token = self.sesion.iniciar('microfonos')
        self.estado_general.set('PROCESANDO')
        self._enviar(token, 'microfonos', self.servicios.microfonos)

    def cambiar_microfono(self, evento=None):
        if self.sesion.operacion:
            return
        opcion = self.combo.current()
        if opcion < 0:
            return
        indice = self.entradas[opcion][0]
        self.formato = None
        self.ultimo_error = ''
        token = self.sesion.iniciar('formato')
        self.estado_general.set('PROCESANDO')
        self._enviar(token, 'formato', lambda: self.servicios.formato(indice))

    def confirmar_salida(self, origen):
        if self.dialogo is not None or self.sesion.cerrada:
            return
        mensajes = {
            'voz': 'Se interpretó el comando Salir. ¿Querés cerrar la aplicación?',
            'manual': 'Pulsaste Salir. ¿Querés cerrar la aplicación?',
            'ventana': '¿Querés cerrar la aplicación?',
        }
        d = self.dialogo = tk.Toplevel(self.raiz)
        d.title('Confirmar salida')
        d.transient(self.raiz)
        d.resizable(False, False)
        d.configure(bg='white', padx=self.px(24), pady=self.px(22))
        self.etiqueta(d, 'Cerrar aplicación', 15, True).pack(anchor='w')
        mensaje = self.etiqueta(d, mensajes[origen], 11)
        mensaje.configure(wraplength=self.px(410))
        mensaje.pack(anchor='w', pady=(12, 20))
        botones = tk.Frame(d, bg='white')
        botones.pack(fill='x')
        def descartar():
            d.grab_release()
            d.destroy()
            self.dialogo = None
            self.hablar_boton.focus_set()
        def cerrar():
            d.grab_release()
            d.destroy()
            self.dialogo = None
            self.sesion.cerrar()
            self.cancelar.set()
            self.progreso.stop()
            self.estado_general.set('CERRANDO')
            self.instruccion.set('Cerrando la aplicación…')
            self._controles()
            self._esperar_cierre(time.monotonic() + 5)
        ttk.Button(botones, text='Cerrar', style='Principal.TButton', command=cerrar).pack(side='right')
        cancelar = ttk.Button(botones, text='Cancelar', command=descartar)
        cancelar.pack(side='right', padx=(0, 10))
        d.protocol('WM_DELETE_WINDOW', descartar)
        d.bind('<Escape>', lambda e: descartar())
        d.update_idletasks()
        x = self.raiz.winfo_rootx() + max(0, (self.raiz.winfo_width() - d.winfo_reqwidth()) // 2)
        y = self.raiz.winfo_rooty() + max(0, (self.raiz.winfo_height() - d.winfo_reqheight()) // 2)
        d.geometry(f'+{x}+{y}')
        d.grab_set()
        cancelar.focus_set()

    def _esperar_cierre(self, limite):
        # capturar_pcm observa el Event y libera PortAudio en su finally.
        # Un cálculo no cancelable puede terminar; sus respuestas ya son inválidas.
        # El hilo daemon evita retener el proceso si un controlador nativo se cuelga.
        if not self.trabajador or not self.trabajador.is_alive() or time.monotonic() >= limite:
            self._destruir()
        else:
            self.raiz.after(50, lambda: self._esperar_cierre(limite))

    def _destruir(self):
        self.cancelar.set()
        if not self.sesion.cerrada:
            self.sesion.cerrar()
        self.progreso.stop()
        # Evita callbacks Tcl pendientes incluso al crear otra ventana después.
        for tarea in self.raiz.tk.splitlist(self.raiz.tk.call('after', 'info')):
            self.raiz.after_cancel(tarea)
        self.imagen = self.foto = None
        self.normalizada = self.mascara = self.foto_normal = None
        self.base_preparacion = self.captura_preparada = self.receta_preparada = None
        self.fotos_preparacion.clear()
        self.raiz.destroy()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, default=RAIZ / 'config/aplicacion.json')
    args = p.parse_args()
    os.environ.setdefault('MPLBACKEND', 'Agg')  # No se abren ventanas de gráficos.
    if os.name == 'nt':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    raiz = tk.Tk()
    Aplicacion(raiz, args.config if args.config.is_absolute() else RAIZ / args.config)
    raiz.mainloop()


if __name__ == '__main__':
    main()
