"""
Tablas para el artículo científico.

calcular_resultados(sistema) ejecuta TODO lo necesario (estadísticas,
backtest del Modelo 1, simulación del Modelo 2, sensibilidad) y lo guarda
en caché. construir_tablas() arma las 8 tablas con título, notas,
fuente e interpretación; exportar_tablas() las escribe en
TABLAS_PARA_ARTICULO.xlsx con formato académico.
"""
import math
import os
from collections import OrderedDict

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter

from configuracion import PRODUCTOS
from modelos import modelo_croston, modelo_precio_optimo, validacion
from utilidades.helpers import redondeo_peruano

FUENTE_TABLA = "Fuente: Elaboración propia."
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


# ----------------------------------------------------------------- formatos
def soles(v):
    return "—" if v is None or (isinstance(v, float) and not math.isfinite(v)) else f"{v:,.2f}"


def pct(v):
    """v ya en porcentaje (8.3 -> '8.3%')."""
    return "—" if v is None or (isinstance(v, float) and not math.isfinite(v)) else f"{v:.1f}%"


def entero(v):
    return "—" if v is None or (isinstance(v, float) and not math.isfinite(v)) else f"{v:,.0f}"


def dec1(v):
    return "—" if v is None or (isinstance(v, float) and not math.isfinite(v)) else f"{v:,.1f}"


def _signo(v, fmt=soles):
    return ("+" if v >= 0 else "−") + fmt(abs(v))


def _signo_soles(v):
    """+S/ 1,234.56 o −S/ 1,234.56"""
    return ("+" if v >= 0 else "−") + "S/ " + soles(abs(v))


# ======================================================= cálculo central
def calcular_resultados(sistema, progreso=None):
    """
    Calcula todos los resultados del artículo (con caché en el sistema).
    progreso: función opcional (fracción, texto) para la barra de progreso.
    """
    if getattr(sistema, "_cache_articulo", None) is not None:
        return sistema._cache_articulo
    avisar = progreso or (lambda f, t: None)
    cfg = sistema.config
    r = {"config": cfg, "advertencias": [], "productos": {}}

    for i, p in enumerate(PRODUCTOS):
        avisar(0.05 + 0.25 * i / 3, f"Backtest Croston TSB — {p}")
        serie, fuente = sistema.serie_precio_proveedor(p)
        det, a, b, eventos = validacion.backtest_croston(
            serie, cfg["croston_alfa_inicial"], cfg["croston_beta_inicial"])
        pron = sistema.pronostico(p)
        avisar(0.30 + 0.25 * i / 3, f"Simulación de políticas (6 meses) — {p}")
        diario, sup = validacion.simular_politicas(sistema, p)
        precio = sistema.precio_optimo(p)
        r["productos"][p] = {
            "serie": serie, "fuente_serie": fuente, "eventos": eventos, "backtest": det,
            "alfa": a, "beta": b, "metricas": validacion.metricas_backtest(det),
            "pronostico": pron, "simulacion": diario, "supuestos": sup, "precio": precio,
        }
        if fuente.startswith("costos"):
            r["advertencias"].append(f"{p}: no se cargó la lista de precios del proveedor; el Modelo 1 "
                                     "usa los costos de las cisternas como aproximación.")
        r["advertencias"] += [f"{p}: {t}" for t in sup.get("advertencias", [])]

    avisar(0.60, "Consolidando resultados")
    sims = [d["simulacion"] for d in r["productos"].values() if d["simulacion"] is not None]
    r["simulacion"] = pd.concat(sims, ignore_index=True) if sims else pd.DataFrame()
    r["resumen_politicas"] = (validacion.resumen_politicas(r["simulacion"], cfg["margen_minimo"])
                              if len(r["simulacion"]) else {})
    dets = [d["backtest"].assign(producto=p) for p, d in r["productos"].items() if len(d["backtest"])]
    r["backtest"] = pd.concat(dets, ignore_index=True) if dets else pd.DataFrame()
    r["metricas_total"] = validacion.metricas_backtest(r["backtest"])
    sistema._cache_articulo = r
    return r


# ===================================================== construcción tablas
def _tabla(titulo, df, notas, interpretacion):
    return {"titulo": titulo, "df": df, "notas": notas, "interpretacion": interpretacion}


