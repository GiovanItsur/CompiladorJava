from typing import Optional
import customtkinter as ctk

from ui_analizador import PantallaAnalizador
from ui_inicio import COLOR_FONDO, PantallaInicio


class VentanaPrincipal(ctk.CTk):
    def __init__(self) -> None:
        super().__init__(fg_color=COLOR_FONDO)

        self.title("Simulador de Etapa de Análisis de un Compilador")
        self.geometry("1340x820")
        self.minsize(1080, 700)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.pantalla_actual: Optional[ctk.CTkFrame] = None
        self.mostrar_pantalla_inicio()

    def _cambiar_pantalla(self, nueva_pantalla: ctk.CTkFrame) -> None:
        if self.pantalla_actual is not None:
            self.pantalla_actual.destroy()

        self.pantalla_actual = nueva_pantalla
        self.pantalla_actual.grid(row=0, column=0, sticky="nsew")

    def mostrar_pantalla_inicio(self) -> None:
        vista_inicio = PantallaInicio(
            master=self, al_iniciar=self.mostrar_pantalla_analizador
        )
        self._cambiar_pantalla(vista_inicio)

    def mostrar_pantalla_analizador(self) -> None:
        vista_analizador = PantallaAnalizador(
            master=self, al_volver=self.mostrar_pantalla_inicio
        )
        self._cambiar_pantalla(vista_analizador)


def main() -> None:
    ctk.set_appearance_mode("dark")
    app = VentanaPrincipal()
    app.mainloop()


if __name__ == "__main__":
    main()