"""
Validación de los dos modelos contra la "verdad oculta" (uso para el artículo).

No es un modelo nuevo: reutiliza Croston TSB (Modelo 1) y el precio óptimo
(Modelo 2) y mide qué tan bien habrían funcionado en los 6 meses simulados.

1) backtest_croston: backtest rolling-origin del intervalo y la magnitud de
   cada cambio de precio del proveedor (una fila por cambio).
2) simular_politicas: simula día a día dos políticas de precio con su propio
   tanque FIFO, las mismas cisternas y la misma demanda logística:
      Política A = costo FIFO × (1 + 8 %) redondeado a XX.X9
      Política B = precio óptimo del Modelo 2 (se recalcula cada vez que
                   cambia el costo FIFO o el precio de mercado)
"""
import math

import numpy as np
import pandas as pd

from modelos import modelo_croston, modelo_precio_optimo
from modelos.inventario_fifo import ErrorInventario, TanqueFIFO
from utilidades.helpers import redondeo_peruano


# ======================================================== MODELO 1: backtest
def backtest_croston(serie, alfa, beta, optimizar=True):
    """
    Backtest rolling-origin de Croston TSB sobre la serie diaria de precios.

    Para cada cambio k (a partir del tercero), el modelo pronostica usando
    SOLO los cambios anteriores y se compara con lo que realmente pasó.
    Devuelve (detalle DataFrame, alfa usado, beta usado, eventos).
    """
    eventos = modelo_croston.extraer_eventos(serie)
    columnas = ["n_cambio", "fecha_real", "intervalo_real", "intervalo_pronosticado",
                "intervalo_naive", "error", "magnitud_real", "magnitud_pronosticada",
                "error_magnitud", "cambio_real"]
    if len(eventos) < modelo_croston.MIN_ORIGEN + 2:
        return pd.DataFrame(columns=columnas), alfa, beta, eventos

    intervalos = eventos["intervalo"].dropna().tolist()   # intervalos[k] -> evento k+1
    magnitudes = eventos["magnitud"].tolist()
    if optimizar:
        alfa = modelo_croston.optimizar_parametro(magnitudes, alfa)
        beta = modelo_croston.optimizar_parametro(intervalos, beta)
    pron_int, _ = modelo_croston.suavizar(intervalos, beta)
    pron_mag, _ = modelo_croston.suavizar(magnitudes, alfa)

    filas = []
    for k in range(modelo_croston.MIN_ORIGEN, len(intervalos)):
        e = eventos.iloc[k + 1]
        real, pred = float(intervalos[k]), float(pron_int[k])
        m_real, m_pred = float(magnitudes[k + 1]), float(pron_mag[k + 1])
        filas.append([k + 2, e["fecha"], real, pred, float(np.mean(intervalos[:k])),
                      pred - real, m_real, m_pred, m_pred - m_real, float(e["cambio"])])
    return pd.DataFrame(filas, columns=columnas), alfa, beta, eventos


def metricas_backtest(detalle):
    """MAE, RMSE, MAPE, MAE magnitud, % dentro de ±2 días, baseline y mejora."""
    if detalle is None or detalle.empty:
        return None
    err = (detalle["intervalo_pronosticado"] - detalle["intervalo_real"]).abs()
    err_naive = (detalle["intervalo_naive"] - detalle["intervalo_real"]).abs()
    mae, mae_naive = float(err.mean()), float(err_naive.mean())
    return {
        "n_evaluados": len(detalle),
        "intervalo_medio_real": float(detalle["intervalo_real"].mean()),
        "mae": mae,
        "rmse": float(math.sqrt((err ** 2).mean())),
        "mape": float((err / detalle["intervalo_real"]).mean() * 100),
        "mae_magnitud": float(detalle["error_magnitud"].abs().mean()),
        "pct_dentro_2": float((err <= 2).mean() * 100),
        "mae_naive": mae_naive,
        "mejora_pct": (mae_naive - mae) / mae_naive * 100 if mae_naive > 0 else 0.0,
        "anticipacion": float(np.minimum(detalle["intervalo_pronosticado"],
                                         detalle["intervalo_real"]).mean()),
    }