def tabla_descriptiva(sistema, r):
    """Hoja 1: estadísticas que demuestran que el problema existe."""
    v = sistema.ventas_procesadas
    vr = sistema.datos["ventas"]
    comp = sistema.datos["compras"]
    perd = sistema.datos["ventas_perdidas"]
    if vr.empty:
        return _tabla("Estadísticas descriptivas", pd.DataFrame({"Indicador": ["Sin datos"]}), [], "")
    ini, fin = vr["fecha"].min(), vr["fecha"].max()
    periodo = f"{MESES[ini.month-1]}-{MESES[fin.month-1]} {fin.year} ({(fin.normalize()-ini.normalize()).days+1} días)"

    col, tot = {}, {}
    acum = {"tx": 0, "vol": 0, "ing": 0, "dem": [], "cis": 0, "camb": 0, "ints": [],
            "q": 0, "gal": 0}
    for p in PRODUCTOS:
        vp = vr[vr["producto"] == p]
        diaria = vp.set_index("fecha")["volumen"].resample("D").sum()
        cp = comp[comp["producto"] == p].sort_values("fecha_llegada")
        ev = r["productos"][p]["eventos"]
        ints = ev["intervalo"].dropna()
        if len(perd):
            pp = perd[(perd["producto"] == p) & (perd["volumen"] > 0)]
            dias_q, gal_q = pp["fecha"].dt.normalize().nunique(), pp["volumen"].sum()
        else:
            rr = sistema.ventas_rechazadas
            rr = rr[rr["producto"] == p]
            dias_q, gal_q = rr["fecha"].dt.normalize().nunique() if len(rr) else 0, rr["volumen"].sum()
        ing = float((vp["volumen"] * vp["precio"]).sum())
        var = cp["costo_galon"].diff().abs().max() if len(cp) > 1 else float("nan")
        col[p] = [periodo if p == PRODUCTOS[0] else "", entero(len(vp)), entero(vp["volumen"].sum()),
                  soles(ing), dec1(diaria.mean()), pct(diaria.std() / diaria.mean() * 100 if diaria.mean() else None),
                  entero(len(cp)), entero(len(ev)), dec1(ints.mean() if len(ints) else None),
                  dec1(ints.min() if len(ints) else None), dec1(ints.max() if len(ints) else None),
                  dec1(ints.std() if len(ints) > 1 else None),
                  f"{cp['costo_galon'].min():.2f}–{cp['costo_galon'].max():.2f}" if len(cp) else "—",
                  soles(var), entero(dias_q), entero(gal_q)]
        acum["tx"] += len(vp); acum["vol"] += vp["volumen"].sum(); acum["ing"] += ing
        acum["dem"].append(diaria); acum["cis"] += len(cp); acum["camb"] += len(ev)
        acum["ints"] += ints.tolist(); acum["q"] += dias_q; acum["gal"] += gal_q
    total_d = pd.concat(acum["dem"], axis=1).fillna(0).sum(axis=1)
    col["Total"] = ["", entero(acum["tx"]), entero(acum["vol"]), soles(acum["ing"]), dec1(total_d.mean()),
                    pct(total_d.std() / total_d.mean() * 100 if total_d.mean() else None),
                    entero(acum["cis"]), entero(acum["camb"]),
                    dec1(np.mean(acum["ints"]) if acum["ints"] else None), "—", "—", "—",
                    f"{comp['costo_galon'].min():.2f}–{comp['costo_galon'].max():.2f}" if len(comp) else "—",
                    "—", entero(acum["q"]), entero(acum["gal"])]
    indicadores = ["Período analizado", "Total ventas (transacciones)", "Volumen total vendido (gal)",
                   "Ingreso total (S/)", "Demanda diaria promedio (gal)", "CV de demanda diaria (%)",
                   "N° de cisternas recibidas", "N° de cambios de precio proveedor",
                   "Intervalo medio entre cambios (días)", "Intervalo mínimo (días)",
                   "Intervalo máximo (días)", "Desv. estándar del intervalo (días)",
                   "Rango de costos de compra (S//gal)", "Variación máxima de costo entre cisternas (S//gal)",
                   "Días con quiebre de stock", "Galones perdidos por quiebre"]
    df = pd.DataFrame({"Indicador": indicadores, **col})

    ints_all = acum["ints"]
    cv_int = (np.std(ints_all) / np.mean(ints_all) * 100) if ints_all else 0
    fuente_q = "Ventas_perdidas (verdad oculta)" if len(perd) else "ventas rechazadas por falta de stock"
    interp = (f"Durante el período analizado el proveedor cambió su precio {acum['camb']} veces en total. "
              f"El intervalo entre cambios fue en promedio de {dec1(np.mean(ints_all) if ints_all else None)} "
              f"días, con un coeficiente de variación de {cv_int:.1f}%: los cambios son irregulares y no "
              "pueden anticiparse con una regla fija. Además, el grifo recibió "
              f"{acum['cis']} cisternas a costos distintos, por lo que en el tanque conviven capas con costos "
              f"diferentes y el administrador no conoce su costo real de venta sin un sistema FIFO. Se "
              f"registraron {entero(acum['q'])} días-producto con quiebre de stock y "
              f"{entero(acum['gal'])} galones de venta perdida.")
    notas = ["DB5 = Diésel B5; GR = Gasolina Regular 90; GP = Gasolina Premium 95.",
             "CV = coeficiente de variación (desviación estándar / media).",
             "Cambios de precio detectados en la serie diaria del precio de lista del proveedor.",
             f"Quiebres de stock según {fuente_q}."]
    return _tabla("Estadísticas descriptivas del problema", df, notas, interp)


