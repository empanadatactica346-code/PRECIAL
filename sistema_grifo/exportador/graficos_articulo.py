"""
Gráficos para el artículo: PNG a 300 DPI, 20 cm × 12 cm, fondo blanco,
títulos y ejes en español y la leyenda "Fuente: Elaboración propia".
"""
import os

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from configuracion import PRODUCTOS
from modelos import modelo_precio_optimo

CM = 1 / 2.54
TAMANO = (20 * CM, 12 * CM)
DPI = 300
COLORES = {"DB5": "#1f4e79", "GR": "#c55a11", "GP": "#548235"}
GRIS = "#7f7f7f"


def _figura(filas=1, columnas=1, compartir_x=False):
    fig = Figure(figsize=TAMANO, dpi=DPI, facecolor="white")
    ejes = fig.subplots(filas, columnas, sharex=compartir_x, squeeze=False)
    for ax in ejes.flat:
        ax.set_facecolor("white")
        ax.grid(alpha=0.25, linewidth=0.5)
        ax.tick_params(labelsize=7)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
    return fig, ejes


def _guardar(fig, carpeta, nombre, titulo):
    fig.suptitle(titulo, fontsize=10, fontweight="bold")
    fig.text(0.01, 0.01, "Fuente: Elaboración propia.", fontsize=7, style="italic")
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    ruta = os.path.join(carpeta, nombre)
    fig.savefig(ruta, dpi=DPI, facecolor="white")
    return ruta


def _sin_datos(carpeta, nombre, titulo):
    fig, ejes = _figura()
    ejes[0, 0].axis("off")
    ejes[0, 0].text(0.5, 0.5, "Sin datos suficientes para este gráfico", ha="center", color=GRIS)
    return _guardar(fig, carpeta, nombre, titulo)


def _fechas(ax):
    import matplotlib.dates as mdates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))


# ------------------------------------------------------------------ gráficos
def fig01(s, r, d):
    t = "Figura 1. Evolución del precio de lista del proveedor"
    fig, ejes = _figura()
    ax = ejes[0, 0]
    for p in PRODUCTOS:
        serie, ev = r["productos"][p]["serie"], r["productos"][p]["eventos"]
        if serie is None or not len(serie):
            continue
        ax.step(serie.index, serie.values, where="post", color=COLORES[p], lw=1, label=p)
        ax.scatter(ev["fecha"], ev["precio_nuevo"], s=10, facecolors="none", edgecolors=COLORES[p], lw=0.7)
    ax.set_xlabel("Fecha", fontsize=8)
    ax.set_ylabel("Precio de lista (S//gal)", fontsize=8)
    ax.legend(fontsize=7, title="○ = cambio de precio", title_fontsize=7)
    _fechas(ax)
    return _guardar(fig, d, "fig01_evolucion_precios_proveedor.png", t)


def fig02(s, r, d):
    t = "Figura 2. Distribución de los intervalos entre cambios de precio"
    datos = {p: r["productos"][p]["eventos"]["intervalo"].dropna() for p in PRODUCTOS}
    if not any(len(v) for v in datos.values()):
        return _sin_datos(d, "fig02_intervalos_entre_cambios.png", t)
    fig, ejes = _figura()
    ax = ejes[0, 0]
    maximo = int(max(v.max() for v in datos.values() if len(v)))
    bins = np.arange(0.5, maximo + 1.5, 1)
    ax.hist([datos[p] for p in PRODUCTOS], bins=bins, color=[COLORES[p] for p in PRODUCTOS],
            label=PRODUCTOS, alpha=0.85)
    for p in PRODUCTOS:
        if len(datos[p]):
            ax.axvline(datos[p].mean(), color=COLORES[p], ls="--", lw=1)
            ax.text(datos[p].mean(), ax.get_ylim()[1] * 0.95, f" {datos[p].mean():.1f}", color=COLORES[p], fontsize=7)
    ax.set_xlabel("Días entre cambios consecutivos", fontsize=8)
    ax.set_ylabel("Frecuencia (n° de cambios)", fontsize=8)
    ax.legend(fontsize=7, title="-- = promedio", title_fontsize=7)
    return _guardar(fig, d, "fig02_intervalos_entre_cambios.png", t)


