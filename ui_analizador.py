from tkinter import filedialog, ttk
from typing import Callable, List, Optional, Set
import customtkinter as ctk

from backend.depurador import depurar_codigo
from backend.lexer import analizar_lexico
from backend.models import ErrorCompilador, Instruccion, Simbolo, Token
from backend.parser import analizar_sintactico_semantico


# Paleta de colores retro moderna
COLOR_FONDO: str = "#141517"
COLOR_PANEL: str = "#1d1f23"
COLOR_EDITOR: str = "#18191c"
COLOR_CREMA: str = "#e8d8c9"
COLOR_AZUL: str = "#4b607f"
COLOR_AZUL_HOVER: str = "#3a4c66"
COLOR_NARANJA: str = "#f3701e"
COLOR_NARANJA_HOVER: str = "#d65c12"
COLOR_TEXTO_OSCURO: str = "#16171a"
COLOR_ERROR_ROJO: str = "#ff4d4d"

# Programa válido de prueba (0 errores) basado en la GLC v7
CODIGO_EJEMPLO: str = """// Inciso 1 a 6: programa COMPLETAMENTE VÁLIDO (0 errores).
// Usa lo que la GLC v7 sí deriva: package, import simple, atributos, un método con
// return, main, objetos, if/else, switch con default y println.
package tienda;
import utilerias.Calculadora;
public class Tienda {
    int inventario = 50;
    private String nombre = "Papeleria";
    public int calcular(int precio, int cantidad) {
        int total = (precio + 1) * cantidad;
        return total;
    }
    public static void main(String[] args) {
        int cantidad = 3;
        double precio = 19.99;
        float descuento = 0.5f;
        char letra = 'A';
        boolean activo = true;
        String texto = "ITSUR";
        Tienda tienda = new Tienda();
        int largo = texto.length();
        cantidad = cantidad + 2 * largo;
        activo = !activo;
        if (cantidad > 2) {
            precio = precio * 2;
        } else {
            precio = 0;
        }
        switch (cantidad) {
            default:
                cantidad = 0;
                break;
        }
        System.out.println(precio);
    }
}"""


