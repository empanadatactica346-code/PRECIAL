"""
MODELO 2 — Precio óptimo de venta.

Maximizar   U(p) = (p - c) · D(p) · T
Demanda     D(p) = D_base · 2 / (1 + exp(κ · (p / p_mercado - 1)))
Sujeto a    c·(1+margen_min) ≤ p ≤ c·(1+margen_max)
            D(p)·T ≤ stock_actual
            D(p)·T ≤ capacidad_maxima

Como D(p) baja cuando p sube, las restricciones de volumen se convierten
en un precio mínimo (se resuelve por bisección). Luego se maximiza U(p)
en el intervalo factible con búsqueda de sección dorada (U es unimodal).
Se implementan aquí para no depender de SciPy (arranque más rápido).
"""
import math

import numpy as np


def biseccion(f, a, b, tol=1e-10, max_iter=200):
    """Raíz de f en [a, b] (f(a) y f(b) con signo distinto)."""
    fa = f(a)
    for _ in range(max_iter):
        m = (a + b) / 2
        fm = f(m)
        if fm == 0 or (b - a) / 2 < tol:
            return m
        if (fm > 0) == (fa > 0):
            a, fa = m, fm
        else:
            b = m
    return (a + b) / 2


def maximo_seccion_dorada(f, a, b, tol=1e-7):
    """Punto que maximiza una función unimodal f en [a, b]."""
    g = (math.sqrt(5) - 1) / 2
    c, d = b - g * (b - a), a + g * (b - a)
    fc, fd = f(c), f(d)
    while b - a > tol:
        if fc > fd:
            b, d, fd = d, c, fc
            c = b - g * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + g * (b - a)
            fd = f(d)
    x = (a + b) / 2
    return max((a, b, x), key=f)

from utilidades.helpers import redondeo_peruano, redondeo_peruano_en_rango

ESCENARIOS_KAPPA = [15, 18, 20, 23, 25]
VARIACIONES_SENSIBILIDAD = [-0.10, -0.05, 0.0, 0.05, 0.10]


def demanda(p, d_base, kappa, p_mercado):
    """Galones/día esperados al precio p (curva logística)."""
    x = np.clip(kappa * (np.asarray(p, dtype=float) / p_mercado - 1.0), -50, 50)
    return d_base * 2.0 / (1.0 + np.exp(x))


def utilidad_diaria(p, costo, d_base, kappa, p_mercado):
    """(p - c) · D(p)."""
    return (p - costo) * demanda(p, d_base, kappa, p_mercado)


def optimizar_precio(costo, d_base, p_mercado, kappa, margen_min, margen_max,
                     horizonte, stock, capacidad):
    """
    Calcula el precio que maximiza la utilidad respetando las restricciones.
    Devuelve un dict con el precio exacto, el precio redondeado (XX.X9),
    demanda, utilidades, límites usados y advertencias.
    """
    adv = []
    if costo <= 0 or d_base <= 0 or p_mercado <= 0 or horizonte <= 0:
        return {"ok": False, "advertencias": [
            "Faltan datos: se necesita costo FIFO, demanda histórica y precio de mercado."]}

    limite_inferior = costo * (1 + margen_min)
    limite_superior = costo * (1 + margen_max)
    restriccion = "ninguna (óptimo interior)"

    # Restricciones de volumen: D(p)·T ≤ min(stock, capacidad)
    limite_vol = min(stock, capacidad)
    nombre_lim = "stock disponible" if stock <= capacidad else "capacidad"
    vol = lambda p: float(demanda(p, d_base, kappa, p_mercado)) * horizonte - limite_vol
    if vol(limite_inferior) > 0:
        if vol(limite_superior) > 0:
            limite_inferior = limite_superior
            adv.append(
                f"Con el {nombre_lim} ({limite_vol:,.0f} gal) no alcanza para {horizonte:.0f} días "
                "ni siquiera con el margen máximo: el stock se agotará antes. "
                "Programe una cisterna.")
        else:
            limite_inferior = biseccion(vol, limite_inferior, limite_superior)
            restriccion = f"{nombre_lim} (no vender más de lo que hay en {horizonte:.0f} días)"

    if limite_superior - limite_inferior < 1e-9:
        p_opt = limite_superior
        restriccion = "margen máximo / stock"
    else:
        p_opt = maximo_seccion_dorada(
            lambda p: float(utilidad_diaria(p, costo, d_base, kappa, p_mercado)),
            limite_inferior, limite_superior)
        tol = (limite_superior - limite_inferior) * 1e-3
        if p_opt - limite_inferior < tol and restriccion.startswith("ninguna"):
            restriccion = "margen mínimo"
        elif limite_superior - p_opt < tol:
            restriccion = "margen máximo"

    p_rec, en_rango = redondeo_peruano_en_rango(p_opt, limite_inferior, limite_superior)
    if not en_rango:
        adv.append("El rango permitido es muy estrecho: no existe un precio XX.X9 dentro; "
                   "se muestra el precio sin redondear.")

    d = float(demanda(p_rec, d_base, kappa, p_mercado))
    u = (p_rec - costo) * d
    return {
        "ok": True,
        "precio_exacto": p_opt,
        "precio_recomendado": p_rec,
        "margen_pct": (p_rec - costo) / costo,
        "demanda_diaria": d,
        "utilidad_diaria": u,
        "utilidad_horizonte": u * horizonte,
        "limite_inferior": limite_inferior,
        "limite_superior": limite_superior,
        "precio_margen_min": costo * (1 + margen_min),
        "precio_margen_max": costo * (1 + margen_max),
        "restriccion_activa": restriccion,
        "horizonte": horizonte,
        "advertencias": adv,
    }


