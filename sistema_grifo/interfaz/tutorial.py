"""
Tutorial guiado de bienvenida: se muestra la primera vez que se abre el
programa y cuando se pulsa «❓ Tutorial». En cada paso abre la pantalla
correspondiente, resalta su botón en el menú y explica qué hace cada parte.
"""
import os

import customtkinter as ctk

from configuracion import DIRECTORIO_SALIDA, asegurar_directorios
from interfaz.componentes import FUENTE
from interfaz.guia import AYUDA_FINAL, INTRO, SECCIONES

MARCA = os.path.join(DIRECTORIO_SALIDA, ".tutorial_visto")
NARANJA, OSCURO, SUAVE = "#E8780C", "#2B1D0E", "#7A6A55"


def ya_visto():
    return os.path.exists(MARCA)


def marcar_visto():
    asegurar_directorios()
    with open(MARCA, "w", encoding="utf-8") as f:
        f.write("ok")


class Tutorial(ctk.CTkToplevel):
    """Ventana flotante de pasos (Anterior / Siguiente / Saltar)."""

    def __init__(self, app):
        super().__init__(app, fg_color="white")
        self.app = app
        self.pasos = ([{"pantalla": "Inicio", "titulo": "¡Bienvenido a PRECIAL! 👋", "para_que": INTRO,
                        "elementos": [], "decision": "En los próximos pasos verá qué hace cada sección. "
                                                     "Puede salir cuando quiera con «Saltar»."}]
                      + SECCIONES
                      + [{"pantalla": "Inicio", "titulo": "¡Listo para empezar! 🚀",
                          "para_que": "Flujo recomendado: 1) Importar datos  →  2) revisar el Tablero de "
                                      "decisiones  →  3) confirmar en Modelo 1 y Modelo 2  →  4) Validación  "
                                      "→  5) Exportar artículo.",
                          "elementos": [], "decision": AYUDA_FINAL}])
        self.i = 0
        self.resaltado = None
        self.title("Tutorial de PRECIAL")
        self.resizable(False, False)
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self.cerrar)

        cab = ctk.CTkFrame(self, fg_color=NARANJA, corner_radius=0, height=6)
        cab.pack(fill="x")
        cuerpo = ctk.CTkFrame(self, fg_color="white")
        cuerpo.pack(fill="both", expand=True, padx=24, pady=(16, 8))
        self.contador = ctk.CTkLabel(cuerpo, text="", font=(FUENTE, 11, "bold"), text_color=NARANJA)
        self.contador.pack(anchor="w")
        self.lbl_titulo = ctk.CTkLabel(cuerpo, text="", font=(FUENTE, 20, "bold"), text_color=OSCURO,
                                       justify="left", anchor="w")
        self.lbl_titulo.pack(anchor="w", pady=(2, 6))
        self.lbl_para = ctk.CTkLabel(cuerpo, text="", font=(FUENTE, 13), text_color=OSCURO, justify="left",
                                     wraplength=470, anchor="w")
        self.lbl_para.pack(anchor="w")
        self.lista = ctk.CTkFrame(cuerpo, fg_color="#FFF8EC", corner_radius=12)
        self.lista.pack(fill="x", pady=10)
        self.lbl_dec = ctk.CTkLabel(cuerpo, text="", font=(FUENTE, 12, "bold"), text_color="#067647",
                                    justify="left", wraplength=470, anchor="w")
        self.lbl_dec.pack(anchor="w")

        self.puntos = ctk.CTkFrame(self, fg_color="white")
        self.puntos.pack(pady=(4, 0))
        self.marcas = []
        for _ in self.pasos:
            m = ctk.CTkFrame(self.puntos, width=8, height=8, corner_radius=4, fg_color="#E5D5BC")
            m.pack(side="left", padx=2)
            self.marcas.append(m)

        pie = ctk.CTkFrame(self, fg_color="white")
        pie.pack(fill="x", padx=24, pady=(10, 18))
        ctk.CTkButton(pie, text="Saltar tutorial", width=110, fg_color="transparent", text_color=SUAVE,
                      hover_color="#F4EBDD", command=self.cerrar).pack(side="left")
        self.btn_sig = ctk.CTkButton(pie, text="Siguiente →", width=130, height=36, corner_radius=10,
                                     fg_color=NARANJA, font=(FUENTE, 13, "bold"), command=self.siguiente)
        self.btn_sig.pack(side="right")
        self.btn_ant = ctk.CTkButton(pie, text="← Anterior", width=110, height=36, corner_radius=10,
                                     fg_color="transparent", border_width=1, border_color=NARANJA,
                                     text_color=NARANJA, hover_color="#FFF1D6", command=self.anterior)
        self.btn_ant.pack(side="right", padx=8)
        self.bind("<Right>", lambda e: self.siguiente())
        self.bind("<Left>", lambda e: self.anterior())
        self.bind("<Escape>", lambda e: self.cerrar())
        self.mostrar_paso()
        self.after(50, self._enfocar)

    def _enfocar(self):
        self.lift()
        self.focus_force()
        self.grab_set()

    def _posicionar(self):
        self.update_idletasks()
        a = self.app
        # Solo se fija la posición: el tamaño lo da el contenido (evita recortes con escala de Windows)
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = a.winfo_rootx() + a.winfo_width() - w - 40
        y = a.winfo_rooty() + max(20, (a.winfo_height() - h) // 2)
        self.wm_geometry(f"+{max(0, x)}+{max(0, y)}")

    def mostrar_paso(self):
        paso = self.pasos[self.i]
        self.app.mostrar(paso["pantalla"])
        if self.resaltado:
            self.resaltado.configure(border_width=0)
        self.resaltado = self.app.botones.get(paso["pantalla"])
        if self.resaltado and 0 < self.i < len(self.pasos) - 1:
            self.resaltado.configure(border_width=2, border_color="#F2B705")
        else:
            self.resaltado = None

        n = len(self.pasos)
        self.contador.configure(text=f"PASO {self.i + 1} DE {n}" + (
            f"  ·  MENÚ: {paso['pantalla'].upper()}" if 0 < self.i < n - 1 else ""))
        self.lbl_titulo.configure(text=paso["titulo"])
        self.lbl_para.configure(text=paso["para_que"])
        for w in self.lista.winfo_children():
            w.destroy()
        if paso["elementos"]:
            self.lista.pack(fill="x", pady=10, before=self.lbl_dec)
            for nombre, texto in paso["elementos"]:
                f = ctk.CTkFrame(self.lista, fg_color="transparent")
                f.pack(fill="x", padx=12, pady=3)
                ctk.CTkLabel(f, text=f"▸ {nombre}", font=(FUENTE, 12, "bold"), text_color="#A63A00",
                             anchor="w", justify="left", wraplength=440).pack(anchor="w")
                ctk.CTkLabel(f, text=texto, font=(FUENTE, 11), text_color=OSCURO, anchor="w",
                             justify="left", wraplength=440).pack(anchor="w", padx=(14, 0))
        else:
            self.lista.pack_forget()
        es_seccion = 0 < self.i < n - 1
        self.lbl_dec.configure(text=("✔ Decisión que apoya: " if es_seccion else "") + paso["decision"],
                               text_color="#067647" if es_seccion else SUAVE)
        for k, m in enumerate(self.marcas):
            m.configure(fg_color=NARANJA if k == self.i else ("#F2B705" if k < self.i else "#E5D5BC"),
                        width=18 if k == self.i else 8)
        self.btn_ant.configure(state="normal" if self.i else "disabled")
        self.btn_sig.configure(text="Comenzar ✓" if self.i == n - 1 else "Siguiente →")
        self._posicionar()

    def siguiente(self):
        if self.i >= len(self.pasos) - 1:
            self.cerrar()
            return
        self.i += 1
        self.mostrar_paso()

    def anterior(self):
        if self.i:
            self.i -= 1
            self.mostrar_paso()

    def cerrar(self):
        if self.resaltado:
            self.resaltado.configure(border_width=0)
        marcar_visto()
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
        self.app.mostrar("Inicio")
