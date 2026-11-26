"""
Gestor de datos del grifo.

- Importa archivos CSV/XLSX con nombres de columnas flexibles.
- Guarda todo en CSV dentro de datos_salida/ (se puede abrir con Excel).
- Reconstruye el inventario FIFO reproduciendo, en orden cronológico,
  el inventario inicial, las cisternas y las ventas.
- Expone los datos que necesitan los dos modelos.
"""
import os

import numpy as np
import pandas as pd

from configuracion import (DIRECTORIO_SALIDA, PRODUCTOS, asegurar_directorios, hoy,
                           cargar_configuracion, guardar_configuracion)
from datos.validador import (ErrorValidacion, limpiar_dataframe, validar_fecha,
                             validar_numero_positivo, validar_producto)
from modelos import modelo_croston, modelo_precio_optimo
from modelos.inventario_fifo import ErrorInventario, TanqueFIFO
from utilidades import persistencia
from utilidades.helpers import (buscar_columna, normalizar_producto, normalizar_texto,
                                tokens)

COLUMNAS = {
    "compras": ["fecha_llegada", "fecha_pedido", "producto", "volumen", "costo_galon", "proveedor"],
    "ventas": ["fecha", "producto", "volumen", "precio"],
    "precios_surtidor": ["fecha", "producto", "precio"],
    "precios_proveedor": ["fecha", "producto", "precio"],
    "inventario_inicial": ["fecha", "producto", "stock", "costo"],
    "precio_mercado": ["fecha", "producto", "precio"],
    "ventas_perdidas": ["fecha", "producto", "volumen"],
}
FECHAS = {"precio_mercado": ["fecha"], "ventas_perdidas": ["fecha"],
          "compras": ["fecha_llegada", "fecha_pedido"], "ventas": ["fecha"],
          "precios_surtidor": ["fecha"], "precios_proveedor": ["fecha"],
          "inventario_inicial": ["fecha"]}
POSITIVOS = {"compras": ["volumen", "costo_galon"], "ventas": ["volumen", "precio"],
             "precios_surtidor": ["precio"], "precios_proveedor": ["precio"],
             "inventario_inicial": ["stock", "costo"], "precio_mercado": ["precio"],
             "ventas_perdidas": []}


def vacio(tipo):
    """DataFrame vacío con las columnas estándar del tipo."""
    return pd.DataFrame(columns=COLUMNAS[tipo])


