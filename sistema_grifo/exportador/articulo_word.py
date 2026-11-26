"""
Borrador del artículo científico en Word (BORRADOR_ARTICULO.docx).

Estructura IMRaD (Introducción, Metodología, Resultados, Discusión) con las
cifras, tablas y figuras calculadas por el propio software, más una matriz de
decisiones gerenciales y operativas. Los textos que debe completar el autor
aparecen resaltados en amarillo con la marca [COMPLETAR: ...].
"""
import os
from datetime import datetime

from configuracion import PRODUCTOS

REFERENCIAS = [
    "Croston, J. D. (1972). Forecasting and stock control for intermittent demands. "
    "Operational Research Quarterly, 23(3), 289–303.",
    "Teunter, R. H., Syntetos, A. A., & Babai, M. Z. (2011). Intermittent demand: Linking forecasting "
    "to inventory obsolescence. European Journal of Operational Research, 214(3), 606–615.",
    "Syntetos, A. A., & Boylan, J. E. (2005). The accuracy of intermittent demand estimates. "
    "International Journal of Forecasting, 21(2), 303–314.",
    "Phillips, R. L. (2021). Pricing and revenue optimization (2nd ed.). Stanford University Press.",
    "Talluri, K. T., & van Ryzin, G. J. (2004). The theory and practice of revenue management. Springer.",
    "Hyndman, R. J., & Athanasopoulos, G. (2021). Forecasting: Principles and practice (3rd ed.). OTexts.",
    "Horngren, C. T., Datar, S. M., & Rajan, M. V. (2015). Cost accounting: A managerial emphasis "
    "(15th ed.). Pearson. (Valuación de inventarios FIFO).",
]


def _fila(df, etiqueta, columna):
    """Valor de la fila cuyo primer campo contiene 'etiqueta'."""
    filas = df[df.iloc[:, 0].astype(str).str.contains(etiqueta, regex=False)]
    return str(filas.iloc[0][columna]) if len(filas) else "—"


def datos_clave(sistema, tablas, r):
    """Cifras centrales del artículo, calculadas una sola vez."""
    m = r.get("metricas_total") or {}
    rp = r.get("resumen_politicas") or {}
    ua = sum(v["utilidad_total"] for (p, k), v in rp.items() if k == "A")
    ub = sum(v["utilidad_total"] for (p, k), v in rp.items() if k == "B")
    qa = sum(v["dias_quiebre"] for (p, k), v in rp.items() if k == "A")
    qb = sum(v["dias_quiebre"] for (p, k), v in rp.items() if k == "B")
    ga = sum(v["galones_perdidos"] for (p, k), v in rp.items() if k == "A")
    gb = sum(v["galones_perdidos"] for (p, k), v in rp.items() if k == "B")
    va = sum(v["demanda_total"] for (p, k), v in rp.items() if k == "A")
    vb = sum(v["demanda_total"] for (p, k), v in rp.items() if k == "B")
    t1 = tablas["Tabla1_Estadisticas_Descriptivas"]["df"]
    return {
        "periodo": _fila(t1, "Período", "DB5"),
        "transacciones": _fila(t1, "transacciones", "Total"),
        "volumen": _fila(t1, "Volumen total", "Total"),
        "ingreso": _fila(t1, "Ingreso total", "Total"),
        "cambios": _fila(t1, "cambios de precio", "Total"),
        "intervalo": _fila(t1, "Intervalo medio", "Total"),
        "variacion": _fila(t1, "Variación máxima", "Total"),
        "quiebres_hist": _fila(t1, "quiebre", "Total"),
        "mae": m.get("mae"), "mae_naive": m.get("mae_naive"), "mejora": m.get("mejora_pct"),
        "dentro2": m.get("pct_dentro_2"), "anticipacion": m.get("anticipacion"),
        "n_eval": m.get("n_evaluados"),
        "util_a": ua, "util_b": ub, "dif": ub - ua, "dif_pct": (ub - ua) / ua * 100 if ua else 0,
        "quiebre_a": qa, "quiebre_b": qb, "gal_perd_a": ga, "gal_perd_b": gb,
        "vol_a": va, "vol_b": vb, "vol_pct": (vb - va) / va * 100 if va else 0,
        "rp": rp,
    }


