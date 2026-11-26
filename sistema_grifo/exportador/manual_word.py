"""
Manual de usuario detallado en Word (MANUAL_PRECIAL.docx).

Usa el mismo contenido que el tutorial (interfaz/guia.py) y, si se le pasan,
capturas reales de cada pantalla.
"""
import os
from datetime import datetime

from interfaz.guia import INTRO, SECCIONES

FORMATOS = [
    ("Ventas", "fecha, producto, volumen (galones), precio", "Reporte de la consola o del sistema de caja."),
    ("Compras / cisternas", "fecha_llegada, producto, volumen, costo_galon (opcional: fecha_pedido, proveedor)",
     "Facturas o guías del proveedor."),
    ("Precios del proveedor", "fecha, producto, precio", "Lista de precios que envía el proveedor."),
    ("Inventario inicial", "fecha, producto, stock, costo", "Medición del tanque al iniciar."),
    ("Precio de mercado (opcional)", "fecha, producto, precio", "Precio de la competencia o referencial."),
]

PREGUNTAS = [
    ("Windows dice «Windows protegió su PC».", "Clic en «Más información» → «Ejecutar de todas formas». "
     "El programa no tiene firma digital comercial, pero no se conecta a internet."),
    ("¿Dónde se guardan mis datos?", "En la carpeta datos_salida, junto a PRECIAL.exe. Para respaldar o "
     "llevar sus datos a otra PC, copie la carpeta completa del programa."),
    ("Importé un archivo y faltan datos.", "Revise que tenga columnas de fecha y producto (DB5, GR o GP). "
     "Al terminar la importación el sistema muestra un resumen con lo que aceptó y rechazó."),
    ("¿Por qué el precio recomendado es más alto que el actual?", "Si el stock no alcanza hasta la próxima "
     "cisterna, el modelo sube el precio para vender menos galones con más margen y evitar quedarse sin "
     "combustible. La tarjeta lo indica con un aviso."),
    ("¿Qué significa «confianza» en el pronóstico?", "ALTA con más de 15 cambios de precio en el historial, "
     "MEDIA con 8 a 15 y BAJA con menos de 8."),
    ("Un archivo no se pudo guardar al exportar.", "Cierre en Excel o Word el archivo con el mismo nombre y "
     "vuelva a exportar."),
]


