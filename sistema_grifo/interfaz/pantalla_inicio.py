"""
Tablero de decisiones (pantalla Inicio).

Arriba: indicadores clave del negocio. Al centro: una tarjeta por combustible
con semáforo (ACTUAR HOY / ATENCIÓN / EN ORDEN), el precio recomendado y las
decisiones gerenciales y operativas. Abajo: alertas y acciones rápidas.
"""
import customtkinter as ctk

from configuracion import PRODUCTOS
from interfaz.componentes import COLORES_PRODUCTO, FUENTE
from utilidades.helpers import formato_fecha, formato_moneda, formato_pct

FONDO = "#FFF8EC"
TARJETA = "#FFFFFF"
BORDE = "#EFD9B4"
TEXTO = "#2B1D0E"
SUAVE = "#7A6A55"
SEMAFORO = {"rojo": ("#B42318", "#FEE4E2", "ACTUAR HOY"),
            "amarillo": ("#B54708", "#FEF0C7", "ATENCIÓN"),
            "verde": ("#067647", "#DCFAE6", "EN ORDEN"),
            "gris": ("#667085", "#F2F4F7", "SIN DATOS")}


def _lbl(padre, texto="", tam=12, peso="normal", color=TEXTO, **kw):
    return ctk.CTkLabel(padre, text=texto, font=(FUENTE, tam, peso), text_color=color, **kw)


class Indicador(ctk.CTkFrame):
    """Tile de KPI: etiqueta pequeña, valor grande y nota."""

    def __init__(self, padre, etiqueta, icono, acento):
        super().__init__(padre, fg_color=TARJETA, corner_radius=14, border_width=1, border_color=BORDE)
        franja = ctk.CTkFrame(self, fg_color=acento, width=6, height=60, corner_radius=3)
        franja.pack(side="left", fill="y", padx=(8, 0), pady=12)
        cuerpo = ctk.CTkFrame(self, fg_color="transparent", height=60)
        cuerpo.pack(side="left", fill="both", expand=True, padx=12, pady=10)
        _lbl(cuerpo, f"{icono}  {etiqueta.upper()}", 10, "bold", SUAVE).pack(anchor="w")
        self.valor = _lbl(cuerpo, "—", 22, "bold")
        self.valor.pack(anchor="w")
        self.nota = _lbl(cuerpo, "", 10, color=SUAVE, wraplength=220, justify="left")
        self.nota.pack(anchor="w")

    def poner(self, valor, nota="", color=TEXTO):
        self.valor.configure(text=valor, text_color=color)
        self.nota.configure(text=nota)


