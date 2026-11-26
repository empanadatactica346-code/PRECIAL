"""
Componentes reutilizables de la interfaz: tablas, gráficos, textos
explicativos con negritas y tarjetas de resumen.
"""
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from configuracion import PRODUCTOS

FUENTE = "Segoe UI"
COLOR_TITULO = "#8A3B00"   # marrón anaranjado
COLOR_ALERTA = "#B42318"   # rojo (para alertas)
COLOR_OK = "#067647"
COLORES_PRODUCTO = {"DB5": "#E8780C", "GR": "#D4A000", "GP": "#A63A00"}
COLOR_PRINCIPAL = "#E8780C"   # naranja
COLOR_DORADO = "#F2B705"      # dorado
COLOR_MENU = "#2B1D0E"        # marrón oscuro
COLOR_SECUNDARIO = "#7A5418"  # botones secundarios


def titulo(padre, texto, tam=20):
    """Etiqueta de título de pantalla."""
    return ctk.CTkLabel(padre, text=texto, font=(FUENTE, tam, "bold"), text_color=COLOR_TITULO)


def explicacion(padre, texto, ancho=900):
    """Texto de ayuda en gris, en lenguaje simple."""
    return ctk.CTkLabel(padre, text=texto, font=(FUENTE, 12), text_color="#555555",
                        wraplength=ancho, justify="left", anchor="w")


def selector_productos(padre, comando, incluir_todos=False):
    """Botones segmentados para elegir el producto."""
    valores = (["Todos"] if incluir_todos else []) + PRODUCTOS
    sel = ctk.CTkSegmentedButton(padre, values=valores, command=comando)
    sel.set(valores[0])
    return sel


class Tabla(ctk.CTkFrame):
    """Tabla (ttk.Treeview) con barra de desplazamiento."""

    def __init__(self, padre, alto=8, **kw):
        super().__init__(padre, **kw)
        estilo = ttk.Style()
        estilo.configure("Grifo.Treeview", font=(FUENTE, 10), rowheight=22)
        estilo.theme_use("clam")
        estilo.configure("Grifo.Treeview.Heading", font=(FUENTE, 10, "bold"),
                         background=COLOR_DORADO, foreground="#2B1D0E")
        estilo.map("Grifo.Treeview", background=[("selected", COLOR_PRINCIPAL)])
        self.arbol = ttk.Treeview(self, show="headings", height=alto, style="Grifo.Treeview")
        barra = ttk.Scrollbar(self, orient="vertical", command=self.arbol.yview)
        self.arbol.configure(yscrollcommand=barra.set)
        self.arbol.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.arbol.tag_configure("alerta", foreground=COLOR_ALERTA)
        self.arbol.tag_configure("destacado", background="#FFF1C2")

    def cargar(self, columnas, filas, anchos=None, etiquetas=None):
        """Reemplaza el contenido. etiquetas: lista paralela de tags por fila."""
        self.arbol.delete(*self.arbol.get_children())
        self.arbol["columns"] = columnas
        for i, c in enumerate(columnas):
            self.arbol.heading(c, text=c)
            self.arbol.column(c, width=(anchos[i] if anchos else 110), anchor="center")
        for i, fila in enumerate(filas):
            tags = (etiquetas[i],) if etiquetas and etiquetas[i] else ()
            self.arbol.insert("", "end", values=list(fila), tags=tags)


class Grafico(ctk.CTkFrame):
    """Contenedor de un gráfico matplotlib embebido."""

    def __init__(self, padre, ancho=9, alto=3.6, **kw):
        super().__init__(padre, **kw)
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg   # import diferido: arranque rápido
        from matplotlib.figure import Figure
        self.figura = Figure(figsize=(ancho, alto), dpi=90)
        self.lienzo = FigureCanvasTkAgg(self.figura, master=self)
        self.lienzo.get_tk_widget().pack(fill="both", expand=True)

    def limpiar(self):
        self.figura.clear()

    def dibujar(self):
        self.figura.tight_layout()
        self.lienzo.draw()

    def mensaje(self, texto):
        """Muestra un texto en lugar del gráfico (por ejemplo, sin datos)."""
        self.limpiar()
        ax = self.figura.add_subplot(111)
        ax.axis("off")
        ax.text(0.5, 0.5, texto, ha="center", va="center", fontsize=11, color="#777777")
        self.dibujar()


