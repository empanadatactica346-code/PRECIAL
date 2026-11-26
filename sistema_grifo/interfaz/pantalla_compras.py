"""Pantalla de registro de compras (llegada de cisternas)."""
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from configuracion import DIRECTORIO_ENTRADA, PRODUCTOS
from datos.validador import ErrorValidacion
from interfaz.componentes import Tabla, campo, explicacion, poner_valor, titulo
from utilidades.helpers import formato_fecha, formato_galones


class PantallaCompras(ctk.CTkFrame):
    """Formulario de cisterna + tabla de compras con su estado."""

    def __init__(self, padre, app):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        titulo(self, "Registro de compras (cisternas)").pack(anchor="w", pady=(0, 4))
        explicacion(self, "Cada cisterna que llega crea una nueva 'capa' en el tanque con su propio "
                          "costo. El sistema no permite recibir una cisterna si no cabe en el tanque."
                    ).pack(anchor="w", pady=(0, 10))

        form = ctk.CTkFrame(self)
        form.pack(fill="x", pady=4)
        ctk.CTkLabel(form, text="Producto").grid(row=0, column=0, sticky="w", padx=10, pady=4)
        self.producto = ctk.CTkComboBox(form, values=PRODUCTOS, width=160, command=lambda _: self._espacio())
        self.producto.grid(row=0, column=1, sticky="w", pady=4)
        self.volumen = campo(form, "Volumen (galones)", 0, 2)
        self.costo = campo(form, "Costo por galón (S/)", 1, 0)
        self.fecha = campo(form, "Fecha de llegada (AAAA-MM-DD HH:MM)", 1, 2)
        self.proveedor = campo(form, "Proveedor (opcional)", 2, 0)
        self.espacio = ctk.CTkLabel(form, text="", text_color="#555555")
        self.espacio.grid(row=2, column=2, columnspan=2, sticky="w", padx=10)
        botones = ctk.CTkFrame(form, fg_color="transparent")
        botones.grid(row=3, column=0, columnspan=4, sticky="w", padx=10, pady=8)
        ctk.CTkButton(botones, text="Registrar cisterna", command=self.registrar).pack(side="left", padx=(0, 8))
        ctk.CTkButton(botones, text="Importar compras (CSV/Excel)", fg_color="#7A5418",
                      command=self.importar).pack(side="left")

        self.info = explicacion(self, "")
        self.info.pack(anchor="w", pady=6)
        self.tabla = Tabla(self, alto=14)
        self.tabla.pack(fill="both", expand=True, pady=6)

    def _espacio(self):
        t = self.app.sistema.tanques[self.producto.get()]
        libre = t.capacidad_maxima - t.stock_actual()
        self.espacio.configure(text=f"Espacio libre en el tanque: {formato_galones(libre)} "
                                    f"(capacidad {formato_galones(t.capacidad_maxima, 0)})")

    def registrar(self):
        try:
            self.app.sistema.registrar_compra(self.fecha.get(), self.producto.get(), self.volumen.get(),
                                              self.costo.get(), self.proveedor.get().strip())
        except ErrorValidacion as e:
            messagebox.showerror("Cisterna rechazada", str(e))
            return
        messagebox.showinfo("Cisterna registrada", "La cisterna se agregó como nueva capa FIFO.")
        self.app.refrescar_todo()

    def importar(self):
        rutas = filedialog.askopenfilenames(
            title="Seleccione archivo(s) de compras", initialdir=DIRECTORIO_ENTRADA,
            filetypes=[("Excel o CSV", "*.xlsx *.xls *.csv")])
        if not rutas:
            return
        reemplazar = messagebox.askyesno(
            "Importar compras", "¿Reemplazar las compras existentes?\n\nSí = reemplazar\nNo = agregar")
        self.app.ejecutar_importacion(rutas, "compras", reemplazar)

    def actualizar(self):
        s = self.app.sistema
        poner_valor(self.fecha, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self._espacio()
        c = s.datos["compras"].iloc[::-1].head(300)
        filas, etiquetas = [], []
        for i, r in c.iterrows():
            estado = s.estado_compras.get(i, "")
            filas.append((formato_fecha(r["fecha_pedido"]), formato_fecha(r["fecha_llegada"], True),
                          r["producto"], f"{r['volumen']:,.0f}", f"{r['costo_galon']:.4f}",
                          f"{r['volumen'] * r['costo_galon']:,.2f}", r["proveedor"], estado))
            etiquetas.append("alerta" if estado.startswith("Rechazada") else None)
        self.tabla.cargar(["Pedido", "Llegada", "Producto", "Galones", "Costo S//gal", "Importe S/",
                           "Proveedor", "Estado"], filas, [90, 130, 70, 80, 100, 110, 120, 260], etiquetas)
        self.info.configure(text=f"{len(s.datos['compras'])} cisternas registradas (más recientes primero).")
