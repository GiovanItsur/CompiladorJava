from typing import Dict, List, Optional, Tuple, Set
from backend.models import ErrorCompilador, Simbolo, Token

# Palabras reservadas oficiales
PALABRAS_RESERVADAS: Dict[str, str] = {
    "int": "TD",
    "boolean": "TD",
    "double": "TD",
    "float": "TD",
    "long": "TD",
    "short": "TD",
    "byte": "TD",
    "char": "TD",
    "String": "STR",
    "public": "MA",
    "protected": "MA",
    "private": "MA",
    "abstract": "MA",
    "class": "CL",
    "void": "TM",
    "static": "ST",
    "final": "TDD",
    "package": "PCK",
    "import": "IMP",
    "extends": "EXTS",
    "implements": "IMPL",
    "new": "NW",
    "this": "RF",
    "super": "SPR",
    "return": "RTN",
    "instanceof": "INOF",
    "synchronized": "SY",
    "throws": "TH",
    "assert": "ASR",
    "if": "PRIF",
    "else": "PRE",
    "switch": "PRSW",
    "case": "CS",
    "default": "DF",
    "deafult": "DF",
    "break": "BR",
    "while": "PRW",
    "do": "PRDO",
    "for": "PRF",
    "try": "ISE",
    "catch": "CE",
    "finally": "FIN",
    "true": "VTB",
    "false": "VTB",
    "null": "NU",
}

# Identificadores de Java
IDS_BASE_JAVA: Set[str] = {
    "System",
    "out",
    "in",
    "err",
    "println",
    "print",
    "printf",
    "length",
    "equals",
    "toString",
    "charAt",
    "substring",
    "indexOf",
    "toUpperCase",
    "toLowerCase",
    "trim",
    "Scanner",
    "nextInt",
    "nextDouble",
    "nextFloat",
    "nextLine",
    "nextBoolean",
    "next",
    "Math",
    "abs",
    "sqrt",
    "pow",
    "max",
    "min",
    "round",
    "random",
    "Integer",
    "Double",
    "Float",
    "Boolean",
    "Character",
    "Object",
    "Exception",
}

OPERADORES_DOBLES: Dict[str, str] = {
    "++": "INC",
    "--": "DEC",
    "==": "OPR",
    "!=": "OPR",
    "<=": "OPR",
    ">=": "OPR",
    "&&": "OPL",
    "||": "OPL",
}

SIMBOLOS_SIMPLES: Dict[str, str] = {
    "=": "ODA",
    ";": "FI",
    "{": "LLA",
    "}": "LLC",
    "(": "PA",
    ")": "PC",
    "[": "COA",
    "]": "COC",
    "+": "OPA",
    "-": "OPA",
    "*": "OPA",
    "/": "OPA",
    "%": "OPA",
    ":": "DOP",
    "?": "OPT",
    "&": "OPL",
    "|": "OPL",
    "<": "OPR",
    ">": "OPR",
    ".": "CA",
    ",": "CO",
    "^": "XOR",
    "!": "OPN",
    "~": "OPB",
}

