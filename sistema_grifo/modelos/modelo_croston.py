"""
MODELO 1 — Pronóstico de cambios de precio del proveedor (Croston, variante TSB).

No pronostica el precio en sí: pronostica CUÁNDO ocurrirá el próximo cambio
y DE QUÉ TAMAÑO será. Los cambios son intermitentes (no ocurren a diario),
por eso se usa la familia Croston.

Cuando ocurre un cambio (d_t > 0):
    z_t = α·d_t + (1-α)·z_{t-1}     tamaño estimado del cambio
    p_t = β·q_t + (1-β)·p_{t-1}     intervalo estimado entre cambios (días)
Tasa de cambio por día (corrección de sesgo):
    y_t = (1 - β/2) · z_t / p_t

Como z solo depende de α y p solo depende de β, ambos parámetros se
optimizan por separado minimizando el MAE con validación rolling-origin.
"""
import math

import numpy as np
import pandas as pd

RANGO_PARAMETROS = np.round(np.arange(0.05, 0.3001, 0.01), 2)
MIN_ORIGEN = 2   # mínimo de observaciones antes de empezar a evaluar


def construir_serie_diaria(df_precios):
    """
    Recibe un DataFrame (fecha, precio) de un producto y devuelve una
    serie diaria (un valor por día; si no cambió, se repite el de ayer).
    """
    if df_precios is None or df_precios.empty:
        return pd.Series(dtype=float)
    s = (df_precios.dropna(subset=["fecha", "precio"])
         .sort_values("fecha")
         .set_index("fecha")["precio"].astype(float))
    s.index = pd.to_datetime(s.index).normalize()
    s = s.groupby(level=0).last()
    return s.resample("D").last().ffill()


def extraer_eventos(serie):
    """
    Detecta los días en que el precio cambió.
    Devuelve DataFrame: fecha, precio_anterior, precio_nuevo, cambio (con signo),
    magnitud (valor absoluto) e intervalo (días desde el cambio anterior).
    """
    if serie is None or len(serie) < 2:
        return pd.DataFrame(columns=["fecha", "precio_anterior", "precio_nuevo",
                                     "cambio", "magnitud", "intervalo"])
    dif = serie.diff()
    mascara = dif.abs() > 1e-6
    eventos = pd.DataFrame({
        "fecha": serie.index[mascara],
        "precio_anterior": serie.shift(1)[mascara].values,
        "precio_nuevo": serie[mascara].values,
        "cambio": dif[mascara].values,
    })
    eventos["magnitud"] = eventos["cambio"].abs()
    eventos["intervalo"] = eventos["fecha"].diff().dt.days
    return eventos.reset_index(drop=True)


def suavizar(valores, parametro):
    """
    Suavizado exponencial simple aplicado solo en los eventos.
    Devuelve (pronosticos_un_paso, valor_final): pronosticos_un_paso[k] es lo
    que se habría pronosticado para valores[k] usando solo valores[:k].
    """
    valores = list(valores)
    if not valores:
        return [], None
    nivel = valores[0]
    pronosticos = [None]
    for v in valores[1:]:
        pronosticos.append(nivel)
        nivel = parametro * v + (1 - parametro) * nivel
    return pronosticos, nivel


def mae_rolling(valores, parametro):
    """MAE del modelo y del baseline naive (promedio histórico) con rolling-origin."""
    valores = list(valores)
    pron, _ = suavizar(valores, parametro)
    err_modelo, err_naive = [], []
    for k in range(MIN_ORIGEN, len(valores)):
        err_modelo.append(abs(valores[k] - pron[k]))
        err_naive.append(abs(valores[k] - float(np.mean(valores[:k]))))
    if not err_modelo:
        return None, None
    return float(np.mean(err_modelo)), float(np.mean(err_naive))


def optimizar_parametro(valores, inicial):
    """Busca en [0.05, 0.30] el parámetro con menor MAE rolling-origin."""
    if len(valores) <= MIN_ORIGEN:
        return inicial
    mejor, mejor_mae = inicial, math.inf
    for param in RANGO_PARAMETROS:
        mae, _ = mae_rolling(valores, param)
        if mae is not None and mae < mejor_mae - 1e-12:
            mejor, mejor_mae = float(param), mae
    return mejor


def nivel_confianza(n_cambios):
    """BAJO (<8 cambios), MEDIO (8–15) o ALTO (>15)."""
    if n_cambios < 8:
        return "BAJA"
    if n_cambios <= 15:
        return "MEDIA"
    return "ALTA"


