"""Pantalla de validación contra la verdad oculta (para el artículo)."""
import os
import traceback
from tkinter import filedialog, messagebox

import customtkinter as ctk

from configuracion import DIRECTORIO_ENTRADA, PRODUCTOS
from exportador import graficos_articulo, tablas_articulo
from exportador.reporte_completo import DIRECTORIO_EXPORTACIONES
from interfaz.componentes import COLORES_PRODUCTO, Grafico, Tabla, TextoRico, explicacion, titulo


def mostrar_tabla(widget, tabla):
    """Carga una tabla del artículo (dict con 'df') en un widget Tabla."""
    df = tabla["df"]
    widget.cargar(list(df.columns), [list(f) for f in df.itertuples(index=False)],
                  [max(90, min(220, len(str(c)) * 8)) for c in df.columns])


class PantallaValidacion(ctk.CTkScrollableFrame):
    """Backtest del Modelo 1 y simulación de 6 meses del Modelo 2."""

    def __init__(self, padre, app):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        self.tablas = None
        titulo(self, "Validación contra la verdad oculta").pack(anchor="w")
        explicacion(self, "Aquí se comprueba qué tan bien habrían funcionado los modelos. Modelo 1: en cada "
                          "cambio de precio del proveedor, se pronostica usando SOLO los datos anteriores "
                          "(rolling-origin) y se compara con lo que pasó. Modelo 2: se simulan los 6 meses con "
                          "dos reglas de precio (A = costo FIFO + 8 %, B = precio óptimo) con las mismas "
                          "cisternas y la misma demanda.").pack(anchor="w", pady=(2, 8))
        b = ctk.CTkFrame(self, fg_color="transparent")
        b.pack(anchor="w", pady=4)
        ctk.CTkButton(b, text="📂 Cargar VERDAD_OCULTA_simulacion.xlsx",
                      command=self.cargar_verdad).pack(side="left", padx=(0, 8))
        ctk.CTkButton(b, text="▶ Ejecutar validación", command=self.ejecutar).pack(side="left", padx=(0, 8))
        ctk.CTkButton(b, text="Exportar validación completa", command=self.exportar).pack(side="left")
        self.texto = TextoRico(self, alto=170)
        self.texto.pack(fill="x", pady=6)
        ctk.CTkLabel(self, text="Desempeño del Modelo 1 (Croston TSB)",
                     font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(8, 2))
        self.t1 = Tabla(self, alto=4)
        self.t1.pack(fill="x", pady=4)
        self.g1 = Grafico(self, alto=3.2)
        self.g1.pack(fill="x", pady=4)
        ctk.CTkLabel(self, text="Comparación de políticas de precio (6 meses)",
                     font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(8, 2))
        self.t2 = Tabla(self, alto=10)
        self.t2.pack(fill="x", pady=4)

    def actualizar(self):
        s = self.app.sistema
        tiene = {k: len(s.datos[k]) > 0 for k in ("precios_proveedor", "precio_mercado", "ventas_perdidas")}
        seg = [("Estado de la verdad oculta:\n", "titulo")]
        for k, nombre in (("precios_proveedor", "Lista de precios del proveedor"),
                          ("precio_mercado", "Precio de mercado diario"), ("ventas_perdidas", "Ventas perdidas")):
            seg.append((f"{'✔' if tiene[k] else '✖'} {nombre}\n", "ok" if tiene[k] else "alerta"))
        seg.append((f"{'✔' if s.parametros_simulacion else '✖'} Parámetros de la simulación\n",
                    "ok" if s.parametros_simulacion else "alerta"))
        if not all(tiene.values()):
            seg.append(("Sin estos datos la validación usa aproximaciones (se indica en cada tabla).", "gris"))
        else:
            seg.append(("Presione «Ejecutar validación».", "gris"))
        self.texto.escribir(seg)

    def cargar_verdad(self):
        ruta = filedialog.askopenfilename(title="Seleccione VERDAD_OCULTA_simulacion.xlsx",
                                          initialdir=DIRECTORIO_ENTRADA, filetypes=[("Excel", "*.xlsx *.xls")])
        if ruta:
            self.app.ejecutar_importacion([ruta], reemplazar=True)

    def ejecutar(self):
        s = self.app.sistema
        if s.datos["ventas"].empty:
            messagebox.showwarning("Sin datos", "Importe primero ventas, compras y la verdad oculta.")
            return
        try:
            self.app.configure(cursor="watch")
            self.update()
            self.tablas = tablas_articulo.construir_tablas(s)
            r = tablas_articulo.calcular_resultados(s)
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error", str(e))
            return
        finally:
            self.app.configure(cursor="")
        # En pantalla se muestran las versiones completas (con RMSE, MAPE, quiebres, etc.)
        m1, m2 = tablas_articulo.tabla_modelo1(r), tablas_articulo.tabla_modelo2(r)
        mostrar_tabla(self.t1, m1)
        mostrar_tabla(self.t2, m2)
        seg = [("Modelo 1: ", "b"), (self.tablas["Tabla3_Resultados_Modelo1"]["interpretacion"] + "\n\n", None),
               ("Modelo 2: ", "b"), (self.tablas["Tabla4_Comparacion_Politicas"]["interpretacion"] + "\n", None)]
        for a in r["advertencias"]:
            seg.append(("⚠ " + a + "\n", "alerta"))
        self.texto.escribir(seg)
        self.g1.limpiar()
        for i, p in enumerate(PRODUCTOS, 1):
            ax = self.g1.figura.add_subplot(1, 3, i)
            bt = r["productos"][p]["backtest"]
            ax.set_title(f"{p}: real vs pronosticado", fontsize=9)
            if bt.empty:
                continue
            lim = max(bt["intervalo_real"].max(), bt["intervalo_pronosticado"].max()) + 1
            ax.plot([0, lim], [0, lim], "--", color="#888888", lw=0.8)
            ax.scatter(bt["intervalo_real"], bt["intervalo_pronosticado"], s=12, color=COLORES_PRODUCTO[p])
            ax.set_xlabel("Real (días)", fontsize=8)
            ax.set_ylabel("Pronosticado (días)", fontsize=8)
            ax.grid(alpha=0.3)
        self.g1.dibujar()

    def exportar(self):
        if self.tablas is None:
            self.ejecutar()
            if self.tablas is None:
                return
        s = self.app.sistema
        r = tablas_articulo.calcular_resultados(s)
        try:
            # Archivo de respaldo (no es parte de las 5 tablas del artículo)
            completo = {"Desempeno_Modelo1": tablas_articulo.tabla_modelo1(r),
                        "Comparacion_Politicas": tablas_articulo.tabla_modelo2(r),
                        **tablas_articulo.tablas_internas(s)}
            ruta = tablas_articulo.exportar_tablas(
                completo, os.path.join(DIRECTORIO_EXPORTACIONES, "VALIDACION_MODELOS.xlsx"))
            carpeta = os.path.join(DIRECTORIO_EXPORTACIONES, "graficos")
            os.makedirs(carpeta, exist_ok=True)
            for f in (graficos_articulo.fig04, graficos_articulo.fig06):
                f(s, r, carpeta)
        except OSError as e:
            messagebox.showerror("Error", f"No se pudo guardar (¿archivo abierto en Excel?).\n{e}")
            return
        messagebox.showinfo("Exportado", f"Validación guardada en:\n{ruta}\ny los gráficos 3 y 5 en:\n{carpeta}")
