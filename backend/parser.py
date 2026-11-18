from typing import Dict, List, Optional, Tuple
from backend.models import ErrorCompilador, Instruccion, Simbolo, Token


# Jerarquía de amplitud para enteros: un tipo de mayor rango (ej. long = 4)
# no puede asignarse a uno de menor rango (ej. int = 3) sin casteo.
# El literal VTE tiene rango 0 para poder asignarse a byte, short, int o long.
JERARQUIA_ENTEROS: Dict[str, int] = {
    "VTE": 0,
    "byte": 1,
    "short": 2,
    "char": 2,
    "int": 3,
    "long": 4,
}

TIPOS_ENTEROS = {"VTE", "int", "long", "short", "byte", "char"}
TIPOS_NUMERICOS = {
    "VTE",
    "int",
    "long",
    "short",
    "byte",
    "char",
    "float",
    "double",
}


def analizar_sintactico_semantico(
    tokens: List[Token], tabla_simbolos: List[Simbolo]
) -> Tuple[bool, List[Instruccion], List[ErrorCompilador]]:
    """Ejecuta las fases 2, 4, 5 y 6 del analizador."""
    analizador = AnalizadorSintacticoSemantico(tokens, tabla_simbolos)
    return analizador.ejecutar()


class AnalizadorSintacticoSemantico:
    """Analizador sintáctico descendente recursivo y validador semántico."""

    def __init__(self, tokens: List[Token], tabla_simbolos: List[Simbolo]) -> None:
        self.tokens: List[Token] = tokens
        self.tabla_simbolos: List[Simbolo] = tabla_simbolos
        self.pos: int = 0

        self.instrucciones_evaluadas: List[Instruccion] = []
        self.errores: List[ErrorCompilador] = []

        self.ambitos: Dict[str, Dict[str, Simbolo]] = {"global": {}}
        self.ambito_actual: str = "global"
        self.metodos: Dict[str, str] = {}

    def ejecutar(self) -> Tuple[bool, List[Instruccion], List[ErrorCompilador]]:
        """Verifica primero el Inciso 2 (estructura base) y luego analiza la GLC."""
        if not self.tokens:
            return False, [], []

        if not self._validar_estructura_principal():
            self.tabla_simbolos.clear()
            self.instrucciones_evaluadas.clear()
            return False, [], self.errores

        self._parse_java()
        self.instrucciones_evaluadas.sort(key=lambda inst: inst.linea)
        return True, self.instrucciones_evaluadas, self.errores

    # =========================================================================
    # FASE 2: VALIDACIÓN DE PACKAGE, CLASE PRINCIPAL Y MAIN
    # =========================================================================

    def _validar_estructura_principal(self) -> bool:
        """
        Verifica estrictamente que el programa inicie con 'package ID;' y contenga
        'public class ID { ... public static void main(String[] ID) { ... } }'.
        """
        n: int = len(self.tokens)

        # 1. Validar que inicie obligatoriamente con DPACKAGE: package ID ;
        if (
            n < 3
            or self.tokens[0].tipo_token != "PCK"
            or self.tokens[1].tipo_token != "ID"
            or self.tokens[2].tipo_token != "FI"
        ):
            linea_pck: int = self.tokens[0].linea if n > 0 else 1
            self._agregar_error(linea_pck, "package", "Sintáctico")
            return False

        idx: int = 3

        # 2. Saltar IMPORTS opcionales: import ID.ID ;
        while idx < n and self.tokens[idx].tipo_token == "IMP":
            while idx < n and self.tokens[idx].tipo_token != "FI":
                idx += 1
            idx += 1

        # 3. Validar encabezado 'public class ID {'
        if (
            idx + 3 >= n
            or self.tokens[idx].lexema != "public"
            or self.tokens[idx + 1].tipo_token != "CL"
            or self.tokens[idx + 2].tipo_token != "ID"
            or self.tokens[idx + 3].tipo_token != "LLA"
        ):
            linea: int = self.tokens[idx].linea if idx < n else 1
            lex: str = self.tokens[idx].lexema if idx < n else "class"
            self._agregar_error(linea, lex, "Sintáctico")
            return False

        # 4. Validar existencia de 'public static void main(String[] ID) {'
        tiene_main: bool = False
        for i in range(idx + 4, n - 10):
            if (
                self.tokens[i].lexema == "public"
                and self.tokens[i + 1].tipo_token == "ST"
                and self.tokens[i + 2].tipo_token == "TM"
                and self.tokens[i + 3].tipo_token == "PMAIN"
                and self.tokens[i + 4].tipo_token == "PA"
                and self.tokens[i + 5].tipo_token == "STR"
                and self.tokens[i + 6].tipo_token == "COA"
                and self.tokens[i + 7].tipo_token == "COC"
                and self.tokens[i + 8].tipo_token == "ID"
                and self.tokens[i + 9].tipo_token == "PC"
                and self.tokens[i + 10].tipo_token == "LLA"
            ):
                tiene_main = True
                break

        if not tiene_main:
            self._agregar_error(self.tokens[0].linea, "main", "Sintáctico")
            return False

        # 5. Validar balanceo de llaves '{' y '}'
        balance: int = 0
        for tok in self.tokens:
            if tok.tipo_token == "LLA":
                balance += 1
            elif tok.tipo_token == "LLC":
                balance -= 1
                if balance < 0:
                    self._agregar_error(tok.linea, "}", "Sintáctico")
                    return False

        if balance != 0 or self.tokens[-1].tipo_token != "LLC":
            self._agregar_error(self.tokens[-1].linea, "}", "Sintáctico")
            return False

        return True

    # =========================================================================
    # REGLAS DE LA GLC v7 (JAVA, DPACKAGE, IMPORTS, CLASE, CONTENT)
    # =========================================================================

    def _parse_java(self) -> None:
        """JAVA ::= DPACKAGE IMPORTS CLASE"""
        self._parse_dpackage()
        self._parse_imports()
        self._parse_clase()

    def _parse_dpackage(self) -> None:
        """DPACKAGE ::= PCK ID FI (Obligatorio en GLC v7)"""
        inicio: int = self.pos
        errores_previos: int = len(self.errores)

        if not self._consumir("PCK") or not self._consumir("ID") or not self._consumir("FI"):
            self._sincronizar_hasta_fi()

        es_valida: bool = len(self.errores) == errores_previos
        self._registrar_instruccion(
            inicio, self.pos, "DPACKAGE ::= PCK ID FI", es_valida
        )

    def _parse_imports(self) -> None:
        """IMPORT ::= IMP ID CA ID FI"""
        while self._coincide("IMP"):
            inicio: int = self.pos
            errores_previos: int = len(self.errores)
            self._avanzar()

            if (
                not self._consumir("ID")
                or not self._consumir("CA")
                or not self._consumir("ID")
                or not self._consumir("FI")
            ):
                self._sincronizar_hasta_fi()

            es_valida: bool = len(self.errores) == errores_previos
            self._registrar_instruccion(
                inicio, self.pos, "IMPORT ::= IMP ID CA ID FI", es_valida
            )

    def _parse_clase(self) -> None:
        """CLASE ::= MA CL ID LLA CONTENT LLC"""
        self._consumir("MA")
        self._consumir("CL")
        self._consumir("ID")
        self._consumir("LLA")
        self._parse_content()
        self._consumir("LLC")

    def _parse_content(self) -> None:
        """CONTENT ::= VARIOS CONTENT | ε ; VARIOS ::= MAIN | METODO | DECS_GLOB"""
        while not self._fin() and not self._coincide("LLC"):
            if (
                self._coincide("MA")
                and self._mirar(1) is not None
                and self._mirar(1).tipo_token == "ST"
                and self._mirar(3) is not None
                and self._mirar(3).tipo_token == "PMAIN"
            ):
                self._parse_main()
                continue

            if self._coincide("ST") or (
                self._coincide("MA")
                and self._mirar(1) is not None
                and self._mirar(1).tipo_token == "ST"
            ):
                inicio_err: int = self.pos
                tok_err: Token = (
                    self._actual() if self._coincide("ST") else self._mirar(1)
                )
                self._agregar_error(tok_err.linea, "static", "Sintáctico")
                self._sincronizar_hasta_fi()
                self._registrar_instruccion(
                    inicio_err, self.pos, "D_GLOB (No permite static)", False
                )
                continue

            if (
                self._coincide("MA")
                and self._mirar(1) is not None
                and self._mirar(1).tipo_token in ("TD", "STR", "TM", "ID")
                and self._mirar(2) is not None
                and self._mirar(2).tipo_token == "ID"
                and self._mirar(3) is not None
                and self._mirar(3).tipo_token == "PA"
            ):
                self._parse_metodo()
                continue

            self._parse_d_glob()

    def _parse_main(self) -> None:
        """MAIN ::= MA ST TM PMAIN PA STR COA COC ID PC LLA CUERPO LLC"""
        self.ambito_actual = "main"
        self.ambitos["main"] = {}

        self._consumir("MA")
        self._consumir("ST")
        self._consumir("TM")
        self._consumir("PMAIN")
        self._consumir("PA")
        self._consumir("STR")
        self._consumir("COA")
        self._consumir("COC")

        tok_args: Optional[Token] = self._actual()
        if self._consumir("ID") and tok_args is not None:
            self._registrar_variable_semantica(
                tok_args.lexema, "String[]", tok_args.linea, inicializada=True
            )

        self._consumir("PC")
        self._consumir("LLA")
        self._parse_cuerpo()
        self._consumir("LLC")
        self.ambito_actual = "global"

    def _parse_metodo(self) -> None:
        """METODO ::= MA TYPE ID PA PARAMS PC LLA CUERPO REE LLC"""
        self._consumir("MA")
        tok_tipo: Optional[Token] = self._actual()
        tipo_retorno: str = tok_tipo.lexema if tok_tipo else "void"
        self._avanzar()

        tok_id: Optional[Token] = self._actual()
        nombre_metodo: str = tok_id.lexema if tok_id else "metodo"
        linea_metodo: int = tok_id.linea if tok_id else 1
        self._consumir("ID")

        self.metodos[nombre_metodo] = tipo_retorno
        self.ambito_actual = nombre_metodo
        self.ambitos[nombre_metodo] = {}

        self._consumir("PA")
        self._parse_params()
        self._consumir("PC")
        self._consumir("LLA")

        self._parse_cuerpo()
        self._parse_ree(tipo_retorno, linea_metodo)

        self._consumir("LLC")
        self.ambito_actual = "global"

    def _parse_params(self) -> None:
        """PARAMS ::= PARAM PARAMS | ε ; PARAM ::= TY ID | CO TY ID"""
        if self._coincide("TD", "STR", "ID"):
            self._parse_un_parametro()
            while self._coincide("CO"):
                self._avanzar()
                self._parse_un_parametro()

    def _parse_un_parametro(self) -> None:
        tok_tipo: Optional[Token] = self._actual()
        if not self._coincide("TD", "STR", "ID"):
            self._error_actual()
            return
        self._avanzar()

        tok_id: Optional[Token] = self._actual()
        if self._consumir("ID") and tok_id and tok_tipo:
            self._registrar_variable_semantica(
                tok_id.lexema, tok_tipo.lexema, tok_id.linea, inicializada=True
            )

    def _parse_ree(self, tipo_retorno: str, linea_metodo: int) -> None:
        """REE ::= RTN FI | RTN EXP FI | ε"""
        if self._coincide("RTN"):
            inicio: int = self.pos
            errores_previos: int = len(self.errores)
            tok_rtn: Token = self._actual()
            self._avanzar()

            if self._coincide("FI"):
                self._avanzar()
                if tipo_retorno != "void":
                    self._agregar_error(tok_rtn.linea, "return", "Semántico")
                es_valida: bool = len(self.errores) == errores_previos
                self._registrar_instruccion(
                    inicio, self.pos, "REE ::= RTN FI", es_valida
                )
                return

            tipo_exp: str = self._parse_exp()
            if not self._consumir("FI"):
                self._sincronizar_hasta_fi()

            if tipo_retorno == "void":
                self._agregar_error(tok_rtn.linea, "return", "Semántico")
            elif tipo_exp != "error":
                self._validar_compatibilidad_tipos(
                    tipo_retorno, tipo_exp, tok_rtn.linea, "return"
                )
            es_valida = len(self.errores) == errores_previos
            self._registrar_instruccion(
                inicio, self.pos, "REE ::= RTN EXP FI", es_valida
            )
        else:
            if tipo_retorno != "void":
                self._agregar_error(linea_metodo, "return", "Semántico")

    def _parse_d_glob(self) -> None:
        """D_GLOB ::= MAO TY ID FI | MAO TY ID ODA EXP FI | OBJ"""
        inicio: int = self.pos
        if self._coincide("MA"):
            self._avanzar()

        if (
            self._coincide("ID")
            and self._mirar(1) is not None
            and self._mirar(1).tipo_token == "ID"
            and self._mirar(2) is not None
            and self._mirar(2).tipo_token == "ODA"
            and self._mirar(3) is not None
            and self._mirar(3).tipo_token == "NW"
        ):
            self._parse_obj(inicio)
            return

        if self._coincide("TD", "STR", "ID"):
            self._parse_dec(inicio, es_global=True)
            return

        self._error_actual()
        self._sincronizar_en_cuerpo()
        self._registrar_instruccion(
            inicio, self.pos, "D_GLOB (Error Sintáctico)", False
        )

    # =========================================================================
    # CUERPO E INSTRUCCIONES (DEC, ASIG, OBJ, ACC, STATMNT, BREAK)
    # =========================================================================

    def _parse_cuerpo(self) -> None:
        """CUERPO ::= INST CUERPO | ε"""
        while not self._fin() and not self._coincide(
            "LLC", "RTN", "CS", "DF", "BR"
        ):
            self._parse_inst()

    def _parse_inst(self) -> None:
        """INST ::= DEC | STAT_B | ASIG | ACC | OBJ"""
        inicio: int = self.pos
        tok: Optional[Token] = self._actual()
        if tok is None:
            return

        if tok.tipo_token == "PRIF":
            self._parse_ifel()
            return
        if tok.tipo_token == "PRW":
            self._parse_while()
            return
        if tok.tipo_token == "PRDO":
            self._parse_do()
            return
        if tok.tipo_token == "PRF":
            self._parse_for()
            return
        if tok.tipo_token == "PRSW":
            self._parse_switch()
            return

        if tok.tipo_token in ("TD", "STR"):
            self._parse_dec(inicio, es_global=False)
            return

        if (
            tok.tipo_token == "ID"
            and self._mirar(1) is not None
            and self._mirar(1).tipo_token == "ID"
        ):
            if (
                self._mirar(2) is not None
                and self._mirar(2).tipo_token == "ODA"
                and self._mirar(3) is not None
                and self._mirar(3).tipo_token == "NW"
            ):
                self._parse_obj(inicio)
            else:
                self._parse_dec(inicio, es_global=False)
            return

        if tok.tipo_token == "ID":
            sig: Optional[Token] = self._mirar(1)
            if sig is not None and sig.tipo_token == "ODA":
                self._parse_asig(inicio)
                return
            if sig is not None and sig.tipo_token in ("CA", "PA"):
                self._parse_acc_instruccion(inicio)
                return
            if sig is not None and sig.tipo_token in ("INC", "DEC"):
                self._parse_inc_dec_instruccion(inicio)
                return

        if tok.tipo_token in ("INC", "DEC"):
            self._parse_inc_dec_instruccion(inicio)
            return

        self._error_actual()
        self._sincronizar_en_cuerpo()
        self._registrar_instruccion(
            inicio, self.pos, "INST (Error Sintáctico)", False
        )

    def _parse_dec(
        self, inicio: int, es_global: bool, consumir_fi: bool = True
    ) -> None:
        """DEC ::= TY ID FI | TY ID ODA EXP FI"""
        errores_previos: int = len(self.errores)
        tok_tipo: Token = self._actual()
        tipo_var: str = tok_tipo.lexema
        self._avanzar()

        tok_id: Optional[Token] = self._actual()
        if not self._consumir("ID"):
            self._sincronizar_hasta_fi()
            regla_err = (
                "D_GLOB ::= MAO TY ID FI" if es_global else "DEC ::= TY ID FI"
            )
            self._registrar_instruccion(inicio, self.pos, regla_err, False)
            return

        nombre_var: str = tok_id.lexema
        linea_dec: int = tok_id.linea
        tiene_asignacion: bool = self._coincide("ODA")

        if tiene_asignacion:
            self._avanzar()
            tipo_exp: str = self._parse_exp()
            if tipo_exp != "error":
                self._validar_compatibilidad_tipos(
                    tipo_var, tipo_exp, linea_dec, nombre_var
                )
            self._registrar_variable_semantica(
                nombre_var, tipo_var, linea_dec, inicializada=True
            )
            regla = (
                "D_GLOB ::= MAO TY ID ODA EXP FI"
                if es_global
                else "DEC ::= TY ID ODA EXP FI"
            )
        else:
            self._registrar_variable_semantica(
                nombre_var, tipo_var, linea_dec, inicializada=es_global
            )
            regla = (
                "D_GLOB ::= MAO TY ID FI" if es_global else "DEC ::= TY ID FI"
            )

        if consumir_fi:
            if not self._consumir("FI"):
                self._sincronizar_hasta_fi()
            es_valida: bool = len(self.errores) == errores_previos
            self._registrar_instruccion(inicio, self.pos, regla, es_valida)

    def _parse_asig(self, inicio: int, consumir_fi: bool = True) -> None:
        """ASIG ::= ID ODA EXP FI"""
        errores_previos: int = len(self.errores)
        tok_id: Token = self._actual()
        nombre_var: str = tok_id.lexema
        linea: int = tok_id.linea
        self._avanzar()

        self._consumir("ODA")
        tipo_exp: str = self._parse_exp()

        simbolo: Optional[Simbolo] = self._buscar_variable_semantica(nombre_var)
        if simbolo is None:
            self._agregar_error(linea, nombre_var, "Semántico")
        else:
            if tipo_exp != "error":
                self._validar_compatibilidad_tipos(
                    simbolo.tipo_dato, tipo_exp, linea, nombre_var
                )
            simbolo.inicializada = True

        if consumir_fi:
            if not self._consumir("FI"):
                self._sincronizar_hasta_fi()
            es_valida: bool = len(self.errores) == errores_previos
            self._registrar_instruccion(
                inicio, self.pos, "ASIG ::= ID ODA EXP FI", es_valida
            )

    def _parse_obj(self, inicio: int) -> None:
        """OBJ ::= ID ID ODA NW ID PA ARGS PC FI"""
        errores_previos: int = len(self.errores)
        tok_clase: Token = self._actual()
        self._avanzar()

        tok_id: Optional[Token] = self._actual()
        self._consumir("ID")
        self._consumir("ODA")
        self._consumir("NW")

        tok_ctor: Optional[Token] = self._actual()
        if self._consumir("ID") and tok_ctor and tok_ctor.lexema != tok_clase.lexema:
            self._agregar_error(tok_ctor.linea, tok_ctor.lexema, "Semántico")

        self._consumir("PA")
        self._parse_args()
        self._consumir("PC")

        if tok_id:
            self._registrar_variable_semantica(
                tok_id.lexema, tok_clase.lexema, tok_id.linea, inicializada=True
            )

        if not self._consumir("FI"):
            self._sincronizar_hasta_fi()

        es_valida: bool = len(self.errores) == errores_previos
        self._registrar_instruccion(
            inicio, self.pos, "OBJ ::= ID ID ODA NW ID PA ARGS PC FI", es_valida
        )

    def _parse_acc_instruccion(self, inicio: int) -> None:
        """ACC ::= CLA OT"""
        errores_previos: int = len(self.errores)
        self._parse_acc(es_instruccion=True)
        if not self._consumir("FI"):
            self._sincronizar_hasta_fi()
        es_valida: bool = len(self.errores) == errores_previos
        self._registrar_instruccion(
            inicio, self.pos, "ACC ::= CLA OT", es_valida
        )

    def _parse_inc_dec_instruccion(
        self, inicio: int, consumir_fi: bool = True
    ) -> None:
        """EXPU ::= OPU VAL"""
        errores_previos: int = len(self.errores)
        if self._coincide("INC", "DEC"):
            self._avanzar()
            tok_id: Optional[Token] = self._actual()
            if self._consumir("ID") and tok_id:
                self._verificar_variable_numerica_usada(tok_id)
        else:
            tok_id = self._actual()
            self._avanzar()
            self._avanzar()
            if tok_id:
                self._verificar_variable_numerica_usada(tok_id)

        if consumir_fi:
            if not self._consumir("FI"):
                self._sincronizar_hasta_fi()
            es_valida: bool = len(self.errores) == errores_previos
            self._registrar_instruccion(
                inicio, self.pos, "EXPU ::= OPU VAL", es_valida
            )

    # =========================================================================
    # ESTRUCTURAS DE CONTROL (IFEL, WHILE, DO, FOR, SWITCH)
    # =========================================================================

    def _parse_ifel(self) -> None:
        """IFEL ::= PRIF PA EXPBOO PC LLA INST LLC CLOS"""
        inicio_encabezado: int = self.pos
        errores_previos: int = len(self.errores)
        tok_if: Token = self._actual()
        self._avanzar()

        self._consumir("PA")
        tipo_cond: str = self._parse_exp()
        if tipo_cond not in ("boolean", "error"):
            self._agregar_error(tok_if.linea, "if", "Semántico")
        self._consumir("PC")
        fin_encabezado: int = self.pos

        es_valido_if: bool = len(self.errores) == errores_previos
        self._registrar_instruccion(
            inicio_encabezado,
            fin_encabezado,
            "IFEL ::= PRIF PA EXPBOO PC LLA INST LLC CLOS",
            es_valido_if,
        )

        self._consumir("LLA")
        self._parse_cuerpo()
        self._consumir("LLC")

        if self._coincide("PRE"):
            self._avanzar()
            if self._coincide("PRIF"):
                self._parse_ifel()
                return
            self._consumir("LLA")
            self._parse_cuerpo()
            self._consumir("LLC")

    def _parse_while(self) -> None:
        """WHILE ::= PRW PA EXP PC STATMNT_B"""
        inicio_enc: int = self.pos
        errores_previos: int = len(self.errores)
        tok_w: Token = self._actual()
        self._avanzar()

        self._consumir("PA")
        tipo_cond: str = self._parse_exp()
        if tipo_cond not in ("boolean", "error"):
            self._agregar_error(tok_w.linea, "while", "Semántico")
        self._consumir("PC")
        fin_enc: int = self.pos

        es_valido_w: bool = len(self.errores) == errores_previos
        self._registrar_instruccion(
            inicio_enc, fin_enc, "WHILE ::= PRW PA EXP PC STATMNT_B", es_valido_w
        )

        self._consumir("LLA")
        self._parse_cuerpo()
        self._consumir("LLC")

    def _parse_do(self) -> None:
        """DO ::= PRDO STATMNT_B PRW PA EXP PC FI"""
        self._avanzar()
        self._consumir("LLA")
        self._parse_cuerpo()
        self._consumir("LLC")

        inicio_w: int = self.pos
        errores_previos: int = len(self.errores)
        tok_w: Optional[Token] = self._actual()
        linea_w: int = tok_w.linea if tok_w else 1
        self._consumir("PRW")
        self._consumir("PA")

        tipo_cond: str = self._parse_exp()
        if tipo_cond not in ("boolean", "error"):
            self._agregar_error(linea_w, "while", "Semántico")

        self._consumir("PC")
        self._consumir("FI")
        es_valido_do: bool = len(self.errores) == errores_previos
        self._registrar_instruccion(
            inicio_w, self.pos, "DO ::= PRDO STATMNT_B PRW PA EXP PC FI", es_valido_do
        )

    def _parse_for(self) -> None:
        """FOR ::= PRF PA DEC EXP FI EXP PC LLA STAT_B LLC"""
        inicio_for: int = self.pos
        errores_previos: int = len(self.errores)
        tok_for: Token = self._actual()
        self._avanzar()

        self._consumir("PA")

        if self._coincide("TD", "STR"):
            self._parse_dec(self.pos, es_global=False, consumir_fi=False)
            self._consumir("FI")
        elif (
            self._coincide("ID")
            and self._mirar(1) is not None
            and self._mirar(1).tipo_token == "ODA"
        ):
            self._parse_asig(self.pos, consumir_fi=False)
            self._consumir("FI")
        else:
            self._consumir("FI")

        tipo_cond: str = self._parse_exp()
        if tipo_cond not in ("boolean", "error"):
            self._agregar_error(tok_for.linea, "for", "Semántico")
        self._consumir("FI")

        if not self._coincide("PC"):
            if (
                self._coincide("ID")
                and self._mirar(1) is not None
                and self._mirar(1).tipo_token == "ODA"
            ):
                self._parse_asig(self.pos, consumir_fi=False)
            elif self._coincide("INC", "DEC") or (
                self._coincide("ID")
                and self._mirar(1) is not None
                and self._mirar(1).tipo_token in ("INC", "DEC")
            ):
                self._parse_inc_dec_instruccion(self.pos, consumir_fi=False)
            else:
                self._parse_exp()

        self._consumir("PC")
        fin_enc: int = self.pos
        es_valido_for: bool = len(self.errores) == errores_previos
        self._registrar_instruccion(
            inicio_for,
            fin_enc,
            "FOR ::= PRF PA DEC EXP FI EXP PC LLA STAT_B LLC",
            es_valido_for,
        )

        self._consumir("LLA")
        self._parse_cuerpo()
        self._consumir("LLC")

    def _parse_switch(self) -> None:
        """SWITCH ::= PRSW PA VAL PC LLA L_CASES C_DEF LLC"""
        inicio_sw: int = self.pos
        errores_previos: int = len(self.errores)
        self._avanzar()

        self._consumir("PA")
        tipo_switch: str = self._parse_val()
        self._consumir("PC")
        fin_enc: int = self.pos

        es_valido_sw: bool = len(self.errores) == errores_previos
        self._registrar_instruccion(
            inicio_sw,
            fin_enc,
            "SWITCH ::= PRSW PA VAL PC LLA L_CASES C_DEF LLC",
            es_valido_sw,
        )

        self._consumir("LLA")

        while self._coincide("CS"):
            inicio_cs: int = self.pos
            err_cs: int = len(self.errores)
            tok_cs: Token = self._actual()
            self._avanzar()
            tipo_case: str = self._parse_val()
            if tipo_switch != "error" and tipo_case != "error":
                self._validar_compatibilidad_tipos(
                    tipo_switch, tipo_case, tok_cs.linea, "case"
                )
            self._consumir("DOP")
            self._registrar_instruccion(
                inicio_cs,
                self.pos,
                "CASE ::= CS VAL DOP CUERPO BREAK",
                len(self.errores) == err_cs,
            )

            self._parse_cuerpo()
            if self._coincide("BR"):
                inicio_br: int = self.pos
                err_br: int = len(self.errores)
                self._avanzar()
                self._consumir("FI")
                self._registrar_instruccion(
                    inicio_br,
                    self.pos,
                    "BREAK ::= BR FI",
                    len(self.errores) == err_br,
                )

        if self._coincide("DF"):
            inicio_df: int = self.pos
            err_df: int = len(self.errores)
            self._avanzar()
            self._consumir("DOP")
            self._registrar_instruccion(
                inicio_df,
                self.pos,
                "C_DEF ::= DF DOP CUERPO BREAK",
                len(self.errores) == err_df,
            )

            self._parse_cuerpo()
            if self._coincide("BR"):
                inicio_br = self.pos
                err_br = len(self.errores)
                self._avanzar()
                self._consumir("FI")
                self._registrar_instruccion(
                    inicio_br,
                    self.pos,
                    "BREAK ::= BR FI",
                    len(self.errores) == err_br,
                )

        self._consumir("LLC")

    # =========================================================================
    # EXPRESIONES, CASTEOS Y ACCESOS
    # =========================================================================

    def _parse_exp(self) -> str:
        """EXP ::= TERMINO (OP TERMINO)*"""
        tipo_izq: str = self._parse_termino()

        while self._coincide("OPA", "OPR", "OPL", "XOR"):
            tok_op: Token = self._actual()
            self._avanzar()
            tipo_der: str = self._parse_termino()
            tipo_izq = self._combinar_tipos_operacion(tipo_izq, tok_op, tipo_der)

        return tipo_izq

    def _parse_termino(self) -> str:
        """Evalúa casteos (TD) TERMINO, (EXP), OPU VAL, ACC o VAL."""
        tok: Optional[Token] = self._actual()
        if tok is None:
            self._agregar_error(1, "EOF", "Sintáctico")
            return "error"

        if (
            tok.tipo_token == "PA"
            and self._mirar(1) is not None
            and self._mirar(1).tipo_token == "TD"
            and self._mirar(2) is not None
            and self._mirar(2).tipo_token == "PC"
        ):
            self._avanzar()
            tok_cast: Token = self._actual()
            tipo_cast: str = tok_cast.lexema
            self._avanzar()
            self._avanzar()

            tipo_operando: str = self._parse_termino()
            if tipo_operando != "error" and (
                tipo_cast not in TIPOS_NUMERICOS
                or tipo_operando not in TIPOS_NUMERICOS
            ):
                if tipo_cast != tipo_operando:
                    self._agregar_error(tok_cast.linea, tipo_cast, "Semántico")
                    return "error"
            return tipo_cast

        if tok.tipo_token == "PA":
            self._avanzar()
            tipo_interno: str = self._parse_exp()
            self._consumir("PC")
            return tipo_interno

        if tok.tipo_token in ("DEC", "INC", "OPB", "OPN") or (
            tok.tipo_token == "OPA" and tok.lexema in ("-", "+")
        ):
            self._avanzar()
            tipo_val: str = self._parse_termino()
            if tok.tipo_token == "OPN":
                if tipo_val not in ("boolean", "error"):
                    self._agregar_error(tok.linea, tok.lexema, "Semántico")
                return "boolean"
            return tipo_val

        if (
            tok.tipo_token in ("ID", "VTS")
            and self._mirar(1) is not None
            and self._mirar(1).tipo_token in ("CA", "PA")
        ):
            return self._parse_acc(es_instruccion=False)

        tipo_base: str = self._parse_val()
        if self._coincide("INC", "DEC"):
            self._avanzar()
        return tipo_base

    def _parse_val(self) -> str:
        """VAL ::= VTE | VTD | VTS | VTB | ID | VTF | VTC"""
        tok: Optional[Token] = self._actual()
        if tok is None:
            return "error"

        if tok.tipo_token == "VTE":
            self._avanzar()
            return "VTE"
        if tok.tipo_token == "VTD":
            self._avanzar()
            return "double"
        if tok.tipo_token == "VTF":
            self._avanzar()
            return "float"
        if tok.tipo_token == "VTC":
            self._avanzar()
            return "char"
        if tok.tipo_token == "VTS":
            self._avanzar()
            return "String"
        if tok.tipo_token == "VTB":
            self._avanzar()
            return "boolean"
        if tok.tipo_token == "NU":
            self._avanzar()
            return "null"

        if tok.tipo_token == "ID":
            self._avanzar()
            simbolo: Optional[Simbolo] = self._buscar_variable_semantica(tok.lexema)
            if simbolo is None:
                self._agregar_error(tok.linea, tok.lexema, "Semántico")
                return "error"
            if not simbolo.inicializada:
                self._agregar_error(tok.linea, tok.lexema, "Semántico")
                return "error"
            return simbolo.tipo_dato

        self._agregar_error(tok.linea, tok.lexema, "Sintáctico")
        self._avanzar()
        return "error"

    def _parse_acc(self, es_instruccion: bool) -> str:
        """ACC ::= CLA OT"""
        tok_inicial: Token = self._actual()
        self._avanzar()

        if (
            tok_inicial.tipo_token == "ID"
            and tok_inicial.lexema != "System"
            and self._coincide("CA")
        ):
            simbolo: Optional[Simbolo] = self._buscar_variable_semantica(
                tok_inicial.lexema
            )
            if simbolo is None or not simbolo.inicializada:
                self._agregar_error(
                    tok_inicial.linea, tok_inicial.lexema, "Semántico"
                )

        ultimo_metodo: str = tok_inicial.lexema

        while self._coincide("CA", "PA"):
            if self._coincide("CA"):
                self._avanzar()
                tok_miembro: Optional[Token] = self._actual()
                if self._consumir("ID") and tok_miembro is not None:
                    ultimo_metodo = tok_miembro.lexema
                if self._coincide("PA"):
                    self._avanzar()
                    self._parse_args()
                    self._consumir("PC")
            elif self._coincide("PA"):
                self._avanzar()
                self._parse_args()
                self._consumir("PC")

        if es_instruccion:
            return "void"
        return self.metodos.get(ultimo_metodo, "int")

    def _parse_args(self) -> None:
        if not self._coincide("PC") and not self._fin():
            self._parse_exp()
            while self._coincide("CO"):
                self._avanzar()
                self._parse_exp()

    # =========================================================================
    # REGLAS DE VALIDACIÓN SEMÁNTICA (INCISO 5)
    # =========================================================================

    def _registrar_variable_semantica(
        self, nombre: str, tipo_dato: str, linea: int, inicializada: bool
    ) -> None:
        tabla_ambito: Dict[str, Simbolo] = self.ambitos[self.ambito_actual]
        if nombre in tabla_ambito:
            self._agregar_error(linea, nombre, "Semántico")
            return

        nuevo = Simbolo(
            id_num="",
            lexema=nombre,
            token="ID",
            tipo_dato=tipo_dato,
            ambito=self.ambito_actual,
            inicializada=inicializada,
        )
        tabla_ambito[nombre] = nuevo

        for sim in self.tabla_simbolos:
            if sim.lexema == nombre and sim.tipo_dato == "":
                sim.tipo_dato = tipo_dato
                sim.ambito = self.ambito_actual
                sim.inicializada = inicializada
                break

    def _buscar_variable_semantica(self, nombre: str) -> Optional[Simbolo]:
        if nombre in self.ambitos.get(self.ambito_actual, {}):
            return self.ambitos[self.ambito_actual][nombre]
        if nombre in self.ambitos.get("global", {}):
            return self.ambitos["global"][nombre]
        return None

    def _verificar_variable_numerica_usada(self, tok_id: Token) -> None:
        simbolo: Optional[Simbolo] = self._buscar_variable_semantica(tok_id.lexema)
        if (
            simbolo is None
            or not simbolo.inicializada
            or simbolo.tipo_dato not in TIPOS_NUMERICOS
        ):
            self._agregar_error(tok_id.linea, tok_id.lexema, "Semántico")

    def _combinar_tipos_operacion(
        self, tipo_izq: str, tok_op: Token, tipo_der: str
    ) -> str:
        if tipo_izq == "error" or tipo_der == "error":
            return "error"

        op_tipo: str = tok_op.tipo_token
        linea: int = tok_op.linea

        if op_tipo == "OPA":
            if tok_op.lexema == "+" and ("String" in (tipo_izq, tipo_der)):
                return "String"
            if tipo_izq in TIPOS_NUMERICOS and tipo_der in TIPOS_NUMERICOS:
                if "double" in (tipo_izq, tipo_der):
                    return "double"
                if "float" in (tipo_izq, tipo_der):
                    return "float"
                if "long" in (tipo_izq, tipo_der):
                    return "long"
                if tipo_izq == "VTE" and tipo_der == "VTE":
                    return "VTE"
                return "int"
            self._agregar_error(linea, tok_op.lexema, "Semántico")
            return "error"

        if op_tipo == "OPR":
            if tok_op.lexema in ("==", "!="):
                if (
                    tipo_izq in TIPOS_NUMERICOS and tipo_der in TIPOS_NUMERICOS
                ) or (tipo_izq == tipo_der):
                    return "boolean"
            else:
                if tipo_izq in TIPOS_NUMERICOS and tipo_der in TIPOS_NUMERICOS:
                    return "boolean"
            self._agregar_error(linea, tok_op.lexema, "Semántico")
            return "error"

        if op_tipo in ("OPL", "XOR"):
            if tipo_izq == "boolean" and tipo_der == "boolean":
                return "boolean"
            if tipo_izq in TIPOS_ENTEROS and tipo_der in TIPOS_ENTEROS:
                return "long" if "long" in (tipo_izq, tipo_der) else "int"
            self._agregar_error(linea, tok_op.lexema, "Semántico")
            return "error"

        return "error"

    def _validar_compatibilidad_tipos(
        self, tipo_destino: str, tipo_origen: str, linea: int, lexema_error: str
    ) -> None:
        if tipo_destino == tipo_origen:
            return

        if tipo_destino == "float" and tipo_origen == "double":
            self._agregar_error(linea, lexema_error, "Semántico")
            return

        if tipo_destino == "double" and tipo_origen in TIPOS_NUMERICOS:
            return
        if tipo_destino == "float" and tipo_origen in TIPOS_ENTEROS:
            return

        if (
            tipo_destino in JERARQUIA_ENTEROS
            and tipo_origen in JERARQUIA_ENTEROS
        ):
            rango_dest: int = JERARQUIA_ENTEROS[tipo_destino]
            rango_orig: int = JERARQUIA_ENTEROS[tipo_origen]
            if rango_dest >= rango_orig:
                return
            self._agregar_error(linea, lexema_error, "Semántico")
            return

        if (
            tipo_destino not in TIPOS_NUMERICOS
            and tipo_destino != "boolean"
            and tipo_origen == "null"
        ):
            return

        self._agregar_error(linea, lexema_error, "Semántico")

    # =========================================================================
    # UTILIDADES DE NAVEGACIÓN Y RECUPERACIÓN INTELIGENTE DE ';'
    # =========================================================================

    def _actual(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _mirar(self, desplazamiento: int) -> Optional[Token]:
        indice: int = self.pos + desplazamiento
        return self.tokens[indice] if 0 <= indice < len(self.tokens) else None

    def _fin(self) -> bool:
        return self.pos >= len(self.tokens)

    def _avanzar(self) -> Optional[Token]:
        tok: Optional[Token] = self._actual()
        if tok is not None:
            self.pos += 1
        return tok

    def _coincide(self, *tipos_esperados: str) -> bool:
        tok: Optional[Token] = self._actual()
        return tok is not None and tok.tipo_token in tipos_esperados

    def _consumir(self, tipo_esperado: str) -> bool:
        tok: Optional[Token] = self._actual()
        if tok is not None and tok.tipo_token == tipo_esperado:
            self.pos += 1
            return True

        if tipo_esperado == "FI" and self.pos > 0:
            tok_previo: Token = self.tokens[self.pos - 1]
            self._agregar_error(tok_previo.linea, ";", "Sintáctico")
            return False

        linea: int = (
            tok.linea
            if tok is not None
            else (self.tokens[-1].linea if self.tokens else 1)
        )
        lexema: str = tok.lexema if tok is not None else "EOF"
        self._agregar_error(linea, lexema, "Sintáctico")
        return False

    def _error_actual(self) -> None:
        tok: Optional[Token] = self._actual()
        if tok is not None:
            self._agregar_error(tok.linea, tok.lexema, "Sintáctico")

    def _agregar_error(self, linea: int, error: str, tipo: str) -> None:
        self.errores.append(ErrorCompilador(linea=linea, error=error, tipo=tipo))

    def _sincronizar_hasta_fi(self) -> None:
        linea_previa: int = (
            self.tokens[self.pos - 1].linea if self.pos > 0 else -1
        )

        while not self._fin() and not self._coincide("FI", "LLC"):
            tok: Optional[Token] = self._actual()
            if tok is not None:
                if tok.tipo_token in (
                    "TD",
                    "STR",
                    "PRIF",
                    "PRW",
                    "PRDO",
                    "PRF",
                    "PRSW",
                    "RTN",
                    "BR",
                    "MA",
                ):
                    return
                if tok.tipo_token == "ID" and tok.linea > linea_previa:
                    return
            self._avanzar()

        if self._coincide("FI"):
            self._avanzar()

    def _sincronizar_en_cuerpo(self) -> None:
        if not self._fin():
            self._avanzar()
        while not self._fin() and not self._coincide(
            "FI", "LLC", "TD", "STR", "PRIF", "PRW", "PRDO", "PRF", "PRSW", "RTN", "BR"
        ):
            self._avanzar()
        if self._coincide("FI"):
            self._avanzar()

    def _registrar_instruccion(
        self,
        indice_inicio: int,
        indice_fin: int,
        regla_glc: str,
        es_valida: bool = True,
    ) -> None:
        segmento: List[Token] = self.tokens[indice_inicio:indice_fin]
        if not segmento:
            return
        linea: int = segmento[0].linea
        texto: str = " ".join(t.lexema for t in segmento)
        texto = (
            texto.replace(" ;", ";")
            .replace(" :", ":")
            .replace(" . ", ".")
            .replace(" ( ", "(")
            .replace(" )", ")")
        )
        self.instrucciones_evaluadas.append(
            Instruccion(
                linea=linea,
                texto=texto,
                regla_glc=regla_glc,
                es_valida=es_valida,
            )
        )