class TarjetaProducto(ctk.CTkFrame):
    """Tarjeta de decisión de un combustible."""

    def __init__(self, padre, app, producto):
        super().__init__(padre, fg_color=TARJETA, corner_radius=16, border_width=1, border_color=BORDE)
        self.app, self.p = app, producto
        color = COLORES_PRODUCTO[producto]
        cab = ctk.CTkFrame(self, fg_color=color, corner_radius=14, height=54)
        cab.pack(fill="x", padx=6, pady=(6, 0))
        _lbl(cab, producto, 20, "bold", "white").pack(side="left", padx=(14, 6), pady=8)
        _lbl(cab, app.sistema.config["nombres_productos"][producto], 12, color="#FFF3DA").pack(side="left")
        self.insignia = ctk.CTkLabel(cab, text="", font=(FUENTE, 10, "bold"), corner_radius=10,
                                     fg_color="white", text_color=TEXTO, padx=10)
        self.insignia.pack(side="right", padx=12)

        c = ctk.CTkFrame(self, fg_color="transparent")
        c.pack(fill="both", expand=True, padx=16, pady=10)
        _lbl(c, "PRECIO RECOMENDADO HOY", 10, "bold", SUAVE).pack(anchor="w")
        fila = ctk.CTkFrame(c, fg_color="transparent")
        fila.pack(anchor="w", fill="x")
        self.precio = _lbl(fila, "—", 32, "bold", color)
        self.precio.pack(side="left")
        self.delta = ctk.CTkLabel(fila, text="", font=(FUENTE, 11, "bold"), corner_radius=8, padx=8)
        self.delta.pack(side="left", padx=10, pady=(8, 0))
        self.detalle_precio = _lbl(c, "", 11, color=SUAVE, justify="left", wraplength=300)
        self.detalle_precio.pack(anchor="w")

        ctk.CTkFrame(c, fg_color=BORDE, height=1).pack(fill="x", pady=8)
        _lbl(c, "🏛  GERENCIAL · próximo cambio del proveedor", 11, "bold").pack(anchor="w")
        self.proveedor = _lbl(c, "", 12, justify="left", wraplength=300)
        self.proveedor.pack(anchor="w", pady=(0, 6))

        _lbl(c, "🚚  OPERATIVA · stock y cisterna", 11, "bold").pack(anchor="w")
        self.barra = ctk.CTkProgressBar(c, height=14, corner_radius=7)
        self.barra.pack(fill="x", pady=(4, 2))
        self.stock = _lbl(c, "", 12, justify="left", wraplength=300)
        self.stock.pack(anchor="w")

        b = ctk.CTkFrame(c, fg_color="transparent")
        b.pack(fill="x", pady=(10, 0))
        ctk.CTkButton(b, text="Ver precio óptimo →", height=30, corner_radius=8, fg_color=color,
                      command=lambda: app.mostrar("Precio óptimo (Modelo 2)")).pack(side="left")
        ctk.CTkButton(b, text="Pronóstico", height=30, width=90, corner_radius=8, fg_color="transparent",
                      border_width=1, border_color=color, text_color=color, hover_color="#FFF1D6",
                      command=lambda: app.mostrar("Pronóstico (Modelo 1)")).pack(side="left", padx=6)

    def actualizar(self):
        s, p = self.app.sistema, self.p
        cfg, mon = s.config, s.config["moneda"]
        t = s.tanques[p]
        po, pr = s.precio_optimo(p), s.pronostico(p)
        v = s.ventas_procesadas[s.ventas_procesadas["producto"] == p]
        actual = float(v["precio"].iloc[-1]) if len(v) else None
        nivel = 0   # 0 verde, 1 amarillo, 2 rojo

        if po.get("ok"):
            self.precio.configure(text=f"{mon} {po['precio_recomendado']:.2f}")
            self.detalle_precio.configure(
                text=f"Margen {formato_pct(po['margen_pct'])} sobre costo FIFO {formato_moneda(po['costo'], 2)} · "
                     f"utilidad estimada {formato_moneda(po['utilidad_diaria'], 0)}/día"
                     + ("\n⚠ Precio elevado a propósito: el stock no alcanza hasta la próxima cisterna "
                        "y conviene vender menos galones con más margen." if "stock" in po.get(
                            "restriccion_activa", "") else ""))
            if actual:
                d = po["precio_recomendado"] - actual
                if abs(d) < 0.005:
                    self.delta.configure(text="= precio actual", fg_color="#DCFAE6", text_color="#067647")
                else:
                    self.delta.configure(text=f"{'▲ subir' if d > 0 else '▼ bajar'} {abs(d):.2f}",
                                         fg_color="#FEF0C7", text_color="#B54708")
                    nivel = max(nivel, 1)
            if po["margen_pct"] < cfg["margen_minimo"] - 1e-4:
                nivel = 2
        else:
            self.precio.configure(text="—")
            self.detalle_precio.configure(text="Sin datos suficientes para recomendar un precio.")

        if pr.get("ok"):
            dias = int(pr["dias_hasta_cambio"])
            flecha = {"ALZA": "▲ SUBIRÍA", "BAJA": "▼ BAJARÍA"}.get(pr["direccion"], "CAMBIARÍA")
            if pr["atrasado"]:
                cuando, nivel = "en cualquier momento (ya superó su intervalo habitual)", max(nivel, 1)
            else:
                cuando = f"en {dias} día{'s' if dias != 1 else ''} ({formato_fecha(pr['fecha_estimada'])})"
                if dias <= 2:
                    nivel = max(nivel, 1)
            self.proveedor.configure(
                text=f"Esperado {cuando}. {flecha} ~{formato_moneda(pr['magnitud'])}/gal · confianza "
                     f"{pr['confianza'].lower()}. Revise el precio cuando ocurra.")
        else:
            self.proveedor.configure(text="Sin historial suficiente del proveedor.")

        d_base, _ = s.demanda_base(p)
        dias_stock = t.stock_actual() / d_base if d_base > 0 else None
        frac = t.porcentaje_lleno()
        self.barra.set(max(0.0, min(1.0, frac)))
        if dias_stock is not None and (dias_stock < 2 or frac < cfg["alerta_stock_pct"]):
            nivel = 2
            self.barra.configure(progress_color="#B42318")
            accion = "PEDIR CISTERNA HOY"
        elif dias_stock is not None and dias_stock < 3.5:
            nivel = max(nivel, 1)
            self.barra.configure(progress_color="#F79009")
            accion = "Programar cisterna en las próximas 24–48 h"
        else:
            self.barra.configure(progress_color="#12B76A")
            accion = "Sin urgencia de compra"
        self.stock.configure(
            text=f"{t.stock_actual():,.0f} gal ({frac*100:.0f}% del tanque) · "
                 f"{'—' if dias_stock is None else f'{dias_stock:.1f} días'} de cobertura\n→ {accion}")

        color_txt, fondo, texto = SEMAFORO[["verde", "amarillo", "rojo"][nivel]
                                           if po.get("ok") else "gris"]
        self.insignia.configure(text=f"● {texto}", text_color=color_txt, fg_color=fondo)
        self.configure(border_color=color_txt if nivel == 2 else BORDE, border_width=2 if nivel == 2 else 1)
        return nivel


