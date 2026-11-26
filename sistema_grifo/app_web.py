"""
PRECIAL — versión WEB del Sistema de Gestión y Optimización de Precios para Grifo.

Ejecutar en local:
    pip install -r requirements.txt
    streamlit run app_web.py

En Railway se inicia solo (ver DESPLIEGUE_RAILWAY.md).
Acceso con UNA sola cuenta: variables de entorno APP_USUARIO y APP_CLAVE.
"""
import hmac
import io
import os
import sys
import tempfile
import threading
import zipfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from configuracion import DIRECTORIO_BASE, PRODUCTOS, hoy  # noqa: E402
from datos.gestor_datos import NOMBRES_TIPO, SistemaGrifo  # noqa: E402
from datos.validador import ErrorValidacion  # noqa: E402
from exportador import graficos_articulo, reporte_completo, tablas_articulo  # noqa: E402
from utilidades import persistencia  # noqa: E402
from utilidades.decisiones import tarjeta_precio, tarjeta_pronostico  # noqa: E402
from utilidades.helpers import formato_fecha, formato_galones, formato_moneda, formato_pct  # noqa: E402

st.set_page_config(page_title="PRECIAL — Precios del grifo", page_icon="⛽", layout="wide")

NARANJA, MARRON = "#E8780C", "#2B1D0E"
COLORES = {"DB5": "#E8780C", "GR": "#D4A000", "GP": "#A63A00"}
SEMAFORO = {"verde": ("#E3F4E1", "#2E7D32"), "amarillo": ("#FFF4C2", "#9A7400"),
            "rojo": ("#FBE0DC", "#B42318"), "gris": ("#EEEEEE", "#666666")}
ESTILOS = {"normal": "font-size:0.95rem", "grande": "font-size:1.6rem;font-weight:800",
           "medio": "font-size:1.05rem;font-weight:700", "chico": "font-size:0.82rem;color:#555",
           "alerta": "font-size:0.9rem;font-weight:700;color:#B42318"}

st.markdown(f"""
<style>
  .stButton>button, .stDownloadButton>button {{ background:{NARANJA}; color:white; border:0; }}
  .stButton>button:hover, .stDownloadButton>button:hover {{ background:#C25F00; color:white; }}
  [data-testid="stSidebar"] {{ background:{MARRON}; }}
  [data-testid="stSidebar"] * {{ color:#FFE8B0 !important; }}
  .tarjeta {{ border-radius:12px; border:3px solid; padding:14px 16px; margin-bottom:12px; }}
  .tarjeta p {{ margin:2px 0; line-height:1.35; }}
</style>""", unsafe_allow_html=True)


# =============================================================== acceso
def credenciales():
    """Usuario y clave de la única cuenta (variables de entorno)."""
    usuario, clave = os.environ.get("APP_USUARIO"), os.environ.get("APP_CLAVE")
    if usuario and clave:
        return usuario, clave, False
    return "admin", "admin", True   # solo para pruebas locales


def pantalla_acceso():
    usuario, clave, por_defecto = credenciales()
    en_nube = any(os.environ.get(v) for v in ("RAILWAY_ENVIRONMENT", "RENDER", "PORT"))
    if por_defecto and en_nube:
        st.error("Falta configurar APP_USUARIO y APP_CLAVE en el servidor (ver DESPLIEGUE_RAILWAY.md).")
        st.stop()
    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        st.markdown(f"<h1 style='color:{NARANJA}'>⛽ PRECIAL</h1>", unsafe_allow_html=True)
        st.write("Sistema de gestión y optimización de precios para grifo")
        with st.form("acceso"):
            u = st.text_input("Usuario")
            c = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", width="stretch"):
                if hmac.compare_digest(u, usuario) and hmac.compare_digest(c, clave):
                    st.session_state["ingresado"] = True
                    st.rerun()
                st.error("Usuario o contraseña incorrectos.")
        if por_defecto:
            st.info("Modo de prueba local: usuario **admin**, contraseña **admin**.")
    st.stop()