class TextoRico(ctk.CTkTextbox):
    """Cuadro de texto de solo lectura que admite negritas y colores."""

    def __init__(self, padre, alto=180, **kw):
        super().__init__(padre, height=alto, font=(FUENTE, 13), wrap="word", **kw)
        t = self._textbox
        t.tag_configure("b", font=(FUENTE, 13, "bold"))
        t.tag_configure("titulo", font=(FUENTE, 14, "bold"), foreground=COLOR_TITULO)
        t.tag_configure("alerta", foreground=COLOR_ALERTA, font=(FUENTE, 12, "bold"))
        t.tag_configure("ok", foreground=COLOR_OK, font=(FUENTE, 13, "bold"))
        t.tag_configure("gris", foreground="#666666", font=(FUENTE, 11))
        self.configure(state="disabled")

    def escribir(self, segmentos):
        """
        segmentos: lista de (texto, tag) o textos simples. Tag puede ser
        None, 'b', 'titulo', 'alerta', 'ok' o 'gris'.
        """
        self.configure(state="normal")
        self._textbox.delete("1.0", tk.END)
        for s in segmentos:
            texto, tag = (s, None) if isinstance(s, str) else s
            self._textbox.insert(tk.END, texto, (tag,) if tag else ())
        self.configure(state="disabled")


class Tarjeta(ctk.CTkFrame):
    """Pequeña tarjeta con un título y varias líneas de valores."""

    def __init__(self, padre, encabezado, color="#E8780C", **kw):
        super().__init__(padre, corner_radius=10, border_width=2, border_color=color, **kw)
        ctk.CTkLabel(self, text=encabezado, font=(FUENTE, 15, "bold"),
                     text_color=color).pack(anchor="w", padx=12, pady=(10, 4))
        self.cuerpo = ctk.CTkLabel(self, text="", font=(FUENTE, 12), justify="left", anchor="w")
        self.cuerpo.pack(anchor="w", padx=12, pady=(0, 6), fill="x")
        self.barra = ctk.CTkProgressBar(self, height=12)
        self.barra.pack(fill="x", padx=12, pady=(0, 12))
        self.barra.set(0)

    def actualizar(self, texto, fraccion=None):
        self.cuerpo.configure(text=texto)
        if fraccion is not None:
            self.barra.set(max(0.0, min(1.0, fraccion)))
            self.barra.configure(progress_color=COLOR_ALERTA if fraccion < 0.2 else COLOR_DORADO)


def campo(padre, etiqueta, fila, columna=0, valor="", ancho=160):
    """Crea una etiqueta + entrada en una grilla y devuelve la entrada."""
    ctk.CTkLabel(padre, text=etiqueta, font=(FUENTE, 12)).grid(
        row=fila, column=columna, sticky="w", padx=(10, 6), pady=4)
    entrada = ctk.CTkEntry(padre, width=ancho)
    entrada.grid(row=fila, column=columna + 1, sticky="w", padx=(0, 14), pady=4)
    if valor != "":
        entrada.insert(0, str(valor))
    return entrada


def poner_valor(entrada, valor):
    entrada.delete(0, tk.END)
    entrada.insert(0, str(valor))


def exportar_hojas_articulo(app, hojas, nombre_archivo):
    """Exporta solo algunas hojas del artículo a exportaciones/<nombre_archivo>."""
    import os
    from tkinter import messagebox

    from exportador import tablas_articulo
    from exportador.reporte_completo import DIRECTORIO_EXPORTACIONES
    if app.sistema.datos["ventas"].empty:
        messagebox.showwarning("Sin datos", "Importe primero los archivos de datos.")
        return
    try:
        app.configure(cursor="watch")
        app.update()
        tablas = tablas_articulo.construir_tablas(app.sistema)
        ruta = tablas_articulo.exportar_tablas(
            tablas, os.path.join(DIRECTORIO_EXPORTACIONES, nombre_archivo), hojas=hojas)
    except OSError as e:
        messagebox.showerror("Error", f"No se pudo guardar (¿archivo abierto en Excel?).\n{e}")
        return
    finally:
        app.configure(cursor="")
    messagebox.showinfo("Exportado", f"Tabla guardada en:\n{ruta}")


