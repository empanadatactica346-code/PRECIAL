"""
Respuestas directas para el administrador (tarjetas de decisión).

Lógica pura, sin interfaz: la usan tanto la app de escritorio como la web.
Cada función devuelve (color, titulo, lineas) con color en
verde | amarillo | rojo | gris y lineas = [(texto, estilo)].
"""
from modelos import modelo_precio_optimo
from utilidades.helpers import formato_fecha, formato_moneda, formato_pct, redondeo_peruano


def tarjeta_pronostico(sistema, p, r):
    """Devuelve (color, titulo, lineas) para la tarjeta del administrador."""
    nombre = sistema.config["nombres_productos"][p].upper()
    if not r.get("ok"):
        return "gris", nombre, [("No hay datos suficientes para pronosticar.", "medio")] +             [(a, "chico") for a in r.get("advertencias", [])[:2]]
    dias = int(r["dias_hasta_cambio"])
    if r["atrasado"] or dias <= 2:
        color, consejo = "rojo", "Cambio inminente: revisar precios HOY"
    elif dias <= 7:
        color, consejo = "amarillo", "Prepararse para ajustar precios"
    else:
        color, consejo = "verde", "No hay urgencia"
    verbo = {"ALZA": "SUBA", "BAJA": "BAJE"}.get(r["direccion"], "CAMBIE")
    conf = {"ALTA": "ALTA ✓", "MEDIA": "MEDIA ⚠️", "BAJA": "BAJA ⚠️ (pocos datos, úselo solo como referencia)"}
    lineas = [("Próximo cambio de precio del proveedor:", "normal"),
              (f"EN {dias} DÍA{'S' if dias != 1 else ''}  →  {formato_fecha(r['fecha_estimada'])}", "grande"),
              (f"Probablemente {verbo} aproximadamente {formato_moneda(r['magnitud'])}/gal", "medio"),
              (f"(Precio actual del proveedor: {formato_moneda(r['precio_actual'])})", "chico"),
              (f"Confianza: {conf[r['confianza']]}", "normal"),
              (consejo, "medio")]
    if r["atrasado"]:
        lineas.insert(2, ("⚠️ Según el patrón histórico, el cambio ya debería haber ocurrido. "
                          "Podría suceder en cualquier momento.", "alerta"))
    return color, nombre, lineas


MARGENES_COMPARACION = [0.05, 0.08, 0.12]


def tarjeta_precio(sistema, p, r, pron):
    """Devuelve (color, titulo, lineas) de la tarjeta de decisión de precio."""
    nombre = sistema.config["nombres_productos"][p].upper()
    if not r.get("ok"):
        return "gris", nombre, ([("No hay datos suficientes para recomendar un precio.", "medio")]
                                + [(a, "chico") for a in r.get("advertencias", [])[:2]])
    c, u_opt, d_opt = r["costo"], r["utilidad_diaria"], r["demanda_diaria"]
    lineas = [("PRECIO RECOMENDADO:", "normal"),
              (f"{formato_moneda(r['precio_recomendado'])}/gal", "grande")]
    if pron.get("ok"):
        dias = int(pron["dias_hasta_cambio"])
        lineas += [(f"Mantener este precio por: {dias} DÍA{'S' if dias != 1 else ''}", "medio"),
                   (f"(hasta el próximo cambio estimado del proveedor: {formato_fecha(pron['fecha_estimada'])})",
                    "chico")]
        if pron["atrasado"]:
            lineas.append(("⚠️ El cambio del proveedor está retrasado: vuelva a revisar el precio mañana.",
                           "alerta"))
    else:
        lineas.append((f"Revisar de nuevo en {sistema.config['horizonte_dias']} días (no hay pronóstico "
                       "del proveedor).", "medio"))
    margen_sol = r["precio_recomendado"] - c
    lineas += [(f"Su costo actual (FIFO): {formato_moneda(c)}/gal", "normal"),
               (f"Su margen con este precio: {formato_pct(r['margen_pct'])} ({formato_moneda(margen_sol)}/gal)",
                "normal"),
               (f"Utilidad diaria estimada: {formato_moneda(u_opt, 0)}", "medio"), ("", "chico")]
    limite = min(r["stock"], r["capacidad"])
    for m in MARGENES_COMPARACION:
        pm = redondeo_peruano(c * (1 + m))
        dm = float(modelo_precio_optimo.demanda(pm, r["d_base"], r["kappa"], r["p_mercado"]))
        dif = (pm - c) * dm - u_opt
        texto = f"vs. margen fijo {m*100:.0f}% ({formato_moneda(pm)}): "
        if abs(pm - r["precio_recomendado"]) < 0.005 or abs(dif) < 1:
            texto += "mismo resultado"
        elif dif < 0:
            texto += f"ganaría {formato_moneda(-dif, 0)}/día MENOS"
        else:
            texto += f"ganaría {formato_moneda(dif, 0)}/día MÁS"
            if dm * r["horizonte"] > limite + 1e-6:
                texto += ", pero su stock no alcanza para vender tanto"
        if d_opt > 0 and dm < d_opt * 0.995:
            texto += f" y perdería ~{(1 - dm / d_opt) * 100:.0f}% de clientes"
        lineas.append((texto, "chico"))
    if r["margen_pct"] < sistema.config["margen_minimo"] - 1e-4:
        color = "rojo"
    elif r["advertencias"]:
        color = "amarillo"
        lineas.append(("⚠️ " + r["advertencias"][0], "alerta"))
    else:
        color = "verde"
    return color, nombre, lineas