def tabla_parametros(sistema, r):
    """Hoja 2: parámetros y configuración de ambos modelos (metodología)."""
    cfg = r["config"]
    alfas = [d["alfa"] for d in r["productos"].values()]
    betas = [d["beta"] for d in r["productos"].values()]
    fmt_par = lambda xs: " / ".join(f"{x:.2f}" for x in xs) + " (DB5/GR/GP, optimizado)"
    filas = [
        ["Suavizado tamaño del cambio (Croston TSB)", "α", fmt_par(alfas),
         "Búsqueda en malla [0.05, 0.30] que minimiza el MAE en backtest rolling-origin"],
        ["Suavizado intervalo entre cambios (Croston TSB)", "β", fmt_par(betas),
         "Búsqueda en malla [0.05, 0.30] que minimiza el MAE en backtest rolling-origin"],
        ["Corrección de sesgo TSB", "1 − β/2", "—", "y_t = (1 − β/2)·z_t / p_t (Teunter, Syntetos y Babai)"],
    ]
    for p in PRODUCTOS:
        filas.append([f"Elasticidad {p}", f"κ_{p}", f"{cfg['kappa'][p]}",
                      "Supuesto basado en literatura de combustibles"])
    filas += [["Margen mínimo", "m_min", pct(cfg["margen_minimo"] * 100), "Restricción de negocio"],
              ["Margen máximo", "m_max", pct(cfg["margen_maximo"] * 100), "Restricción de negocio"],
              ["Margen fijo (Política A)", "m_A", pct(cfg.get("margen_politica_fija", 0.08) * 100),
               "Práctica habitual de un grifo (referencia)"]]
    for p in PRODUCTOS:
        filas.append([f"Capacidad tanque {p}", f"Cap_{p}", f"{cfg['capacidad_tanque'][p]:,.0f} gal",
                      "Dato del grifo"])
    filas.append(["Horizonte de planificación", "T", f"{cfg['horizonte_dias']} días (máx.)",
                  "Días hasta la próxima cisterna pedida, con tope en T"])
    for p in PRODUCTOS:
        sup = r["productos"][p]["supuestos"]
        if "d_base" in sup:
            filas.append([f"Demanda base {p}", f"D_{p}", f"{sup['d_base']:,.1f} gal/día", sup["fuente_demanda"]])
    filas.append(["Precio de mercado", "p_mercado", "Serie diaria",
                  r["productos"][PRODUCTOS[0]]["supuestos"].get("fuente_mercado", "—")])
    filas.append(["Método de optimización", "—", "Búsqueda de sección dorada",
                  "Maximización en el intervalo factible; restricción de stock resuelta por bisección"])
    df = pd.DataFrame(filas, columns=["Parámetro", "Símbolo", "Valor", "Justificación"])
    interp = ("El Modelo 1 (Croston TSB) se calibró por producto eligiendo α y β que minimizan el error "
              "absoluto medio en un backtest rolling-origin. El Modelo 2 maximiza U(p) = (p − c)·D(p)·T con "
              "demanda logística D(p) = D_base·2/(1 + exp(κ(p/p_mercado − 1))), sujeto a márgenes mínimo y "
              "máximo y a no vender más que el stock disponible en el horizonte.")
    notas = ["c = costo promedio ponderado FIFO del inventario.",
             "Los valores de κ son supuestos; su efecto se analiza en la hoja Sensibilidad_Elasticidad."]
    return _tabla("Parámetros y configuración de los modelos", df, notas, interp)


def tabla_modelo1(r):
    """Hoja 3: desempeño del Croston TSB (backtest rolling-origin)."""
    filas = []
    for p in PRODUCTOS + ["Consolidado"]:
        if p == "Consolidado":
            m = r["metricas_total"]
            n = sum(len(d["eventos"]) for d in r["productos"].values())
        else:
            m = r["productos"][p]["metricas"]
            n = len(r["productos"][p]["eventos"])
        conf = modelo_croston.nivel_confianza(n if p != "Consolidado" else
                                              min(len(d["eventos"]) for d in r["productos"].values()))
        if m is None:
            filas.append([p, n] + ["—"] * 9 + [conf])
            continue
        filas.append([p, n, m["n_evaluados"], dec1(m["intervalo_medio_real"]), dec1(m["mae"]),
                      dec1(m["mae_naive"]), pct(m["mejora_pct"]), dec1(m["rmse"]), pct(m["mape"]),
                      soles(m["mae_magnitud"]), pct(m["pct_dentro_2"]), conf])
    df = pd.DataFrame(filas, columns=[
        "Producto", "N° cambios", "N° pronósticos evaluados", "Intervalo medio real (días)",
        "MAE modelo (días)", "MAE baseline (días)", "Mejora (%)", "RMSE (días)", "MAPE (%)",
        "MAE magnitud (S//gal)", "% dentro ±2 días", "Confianza"])
    m = r["metricas_total"]
    if m:
        mejor = "una mejora" if m["mejora_pct"] >= 0 else "un desempeño inferior"
        interp = (f"El Modelo Croston TSB pronostica el intervalo entre cambios de precio con un error "
                  f"promedio de {dec1(m['mae'])} días, lo que representa {mejor} del "
                  f"{abs(m['mejora_pct']):.1f}% respecto al pronóstico naive (promedio simple, MAE = "
                  f"{dec1(m['mae_naive'])} días). El {m['pct_dentro_2']:.1f}% de los pronósticos cae dentro de "
                  f"±2 días del cambio real. En promedio, el administrador conoce con "
                  f"{dec1(m['anticipacion'])} días de anticipación la fecha aproximada del próximo cambio.")
        if m["mejora_pct"] < 0:
            interp += (" Advertencia: el modelo no supera al promedio simple en estos datos; los resultados "
                       "deben reportarse con esta limitación.")
    else:
        interp = "No hay suficientes cambios de precio para validar el modelo."
    notas = ["MAE = error absoluto medio; RMSE = raíz del error cuadrático medio; MAPE = error porcentual "
             "absoluto medio.",
             "Baseline naive = promedio simple de todos los intervalos anteriores.",
             "Mejora = (MAE baseline − MAE modelo) / MAE baseline × 100.",
             "Confianza: BAJA < 8 cambios; MEDIA 8–15; ALTA > 15.",
             "Rolling-origin: cada pronóstico usa solo los cambios ocurridos antes de él."]
    return _tabla("Desempeño del Modelo Croston TSB (backtest rolling-origin)", df, notas, interp)