def _n(v, d=1):
    return "—" if v is None else f"{v:,.{d}f}"


def lectura_modelo1(k):
    """Interpretación honesta del desempeño del Modelo 1 frente al baseline."""
    if k["mejora"] is None:
        return "No hubo cambios suficientes para evaluar el Modelo 1."
    if k["mejora"] >= 5:
        return (f"El Modelo 1 redujo el error en {k['mejora']:.1f}% respecto al promedio simple, "
                "por lo que aporta precisión adicional.")
    if k["mejora"] > -5:
        return (f"El Modelo 1 obtuvo una precisión equivalente al promedio simple (diferencia de "
                f"{k['mejora']:+.1f}%). Su aporte no está en un menor error, sino en que se actualiza "
                "automáticamente después de cada cambio, estima también la dirección y magnitud del "
                "siguiente ajuste y entrega una fecha concreta para planificar.")
    return (f"El Modelo 1 fue {abs(k['mejora']):.1f}% menos preciso que el promedio simple; con estos "
            "datos conviene usar el promedio simple como referencia y revisar los parámetros α y β.")


def matriz_decisiones(sistema):
    """Filas (nivel, decisión, indicador, regla del software, acción hoy)."""
    filas = []
    cfg = sistema.config
    for p in PRODUCTOS:
        t = sistema.tanques[p]
        pr = sistema.pronostico(p)
        po = sistema.precio_optimo(p)
        d_base, _ = sistema.demanda_base(p)
        dias = t.stock_actual() / d_base if d_base > 0 else None
        if po.get("ok"):
            accion = (f"Fijar {cfg['moneda']} {po['precio_recomendado']:.2f}/gal "
                      f"(margen {po['margen_pct']*100:.1f}%, restricción: {po.get('restriccion_activa', '—')})")
        else:
            accion = "Sin datos suficientes"
        filas.append(["Gerencial", f"Precio de venta {p}", "Precio óptimo y margen FIFO",
                      "Maximizar U(p) con márgenes 5–15% y stock", accion])
        if pr.get("ok"):
            cuando = ("en cualquier momento (atrasado)" if pr["atrasado"]
                      else f"en {int(pr['dias_hasta_cambio'])} días ({pr['fecha_estimada']:%d/%m/%Y})")
            filas.append(["Gerencial", f"Anticipar cambio del proveedor {p}", "Croston TSB",
                          "Revisar precio si el cambio es ≤ 2 días",
                          f"Cambio esperado {cuando}, {pr['direccion']} ~{cfg['moneda']} {pr['magnitud']:.2f}/gal"])
        if dias is not None:
            pct = t.porcentaje_lleno()
            urgente = pct < cfg["alerta_stock_pct"] or dias < 2
            filas.append(["Operativa", f"Pedido de cisterna {p}", "Días de cobertura del stock",
                          f"Pedir si cobertura < 2 días o tanque < {cfg['alerta_stock_pct']*100:.0f}%",
                          (f"PEDIR HOY — {dias:.1f} días ({pct*100:.0f}% del tanque)" if urgente
                           else f"Sin urgencia — {dias:.1f} días de cobertura ({pct*100:.0f}% del tanque)")])
    return filas


