"""Pantalla de inventario: capas FIFO por producto."""
import customtkinter as ctk

from interfaz.componentes import (COLORES_PRODUCTO, Grafico, Tabla, TextoRico, explicacion,
                                  selector_productos, titulo)
from utilidades.helpers import formato_fecha, formato_galones, formato_moneda, formato_pct


class PantallaInventario(ctk.CTkFrame):
    """Stock, valor, capas FIFO y nivel del tanque."""

    def __init__(self, padre, app):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        titulo(self, "Inventario (capas FIFO)").pack(anchor="w", pady=(0, 4))
        explicacion(self, "El tanque se ve como 'capas' de combustible comprado a distintos costos. "
                          "La capa de arriba de la tabla es la más antigua y es la que se vende primero."
                    ).pack(anchor="w", pady=(0, 8))
        self.selector = selector_productos(self, lambda _: self.actualizar())
        self.selector.pack(anchor="w", pady=4)
        self.texto = TextoRico(self, alto=150)
        self.texto.pack(fill="x", pady=4)
        self.barra = ctk.CTkProgressBar(self, height=18)
        self.barra.pack(fill="x", pady=4)
        self.tabla = Tabla(self, alto=6)
        self.tabla.pack(fill="x", pady=4)
        self.grafico = Grafico(self, alto=2.8)
        self.grafico.pack(fill="both", expand=True, pady=4)

    def actualizar(self):
        s = self.app.sistema
        p = self.selector.get()
        t = s.tanques[p]
        pct = t.porcentaje_lleno()
        self.barra.set(pct)
        self.barra.configure(progress_color="#b54708" if pct < s.config["alerta_stock_pct"]
                             else COLORES_PRODUCTO[p])
        seg = [(f"{s.config['nombres_productos'][p]} ({p})\n", "titulo"),
               "Stock total: ", (formato_galones(t.stock_actual()), "b"),
               f"  ({formato_pct(pct)} de la capacidad de {formato_galones(t.capacidad_maxima, 0)})\n",
               "Valor del inventario: ", (formato_moneda(t.valor_inventario()), "b"), "\n",
               "Costo promedio ponderado actual: ", (formato_moneda(t.costo_promedio_actual(), 4) + "/gal", "b"),
               "  ← este es el costo que usa el Modelo 2 para calcular el precio óptimo.\n"]
        if t.capas:
            seg += ["Costo de la capa más antigua (se vende ahora): ",
                    (formato_moneda(t.costo_capa_mas_antigua(), 4), "b"),
                    "   |   Costo de la cisterna más reciente: ",
                    (formato_moneda(t.costo_capa_mas_reciente(), 4), "b"), "\n"]
            if len(t.capas) > 1:
                dif = t.costo_capa_mas_reciente() - t.costo_capa_mas_antigua()
                seg.append(("La última cisterna costó " + ("MÁS" if dif > 0 else "MENOS") +
                            f" que la capa actual ({formato_moneda(dif, 4, True)}/gal). Cuando se termine "
                            "la capa antigua, el costo real de venta cambiará.\n", "gris"))
        else:
            seg.append(("El tanque está vacío.", "alerta"))
        if pct < s.config["alerta_stock_pct"]:
            seg.append(("⚠ Stock bajo: programe una cisterna.", "alerta"))
        self.texto.escribir(seg)

        filas = [(i + 1, formato_fecha(c["fecha"], True), c.get("origen", ""),
                  f"{c['volumen_original']:,.1f}", f"{c['volumen_restante']:,.1f}",
                  f"{c['costo_galon']:.4f}", f"{c['volumen_restante'] * c['costo_galon']:,.2f}")
                 for i, c in enumerate(t.detalle_capas())]
        self.tabla.cargar(["Capa", "Fecha llegada", "Origen", "Vol. original", "Vol. restante",
                           "Costo S//gal", "Valor S/"], filas, [50, 130, 120, 100, 100, 100, 110])

        h = s.historial_diario
        h = h[h["producto"] == p]
        if h.empty:
            self.grafico.mensaje("Sin historial de stock todavía.")
            return
        self.grafico.limpiar()
        ax = self.grafico.figura.add_subplot(111)
        ax.fill_between(h["fecha"], h["stock"], color=COLORES_PRODUCTO[p], alpha=0.3)
        ax.plot(h["fecha"], h["stock"], color=COLORES_PRODUCTO[p])
        ax.axhline(t.capacidad_maxima, color="gray", ls="--", lw=1, label="Capacidad")
        ax.set_title(f"Evolución del stock de {p} (galones al cierre de cada día)")
        ax.legend(loc="upper left")
        ax.grid(alpha=0.3)
        self.grafico.dibujar()