def fig03(s, r, d):
    t = "Figura 2. Costo FIFO diario vs. precio de venta en surtidor"
    v = s.ventas_procesadas
    if v.empty:
        return _sin_datos(d, "fig02_costo_fifo_vs_precio_venta.png", t)
    fig, ejes = _figura(3, 1, compartir_x=True)
    for ax, p in zip(ejes[:, 0], PRODUCTOS):
        g = v[v["producto"] == p].set_index("fecha")
        if g.empty:
            continue
        w = g["volumen"]
        precio = (g["precio"] * w).resample("D").sum() / w.resample("D").sum()
        costo = (g["costo_fifo"] * w).resample("D").sum() / w.resample("D").sum()
        ax.plot(costo.index, costo, color=GRIS, lw=1, label="Costo FIFO")
        ax.plot(precio.index, precio, color=COLORES[p], lw=1, label="Precio de venta")
        ax.fill_between(costo.index, costo, precio, color=COLORES[p], alpha=0.15, label="Margen real")
        ax.set_ylabel(f"{p} (S//gal)", fontsize=7)
        ax.legend(fontsize=6, loc="upper left", ncol=3)
    ejes[-1, 0].set_xlabel("Fecha", fontsize=8)
    _fechas(ejes[-1, 0])
    return _guardar(fig, d, "fig02_costo_fifo_vs_precio_venta.png", t)


def fig04(s, r, d):
    t = "Figura 3. Backtest Croston TSB: intervalo real vs. pronosticado"
    fig, ejes = _figura(1, 3)
    for ax, p in zip(ejes[0], PRODUCTOS):
        bt = r["productos"][p]["backtest"]
        ax.set_title(p, fontsize=8)
        if bt.empty:
            ax.text(0.5, 0.5, "Sin datos", transform=ax.transAxes, ha="center", color=GRIS)
            continue
        lim = max(bt["intervalo_real"].max(), bt["intervalo_pronosticado"].max()) + 1
        ax.plot([0, lim], [0, lim], color=GRIS, ls="--", lw=0.8, label="Pronóstico perfecto")
        ax.fill_between([0, lim], [-2, lim - 2], [2, lim + 2], color=GRIS, alpha=0.1, label="±2 días")
        ax.scatter(bt["intervalo_real"], bt["intervalo_pronosticado"], s=12, color=COLORES[p])
        ax.set_xlim(0, lim)
        ax.set_ylim(0, lim)
        ax.set_xlabel("Intervalo real (días)", fontsize=7)
    ejes[0, 0].set_ylabel("Intervalo pronosticado (días)", fontsize=7)
    ejes[0, 0].legend(fontsize=6, loc="upper left")
    return _guardar(fig, d, "fig03_backtest_croston.png", t)


def fig05(s, r, d):
    t = "Figura 4. Utilidad diaria en función del precio de venta"
    fig, ejes = _figura(1, 3)
    for ax, p in zip(ejes[0], PRODUCTOS):
        pr = r["productos"][p]["precio"]
        ax.set_title(p, fontsize=8)
        if not pr.get("ok"):
            ax.text(0.5, 0.5, "Sin datos", transform=ax.transAxes, ha="center", color=GRIS)
            continue
        x, y = pr["curva"]
        ax.plot(x, y, color=COLORES[p], lw=1.2)
        ax.axvspan(pr["precio_margen_min"], pr["precio_margen_max"], color=COLORES[p], alpha=0.1,
                   label="Margen permitido")
        ax.plot(pr["precio_recomendado"], pr["utilidad_diaria"], "o", color="black", ms=4,
                label=f"Óptimo S/ {pr['precio_recomendado']:.2f}")
        ax.set_xlabel("Precio (S//gal)", fontsize=7)
        ax.legend(fontsize=6, loc="lower center")
    ejes[0, 0].set_ylabel("Utilidad diaria (S/)", fontsize=7)
    return _guardar(fig, d, "fig04_utilidad_vs_precio.png", t)