def tabla_modelo2(r):
    """Hoja 4: comparación de políticas de precio durante los 6 meses."""
    res = r["resumen_politicas"]
    if not res:
        return _tabla("Comparación de políticas de precios", pd.DataFrame({"Indicador": ["Sin datos"]}), [], "")
    nombres = [("precio_promedio", "Precio promedio (S//gal)", soles),
               ("demanda_total", "Demanda atendida total (gal)", entero),
               ("ingreso_total", "Ingreso total (S/)", soles),
               ("costo_total", "Costo total (S/)", soles),
               ("utilidad_total", "Utilidad total (S/)", soles),
               ("margen_promedio", "Margen promedio (%)", lambda v: pct(v * 100)),
               ("dias_margen_bajo", "Días con margen < mínimo", entero),
               ("dias_quiebre", "Días de quiebre de stock", entero),
               ("galones_perdidos", "Galones no vendidos por quiebre", entero)]
    datos = {"Indicador": [n for _, n, _ in nombres] + ["Diferencia utilidad (B − A)"]}
    total = {"A": 0.0, "B": 0.0}
    for p in PRODUCTOS:
        for pol in ("A", "B"):
            m = res.get((p, pol))
            col = f"{p} Pol.{pol}"
            if m is None:
                datos[col] = ["—"] * (len(nombres) + 1)
                continue
            datos[col] = [f(m[k]) for k, _, f in nombres]
            total[pol] += m["utilidad_total"]
            if pol == "A":
                datos[col].append("—")
            else:
                ua = res[(p, "A")]["utilidad_total"]
                dif = m["utilidad_total"] - ua
                datos[col].append(f"{_signo(dif)} ({_signo(dif / ua * 100 if ua else 0, dec1)}%)")
    df = pd.DataFrame(datos)
    dif = total["B"] - total["A"]
    dif_pct = dif / total["A"] * 100 if total["A"] else 0
    q_a = sum(res[(p, "A")]["dias_quiebre"] for p in PRODUCTOS if (p, "A") in res)
    q_b = sum(res[(p, "B")]["dias_quiebre"] for p in PRODUCTOS if (p, "B") in res)
    va = sum(res[(p, "A")]["demanda_total"] for p in PRODUCTOS if (p, "A") in res)
    vb = sum(res[(p, "B")]["demanda_total"] for p in PRODUCTOS if (p, "B") in res)
    interp = (f"En la simulación de {r['productos'][PRODUCTOS[0]]['supuestos'].get('dias', '—')} días, la "
              f"política de precio óptimo (B) obtiene una utilidad total de S/ {soles(total['B'])} frente a "
              f"S/ {soles(total['A'])} de la política de margen fijo (A), una diferencia de "
              f"{_signo(dif)} soles ({_signo(dif_pct, dec1)}%). Los días-producto con quiebre de stock pasan "
              f"de {q_a} a {q_b}. Ambas políticas usan las mismas cisternas, el mismo costo FIFO y la misma "
              "función de demanda, por lo que la diferencia se debe solo a la regla de precio. "
              f"La política B vende {abs(vb - va) / va * 100 if va else 0:.1f}% "
              f"{'menos' if vb < va else 'más'} galones ({entero(vb)} vs {entero(va)}): "
              "gana por margen, no por volumen, lo que puede afectar la participación de mercado.")
    notas = ["Pol.A = costo FIFO × 1.08 redondeado a XX.X9; Pol.B = precio óptimo del Modelo 2.",
             "Demanda simulada con la función logística y el precio de mercado diario.",
             "Cada política tiene su propio tanque FIFO; las cisternas que no caben se reciben parcialmente."]
    return _tabla("Comparación de políticas de precios (6 meses simulados)", df, notas, interp)


def tabla_kappa(r):
    """Hoja 5: precio óptimo y utilidad para distintos κ."""
    filas = {k: [k] for k in modelo_precio_optimo.ESCENARIOS_KAPPA}
    for p in PRODUCTOS:
        pr = r["productos"][p]["precio"]
        esc = {e["kappa"]: e for e in pr.get("escenarios", [])} if pr.get("ok") else {}
        for k in filas:
            e = esc.get(k)
            filas[k] += [soles(e["precio"]) if e else "—", soles(e["utilidad_diaria"]) if e else "—"]
    cols = ["κ"] + [c for p in PRODUCTOS for c in (f"Precio óptimo {p} (S//gal)", f"Utilidad diaria {p} (S/)")]
    df = pd.DataFrame(list(filas.values()), columns=cols)
    partes = []
    for p in PRODUCTOS:
        pr = r["productos"][p]["precio"]
        if pr.get("ok") and pr.get("escenarios"):
            ps = [e["precio"] for e in pr["escenarios"]]
            partes.append(f"{p}: entre S/ {min(ps):.2f} y S/ {max(ps):.2f}")
    interp = ("Al variar la elasticidad κ entre 15 y 25, el precio óptimo recomendado se mueve "
              + "; ".join(partes) + ". Cuanto más sensibles son los clientes al precio (κ alto), menor es el "
              "precio óptimo. Si el rango es estrecho, la recomendación es robusta frente a la incertidumbre "
              "sobre κ.") if partes else "Sin datos suficientes."
    notas = ["Calculado con el costo FIFO, stock y precio de mercado del último día disponible.",
             "Utilidad diaria = (p − c)·D(p)."]
    return _tabla("Sensibilidad del precio óptimo a la elasticidad (κ)", df, notas, interp)