# =================================================================== lectura
def leer_hojas(ruta):
    """Lee un CSV (una hoja) o un Excel (todas las hojas). Devuelve {nombre: df}."""
    ext = os.path.splitext(ruta)[1].lower()
    if ext == ".csv":
        try:
            df = pd.read_csv(ruta, sep=None, engine="python", encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(ruta, sep=None, engine="python", encoding="latin-1")
        return {os.path.basename(ruta): df}
    if ext in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(ruta, sheet_name=None)
    raise ErrorValidacion(f"Formato no soportado: {ext}. Use CSV o XLSX.")


def _producto(df):
    col = buscar_columna(df, ["producto"], ["combustible"], ["codigo"])
    return None if col is None else df[col].map(normalizar_producto)


def _ancho_a_largo(df, col_fecha, preferencias):
    """
    Convierte tablas 'anchas' (una columna por producto, ej. precio_DB5)
    a formato largo (fecha, producto, valor).
    """
    partes = []
    for prod in PRODUCTOS:
        candidatas = [c for c in df.columns if prod.lower() in tokens(c) and c != col_fecha]
        elegida = None
        for palabra in preferencias:
            elegida = next((c for c in candidatas if palabra in normalizar_texto(c)), None)
            if elegida:
                break
        if elegida:
            partes.append(pd.DataFrame({"fecha": df[col_fecha], "producto": prod,
                                        "valor": df[elegida]}))
    return pd.concat(partes, ignore_index=True) if partes else None


def convertir_ventas(df):
    """Normaliza un DataFrame de ventas a: fecha, producto, volumen, precio."""
    cf = buscar_columna(df, ["fecha", "hora"], ["fecha"])
    if cf is None:
        return None
    prod = _producto(df)
    if prod is None:   # formato ancho (ej. Volumen_DB5, Precio_DB5)
        vol = _ancho_a_largo(df, cf, ["vol", "gal"])
        pre = _ancho_a_largo(df, cf, ["precio"])
        if vol is None:
            return None
        out = vol.rename(columns={"valor": "volumen"})
        out["precio"] = pre["valor"].values if pre is not None and len(pre) == len(out) else np.nan
    else:
        cv = buscar_columna(df, ["volumen"], ["galones"], ["cantidad"], ["gal"])
        cp = buscar_columna(df, ["precio"])
        ci = buscar_columna(df, ["importe"], ["monto"], ["total"])
        if cv is None:
            return None
        out = pd.DataFrame({"fecha": df[cf], "producto": prod, "volumen": df[cv]})
        out["precio"] = df[cp] if cp else np.nan
        if ci is not None:
            faltan = out["precio"].isna()
            out.loc[faltan, "precio"] = (pd.to_numeric(df[ci], errors="coerce")
                                         / pd.to_numeric(df[cv], errors="coerce"))[faltan]
    return out[COLUMNAS["ventas"]]


def convertir_compras(df):
    """Normaliza compras de cisternas."""
    cl = buscar_columna(df, ["fecha", "llegada"], ["fecha", "recep"], ["fecha"])
    cped = buscar_columna(df, ["fecha", "pedido"])
    cv = buscar_columna(df, ["volumen"], ["galones"], ["cantidad"])
    cc = buscar_columna(df, ["costo", "gal"], ["costo"], ["precio"])
    ci = buscar_columna(df, ["importe"], ["total"])
    prod = _producto(df)
    if cl is None or cv is None or prod is None or (cc is None and ci is None):
        return None
    out = pd.DataFrame({"fecha_llegada": df[cl], "producto": prod, "volumen": df[cv]})
    out["fecha_pedido"] = df[cped] if cped else df[cl]
    if cc is not None:
        out["costo_galon"] = df[cc]
    else:
        out["costo_galon"] = pd.to_numeric(df[ci], errors="coerce") / pd.to_numeric(df[cv], errors="coerce")
    cprov = buscar_columna(df, ["proveedor"])
    out["proveedor"] = df[cprov].astype(str) if cprov else ""
    return out[COLUMNAS["compras"]]


def convertir_precios(df, tipo):
    """Normaliza precios del surtidor o del proveedor a: fecha, producto, precio."""
    cf = buscar_columna(df, ["fecha", "inicio"], ["fecha"])
    if cf is None:
        return None
    if tipo == "precios_proveedor":
        grupos = [["precio", "lista"], ["precio", "prov"], ["costo", "prov"], ["prov"], ["precio", "compra"], ["costo"]]
        prefer = ["lista", "prov", "compra", "costo", "precio"]
    elif tipo == "precio_mercado":
        grupos = [["precio", "merc"], ["mercado"], ["precio"]]
        prefer = ["merc", "precio"]
    else:
        grupos = [["precio", "venta"], ["precio", "surt"], ["precio"]]
        prefer = ["venta", "surt", "precio"]
    prod = _producto(df)
    if prod is not None:
        cp = buscar_columna(df, *grupos)
        if cp is None:
            return None
        out = pd.DataFrame({"fecha": df[cf], "producto": prod, "precio": df[cp]})
    else:
        largo = _ancho_a_largo(df, cf, prefer)
        if largo is None:
            return None
        out = largo.rename(columns={"valor": "precio"})
    return out[COLUMNAS[tipo]]


def convertir_inventario(df):
    """Normaliza inventario diario: fecha, producto, stock, costo."""
    cf = buscar_columna(df, ["fecha"])
    cs = buscar_columna(df, ["stock"], ["inventario"], ["volumen"], ["existencia"])
    cc = buscar_columna(df, ["costo"])
    prod = _producto(df)
    if None in (cf, cs, cc) or prod is None:
        return None
    return pd.DataFrame({"fecha": df[cf], "producto": prod, "stock": df[cs], "costo": df[cc]})


def convertir_perdidas(df):
    """Normaliza ventas perdidas (verdad oculta): fecha, producto, volumen."""
    cf = buscar_columna(df, ["fecha"])
    cv = buscar_columna(df, ["volumen"], ["gal"], ["perdid"])
    prod = _producto(df)
    if cf is None or cv is None or prod is None:
        return None
    out = pd.DataFrame({"fecha": df[cf], "producto": prod,
                        "volumen": pd.to_numeric(df[cv], errors="coerce").fillna(0)})
    return out[COLUMNAS["ventas_perdidas"]]


def leer_parametros_simulacion(df):
    """
    Convierte la hoja 'Parametros' de la verdad oculta en un diccionario
    {nombre: valor}. Acepta formato clave-valor (2 columnas) o una fila
    por producto (columna Producto + columnas de parámetros).
    """
    resultado = {}
    if df is None or df.empty:
        return resultado
    df = df.dropna(how="all")
    prod = _producto(df) if len(df.columns) > 2 else None
    if prod is not None and prod.notna().any():
        for (_, fila), p in zip(df.iterrows(), prod):
            if p is None:
                continue
            for c in df.columns:
                v = pd.to_numeric(pd.Series([fila[c]]), errors="coerce").iloc[0]
                if pd.notna(v):
                    resultado[f"{normalizar_texto(c)}_{p.lower()}"] = float(v)
        return resultado
    for fila in df.itertuples(index=False):
        if len(fila) < 2:
            continue
        clave = normalizar_texto(fila[0])
        valores = [v for v in fila[1:] if pd.notna(v)]
        if clave and valores:
            v = valores[0]
            num = pd.to_numeric(pd.Series([v]), errors="coerce").iloc[0]
            resultado[clave] = float(num) if pd.notna(num) else str(v)
    return resultado


def parametro_sim(parametros, palabra, producto):
    """Busca en los parámetros de simulación un valor (ej. 'kappa') para un producto."""
    p = producto.lower()
    for k, v in parametros.items():
        if palabra in k and p in tokens(k) and isinstance(v, (int, float)):
            return float(v)
    return None


CONVERTIDORES = {
    "precio_mercado": lambda d: convertir_precios(d, "precio_mercado"),
    "ventas_perdidas": convertir_perdidas,
    "ventas": convertir_ventas,
    "compras": convertir_compras,
    "precios_surtidor": lambda d: convertir_precios(d, "precios_surtidor"),
    "precios_proveedor": lambda d: convertir_precios(d, "precios_proveedor"),
    "inventario_inicial": convertir_inventario,
}


def clasificar_hoja(nombre_archivo, nombre_hoja, df):
    """Adivina qué tipo de datos contiene una hoja (por su nombre y columnas)."""
    h = normalizar_texto(nombre_hoja)
    a = normalizar_texto(nombre_archivo)
    cols = " ".join(normalizar_texto(c) for c in df.columns)
    if "parametro" in h:
        return "parametros"
    if "mercado" in h:
        return "precio_mercado"
    if "perdid" in h:
        return "ventas_perdidas"
    if "lista" in h:
        return "precios_proveedor"
    if "compra" in h or "cisterna" in h:
        return "compras"
    if "surtidor" in h:
        return "precios_surtidor"
    if "inventario" in h or "stock" in h:
        return "inventario_inicial"
    if "prov" in h or ("verdad" in a and "prov" in cols):
        return "precios_proveedor"
    if "venta" in h or "consola" in h or "consola" in a:
        return "ventas_diarias" if "diari" in h else "ventas"
    if "prov" in cols and "precio" in cols:
        return "precios_proveedor"
    if "costo" in cols and "volumen" in cols:
        return "compras"
    if "stock" in cols:
        return "inventario_inicial"
    if "volumen" in cols and ("precio" in cols or "importe" in cols):
        return "ventas"
    if "precio" in cols:
        return "precios_surtidor"
    return None


# ============================================================ sistema central
class SistemaGrifo:
    """Estado completo del grifo: datos, tanques FIFO y acceso a los modelos."""

    def __init__(self):
        asegurar_directorios()
        persistencia.descargar_todo(DIRECTORIO_SALIDA)   # restaura datos si hay Postgres
        self.config = cargar_configuracion()
        self.datos = {t: vacio(t) for t in COLUMNAS}
        self.parametros_simulacion = {}
        self.fecha_actual = hoy()   # editable en la pantalla del Modelo 1
        self.cargar_csv()
        self.reconstruir(usar_cache=True)

    # ------------------------------------------------------- persistencia
    def ruta(self, tipo):
        return os.path.join(DIRECTORIO_SALIDA, f"{tipo}.csv")

    def cargar_csv(self):
        """Lee los CSV de datos_salida/ (si existen)."""
        for tipo in COLUMNAS:
            if os.path.exists(self.ruta(tipo)):
                df = pd.read_csv(self.ruta(tipo), encoding="utf-8-sig")
                for c in FECHAS[tipo]:
                    df[c] = pd.to_datetime(df[c], errors="coerce")
                if "proveedor" in df.columns:
                    df["proveedor"] = df["proveedor"].fillna("")
                self.datos[tipo] = df
        ruta_par = os.path.join(DIRECTORIO_SALIDA, "parametros_simulacion.csv")
        if os.path.exists(ruta_par):
            df = pd.read_csv(ruta_par, encoding="utf-8-sig")
            self.parametros_simulacion = {
                str(k): (float(v) if pd.notna(pd.to_numeric(v, errors="coerce")) else v)
                for k, v in zip(df["parametro"], df["valor"])}

    def guardar_csv(self, tipo=None):
        """Guarda uno o todos los tipos de datos en datos_salida/."""
        asegurar_directorios()
        for t in ([tipo] if tipo else COLUMNAS):
            self.datos[t].to_csv(self.ruta(t), index=False, encoding="utf-8-sig",
                                 date_format="%Y-%m-%d %H:%M:%S")
            persistencia.subir(self.ruta(t))
        if tipo is None:
            ruta_par = os.path.join(DIRECTORIO_SALIDA, "parametros_simulacion.csv")
            pd.DataFrame({"parametro": list(self.parametros_simulacion),
                          "valor": list(self.parametros_simulacion.values())}).to_csv(
                ruta_par, index=False, encoding="utf-8-sig")
            persistencia.subir(ruta_par)

    def guardar_configuracion(self, config):
        self.config = config
        guardar_configuracion(config)
        self.reconstruir()

    def cargar_ejemplo(self, carpeta):
        """Copia los CSV de ejemplo a datos_salida/ y recarga todo."""
        import shutil
        asegurar_directorios()
        for nombre in os.listdir(carpeta):
            if nombre.endswith(".csv"):
                shutil.copy(os.path.join(carpeta, nombre), os.path.join(DIRECTORIO_SALIDA, nombre))
        self.datos = {t: vacio(t) for t in COLUMNAS}
        self.parametros_simulacion = {}
        self.cargar_csv()
        self.reconstruir()

    def borrar_todo(self):
        """Elimina todos los datos registrados (no borra la configuración)."""
        self.datos = {t: vacio(t) for t in COLUMNAS}
        self.parametros_simulacion = {}
        self.guardar_csv()
        self.reconstruir()

    # --------------------------------------------------------- importación
    def importar_archivos(self, rutas, tipo_forzado=None, reemplazar=True):
        """
        Importa uno o varios archivos. Si tipo_forzado es None, detecta el tipo
        de cada hoja. Devuelve un texto con el resumen de lo importado.
        """
        encontrados = {}
        mensajes = []
        for ruta in rutas:
            archivo = os.path.basename(ruta)
            hojas = leer_hojas(ruta)
            for nombre, df in hojas.items():
                if df is None or df.empty:
                    continue
                df.columns = [str(c) for c in df.columns]
                tipo = tipo_forzado or clasificar_hoja(archivo, nombre, df)
                if tipo == "parametros":
                    self.parametros_simulacion.update(leer_parametros_simulacion(df))
                    mensajes.insert(0, f"✔ Parámetros de la simulación: "
                                       f"{len(self.parametros_simulacion)} valores desde {archivo} / {nombre}.")
                    continue
                if tipo is None:
                    mensajes.append(f"• {archivo} / {nombre}: no se reconoció el contenido (omitida).")
                    continue
                conv = CONVERTIDORES["ventas" if tipo == "ventas_diarias" else tipo](df)
                if conv is None and tipo_forzado is None and "verdad" in normalizar_texto(archivo):
                    conv = convertir_precios(df, "precios_proveedor")
                    tipo = "precios_proveedor"
                if conv is None:
                    mensajes.append(f"• {archivo} / {nombre}: columnas no reconocidas para '{tipo}'.")
                    continue
                encontrados.setdefault(tipo, []).append((f"{archivo} / {nombre}", conv))

        # Ventas detalladas tienen prioridad sobre las ventas diarias resumidas
        if "ventas_diarias" in encontrados:
            if "ventas" in encontrados or not self.datos["ventas"].empty and not reemplazar:
                for origen, _ in encontrados.pop("ventas_diarias"):
                    mensajes.append(f"• {origen}: ventas diarias omitidas (se usan las ventas detalladas).")
            else:
                encontrados["ventas"] = encontrados.pop("ventas_diarias")

        if not encontrados:
            return "No se importó nada.\n" + "\n".join(mensajes)

        for tipo, lista in encontrados.items():
            df = pd.concat([d for _, d in lista], ignore_index=True)
            df, descartadas = limpiar_dataframe(df, FECHAS[tipo], POSITIVOS[tipo])
            if tipo == "compras":
                df["fecha_pedido"] = df["fecha_pedido"].fillna(df["fecha_llegada"])
                df["proveedor"] = df["proveedor"].fillna("").replace("nan", "")
            if not reemplazar:
                df = pd.concat([self.datos[tipo], df], ignore_index=True)
            orden = FECHAS[tipo][0]
            self.datos[tipo] = df.sort_values(orden, kind="stable").reset_index(drop=True)
            origenes = ", ".join(o for o, _ in lista)
            extra = f" ({descartadas} filas inválidas descartadas)" if descartadas else ""
            mensajes.insert(0, f"✔ {NOMBRES_TIPO[tipo]}: {len(df):,} registros desde {origenes}{extra}.")
        self.guardar_csv()
        self.reconstruir()
        mensajes.append(self.texto_rechazos())
        return "\n".join(m for m in mensajes if m)

    # ---------------------------------------------------- reconstrucción FIFO
    # Caché del FIFO: si los datos no cambiaron, el arranque no repite los 100 000+ movimientos
    CAMPOS_CACHE = ("tanques", "ventas_procesadas", "ventas_rechazadas", "historial_diario",
                    "estado_compras", "ventas_omitidas", "ultima_fecha")

    def _clave_cache(self):
        partes = [repr(self.config["capacidad_tanque"])]
        for t in ("compras", "ventas", "inventario_inicial"):
            r = self.ruta(t)
            partes.append(f"{os.path.getmtime(r)}:{os.path.getsize(r)}" if os.path.exists(r) else "-")
        return "|".join(partes)

    def reconstruir(self, usar_cache=False):
        """Reproduce todos los movimientos en orden y recalcula el FIFO."""
        import pickle
        ruta_cache = os.path.join(DIRECTORIO_SALIDA, ".cache_fifo.pkl")
        clave = self._clave_cache()
        self._cache_pronostico = {}
        self._cache_articulo = None
        if usar_cache and os.path.exists(ruta_cache):
            try:
                with open(ruta_cache, "rb") as f:
                    guardado = pickle.load(f)
                if guardado.get("clave") == clave:
                    for campo in self.CAMPOS_CACHE:
                        setattr(self, campo, guardado[campo])
                    self._ajustar_fecha()
                    return
            except Exception:
                pass   # caché dañada: se recalcula
        self._reconstruir_fifo()
        self._ajustar_fecha()
        try:
            with open(ruta_cache, "wb") as f:
                pickle.dump({"clave": clave, **{c: getattr(self, c) for c in self.CAMPOS_CACHE}}, f,
                            protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            pass

    def _ajustar_fecha(self):
        """
        Fecha de análisis: hoy, salvo que los datos terminen antes (por ejemplo, datos
        históricos o simulados); entonces se usa el último día con movimientos para que
        los pronósticos y decisiones no salgan 'atrasados' artificialmente.
        """
        if self.ultima_fecha is not None:
            ultimo = pd.Timestamp(self.ultima_fecha).normalize()
            self.fecha_actual = min(hoy(), ultimo + pd.Timedelta(days=1))

    def _reconstruir_fifo(self):
        cap = self.config["capacidad_tanque"]
        self.tanques = {p: TanqueFIFO(p, cap[p], guardar_historial=False) for p in PRODUCTOS}
        self._cache_pronostico = {}
        self._cache_articulo = None
        compras = self.datos["compras"]
        ventas = self.datos["ventas"]
        inv = self.datos["inventario_inicial"]

        eventos = []   # (fecha, orden, tipo, indice)
        inicio = {}
        for prod in PRODUCTOS:
            filas = inv[inv["producto"] == prod]
            if filas.empty:
                continue
            fila = filas.sort_values("fecha").iloc[0]
            inicio[prod] = pd.Timestamp(fila["fecha"]).normalize()
            eventos.append((inicio[prod] - pd.Timedelta(seconds=1), 0, "I", fila.name))

        self.estado_compras = {}
        for i, f in zip(compras.index, compras["fecha_llegada"]):
            eventos.append((f, 1, "C", i))
        for i, f in zip(ventas.index, ventas["fecha"]):
            eventos.append((f, 2, "V", i))
        eventos.sort(key=lambda e: (e[0], e[1]))

        procesadas, rechazadas, fotos = [], [], []
        ultimo_costo = {p: None for p in PRODUCTOS}
        omitidas = 0
        dia_actual = None
        c_prod, c_vol, c_cos = (compras["producto"].tolist(), compras["volumen"].tolist(),
                                compras["costo_galon"].tolist())
        v_prod, v_vol, v_pre = (ventas["producto"].tolist(), ventas["volumen"].tolist(),
                                ventas["precio"].tolist())
        pos_c = {i: k for k, i in enumerate(compras.index)}
        pos_v = {i: k for k, i in enumerate(ventas.index)}

        for fecha, _, tipo, idx in eventos:
            dia = fecha.normalize()
            if dia_actual is not None and dia != dia_actual:
                self._foto(fotos, dia_actual)
            dia_actual = dia

            if tipo == "I":
                fila = inv.loc[idx]
                prod = fila["producto"]
                d = pd.Timestamp(fila["fecha"]).normalize()
                vol_v = ventas.loc[(ventas["producto"] == prod) &
                                   (ventas["fecha"].dt.normalize() == d), "volumen"].sum()
                vol_c = compras.loc[(compras["producto"] == prod) &
                                    (compras["fecha_llegada"].dt.normalize() == d), "volumen"].sum()
                stock_ini = float(fila["stock"]) + vol_v - vol_c   # stock al inicio del día
                if stock_ini > 0:
                    self.tanques[prod].agregar_cisterna(fecha, min(stock_ini, cap[prod]),
                                                        float(fila["costo"]), origen="inventario inicial")
                ultimo_costo[prod] = float(fila["costo"])
            elif tipo == "C":
                k = pos_c[idx]
                prod = c_prod[k]
                if prod in inicio and fecha < inicio[prod]:
                    self.estado_compras[idx] = "Anterior al inventario inicial (ya incluida)"
                    continue
                if self.tanques[prod].agregar_cisterna(fecha, c_vol[k], c_cos[k]):
                    self.estado_compras[idx] = "Aceptada"
                    ultimo_costo[prod] = c_cos[k]
                else:
                    self.estado_compras[idx] = "Rechazada: " + self.tanques[prod].ultimo_error
            else:
                k = pos_v[idx]
                prod = v_prod[k]
                if prod in inicio and fecha < inicio[prod]:
                    omitidas += 1
                    continue
                try:
                    r = self.tanques[prod].registrar_venta(fecha, v_vol[k], v_pre[k])
                    procesadas.append((fecha, prod, r["volumen"], r["precio_venta"],
                                       r["costo_promedio"], r["margen"], r["utilidad"],
                                       ultimo_costo[prod]))
                except ErrorInventario as e:
                    rechazadas.append({"fecha": fecha, "producto": prod, "volumen": v_vol[k],
                                       "precio": v_pre[k], "motivo": str(e)})
        if dia_actual is not None:
            self._foto(fotos, dia_actual)

        self.ventas_procesadas = pd.DataFrame(procesadas, columns=[
            "fecha", "producto", "volumen", "precio", "costo_fifo", "margen", "utilidad",
            "costo_reposicion"])
        self.ventas_rechazadas = pd.DataFrame(rechazadas, columns=[
            "fecha", "producto", "volumen", "precio", "motivo"])
        self.historial_diario = pd.DataFrame(fotos, columns=[
            "fecha", "producto", "stock", "costo_promedio", "valor"])
        self.ventas_omitidas = omitidas
        self.ultima_fecha = max((e[0] for e in eventos), default=None)

    def _foto(self, fotos, dia):
        for p, t in self.tanques.items():
            fotos.append((dia, p, t.stock_actual(), t.costo_promedio_actual(), t.valor_inventario()))

    def texto_rechazos(self):
        """Resumen de movimientos rechazados para mostrar al usuario."""
        partes = []
        if len(self.ventas_rechazadas):
            partes.append(f"⚠ {len(self.ventas_rechazadas):,} ventas rechazadas por falta de stock.")
        n = sum(1 for v in self.estado_compras.values() if v.startswith("Rechazada"))
        if n:
            partes.append(f"⚠ {n} cisternas rechazadas por exceder la capacidad del tanque.")
        if self.ventas_omitidas:
            partes.append(f"ℹ {self.ventas_omitidas:,} ventas anteriores al inventario inicial no "
                          "se procesaron en el FIFO.")
        return "\n".join(partes)

    # ------------------------------------------------------ registro manual
    def _validar_orden(self, fecha):
        if self.ultima_fecha is not None and fecha < self.ultima_fecha:
            raise ErrorValidacion(
                "La fecha es anterior al último movimiento registrado "
                f"({self.ultima_fecha:%d/%m/%Y %H:%M}). En FIFO los movimientos deben "
                "registrarse en orden cronológico.")

    def registrar_venta(self, fecha, producto, volumen, precio):
        """Valida y registra una venta; devuelve el resultado FIFO."""
        fecha = validar_fecha(fecha)
        producto = validar_producto(producto)
        volumen = validar_numero_positivo(volumen, "Volumen")
        precio = validar_numero_positivo(precio, "Precio de venta")
        self._validar_orden(fecha)
        tanque = self.tanques[producto]
        if volumen > tanque.stock_actual() + 1e-6:
            raise ErrorValidacion(f"Venta rechazada: solo hay {tanque.stock_actual():,.2f} gal "
                                  f"de {producto} en el tanque.")
        nueva = pd.DataFrame([[fecha, producto, volumen, precio]], columns=COLUMNAS["ventas"])
        self.datos["ventas"] = pd.concat([self.datos["ventas"], nueva], ignore_index=True)
        self.guardar_csv("ventas")
        self.reconstruir()
        return self.ventas_procesadas.iloc[-1].to_dict() if len(self.ventas_procesadas) else None

    def registrar_compra(self, fecha, producto, volumen, costo, proveedor=""):
        """Valida y registra una cisterna."""
        fecha = validar_fecha(fecha)
        producto = validar_producto(producto)
        volumen = validar_numero_positivo(volumen, "Volumen")
        costo = validar_numero_positivo(costo, "Costo por galón")
        self._validar_orden(fecha)
        t = self.tanques[producto]
        if t.stock_actual() + volumen > t.capacidad_maxima + 1e-6:
            raise ErrorValidacion(
                f"Cisterna rechazada: el tanque de {producto} tiene {t.stock_actual():,.1f} gal y "
                f"capacidad {t.capacidad_maxima:,.0f} gal. Solo caben "
                f"{t.capacidad_maxima - t.stock_actual():,.1f} gal.")
        nueva = pd.DataFrame([[fecha, fecha, producto, volumen, costo, proveedor]],
                             columns=COLUMNAS["compras"])
        self.datos["compras"] = pd.concat([self.datos["compras"], nueva], ignore_index=True)
        self.guardar_csv("compras")
        self.reconstruir()

    # ------------------------------------------------------ datos de modelos
    def serie_precio_proveedor(self, producto):
        """
        Serie diaria del precio del proveedor. Si no se importaron precios del
        proveedor, se aproxima con el costo de las cisternas (fecha de pedido).
        Devuelve (serie, fuente).
        """
        pp = self.datos["precios_proveedor"]
        pp = pp[pp["producto"] == producto]
        if len(pp) >= 2:
            return modelo_croston.construir_serie_diaria(pp[["fecha", "precio"]]), "precios del proveedor"
        c = self.datos["compras"]
        c = c[c["producto"] == producto]
        df = pd.DataFrame({"fecha": c["fecha_pedido"].fillna(c["fecha_llegada"]),
                           "precio": c["costo_galon"]})
        return (modelo_croston.construir_serie_diaria(df),
                "costos de las cisternas (aproximación: no se importaron precios del proveedor)")

    def pronostico(self, producto, alfa=None, beta=None, optimizar=True):
        """Ejecuta (o recupera de caché) el Modelo 1 para un producto."""
        alfa = self.config["croston_alfa_inicial"] if alfa is None else alfa
        beta = self.config["croston_beta_inicial"] if beta is None else beta
        clave = (producto, alfa, beta, optimizar, self.fecha_actual)
        if clave not in self._cache_pronostico:
            serie, fuente = self.serie_precio_proveedor(producto)
            r = modelo_croston.pronosticar(serie, alfa, beta, optimizar, self.fecha_actual)
            r["fuente"] = fuente
            if fuente.startswith("costos"):
                r["advertencias"].insert(0, "Se usan los costos de cisternas como aproximación del "
                                            "precio del proveedor (importe precios del proveedor "
                                            "para mayor precisión).")
            self._cache_pronostico[clave] = r
        return self._cache_pronostico[clave]

    def demanda_base(self, producto, dias=28):
        """Promedio de galones vendidos por día en los últimos 'dias' días."""
        v = self.ventas_procesadas
        v = v[v["producto"] == producto]
        if v.empty:
            return 0.0, 0
        fin = v["fecha"].max().normalize()
        ini = fin - pd.Timedelta(days=dias - 1)
        rec = v[v["fecha"] >= ini]
        n_dias = max((fin - max(rec["fecha"].min().normalize(), ini)).days + 1, 1)
        return float(rec["volumen"].sum()) / n_dias, n_dias

    def precio_mercado(self, producto):
        """Precio de mercado (verdad oculta) o último precio del surtidor como referencia."""
        pm = self.datos["precio_mercado"]
        pm = pm[pm["producto"] == producto]
        if not pm.empty:
            return float(pm.sort_values("fecha")["precio"].iloc[-1]), "precio de mercado (último día)"
        ps = self.datos["precios_surtidor"]
        ps = ps[ps["producto"] == producto]
        if not ps.empty:
            return float(ps.sort_values("fecha")["precio"].iloc[-1]), "último precio del surtidor"
        v = self.ventas_procesadas
        v = v[v["producto"] == producto]
        if not v.empty:
            return float(v["precio"].iloc[-1]), "precio de la última venta"
        c = self.tanques[producto].costo_promedio_actual()
        return c * 1.08, "estimado (costo + 8 %), no hay precios registrados"

    def precio_optimo(self, producto, kappa=None, margen_min=None, margen_max=None,
                      horizonte=None, usar_pronostico=False):
        """Ejecuta el Modelo 2 con los datos actuales del producto."""
        cfg = self.config
        kappa = cfg["kappa"][producto] if kappa is None else kappa
        mmin = cfg["margen_minimo"] if margen_min is None else margen_min
        mmax = cfg["margen_maximo"] if margen_max is None else margen_max
        horizonte = cfg["horizonte_dias"] if horizonte is None else horizonte
        nota_h = "configurado"
        if usar_pronostico:
            pr = self.pronostico(producto)
            if pr.get("ok"):
                horizonte = float(min(max(round(pr["dias_hasta_cambio"]), 1), 30))
                nota_h = "días hasta el próximo cambio de precio (Modelo 1)"
        t = self.tanques[producto]
        c = t.costo_promedio_actual()
        d_base, n_dias = self.demanda_base(producto)
        p_merc, fuente_merc = self.precio_mercado(producto)
        r = modelo_precio_optimo.optimizar_precio(
            c, d_base, p_merc, kappa, mmin, mmax, horizonte, t.stock_actual(), t.capacidad_maxima)
        r.update({"costo": c, "d_base": d_base, "dias_demanda": n_dias, "p_mercado": p_merc,
                  "fuente_mercado": fuente_merc, "kappa": kappa, "margen_min": mmin,
                  "margen_max": mmax, "horizonte": horizonte, "nota_horizonte": nota_h,
                  "stock": t.stock_actual(), "capacidad": t.capacidad_maxima})
        if not r["ok"]:
            return r
        if n_dias < 7:
            r["advertencias"].append(f"La demanda base se calculó con solo {n_dias} día(s) de ventas.")
        r["sensibilidad"] = modelo_precio_optimo.tabla_sensibilidad(
            r["precio_recomendado"], c, d_base, kappa, p_merc, horizonte,
            r["limite_inferior"], r["limite_superior"])
        r["escenarios"] = modelo_precio_optimo.escenarios_kappa(
            c, d_base, p_merc, mmin, mmax, horizonte, t.stock_actual(), t.capacidad_maxima)
        r["politicas"] = modelo_precio_optimo.comparar_politicas(
            r, c, d_base, kappa, p_merc, cfg.get("margen_politica_fija", 0.08))
        r["curva"] = modelo_precio_optimo.curva_utilidad(c, d_base, kappa, p_merc)
        return r

    # ------------------------------------------------------------- reportes
    def reporte(self, periodo="D", producto=None):
        """
        Reporte por día ('D'), semana ('W') o mes ('M'): ventas, compras,
        utilidad, margen real (FIFO) vs margen esperado (precio vs costo de la
        última cisterna, que es lo que un administrador 'cree' que gana).
        """
        v = self.ventas_procesadas.copy()
        c = self.datos["compras"].copy()
        if producto:
            v = v[v["producto"] == producto]
            c = c[c["producto"] == producto]
        if v.empty:   # sin ventas procesadas no hay márgenes que reportar
            return pd.DataFrame()
        regla = {"D": "D", "W": "W-MON", "M": "MS"}[periodo]
        v["importe"] = v["volumen"] * v["precio"]
        v["costo_total"] = v["volumen"] * v["costo_fifo"]
        v["costo_rep_total"] = v["volumen"] * v["costo_reposicion"].fillna(v["costo_fifo"])
        g = v.set_index("fecha").resample(regla, label="left", closed="left").agg(
            {"volumen": "sum", "importe": "sum", "costo_total": "sum", "utilidad": "sum",
             "costo_rep_total": "sum"})
        cc = c.set_index("fecha_llegada")["volumen"].resample(regla, label="left", closed="left").sum()
        g = g.join(cc.rename("compras_gal"), how="outer").fillna(0)
        g["margen_real_pct"] = np.where(g["costo_total"] > 0,
                                        (g["importe"] - g["costo_total"]) / g["costo_total"].replace(0, np.nan), np.nan)
        g["margen_esperado_pct"] = np.where(g["costo_rep_total"] > 0,
                                            (g["importe"] - g["costo_rep_total"]) / g["costo_rep_total"].replace(0, np.nan), np.nan)
        g = g.reset_index().rename(columns={"index": "fecha", "fecha_llegada": "fecha"})
        g.columns = ["fecha"] + list(g.columns[1:])
        return g[["fecha", "volumen", "importe", "costo_total", "utilidad", "compras_gal",
                  "margen_real_pct", "margen_esperado_pct"]]

    def exportar_excel(self, ruta):
        """Exporta reportes, ventas procesadas, inventario y compras a Excel."""
        with pd.ExcelWriter(ruta, engine="openpyxl") as w:
            for nombre, per in (("Reporte_diario", "D"), ("Reporte_semanal", "W"), ("Reporte_mensual", "M")):
                self.reporte(per).to_excel(w, sheet_name=nombre, index=False)
            for p in PRODUCTOS:
                pd.DataFrame(self.tanques[p].detalle_capas()).to_excel(
                    w, sheet_name=f"Capas_{p}", index=False)
            self.historial_diario.to_excel(w, sheet_name="Historial_stock", index=False)
            self.ventas_procesadas.tail(100000).to_excel(w, sheet_name="Ventas_FIFO", index=False)
            c = self.datos["compras"].copy()
            c["estado"] = [self.estado_compras.get(i, "") for i in c.index]
            c.to_excel(w, sheet_name="Compras", index=False)
            self.ventas_rechazadas.to_excel(w, sheet_name="Ventas_rechazadas", index=False)


NOMBRES_TIPO = {
    "ventas": "Ventas", "compras": "Compras (cisternas)",
    "precios_surtidor": "Precios del surtidor", "precios_proveedor": "Precios del proveedor",
    "inventario_inicial": "Inventario inicial", "precio_mercado": "Precio de mercado diario",
    "ventas_perdidas": "Ventas perdidas (verdad oculta)",
}