class PantallaInicio(ctk.CTkScrollableFrame):
    """Tablero de decisiones."""

    def __init__(self, padre, app):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.pack(fill="x", pady=(0, 10))
        izq = ctk.CTkFrame(cab, fg_color="transparent")
        izq.pack(side="left")
        _lbl(izq, "Tablero de decisiones", 26, "bold", "#8A3B00").pack(anchor="w")
        self.subtitulo = _lbl(izq, "", 12, color=SUAVE)
        self.subtitulo.pack(anchor="w")
        der = ctk.CTkFrame(cab, fg_color="transparent")
        der.pack(side="right")
        ctk.CTkButton(der, text="📝  Generar artículo", height=40, corner_radius=10, fg_color="#A63A00",
                      hover_color="#7F2C00", font=(FUENTE, 13, "bold"),
                      command=lambda: app.mostrar("Exportar artículo")).pack(side="right")
        ctk.CTkButton(der, text="📂  Importar datos", height=40, corner_radius=10, fg_color="transparent",
                      border_width=1, border_color="#E8780C", text_color="#A63A00", hover_color="#FFF1D6",
                      font=(FUENTE, 13), command=app.importar_todo).pack(side="right", padx=8)

        kpis = ctk.CTkFrame(self, fg_color="transparent")
        kpis.pack(fill="x")
        defs = [("Ventas del periodo", "💰", "#E8780C"), ("Utilidad bruta (FIFO)", "📈", "#12B76A"),
                ("Ganancia extra con el modelo", "🎯", "#A63A00"), ("Decisiones urgentes", "🚦", "#B42318")]
        self.kpi = []
        for i, (e, ic, ac) in enumerate(defs):
            k = Indicador(kpis, e, ic, ac)
            k.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)
            kpis.grid_columnconfigure(i, weight=1, uniform="k")
            self.kpi.append(k)

        _lbl(self, "Qué hacer hoy con cada combustible", 16, "bold").pack(anchor="w", pady=(14, 2), padx=6)
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x")
        self.tarjetas = []
        for i, p in enumerate(PRODUCTOS):
            t = TarjetaProducto(fila, app, p)
            t.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)
            fila.grid_columnconfigure(i, weight=1, uniform="p")
            self.tarjetas.append(t)

        _lbl(self, "Alertas y avisos", 16, "bold").pack(anchor="w", pady=(14, 2), padx=6)
        self.caja_alertas = ctk.CTkFrame(self, fg_color=TARJETA, corner_radius=14, border_width=1,
                                         border_color=BORDE)
        self.caja_alertas.pack(fill="x", padx=6)

        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(fill="x", pady=12, padx=6)
        ctk.CTkButton(pie, text="🧪 Cargar datos de ejemplo", height=32, corner_radius=8, fg_color="#7A5418",
                      command=app.cargar_ejemplo).pack(side="left")
        ctk.CTkButton(pie, text="Borrar todos los datos", height=32, corner_radius=8, fg_color="transparent",
                      border_width=1, border_color="#912018", text_color="#912018", hover_color="#FEE4E2",
                      command=app.borrar_datos).pack(side="left", padx=8)

    def _alerta(self, icono, texto, color):
        f = ctk.CTkFrame(self.caja_alertas, fg_color="transparent")
        f.pack(fill="x", padx=12, pady=3)
        _lbl(f, icono, 14, color=color).pack(side="left", padx=(0, 8))
        _lbl(f, texto, 12, color=TEXTO, justify="left", wraplength=1000, anchor="w").pack(side="left", fill="x")

    def actualizar(self):
        s = self.app.sistema
        for w in self.caja_alertas.winfo_children():
            w.destroy()
        if s.ultima_fecha is None:
            self.subtitulo.configure(text="Sin datos cargados")
            for k in self.kpi:
                k.poner("—")
            self._alerta("📂", "No hay datos. Use «Importar datos» o «Cargar datos de ejemplo».", "#B54708")
            return
        self.subtitulo.configure(text=f"Fecha de análisis: {formato_fecha(s.fecha_actual)}  ·  último "
                                      f"movimiento {formato_fecha(s.ultima_fecha, True)}")
        vp = s.ventas_procesadas
        mon = s.config["moneda"]
        ingreso = float((vp["volumen"] * vp["precio"]).sum())
        util = float(vp["utilidad"].sum())
        self.kpi[0].poner(f"{mon} {ingreso/1e6:,.2f} M", f"{vp['volumen'].sum():,.0f} galones vendidos")
        self.kpi[1].poner(f"{mon} {util/1e3:,.0f} mil", f"margen medio {util/ingreso*100:.1f}% sobre ventas"
                          if ingreso else "")
        niveles = [t.actualizar() for t in self.tarjetas]
        urg = sum(n == 2 for n in niveles)
        self.kpi[3].poner(str(urg), "productos requieren acción hoy" if urg else "todo bajo control",
                          "#B42318" if urg else "#067647")
        self.kpi[2].poner("calculando…", "simulación de 6 meses")
        self.after(30, self._kpi_modelo)

        hubo = False
        for p in PRODUCTOS:
            t = s.tanques[p]
            if t.porcentaje_lleno() < s.config["alerta_stock_pct"]:
                self._alerta("⛽", f"{p}: stock bajo ({formato_pct(t.porcentaje_lleno())} del tanque). "
                                  "Programe una cisterna.", "#B42318")
                hubo = True
            pr = s.pronostico(p)
            if pr.get("ok") and pr["atrasado"]:
                self._alerta("⏰", f"{p}: el proveedor ya superó su intervalo habitual de cambio de precio "
                                  f"({pr['dias_desde_ultimo']} días sin cambios). Es probable que "
                                  f"{'suba' if pr['direccion'] == 'ALZA' else 'baje'} pronto.", "#B54708")
                hubo = True
        rech = s.texto_rechazos()
        if rech:
            self._alerta("ℹ", rech, SUAVE)
            hubo = True
        if not hubo:
            self._alerta("✔", "Sin alertas.", "#067647")

    def _kpi_modelo(self):
        """KPI que requiere la simulación completa (se calcula después de mostrar la pantalla)."""
        try:
            from exportador import tablas_articulo
            r = tablas_articulo.calcular_resultados(self.app.sistema)
            rp = r.get("resumen_politicas") or {}
            a = sum(v["utilidad_total"] for (p, k), v in rp.items() if k == "A")
            b = sum(v["utilidad_total"] for (p, k), v in rp.items() if k == "B")
            mon = self.app.sistema.config["moneda"]
            if a:
                self.kpi[2].poner(f"{'+' if b >= a else ''}{mon} {(b-a)/1e3:,.1f} mil",
                                  f"{(b-a)/a*100:+.1f}% vs margen fijo "
                                  f"{self.app.sistema.config['margen_politica_fija']*100:.0f}% (6 meses)",
                                  "#067647" if b >= a else "#B42318")
            else:
                self.kpi[2].poner("—", "datos insuficientes para simular")
        except Exception as e:   # el tablero nunca debe caerse por este indicador
            self.kpi[2].poner("—", f"no disponible: {e}")