def analizar_lexico(
    codigo_depurado: str, mapa_lineas: List[int]
) -> Tuple[List[Token], List[Simbolo], List[ErrorCompilador]]:

    """
    Fase 3: Escanea el código depurado y genera la lista de tokens,
    la Tabla de Símbolos (separando IDs globales y locales por mét odo)
    y la lista de errores léxicos.
    """

    tokens: List[Token] = []
    tabla_simbolos: List[Simbolo] = []
    errores: List[ErrorCompilador] = []

    ids_por_ambito: Dict[str, Dict[str, int]] = {"global": {}}
    ambito_actual: str = "global"
    nivel_llaves: int = 0
    contador_ids: int = 1

    longitud: int = len(codigo_depurado)
    i: int = 0

    while i < longitud:
        actual: str = codigo_depurado[i]
        linea_actual: int = mapa_lineas[i] if i < len(mapa_lineas) else 1

        # 1. Ignorar espacios y saltos de línea
        if actual in (" ", "\n"):
            i += 1
            continue

        # 2. Control de llaves '{' y '}' para seguimiento de ámbitos
        if actual == "{":
            nivel_llaves += 1
            _registrar_token_y_simbolo(
                "{", "LLA", linea_actual, tokens, tabla_simbolos
            )
            i += 1
            continue

        if actual == "}":
            nivel_llaves = max(0, nivel_llaves - 1)
            if nivel_llaves <= 1:
                ambito_actual = "global"
            _registrar_token_y_simbolo(
                "}", "LLC", linea_actual, tokens, tabla_simbolos
            )
            i += 1
            continue

        # 3. Literales de cadena (VTS)
        if actual == '"':
            lexema, nuevo_indice, cerrado = _leer_cadena(codigo_depurado, i, '"')
            i = nuevo_indice
            if cerrado:
                _registrar_token_y_simbolo(
                    lexema, "VTS", linea_actual, tokens, tabla_simbolos
                )
            else:
                errores.append(
                    ErrorCompilador(linea=linea_actual, error=lexema, tipo="Léxico")
                )
            continue

        # 4. Literales de carácter (VTC)
        if actual == "'":
            lexema, nuevo_indice, cerrado = _leer_cadena(codigo_depurado, i, "'")
            i = nuevo_indice
            if cerrado and _es_caracter_valido(lexema):
                _registrar_token_y_simbolo(
                    lexema, "VTC", linea_actual, tokens, tabla_simbolos
                )
            else:
                errores.append(
                    ErrorCompilador(linea=linea_actual, error=lexema, tipo="Léxico")
                )
            continue

        # 5. Operadores dobles (++, --, ==, !=, <=, >=, &&, ||)
        if (i + 1) < longitud:
            par: str = codigo_depurado[i : i + 2]
            if par in OPERADORES_DOBLES:
                _registrar_token_y_simbolo(
                    par, OPERADORES_DOBLES[par], linea_actual, tokens, tabla_simbolos
                )
                i += 2
                continue

        # 6. Números (VTE, VTD, VTF)
        if actual.isdigit():
            lexema, nuevo_indice = _leer_secuencia_numerica(codigo_depurado, i)
            i = nuevo_indice
            tipo_num: Optional[str] = _clasificar_numero(lexema)
            if tipo_num is not None:
                _registrar_token_y_simbolo(
                    lexema, tipo_num, linea_actual, tokens, tabla_simbolos
                )
            else:
                errores.append(
                    ErrorCompilador(linea=linea_actual, error=lexema, tipo="Léxico")
                )
            continue

        # 7. Palabras reservadas, PMAIN, IDs base de Java e IDs del programador
        if actual.isalpha() or actual == "_":
            lexema, nuevo_indice = _leer_palabra(codigo_depurado, i)
            i = nuevo_indice

            # Regla de PMAIN
            if lexema == "main" and _es_firma_main(tokens, codigo_depurado, i):
                _registrar_token_y_simbolo(
                    lexema, "PMAIN", linea_actual, tokens, tabla_simbolos
                )
                ambito_actual = "main"
                ids_por_ambito["main"] = {}
                continue

            # Palabras reservadas
            if lexema in PALABRAS_RESERVADAS:
                _registrar_token_y_simbolo(
                    lexema,
                    PALABRAS_RESERVADAS[lexema],
                    linea_actual,
                    tokens,
                    tabla_simbolos,
                )
                continue

            # IDs base de Java (System, out, println, length, etc.):
            # Llevan token 'ID', pero NO se les asigna número en la columna ID.
            if lexema in IDS_BASE_JAVA:
                _registrar_token_y_simbolo(
                    lexema, "ID", linea_actual, tokens, tabla_simbolos
                )
                continue

            # Declaración de mét odo del programador en el cuerpo de la clase
            if nivel_llaves == 1 and _es_declaracion_metodo(tokens, codigo_depurado, i):
                contador_ids = _registrar_identificador(
                    lexema,
                    linea_actual,
                    "global",
                    tokens,
                    tabla_simbolos,
                    ids_por_ambito,
                    contador_ids,
                )
                ambito_actual = lexema
                ids_por_ambito[ambito_actual] = {}
                continue

            # Identificador del programador (global o local)
            contador_ids = _registrar_identificador(
                lexema,
                linea_actual,
                ambito_actual,
                tokens,
                tabla_simbolos,
                ids_por_ambito,
                contador_ids,
            )
            continue

        # 8. Operadores y símbolos simples
        if actual in SIMBOLOS_SIMPLES:
            _registrar_token_y_simbolo(
                actual, SIMBOLOS_SIMPLES[actual], linea_actual, tokens, tabla_simbolos
            )
            i += 1
            continue

        # 9. Carácter inválido (Error Léxico)
        errores.append(
            ErrorCompilador(linea=linea_actual, error=actual, tipo="Léxico")
        )
        i += 1

    return tokens, tabla_simbolos, errores


def _registrar_token_y_simbolo(
    lexema: str,
    tipo_token: str,
    linea: int,
    tokens: List[Token],
    tabla_simbolos: List[Simbolo],
) -> None:
    """Agrega un token sin número de ID a la lista de tokens y a la Tabla de Símbolos."""
    tokens.append(Token(lexema=lexema, tipo_token=tipo_token, linea=linea))
    tabla_simbolos.append(Simbolo(id_num="", lexema=lexema, token=tipo_token))


