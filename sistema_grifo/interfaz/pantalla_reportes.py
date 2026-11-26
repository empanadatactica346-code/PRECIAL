"""Pantalla de reportes: diario/semanal/mensual, gráficos y exportación a Excel."""
import os
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from configuracion import DIRECTORIO_SALIDA, PRODUCTOS
from interfaz.componentes import (COLORES_PRODUCTO, Grafico, Tabla, explicacion,
                                  selector_productos, titulo)
from utilidades.helpers import formato_fecha

PERIODOS = {"Diario": "D", "Semanal": "W", "Mensual": "M"}


class PantallaReportes(ctk.CTkScrollableFrame):
    """Reporte de ventas, compras y margen real vs margen esperado."""

    def __init__(self, padre, app):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        titulo(self, "Reportes").pack(anchor="w")
        explicacion(self, "Margen REAL = (venta − costo FIFO de los galones vendidos) / costo FIFO. "
                          "Margen ESPERADO = margen calculado con el costo de la última cisterna, que es lo "
                          "que muchos administradores creen estar ganando. La diferencia muestra el efecto "
                          "de vender combustible comprado a otro precio.").pack(anchor="w", pady=(2, 8))
        ctrl = ctk.CTkFrame(self)
        ctrl.pack(fill="x", pady=4)
        self.periodo = ctk.CTkSegmentedButton(ctrl, values=list(PERIODOS), command=lambda _: self.actualizar())
        self.periodo.set("Diario")
        self.periodo.pack(side="left", padx=10, pady=6)
        self.producto = selector_productos(ctrl, lambda _: self.actualizar(), incluir_todos=True)
        self.producto.pack(side="left", padx=10)
        ctk.CTkButton(ctrl, text="Exportar a Excel", command=self.exportar).pack(side="right", padx=10)
        self.tabla = Tabla(self, alto=10)
        self.tabla.pack(fill="x", pady=6)
        self.g_margen = Grafico(self, alto=2.8)
        self.g_margen.pack(fill="x", pady=4)
        self.g_stock = Grafico(self, alto=2.8)
        self.g_stock.pack(fill="x", pady=4)
        self.g_costo = Grafico(self, alto=2.8)
        self.g_costo.pack(fill="x", pady=4)

    def actualizar(self):
        s = self.app.sistema
        prod = self.producto.get()
        prod = None if prod == "Todos" else prod
        df = s.reporte(PERIODOS[self.periodo.get()], prod)
        if df.empty:
            self.tabla.cargar(["Sin datos"], [])
            for g in (self.g_margen, self.g_stock, self.g_costo):
                g.mensaje("Sin datos. Importe ventas y compras primero.")
            return
        pct = lambda v: "—" if v != v else f"{v*100:.2f}%"
        filas = [(formato_fecha(r.fecha), f"{r.volumen:,.0f}", f"{r.importe:,.0f}", f"{r.utilidad:,.0f}",
                  f"{r.compras_gal:,.0f}", pct(r.margen_real_pct), pct(r.margen_esperado_pct),
                  "—" if r.margen_real_pct != r.margen_real_pct else
                  f"{(r.margen_real_pct - r.margen_esperado_pct)*100:+.2f} pp")
                 for r in df.iloc[::-1].itertuples()]
        self.tabla.cargar(["Desde", "Galones vendidos", "Ventas S/", "Utilidad S/", "Galones comprados",
                           "Margen real", "Margen esperado", "Diferencia"], filas,
                          [100, 120, 110, 110, 130, 100, 120, 100])

        self.g_margen.limpiar()
        ax = self.g_margen.figura.add_subplot(111)
        ax.plot(df["fecha"], df["margen_real_pct"] * 100, label="Margen real (FIFO)", color="#E8780C")
        ax.plot(df["fecha"], df["margen_esperado_pct"] * 100, label="Margen esperado (últ. cisterna)",
                color="#8A5A00", ls="--")
        ax.set_title("Evolución del margen (%)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
        self.g_margen.dibujar()

        h = s.historial_diario
        productos = [prod] if prod else PRODUCTOS
        for graf, col, tit in ((self.g_stock, "stock", "Evolución del stock (galones)"),
                               (self.g_costo, "costo_promedio", "Evolución del costo FIFO promedio (S//gal)")):
            graf.limpiar()
            ax = graf.figura.add_subplot(111)
            for p in productos:
                hp = h[h["producto"] == p]
                if col == "costo_promedio":
                    hp = hp[hp[col] > 0]
                ax.plot(hp["fecha"], hp[col], label=p, color=COLORES_PRODUCTO[p])
            ax.set_title(tit)
            ax.grid(alpha=0.3)
            ax.legend(fontsize=8)
            graf.dibujar()

    def exportar(self):
        nombre = f"reporte_grifo_{datetime.now():%Y%m%d_%H%M}.xlsx"
        ruta = filedialog.asksaveasfilename(initialdir=DIRECTORIO_SALIDA, initialfile=nombre,
                                            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if not ruta:
            return
        try:
            self.app.sistema.exportar_excel(ruta)
        except OSError as e:
            messagebox.showerror("Error", f"No se pudo guardar (¿el archivo está abierto en Excel?).\n{e}")
            return
        messagebox.showinfo("Exportado", f"Reporte guardado en:\n{os.path.abspath(ruta)}")