# ============================================================ sistema
@st.cache_resource
def obtener_sistema():
    """Una sola instancia compartida (una sola cuenta para todos)."""
    sis = SistemaGrifo()
    carpeta = os.path.join(DIRECTORIO_BASE, "datos_iniciales")
    if sis.datos["ventas"].empty and os.path.isdir(carpeta):
        rutas = sorted(os.path.join(carpeta, f) for f in os.listdir(carpeta)
                       if f.lower().endswith((".xlsx", ".xls", ".csv")))
        if rutas:
            try:
                sis.importar_archivos(rutas)
            except Exception:
                pass   # si falla, el usuario puede importar a mano
    return sis, threading.Lock()


sistema, CANDADO = obtener_sistema()


def tarjeta(color, titulo, lineas):
    fondo, borde = SEMAFORO[color]
    cuerpo = "".join(f"<p style='{ESTILOS[e]}'>{t or '&nbsp;'}</p>" for t, e in lineas)
    st.markdown(f"<div class='tarjeta' style='background:{fondo};border-color:{borde}'>"
                f"<p style='font-size:1.1rem;font-weight:800;color:{borde}'>● {titulo}</p>{cuerpo}</div>",
                unsafe_allow_html=True)


def sin_datos():
    if sistema.datos["ventas"].empty:
        st.warning("Todavía no hay datos. Vaya a **📂 Importar datos** y suba sus archivos Excel.")
        return True
    return False


def importar(archivos, tipo=None):
    """Guarda los archivos subidos en temporal y los importa."""
    with tempfile.TemporaryDirectory() as tmp:
        rutas = []
        for a in archivos:
            r = os.path.join(tmp, os.path.basename(a.name))
            with open(r, "wb") as f:
                f.write(a.getbuffer())
            rutas.append(r)
        with CANDADO:
            return sistema.importar_archivos(rutas, tipo)


# ============================================================= páginas
def pagina_tutorial():
    ruta = os.path.join(DIRECTORIO_BASE, "TUTORIAL.md")
    with open(ruta, encoding="utf-8") as f:
        st.markdown(f.read())


def pagina_inicio():
    st.title("Resumen del grifo")
    st.caption("Estado de cada tanque. El costo es el costo FIFO: el costo real del combustible que queda.")
    if sin_datos():
        return
    cols = st.columns(3)
    alertas = []
    for col, p in zip(cols, PRODUCTOS):
        t = sistema.tanques[p]
        v = sistema.ventas_procesadas[sistema.ventas_procesadas["producto"] == p]
        precio = v["precio"].iloc[-1] if len(v) else None
        costo = t.costo_promedio_actual()
        margen = (precio - costo) / costo if precio and costo else None
        d_base, _ = sistema.demanda_base(p)
        dias = t.stock_actual() / d_base if d_base > 0 else None
        with col:
            st.subheader(f"{p} — {sistema.config['nombres_productos'][p]}")
            st.metric("Stock", formato_galones(t.stock_actual(), 0), formato_pct(t.porcentaje_lleno()) + " lleno",
                      delta_color="off")
            st.progress(min(t.porcentaje_lleno(), 1.0))
            st.write(f"Último precio de venta: **{formato_moneda(precio) if precio else '—'}**")
            st.write(f"Costo FIFO actual: **{formato_moneda(costo, 4) if costo else '—'}**")
            st.write(f"Margen actual: **{formato_pct(margen) if margen is not None else '—'}**")
            st.write(f"Alcanza para: **{f'{dias:.1f} días' if dias else '—'}**")
        if t.porcentaje_lleno() < sistema.config["alerta_stock_pct"]:
            alertas.append(f"⚠ {p}: stock bajo ({formato_pct(t.porcentaje_lleno())}). Programe una cisterna.")
        if margen is not None and margen < sistema.config["margen_minimo"] - 0.0005:
            alertas.append(f"⚠ {p}: margen actual ({formato_pct(margen)}) por debajo del mínimo.")
        pr = sistema.pronostico(p)
        if pr.get("ok") and pr["dias_hasta_cambio"] <= 2:
            alertas.append(f"⏰ {p}: cambio de precio del proveedor esperado hacia el "
                           f"{formato_fecha(pr['fecha_estimada'])} (dirección probable {pr['direccion']}).")
    st.subheader("Alertas")
    for a in alertas or ["✔ Sin alertas."]:
        st.write(a)
    rech = sistema.texto_rechazos()
    if rech:
        st.caption(rech)