def tabla_sensibilidad_precio(r):
    """Hoja 6: utilidad desde margen mínimo a máximo en pasos de 1 %."""
    cfg = r["config"]
    bloques = []
    for p in PRODUCTOS:
        pr = r["productos"][p]["precio"]
        if not pr.get("ok"):
            continue
        c, d0, k, pm = pr["costo"], pr["d_base"], pr["kappa"], pr["p_mercado"]
        u_opt = pr["utilidad_diaria"]
        limite = min(pr["stock"], pr["capacidad"])
        for m in np.arange(round(cfg["margen_minimo"] * 100), round(cfg["margen_maximo"] * 100) + 1):
            precio = redondeo_peruano(c * (1 + m / 100))
            dem = float(modelo_precio_optimo.demanda(precio, d0, k, pm))
            u = (precio - c) * dem
            bloques.append([p, f"{m:.0f}%", soles(precio), dec1(dem), soles(precio * dem), soles(c * dem),
                            soles(u), pct((u - u_opt) / u_opt * 100 if u_opt else 0),
                            "Sí" if dem * pr["horizonte"] <= limite + 1e-6 else "No (stock)"])
        bloques.append([p, "Óptimo", soles(pr["precio_recomendado"]), dec1(pr["demanda_diaria"]),
                        soles(pr["precio_recomendado"] * pr["demanda_diaria"]),
                        soles(c * pr["demanda_diaria"]), soles(u_opt), "0.0%",
                        f"Óptimo factible ({pr['restriccion_activa']})"])
    df = pd.DataFrame(bloques, columns=["Producto", "Margen (%)", "Precio (S/)", "Demanda estimada (gal/día)",
                                        "Ingreso diario (S/)", "Costo diario (S/)", "Utilidad diaria (S/)",
                                        "Diferencia vs óptimo (%)", "Factible"])
    interp = ("La tabla muestra cómo cambia la utilidad diaria al fijar el margen entre el mínimo y el máximo "
              "permitido. Márgenes por encima del óptimo reducen la demanda más de lo que aumenta la ganancia "
              "por galón; márgenes por debajo venden más galones pero con menos utilidad unitaria. Las filas «No "
              "(stock)» exigirían vender en el horizonte más galones de los que hay en el tanque, por eso el "
              "óptimo factible puede tener menor utilidad diaria que ellas.")
    notas = ["Precios redondeados a XX.X9.", "Diferencia vs óptimo = (U − U*) / U* × 100.",
             "Valores negativos indican pérdida de utilidad respecto al precio óptimo.",
             "Factible = cumple D(p)·T ≤ stock disponible."]
    return _tabla("Sensibilidad de la utilidad al precio de venta", df, notas, interp)


def tabla_resumen(sistema, r):
    """Hoja 7: indicadores de mejora para conclusiones."""
    res = r["resumen_politicas"]
    m = r["metricas_total"]
    ua = sum(res[(p, "A")]["utilidad_total"] for p in PRODUCTOS if (p, "A") in res)
    ub = sum(res[(p, "B")]["utilidad_total"] for p in PRODUCTOS if (p, "B") in res)
    qa = sum(res[(p, "A")]["dias_quiebre"] for p in PRODUCTOS if (p, "A") in res)
    qb = sum(res[(p, "B")]["dias_quiebre"] for p in PRODUCTOS if (p, "B") in res)
    ga = sum(res[(p, "A")]["galones_perdidos"] for p in PRODUCTOS if (p, "A") in res)
    gb = sum(res[(p, "B")]["galones_perdidos"] for p in PRODUCTOS if (p, "B") in res)
    perd = sistema.datos["ventas_perdidas"]
    v = sistema.ventas_procesadas
    precio_medio = float((v["precio"] * v["volumen"]).sum() / v["volumen"].sum()) if len(v) else 0
    costo_medio = float((v["costo_fifo"] * v["volumen"]).sum() / v["volumen"].sum()) if len(v) else 0
    gal_obs = float(perd["volumen"].sum()) if len(perd) else float(sistema.ventas_rechazadas["volumen"].sum())
    dias_obs = (perd[perd["volumen"] > 0]["fecha"].dt.normalize().nunique() if len(perd) else 0)
    dif = ub - ua
    filas = [
        ["Utilidad total Pol. A (6 meses)", f"S/ {soles(ua)}", "Con margen fijo del 8% sobre costo FIFO"],
        ["Utilidad total Pol. B (6 meses)", f"S/ {soles(ub)}", "Con precio óptimo del Modelo 2"],
        ["Diferencia de utilidad", f"{_signo(dif)} ({_signo(dif / ua * 100 if ua else 0, dec1)}%)",
         "Ganancia adicional atribuible al modelo" if dif >= 0 else "El modelo NO mejora la utilidad en estos datos"],
        ["Días de anticipación promedio", f"{dec1(m['anticipacion']) if m else '—'} días",
         "Días de aviso con que el Modelo 1 anticipa el próximo cambio"],
        ["Error promedio del pronóstico", f"{dec1(m['mae']) if m else '—'} días", "MAE del Modelo 1"],
        ["Mejora vs pronóstico naive", f"{_signo(m['mejora_pct'], dec1) if m else '—'}%",
         "Reducción del error respecto al promedio simple"],
        ["Quiebres de stock observados", f"{dias_obs} días-producto", "Según la verdad oculta (Ventas_perdidas)"],
        ["Quiebres de stock evitados (simulación)", f"{qa - qb} días-producto",
         f"Pol. A: {qa} días; Pol. B: {qb} días"],
        ["Volumen perdido observado", f"{entero(gal_obs)} gal (S/ {soles(gal_obs * (precio_medio - costo_medio))})",
         "Utilidad que se dejó de ganar (margen medio observado)"],
        ["Volumen perdido evitable (simulación)", f"{entero(max(ga - gb, 0))} gal",
         "Galones de quiebre que la Pol. B evita frente a la Pol. A"],
    ]
    df = pd.DataFrame(filas, columns=["Indicador", "Valor", "Interpretación"])
    interp = (f"Usando FIFO y los dos modelos, el administrador pasa de fijar precios a ciegas a una decisión "
              f"informada: la utilidad simulada cambia en {_signo(dif)} soles "
              f"({_signo(dif / ua * 100 if ua else 0, dec1)}%) en seis meses, y el Modelo 1 permite prever los "
              f"cambios del proveedor con un error medio de {dec1(m['mae']) if m else '—'} días.")
    notas = ["Días-producto: un día con quiebre en dos productos cuenta como 2.",
             "La simulación usa la demanda logística; los resultados dependen de los supuestos de κ."]
    return _tabla("Resumen ejecutivo de resultados", df, notas, interp)