def curva_utilidad(costo, d_base, kappa, p_mercado, puntos=200):
    """Precios y utilidades diarias para graficar (de c·0.98 a c·1.22)."""
    precios = np.linspace(costo * 0.98, costo * 1.22, puntos)
    return precios, utilidad_diaria(precios, costo, d_base, kappa, p_mercado)


def tabla_sensibilidad(p_opt, costo, d_base, kappa, p_mercado, horizonte, lim_inf, lim_sup):
    """Qué pasa con la utilidad si el precio se mueve ±5 % y ±10 % del óptimo."""
    u_opt = float(utilidad_diaria(p_opt, costo, d_base, kappa, p_mercado))
    filas = []
    for v in VARIACIONES_SENSIBILIDAD:
        p = p_opt * (1 + v)
        d = float(demanda(p, d_base, kappa, p_mercado))
        u = (p - costo) * d
        filas.append({
            "variacion": v, "precio": p, "margen_pct": (p - costo) / costo,
            "demanda": d, "utilidad_diaria": u, "utilidad_horizonte": u * horizonte,
            "dif_vs_optimo": u - u_opt,
            "permitido": lim_inf - 1e-6 <= p <= lim_sup + 1e-6,
        })
    return filas


def escenarios_kappa(costo, d_base, p_mercado, margen_min, margen_max, horizonte,
                     stock, capacidad, kappas=ESCENARIOS_KAPPA):
    """Precio óptimo para distintos supuestos de elasticidad."""
    filas = []
    for k in kappas:
        r = optimizar_precio(costo, d_base, p_mercado, k, margen_min, margen_max,
                             horizonte, stock, capacidad)
        if r["ok"]:
            filas.append({"kappa": k, "precio": r["precio_recomendado"],
                          "margen_pct": r["margen_pct"], "demanda": r["demanda_diaria"],
                          "utilidad_diaria": r["utilidad_diaria"]})
    return filas


def comparar_politicas(resultado, costo, d_base, kappa, p_mercado, margen_fijo=0.08):
    """Política A (costo + margen fijo) vs Política B (precio óptimo)."""
    p_a = redondeo_peruano(costo * (1 + margen_fijo))
    d_a = float(demanda(p_a, d_base, kappa, p_mercado))
    u_a = (p_a - costo) * d_a
    u_b = resultado["utilidad_diaria"]
    return {
        "A": {"nombre": f"Costo FIFO + margen fijo {margen_fijo*100:.0f}%", "precio": p_a,
              "demanda": d_a, "utilidad_diaria": u_a},
        "B": {"nombre": "Precio óptimo del modelo", "precio": resultado["precio_recomendado"],
              "demanda": resultado["demanda_diaria"], "utilidad_diaria": u_b},
        "diferencia": u_b - u_a,
        "diferencia_pct": (u_b - u_a) / u_a if u_a > 0 else None,
    }