def _registrar_identificador(
    lexema: str,
    linea: int,
    ambito_actual: str,
    tokens: List[Token],
    tabla_simbolos: List[Simbolo],
    ids_por_ambito: Dict[str, Dict[str, int]],
    contador_ids: int,
) -> int:
    """Registra un ID del programador separando el ámbito global del local."""
    es_declaracion: bool = _es_declaracion_variable(tokens)
    tokens.append(Token(lexema=lexema, tipo_token="ID", linea=linea))

    mapa_global: Dict[str, int] = ids_por_ambito["global"]
    mapa_local: Dict[str, int] = ids_por_ambito.setdefault(ambito_actual, {})

    if ambito_actual == "global":
        if lexema not in mapa_global:
            mapa_global[lexema] = contador_ids
            tabla_simbolos.append(
                Simbolo(id_num=str(contador_ids), lexema=lexema, token="ID")
            )
            return contador_ids + 1
        else:
            num_id: int = mapa_global[lexema]
            tabla_simbolos.append(
                Simbolo(id_num="", lexema=f"ID{num_id}", token="ID")
            )
            return contador_ids

    if es_declaracion:
        if lexema not in mapa_local:
            mapa_local[lexema] = contador_ids
            tabla_simbolos.append(
                Simbolo(id_num=str(contador_ids), lexema=lexema, token="ID")
            )
            return contador_ids + 1
        else:
            num_id = mapa_local[lexema]
            tabla_simbolos.append(
                Simbolo(id_num="", lexema=f"ID{num_id}", token="ID")
            )
            return contador_ids

    if lexema in mapa_local:
        num_id = mapa_local[lexema]
        tabla_simbolos.append(
            Simbolo(id_num="", lexema=f"ID{num_id}", token="ID")
        )
        return contador_ids

    if lexema in mapa_global:
        num_id = mapa_global[lexema]
        tabla_simbolos.append(
            Simbolo(id_num="", lexema=f"ID{num_id}", token="ID")
        )
        return contador_ids

    mapa_local[lexema] = contador_ids
    tabla_simbolos.append(
        Simbolo(id_num=str(contador_ids), lexema=lexema, token="ID")
    )
    return contador_ids + 1


def _es_declaracion_variable(tokens_previos: List[Token]) -> bool:
    """Verifica si el token previo es un tipo de dato que declara una variable."""
    if not tokens_previos:
        return False

    ultimo: Token = tokens_previos[-1]
    if ultimo.tipo_token in ("TD", "STR"):
        return True

    if (
        ultimo.tipo_token == "COC"
        and len(tokens_previos) >= 3
        and tokens_previos[-2].tipo_token == "COA"
        and tokens_previos[-3].tipo_token == "STR"
    ):
        return True

    if ultimo.tipo_token == "ID":
        return True

    return False


def _es_declaracion_metodo(tokens_previos: List[Token], codigo: str, indice_post_id: int) -> bool:
    """Verifica si un ID en nivel de clase es el nombre de un métod o."""
    if len(tokens_previos) < 2:
        return False

    penultimo: Token = tokens_previos[-2]
    ultimo: Token = tokens_previos[-1]

    if penultimo.tipo_token != "MA" or ultimo.tipo_token not in (
        "TD",
        "STR",
        "TM",
        "ID",
    ):
        return False

    j: int = indice_post_id
    while j < len(codigo) and codigo[j] in (" ", "\n"):
        j += 1

    return j < len(codigo) and codigo[j] == "("


def _es_firma_main(tokens_previos: List[Token], codigo: str, indice_post_main: int) -> bool:
    """Verifica que 'main' esté precedido por 'public static void' y seguido de '('."""
    if len(tokens_previos) < 3:
        return False

    es_encabezado: bool = (
        tokens_previos[-3].lexema == "public"
        and tokens_previos[-2].lexema == "static"
        and tokens_previos[-1].lexema == "void"
    )
    if not es_encabezado:
        return False

    j: int = indice_post_main
    while j < len(codigo) and codigo[j] in (" ", "\n"):
        j += 1

    return j < len(codigo) and codigo[j] == "("


def _leer_cadena(codigo: str, inicio: int, delimitador: str) -> Tuple[str, int, bool]:
    longitud: int = len(codigo)
    i: int = inicio + 1

    while i < longitud and codigo[i] != "\n":
        if codigo[i] == "\\" and (i + 1) < longitud:
            i += 2
            continue
        if codigo[i] == delimitador:
            return codigo[inicio : i + 1], i + 1, True
        i += 1

    return codigo[inicio:i], i, False


def _es_caracter_valido(lexema: str) -> bool:
    contenido: str = lexema[1:-1]
    if len(contenido) == 1 and contenido != "'":
        return True
    if len(contenido) == 2 and contenido.startswith("\\"):
        return True
    return False


def _leer_secuencia_numerica(codigo: str, inicio: int) -> Tuple[str, int]:
    longitud: int = len(codigo)
    i: int = inicio
    while i < longitud and (codigo[i].isalnum() or codigo[i] == "_" or codigo[i] == "."):
        i += 1
    return codigo[inicio:i], i


def _clasificar_numero(lexema: str) -> Optional[str]:
    if lexema.isdigit():
        return "VTE"

    if "." not in lexema:
        return None

    partes: List[str] = lexema.split(".")
    if len(partes) != 2:
        return None

    entera, decimal = partes[0], partes[1]
    if not entera.isdigit() or decimal == "":
        return None

    if decimal.endswith("f") or decimal.endswith("F"):
        digitos: str = decimal[:-1]
        return "VTF" if (digitos.isdigit() and len(digitos) > 0) else None

    if decimal.isdigit():
        return "VTD"

    return None


def _leer_palabra(codigo: str, inicio: int) -> Tuple[str, int]:
    longitud: int = len(codigo)
    i: int = inicio
    while i < longitud and (codigo[i].isalnum() or codigo[i] == "_"):
        i += 1
    return codigo[inicio:i], i