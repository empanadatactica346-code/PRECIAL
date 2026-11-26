"""Pantalla del Modelo 1: pronóstico de cambios de precio del proveedor (Croston TSB)."""
from tkinter import messagebox

import customtkinter as ctk
import pandas as pd

from configuracion import PRODUCTOS, hoy
from utilidades.decisiones import tarjeta_pronostico
from interfaz.componentes import (SeccionPlegable, TarjetaDecision, exportar_hojas_articulo, COLORES_PRODUCTO, Grafico, Tabla, TextoRico, campo, explicacion,
                                  poner_valor, selector_productos, titulo)
from utilidades.helpers import formato_fecha, formato_moneda


class PantallaPronostico(ctk.CTkScrollableFrame):
    """Respuesta directa por producto (tarjetas) y detalles técnicos plegables."""

    def __init__(self, padre, app):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        titulo(self, "Modelo 1 — ¿Cuándo cambiará el precio del proveedor?").pack(anchor="w")
        explicacion(self, "Cada recuadro le dice cuándo se espera el próximo cambio de precio de su proveedor "
                          "y si probablemente subirá o bajará. Verde = sin urgencia (más de 7 días); amarillo = "
                          "prepárese (3 a 7 días); rojo = revise sus precios hoy.").pack(anchor="w", pady=(2, 8))
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(f, text="Fecha actual:", font=("Segoe UI", 13, "bold")).pack(side="left")
        self.fecha = ctk.CTkEntry(f, width=120)
        self.fecha.pack(side="left", padx=6)
        poner_valor(self.fecha, app.sistema.fecha_actual.strftime("%d/%m/%Y"))
        ctk.CTkButton(f, text="Aplicar fecha", width=110, command=self.aplicar_fecha).pack(side="left")
        ctk.CTkButton(f, text="Hoy", width=60, fg_color="#7A5418",
                      command=lambda: (poner_valor(self.fecha, hoy().strftime("%d/%m/%Y")),
                                       self.aplicar_fecha())).pack(side="left", padx=6)
        explicacion(self, "Cámbiela solo para simular escenarios (por ejemplo, ver qué decía el sistema "
                          "en una fecha pasada).", 500).pack(side="left", padx=8, in_=f)

        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x")
        self.tarjetas = {}
        for i, prod in enumerate(PRODUCTOS):
            t = TarjetaDecision(fila)
            t.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)
            fila.grid_columnconfigure(i, weight=1, uniform="t")
            self.tarjetas[prod] = t

        self.plegable = SeccionPlegable(self, "Ver detalles técnicos")
        self.plegable.pack(fill="x")
        self.plegable.al_abrir = self.actualizar_detalles
        d = self.plegable.contenido
        ctrl = ctk.CTkFrame(d)
        ctrl.pack(fill="x", pady=4)
        self.selector = selector_productos(ctrl, lambda _: self.actualizar_detalles())
        self.selector.grid(row=0, column=0, columnspan=2, padx=10, pady=6, sticky="w")
        self.alfa = campo(ctrl, "α (tamaño, 0.05–0.30)", 1, 0, ancho=80)
        self.beta = campo(ctrl, "β (intervalo, 0.05–0.30)", 1, 2, ancho=80)
        self.optimizar = ctk.CTkCheckBox(ctrl, text="Optimizar α y β automáticamente (menor error)")
        self.optimizar.grid(row=2, column=0, columnspan=3, sticky="w", padx=10, pady=4)
        self.optimizar.select()
        ctk.CTkButton(ctrl, text="Recalcular", command=self.recalcular).grid(row=2, column=3, padx=10, pady=4)
        ctk.CTkButton(ctrl, text="Exportar tabla del Modelo 1", command=lambda: exportar_hojas_articulo(
            app, ["Tabla3_Resultados_Modelo1"], "TABLA_MODELO1.xlsx")).grid(row=2, column=4, padx=10, pady=4)
        self.texto = TextoRico(d, alto=230)
        self.texto.pack(fill="x", pady=6)
        self.grafico = Grafico(d, alto=3.4)
        self.grafico.pack(fill="x", pady=6)
        ctk.CTkLabel(d, text="Backtest: ¿qué tan bien habría acertado el modelo en el pasado?",
                     font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(8, 2))
        explicacion(d, "En cada cambio de precio pasado, el modelo pronostica usando solo los datos anteriores "
                       "y se mide el error, comparándolo con el promedio simple.").pack(anchor="w")
        self.tabla = Tabla(d, alto=3)
        self.tabla.pack(fill="x", pady=4)
        ctk.CTkLabel(d, text="Últimos cambios de precio observados",
                     font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(8, 2))
        self.tabla_eventos = Tabla(d, alto=8)
        self.tabla_eventos.pack(fill="x", pady=4)
        self._parametros_iniciales()

    def aplicar_fecha(self):
        try:
            f = pd.to_datetime(self.fecha.get().strip(), dayfirst=True)
        except (ValueError, TypeError):
            f = pd.NaT
        if pd.isna(f):
            messagebox.showerror("Fecha inválida", "Use el formato DD/MM/AAAA.")
            return
        self.app.sistema.fecha_actual = f.normalize()
        self.app.refrescar_todo()

    def _parametros_iniciales(self):
        cfg = self.app.sistema.config
        poner_valor(self.alfa, cfg["croston_alfa_inicial"])
        poner_valor(self.beta, cfg["croston_beta_inicial"])

    def _leer_parametros(self):
        try:
            a, b = float(self.alfa.get()), float(self.beta.get())
        except ValueError:
            raise ValueError("α y β deben ser números.")
        if not (0.05 <= a <= 0.30 and 0.05 <= b <= 0.30):
            raise ValueError("α y β deben estar entre 0.05 y 0.30.")
        return a, b

    def recalcular(self):
        self.app.sistema._cache_pronostico.clear()
        self.actualizar_detalles()

    def actualizar(self):
        s = self.app.sistema
        poner_valor(self.fecha, s.fecha_actual.strftime("%d/%m/%Y"))
        for prod, t in self.tarjetas.items():
            t.mostrar(*tarjeta_pronostico(s, prod, s.pronostico(prod)))
        if self.plegable.abierto:
            self.actualizar_detalles()

    def actualizar_detalles(self):
        try:
            a, b = self._leer_parametros()
        except ValueError as e:
            messagebox.showerror("Parámetros inválidos", str(e))
            return
        p = self.selector.get()
        r = self.app.sistema.pronostico(p, a, b, bool(self.optimizar.get()))
        self._texto(p, r)
        self._grafico(p, r)
        self._tablas(r)

    def _texto(self, p, r):
        seg = [(f"{self.app.sistema.config['nombres_productos'][p]} ({p})\n", "titulo"),
               (f"Fuente de datos: {r.get('fuente', '—')}\n\n", "gris")]
        if not r["ok"]:
            seg.append(("No es posible pronosticar.\n", "alerta"))
            seg += [(f"⚠ {a}\n", "alerta") for a in r["advertencias"]]
            self.texto.escribir(seg)
            return
        if r["atrasado"]:
            seg += ["Se estima que el próximo cambio de precio del proveedor para ", (p, "b"),
                    " puede ocurrir ", ("en cualquier momento", "b"),
                    f" (el intervalo típico es de {r['intervalo_estimado']:.1f} días y ya pasaron "
                    f"{r['dias_desde_ultimo']} días desde el último cambio).\n"]
        else:
            seg += ["Se estima que el próximo cambio de precio del proveedor para ", (p, "b"),
                    " ocurrirá en ", (f"{r['dias_hasta_cambio']:.0f} días", "b"),
                    " (alrededor del ", (formato_fecha(r["fecha_estimada"]), "b"), ").\n"]
        seg += ["La magnitud estimada del cambio es de ", (f"{formato_moneda(r['magnitud'])} por galón", "b"),
                f" (precio actual del proveedor: {formato_moneda(r['precio_actual'])}).\n"]
        ult = ", ".join(f"{c:+.2f}" for c in r["ultimos_cambios"])
        seg += [f"Tendencia reciente: los últimos {len(r['ultimos_cambios'])} cambios fueron [{ult}], "
                "dirección probable: ", (r["direccion"], "b"), "\n"]
        seg += ["Confianza del pronóstico: ", (r["confianza"], "ok" if r["confianza"] == "ALTA" else "b"),
                f" ({r['n_cambios']} cambios observados).\n"]
        seg.append((f"\nDetalle técnico: intervalo estimado p = {r['intervalo_estimado']:.2f} días, "
                    f"tamaño estimado z = {r['magnitud']:.4f}, tasa TSB y = (1-β/2)·z/p = "
                    f"{r['tasa_diaria']:.4f} S//gal por día, α = {r['alfa']:.2f}, β = {r['beta']:.2f}"
                    f"{' (optimizados)' if self.optimizar.get() else ''}.\n", "gris"))
        if r["advertencias"]:
            seg.append("\n")
            seg += [(f"⚠ {a}\n", "alerta") for a in r["advertencias"]]
        self.texto.escribir(seg)

    def _grafico(self, p, r):
        serie = r.get("serie")
        if serie is None or len(serie) == 0:
            self.grafico.mensaje("No hay datos de precios del proveedor.")
            return
        self.grafico.limpiar()
        ax = self.grafico.figura.add_subplot(111)
        ax.step(serie.index, serie.values, where="post", color=COLORES_PRODUCTO[p], label="Precio proveedor")
        ev = r["eventos"]
        if not ev.empty:
            sub, baj = ev[ev["cambio"] > 0], ev[ev["cambio"] < 0]
            ax.scatter(sub["fecha"], sub["precio_nuevo"], marker="^", color="#d62728", zorder=3, label="Alza")
            ax.scatter(baj["fecha"], baj["precio_nuevo"], marker="v", color="#2ca02c", zorder=3, label="Baja")
        if r["ok"]:
            signo = {"ALZA": 1, "BAJA": -1}.get(r["direccion"], 0)
            f0, f1 = serie.index[-1], max(r["fecha_estimada"], serie.index[-1] + pd.Timedelta(days=1))
            p0 = r["precio_actual"]
            ax.plot([f0, f1, f1 + pd.Timedelta(days=3)], [p0, p0, p0 + signo * r["magnitud"]],
                    ls="--", color="gray", label="Proyección")
            ax.axvline(f1, ls=":", color="gray")
        ax.set_title(f"Cambios históricos del precio del proveedor — {p}")
        ax.set_ylabel("S//gal")
        ax.grid(alpha=0.3)
        ax.legend(loc="best", fontsize=8)
        self.grafico.dibujar()

    def _tablas(self, r):
        bt = r.get("backtest")
        f = lambda v, u: "—" if v is None else f"{v:.3f} {u}"
        if bt:
            mejora = lambda m, n: "—" if m is None or not n else f"{(n - m) / n * 100:+.1f}%"
            filas = [("Intervalo entre cambios (días)", f(bt["mae_intervalo_modelo"], "días"),
                      f(bt["mae_intervalo_naive"], "días"),
                      mejora(bt["mae_intervalo_modelo"], bt["mae_intervalo_naive"])),
                     ("Tamaño del cambio (S//gal)", f(bt["mae_magnitud_modelo"], "S/"),
                      f(bt["mae_magnitud_naive"], "S/"),
                      mejora(bt["mae_magnitud_modelo"], bt["mae_magnitud_naive"]))]
        else:
            filas = [("Sin datos suficientes", "—", "—", "—")]
        self.tabla.cargar(["Qué se pronostica", "Error medio (MAE) Croston TSB",
                           "Error medio método simple", "Mejora del modelo"], filas, [220, 200, 200, 140])
        ev = r["eventos"].iloc[::-1].head(30)
        self.tabla_eventos.cargar(
            ["Fecha", "Precio anterior", "Precio nuevo", "Cambio", "Días desde cambio anterior"],
            [(formato_fecha(e.fecha), f"{e.precio_anterior:.2f}", f"{e.precio_nuevo:.2f}",
              f"{e.cambio:+.2f}", "—" if pd.isna(e.intervalo) else int(e.intervalo))
             for e in ev.itertuples()], [110, 120, 120, 90, 180])