def fig06(s, r, d):
    t = "Figura 5. Utilidad diaria: margen fijo (A) vs. precio óptimo (B)"
    sim = r["simulacion"]
    if sim.empty:
        return _sin_datos(d, "fig05_comparacion_politicas.png", t)
    fig, ejes = _figura(3, 1, compartir_x=True)
    for ax, p in zip(ejes[:, 0], PRODUCTOS):
        a = sim[(sim["producto"] == p) & (sim["politica"] == "A")].set_index("fecha")["utilidad"]
        b = sim[(sim["producto"] == p) & (sim["politica"] == "B")].set_index("fecha")["utilidad"]
        if a.empty:
            continue
        ax.plot(a.index, a, color=GRIS, lw=0.8, label="Política A")
        ax.plot(b.index, b, color=COLORES[p], lw=0.8, label="Política B")
        ax.fill_between(a.index, a, b, where=b >= a, color="#2e7d32", alpha=0.2, label="B > A")
        ax.fill_between(a.index, a, b, where=b < a, color="#c62828", alpha=0.2, label="B < A")
        ax.set_ylabel(f"{p} (S/)", fontsize=7)
        ax.legend(fontsize=6, loc="upper left", ncol=4)
    ejes[-1, 0].set_xlabel("Fecha", fontsize=8)
    _fechas(ejes[-1, 0])
    return _guardar(fig, d, "fig05_comparacion_politicas.png", t)


def fig07(s, r, d):
    t = "Figura 6. Evolución del stock diario por producto"
    h = s.historial_diario
    if h.empty:
        return _sin_datos(d, "fig06_stock_diario.png", t)
    fig, ejes = _figura(3, 1, compartir_x=True)
    for ax, p in zip(ejes[:, 0], PRODUCTOS):
        hp = h[h["producto"] == p]
        cap = s.config["capacidad_tanque"][p]
        reorden = cap * s.config.get("alerta_stock_pct", 0.2)
        ax.plot(hp["fecha"], hp["stock"], color=COLORES[p], lw=1, label="Stock al cierre")
        ax.axhline(cap, color="black", ls="--", lw=0.8, label=f"Capacidad ({cap:,.0f})")
        ax.axhline(reorden, color="#c62828", ls=":", lw=0.8, label=f"Punto de reorden ({reorden:,.0f})")
        perd = s.datos["ventas_perdidas"]
        perd = perd[(perd["producto"] == p) & (perd["volumen"] > 0)]
        dias_q = set(perd["fecha"].dt.normalize())
        if not dias_q:   # sin verdad oculta: días con stock agotado
            dias_q = set(hp.loc[hp["stock"] <= 1e-6, "fecha"])
        q = hp[hp["fecha"].isin(dias_q)]
        if len(q):
            ax.scatter(q["fecha"], q["stock"], marker="x", color="#c62828", s=18, zorder=3,
                       label=f"Quiebre de stock ({len(q)} días)")
        ax.set_ylabel(f"{p} (gal)", fontsize=7)
        ax.legend(fontsize=6, loc="lower left", ncol=3)
    ejes[-1, 0].set_xlabel("Fecha", fontsize=8)
    _fechas(ejes[-1, 0])
    return _guardar(fig, d, "fig06_stock_diario.png", t)


def fig08(s, r, d):
    t = "Figura 8. Sensibilidad del precio óptimo y la utilidad a la elasticidad κ"
    fig, ejes = _figura(1, 2)
    k = np.array(modelo_precio_optimo.ESCENARIOS_KAPPA)
    ancho = 0.8
    for i, p in enumerate(PRODUCTOS):
        pr = r["productos"][p]["precio"]
        esc = {e["kappa"]: e for e in pr.get("escenarios", [])} if pr.get("ok") else {}
        if not esc:
            continue
        ejes[0, 0].plot(k, [esc[x]["precio"] if x in esc else np.nan for x in k], "o-",
                        color=COLORES[p], ms=3, lw=1, label=p)
        ejes[0, 1].bar(k + (i - 1) * ancho, [esc[x]["utilidad_diaria"] if x in esc else 0 for x in k],
                       width=ancho, color=COLORES[p], label=p)
    ejes[0, 0].set_xlabel("Elasticidad κ", fontsize=7)
    ejes[0, 0].set_ylabel("Precio óptimo (S//gal)", fontsize=7)
    ejes[0, 1].set_xlabel("Elasticidad κ", fontsize=7)
    ejes[0, 1].set_ylabel("Utilidad diaria (S/)", fontsize=7)
    ejes[0, 1].set_xticks(k)
    for ax in ejes[0]:
        ax.legend(fontsize=6)
    return _guardar(fig, d, "fig08_sensibilidad_kappa.png", t)