def generar_manual(ruta, capturas=None):
    """Escribe el manual en 'ruta'. capturas: {pantalla: ruta_png}."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt, RGBColor

    capturas = capturas or {}
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)

    def h(texto, nivel):
        t = doc.add_heading(texto, level=nivel)
        for r in t.runs:
            r.font.color.rgb = RGBColor(0x8A, 0x3B, 0x00)

    def tabla(cabecera, filas, anchos=None):
        tb = doc.add_table(rows=1, cols=len(cabecera))
        tb.style = "Light Grid Accent 2"
        for j, c in enumerate(cabecera):
            tb.rows[0].cells[j].text = c
        for f in filas:
            celdas = tb.add_row().cells
            for j, v in enumerate(f):
                celdas[j].text = v
        if anchos:
            for fila in tb.rows:
                for j, w in enumerate(anchos):
                    fila.cells[j].width = Cm(w)
        doc.add_paragraph()

    # Portada
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("⛽ PRECIAL")
    r.bold, r.font.size, r.font.color.rgb = True, Pt(36), RGBColor(0xE8, 0x78, 0x0C)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Manual de usuario\nGestión de inventario y optimización de precios para grifo")
    r.font.size = Pt(16)
    p = doc.add_paragraph(f"Versión local para Windows · {datetime.now():%d/%m/%Y}")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if "Inicio" in capturas:
        doc.add_picture(capturas["Inicio"], width=Cm(16))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_page_break()

    h("1. ¿Qué es PRECIAL?", 1)
    doc.add_paragraph(INTRO)
    h("Decisiones que apoya", 2)
    tabla(["Nivel", "Decisión", "Dónde se ve"],
          [["Gerencial", "Precio de venta de cada combustible", "Inicio y Precio óptimo (Modelo 2)"],
           ["Gerencial", "Cuándo revisar el precio (cambio del proveedor)", "Inicio y Pronóstico (Modelo 1)"],
           ["Gerencial", "Justificar la política de precios", "Validación y Exportar artículo"],
           ["Operativa", "Cuándo pedir cisterna", "Inicio (bloque OPERATIVA) e Inventario"],
           ["Operativa", "Control del costo real y del margen de cada venta", "Ventas e Inventario"]],
          [2.5, 7, 6])

    h("2. Instalación y primer uso", 1)
    for i, t in enumerate([
            "Descomprima el archivo ZIP en una carpeta (por ejemplo, Documentos\\PRECIAL). No lo ejecute "
            "desde dentro del ZIP.",
            "Abra PRECIAL.exe. No necesita internet ni instalar Python.",
            "La primera vez se cargan 6 meses de datos de ejemplo y aparece el tutorial guiado.",
            "Para usar sus datos: «Borrar todos los datos» en Inicio y luego «Importar datos».",
            "Repita el tutorial cuando quiera con «❓ Tutorial» en el menú lateral."], 1):
        doc.add_paragraph(f"{i}. {t}")
    h("Flujo de trabajo recomendado", 2)
    doc.add_paragraph("Importar datos → Tablero de decisiones → Modelo 1 y Modelo 2 → Validación → "
                      "Exportar artículo.")

    h("3. Pantallas y botones", 1)
    for n, sec in enumerate(SECCIONES, 1):
        h(f"3.{n} {sec['titulo']}  (menú: {sec['pantalla']})", 2)
        doc.add_paragraph(sec["para_que"])
        if sec["pantalla"] in capturas:
            doc.add_picture(capturas[sec["pantalla"]], width=Cm(16))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            c = doc.add_paragraph(f"Figura {n}. Pantalla {sec['pantalla']}.")
            c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.runs[0].italic = True
        tabla(["Botón o zona", "Qué hace"], [[a, b] for a, b in sec["elementos"]], [5, 11])
        p = doc.add_paragraph()
        p.add_run("Decisión que apoya: ").bold = True
        p.add_run(sec["decision"])

    h("4. Formato de los archivos a importar", 1)
    doc.add_paragraph("Se aceptan Excel (.xlsx) y CSV. Los nombres de columnas son flexibles y un mismo "
                      "Excel puede tener varias hojas: el sistema detecta qué contiene cada una. "
                      "Productos válidos: DB5 (Diésel B5), GR (Gasolina Regular 90), GP (Gasolina Premium 95).")
    tabla(["Archivo", "Columnas", "Origen habitual"], [list(f) for f in FORMATOS], [3.5, 7.5, 5])

    h("5. Cómo se calculan los resultados", 1)
    for t, d in [("Inventario FIFO", "Cada cisterna es un lote con su costo; las ventas consumen primero el "
                                     "lote más antiguo. Así se conoce el costo real de cada galón vendido."),
                 ("Modelo 1 — Croston TSB", "Suaviza la probabilidad y la magnitud de los cambios de precio del "
                                            "proveedor para estimar cuándo y cuánto cambiará."),
                 ("Modelo 2 — Precio óptimo", "Maximiza U(p) = (p − c)·D(p)·T con demanda logística, margen entre "
                                              "5 % y 15 % y sin vender más que el stock disponible. El precio se "
                                              "redondea a XX.X9.")]:
        p = doc.add_paragraph()
        p.add_run(t + ": ").bold = True
        p.add_run(d)

    h("6. Exportar el artículo", 1)
    doc.add_paragraph("En «Exportar artículo» → «Exportar todo para el artículo» se genera la carpeta "
                      "exportaciones con: BORRADOR_ARTICULO.docx (artículo IMRaD con sus cifras, tablas, figuras "
                      "y matriz de decisiones; complete las partes resaltadas [COMPLETAR]), "
                      "TABLAS_PARA_ARTICULO.xlsx, la carpeta graficos con 6 figuras a 300 DPI y "
                      "RESUMEN_RESULTADOS.txt.")

    h("7. Preguntas frecuentes", 1)
    for q, a in PREGUNTAS:
        p = doc.add_paragraph()
        p.add_run(q).bold = True
        doc.add_paragraph(a)

    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    doc.save(ruta)
    return ruta
