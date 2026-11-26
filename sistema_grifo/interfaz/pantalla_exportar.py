"""Pantalla 'Exportar para el artículo': todo en un clic, con vista previa."""
import os
import traceback
from tkinter import filedialog, messagebox

import customtkinter as ctk

from exportador import graficos_articulo, reporte_completo, tablas_articulo
from interfaz.componentes import Tabla, TextoRico, explicacion, titulo
from interfaz.pantalla_validacion import mostrar_tabla

HOJAS = ["Tabla1_Estadisticas_Descriptivas", "Tabla2_Parametros_Modelos", "Tabla3_Resultados_Modelo1",
         "Tabla4_Comparacion_Politicas", "Tabla5_Resumen_Conclusiones"]


class PantallaExportar(ctk.CTkScrollableFrame):
    """Genera TABLAS_PARA_ARTICULO.xlsx, 6 gráficos PNG 300 DPI y RESUMEN_RESULTADOS.txt."""

    def __init__(self, padre, app):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        self.carpeta = reporte_completo.DIRECTORIO_EXPORTACIONES
        self.tablas = None
        titulo(self, "Exportar para el artículo").pack(anchor="w")
        explicacion(self, "Genera de una sola vez todo lo que necesita para redactar el artículo: tablas con "
                          "formato académico (título, notas, fuente e interpretación), gráficos listos para "
                          "insertar y un resumen en texto para copiar y pegar.").pack(anchor="w", pady=(2, 8))
        lista = ctk.CTkFrame(self)
        lista.pack(fill="x", pady=4)
        ctk.CTkLabel(lista, text="Se va a generar:", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        for i, h in enumerate(HOJAS):
            ctk.CTkLabel(lista, text=f"☑ Hoja {i+1}: {h}", font=("Segoe UI", 11)).grid(
                row=1 + i, column=0, sticky="w", padx=14)
        for i, n in enumerate(graficos_articulo.NOMBRES):
            ctk.CTkLabel(lista, text=f"☑ Fig. {i+1}: {n}", font=("Segoe UI", 11)).grid(
                row=1 + i, column=1, sticky="w", padx=14)
        ctk.CTkLabel(lista, text="☑ BORRADOR_ARTICULO.docx (artículo completo en Word: resumen, metodología, "
                                 "resultados, matriz de decisiones y conclusiones)\n"
                                 "☑ RESUMEN_RESULTADOS.txt (hallazgos en texto plano)",
                     justify="left",
                     font=("Segoe UI", 11)).grid(row=7, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 8))

        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", pady=6)
        ctk.CTkButton(f, text="Carpeta de destino…", command=self.elegir_carpeta).pack(side="left")
        self.lbl_carpeta = ctk.CTkLabel(f, text=self.carpeta, font=("Segoe UI", 11))
        self.lbl_carpeta.pack(side="left", padx=10)
        ctk.CTkButton(self, text="📊 Exportar todo para el artículo", height=44,
                      font=("Segoe UI", 15, "bold"), command=self.exportar).pack(anchor="w", pady=6)
        self.barra = ctk.CTkProgressBar(self, height=14)
        self.barra.pack(fill="x", pady=(4, 0))
        self.barra.set(0)
        self.estado = ctk.CTkLabel(self, text="", font=("Segoe UI", 11))
        self.estado.pack(anchor="w")

        ctk.CTkLabel(self, text="Vista previa de las tablas", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", pady=(12, 2))
        p = ctk.CTkFrame(self, fg_color="transparent")
        p.pack(fill="x")
        self.hoja = ctk.CTkComboBox(p, values=HOJAS, width=260, command=lambda _: self.vista_previa())
        self.hoja.set(HOJAS[0])
        self.hoja.pack(side="left")
        ctk.CTkButton(p, text="Calcular vista previa", command=self.calcular).pack(side="left", padx=8)
        self.tabla = Tabla(self, alto=12)
        self.tabla.pack(fill="x", pady=4)
        self.interp = TextoRico(self, alto=110)
        self.interp.pack(fill="x", pady=4)

    def actualizar(self):
        self.tablas = None
        self.tabla.cargar(["Vista previa"], [["Presione «Calcular vista previa»"]])

    def _progreso(self, fraccion, texto):
        self.barra.set(fraccion)
        self.estado.configure(text=texto)
        self.update()

    def elegir_carpeta(self):
        c = filedialog.askdirectory(initialdir=self.carpeta, title="Carpeta de destino")
        if c:
            self.carpeta = c
            self.lbl_carpeta.configure(text=c)

    def calcular(self):
        if self.app.sistema.datos["ventas"].empty:
            messagebox.showwarning("Sin datos", "Importe primero los archivos de datos.")
            return
        try:
            self.tablas = tablas_articulo.construir_tablas(self.app.sistema, self._progreso)
            self._progreso(1, "Vista previa lista")
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error", str(e))
            return
        self.vista_previa()

    def vista_previa(self):
        if self.tablas is None:
            return
        t = self.tablas[self.hoja.get()]
        mostrar_tabla(self.tabla, t)
        self.interp.escribir([(t["titulo"] + "\n", "titulo"), (t["interpretacion"], None)])

    def exportar(self):
        if self.app.sistema.datos["ventas"].empty:
            messagebox.showwarning("Sin datos", "Importe primero los archivos de datos.")
            return
        try:
            self.app.configure(cursor="watch")
            out = reporte_completo.exportar_todo(self.app.sistema, self.carpeta, self._progreso)
        except OSError as e:
            messagebox.showerror("Error", f"No se pudo guardar (¿algún archivo está abierto en Excel?).\n{e}")
            return
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error", str(e))
            return
        finally:
            self.app.configure(cursor="")
        messagebox.showinfo("Exportación completa",
                            f"Exportación completa. Archivos guardados en la carpeta "
                            f"'{os.path.basename(out['carpeta'])}/':\n\n{out['carpeta']}")
        try:
            os.startfile(out["carpeta"])
        except (AttributeError, OSError):
            pass