class PantallaAnalizador(ctk.CTkFrame):
    """
    Pantalla principal con Editor de Código de altura completa a la izquierda
    y Pestañas a la derecha estilizadas con la paleta Crema / Azul Pizarra / Naranja.
    """

    def __init__(self, master: ctk.CTk, al_volver: Callable[[], None]) -> None:
        super().__init__(master, fg_color=COLOR_FONDO)
        self.al_volver: Callable[[], None] = al_volver
        self._after_id: Optional[str] = None

        self._configurar_estilo_tablas()
        self._construir_interfaz()
        self._cargar_codigo_ejemplo()

    def _configurar_estilo_tablas(self) -> None:
        """Estiliza ttk.Treeview con fondo carbón, texto crema y cabeceras en azul pizarra."""
        estilo = ttk.Style()
        estilo.theme_use("clam")

        estilo.configure(
            "Compilador.Treeview",
            background=COLOR_EDITOR,
            foreground=COLOR_CREMA,
            fieldbackground=COLOR_EDITOR,
            rowheight=28,
            borderwidth=0,
            font=("Segoe UI", 11),
        )
        estilo.configure(
            "Compilador.Treeview.Heading",
            background=COLOR_AZUL,
            foreground=COLOR_CREMA,
            relief="flat",
            font=("Segoe UI", 11, "bold"),
        )
        estilo.map(
            "Compilador.Treeview",
            background=[("selected", COLOR_AZUL_HOVER)],
        )
        estilo.map(
            "Compilador.Treeview.Heading",
            background=[("active", COLOR_AZUL_HOVER)],
        )

    def _construir_interfaz(self) -> None:
        """Divide la pantalla en: Barra superior, Editor (Izquierda) y Pestañas (Derecha)."""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # =====================================================================
        # 1. BARRA SUPERIOR DE ACCIONES
        # =====================================================================
        barra_sup = ctk.CTkFrame(
            self,
            height=58,
            corner_radius=14,
            fg_color=COLOR_PANEL,
            border_width=1,
            border_color=COLOR_AZUL,
        )
        barra_sup.grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(12, 6)
        )

        btn_volver = ctk.CTkButton(
            barra_sup,
            text="← Inicio",
            width=90,
            height=34,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_AZUL,
            text_color=COLOR_CREMA,
            hover_color=COLOR_AZUL_HOVER,
            command=self.al_volver,
        )
        btn_volver.pack(side="left", padx=12, pady=10)

        lbl_titulo = ctk.CTkLabel(
            barra_sup,
            text="Simulador de Análisis (GLC v7)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLOR_CREMA,
        )
        lbl_titulo.pack(side="left", padx=8)

        self.lbl_resumen = ctk.CTkLabel(
            barra_sup,
            text="Símbolos: 0  |  Instrucciones: 0  |  Errores: 0",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_AZUL,
        )
        self.lbl_resumen.pack(side="left", padx=20)

        self.lbl_estado = ctk.CTkLabel(
            barra_sup,
            text="● Listo",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_CREMA,
        )
        self.lbl_estado.pack(side="right", padx=16)

        btn_limpiar = ctk.CTkButton(
            barra_sup,
            text="Limpiar",
            width=85,
            height=34,
            fg_color=COLOR_AZUL,
            hover_color=COLOR_AZUL_HOVER,
            text_color=COLOR_CREMA,
            command=self._limpiar_editor,
        )
        btn_limpiar.pack(side="right", padx=5, pady=10)

        btn_ejemplo = ctk.CTkButton(
            barra_sup,
            text="Cargar Ejemplo",
            width=125,
            height=34,
            fg_color=COLOR_AZUL,
            hover_color=COLOR_AZUL_HOVER,
            text_color=COLOR_CREMA,
            command=self._cargar_codigo_ejemplo,
        )
        btn_ejemplo.pack(side="right", padx=5, pady=10)

        btn_archivo = ctk.CTkButton(
            barra_sup,
            text="Abrir Archivo (.java / .txt)",
            width=180,
            height=34,
            fg_color=COLOR_NARANJA,
            hover_color=COLOR_NARANJA_HOVER,
            text_color=COLOR_TEXTO_OSCURO,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._abrir_archivo,
        )
        btn_archivo.pack(side="right", padx=5, pady=10)

        # =====================================================================
        # 2. MITAD IZQUIERDA (100% ALTURA): EDITOR DE CÓDIGO FUENTE
        # =====================================================================
        marco_editor = ctk.CTkFrame(
            self,
            corner_radius=14,
            fg_color=COLOR_PANEL,
            border_width=1,
            border_color=COLOR_AZUL,
        )
        marco_editor.grid(
            row=1, column=0, sticky="nsew", padx=(14, 7), pady=(6, 14)
        )
        marco_editor.grid_rowconfigure(1, weight=1)
        marco_editor.grid_columnconfigure(0, weight=1)

        lbl_editor = ctk.CTkLabel(
            marco_editor,
            text="Editor de Código Fuente (Java sin depurar)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_CREMA,
        )
        lbl_editor.grid(row=0, column=0, sticky="w", padx=14, pady=(10, 6))

        self.txt_codigo = ctk.CTkTextbox(
            marco_editor,
            font=ctk.CTkFont(family="Consolas", size=14),
            fg_color=COLOR_EDITOR,
            text_color=COLOR_CREMA,
            border_width=1,
            border_color="#2b3038",
            wrap="none",
            undo=True,
        )
        self.txt_codigo.grid(
            row=1, column=0, sticky="nsew", padx=12, pady=(0, 12)
        )
        self.txt_codigo.bind("<KeyRelease>", self._al_escribir_codigo)

        # =====================================================================
        # 3. MITAD DERECHA (100% ALTURA): PESTAÑAS DE RESULTADOS
        # =====================================================================
        self.pestanas = ctk.CTkTabview(
            self,
            corner_radius=14,
            fg_color=COLOR_PANEL,
            border_width=1,
            border_color=COLOR_AZUL,
            segmented_button_fg_color=COLOR_EDITOR,
            segmented_button_selected_color=COLOR_NARANJA,
            segmented_button_selected_hover_color=COLOR_NARANJA_HOVER,
            segmented_button_unselected_color=COLOR_AZUL,
            segmented_button_unselected_hover_color=COLOR_AZUL_HOVER,
            text_color=COLOR_CREMA,
        )
        self.pestanas.grid(
            row=1, column=1, sticky="nsew", padx=(7, 14), pady=(6, 14)
        )

        tab_depurado = self.pestanas.add("1. Código Depurado")
        tab_simbolos = self.pestanas.add("2. Tabla de Símbolos")
        tab_instrucciones = self.pestanas.add("3. Instrucciones Válidas")
        tab_errores = self.pestanas.add("4. Tabla de Errores")

        # --- Pestaña 1: Código Depurado ---
        tab_depurado.grid_rowconfigure(0, weight=1)
        tab_depurado.grid_columnconfigure(0, weight=1)

        self.txt_depurado = ctk.CTkTextbox(
            tab_depurado,
            font=ctk.CTkFont(family="Consolas", size=14),
            fg_color=COLOR_EDITOR,
            text_color=COLOR_CREMA,
            wrap="none",
            state="disabled",
        )
        self.txt_depurado.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        # --- Pestaña 2: Tabla de Símbolos (ID, Lexema, Token) ---
        tab_simbolos.grid_rowconfigure(0, weight=1)
        tab_simbolos.grid_columnconfigure(0, weight=1)

        self.tabla_simbolos_view = ttk.Treeview(
            tab_simbolos,
            columns=("id", "lexema", "token"),
            show="headings",
            style="Compilador.Treeview",
        )
        self.tabla_simbolos_view.heading("id", text="ID")
        self.tabla_simbolos_view.heading("lexema", text="Lexema")
        self.tabla_simbolos_view.heading("token", text="Token")

        self.tabla_simbolos_view.column("id", width=90, anchor="center", stretch=False)
        self.tabla_simbolos_view.column("lexema", width=260, anchor="w")
        self.tabla_simbolos_view.column("token", width=140, anchor="center")

        scroll_simbolos = ttk.Scrollbar(
            tab_simbolos,
            orient="vertical",
            command=self.tabla_simbolos_view.yview,
        )
        self.tabla_simbolos_view.configure(yscrollcommand=scroll_simbolos.set)

        self.tabla_simbolos_view.grid(
            row=0, column=0, sticky="nsew", padx=(6, 0), pady=6
        )
        scroll_simbolos.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=6)

        # --- Pestaña 3: Tabla de Instrucciones (Fila, Instrucción, Regla de la GLC) ---
        tab_instrucciones.grid_rowconfigure(0, weight=1)
        tab_instrucciones.grid_columnconfigure(0, weight=1)

        self.tabla_instrucciones_view = ttk.Treeview(
            tab_instrucciones,
            columns=("fila", "instruccion", "regla"),
            show="headings",
            style="Compilador.Treeview",
        )
        self.tabla_instrucciones_view.heading("fila", text="Fila")
        self.tabla_instrucciones_view.heading("instruccion", text="Instrucción")
        self.tabla_instrucciones_view.heading("regla", text="Regla de la GLC")

        self.tabla_instrucciones_view.column(
            "fila", width=65, anchor="center", stretch=False
        )
        self.tabla_instrucciones_view.column("instruccion", width=260, anchor="w")
        self.tabla_instrucciones_view.column("regla", width=250, anchor="w")

        # Tag para pintar en rojo las instrucciones que contienen error
        self.tabla_instrucciones_view.tag_configure(
            "invalida", foreground=COLOR_ERROR_ROJO
        )
        self.tabla_instrucciones_view.tag_configure(
            "valida", foreground=COLOR_CREMA
        )

        scroll_inst_v = ttk.Scrollbar(
            tab_instrucciones,
            orient="vertical",
            command=self.tabla_instrucciones_view.yview,
        )
        scroll_inst_h = ttk.Scrollbar(
            tab_instrucciones,
            orient="horizontal",
            command=self.tabla_instrucciones_view.xview,
        )
        self.tabla_instrucciones_view.configure(
            yscrollcommand=scroll_inst_v.set, xscrollcommand=scroll_inst_h.set
        )

        self.tabla_instrucciones_view.grid(
            row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0)
        )
        scroll_inst_v.grid(
            row=0, column=1, sticky="ns", padx=(0, 6), pady=(6, 0)
        )
        scroll_inst_h.grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 6)
        )

        # --- Pestaña 4: Tabla de Errores (Línea, Error, Tipo) ---
        tab_errores.grid_rowconfigure(0, weight=1)
        tab_errores.grid_columnconfigure(0, weight=1)

        self.tabla_errores_view = ttk.Treeview(
            tab_errores,
            columns=("linea", "error", "tipo"),
            show="headings",
            style="Compilador.Treeview",
        )
        self.tabla_errores_view.heading("linea", text="Línea")
        self.tabla_errores_view.heading("error", text="Error")
        self.tabla_errores_view.heading("tipo", text="Tipo")

        self.tabla_errores_view.column("linea", width=90, anchor="center", stretch=False)
        self.tabla_errores_view.column("error", width=240, anchor="center")
        self.tabla_errores_view.column("tipo", width=160, anchor="center")

        scroll_err = ttk.Scrollbar(
            tab_errores,
            orient="vertical",
            command=self.tabla_errores_view.yview,
        )
        self.tabla_errores_view.configure(yscrollcommand=scroll_err.set)

        self.tabla_errores_view.grid(
            row=0, column=0, sticky="nsew", padx=(6, 0), pady=6
        )
        scroll_err.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=6)

    # =========================================================================
    # ACTUALIZACIÓN CONTINUA (INCISO 7) Y EJECUCIÓN DE FASES
    # =========================================================================

    def _al_escribir_codigo(self, _evento: object = None) -> None:
        """Reinicia el temporizador de 300 ms al soltar una tecla (debounce)."""
        if self._after_id is not None:
            self.after_cancel(self._after_id)

        self.lbl_estado.configure(text="● Analizando...", text_color=COLOR_NARANJA)
        self._after_id = self.after(300, self.ejecutar_analisis)

    def ejecutar_analisis(self) -> None:
        """Ejecuta las fases del compilador respetando el bloqueo del Inciso 2."""
        self._after_id = None
        codigo_crudo: str = self.txt_codigo.get("1.0", "end-1c")

        if not codigo_crudo.strip():
            self._actualizar_panel_texto(self.txt_depurado, "")
            self._llenar_tabla_simbolos([])
            self._llenar_tabla_instrucciones([], set())
            self._llenar_tabla_errores([])
            self.lbl_resumen.configure(
                text="Símbolos: 0  |  Instrucciones: 0  |  Errores: 0"
            )
            self.lbl_estado.configure(text="● Editor vacío", text_color=COLOR_AZUL)
            return

        # 1. Depuración (Inciso 1)
        codigo_depurado, mapa_lineas = depurar_codigo(codigo_crudo)
        self._actualizar_panel_texto(self.txt_depurado, codigo_depurado)

        # 2. Tokenización base y Tabla de Símbolos con ámbitos (Inciso 3)
        tokens: List[Token]
        tabla_simbolos: List[Simbolo]
        errores_lexicos: List[ErrorCompilador]
        tokens, tabla_simbolos, errores_lexicos = analizar_lexico(
            codigo_depurado, mapa_lineas
        )

        # 3. Validación de Clase Principal (Inciso 2) y Análisis Sintáctico/Semántico
        estructura_valida: bool
        instrucciones: List[Instruccion]
        errores_sint_sem: List[ErrorCompilador]
        estructura_valida, instrucciones, errores_sint_sem = (
            analizar_sintactico_semantico(tokens, tabla_simbolos)
        )

        # Si NO cumple el Inciso 2, NO procesa los siguientes incisos
        if not estructura_valida:
            self._llenar_tabla_simbolos([])
            self._llenar_tabla_instrucciones([], set())
            self._llenar_tabla_errores(errores_sint_sem)
            self.lbl_resumen.configure(
                text=f"Símbolos: 0  |  Instrucciones: 0  |  Errores: {len(errores_sint_sem)}"
            )
            self.lbl_estado.configure(
                text="✖ Falla validación de clase principal (Inciso 2)",
                text_color=COLOR_NARANJA,
            )
            return

        todos_los_errores: List[ErrorCompilador] = errores_lexicos + errores_sint_sem
        todos_los_errores.sort(key=lambda e: e.linea)

        # Conjunto de líneas con cualquier error para pintar la instrucción en rojo
        lineas_con_error: Set[int] = {err.linea for err in todos_los_errores}

        self._llenar_tabla_simbolos(tabla_simbolos)
        self._llenar_tabla_instrucciones(instrucciones, lineas_con_error)
        self._llenar_tabla_errores(todos_los_errores)

        total_validas: int = sum(
            1
            for inst in instrucciones
            if inst.es_valida and inst.linea not in lineas_con_error
        )

        self.lbl_resumen.configure(
            text=(
                f"Símbolos: {len(tabla_simbolos)}  |  "
                f"Instrucciones Válidas: {total_validas}/{len(instrucciones)}  |  "
                f"Errores: {len(todos_los_errores)}"
            )
        )

        if todos_los_errores:
            self.lbl_estado.configure(
                text=f"⚠ {len(todos_los_errores)} error(es) encontrado(s)",
                text_color=COLOR_NARANJA,
            )
        else:
            self.lbl_estado.configure(
                text="✔ Análisis completado (0 errores)", text_color=COLOR_CREMA
            )

    def _actualizar_panel_texto(
        self, widget: ctk.CTkTextbox, nuevo_texto: str
    ) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", nuevo_texto)
        widget.configure(state="disabled")

    def _llenar_tabla_simbolos(self, simbolos: List[Simbolo]) -> None:
        for item in self.tabla_simbolos_view.get_children():
            self.tabla_simbolos_view.delete(item)
        for sim in simbolos:
            self.tabla_simbolos_view.insert(
                "", "end", values=(sim.id_num, sim.lexema, sim.token)
            )

    def _llenar_tabla_instrucciones(
        self, instrucciones: List[Instruccion], lineas_con_error: Set[int]
    ) -> None:
        """Llena la tabla de instrucciones y aplica el tag 'invalida' (rojo) si tiene error."""
        for item in self.tabla_instrucciones_view.get_children():
            self.tabla_instrucciones_view.delete(item)

        for inst in instrucciones:
            es_correcta: bool = (
                inst.es_valida and inst.linea not in lineas_con_error
            )
            etiqueta: str = "valida" if es_correcta else "invalida"
            self.tabla_instrucciones_view.insert(
                "",
                "end",
                values=(inst.linea, inst.texto, inst.regla_glc),
                tags=(etiqueta,),
            )

    def _llenar_tabla_errores(self, errores: List[ErrorCompilador]) -> None:
        for item in self.tabla_errores_view.get_children():
            self.tabla_errores_view.delete(item)
        for err in errores:
            self.tabla_errores_view.insert(
                "", "end", values=(err.linea, err.error, err.tipo)
            )

    def _abrir_archivo(self) -> None:
        ruta: str = filedialog.askopenfilename(
            title="Seleccionar archivo Java o de texto",
            filetypes=[
                ("Archivos Java o Texto", "*.java *.txt"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not ruta:
            return

        with open(ruta, "r", encoding="utf-8", errors="replace") as archivo:
            contenido: str = archivo.read()

        self.txt_codigo.delete("1.0", "end")
        self.txt_codigo.insert("1.0", contenido)
        self.ejecutar_analisis()

    def _cargar_codigo_ejemplo(self) -> None:
        self.txt_codigo.delete("1.0", "end")
        self.txt_codigo.insert("1.0", CODIGO_EJEMPLO)
        self.ejecutar_analisis()

    def _limpiar_editor(self) -> None:
        self.txt_codigo.delete("1.0", "end")
        self.ejecutar_analisis()