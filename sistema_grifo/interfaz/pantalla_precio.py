"""Pantalla del Modelo 2: precio óptimo de venta."""
from tkinter import messagebox

import customtkinter as ctk

from configuracion import PRODUCTOS
from utilidades.decisiones import tarjeta_precio
from interfaz.componentes import (SeccionPlegable, TarjetaDecision, exportar_hojas_articulo, COLORES_PRODUCTO, Grafico, Tabla, TextoRico, campo, explicacion,
                                  poner_valor, selector_productos, titulo)
from modelos import modelo_precio_optimo
from utilidades.helpers import (formato_fecha, formato_galones, formato_moneda, formato_pct,
                                redondeo_peruano)


class PantallaPrecio(ctk.CTkScrollableFrame):
    """Decisión de precio por producto (tarjetas) y análisis completo plegable."""

    def __init__(self, padre, app):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        titulo(self, "Modelo 2 — ¿A qué precio conviene vender?").pack(anchor="w")
        explicacion(self, "Cada recuadro le da el precio que deja la mayor utilidad con su costo real (FIFO), "
                          "sin salirse del margen mínimo y máximo y sin vender más combustible del que tiene. "
                          "También le dice hasta cuándo mantenerlo: hasta el próximo cambio de precio que se "
                          "espera del proveedor (Modelo 1).").pack(anchor="w", pady=(2, 8))
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x")
        self.tarjetas = {}
        for i, prod in enumerate(PRODUCTOS):
            t = TarjetaDecision(fila)
            t.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)
            fila.grid_columnconfigure(i, weight=1, uniform="t")
            self.tarjetas[prod] = t
        explicacion(self, "⚠️ Las utilidades son estimaciones: dependen de qué tan sensibles son sus clientes "
                          "al precio (κ). Véalo en el análisis completo.").pack(anchor="w")

        self.plegable = SeccionPlegable(self, "Ver análisis completo")
        self.plegable.pack(fill="x")
        self.plegable.al_abrir = self.actualizar_detalles
        d = self.plegable.contenido
        ctrl = ctk.CTkFrame(d)
        ctrl.pack(fill="x", pady=4)
        self.selector = selector_productos(ctrl, lambda _: self._cargar_parametros())
        self.selector.grid(row=0, column=0, columnspan=2, padx=10, pady=6, sticky="w")
        self.kappa = campo(ctrl, "κ elasticidad (15–25)", 1, 0, ancho=80)
        self.horizonte = campo(ctrl, "Horizonte (días)", 1, 2, ancho=80)
        self.mmin = campo(ctrl, "Margen mínimo (%)", 2, 0, ancho=80)
        self.mmax = campo(ctrl, "Margen máximo (%)", 2, 2, ancho=80)
        self.usar_m1 = ctk.CTkCheckBox(ctrl, text="Usar como horizonte los días hasta el próximo "
                                                  "cambio de precio (Modelo 1)")
        self.usar_m1.grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=4)
        ctk.CTkButton(ctrl, text="Recalcular", command=self.actualizar_detalles).grid(row=3, column=3, padx=10)
        ctk.CTkButton(ctrl, text="Exportar tabla del Modelo 2", command=lambda: exportar_hojas_articulo(
            app, ["Tabla4_Comparacion_Politicas"], "TABLA_MODELO2.xlsx")).grid(row=3, column=4, padx=10)

        self.texto = TextoRico(d, alto=250)
        self.texto.pack(fill="x", pady=6)
        self.grafico = Grafico(d, alto=3.4)
        self.grafico.pack(fill="x", pady=6)
        for atributo, tit, ayuda, alto in (
            ("t_politicas", "Comparación de políticas",
             "Política A = lo que hace un grifo típico (costo + margen fijo). Política B = precio del modelo.", 3),
            ("t_sens", "Tabla de sensibilidad",
             "¿Qué pasa con la utilidad si el precio se mueve respecto al recomendado? En rojo: "
             "precios fuera de los límites permitidos.", 5),
            ("t_kappa", "Escenarios de elasticidad (κ)",
             "Como κ es una suposición, se muestra el precio óptimo para varios valores. Si todos los "
             "escenarios recomiendan precios parecidos, la recomendación es robusta.", 5)):
            ctk.CTkLabel(d, text=tit, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(10, 0))
            explicacion(d, ayuda).pack(anchor="w")
            t = Tabla(d, alto=alto)
            t.pack(fill="x", pady=4)
            setattr(self, atributo, t)
        self._cargar_parametros(recalcular=False)

    def _cargar_parametros(self, recalcular=True):
        cfg = self.app.sistema.config
        p = self.selector.get()
        poner_valor(self.kappa, cfg["kappa"][p])
        poner_valor(self.horizonte, cfg["horizonte_dias"])
        poner_valor(self.mmin, round(cfg["margen_minimo"] * 100, 2))
        poner_valor(self.mmax, round(cfg["margen_maximo"] * 100, 2))
        if recalcular:
            self.actualizar_detalles()

    def _parametros(self):
        k, h = float(self.kappa.get()), float(self.horizonte.get())
        mmin, mmax = float(self.mmin.get()) / 100, float(self.mmax.get()) / 100
        if k <= 0 or h <= 0 or mmin < 0 or mmax <= mmin:
            raise ValueError("Revise: κ y horizonte > 0, y margen máximo > margen mínimo ≥ 0.")
        return k, h, mmin, mmax

    def actualizar(self):
        s = self.app.sistema
        for prod, t in self.tarjetas.items():
            t.mostrar(*tarjeta_precio(s, prod, s.precio_optimo(prod), s.pronostico(prod)))
        if self.plegable.abierto:
            self.actualizar_detalles()

    def actualizar_detalles(self):
        try:
            k, h, mmin, mmax = self._parametros()
        except ValueError as e:
            messagebox.showerror("Parámetros inválidos", str(e) if "Revise" in str(e) else
                                 "Todos los parámetros deben ser números.")
            return
        p = self.selector.get()
        r = self.app.sistema.precio_optimo(p, k, mmin, mmax, h, bool(self.usar_m1.get()))
        self._texto(p, r)
        if not r["ok"]:
            self.grafico.mensaje("Sin datos suficientes para el cálculo.")
            for t in (self.t_politicas, self.t_sens, self.t_kappa):
                t.cargar([], [])
            return
        self._grafico(p, r)
        self._tablas(r)

    def _texto(self, p, r):
        seg = [(f"{self.app.sistema.config['nombres_productos'][p]} ({p})\n", "titulo")]
        if not r["ok"]:
            seg += [(f"⚠ {a}\n", "alerta") for a in r["advertencias"]]
            self.texto.escribir(seg)
            return
        pol = r["politicas"]
        seg += ["Costo FIFO actual: ", (formato_moneda(r["costo"], 4) + "/gal", "b"), "\n",
                "Precio óptimo recomendado: ", (formato_moneda(r["precio_recomendado"]) + "/gal", "ok"),
                f" (margen: {formato_pct(r['margen_pct'])})\n",
                "Con este precio, la utilidad diaria estimada es ", (formato_moneda(r["utilidad_diaria"], 0), "b"),
                f" vendiendo unos {formato_galones(r['demanda_diaria'], 0)}/día "
                f"({formato_moneda(r['utilidad_horizonte'], 0)} en {r['horizonte']:.0f} días).\n"]
        if pol["diferencia_pct"] is not None:
            seg += [f"Comparado con margen fijo del {self.app.sistema.config['margen_politica_fija']*100:.0f}% "
                    f"({formato_moneda(pol['A']['precio'])}), la diferencia estimada es ",
                    (f"{formato_moneda(pol['diferencia'], 0, True)}/día ({formato_pct(pol['diferencia_pct'], 1, True)})", "b"),
                    ".\n"]
        seg.append((f"\nDatos usados: demanda base {formato_galones(r['d_base'], 0)}/día (promedio de los "
                    f"últimos {r['dias_demanda']} días), precio de mercado {formato_moneda(r['p_mercado'])} "
                    f"({r['fuente_mercado']}), stock {formato_galones(r['stock'], 0)}, horizonte "
                    f"{r['horizonte']:.0f} días ({r['nota_horizonte']}). Rango permitido: "
                    f"{formato_moneda(r['limite_inferior'])} – {formato_moneda(r['limite_superior'])}. "
                    f"Restricción que define el precio: {r['restriccion_activa']}. Precio exacto antes del "
                    f"redondeo XX.X9: {r['precio_exacto']:.4f}.\n", "gris"))
        seg.append((f"\n⚠️ Este cálculo depende del parámetro de elasticidad (κ={r['kappa']:g}). Si la demanda "
                    "real reacciona diferente, los resultados variarán. Use la tabla de sensibilidad como guía.\n",
                    "alerta"))
        seg += [(f"⚠ {a}\n", "alerta") for a in r["advertencias"]]
        self.texto.escribir(seg)

    def _grafico(self, p, r):
        precios, util = r["curva"]
        self.grafico.limpiar()
        ax = self.grafico.figura.add_subplot(111)
        ax.plot(precios, util, color=COLORES_PRODUCTO[p], label="Utilidad diaria estimada")
        ax.axvspan(r["limite_inferior"], r["limite_superior"], color="#FFE08A", alpha=0.5,
                   label="Rango permitido")
        ax.axvline(r["costo"], color="black", ls=":", lw=1, label="Costo FIFO")
        pa = r["politicas"]["A"]
        ax.scatter([pa["precio"]], [pa["utilidad_diaria"]], color="gray", s=60, zorder=3,
                   label=f"Política A ({formato_moneda(pa['precio'])})")
        ax.scatter([r["precio_recomendado"]], [r["utilidad_diaria"]], color="#B42318", s=90, marker="*",
                   zorder=4, label=f"Óptimo ({formato_moneda(r['precio_recomendado'])})")
        ax.set_xlabel("Precio de venta (S//gal)")
        ax.set_ylabel("S/ por día")
        ax.set_title(f"Utilidad diaria vs precio — {p}")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="best")
        self.grafico.dibujar()

    def _tablas(self, r):
        pol = r["politicas"]
        self.t_politicas.cargar(
            ["Política", "Precio S//gal", "Demanda gal/día", "Utilidad diaria S/", "Diferencia vs A"],
            [(pol["A"]["nombre"], f"{pol['A']['precio']:.2f}", f"{pol['A']['demanda']:,.0f}",
              f"{pol['A']['utilidad_diaria']:,.0f}", "—"),
             (pol["B"]["nombre"], f"{pol['B']['precio']:.2f}", f"{pol['B']['demanda']:,.0f}",
              f"{pol['B']['utilidad_diaria']:,.0f}", formato_moneda(pol["diferencia"], 0, True))],
            [240, 110, 130, 140, 130], [None, "destacado"])
        sens = r["sensibilidad"]
        self.t_sens.cargar(
            ["Variación", "Precio S//gal", "Margen %", "Demanda gal/día", "Utilidad diaria S/",
             "Utilidad horizonte S/", "vs recomendado S//día"],
            [(f"{s['variacion']*100:+.0f}%", f"{s['precio']:.2f}", formato_pct(s["margen_pct"]),
              f"{s['demanda']:,.0f}", f"{s['utilidad_diaria']:,.0f}", f"{s['utilidad_horizonte']:,.0f}",
              f"{s['dif_vs_optimo']:+,.0f}") for s in sens],
            [80, 100, 80, 120, 130, 140, 150],
            ["destacado" if s["variacion"] == 0 else (None if s["permitido"] else "alerta") for s in sens])
        esc = r["escenarios"]
        self.t_kappa.cargar(
            ["κ", "Precio óptimo S//gal", "Margen %", "Demanda gal/día", "Utilidad diaria S/"],
            [(e["kappa"], f"{e['precio']:.2f}", formato_pct(e["margen_pct"]), f"{e['demanda']:,.0f}",
              f"{e['utilidad_diaria']:,.0f}") for e in esc], [60, 140, 90, 130, 140],
            ["destacado" if abs(e["kappa"] - r["kappa"]) < 1e-9 else None for e in esc])
