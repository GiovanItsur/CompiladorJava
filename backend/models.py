from dataclasses import dataclass


@dataclass
class Token:
    """Representa una unidad léxica extraída del código fuente."""
    lexema: str
    tipo_token: str
    linea: int


@dataclass
class Simbolo:
    """
    Representa una fila en la Tabla de Símbolos.
    Incluye campos visuales (id_num, lexema, token) y metadatos semánticos.
    """
    id_num: str
    lexema: str
    token: str
    tipo_dato: str = ""
    ambito: str = ""
    inicializada: bool = False


@dataclass
class Instruccion:
    """
    Representa una instrucción evaluada por el parser.
    Si 'es_valida' es False, la tabla la mostrará en color rojo.
    """
    linea: int
    texto: str
    regla_glc: str
    es_valida: bool = True


@dataclass
class ErrorCompilador:
    """
    Representa un error detectado en cualquiera de las fases.
    El campo 'tipo' puede ser: 'Léxico', 'Sintáctico' o 'Semántico'.
    """
    linea: int
    error: str
    tipo: str