def tabla_backtest_detallado(r):
    """Hoja 8: una fila por cambio de precio evaluado."""
    bt = r["backtest"]
    if bt.empty:
        return _tabla("Backtest detallado", pd.DataFrame({"Mensaje": ["Sin cambios suficientes"]}), [], "")
    df = pd.DataFrame({
        "N° cambio": bt["n_cambio"], "Producto": bt["producto"],
        "Fecha real": bt["fecha_real"].dt.strftime("%d/%m/%Y"),
        "Intervalo real (días)": bt["intervalo_real"].map(entero),
        "Intervalo pronosticado (días)": bt["intervalo_pronosticado"].map(dec1),
        "Error (días)": bt["error"].map(lambda x: _signo(x, dec1)),
        "Magnitud real (S/)": bt["magnitud_real"].map(soles),
        "Magnitud pronosticada (S/)": bt["magnitud_pronosticada"].map(soles),
        "Error magnitud (S/)": bt["error_magnitud"].map(lambda x: _signo(x)),
    })
    interp = ("Cada fila muestra lo que el modelo habría pronosticado justo después del cambio anterior, "
              "usando solo la información disponible en ese momento, frente a lo que realmente ocurrió.")
    notas = ["Error = pronosticado − real (positivo: el modelo esperaba el cambio más tarde).",
             "Los dos primeros cambios de cada producto se usan solo para inicializar el modelo."]
    return _tabla("Backtest detallado del Modelo 1", df, notas, interp)


# ============================================ las 5 tablas del artículo
FILAS_TABLA1 = ["Período analizado", "Ventas totales (transacciones)", "Volumen total vendido (gal)",
                "Ingreso total (S/)", "Demanda diaria promedio (gal/día)", "N° cisternas recibidas",
                "N° cambios de precio del proveedor", "Intervalo medio entre cambios (días)",
                "Desv. estándar del intervalo (días)", "Rango de costos de compra (S//gal)",
                "Variación máxima de costo en el período (S//gal)", "Días con quiebre de stock"]


def tabla1(sistema, r):
    """Tabla 1: estadísticas descriptivas (planteamiento del problema)."""
    base = tabla_descriptiva(sistema, r)
    df = base["df"]
    if "DB5" not in df.columns:
        return base
    renombre = {"Total ventas (transacciones)": "Ventas totales (transacciones)",
                "Demanda diaria promedio (gal)": "Demanda diaria promedio (gal/día)",
                "N° de cisternas recibidas": "N° cisternas recibidas",
                "N° de cambios de precio proveedor": "N° cambios de precio del proveedor"}
    df = df.assign(Indicador=df["Indicador"].replace(renombre))
    comp = sistema.datos["compras"]
    variaciones = {}
    for p in PRODUCTOS:
        cp = comp[comp["producto"] == p]["costo_galon"]
        variaciones[p] = float(cp.max() - cp.min()) if len(cp) else None
    fila_var = {"Indicador": FILAS_TABLA1[10], **{p: soles(variaciones[p]) for p in PRODUCTOS},
                "Total": soles(max([v for v in variaciones.values() if v is not None], default=None))}
    df = df[df["Indicador"].isin(FILAS_TABLA1)]
    df = pd.concat([df, pd.DataFrame([fila_var])], ignore_index=True)
    df = df.set_index("Indicador").reindex(FILAS_TABLA1).reset_index()

    ev = [r["productos"][p]["eventos"] for p in PRODUCTOS]
    n = sum(len(e) for e in ev)
    ints = pd.concat([e["intervalo"].dropna() for e in ev])
    var_max = max([v for v in variaciones.values() if v is not None], default=0)
    interp = (f"La tabla muestra que el precio del proveedor cambió {n} veces en el período analizado "
              f"con intervalos irregulares (promedio de {dec1(ints.mean() if len(ints) else None)} días y "
              f"desviación estándar de {dec1(ints.std() if len(ints) > 1 else None)} días), lo que confirma "
              "que el administrador no puede predecir los cambios con un patrón simple. La variación de "
              f"costos de hasta S/ {var_max:.2f} por galón significa que fijar un precio de venta sin conocer "
              "el costo real FIFO genera riesgo de pérdida.")
    notas = [x for x in base["notas"] if not x.startswith("CV")]
    notas.append("Variación máxima = costo de compra más alto − más bajo de las cisternas del período.")
    return _tabla("Estadísticas descriptivas del problema", df, notas, interp)


def tabla3(r):
    """Tabla 3: resultados del Modelo 1 (Croston TSB)."""
    base = tabla_modelo1(r)
    df = base["df"]
    if "MAE modelo (días)" not in df.columns:
        return base
    df = df[["Producto", "N° cambios", "Intervalo medio real (días)", "MAE modelo (días)",
             "MAE baseline (días)", "Mejora (%)", "% dentro ±2 días", "Confianza"]].copy()
    df.columns = ["Producto", "N° cambios observados", "Intervalo medio real (días)", "MAE modelo (días)",
                  "MAE baseline naive (días)", "Mejora vs baseline (%)", "% pronósticos dentro de ±2 días",
                  "Confianza"]
    df["Producto"] = df["Producto"].replace({"Consolidado": "Promedio"})
    m = r["metricas_total"]
    if m:
        palabra = "una mejora" if m["mejora_pct"] >= 0 else "un resultado peor"
        interp = (f"El modelo Croston TSB logra pronosticar el intervalo entre cambios de precio con un error "
                  f"promedio de {dec1(m['mae'])} días, lo que representa {palabra} del "
                  f"{abs(m['mejora_pct']):.1f}% respecto al método de simplemente usar el promedio histórico. "
                  f"En la práctica, esto significa que el administrador puede anticiparse al próximo cambio con "
                  f"{dec1(m['anticipacion'])} días de ventaja para preparar su estrategia de precios.")
        if m["mejora_pct"] < 0:
            interp += (" Advertencia: en estos datos el modelo no supera al promedio histórico; debe "
                       "reportarse como limitación.")
    else:
        interp = base["interpretacion"]
    notas = ["MAE = error absoluto medio (días entre el cambio pronosticado y el real).",
             "Baseline naive = promedio simple de todos los intervalos anteriores.",
             "Mejora vs baseline = (MAE baseline − MAE modelo) / MAE baseline × 100.",
             "Promedio = métricas calculadas con los pronósticos de los tres productos juntos.",
             "Confianza: BAJA < 8 cambios; MEDIA 8–15; ALTA > 15.",
             "Cada pronóstico usa solo los cambios ocurridos antes de él (validación rolling-origin)."]
    return _tabla("Resultados del Modelo 1: pronóstico de cambios de precio (Croston TSB)", df, notas, interp)


