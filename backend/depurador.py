from typing import List, Tuple

def _es_caracter_palabra(c: str) -> bool:
    return c.isalnum() or c == "_"

def depurar_codigo(codigo_crudo: str) -> Tuple[str, List[int]]:
    """
    Fase 1: Limpia el código fuente eliminando comentarios, tabulaciones,
    líneas vacías y espacios innecesarios alrededor de operadores/delimitadores,
    conservando un salto de línea por cada línea con código válido.
    """
    caracteres_depurados: List[str] = []
    mapa_lineas: List[int] = []

    longitud: int = len(codigo_crudo)
    i: int = 0
    linea_actual: int = 1

    en_cadena: bool = False
    en_caracter: bool = False
    espacio_pendiente: bool = False

    while i < longitud:
        actual: str = codigo_crudo[i]
        siguiente: str = codigo_crudo[i + 1] if (i + 1) < longitud else ""

        # 1. Manejo de saltos de línea (conservando saltos entre líneas con código)
        if actual == "\n":
            linea_actual += 1
            en_cadena = False
            en_caracter = False
            espacio_pendiente = False
            # Solo agregamos salto de línea si la línea actual tuvo código real
            if caracteres_depurados and caracteres_depurados[-1] != "\n":
                caracteres_depurados.append("\n")
                mapa_lineas.append(linea_actual)
            i += 1
            continue

        # 2. Conservar literales de cadena ("...") intactos
        if en_cadena:
            caracteres_depurados.append(actual)
            mapa_lineas.append(linea_actual)
            if actual == "\\" and siguiente != "":
                i += 1
                caracteres_depurados.append(codigo_crudo[i])
                mapa_lineas.append(linea_actual)
            elif actual == '"':
                en_cadena = False
            i += 1
            continue

        # 3. Conservar literales de carácter ('...') intactos
        if en_caracter:
            caracteres_depurados.append(actual)
            mapa_lineas.append(linea_actual)
            if actual == "\\" and siguiente != "":
                i += 1
                caracteres_depurados.append(codigo_crudo[i])
                mapa_lineas.append(linea_actual)
            elif actual == "'":
                en_caracter = False
            i += 1
            continue

        # 4. Ignorar comentarios de una línea (// ...) hasta el salto de línea
        if actual == "/" and siguiente == "/":
            i += 2
            while i < longitud and codigo_crudo[i] != "\n":
                i += 1
            continue

        # 5. Ignorar comentarios multilínea (/* ... */)
        if actual == "/" and siguiente == "*":
            i += 2
            while i < longitud:
                if codigo_crudo[i] == "\n":
                    linea_actual += 1
                if (
                    codigo_crudo[i] == "*"
                    and (i + 1) < longitud
                    and codigo_crudo[i + 1] == "/"
                ):
                    i += 2
                    break
                i += 1
            espacio_pendiente = True
            continue

        # 6. Marcar espacios y tabulaciones como pendientes
        if actual in (" ", "\t", "\r"):
            espacio_pendiente = True
            i += 1
            continue

        # 7. Colapsar puntos y comas consecutivos (ej. ';;;;' -> ';')
        if actual == ";":
            espacio_pendiente = False
            if not caracteres_depurados or caracteres_depurados[-1] != ";":
                caracteres_depurados.append(";")
                mapa_lineas.append(linea_actual)
            i += 1
            continue

        # 8. Insertar espacio ÚNICAMENTE si separa dos palabras/identificadores
        #    (ej. 'public class', 'int cantidad', 'return total')
        if espacio_pendiente:
            if (
                caracteres_depurados
                and _es_caracter_palabra(caracteres_depurados[-1])
                and _es_caracter_palabra(actual)
            ):
                caracteres_depurados.append(" ")
                mapa_lineas.append(linea_actual)
            espacio_pendiente = False

        # 9. Apertura de comillas dobles o simples
        if actual == '"':
            en_cadena = True
        elif actual == "'":
            en_caracter = True

        # 10. Agregar carácter depurado
        caracteres_depurados.append(actual)
        mapa_lineas.append(linea_actual)
        i += 1

    # Quitar salto de línea sobrante al final del archivo si existe
    if caracteres_depurados and caracteres_depurados[-1] == "\n":
        caracteres_depurados.pop()
        mapa_lineas.pop()

    return "".join(caracteres_depurados), mapa_lineas