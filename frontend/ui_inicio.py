from typing import Callable
import customtkinter as ctk


# Paleta de colores extraída de la imagen de referencia
COLOR_FONDO: str = "#141517"
COLOR_PANEL: str = "#1d1f23"
COLOR_CREMA: str = "#e8d8c9"
COLOR_AZUL: str = "#4b607f"
COLOR_NARANJA: str = "#f3701e"
COLOR_NARANJA_HOVER: str = "#d65c12"
COLOR_TEXTO_OSCURO: str = "#16171a"


class PantallaInicio(ctk.CTkFrame):
    """
    Pantalla de bienvenida con estética retro moderna basada en la paleta:
    Crema (#e8d8c9), Azul Pizarra (#4b607f) y Naranja (#f3701e) sobre Carbón (#141517).
    """

    def __init__(self, master: ctk.CTk, al_iniciar: Callable[[], None]) -> None:
        super().__init__(master, fg_color=COLOR_FONDO)
        self.al_iniciar: Callable[[], None] = al_iniciar
        self._construir_interfaz()

    def _construir_interfaz(self) -> None:
        """Construye un layout de dos columnas: presentación a la izquierda y tarjetas a la derecha."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Contenedor principal centrado
        contenedor = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=COLOR_PANEL,
            border_width=2,
            border_color=COLOR_AZUL,
        )
        contenedor.grid(row=0, column=0, padx=60, pady=50, ipadx=25, ipady=25)
        contenedor.grid_columnconfigure(0, weight=5)
        contenedor.grid_columnconfigure(1, weight=4)

        # =====================================================================
        # COLUMNA IZQUIERDA: TÍTULO, DESCRIPCIÓN Y BOTÓN DE ACCIÓN
        # =====================================================================
        col_izq = ctk.CTkFrame(contenedor, fg_color="transparent")
        col_izq.grid(row=0, column=0, sticky="nsew", padx=(40, 25), pady=35)

        # Insignia superior en naranja retro
        insignia = ctk.CTkLabel(
            col_izq,
            text="  LENGUAJES Y AUTÓMATAS II • ITSUR  ",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLOR_NARANJA,
            text_color=COLOR_TEXTO_OSCURO,
            corner_radius=8,
            height=28,
        )
        insignia.pack(anchor="w", pady=(0, 18))

        # Título grande en color crema (#e8d8c9)
        lbl_titulo = ctk.CTkLabel(
            col_izq,
            text="Simulador de la\nEtapa de Análisis\nde un Compilador",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=COLOR_CREMA,
            justify="left",
        )
        lbl_titulo.pack(anchor="w", pady=(0, 16))

        # Subtítulo descriptivo
        lbl_subtitulo = ctk.CTkLabel(
            col_izq,
            text=(
                "Entorno interactivo para validación de código Java bajo la GLC v7.\n"
                "Ejecuta depuración, análisis léxico por ámbitos, descenso recursivo\n"
                "y verificación semántica de tipos en tiempo real."
            ),
            font=ctk.CTkFont(size=14),
            text_color="#a9b2c3",
            justify="left",
        )
        lbl_subtitulo.pack(anchor="w", pady=(0, 32))

        # Botón principal en naranja (#f3701e)
        btn_iniciar = ctk.CTkButton(
            col_izq,
            text="Iniciar Analizador  →",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLOR_NARANJA,
            hover_color=COLOR_NARANJA_HOVER,
            text_color=COLOR_TEXTO_OSCURO,
            width=240,
            height=52,
            corner_radius=14,
            command=self.al_iniciar,
        )
        btn_iniciar.pack(anchor="w", pady=(0, 20))

        # Pie de tarjeta con indicadores rápidos
        lbl_pie = ctk.CTkLabel(
            col_izq,
            text="GLC v7  •  6 Fases de Análisis  •  Actualización Continua",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_AZUL,
        )
        lbl_pie.pack(anchor="w", pady=(10, 0))

        # =====================================================================
        # COLUMNA DERECHA: 3 BLOQUES DE COLOR INSPIRADOS EN EL PÓSTER
        # =====================================================================
        col_der = ctk.CTkFrame(contenedor, fg_color="transparent")
        col_der.grid(row=0, column=1, sticky="nsew", padx=(15, 40), pady=35)

        self._crear_tarjeta_etapa(
            padre=col_der,
            numero="01",
            titulo="Depuración y Léxico",
            detalle="Limpieza de comentarios, colapso de ';' y Tabla de Símbolos por ámbito.",
            color_fondo=COLOR_CREMA,
            color_texto=COLOR_TEXTO_OSCURO,
            color_sub="#3b3834",
        )

        self._crear_tarjeta_etapa(
            padre=col_der,
            numero="02",
            titulo="Sintáctico (GLC v7)",
            detalle="Validación estricta de clase principal, método main e instrucciones.",
            color_fondo=COLOR_AZUL,
            color_texto=COLOR_CREMA,
            color_sub="#d0d8e4",
        )

        self._crear_tarjeta_etapa(
            padre=col_der,
            numero="03",
            titulo="Semántico de Tipos",
            detalle="Verificación de tipos (VTD vs VTF, VTC), retornos y variables locales.",
            color_fondo=COLOR_NARANJA,
            color_texto=COLOR_TEXTO_OSCURO,
            color_sub="#2b1608",
        )

    def _crear_tarjeta_etapa(
        self,
        padre: ctk.CTkFrame,
        numero: str,
        titulo: str,
        detalle: str,
        color_fondo: str,
        color_texto: str,
        color_sub: str,
    ) -> None:
        """Crea un bloque horizontal estilizado con los colores de la paleta."""
        bloque = ctk.CTkFrame(
            padre, corner_radius=16, fg_color=color_fondo, width=360, height=105
        )
        bloque.pack(fill="x", pady=8, ipadx=14, ipady=10)

        encabezado = ctk.CTkFrame(bloque, fg_color="transparent")
        encabezado.pack(fill="x", padx=16, pady=(8, 2))

        lbl_num = ctk.CTkLabel(
            encabezado,
            text=numero,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=color_texto,
        )
        lbl_num.pack(side="left")

        lbl_tit = ctk.CTkLabel(
            encabezado,
            text=titulo,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=color_texto,
        )
        lbl_tit.pack(side="left", padx=12)

        lbl_det = ctk.CTkLabel(
            bloque,
            text=detalle,
            font=ctk.CTkFont(size=12),
            text_color=color_sub,
            justify="left",
            wraplength=320,
        )
        lbl_det.pack(anchor="w", padx=16, pady=(0, 8))