def tabla4(r):
    """Tabla 4: comparación margen fijo vs precio óptimo."""
    res = r["resumen_politicas"]
    if not res:
        return _tabla("Comparación de políticas de precios", pd.DataFrame({"Indicador": ["Sin datos"]}), [], "")
    cfg = r["config"]
    filas = [("precio_promedio", "Precio promedio (S//gal)", soles),
             ("demanda_total", "Demanda total (gal)", entero),
             ("ingreso_total", "Ingreso total (S/)", soles),
             ("utilidad_total", "Utilidad total (S/)", soles),
             ("margen_promedio", "Margen promedio (%)", lambda v: pct(v * 100)),
             ("dias_perdida", "Días vendiendo a pérdida", entero),
             ("dias_margen_bajo", f"Días con margen < mínimo ({cfg['margen_minimo']*100:.0f}%)", entero)]
    sim = r["simulacion"]
    for (prod, pol), m in res.items():
        g = sim[(sim["producto"] == prod) & (sim["politica"] == pol)]
        m["dias_perdida"] = int((g["margen_pct"] < 0).sum())
    datos = {"Indicador": [n for _, n, _ in filas] + ["Diferencia de utilidad"]}
    tot = {"A": 0.0, "B": 0.0}
    for p in PRODUCTOS:
        for pol, nombre in (("A", "Margen fijo"), ("B", "Precio óptimo")):
            m = res.get((p, pol))
            col = f"{p} {nombre}"
            if m is None:
                datos[col] = ["—"] * (len(filas) + 1)
                continue
            datos[col] = [f(m[k]) for k, _, f in filas]
            tot[pol] += m["utilidad_total"]
            if pol == "A":
                datos[col].append("—")
            else:
                ua = res[(p, "A")]["utilidad_total"]
                dif = m["utilidad_total"] - ua
                datos[col].append(f"{_signo(dif)} ({_signo(dif / ua * 100 if ua else 0, dec1)}%)")
    df = pd.DataFrame(datos)
    dif = tot["B"] - tot["A"]
    da = sum(res[(p, "A")]["dias_margen_bajo"] for p in PRODUCTOS if (p, "A") in res)
    db = sum(res[(p, "B")]["dias_margen_bajo"] for p in PRODUCTOS if (p, "B") in res)
    va = sum(res[(p, "A")]["demanda_total"] for p in PRODUCTOS if (p, "A") in res)
    vb = sum(res[(p, "B")]["demanda_total"] for p in PRODUCTOS if (p, "B") in res)
    interp = (f"Al comparar la política de margen fijo ({cfg.get('margen_politica_fija', 0.08)*100:.0f}%) con el "
              f"precio óptimo calculado por el modelo, se observa una diferencia de {_signo_soles(dif)} en utilidad "
              f"total durante los 6 meses analizados, equivalente a "
              f"{'un incremento' if dif >= 0 else 'una disminución'} del "
              f"{abs(dif / tot['A'] * 100) if tot['A'] else 0:.1f}%. Además, la política optimizada "
              + (f"mantiene en {da} los días" if db == da else
                 f"{'reduce' if db < da else 'aumenta'} de {da} a {db} los días")
              + " en que el grifo vende con margen inferior al mínimo deseado.")
    if va:
        interp += (f" La política optimizada vende {abs(vb - va) / va * 100:.1f}% "
                   f"{'menos' if vb < va else 'más'} galones: su ganancia proviene del margen por galón.")
    notas = ["Margen fijo = costo FIFO × 1.08 redondeado a XX.X9; Precio óptimo = Modelo 2.",
             "Simulación diaria con el mismo costo FIFO, las mismas cisternas y la misma demanda logística.",
             "Días vendiendo a pérdida = días con precio por debajo del costo FIFO de lo vendido."]
    return _tabla("Comparación de políticas de precios: margen fijo vs. precio óptimo (6 meses)", df, notas,
                  interp)