# ----------------------------------------------------- vista del administrador
SEMAFORO = {
    "verde": {"fondo": "#E3F4E1", "borde": "#2E7D32", "icono": "🟢"},
    "amarillo": {"fondo": "#FFF4C2", "borde": "#C99A00", "icono": "🟡"},
    "rojo": {"fondo": "#FBE0DC", "borde": "#B42318", "icono": "🔴"},
    "gris": {"fondo": "#EEEEEE", "borde": "#888888", "icono": "⚪"},
}


class TarjetaDecision(ctk.CTkFrame):
    """Recuadro grande de color con la respuesta directa para el administrador."""

    def __init__(self, padre, **kw):
        super().__init__(padre, corner_radius=12, border_width=3, **kw)
        self.encabezado = ctk.CTkLabel(self, text="", font=(FUENTE, 17, "bold"), anchor="w")
        self.encabezado.pack(anchor="w", padx=16, pady=(12, 4))
        self.lineas = []
        self.ancho_texto = 380
        self.bind("<Configure>", self._ajustar_ancho)

    def _ajustar_ancho(self, evento):
        """Ajusta el salto de línea al ancho real de la tarjeta (evita textos cortados)."""
        # evento.width está en píxeles reales; CTk vuelve a escalar wraplength según el DPI
        ancho = max((evento.width - 44) / self._get_widget_scaling(), 150)
        if abs(ancho - self.ancho_texto) > 4:
            self.ancho_texto = ancho
            for l in self.lineas:
                l.configure(wraplength=ancho)

    def mostrar(self, color, titulo_txt, lineas):
        """
        lineas: lista de (texto, estilo) con estilo en
        'normal' | 'grande' | 'medio' | 'chico' | 'alerta'.
        """
        c = SEMAFORO[color]
        self.configure(fg_color=c["fondo"], border_color=c["borde"])
        self.encabezado.configure(text=f"●  {titulo_txt}", text_color=c["borde"])
        for l in self.lineas:
            l.destroy()
        self.lineas = []
        estilos = {"normal": ((FUENTE, 13), "#2B1D0E"), "grande": ((FUENTE, 22, "bold"), "#2B1D0E"),
                   "medio": ((FUENTE, 15, "bold"), "#2B1D0E"), "chico": ((FUENTE, 11), "#555555"),
                   "alerta": ((FUENTE, 12, "bold"), COLOR_ALERTA)}
        for texto, estilo in lineas:
            fuente, color_txt = estilos[estilo]
            l = ctk.CTkLabel(self, text=texto, font=fuente, text_color=color_txt, anchor="w",
                             justify="left", wraplength=self.ancho_texto)
            l.pack(anchor="w", padx=16, pady=1)
            self.lineas.append(l)
        margen = ctk.CTkLabel(self, text="", height=6)
        margen.pack()
        self.lineas.append(margen)


class SeccionPlegable(ctk.CTkFrame):
    """Botón 'Ver ... ▼' que muestra u oculta un contenedor (oculto por defecto)."""

    def __init__(self, padre, texto, **kw):
        super().__init__(padre, fg_color="transparent", **kw)
        self.texto = texto
        self.boton = ctk.CTkButton(self, text=f"{texto} ▼", fg_color=COLOR_SECUNDARIO,
                                   hover_color="#5C3A10", command=self.alternar)
        self.boton.pack(anchor="w", pady=(10, 4))
        self.contenido = ctk.CTkFrame(self, fg_color="transparent")
        self.abierto = False
        self.al_abrir = None

    def alternar(self):
        self.abierto = not self.abierto
        if self.abierto:
            self.contenido.pack(fill="x")
            self.boton.configure(text=f"Ocultar {self.texto[4:] if self.texto.startswith('Ver ') else self.texto} ▲")
            if self.al_abrir:
                self.al_abrir()
        else:
            self.contenido.pack_forget()
            self.boton.configure(text=f"{self.texto} ▼")
