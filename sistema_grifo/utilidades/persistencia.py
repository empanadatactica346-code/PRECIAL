"""
Persistencia opcional en PostgreSQL.

Si existe la variable de entorno DATABASE_URL, los archivos CSV de datos_salida/
(ventas, compras, precios, configuración...) se guardan comprimidos en una tabla
de Postgres y se restauran al arrancar. Así los datos sobreviven a los reinicios
de un servidor sin disco (por ejemplo, el plan gratuito de Render).
Sin DATABASE_URL no hace nada y todo sigue funcionando con archivos locales.
"""
import gzip
import os

ultimo_error = ""


def activa():
    """True si hay una base de datos configurada."""
    return bool(os.environ.get("DATABASE_URL"))


def _conectar():
    import psycopg
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    con = psycopg.connect(url, autocommit=True, connect_timeout=20)
    con.execute("CREATE TABLE IF NOT EXISTS grifo_archivos ("
                "nombre TEXT PRIMARY KEY, contenido BYTEA NOT NULL, "
                "actualizado TIMESTAMPTZ NOT NULL DEFAULT now())")
    return con


def descargar_todo(directorio):
    """Restaura en 'directorio' todos los archivos guardados. Devuelve cuántos."""
    global ultimo_error
    if not activa():
        return 0
    try:
        os.makedirs(directorio, exist_ok=True)
        with _conectar() as con:
            filas = con.execute("SELECT nombre, contenido FROM grifo_archivos").fetchall()
        for nombre, contenido in filas:
            with open(os.path.join(directorio, nombre), "wb") as f:
                f.write(gzip.decompress(bytes(contenido)))
        ultimo_error = ""
        return len(filas)
    except Exception as e:   # no detener la app si la base falla
        ultimo_error = f"{type(e).__name__}: {e}"
        print("[persistencia] error al restaurar:", ultimo_error)
        return 0


def subir(ruta):
    """Guarda (o reemplaza) un archivo en la base de datos."""
    global ultimo_error
    if not activa() or not os.path.exists(ruta):
        return False
    try:
        with open(ruta, "rb") as f:
            datos = gzip.compress(f.read(), compresslevel=6)
        with _conectar() as con:
            con.execute("INSERT INTO grifo_archivos (nombre, contenido, actualizado) "
                        "VALUES (%s, %s, now()) ON CONFLICT (nombre) DO UPDATE "
                        "SET contenido = EXCLUDED.contenido, actualizado = now()",
                        (os.path.basename(ruta), datos))
        ultimo_error = ""
        return True
    except Exception as e:
        ultimo_error = f"{type(e).__name__}: {e}"
        print("[persistencia] error al guardar:", ultimo_error)
        return False


def estado():
    """Texto corto para mostrar en la interfaz."""
    if not activa():
        return "💾 Datos: archivos locales (se pierden al reiniciar en servidores sin disco)"
    if ultimo_error:
        return f"⚠ Base de datos con error: {ultimo_error[:120]}"
    return "💾 Datos guardados en PostgreSQL"
