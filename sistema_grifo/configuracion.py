"""
Parámetros del sistema del grifo.

Los valores por defecto están en CONFIGURACION. Los cambios hechos desde la
pantalla de Configuración se guardan en datos_salida/configuracion.csv
(columnas: clave, valor) para que también puedan abrirse con Excel.
"""
import copy
import csv
import json
import os
import sys

# Si corre como .exe (PyInstaller), las carpetas de datos quedan junto al .exe
if getattr(sys, "frozen", False):
    DIRECTORIO_BASE = os.path.dirname(sys.executable)
else:
    DIRECTORIO_BASE = os.path.dirname(os.path.abspath(__file__))
# En la web (Railway) los datos se guardan en un volumen persistente:
# la variable de entorno GRIFO_DATOS indica su ruta (ej. /data).
def _directorio_escribible(ruta):
    """Devuelve ruta si se puede escribir en ella; si no, la carpeta del programa."""
    try:
        os.makedirs(ruta, exist_ok=True)
        prueba = os.path.join(ruta, ".prueba")
        with open(prueba, "w") as f:
            f.write("ok")
        os.remove(prueba)
        return ruta
    except OSError:
        return DIRECTORIO_BASE


DIRECTORIO_DATOS = _directorio_escribible(os.environ["GRIFO_DATOS"]) if os.environ.get("GRIFO_DATOS")     else DIRECTORIO_BASE
DIRECTORIO_ENTRADA = os.path.join(DIRECTORIO_DATOS, "datos_entrada")
DIRECTORIO_SALIDA = os.path.join(DIRECTORIO_DATOS, "datos_salida")
# Datos de ejemplo incluidos con el programa (dentro del .exe: sys._MEIPASS)
DIRECTORIO_EJEMPLO = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))),
                                  "datos_ejemplo")
ZONA_HORARIA = os.environ.get("TZ_GRIFO", "America/Lima")


def hoy():
    """Fecha de hoy en la hora de Perú (el servidor web puede estar en otra zona)."""
    import pandas as pd
    return pd.Timestamp.now(tz=ZONA_HORARIA).tz_localize(None).normalize()
ARCHIVO_CONFIGURACION = os.path.join(DIRECTORIO_SALIDA, "configuracion.csv")

CONFIGURACION = {
    "productos": ["DB5", "GR", "GP"],
    "nombres_productos": {
        "DB5": "Diésel B5",
        "GR": "Gasolina Regular 90",
        "GP": "Gasolina Premium 95",
    },
    "capacidad_tanque": {
        "DB5": 12000,  # galones
        "GR": 7000,
        "GP": 5500,
    },
    "margen_minimo": 0.05,    # 5 %
    "margen_maximo": 0.15,    # 15 %
    "kappa": {
        "DB5": 18,
        "GR": 20,
        "GP": 19,
    },
    "croston_alfa_inicial": 0.15,
    "croston_beta_inicial": 0.15,
    "horizonte_dias": 7,
    "margen_politica_fija": 0.08,   # política A de comparación (8 %)
    "alerta_stock_pct": 0.20,       # alerta cuando el tanque baja del 20 %
    "moneda": "S/",
    "unidad_volumen": "galones",
}

PRODUCTOS = CONFIGURACION["productos"]


def asegurar_directorios():
    """Crea las carpetas de entrada y salida si no existen."""
    os.makedirs(DIRECTORIO_ENTRADA, exist_ok=True)
    os.makedirs(DIRECTORIO_SALIDA, exist_ok=True)


def cargar_configuracion():
    """Devuelve la configuración: valores por defecto + lo guardado en CSV."""
    config = copy.deepcopy(CONFIGURACION)
    if os.path.exists(ARCHIVO_CONFIGURACION):
        try:
            with open(ARCHIVO_CONFIGURACION, newline="", encoding="utf-8-sig") as f:
                for fila in csv.DictReader(f):
                    clave = fila.get("clave")
                    if clave in config:
                        config[clave] = json.loads(fila["valor"])
        except (OSError, ValueError, KeyError):
            pass  # si el archivo está dañado se usan los valores por defecto
    return config


def guardar_configuracion(config):
    """Guarda la configuración en datos_salida/configuracion.csv."""
    asegurar_directorios()
    with open(ARCHIVO_CONFIGURACION, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f)
        escritor.writerow(["clave", "valor"])
        for clave, valor in config.items():
            escritor.writerow([clave, json.dumps(valor, ensure_ascii=False)])
    from utilidades import persistencia
    persistencia.subir(ARCHIVO_CONFIGURACION)
