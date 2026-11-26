"""
Sistema de Gestión y Optimización de Precios para Grifo — punto de entrada.

Ejecutar:
    pip install -r requisitos.txt
    python principal.py
"""
import os
import sys
import traceback
from tkinter import filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk  # noqa: E402

from configuracion import DIRECTORIO_EJEMPLO, DIRECTORIO_ENTRADA, PRODUCTOS  # noqa: E402
from datos.gestor_datos import SistemaGrifo  # noqa: E402
from interfaz.pantalla_inicio import PantallaInicio  # noqa: E402


def aplicar_tema_naranja():
    """Tema de colores naranja / dorado / amarillo para todos los controles."""
    t = ctk.ThemeManager.theme
    naranja, oscuro, dorado = ["#E8780C", "#E8780C"], ["#C25F00", "#C25F00"], ["#F2B705", "#F2B705"]
    t["CTkButton"].update(fg_color=naranja, hover_color=oscuro)
    t["CTkCheckBox"].update(fg_color=naranja, hover_color=oscuro, border_color=["#C25F00", "#C25F00"])
    t["CTkProgressBar"].update(progress_color=dorado, fg_color=["#F3E3C3", "#F3E3C3"])
    t["CTkSegmentedButton"].update(selected_color=naranja, selected_hover_color=oscuro,
                                   fg_color=["#F3D9A4", "#F3D9A4"], unselected_color=["#F3D9A4", "#F3D9A4"],
                                   unselected_hover_color=["#F2C66B", "#F2C66B"], text_color=["#2B1D0E", "#2B1D0E"])
    t["CTkEntry"].update(border_color=["#E0B46A", "#E0B46A"])
    t["CTkComboBox"].update(border_color=["#E0B46A", "#E0B46A"], button_color=naranja,
                            button_hover_color=oscuro)
    t["CTkFrame"].update(fg_color=["#FCEBC9", "#FCEBC9"], top_fg_color=["#FFF3DA", "#FFF3DA"])
    t["CTkScrollbar"].update(button_color=["#E0B46A", "#E0B46A"], button_hover_color=naranja)


