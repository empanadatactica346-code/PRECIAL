"""
"Exportar todo para el artículo": 5 tablas en Excel + 6 gráficos PNG 300 DPI
+ RESUMEN_RESULTADOS.txt con los hallazgos en texto plano
+ BORRADOR_ARTICULO.docx (artículo IMRaD con cifras, tablas y figuras).
"""
import os
from datetime import datetime

from configuracion import DIRECTORIO_DATOS
from exportador import articulo_word, graficos_articulo, tablas_articulo

DIRECTORIO_EXPORTACIONES = os.path.join(DIRECTORIO_DATOS, "exportaciones")


def texto_resumen(sistema, tablas, resultados):
    """Arma el resumen en texto plano (para copiar y pegar al artículo)."""
    lineas = ["RESUMEN DE RESULTADOS — Sistema de Gestión y Optimización de Precios para Grifo",
              f"Generado: {datetime.now():%d/%m/%Y %H:%M}", "=" * 78, ""]
    secciones = [("1. PLANTEAMIENTO DEL PROBLEMA (Tabla 1)", "Tabla1_Estadisticas_Descriptivas"),
                 ("2. METODOLOGÍA (Tabla 2)", "Tabla2_Parametros_Modelos"),
                 ("3. RESULTADOS — MODELO 1, Croston TSB (Tabla 3)", "Tabla3_Resultados_Modelo1"),
                 ("4. RESULTADOS — MODELO 2, precio óptimo (Tabla 4)", "Tabla4_Comparacion_Politicas"),
                 ("5. CONCLUSIONES (Tabla 5)", "Tabla5_Resumen_Conclusiones")]
    for titulo, hoja in secciones:
        lineas += [titulo, "-" * len(titulo), tablas[hoja]["interpretacion"], ""]
    lineas += ["HALLAZGOS CLAVE", "---------------"]
    for fila in tablas["Tabla5_Resumen_Conclusiones"]["df"].itertuples(index=False):
        lineas.append(f"• {fila[0]}: {fila[1]}  ({fila[2]})")
    if resultados["advertencias"]:
        lineas += ["", "ADVERTENCIAS Y LIMITACIONES", "---------------------------"]
        lineas += [f"• {a}" for a in resultados["advertencias"]]
    lineas += ["", "• La demanda de la simulación sigue una función logística con κ supuesto; los resultados "
                   "del Modelo 2 dependen de ese supuesto.",
               "", "Fuente: Elaboración propia."]
    return "\n".join(lineas)


def exportar_todo(sistema, carpeta=None, progreso=None):
    """
    Genera todo en 'carpeta' (por defecto exportaciones/).
    progreso(fraccion, texto) se llama para actualizar la barra.
    Devuelve dict con las rutas generadas.
    """
    carpeta = carpeta or DIRECTORIO_EXPORTACIONES
    os.makedirs(carpeta, exist_ok=True)
    avisar = progreso or (lambda f, t: None)

    tablas = tablas_articulo.construir_tablas(sistema, lambda f, t: avisar(f * 0.5, t))
    resultados = tablas_articulo.calcular_resultados(sistema)
    avisar(0.5, "Escribiendo TABLAS_PARA_ARTICULO.xlsx")
    excel = tablas_articulo.exportar_tablas(tablas, os.path.join(carpeta, "TABLAS_PARA_ARTICULO.xlsx"))
    graficos = graficos_articulo.generar_graficos(
        sistema, resultados, os.path.join(carpeta, "graficos"),
        lambda f, t: avisar(0.55 + f * 0.4, t))
    avisar(0.96, "Escribiendo RESUMEN_RESULTADOS.txt")
    txt = os.path.join(carpeta, "RESUMEN_RESULTADOS.txt")
    with open(txt, "w", encoding="utf-8") as f:
        f.write(texto_resumen(sistema, tablas, resultados))
    avisar(0.98, "Escribiendo BORRADOR_ARTICULO.docx")
    docx = articulo_word.generar_articulo(sistema, tablas, resultados, graficos,
                                          os.path.join(carpeta, "BORRADOR_ARTICULO.docx"))
    avisar(1.0, "Exportación completa")
    return {"excel": excel, "graficos": graficos, "resumen": txt, "articulo": docx, "carpeta": carpeta}
