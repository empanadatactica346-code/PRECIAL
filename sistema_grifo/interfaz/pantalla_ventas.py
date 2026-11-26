"""Pantalla de registro de ventas (descuenta FIFO automáticamente)."""
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from configuracion import DIRECTORIO_ENTRADA, PRODUCTOS
from datos.validador import ErrorValidacion
from interfaz.componentes import Tabla, campo, explicacion, poner_valor, titulo
from utilidades.helpers import formato_fecha, formato_moneda


class PantallaVentas(ctk.CTkFrame):
    """Formulario de venta + tabla de últimas ventas con su costo FIFO."""

    def __init__(self, padre, app):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        titulo(self, "Registro de ventas").pack(anchor="w", pady=(0, 4))
        explicacion(self, "Cada venta se descuenta del tanque empezando por el combustible más "
                          "antiguo (FIFO). Así sabemos el costo REAL de los galones vendidos y el "
                          "margen que realmente se ganó.").pack(anchor="w", pady=(0, 10))

        form = ctk.CTkFrame(self)
        form.pack(fill="x", pady=4)
        ctk.CTkLabel(form, text="Producto").grid(row=0, column=0, sticky="w", padx=10, pady=4)
        self.producto = ctk.CTkComboBox(form, values=PRODUCTOS, width=160, command=self._sugerir_precio)
        self.producto.grid(row=0, column=1, sticky="w", pady=4)
        self.volumen = campo(form, "Volumen (galones)", 0, 2)
        self.precio = campo(form, "Precio de venta (S//gal)", 1, 0)
        self.fecha = campo(form, "Fecha y hora (AAAA-MM-DD HH:MM)", 1, 2)
        botones = ctk.CTkFrame(form, fg_color="transparent")
        botones.grid(row=2, column=0, columnspan=4, sticky="w", padx=10, pady=8)
        ctk.CTkButton(botones, text="Registrar venta", command=self.registrar).pack(side="left", padx=(0, 8))
        ctk.CTkButton(botones, text="Importar ventas (CSV/Excel)", fg_color="#7A5418",
                      command=self.importar).pack(side="left")

        self.resultado = ctk.CTkLabel(self, text="", font=("Segoe UI", 13), justify="left",
                                      anchor="w", wraplength=900)
        self.resultado.pack(anchor="w", pady=6)
        self.info = explicacion(self, "")
        self.info.pack(anchor="w")
        self.tabla = Tabla(self, alto=14)
        self.tabla.pack(fill="both", expand=True, pady=6)

    def _sugerir_precio(self, _=None):
        p, _f = self.app.sistema.precio_mercado(self.producto.get())
        poner_valor(self.precio, f"{p:.2f}")

    def registrar(self):
        try:
            r = self.app.sistema.registrar_venta(self.fecha.get(), self.producto.get(),
                                                 self.volumen.get(), self.precio.get())
        except ErrorValidacion as e:
            messagebox.showerror("Venta rechazada", str(e))
            return
        if r:
            color = "#067647" if r["margen"] > 0 else "#b54708"
            self.resultado.configure(text_color=color, text=(
                f"✔ Venta registrada: {r['volumen']:,.2f} gal de {r['producto']}. "
                f"Costo FIFO de esos galones: {formato_moneda(r['costo_fifo'], 4)}/gal. "
                f"Margen: {formato_moneda(r['margen'], 4)}/gal → utilidad {formato_moneda(r['utilidad'])}."
                + ("  ⚠ ¡Se vendió por debajo del costo!" if r["margen"] <= 0 else "")))
        self.app.refrescar_todo()

    def importar(self):
        rutas = filedialog.askopenfilenames(
            title="Seleccione archivo(s) de ventas", initialdir=DIRECTORIO_ENTRADA,
            filetypes=[("Excel o CSV", "*.xlsx *.xls *.csv")])
        if not rutas:
            return
        reemplazar = messagebox.askyesno(
            "Importar ventas", "¿Reemplazar las ventas existentes?\n\nSí = reemplazar\nNo = agregar al final")
        self.app.ejecutar_importacion(rutas, "ventas", reemplazar)

    def actualizar(self):
        s = self.app.sistema
        poner_valor(self.fecha, datetime.now().strftime("%Y-%m-%d %H:%M"))
        if not self.precio.get():
            self._sugerir_precio()
        v = s.ventas_procesadas.tail(300).iloc[::-1]
        filas = [(formato_fecha(r.fecha, True), r.producto, f"{r.volumen:,.2f}", f"{r.precio:.2f}",
                  f"{r.costo_fifo:.4f}", f"{r.margen:.4f}", f"{r.margen / r.costo_fifo * 100:.1f}%"
                  if r.costo_fifo else "—", f"{r.utilidad:,.2f}") for r in v.itertuples()]
        etiquetas = ["alerta" if r.margen <= 0 else None for r in v.itertuples()]
        self.tabla.cargar(["Fecha", "Producto", "Galones", "Precio S/", "Costo FIFO S/",
                           "Margen S//gal", "Margen %", "Utilidad S/"], filas,
                          [140, 80, 90, 90, 110, 110, 90, 100], etiquetas)
        txt = (f"Se muestran las últimas {len(filas)} de {len(s.ventas_procesadas):,} ventas procesadas. "
               "Las filas en naranja se vendieron sin margen.")
        if len(s.ventas_rechazadas):
            txt += f"  ⚠ {len(s.ventas_rechazadas):,} ventas fueron rechazadas por falta de stock."
        self.info.configure(text=txt)