# ============================================================== documento
def generar_articulo(sistema, tablas, resultados, graficos, ruta):
    """Escribe el borrador .docx en 'ruta' y lo devuelve."""
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
    from docx.shared import Cm, Pt, RGBColor

    k = datos_clave(sistema, tablas, resultados)
    mon = sistema.config["moneda"]
    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.name = "Times New Roman"
    estilo.font.size = Pt(12)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.5)
        s.top_margin = s.bottom_margin = Cm(2.5)

    def parrafo(texto="", negrita=False, cursiva=False, centrado=False, tam=None):
        p = doc.add_paragraph()
        if centrado:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _texto(p, texto, negrita, cursiva, tam)
        return p

    def _texto(p, texto, negrita=False, cursiva=False, tam=None):
        # Las marcas [COMPLETAR: ...] se resaltan para que el autor las vea
        partes = texto.split("[COMPLETAR")
        for i, parte in enumerate(partes):
            if i:
                fin = parte.find("]") + 1
                run = p.add_run("[COMPLETAR" + parte[:fin])
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW
                run.bold = True
                parte = parte[fin:]
            run = p.add_run(parte)
            run.bold, run.italic = negrita, cursiva
            if tam:
                run.font.size = Pt(tam)

    def titulo(texto, nivel=1):
        h = doc.add_heading(texto, level=nivel)
        for run in h.runs:
            run.font.name = "Times New Roman"
            run.font.color.rgb = RGBColor(0, 0, 0)
        return h

    def tabla(numero, t):
        parrafo(f"Tabla {numero}", negrita=True)
        parrafo(t["titulo"], cursiva=True)
        df = t["df"]
        tb = doc.add_table(rows=1, cols=len(df.columns))
        tb.style = "Table Grid"
        tb.alignment = WD_TABLE_ALIGNMENT.CENTER
        for j, c in enumerate(df.columns):
            celda = tb.rows[0].cells[j]
            celda.text = str(c)
            celda.paragraphs[0].runs[0].bold = True
        for fila in df.itertuples(index=False):
            celdas = tb.add_row().cells
            for j, v in enumerate(fila):
                celdas[j].text = "" if v is None else str(v)
        for fila in tb.rows:
            for c in fila.cells:
                for p in c.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(8)
        if t.get("notas"):
            parrafo("Nota. " + " ".join(t["notas"]) + " Fuente: Elaboración propia.", tam=9)
        else:
            parrafo("Fuente: Elaboración propia.", tam=9)

    def figura(i, leyenda):
        if i < len(graficos) and graficos[i] and os.path.exists(graficos[i]):
            doc.add_picture(graficos[i], width=Cm(16))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            parrafo(leyenda, cursiva=True, centrado=True, tam=10)

    # ------------------------------------------------------------ portada
    parrafo("Gestión de inventario FIFO, pronóstico de cambios de precio con Croston TSB y "
            "optimización del precio de venta en una estación de combustible", negrita=True,
            centrado=True, tam=14)
    parrafo("[COMPLETAR: Autores, filiación, correo]", centrado=True)
    parrafo(f"Borrador generado por PRECIAL el {datetime.now():%d/%m/%Y %H:%M} con datos de "
            f"{k['periodo']}.", cursiva=True, centrado=True, tam=9)

    # ------------------------------------------------------------ resumen
    titulo("Resumen")
    parrafo(
        f"Las estaciones de combustible fijan su precio de venta sin conocer el costo real del galón "
        f"vendido, porque el tanque mezcla cisternas compradas a precios distintos, y sin anticipar "
        f"cuándo el proveedor cambiará su precio. En el periodo analizado ({k['periodo']}; "
        f"{k['transacciones']} transacciones y {k['volumen']} galones) el proveedor modificó su precio "
        f"{k['cambios']} veces, con un intervalo medio de {k['intervalo']} días y una variación de costo "
        f"de hasta {mon} {k['variacion']}/gal. Se desarrolló un sistema que integra (i) la valuación FIFO "
        f"del inventario, (ii) un pronóstico Croston TSB del intervalo entre cambios de precio y (iii) un "
        f"modelo de precio óptimo con demanda logística y restricciones de margen y stock. El pronóstico "
        f"obtuvo un error absoluto medio de {_n(k['mae'])} días ({_n(k['dentro2'], 0)}% de aciertos dentro "
        f"de ±2 días). En una simulación de 6 meses, la política de precio óptimo generó "
        f"{mon} {k['dif']:+,.0f} ({k['dif_pct']:+.1f}%) de utilidad frente a un margen fijo del "
        f"{sistema.config['margen_politica_fija']*100:.0f}% y redujo los días con quiebre de stock de "
        f"{k['quiebre_a']} a {k['quiebre_b']}. El sistema traduce estos resultados en decisiones "
        f"gerenciales (precio, momento de ajuste) y operativas (pedido de cisternas).")
    parrafo("Palabras clave: inventario FIFO, Croston TSB, demanda intermitente, optimización de precios, "
            "estación de combustible, toma de decisiones.", cursiva=True)

    # ------------------------------------------------------- introducción
    titulo("1. Introducción")
    parrafo("[COMPLETAR: contexto del mercado de combustibles en el Perú y del grifo estudiado]")
    parrafo(tablas["Tabla1_Estadisticas_Descriptivas"]["interpretacion"])
    parrafo("Problema: el administrador decide su precio con un margen fijo sobre el último costo de "
            "compra. Esto ignora (a) que el galón vendido hoy pudo comprarse más caro o más barato "
            "(costo FIFO), (b) que el proveedor cambia precios a intervalos irregulares y (c) que un "
            "precio alto pierde clientes mientras uno bajo agota el tanque. Como consecuencia, el grifo "
            "vende con márgenes que no controla y sufre quiebres de stock "
            f"({k['quiebres_hist']} días con quiebre en el histórico).")
    parrafo("Objetivo: desarrollar y validar un sistema de apoyo a la decisión que determine el costo "
            "real del inventario, anticipe los cambios de precio del proveedor y recomiende el precio de "
            "venta que maximiza la utilidad respetando las restricciones del negocio.")

    # -------------------------------------------------------- metodología
    titulo("2. Metodología")
    titulo("2.1 Datos", 2)
    parrafo(f"Se utilizaron {k['transacciones']} transacciones de venta de consola, el registro de "
            f"cisternas recibidas, la lista de precios del proveedor y el precio de mercado de tres "
            f"productos (DB5, GR y GP) durante {k['periodo']}. "
            "[COMPLETAR: indicar si los datos son reales o simulados y su fuente]")
    titulo("2.2 Valuación FIFO del inventario", 2)
    parrafo("Cada cisterna entra al tanque como un lote con su propio costo. Las ventas consumen primero "
            "el lote más antiguo, de modo que el costo de cada galón vendido y el costo promedio "
            "ponderado del stock restante (c) se conocen en todo momento.")
    titulo("2.3 Modelo 1: pronóstico Croston TSB", 2)
    parrafo("Los cambios de precio del proveedor se tratan como una serie intermitente. El método TSB "
            "(Teunter, Syntetos y Babai, 2011) suaviza por separado la probabilidad de cambio y su "
            "magnitud: z_t = z_{t−1} + α(x_t − z_{t−1}); p_t = p_{t−1} + β(I_t − p_{t−1}). Los parámetros "
            "α y β se eligieron por producto minimizando el MAE en una validación rolling-origin, donde "
            "cada pronóstico usa solo la información anterior.")
    titulo("2.4 Modelo 2: precio óptimo", 2)
    parrafo("Se maximiza U(p) = (p − c)·D(p)·T, con demanda logística "
            "D(p) = D_base·2 / (1 + exp(κ(p/p_mercado − 1))), sujeto a c(1 + m_min) ≤ p ≤ c(1 + m_max) y "
            "D(p)·T ≤ stock disponible. El precio se redondea al formato comercial XX.X9.")
    tabla(1, tablas["Tabla2_Parametros_Modelos"])
    parrafo(tablas["Tabla2_Parametros_Modelos"]["interpretacion"])
    titulo("2.5 Validación", 2)
    parrafo(f"El Modelo 1 se comparó con un baseline (promedio simple de intervalos) sobre "
            f"{k['n_eval']} cambios. El Modelo 2 se comparó con la política de margen fijo mediante una "
            "simulación diaria de 6 meses con los mismos costos FIFO, cisternas y demanda.")

    # ---------------------------------------------------------- resultados
    titulo("3. Resultados")
    titulo("3.1 Diagnóstico del problema", 2)
    tabla(2, tablas["Tabla1_Estadisticas_Descriptivas"])
    figura(0, "Figura 1. Evolución del precio de lista del proveedor.")
    figura(1, "Figura 2. Costo FIFO frente al precio de venta.")
    titulo("3.2 Modelo 1: anticipación de cambios de precio", 2)
    tabla(3, tablas["Tabla3_Resultados_Modelo1"])
    parrafo(f"El error absoluto medio fue de {_n(k['mae'])} días frente a {_n(k['mae_naive'])} días del "
            f"baseline. {lectura_modelo1(k)} En promedio, el administrador conoce la fecha probable del "
            f"siguiente cambio con {_n(k['anticipacion'])} días de anticipación.")
    figura(2, "Figura 3. Backtest del Modelo 1: intervalo real frente al pronosticado.")
    titulo("3.3 Modelo 2: precio óptimo frente a margen fijo", 2)
    tabla(4, tablas["Tabla4_Comparacion_Politicas"])
    parrafo(f"La política optimizada obtuvo {mon} {k['util_b']:,.0f} de utilidad frente a "
            f"{mon} {k['util_a']:,.0f} del margen fijo ({k['dif_pct']:+.1f}%), vendiendo "
            f"{abs(k['vol_pct']):.1f}% {'menos' if k['vol_pct'] < 0 else 'más'} galones. Los días con quiebre de "
            f"stock pasaron de {k['quiebre_a']} a {k['quiebre_b']} y las ventas perdidas por falta de "
            f"combustible de {k['gal_perd_a']:,.0f} a {k['gal_perd_b']:,.0f} galones: un precio mejor "
            "calibrado evita vaciar el tanque antes de la siguiente cisterna.")
    figura(3, "Figura 4. Utilidad en función del precio y precio óptimo.")
    figura(4, "Figura 5. Utilidad diaria: margen fijo frente a precio óptimo.")
    figura(5, "Figura 6. Stock diario y quiebres de stock.")

    # ----------------------------------------------------------- discusión
    titulo("4. Discusión: uso del sistema para la toma de decisiones")
    parrafo("La Tabla 5 resume cómo cada resultado del sistema se convierte en una decisión concreta, "
            "separando el nivel gerencial (estrategia de precios) del operativo (abastecimiento). Los "
            "valores corresponden al último día registrado.")
    filas = matriz_decisiones(sistema)
    import pandas as pd
    tabla(5, {"titulo": "Matriz de decisiones gerenciales y operativas generada por el sistema",
              "df": pd.DataFrame(filas, columns=["Nivel", "Decisión", "Indicador", "Regla", "Acción hoy"]),
              "notas": []})
    parrafo("Limitaciones: la elasticidad κ es un supuesto tomado de la literatura; la utilidad adicional "
            "depende de ese valor y debe recalibrarse con datos reales de respuesta de la demanda. "
            "[COMPLETAR: otras limitaciones y comparación con estudios previos]")
    for a in resultados.get("advertencias", [])[:5]:
        parrafo("• " + a, tam=10)

    # --------------------------------------------------------- conclusiones
    titulo("5. Conclusiones")
    tabla(6, tablas["Tabla5_Resumen_Conclusiones"])
    parrafo(f"(1) La valuación FIFO revela el costo real del galón vendido, que varió hasta "
            f"{mon} {k['variacion']}/gal en el periodo. (2) {lectura_modelo1(k)} (3) El precio óptimo "
            f"aumenta la utilidad en {k['dif_pct']:+.1f}% y reduce los quiebres de stock. (4) El sistema "
            "entrega al administrador reglas claras: qué precio fijar, cuándo revisarlo y cuándo pedir "
            "cisterna. Se recomienda su implementación gradual, comenzando por el registro sistemático "
            "de ventas y compras.")

    titulo("Referencias")
    for ref in REFERENCIAS:
        p = parrafo(ref, tam=11)
        p.paragraph_format.left_indent = Cm(1)
        p.paragraph_format.first_line_indent = Cm(-1)

    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    doc.save(ruta)
    return ruta