def tabla5(r):
    """Tabla 5: resumen para conclusiones."""
    res, m = r["resumen_politicas"], r["metricas_total"]
    ua = sum(res[(p, "A")]["utilidad_total"] for p in PRODUCTOS if (p, "A") in res)
    ub = sum(res[(p, "B")]["utilidad_total"] for p in PRODUCTOS if (p, "B") in res)
    sim = r["simulacion"]
    pa = int(((sim["politica"] == "A") & (sim["margen_pct"] < 0)).sum()) if len(sim) else 0
    pb = int(((sim["politica"] == "B") & (sim["margen_pct"] < 0)).sum()) if len(sim) else 0
    dif = ub - ua
    inc = dif / ua * 100 if ua else 0
    supera = m and m["mejora_pct"] >= 0
    filas = [
        ["Error promedio del pronóstico de intervalo", f"{dec1(m['mae']) if m else '—'} días",
         "El modelo anticipa los cambios con precisión aceptable" if m and m["mae"] <= 3 else
         "El modelo anticipa los cambios con un margen de error de varios días"],
        ["Mejora vs pronóstico simple (baseline)", f"{_signo(m['mejora_pct'], dec1) if m else '—'}%",
         "El modelo supera al método intuitivo" if supera else "El modelo NO supera al método intuitivo"],
        ["Utilidad adicional con precio óptimo (6 meses)", _signo_soles(dif),
         "Ganancia que se habría obtenido usando el modelo" if dif >= 0 else
         "Utilidad que se habría perdido usando el modelo"],
        ["Incremento porcentual de utilidad", f"{_signo(inc, dec1)}%",
         "Mejora respecto a la política de margen fijo"],
        ["Días de anticipación promedio", f"{dec1(m['anticipacion']) if m else '—'} días",
         "Tiempo que gana el administrador para prepararse"],
        ["Reducción de días vendiendo a pérdida", f"{pa} → {pb} días",
         "Protección contra pérdidas por costo no actualizado"],
    ]
    df = pd.DataFrame(filas, columns=["Hallazgo", "Valor", "Significado práctico"])
    interp = (f"Los resultados indican que la implementación del sistema FIFO con los modelos Croston TSB y de "
              f"precio óptimo permitiría al grifo {'incrementar' if dif >= 0 else 'modificar'} su utilidad en un "
              f"{_signo(inc, dec1)}% y anticiparse a los cambios de precio del proveedor con "
              f"{dec1(m['anticipacion']) if m else '—'} días de ventaja promedio. Se recomienda su implementación "
              "gradual, comenzando por el registro sistemático de ventas y compras para alimentar los modelos "
              "con datos reales.")
    notas = ["Valores obtenidos de las Tablas 3 y 4.",
             "Los resultados de utilidad dependen del supuesto de elasticidad κ de la demanda."]
    return _tabla("Resumen de hallazgos para las conclusiones", df, notas, interp)


def construir_tablas(sistema, progreso=None):
    """Devuelve OrderedDict {nombre_hoja: tabla} con las 5 tablas del artículo."""
    r = calcular_resultados(sistema, progreso)
    return OrderedDict([
        ("Tabla1_Estadisticas_Descriptivas", tabla1(sistema, r)),
        ("Tabla2_Parametros_Modelos", tabla_parametros(sistema, r)),
        ("Tabla3_Resultados_Modelo1", tabla3(r)),
        ("Tabla4_Comparacion_Politicas", tabla4(r)),
        ("Tabla5_Resumen_Conclusiones", tabla5(r)),
    ])


def tablas_internas(sistema):
    """Tablas que se ven en el software pero NO se exportan al artículo."""
    r = calcular_resultados(sistema)
    return OrderedDict([("Sensibilidad_Elasticidad", tabla_kappa(r)),
                        ("Sensibilidad_Precio", tabla_sensibilidad_precio(r)),
                        ("Backtest_Detallado", tabla_backtest_detallado(r))])


# ================================================================ escritura
def _escribir_hoja(ws, numero, tabla):
    """Escribe una tabla con formato académico (estilo APA: bordes horizontales)."""
    df = tabla["df"]
    ws.cell(row=1, column=1, value=f"Tabla {numero}").font = Font(bold=True, size=11)
    ws.cell(row=2, column=1, value=tabla["titulo"]).font = Font(italic=True, size=11)
    fila0 = 4
    fino, grueso = Side(style="thin"), Side(style="medium")
    for j, c in enumerate(df.columns, 1):
        celda = ws.cell(row=fila0, column=j, value=str(c))
        celda.font = Font(bold=True)
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        celda.border = Border(top=grueso, bottom=fino)
    for i, fila in enumerate(df.itertuples(index=False), 1):
        for j, v in enumerate(fila, 1):
            if isinstance(v, (np.integer,)):
                v = int(v)
            elif isinstance(v, (np.floating,)):
                v = float(v)
            celda = ws.cell(row=fila0 + i, column=j, value=v)
            celda.alignment = Alignment(horizontal="left" if j == 1 else "center", wrap_text=True)
            if fila[0] in ("Consolidado", "Promedio", "Total", "Óptimo") or str(fila[1]) == "Óptimo":
                celda.font = Font(bold=True)
    ultima = fila0 + len(df)
    for j in range(1, len(df.columns) + 1):
        ws.cell(row=ultima, column=j).border = Border(bottom=grueso)
    f = ultima + 2
    ws.cell(row=f, column=1, value="Nota. " + " ".join(tabla["notas"])).font = Font(size=9)
    ws.cell(row=f + 1, column=1, value=FUENTE_TABLA).font = Font(size=9, italic=True)
    ws.cell(row=f + 3, column=1, value="Interpretación:").font = Font(bold=True)
    c = ws.cell(row=f + 4, column=1, value=tabla["interpretacion"])
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ancho_total = max(len(df.columns), 4)
    ws.merge_cells(start_row=f + 4, start_column=1, end_row=f + 4, end_column=ancho_total)
    ws.merge_cells(start_row=f, start_column=1, end_row=f, end_column=ancho_total)
    ws.cell(row=f, column=1).alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[f].height = 15 * max(2, len(" ".join(tabla["notas"])) // 110 + 1)
    ws.row_dimensions[f + 4].height = 15 * max(3, len(tabla["interpretacion"]) // 100 + 1)
    for j, col in enumerate(df.columns, 1):
        largo = max([len(str(col)) * 0.6] + [len(str(x)) for x in df.iloc[:, j - 1]] + [8])
        ws.column_dimensions[get_column_letter(j)].width = min(max(largo + 2, 12), 60)
    ws.freeze_panes = ws.cell(row=fila0 + 1, column=2)


def exportar_tablas(tablas, ruta, hojas=None):
    """Escribe las tablas (todas o solo 'hojas') en un Excel. Devuelve la ruta."""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    libro = Workbook()
    libro.remove(libro.active)
    for n, (nombre, tabla) in enumerate(tablas.items(), 1):
        if hojas and nombre not in hojas:
            continue
        _escribir_hoja(libro.create_sheet(nombre[:31]), n, tabla)
    libro.save(ruta)
    return ruta