def pronosticar(serie, alfa=0.15, beta=0.15, optimizar=True, fecha_referencia=None):
    """
    Ejecuta Croston TSB sobre una serie diaria de precios del proveedor.

    Devuelve un dict con: dias_hasta_cambio, fecha_estimada, magnitud,
    direccion, ultimos_cambios, confianza, n_cambios, intervalo_estimado,
    tasa_diaria, alfa, beta, backtest (MAE), eventos, serie y advertencias.
    """
    res = {"ok": False, "advertencias": [], "serie": serie,
           "eventos": extraer_eventos(serie), "alfa": alfa, "beta": beta}
    eventos = res["eventos"]
    n = len(eventos)
    res["n_cambios"] = n
    res["confianza"] = nivel_confianza(n)

    if serie is None or len(serie) < 2:
        res["advertencias"].append("No hay serie de precios del proveedor para este producto.")
        return res
    if n < 2:
        res["advertencias"].append(
            f"Solo se observó {n} cambio(s) de precio. Se necesitan al menos 2 para "
            "estimar el intervalo entre cambios. No se puede pronosticar.")
        return res

    intervalos = eventos["intervalo"].dropna().tolist()     # n-1 valores
    magnitudes = eventos["magnitud"].tolist()                # n valores

    if optimizar:
        alfa = optimizar_parametro(magnitudes, alfa)
        beta = optimizar_parametro(intervalos, beta)
    res["alfa"], res["beta"] = alfa, beta

    _, z = suavizar(magnitudes, alfa)
    _, p = suavizar(intervalos, beta)
    p = max(p, 1.0)

    # Fecha de referencia = HOY (o la que elija el usuario). El pronóstico
    # siempre apunta hacia adelante desde esa fecha.
    fecha_ref = pd.Timestamp(fecha_referencia or pd.Timestamp.now()).normalize()
    ultimo = eventos["fecha"].iloc[-1]
    dias_desde = (fecha_ref - ultimo).days
    fecha_pron = ultimo + pd.Timedelta(days=math.ceil(p))
    if fecha_pron <= fecha_ref:
        # El cambio ya debería haber ocurrido según el patrón histórico
        dias_hasta = max(1, math.ceil(p - dias_desde))
        fecha_pron = fecha_ref + pd.Timedelta(days=dias_hasta)
        atrasado = True
    else:
        dias_hasta = (fecha_pron - fecha_ref).days
        atrasado = False

    ult = eventos["cambio"].tail(3).tolist()
    suma = sum(ult)
    if abs(suma) < 1e-9:
        direccion = "INCIERTA"
    else:
        direccion = "ALZA" if suma > 0 else "BAJA"

    mae_int, mae_int_naive = mae_rolling(intervalos, beta)
    mae_mag, mae_mag_naive = mae_rolling(magnitudes, alfa)

    res.update({
        "ok": True,
        "intervalo_estimado": p,
        "magnitud": z,
        "tasa_diaria": (1 - beta / 2) * z / p,
        "fecha_ultimo_cambio": ultimo,
        "dias_desde_ultimo": dias_desde,
        "dias_hasta_cambio": float(dias_hasta),
        "atrasado": atrasado,
        "fecha_estimada": fecha_pron,
        "fecha_referencia": fecha_ref,
        "precio_actual": float(serie.iloc[-1]),
        "ultimos_cambios": ult,
        "direccion": direccion,
        "backtest": {
            "mae_intervalo_modelo": mae_int, "mae_intervalo_naive": mae_int_naive,
            "mae_magnitud_modelo": mae_mag, "mae_magnitud_naive": mae_mag_naive,
            "evaluaciones_intervalo": max(len(intervalos) - MIN_ORIGEN, 0),
        },
    })

    if res["confianza"] == "BAJA":
        res["advertencias"].append(
            f"Solo hay {n} cambios observados: el pronóstico es orientativo, "
            "no lo use como único criterio.")
    if mae_int is None:
        res["advertencias"].append("Muy pocos cambios para hacer un backtest del intervalo.")
    elif mae_int_naive is not None and mae_int > mae_int_naive:
        res["advertencias"].append(
            "En el backtest el modelo se equivocó más que el promedio simple; "
            "tome el pronóstico de fecha con cautela.")
    if res["atrasado"]:
        res["advertencias"].append(
            "Según el patrón histórico, el cambio ya debería haber ocurrido "
            f"(último cambio hace {dias_desde} días; intervalo típico {p:.1f} días). "
            "Podría suceder en cualquier momento.")
    if direccion == "INCIERTA" or len(ult) < 3:
        res["advertencias"].append("La dirección del próximo cambio no es clara.")
    return res
