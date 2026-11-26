"""
Validación de datos ingresados por el usuario o importados de archivos.
"""
import pandas as pd

from configuracion import PRODUCTOS


class ErrorValidacion(Exception):
    """Dato ingresado inválido (mensaje listo para mostrar al usuario)."""


def validar_producto(producto):
    """Verifica que el producto sea DB5, GR o GP."""
    if producto not in PRODUCTOS:
        raise ErrorValidacion(f"Producto inválido: '{producto}'. Use {', '.join(PRODUCTOS)}.")
    return producto


def validar_numero_positivo(valor, nombre):
    """Convierte a número y verifica que sea mayor que cero."""
    try:
        numero = float(str(valor).replace(",", "").strip())
    except (TypeError, ValueError):
        raise ErrorValidacion(f"'{nombre}' debe ser un número (se recibió '{valor}').")
    if numero <= 0:
        raise ErrorValidacion(f"'{nombre}' debe ser mayor que cero (no se permiten negativos).")
    return numero


def validar_fecha(valor, nombre="Fecha"):
    """Convierte texto (AAAA-MM-DD [HH:MM]) a fecha."""
    try:
        fecha = pd.to_datetime(str(valor).strip(), dayfirst=False)
    except (TypeError, ValueError):
        raise ErrorValidacion(f"'{nombre}' no es válida. Use el formato AAAA-MM-DD HH:MM.")
    if pd.isna(fecha):
        raise ErrorValidacion(f"'{nombre}' está vacía.")
    return fecha


def limpiar_dataframe(df, columnas_fecha, columnas_positivas):
    """
    Elimina filas con fechas inválidas, productos desconocidos o números
    no positivos. Devuelve (df_limpio, filas_descartadas).
    """
    if df is None or df.empty:
        return df, 0
    n_inicial = len(df)
    df = df.copy()
    for c in columnas_fecha:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in columnas_positivas:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=list(columnas_fecha[:1]) + list(columnas_positivas))
    if "producto" in df.columns:
        df = df[df["producto"].isin(PRODUCTOS)]
    for c in columnas_positivas:
        df = df[df[c] > 0]
    return df.reset_index(drop=True), n_inicial - len(df)
