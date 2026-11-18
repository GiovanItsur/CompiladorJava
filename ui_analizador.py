import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Dict, List, Optional, Set
import customtkinter as ctk

from backend.depurador import depurar_codigo
from backend.lexer import analizar_lexico
from backend.models import ErrorCompilador, Instruccion, Simbolo, Token
from backend.parser import analizar_sintactico_semantico


# Paleta de colores retro moderna
COLOR_FONDO: str = "#141517"
COLOR_PANEL: str = "#1d1f23"
COLOR_EDITOR: str = "#18191c"
COLOR_GUTTER: str = "#131417"
COLOR_CREMA: str = "#e8d8c9"
COLOR_AZUL: str = "#4b607f"
COLOR_AZUL_HOVER: str = "#3a4c66"
COLOR_NARANJA: str = "#f3701e"
COLOR_NARANJA_HOVER: str = "#d65c12"
COLOR_TEXTO_OSCURO: str = "#16171a"
COLOR_ERROR_ROJO: str = "#ff4d4d"


# Diccionario de casos de prueba precargados para la defensa del proyecto
CASOS_PRUEBA: Dict[str, str] = {
    "1. Válido Completo (Tienda)": """// Prueba 1: Programa completamente válido (0 errores).
// Muestra ámbitos separados (global vs calcular vs main), objetos, if/else y switch.
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
}""",
    "2. Depuración y Ciclos (while/for/do)": """/* Prueba 2: Demuestra eliminación de comentarios multilínea,
   colapso de múltiples ';;;;', char + int, casteo explícito y ciclos. */
package ciclos;
public class ControlCiclos {
    int globalBase; // Global inicia en 0 automáticamente
    public static void main(String[] args) {
        int i = 0;;;;
        char codigo = 'B';
        int suma = globalBase + codigo;;;;
        double decimal = 45.8;
        int truncado = (int) decimal;

        while (i < 5) {
            suma = suma + i;
            i++;
        }
        do {
            suma--;
        } while (suma > 100);

        for (int k = 0; k < 3; k++) {
            System.out.println(suma);
        }
    }
}""",
    "3. Error Fase 2 (Falta package)": """// Prueba 3: Incumple el Inciso 2 porque no tiene 'package ID;' al inicio.
// Bloquea el llenado de la Tabla de Símbolos y de Instrucciones.
public class SinPaquete {
    public static void main(String[] args) {
        int x = 10;
        System.out.println(x);
    }
}""",
    "4. Errores Léxicos (Fase 3)": """// Prueba 4: Demuestra errores léxicos (@, #, identificador que inicia con número
// y número decimal mal formado).
package lexico;
public class PruebaLexica {
    public static void main(String[] args) {
        int 1variable = 10;
        double pi = 3.14.16;
        int valor = 5 @ 2;
        char malo = 'AB';
    }
}""",
    "5. Errores Sintácticos (Falta ; y static)": """// Prueba 5: Demuestra detección exacta de falta de ';' al final de la línea
// y prohibición de variables 'static' en la GLC v7.
package sintaxis;
public class PruebaSintactica {
    static int prohibido = 1;
    public static void main(String[] args) {
        float a = 2.5f
        int b = 3;
        System.out.println(b)
    }
}""",
    "6. Errores Semánticos (Tipos y Ámbitos)": """// Prueba 6: Demuestra errores semánticos:
// - Asignar decimal sin 'f' (VTD/double) a float
// - Asignar un long a un int sin casteo
// - Usar variable local sin inicializar
// - Redeclarar variable en el mismo ámbito
package semantica;
public class PruebaSemantica {
    public static void main(String[] args) {
        float peso = 15.75;
        long grande = 500;
        int chico = grande;
        int sinValor;
        int resultado = sinValor + 10;
        int chico = 2;
    }
}""",
}