def pagina_importar():
    st.title("📂 Importar datos")
    st.write("Suba **juntos** sus archivos Excel o CSV (por ejemplo `SIMULADO_grifo_resumen.xlsx`, "
             "`SIMULADO_ventas_consola.xlsx` y `VERDAD_OCULTA_simulacion.xlsx`). El sistema reconoce solo "
             "qué contiene cada hoja. Los datos del mismo tipo se **reemplazan**.")
    archivos = st.file_uploader("Archivos", type=["xlsx", "xls", "csv"], accept_multiple_files=True)
    if archivos and st.button("Importar archivos", type="primary"):
        with st.spinner("Importando y recalculando el inventario FIFO… (puede tardar un minuto)"):
            try:
                st.success(importar(archivos).replace("\n", "  \n"))
            except Exception as e:
                st.error(f"No se pudo importar: {e}")
    st.divider()
    st.subheader("Datos cargados actualmente")
    st.table(pd.DataFrame({"Tipo": [NOMBRES_TIPO[t] for t in sistema.datos],
                           "Registros": [f"{len(d):,}" for d in sistema.datos.values()]}))
    with st.expander("⚠ Borrar todos los datos"):
        st.write("Elimina ventas, compras, precios e inventario. **No se puede deshacer.**")
        if st.checkbox("Sí, quiero borrar todo") and st.button("Borrar todo"):
            with CANDADO:
                sistema.borrar_todo()
            st.success("Datos borrados.")