def fig09(s, r, d):
    t = "Figura 9. Margen real diario (FIFO) frente al margen objetivo"
    v = s.ventas_procesadas
    if v.empty:
        return _sin_datos(d, "fig09_margen_real_diario.png", t)
    fig, ejes = _figura()
    ax = ejes[0, 0]
    for p in PRODUCTOS:
        g = v[v["producto"] == p].set_index("fecha")
        if g.empty:
            continue
        u = g["utilidad"].resample("D").sum()
        c = (g["costo_fifo"] * g["volumen"]).resample("D").sum()
        m = (u / c.replace(0, np.nan)) * 100
        ax.plot(m.index, m, color=COLORES[p], lw=0.9, label=p)
    objetivo = s.config.get("margen_politica_fija", 0.08) * 100
    ax.axhline(objetivo, color="black", ls="--", lw=0.9, label=f"Margen objetivo ({objetivo:.0f}%)")
    ax.axhline(s.config["margen_minimo"] * 100, color="#c62828", ls=":", lw=0.9,
               label=f"Margen mínimo ({s.config['margen_minimo']*100:.0f}%)")
    ax.set_xlabel("Fecha", fontsize=8)
    ax.set_ylabel("Margen real sobre costo FIFO (%)", fontsize=8)
    ax.legend(fontsize=7, ncol=3)
    _fechas(ax)
    return _guardar(fig, d, "fig09_margen_real_diario.png", t)


def fig10(s, r, d):
    t = "Figura 10. Error absoluto medio acumulado del Modelo 1"
    bt = r["backtest"]
    if bt.empty:
        return _sin_datos(d, "fig10_error_pronostico_acumulado.png", t)
    fig, ejes = _figura()
    ax = ejes[0, 0]
    for p in PRODUCTOS:
        g = bt[bt["producto"] == p].sort_values("fecha_real")
        if g.empty:
            continue
        e = (g["intervalo_pronosticado"] - g["intervalo_real"]).abs().expanding().mean()
        en = (g["intervalo_naive"] - g["intervalo_real"]).abs().expanding().mean()
        ax.plot(g["fecha_real"], e, color=COLORES[p], lw=1.2, marker="o", ms=2, label=f"{p} Croston TSB")
        ax.plot(g["fecha_real"], en, color=COLORES[p], lw=0.8, ls="--", label=f"{p} naive")
    ax.set_xlabel("Fecha del cambio de precio", fontsize=8)
    ax.set_ylabel("MAE acumulado (días)", fontsize=8)
    ax.legend(fontsize=6, ncol=3)
    _fechas(ax)
    return _guardar(fig, d, "fig10_error_pronostico_acumulado.png", t)


# Los 6 gráficos del artículo (fig02, fig08, fig09 y fig10 se conservan solo como funciones internas)
GRAFICOS = [fig01, fig03, fig04, fig05, fig06, fig07]
NOMBRES = ["Evolución de precios del proveedor", "Costo FIFO vs precio de venta",
           "Backtest Croston: real vs pronosticado", "Utilidad vs precio (óptimo)",
           "Margen fijo vs precio óptimo: utilidad diaria", "Stock diario con quiebres"]


def generar_graficos(sistema, resultados, carpeta, progreso=None):
    """Genera los 6 gráficos en 'carpeta'. Devuelve la lista de rutas."""
    os.makedirs(carpeta, exist_ok=True)
    rutas = []
    for i, f in enumerate(GRAFICOS):
        if progreso:
            progreso(i / len(GRAFICOS), f"Gráfico {i+1}/{len(GRAFICOS)}: {NOMBRES[i]}")
        rutas.append(f(sistema, resultados, carpeta))
    return rutas
