"""Pantalla de configuración: parámetros editables del sistema."""
from tkinter import messagebox

import customtkinter as ctk

from configuracion import CONFIGURACION, PRODUCTOS
from interfaz.componentes import campo, explicacion, poner_valor, titulo


class PantallaConfiguracion(ctk.CTkScrollableFrame):
    """Permite editar capacidades, márgenes, κ, α, β y horizonte."""

    def __init__(self, padre, app):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        titulo(self, "Configuración").pack(anchor="w")
        explicacion(self, "Los cambios se guardan en datos_salida/configuracion.csv. Al guardar, el "
                          "inventario FIFO se recalcula con las nuevas capacidades.").pack(anchor="w", pady=(2, 8))
        f = ctk.CTkFrame(self)
        f.pack(fill="x", pady=4)
        self.e = {}
        fila = 0
        for p in PRODUCTOS:
            self.e[f"cap_{p}"] = campo(f, f"Capacidad tanque {p} (gal)", fila, 0, ancho=100)
            self.e[f"k_{p}"] = campo(f, f"Elasticidad κ {p}", fila, 2, ancho=100)
            fila += 1
        for clave, etiqueta in (("margen_minimo", "Margen mínimo (%)"), ("margen_maximo", "Margen máximo (%)"),
                                ("margen_politica_fija", "Margen fijo política A (%)"),
                                ("alerta_stock_pct", "Alerta de stock bajo (%)"),
                                ("croston_alfa_inicial", "α inicial Croston"),
                                ("croston_beta_inicial", "β inicial Croston"),
                                ("horizonte_dias", "Horizonte de planificación (días)")):
            self.e[clave] = campo(f, etiqueta, fila // 2 + 3, (fila % 2) * 2, ancho=100)
            fila += 1
        b = ctk.CTkFrame(self, fg_color="transparent")
        b.pack(anchor="w", pady=10)
        ctk.CTkButton(b, text="Guardar configuración", command=self.guardar).pack(side="left", padx=(0, 8))
        ctk.CTkButton(b, text="Restaurar valores por defecto", fg_color="#7A5418",
                      command=self.restaurar).pack(side="left")

    PORCENTAJES = ("margen_minimo", "margen_maximo", "margen_politica_fija", "alerta_stock_pct")

    def _mostrar(self, cfg):
        for p in PRODUCTOS:
            poner_valor(self.e[f"cap_{p}"], cfg["capacidad_tanque"][p])
            poner_valor(self.e[f"k_{p}"], cfg["kappa"][p])
        for c in self.PORCENTAJES:
            poner_valor(self.e[c], round(cfg[c] * 100, 2))
        for c in ("croston_alfa_inicial", "croston_beta_inicial", "horizonte_dias"):
            poner_valor(self.e[c], cfg[c])

    def actualizar(self):
        self._mostrar(self.app.sistema.config)

    def guardar(self):
        cfg = dict(self.app.sistema.config)
        try:
            cfg["capacidad_tanque"] = {p: float(self.e[f"cap_{p}"].get()) for p in PRODUCTOS}
            cfg["kappa"] = {p: float(self.e[f"k_{p}"].get()) for p in PRODUCTOS}
            for c in self.PORCENTAJES:
                cfg[c] = float(self.e[c].get()) / 100
            cfg["croston_alfa_inicial"] = float(self.e["croston_alfa_inicial"].get())
            cfg["croston_beta_inicial"] = float(self.e["croston_beta_inicial"].get())
            cfg["horizonte_dias"] = float(self.e["horizonte_dias"].get())
        except ValueError:
            messagebox.showerror("Error", "Todos los valores deben ser números.")
            return
        if any(v <= 0 for v in cfg["capacidad_tanque"].values()) or any(v <= 0 for v in cfg["kappa"].values()):
            messagebox.showerror("Error", "Capacidades y κ deben ser mayores que cero.")
            return
        if not (0 <= cfg["margen_minimo"] < cfg["margen_maximo"]):
            messagebox.showerror("Error", "El margen máximo debe ser mayor que el mínimo (y este ≥ 0).")
            return
        if not all(0.05 <= cfg[c] <= 0.30 for c in ("croston_alfa_inicial", "croston_beta_inicial")):
            messagebox.showerror("Error", "α y β deben estar entre 0.05 y 0.30.")
            return
        if cfg["horizonte_dias"] <= 0:
            messagebox.showerror("Error", "El horizonte debe ser mayor que cero.")
            return
        self.app.sistema.guardar_configuracion(cfg)
        self.app.refrescar_todo()
        msg = self.app.sistema.texto_rechazos()
        messagebox.showinfo("Configuración", "Configuración guardada." + (f"\n\n{msg}" if msg else ""))

    def restaurar(self):
        self._mostrar(CONFIGURACION)