# ================================================== MODELO 2: simulación
def _serie_diaria(df, dias, columna="precio"):
    """Serie diaria (rellena hacia adelante y hacia atrás) sobre el rango 'dias'."""
    if df is None or df.empty:
        return None
    s = df.sort_values("fecha").set_index("fecha")[columna].astype(float)
    s.index = pd.to_datetime(s.index).normalize()
    s = s.groupby(level=0).last()
    return s.reindex(s.index.union(dias)).ffill().bfill().reindex(dias)


def simular_politicas(sistema, producto):
    """
    Simula los días del historial con las dos políticas para un producto.

    Devuelve (DataFrame diario con ambas políticas, dict de supuestos usados)
    o (None, supuestos) si faltan datos.
    """
    cfg = sistema.config
    datos = sistema.datos
    sup = {"producto": producto, "advertencias": []}

    ventas = datos["ventas"][datos["ventas"]["producto"] == producto]
    if ventas.empty:
        sup["advertencias"].append("No hay ventas para definir el período de simulación.")
        return None, sup
    dias = pd.date_range(ventas["fecha"].min().normalize(), ventas["fecha"].max().normalize())

    # --- precio de mercado diario (referencia de la demanda logística)
    pm = _serie_diaria(datos["precio_mercado"][datos["precio_mercado"]["producto"] == producto], dias)
    sup["fuente_mercado"] = "Precio_mercado_diario (verdad oculta)"
    if pm is None:
        pm = _serie_diaria(datos["precios_surtidor"][datos["precios_surtidor"]["producto"] == producto], dias)
        sup["fuente_mercado"] = "precio del surtidor (aproximación)"
        sup["advertencias"].append("No se cargó el precio de mercado de la verdad oculta: se usa el "
                                   "precio del surtidor como referencia de mercado.")
    if pm is None:
        sup["advertencias"].append("No hay precios de mercado ni del surtidor.")
        return None, sup

    # --- demanda base y elasticidad
    from datos.gestor_datos import parametro_sim  # import local para evitar ciclo
    d_base = parametro_sim(sistema.parametros_simulacion, "demanda", producto)
    sup["fuente_demanda"] = "Parametros (verdad oculta)"
    if d_base is None:
        perd = datos["ventas_perdidas"]
        perd = perd[perd["producto"] == producto]["volumen"].sum()
        d_base = (ventas["volumen"].sum() + perd) / len(dias)
        sup["fuente_demanda"] = "promedio histórico (ventas + ventas perdidas) / días"
    kappa = cfg["kappa"][producto]
    sup.update({"d_base": d_base, "kappa": kappa, "dias": len(dias),
                "inicio": dias[0], "fin": dias[-1]})

    # --- stock inicial y cisternas
    cap = cfg["capacidad_tanque"][producto]
    inv = datos["inventario_inicial"]
    inv = inv[inv["producto"] == producto].sort_values("fecha")
    compras = datos["compras"][datos["compras"]["producto"] == producto].copy()
    compras["dia"] = compras["fecha_llegada"].dt.normalize()
    compras["dia_pedido"] = compras["fecha_pedido"].fillna(compras["fecha_llegada"]).dt.normalize()
    if not inv.empty:
        f0 = inv.iloc[0]
        d0 = pd.Timestamp(f0["fecha"]).normalize()
        vend0 = ventas[ventas["fecha"].dt.normalize() == d0]["volumen"].sum()
        comp0 = compras[compras["dia"] == d0]["volumen"].sum()
        stock0 = max(float(f0["stock"]) + vend0 - comp0, 0.0)
        costo0 = float(f0["costo"])
    else:
        stock0, costo0 = 0.0, (float(compras["costo_galon"].iloc[0]) if len(compras) else 0.0)
        sup["advertencias"].append("Sin inventario inicial: la simulación empieza con el tanque vacío.")
    llegadas = compras.groupby("dia")[["volumen", "costo_galon"]].apply(
        lambda g: list(zip(g["volumen"], g["costo_galon"]))).to_dict()

    mmin, mmax = cfg["margen_minimo"], cfg["margen_maximo"]
    m_fijo = cfg.get("margen_politica_fija", 0.08)
    horizonte = cfg["horizonte_dias"]
    filas = []
    for politica in ("A", "B"):
        t = TanqueFIFO(producto, cap, guardar_historial=False)
        if stock0 > 0:
            t.agregar_cisterna(dias[0], min(stock0, cap), costo0, "inventario inicial")
        ultimo_costo = costo0
        precio_b, clave_b = None, None
        for dia in dias:
            no_recibido = 0.0
            for vol, costo in llegadas.get(dia, []):
                libre = cap - t.stock_actual()
                entra = min(vol, libre)
                if entra > 0:
                    t.agregar_cisterna(dia, entra, costo)
                no_recibido += vol - max(entra, 0)
                ultimo_costo = costo
            c = t.costo_promedio_actual() or ultimo_costo
            p_merc = float(pm.loc[dia])
            if politica == "A":
                precio = redondeo_peruano(c * (1 + m_fijo))
            else:
                clave = (round(c, 3), round(p_merc, 2), round(t.stock_actual(), -1) if
                         t.stock_actual() < cap * 0.3 else 0)
                if clave != clave_b:
                    prox = compras[(compras["dia"] > dia) & (compras["dia_pedido"] <= dia)]
                    T = (prox["dia"].min() - dia).days if len(prox) else horizonte
                    T = float(max(1, min(T, horizonte)))
                    r = modelo_precio_optimo.optimizar_precio(
                        c, d_base, p_merc, kappa, mmin, mmax, T, t.stock_actual(), cap)
                    precio_b = r["precio_recomendado"] if r["ok"] else redondeo_peruano(c * (1 + m_fijo))
                    clave_b = clave
                precio = precio_b
            dem = float(modelo_precio_optimo.demanda(precio, d_base, kappa, p_merc))
            vendido = min(dem, t.stock_actual())
            costo_v = c
            if vendido > 1e-6:
                try:
                    costo_v = t.registrar_venta(dia, vendido, precio)["costo_promedio"]
                except ErrorInventario:
                    vendido = 0.0
            perdido = max(dem - vendido, 0.0)
            filas.append({
                "fecha": dia, "producto": producto, "politica": politica,
                "precio": precio, "costo_fifo": costo_v, "precio_mercado": p_merc,
                "demanda": dem, "vendido": vendido, "perdido": perdido,
                "ingreso": precio * vendido, "costo_total": costo_v * vendido,
                "utilidad": (precio - costo_v) * vendido,
                "margen_pct": (precio - costo_v) / costo_v if costo_v > 0 else np.nan,
                "stock_final": t.stock_actual(), "quiebre": perdido > 1e-6,
                "no_recibido": no_recibido,
            })
    return pd.DataFrame(filas), sup


def resumen_politicas(diario, margen_minimo=0.05):
    """Indicadores de 6 meses por producto y política."""
    res = {}
    for (prod, pol), g in diario.groupby(["producto", "politica"]):
        vend = g["vendido"].sum()
        res[(prod, pol)] = {
            "precio_promedio": float((g["precio"] * g["vendido"]).sum() / vend) if vend else float(g["precio"].mean()),
            "demanda_total": float(vend),
            "ingreso_total": float(g["ingreso"].sum()),
            "costo_total": float(g["costo_total"].sum()),
            "utilidad_total": float(g["utilidad"].sum()),
            "margen_promedio": float(g["utilidad"].sum() / g["costo_total"].sum()) if g["costo_total"].sum() else 0.0,
            "dias_margen_bajo": int((g["margen_pct"] < margen_minimo - 1e-4).sum()),
            "dias_quiebre": int(g["quiebre"].sum()),
            "galones_perdidos": float(g["perdido"].sum()),
        }
    return res
