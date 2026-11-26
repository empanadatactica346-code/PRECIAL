"""
Funciones auxiliares: redondeo peruano, formatos de moneda/volumen,
normalización de textos y búsqueda flexible de columnas.
"""
import math
import re
import unicodedata


# ---------------------------------------------------------------- redondeo
def redondeo_peruano(precio):
    """
    Redondea un precio al valor XX.X9 más cercano (costumbre peruana).
    Ej.: 24.83 -> 24.79 ; 24.86 -> 24.89 ; 21.40 -> 21.39
    """
    if precio is None or not math.isfinite(precio) or precio <= 0:
        return precio
    k = round((precio - 0.09) * 10)
    return round(k / 10 + 0.09, 2)


def redondeo_peruano_en_rango(precio, minimo, maximo):
    """
    Redondea a XX.X9 intentando respetar el rango [minimo, maximo].
    Devuelve (precio_redondeado, cumple_rango). Si ningún XX.X9 cae dentro
    del rango, devuelve el precio con 2 decimales y cumple_rango=False.
    """
    tol = 1e-9
    r = redondeo_peruano(precio)
    if minimo - tol <= r <= maximo + tol:
        return r, True
    candidatos = [round(r - 0.1, 2), round(r + 0.1, 2)]
    validos = [c for c in candidatos if minimo - tol <= c <= maximo + tol]
    if validos:
        return min(validos, key=lambda c: abs(c - precio)), True
    return round(precio, 2), False


# ----------------------------------------------------------------- formatos
def formato_moneda(valor, decimales=2, signo=False):
    """Ej.: 1234.5 -> 'S/ 1,234.50'. Con signo=True agrega '+' a positivos."""
    if valor is None or (isinstance(valor, float) and not math.isfinite(valor)):
        return "—"
    s = "+" if signo and valor > 0 else ("-" if valor < 0 else "")
    return f"{s}S/ {abs(valor):,.{decimales}f}"


def formato_galones(valor, decimales=1):
    """Ej.: 4523.5 -> '4,523.5 gal'."""
    if valor is None:
        return "—"
    return f"{valor:,.{decimales}f} gal"


def formato_pct(valor, decimales=1, signo=False):
    """Recibe una fracción (0.083) y devuelve '8.3%'."""
    if valor is None or (isinstance(valor, float) and not math.isfinite(valor)):
        return "—"
    s = "+" if signo and valor > 0 else ""
    return f"{s}{valor * 100:.{decimales}f}%"


def formato_fecha(fecha, con_hora=False):
    """Convierte una fecha a 'DD/MM/AAAA' (o 'DD/MM/AAAA HH:MM')."""
    if fecha is None:
        return "—"
    try:
        return fecha.strftime("%d/%m/%Y %H:%M" if con_hora else "%d/%m/%Y")
    except (AttributeError, ValueError):
        return str(fecha)


# ------------------------------------------------------------ normalización
def normalizar_texto(texto):
    """Minúsculas, sin tildes y con '_' en lugar de espacios/símbolos."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower().strip()
    return re.sub(r"[^a-z0-9]+", "_", texto).strip("_")


def tokens(texto):
    """Lista de palabras de un nombre de columna normalizado."""
    return normalizar_texto(texto).split("_")


def buscar_columna(df, *grupos):
    """
    Busca la primera columna cuyo nombre contenga TODAS las palabras de un
    grupo. Se prueban los grupos en orden. Ej.:
        buscar_columna(df, ["fecha", "llegada"], ["fecha"])
    """
    nombres = {c: normalizar_texto(c) for c in df.columns}
    for grupo in grupos:
        for original, norm in nombres.items():
            if all(palabra in norm for palabra in grupo):
                return original
    return None


ALIAS_PRODUCTOS = {
    "DB5": "DB5", "DIESEL": "DB5", "DIESEL_B5": "DB5", "D_B5": "DB5", "B5": "DB5",
    "GR": "GR", "REGULAR": "GR", "GASOLINA_REGULAR": "GR", "G90": "GR", "90": "GR",
    "GASOLINA_REGULAR_90": "GR", "GASOHOL_90": "GR",
    "GP": "GP", "PREMIUM": "GP", "GASOLINA_PREMIUM": "GP", "G95": "GP", "95": "GP",
    "GASOLINA_PREMIUM_95": "GP", "GASOHOL_95": "GP",
}


def normalizar_producto(valor):
    """Convierte variantes ('Diesel B5', 'db5', 'Premium') al código estándar."""
    clave = normalizar_texto(valor).upper()
    if clave in ALIAS_PRODUCTOS:
        return ALIAS_PRODUCTOS[clave]
    if "DIESEL" in clave or "DB5" in clave:
        return "DB5"
    if "PREMIUM" in clave or "95" in clave:
        return "GP"
    if "REGULAR" in clave or "90" in clave:
        return "GR"
    return None