class PantallaAnalizador(ctk.CTkFrame):
    """
    Pantalla principal con divisor arrastrable (PanedWindow), selector de
    casos de prueba precargados y editor con numeración de líneas.
    """

    def __init__(self, master: ctk.CTk, al_volver: Callable[[], None]) -> None:
        super().__init__(master, fg_color=COLOR_FONDO)
        self.al_volver: Callable[[], None] = al_volver
        self._after_id: Optional[str] = None
        self._total_lineas_actual: int = 0

        self._configurar_estilo_tablas()
        self._construir_interfaz()

        # Cargar la primera prueba por defecto al abrir
        primera_prueba: str = list(CASOS_PRUEBA.keys())[0]
        self._seleccionar_caso_prueba(primera_prueba)

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
        """Divide la pantalla en Barra Superior y un PanedWindow horizontal redimensionable."""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # =====================================================================
        # 1. BARRA SUPERIOR DE ACCIONES Y SELECTOR DE PRUEBAS
        # =====================================================================
        barra_sup = ctk.CTkFrame(
            self,
            height=58,
            corner_radius=14,
            fg_color=COLOR_PANEL,
            border_width=1,
            border_color=COLOR_AZUL,
        )
        barra_sup.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))

        btn_volver = ctk.CTkButton(
            barra_sup,
            text="← Inicio",
            width=85,
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
            text="Simulador GLC v7",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLOR_CREMA,
        )
        lbl_titulo.pack(side="left", padx=6)

        self.lbl_resumen = ctk.CTkLabel(
            barra_sup,
            text="Símbolos: 0  |  Instrucciones: 0  |  Errores: 0",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_AZUL,
        )
        self.lbl_resumen.pack(side="left", padx=14)

        self.lbl_estado = ctk.CTkLabel(
            barra_sup,
            text="● Listo",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_CREMA,
        )
        self.lbl_estado.pack(side="right", padx=14)

        btn_limpiar = ctk.CTkButton(
            barra_sup,
            text="Limpiar",
            width=80,
            height=34,
            fg_color=COLOR_AZUL,
            hover_color=COLOR_AZUL_HOVER,
            text_color=COLOR_CREMA,
            command=self._limpiar_editor,
        )
        btn_limpiar.pack(side="right", padx=5, pady=10)

        btn_archivo = ctk.CTkButton(
            barra_sup,
            text="Abrir Archivo",
            width=120,
            height=34,
            fg_color=COLOR_NARANJA,
            hover_color=COLOR_NARANJA_HOVER,
            text_color=COLOR_TEXTO_OSCURO,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._abrir_archivo,
        )
        btn_archivo.pack(side="right", padx=5, pady=10)

        # Menú desplegable con las pruebas precargadas
        self.menu_pruebas = ctk.CTkOptionMenu(
            barra_sup,
            values=list(CASOS_PRUEBA.keys()),
            width=250,
            height=34,
            fg_color=COLOR_AZUL,
            button_color=COLOR_AZUL_HOVER,
            button_hover_color=COLOR_NARANJA,
            dropdown_fg_color=COLOR_PANEL,
            dropdown_text_color=COLOR_CREMA,
            dropdown_hover_color=COLOR_AZUL_HOVER,
            text_color=COLOR_CREMA,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._seleccionar_caso_prueba,
        )
        self.menu_pruebas.pack(side="right", padx=5, pady=10)

        lbl_pruebas = ctk.CTkLabel(
            barra_sup,
            text="Pruebas:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_CREMA,
        )
        lbl_pruebas.pack(side="right", padx=(8, 2))

        # =====================================================================
        # 2. CONTENEDOR DIVIDIDO REDIMENSIONABLE (PANEDWINDOW)
        #    Permite arrastrar el borde central hacia la izquierda o derecha.
        # =====================================================================
        self.panel_dividido = tk.PanedWindow(
            self,
            orient="horizontal",
            bg=COLOR_AZUL,
            bd=0,
            sashwidth=6,
            sashpad=0,
            sashrelief="flat",
            opaqueresize=True,
        )
        self.panel_dividido.grid(
            row=1, column=0, sticky="nsew", padx=14, pady=(6, 14)
        )

        # =====================================================================
        # 2.1 PANEL IZQUIERDO: EDITOR CON NUMERACIÓN DE LÍNEAS
        # =====================================================================
        marco_editor = ctk.CTkFrame(
            self.panel_dividido,
            corner_radius=12,
            fg_color=COLOR_PANEL,
            border_width=1,
            border_color=COLOR_AZUL,
        )
        marco_editor.grid_rowconfigure(1, weight=1)
        marco_editor.grid_columnconfigure(0, weight=1)

        lbl_editor = ctk.CTkLabel(
            marco_editor,
            text="Editor de Código Fuente (Arrastra la barra central ⇔ para redimensionar)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_CREMA,
        )
        lbl_editor.grid(row=0, column=0, sticky="w", padx=14, pady=(10, 6))

        contenedor_codigo = ctk.CTkFrame(
            marco_editor,
            fg_color=COLOR_EDITOR,
            corner_radius=8,
            border_width=1,
            border_color="#2b3038",
        )
        contenedor_codigo.grid(
            row=1, column=0, sticky="nsew", padx=12, pady=(0, 12)
        )
        contenedor_codigo.grid_rowconfigure(0, weight=1)
        contenedor_codigo.grid_columnconfigure(1, weight=1)

        self.txt_lineas = ctk.CTkTextbox(
            contenedor_codigo,
            width=50,
            font=ctk.CTkFont(family="Consolas", size=14),
            fg_color=COLOR_GUTTER,
            text_color=COLOR_AZUL,
            border_width=0,
            corner_radius=0,
            wrap="none",
            activate_scrollbars=False,
            state="disabled",
        )
        self.txt_lineas.grid(row=0, column=0, sticky="ns", padx=(2, 0), pady=2)
        self.txt_lineas._textbox.tag_configure("derecha", justify="right")

        self.txt_codigo = ctk.CTkTextbox(
            contenedor_codigo,
            font=ctk.CTkFont(family="Consolas", size=14),
            fg_color=COLOR_EDITOR,
            text_color=COLOR_CREMA,
            border_width=0,
            corner_radius=0,
            wrap="none",
            undo=True,
        )
        self.txt_codigo.grid(
            row=0, column=1, sticky="nsew", padx=(0, 2), pady=2
        )

        self.txt_codigo._textbox.configure(
            yscrollcommand=self._al_desplazar_editor
        )
        self.txt_codigo.bind("<KeyRelease>", self._al_escribir_codigo)
        self.txt_codigo.bind("<MouseWheel>", self._sincronizar_scroll_lineas)
        self.txt_codigo.bind("<Button-4>", self._sincronizar_scroll_lineas)
        self.txt_codigo.bind("<Button-5>", self._sincronizar_scroll_lineas)
        self.txt_codigo.bind("<ButtonRelease-1>", self._sincronizar_scroll_lineas)

        # =====================================================================
        # 2.2 PANEL DERECHO: PESTAÑAS DE RESULTADOS
        # =====================================================================
        self.pestanas = ctk.CTkTabview(
            self.panel_dividido,
            corner_radius=12,
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

        # Agregar ambos paneles al PanedWindow con tamaño mínimo para que nunca desaparezcan
        self.panel_dividido.add(marco_editor, minsize=340, stretch="always")
        self.panel_dividido.add(self.pestanas, minsize=400, stretch="always")

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
    # NUMERACIÓN DE LÍNEAS SINCRONIZADA
    # =========================================================================

    def _al_desplazar_editor(self, primero: str, ultimo: str) -> None:
        self.txt_codigo._y_scrollbar.set(primero, ultimo)
        self.txt_lineas._textbox.yview_moveto(primero)

    def _sincronizar_scroll_lineas(self, _evento: object = None) -> None:
        fraccion_superior: float = self.txt_codigo._textbox.yview()[0]
        self.txt_lineas._textbox.yview_moveto(fraccion_superior)

    def _actualizar_numeros_linea(self) -> None:
        indice_final: str = self.txt_codigo._textbox.index("end-1c")
        total_lineas: int = int(indice_final.split(".")[0])

        if total_lineas != self._total_lineas_actual:
            self._total_lineas_actual = total_lineas
            numeros: str = "\n".join(str(i) for i in range(1, total_lineas + 1))

            self.txt_lineas.configure(state="normal")
            self.txt_lineas.delete("1.0", "end")
            self.txt_lineas.insert("1.0", numeros)
            self.txt_lineas._textbox.tag_add("derecha", "1.0", "end")
            self.txt_lineas.configure(state="disabled")

        self._sincronizar_scroll_lineas()

    # =========================================================================
    # ACTUALIZACIÓN CONTINUA (INCISO 7) Y EJECUCIÓN DE FASES
    # =========================================================================

    def _al_escribir_codigo(self, _evento: object = None) -> None:
        self._actualizar_numeros_linea()

        if self._after_id is not None:
            self.after_cancel(self._after_id)

        self.lbl_estado.configure(text="● Analizando...", text_color=COLOR_NARANJA)
        self._after_id = self.after(300, self.ejecutar_analisis)

    def ejecutar_analisis(self) -> None:
        self._after_id = None
        self._actualizar_numeros_linea()
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

        if not estructura_valida:
            self._llenar_tabla_simbolos([])
            self._llenar_tabla_instrucciones([], set())
            self._llenar_tabla_errores(errores_sint_sem)
            self.lbl_resumen.configure(
                text=f"Símbolos: 0  |  Instrucciones: 0  |  Errores: {len(errores_sint_sem)}"
            )
            self.lbl_estado.configure(
                text="✖ Falla validación base: requiere package, class y main (Inciso 2)",
                text_color=COLOR_NARANJA,
            )
            return

        todos_los_errores: List[ErrorCompilador] = errores_lexicos + errores_sint_sem
        todos_los_errores.sort(key=lambda e: e.linea)

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

    def _seleccionar_caso_prueba(self, nombre_prueba: str) -> None:
        """Carga en el editor el caso de prueba elegido en el menú desplegable."""
        codigo: str = CASOS_PRUEBA.get(nombre_prueba, "")
        self.txt_codigo.delete("1.0", "end")
        self.txt_codigo.insert("1.0", codigo)
        self.ejecutar_analisis()

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

    def _limpiar_editor(self) -> None:
        self.txt_codigo.delete("1.0", "end")
        self.ejecutar_analisis()