class AplicacionGrifo(ctk.CTk):
    """Ventana principal con menú lateral."""

    # Cada pantalla se importa y construye solo cuando se abre (arranque rápido)
    PANTALLAS = [("Inicio", None), ("Ventas", "pantalla_ventas:PantallaVentas"),
                 ("Compras", "pantalla_compras:PantallaCompras"),
                 ("Inventario", "pantalla_inventario:PantallaInventario"),
                 ("Pronóstico (Modelo 1)", "pantalla_pronostico:PantallaPronostico"),
                 ("Precio óptimo (Modelo 2)", "pantalla_precio:PantallaPrecio"),
                 ("Reportes", "pantalla_reportes:PantallaReportes"),
                 ("Validación", "pantalla_validacion:PantallaValidacion"),
                 ("Exportar artículo", "pantalla_exportar:PantallaExportar"),
                 ("Configuración", "pantalla_configuracion:PantallaConfiguracion")]

    ICONOS = {"Inicio": "🏠", "Ventas": "🧾", "Compras": "🚚", "Inventario": "🛢",
              "Pronóstico (Modelo 1)": "📅", "Precio óptimo (Modelo 2)": "🎯", "Reportes": "📊",
              "Validación": "✅", "Exportar artículo": "📝", "Configuración": "⚙"}

    @staticmethod
    def _clase(ref):
        if ref is None:
            return PantallaInicio
        import importlib
        modulo, clase = ref.split(":")
        return getattr(importlib.import_module("interfaz." + modulo), clase)

    def __init__(self):
        aplicar_tema_naranja()
        super().__init__(fg_color="#FFF8EC")
        ctk.set_appearance_mode("light")
        self.title("PRECIAL — Gestión y Optimización de Precios para Grifo")
        self.geometry("1280x820")
        self.minsize(1050, 650)
        icono = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "precial.ico")
        if os.path.exists(icono):   # customtkinter fija su propio icono a los 200 ms: se reemplaza después
            self.after(250, lambda: self.iconbitmap(icono))
        self.sistema = SistemaGrifo()
        # Primera vez en una PC nueva: cargar los datos de ejemplo para que todo funcione al instante
        from configuracion import DIRECTORIO_SALIDA
        if (not os.path.exists(os.path.join(DIRECTORIO_SALIDA, "ventas.csv"))
                and os.path.isdir(DIRECTORIO_EJEMPLO)):
            self.sistema.cargar_ejemplo(DIRECTORIO_EJEMPLO)

        menu = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#2B1D0E")
        menu.pack(side="left", fill="y")
        menu.pack_propagate(False)
        ctk.CTkLabel(menu, text="⛽ PRECIAL", font=("Segoe UI", 24, "bold"),
                     text_color="#F2B705").pack(pady=(22, 0))
        ctk.CTkLabel(menu, text="Precio · Inventario · Decisión", font=("Segoe UI", 10),
                     text_color="#C9A86A").pack(pady=(0, 16))
        self.contenedor = ctk.CTkFrame(self, fg_color="transparent")
        self.contenedor.pack(side="left", fill="both", expand=True, padx=16, pady=12)

        self.pantallas, self.botones, self.pendientes = {}, {}, set()
        self.clases = dict(self.PANTALLAS)
        for nombre, clase in self.PANTALLAS:
            self.botones[nombre] = ctk.CTkButton(
                menu, text=f"{self.ICONOS.get(nombre, '•')}   {nombre}", anchor="w", height=38,
                corner_radius=10, font=("Segoe UI", 13), fg_color="transparent",
                hover_color="#5C3A10", text_color="#FFE8B0", command=lambda n=nombre: self.mostrar(n))
            self.botones[nombre].pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(menu, text="Modelos Cuantitativos\ny de Optimización", font=("Segoe UI", 10),
                     text_color="#C9A86A").pack(side="bottom", pady=12)
        ayuda = ctk.CTkFrame(menu, fg_color="transparent")
        ayuda.pack(side="bottom", fill="x", padx=10, pady=(0, 4))
        ctk.CTkButton(ayuda, text="❓ Tutorial", height=34, corner_radius=10, fg_color="#5C3A10",
                      hover_color="#7A5418", text_color="#FFE8B0", width=105,
                      command=self.abrir_tutorial).pack(side="left", expand=True, fill="x", padx=(0, 3))
        ctk.CTkButton(ayuda, text="📘 Manual", height=34, corner_radius=10, fg_color="#F2B705",
                      hover_color="#D4A000", text_color="#2B1D0E", width=105,
                      command=self.exportar_manual).pack(side="left", expand=True, fill="x", padx=(3, 0))
        self.actual = None
        self.pendientes = set()
        self.mostrar("Inicio")
        from interfaz import tutorial
        if not tutorial.ya_visto():   # primera vez que se abre: tutorial guiado
            self.after(700, self.abrir_tutorial)

    def abrir_tutorial(self):
        from interfaz.tutorial import Tutorial
        if getattr(self, "_tutorial", None) is not None and self._tutorial.winfo_exists():
            self._tutorial.lift()
            return
        self._tutorial = Tutorial(self)

    def exportar_manual(self, abrir=True):
        """Genera MANUAL_PRECIAL.docx con capturas reales de cada pantalla y lo abre."""
        from exportador.manual_word import generar_manual
        from exportador.reporte_completo import DIRECTORIO_EXPORTACIONES
        from utilidades.captura import capturar_ventana
        carpeta = os.path.join(DIRECTORIO_EXPORTACIONES, "capturas_manual")
        os.makedirs(carpeta, exist_ok=True)
        anterior, capturas = self.actual, {}
        self.configure(cursor="watch")
        try:
            for nombre, _ in self.PANTALLAS:
                self.mostrar(nombre)
                for _ in range(6):
                    self.update()
                ruta = os.path.join(carpeta, f"{len(capturas) + 1:02d}.png")
                if capturar_ventana(self, ruta):
                    capturas[nombre] = ruta
            self.mostrar(anterior)
            ruta = generar_manual(os.path.join(DIRECTORIO_EXPORTACIONES, "MANUAL_PRECIAL.docx"), capturas)
        except OSError as e:
            messagebox.showerror("Error", f"No se pudo guardar el manual (¿está abierto en Word?).\n{e}")
            return None
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error", str(e))
            return None
        finally:
            self.configure(cursor="")
        if abrir:
            messagebox.showinfo("Manual exportado", f"Manual guardado en:\n{ruta}")
            try:
                os.startfile(ruta)
            except (AttributeError, OSError):
                pass
        return ruta

    def mostrar(self, nombre):
        """Muestra una pantalla (y la actualiza si sus datos cambiaron)."""
        if self.actual:
            self.pantallas[self.actual].pack_forget()
            self.botones[self.actual].configure(fg_color="transparent", text_color="#FFE8B0")
        self.actual = nombre
        self.botones[nombre].configure(fg_color="#E8780C", text_color="white")
        if nombre not in self.pantallas:   # se construye la primera vez que se abre (arranque rápido)
            self.configure(cursor="watch")
            self.update_idletasks()
            self.pantallas[nombre] = self._clase(self.clases[nombre])(self.contenedor, self)
            self.pendientes.add(nombre)
        self.pantallas[nombre].pack(fill="both", expand=True)
        if nombre in self.pendientes:
            self.pendientes.discard(nombre)
            self._actualizar(nombre)

    def _actualizar(self, nombre):
        try:
            self.configure(cursor="watch")
            self.update_idletasks()
            self.pantallas[nombre].actualizar()
        except Exception as e:  # mostrar el error en lugar de cerrar el programa
            traceback.print_exc()
            messagebox.showerror("Error", f"Ocurrió un error al actualizar '{nombre}':\n{e}")
        finally:
            self.configure(cursor="")

    def refrescar_todo(self):
        """Marca todas las pantallas como desactualizadas y refresca la visible."""
        self.pendientes = set(self.pantallas) - {self.actual}
        self._actualizar(self.actual)

    def ejecutar_importacion(self, rutas, tipo=None, reemplazar=True):
        """Importa archivos mostrando el resumen al usuario."""
        self.configure(cursor="watch")
        self.update()
        try:
            resumen = self.sistema.importar_archivos(list(rutas), tipo, reemplazar)
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error al importar", str(e))
            return
        finally:
            self.configure(cursor="")
        self.refrescar_todo()
        messagebox.showinfo("Importación terminada", resumen)

    def importar_todo(self):
        rutas = filedialog.askopenfilenames(
            title="Seleccione los archivos a importar", initialdir=DIRECTORIO_ENTRADA,
            filetypes=[("Excel o CSV", "*.xlsx *.xls *.csv")])
        if rutas:
            self.ejecutar_importacion(rutas)

    def cargar_ejemplo(self):
        """Carga los datos de ejemplo incluidos con el programa (6 meses simulados)."""
        if not os.path.isdir(DIRECTORIO_EJEMPLO):
            messagebox.showerror("Sin datos de ejemplo", f"No se encontró la carpeta: {DIRECTORIO_EJEMPLO}")
            return
        if not self.sistema.datos["ventas"].empty and not messagebox.askyesno(
                "Confirmar", "Esto reemplaza los datos actuales por los de ejemplo. ¿Continuar?"):
            return
        self.configure(cursor="watch")
        self.update()
        try:
            self.sistema.cargar_ejemplo(DIRECTORIO_EJEMPLO)
        finally:
            self.configure(cursor="")
        self.refrescar_todo()

    def borrar_datos(self):
        if messagebox.askyesno("Confirmar", "¿Borrar TODAS las ventas, compras, precios e inventario "
                                            "registrados? Esta acción no se puede deshacer."):
            self.sistema.borrar_todo()
            self.refrescar_todo()


def exportar_sin_ventana(carpeta):
    """PRECIAL.exe --exportar CARPETA : genera todo el material del artículo sin abrir la ventana."""
    from configuracion import DIRECTORIO_SALIDA
    from exportador import reporte_completo
    s = SistemaGrifo()
    if not os.path.exists(os.path.join(DIRECTORIO_SALIDA, "ventas.csv")) and os.path.isdir(DIRECTORIO_EJEMPLO):
        s.cargar_ejemplo(DIRECTORIO_EJEMPLO)
    reporte_completo.exportar_todo(s, carpeta)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--exportar":
        exportar_sin_ventana(sys.argv[2])
    else:
        AplicacionGrifo().mainloop()