def pagina_ventas():
    st.title("Registro de ventas")
    st.caption("Al registrar una venta, el sistema descuenta el combustible de la capa más antigua (FIFO) "
               "y calcula su costo y margen real.")
    with st.form("venta", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        prod = c1.selectbox("Producto", PRODUCTOS)
        vol = c2.number_input("Galones", min_value=0.0, step=1.0)
        precio = c3.number_input("Precio S//gal", min_value=0.0, step=0.1, format="%.2f")
        fecha = c4.text_input("Fecha y hora", pd.Timestamp.now(tz="America/Lima").strftime("%Y-%m-%d %H:%M"))
        if st.form_submit_button("Registrar venta"):
            try:
                with CANDADO:
                    r = sistema.registrar_venta(fecha, prod, vol, precio)
                st.success(f"Venta registrada. Costo FIFO {formato_moneda(r['costo_fifo'], 4)}, "
                           f"margen {formato_moneda(r['margen'])}/gal, utilidad {formato_moneda(r['utilidad'])}.")
            except ErrorValidacion as e:
                st.error(str(e))
    subir = st.file_uploader("Importar ventas (CSV/Excel: fecha, producto, volumen, precio)",
                             type=["xlsx", "xls", "csv"], key="sv")
    if subir and st.button("Importar ventas"):
        st.info(importar([subir], "ventas"))
    st.subheader("Últimas ventas")
    v = sistema.ventas_procesadas.tail(200).iloc[::-1]
    st.dataframe(v.rename(columns={"fecha": "Fecha", "producto": "Producto", "volumen": "Galones",
                                   "precio": "Precio", "costo_fifo": "Costo FIFO", "margen": "Margen S//gal",
                                   "utilidad": "Utilidad S/"}).drop(columns="costo_reposicion"),
                 width="stretch", hide_index=True)


def pagina_compras():
    st.title("Registro de compras (cisternas)")
    st.caption("Cada cisterna crea una nueva capa de costo en el tanque. No se aceptan cisternas que "
               "excedan la capacidad.")
    with st.form("compra", clear_on_submit=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        prod = c1.selectbox("Producto", PRODUCTOS)
        vol = c2.number_input("Galones", min_value=0.0, step=100.0)
        costo = c3.number_input("Costo S//gal", min_value=0.0, step=0.1, format="%.2f")
        fecha = c4.text_input("Fecha llegada", pd.Timestamp.now(tz="America/Lima").strftime("%Y-%m-%d %H:%M"))
        prov = c5.text_input("Proveedor (opcional)")
        if st.form_submit_button("Registrar cisterna"):
            try:
                with CANDADO:
                    sistema.registrar_compra(fecha, prod, vol, costo, prov)
                st.success("Cisterna registrada.")
            except ErrorValidacion as e:
                st.error(str(e))
    subir = st.file_uploader("Importar compras (CSV/Excel)", type=["xlsx", "xls", "csv"], key="sc")
    if subir and st.button("Importar compras"):
        st.info(importar([subir], "compras"))
    st.subheader("Últimas compras")
    c = sistema.datos["compras"].copy()
    c["estado"] = [sistema.estado_compras.get(i, "") for i in c.index]
    st.dataframe(c.iloc[::-1].head(200), width="stretch", hide_index=True)


def pagina_inventario():
    st.title("Inventario (capas FIFO)")
    st.caption("Cada fila es una cisterna que todavía tiene combustible. Se vende primero la de arriba.")
    if sin_datos():
        return
    for p in PRODUCTOS:
        t = sistema.tanques[p]
        st.subheader(f"{p} — {sistema.config['nombres_productos'][p]}")
        a, b, c = st.columns(3)
        a.metric("Stock", formato_galones(t.stock_actual(), 0))
        b.metric("Valor del inventario", formato_moneda(t.valor_inventario(), 0))
        c.metric("Costo promedio FIFO", formato_moneda(t.costo_promedio_actual(), 4))
        st.progress(min(t.porcentaje_lleno(), 1.0), text=f"{formato_pct(t.porcentaje_lleno())} de "
                                                          f"{t.capacidad_maxima:,.0f} gal")
        capas = pd.DataFrame(t.detalle_capas())
        if len(capas):
            st.dataframe(capas.rename(columns={"fecha": "Fecha", "volumen_original": "Volumen original",
                                               "volumen_restante": "Volumen restante",
                                               "costo_galon": "Costo S//gal", "origen": "Origen"}),
                         width="stretch", hide_index=True)


def selector_fecha():
    f = st.date_input("Fecha actual (cámbiela solo para simular escenarios)", sistema.fecha_actual.date(),
                      format="DD/MM/YYYY")
    f = pd.Timestamp(f).normalize()
    if f != sistema.fecha_actual:
        sistema.fecha_actual = f
        sistema._cache_pronostico.clear()


def pagina_pronostico():
    st.title("Modelo 1 — ¿Cuándo cambiará el precio del proveedor?")
    st.caption("🟢 más de 7 días: sin urgencia · 🟡 3 a 7 días: prepárese · 🔴 0 a 2 días o retrasado: "
               "revise sus precios hoy.")
    if sin_datos():
        return
    selector_fecha()
    for col, p in zip(st.columns(3), PRODUCTOS):
        with col:
            tarjeta(*tarjeta_pronostico(sistema, p, sistema.pronostico(p)))
    with st.expander("Ver detalles técnicos ▼"):
        p = st.radio("Producto", PRODUCTOS, horizontal=True, key="p_m1")
        r = sistema.pronostico(p)
        st.write(f"Fuente de datos: {r.get('fuente', '—')}")
        for a in r.get("advertencias", []):
            st.warning(a)
        if r.get("ok"):
            st.write(f"Intervalo estimado **{r['intervalo_estimado']:.2f} días**, tamaño estimado "
                     f"**{r['magnitud']:.4f} S//gal**, α = {r['alfa']:.2f}, β = {r['beta']:.2f} (optimizados). "
                     f"Últimos cambios: {', '.join(f'{c:+.2f}' for c in r['ultimos_cambios'])}.")
        serie = r.get("serie")
        if serie is not None and len(serie):
            fig, ax = plt.subplots(figsize=(10, 3.5))
            ax.step(serie.index, serie.values, where="post", color=COLORES[p])
            ev = r["eventos"]
            ax.scatter(ev["fecha"], ev["precio_nuevo"], s=14, color="black", zorder=3, label="Cambio")
            if r.get("ok"):
                ax.axvline(r["fecha_estimada"], ls="--", color="gray", label="Próximo cambio estimado")
            ax.set_ylabel("S//gal")
            ax.grid(alpha=0.3)
            ax.legend()
            st.pyplot(fig)
        bt = r.get("backtest")
        if bt and bt.get("mae_intervalo_modelo") is not None:
            st.write("**Backtest** (error medio en el pasado):")
            st.table(pd.DataFrame({
                "Qué se pronostica": ["Intervalo entre cambios (días)", "Tamaño del cambio (S//gal)"],
                "Croston TSB": [f"{bt['mae_intervalo_modelo']:.2f}", f"{bt['mae_magnitud_modelo']:.3f}"],
                "Promedio simple": [f"{bt['mae_intervalo_naive']:.2f}", f"{bt['mae_magnitud_naive']:.3f}"]}))


def pagina_precio():
    st.title("Modelo 2 — ¿A qué precio conviene vender?")
    st.caption("Precio que deja la mayor utilidad con su costo real (FIFO), sin salirse de los márgenes y sin "
               "vender más combustible del que tiene. Manténgalo hasta el próximo cambio del proveedor.")
    if sin_datos():
        return
    for col, p in zip(st.columns(3), PRODUCTOS):
        with col:
            tarjeta(*tarjeta_precio(sistema, p, sistema.precio_optimo(p), sistema.pronostico(p)))
    st.caption("⚠️ Las utilidades son estimaciones: dependen de qué tan sensibles son sus clientes al precio (κ).")
    with st.expander("Ver análisis completo ▼"):
        p = st.radio("Producto", PRODUCTOS, horizontal=True, key="p_m2")
        cfg = sistema.config
        c1, c2, c3, c4 = st.columns(4)
        k = c1.number_input("κ elasticidad", 1.0, 60.0, float(cfg["kappa"][p]), 1.0)
        h = c2.number_input("Horizonte (días)", 1.0, 60.0, float(cfg["horizonte_dias"]), 1.0)
        mmin = c3.number_input("Margen mínimo %", 0.0, 50.0, cfg["margen_minimo"] * 100, 0.5) / 100
        mmax = c4.number_input("Margen máximo %", 0.5, 80.0, cfg["margen_maximo"] * 100, 0.5) / 100
        r = sistema.precio_optimo(p, k, mmin, mmax, h)
        if not r.get("ok"):
            for a in r.get("advertencias", []):
                st.warning(a)
            return
        x, y = r["curva"]
        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.plot(x, y, color=COLORES[p])
        ax.axvspan(r["limite_inferior"], r["limite_superior"], color="#FFE08A", alpha=0.5, label="Rango permitido")
        ax.scatter([r["precio_recomendado"]], [r["utilidad_diaria"]], color="#B42318", marker="*", s=150,
                   zorder=3, label=f"Óptimo {formato_moneda(r['precio_recomendado'])}")
        ax.set_xlabel("Precio S//gal")
        ax.set_ylabel("Utilidad S//día")
        ax.grid(alpha=0.3)
        ax.legend()
        st.pyplot(fig)
        st.write(f"Restricción que define el precio: **{r['restriccion_activa']}**. Precio de mercado "
                 f"{formato_moneda(r['p_mercado'])} ({r['fuente_mercado']}); demanda base "
                 f"{formato_galones(r['d_base'], 0)}/día.")
        pol = r["politicas"]
        st.write("**Comparación de políticas**")
        st.table(pd.DataFrame([
            [pol["A"]["nombre"], f"{pol['A']['precio']:.2f}", f"{pol['A']['demanda']:,.0f}",
             f"{pol['A']['utilidad_diaria']:,.0f}"],
            [pol["B"]["nombre"], f"{pol['B']['precio']:.2f}", f"{pol['B']['demanda']:,.0f}",
             f"{pol['B']['utilidad_diaria']:,.0f}"]],
            columns=["Política", "Precio", "Galones/día", "Utilidad S//día"]))
        st.write("**Sensibilidad al precio**")
        st.table(pd.DataFrame([[f"{s['variacion']*100:+.0f}%", f"{s['precio']:.2f}", formato_pct(s["margen_pct"]),
                                f"{s['demanda']:,.0f}", f"{s['utilidad_diaria']:,.0f}",
                                "Sí" if s["permitido"] else "No"] for s in r["sensibilidad"]],
                              columns=["Variación", "Precio", "Margen", "Galones/día", "Utilidad S//día",
                                       "Permitido"]))
        st.write("**Escenarios de elasticidad (κ)**")
        st.table(pd.DataFrame([[e["kappa"], f"{e['precio']:.2f}", formato_pct(e["margen_pct"]),
                                f"{e['utilidad_diaria']:,.0f}"] for e in r["escenarios"]],
                              columns=["κ", "Precio óptimo", "Margen", "Utilidad S//día"]))


def pagina_reportes():
    st.title("Reportes")
    st.caption("Margen REAL = calculado con el costo FIFO. Margen ESPERADO = calculado con el costo de la "
               "última cisterna (lo que el administrador cree que gana).")
    if sin_datos():
        return
    c1, c2 = st.columns(2)
    per = c1.radio("Periodo", ["Diario", "Semanal", "Mensual"], horizontal=True)
    prod = c2.radio("Producto", ["Todos"] + PRODUCTOS, horizontal=True)
    df = sistema.reporte({"Diario": "D", "Semanal": "W", "Mensual": "M"}[per], None if prod == "Todos" else prod)
    if df.empty:
        st.info("Sin datos para este filtro.")
        return
    graf = df.set_index("fecha")[["margen_real_pct", "margen_esperado_pct"]] * 100
    st.write("**Margen (%)**")
    st.line_chart(graf.rename(columns={"margen_real_pct": "Margen real", "margen_esperado_pct": "Margen esperado"}))
    h = sistema.historial_diario
    st.write("**Stock diario (galones)**")
    st.line_chart(h.pivot_table(index="fecha", columns="producto", values="stock"))
    st.dataframe(df.iloc[::-1], width="stretch", hide_index=True)
    buf = io.BytesIO()
    with tempfile.TemporaryDirectory() as tmp:
        ruta = os.path.join(tmp, "reporte.xlsx")
        if st.button("Preparar Excel del reporte"):
            sistema.exportar_excel(ruta)
            with open(ruta, "rb") as f:
                buf.write(f.read())
            st.download_button("⬇ Descargar reporte_grifo.xlsx", buf.getvalue(), "reporte_grifo.xlsx")


def pagina_validacion():
    st.title("Validación contra la verdad oculta")
    st.caption("Modelo 1: en cada cambio pasado se pronostica solo con datos anteriores y se compara con lo "
               "que pasó. Modelo 2: se simulan los 6 meses con margen fijo (A) y precio óptimo (B).")
    for k, n in (("precios_proveedor", "Lista de precios del proveedor"),
                 ("precio_mercado", "Precio de mercado diario"), ("ventas_perdidas", "Ventas perdidas")):
        st.write(("✔ " if len(sistema.datos[k]) else "✖ ") + n)
    if sin_datos():
        return
    if st.button("▶ Ejecutar validación", type="primary"):
        st.session_state["validar"] = True
    if not st.session_state.get("validar"):
        return
    with st.spinner("Calculando backtest y simulación…"):
        tablas = tablas_articulo.construir_tablas(sistema)
        r = tablas_articulo.calcular_resultados(sistema)
    for a in r["advertencias"]:
        st.warning(a)
    for nombre, t in (("Modelo 1", tablas_articulo.tabla_modelo1(r)), ("Modelo 2", tablas_articulo.tabla_modelo2(r))):
        st.subheader(f"{nombre}: {t['titulo']}")
        st.dataframe(t["df"], width="stretch", hide_index=True)
        st.info(t["interpretacion"])
    with tempfile.TemporaryDirectory() as tmp:
        st.image(graficos_articulo.fig04(sistema, r, tmp))
        st.image(graficos_articulo.fig06(sistema, r, tmp))


def pagina_exportar():
    st.title("📊 Exportar para el artículo")
    st.write("Genera en un archivo ZIP: **TABLAS_PARA_ARTICULO.xlsx** (5 tablas con título, notas, fuente e "
             "interpretación), **6 gráficos PNG a 300 DPI** y **RESUMEN_RESULTADOS.txt** para copiar y pegar.")
    if sin_datos():
        return
    if st.button("Generar exportación", type="primary"):
        barra = st.progress(0.0, text="Iniciando…")
        with tempfile.TemporaryDirectory() as tmp:
            out = reporte_completo.exportar_todo(sistema, tmp, lambda f, t: barra.progress(min(f, 1.0), text=t))
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for raiz, _, archivos in os.walk(tmp):
                    for a in archivos:
                        z.write(os.path.join(raiz, a), os.path.relpath(os.path.join(raiz, a), tmp))
            st.session_state["zip"] = buf.getvalue()
        st.success("Exportación completa.")
    if st.session_state.get("zip"):
        st.download_button("⬇ Descargar exportaciones_articulo.zip", st.session_state["zip"],
                           "exportaciones_articulo.zip", "application/zip")
    st.divider()
    st.subheader("Vista previa de las tablas")
    if st.checkbox("Mostrar vista previa"):
        for nombre, t in tablas_articulo.construir_tablas(sistema).items():
            with st.expander(f"{nombre} — {t['titulo']}"):
                st.dataframe(t["df"], width="stretch", hide_index=True)
                st.caption(" ".join(t["notas"]))
                st.info(t["interpretacion"])


def pagina_configuracion():
    st.title("Configuración")
    st.caption("Parámetros del grifo y de los modelos. Al guardar se recalcula todo.")
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in sistema.config.items()}
    with st.form("config"):
        st.write("**Capacidad de tanques (galones)**")
        cols = st.columns(3)
        for c, p in zip(cols, PRODUCTOS):
            cfg["capacidad_tanque"][p] = c.number_input(p, 100.0, 100000.0, float(cfg["capacidad_tanque"][p]), 100.0)
        st.write("**Elasticidad κ** (qué tan sensibles son los clientes al precio; típico 15–25)")
        cols = st.columns(3)
        for c, p in zip(cols, PRODUCTOS):
            cfg["kappa"][p] = c.number_input(f"κ {p}", 1.0, 60.0, float(cfg["kappa"][p]), 1.0)
        c1, c2, c3 = st.columns(3)
        cfg["margen_minimo"] = c1.number_input("Margen mínimo %", 0.0, 50.0, cfg["margen_minimo"] * 100) / 100
        cfg["margen_maximo"] = c2.number_input("Margen máximo %", 0.5, 80.0, cfg["margen_maximo"] * 100) / 100
        cfg["margen_politica_fija"] = c3.number_input("Margen fijo de comparación %", 0.0, 50.0,
                                                      cfg["margen_politica_fija"] * 100) / 100
        c1, c2, c3, c4 = st.columns(4)
        cfg["horizonte_dias"] = int(c1.number_input("Horizonte (días)", 1, 60, int(cfg["horizonte_dias"])))
        cfg["croston_alfa_inicial"] = c2.number_input("α inicial", 0.05, 0.30, float(cfg["croston_alfa_inicial"]))
        cfg["croston_beta_inicial"] = c3.number_input("β inicial", 0.05, 0.30, float(cfg["croston_beta_inicial"]))
        cfg["alerta_stock_pct"] = c4.number_input("Alerta de stock %", 1.0, 90.0, cfg["alerta_stock_pct"] * 100) / 100
        if st.form_submit_button("Guardar configuración"):
            if cfg["margen_maximo"] <= cfg["margen_minimo"]:
                st.error("El margen máximo debe ser mayor que el mínimo.")
            else:
                with CANDADO:
                    sistema.guardar_configuracion(cfg)
                st.success("Configuración guardada y datos recalculados.")


PAGINAS = {"📘 Tutorial": pagina_tutorial, "🏠 Inicio": pagina_inicio, "📂 Importar datos": pagina_importar,
           "🧾 Ventas": pagina_ventas, "🚚 Compras": pagina_compras, "🛢 Inventario": pagina_inventario,
           "⏰ Pronóstico (Modelo 1)": pagina_pronostico, "💲 Precio óptimo (Modelo 2)": pagina_precio,
           "📈 Reportes": pagina_reportes, "✅ Validación": pagina_validacion,
           "📊 Exportar artículo": pagina_exportar, "⚙ Configuración": pagina_configuracion}


def main():
    if not st.session_state.get("ingresado"):
        pantalla_acceso()
    with st.sidebar:
        st.markdown("## ⛽ PRECIAL")
        pagina = st.radio("Menú", list(PAGINAS), label_visibility="collapsed")
        st.divider()
        st.caption(f"Hoy: {formato_fecha(hoy())}")
        st.caption(persistencia.estado())
        if st.button("Cerrar sesión"):
            st.session_state.clear()
            st.rerun()
    PAGINAS[pagina]()


main()
