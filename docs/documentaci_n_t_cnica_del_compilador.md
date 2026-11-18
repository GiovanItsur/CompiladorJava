# Manual Técnico y Guía de Defensa: Simulador de la Etapa de Análisis de un Compilador (GLC v7)

**Materia:** Lenguajes y Autómatas II — Ingeniería en Sistemas Computacionales (ITSUR)  
**Docente:** Mtra. Nancy Carolina Quintana Martínez  
**Arquitectura:** Python 3 + `customtkinter` + `tkinter.ttk` (7 módulos desacoplados)

---

## 1. Arquitectura General y Flujo de Ejecución (*Pipeline*)

El simulador separa estrictamente la lógica de análisis (`backend/`) de la interfaz gráfica de usuario (`ui_inicio.py`, `ui_analizador.py`, `main.py`).

Cada vez que el usuario escribe en el editor y deja de presionar teclas durante **300 milisegundos** (*debounce*), el método `ejecutar_analisis()` en `ui_analizador.py` ejecuta una tubería (*pipeline*) lineal de 4 pasos:

1. **Fase 1 (Inciso 1) $\rightarrow$ `depurar_codigo(codigo_crudo)` en `backend/depurador.py`:**
   Elimina comentarios (`//` y `/* */`), tabulaciones, líneas vacías, espacios innecesarios y puntos y comas repetidos (`;;;;` $\rightarrow$ `;`), devolviendo el `codigo_depurado` y la lista paralela `mapa_lineas`.
2. **Fase 3 (Inciso 3) $\rightarrow$ `analizar_lexico(codigo_depurado, mapa_lineas)` en `backend/lexer.py`:**
   Recorre el código depurado carácter por carácter, clasifica cada unidad léxica con la lista oficial de tokens, separa los ámbitos (`global` vs métodos) para numerar los `ID` del programador y reemplaza sus referencias posteriores por `ID1`, `ID2`, etc.
3. **Fases 2, 4, 5 y 6 (Incisos 2, 4, 5 y 6) $\rightarrow$ `analizar_sintactico_semantico(tokens, tabla_simbolos)` en `backend/parser.py`:**
   * Verifica primero el **Inciso 2** (`package`, `public class` y método `main` con llaves balanceadas). Si falla, limpia las listas y detiene el proceso.
   * Si cumple el Inciso 2, ejecuta el descenso recursivo basado en la **GLC v7**, extrae las instrucciones indicando su regla gramatical y valida toda la correspondencia semántica de tipos y ámbitos.
4. **Fase 7 (Inciso 7) $\rightarrow$ Actualización Continua en `ui_analizador.py`:**
   Puebla en tiempo real el panel de Código Depurado, la Tabla de Símbolos, la Tabla de Instrucciones (pintando en rojo las filas con error) y la Tabla de Errores.

---

## 2. Módulo `backend/models.py`: Estructuras de Datos

Utiliza el decorador `@dataclass` de Python para generar automáticamente los constructores `__init__` con tipado estático claro.

### 2.1. `Token` vs `Simbolo` (Pregunta clave de defensa)
```python
@dataclass
class Token:
    lexema: str
    tipo_token: str
    linea: int

@dataclass
class Simbolo:
    id_num: str
    lexema: str
    token: str
    tipo_dato: str = ""
    ambito: str = ""
    inicializada: bool = False
```
* **¿Por qué existen dos clases separadas (`Token` y `Simbolo`)?**
  * El **Inciso 3b** exige que en la **Tabla de Símbolos** los identificadores usados después de su declaración cambien su texto a `ID1`, `ID2`, etc., y dejen su columna `ID` vacía (`""`).
  * Sin embargo, en el **Inciso 5**, `parser.py` necesita conocer el nombre original de la variable (ej. `"precio"` o `"cantidad"`) en cada operación para buscar su tipo de dato y saber si fue inicializada.
  * Por ello, `lexer.py` guarda siempre el nombre real en la lista `tokens` (para uso interno del parser) y guarda el formato enlazado (`ID1`, `ID2`) en la lista `tabla_simbolos` (para visualización en la GUI).
* **Campos semánticos por defecto:** `tipo_dato`, `ambito` e `inicializada` nacen vacíos en la Fase 3 (Léxico) y son rellenados por `parser.py` en la Fase 5 (Semántico).

### 2.2. `Instruccion` y `ErrorCompilador`
```python
@dataclass
class Instruccion:
    linea: int
    texto: str
    regla_glc: str
    es_valida: bool = True

@dataclass
class ErrorCompilador:
    linea: int
    error: str
    tipo: str
```
* **`Instruccion`:** Almacena el número de renglón (`linea`), la sentencia reconstruida (`texto`), la producción de la GLC aplicada (`regla_glc`) y la bandera `es_valida` (si es `False`, la tabla gráfica colorea la fila en rojo).
* **`ErrorCompilador`:** Representa las 3 columnas de la Tabla de Errores (`Línea`, `Error`, `Tipo`: `"Léxico"`, `"Sintáctico"` o `"Semántico"`).

---

## 3. Módulo `backend/depurador.py`: Fase 1 (Limpieza y Rastreo de Líneas)

Resuelve el **Inciso 1** de la rúbrica mediante dos funciones:

### 3.1. `_es_caracter_palabra(c: str) -> bool`
* **Qué hace:** Devuelve `True` si el carácter `c` es alfanumérico (`c.isalnum()`) o un guion bajo (`"_"`).
* **Por qué existe:** Permite decidir cuándo es obligatorio conservar un espacio en blanco. Entre dos palabras seguidas (`public class`, `int cantidad`, `return total`) sí debe quedar un espacio; pero entre una palabra y un operador o símbolo (`cantidad=3;`, `if(cantidad>2){`) el espacio se elimina.

### 3.2. `depurar_codigo(codigo_crudo: str) -> Tuple[str, List[int]]`
Recorre `codigo_crudo` carácter por carácter con un índice `i` y construye dos listas paralelas: `caracteres_depurados` y `mapa_lineas`.

* **¿Cómo funciona `mapa_lineas` para no perder el renglón original de los errores?**
  Cada vez que el depurador encuentra un `"\n"`, incrementa `linea_actual += 1`. Cada vez que inserta un carácter válido en `caracteres_depurados`, inserta también `linea_actual` en `mapa_lineas`. Ambas listas tienen exactamente la misma longitud: el carácter en `codigo_depurado[k]` provino del renglón `mapa_lineas[k]`.
* **Protección de cadenas (`en_cadena`) y caracteres (`en_caracter`):**
  Cuando aparece `"` o `'`, se activan estas banderas booleanas. Mientras estén activas, el ciclo copia todos los caracteres literalmente (incluyendo espacios, `//` o `;;;;`) y respeta secuencias escapadas como `\"`. Así evita borrar contenido dentro de literales `VTS` o `VTC`.
* **Eliminación de comentarios `//` y `/* */`:**
  * Si detecta `//`, avanza `i` hasta encontrar `"\n"`.
  * Si detecta `/*`, avanza `i` hasta encontrar `*/`, pero sigue incrementando `linea_actual += 1` si hay saltos de línea dentro del comentario multilínea para no desfasar el conteo de renglones.
* **Colapso de múltiples puntos y comas (`;;;;` $\rightarrow$ `;`):**
  ```python
  if actual == ";":
      espacio_pendiente = False
      if not caracteres_depurados or caracteres_depurados[-1] != ";":
          caracteres_depurados.append(";")
          mapa_lineas.append(linea_actual)
      i += 1
      continue
  ```
  Si el último carácter emitido en `caracteres_depurados` ya fue un `";"`, ignora cualquier `";"` repetido consecutivo.

---

## 4. Módulo `backend/lexer.py`: Fase 3 (Análisis Léxico y Tabla de Símbolos)

### 4.1. Constantes de Clasificación Léxica (Búsqueda en tiempo $O(1)$)
1. **`PALABRAS_RESERVADAS` (`Dict[str, str]`):** Mapea cada palabra reservada de Java a su token oficial del PDF (`"int": "TD"`, `"String": "STR"`, `"public": "MA"`, `"void": "TM"`, `"if": "PRIF"`, etc.). Incluye tanto `"default": "DF"` como `"deafult": "DF"`.
2. **`IDS_BASE_JAVA` (`Set[str]`):** Conjunto con identificadores propios de la librería estándar de Java (`"System"`, `"out"`, `"println"`, `"length"`, `"Scanner"`, `"Math"`, etc.). Se clasifican con el token `"ID"`, pero **no** reciben número en la columna `ID` porque no son variables creadas por el programador.
3. **`OPERADORES_DOBLES` (`Dict[str, str]`):** Operadores de 2 caracteres (`"++": "INC"`, `"--": "DEC"`, `"==": "OPR"`, `"!=": "OPR"`, `"<=": "OPR"`, `">=": "OPR"`, `"&&": "OPL"`, `"||": "OPL"`). Se evalúan antes que los simples.
4. **`SIMBOLOS_SIMPLES` (`Dict[str, str]`):** Operadores y delimitadores de 1 carácter (`"=": "ODA"`, `";": "FI"`, `"{": "LLA"`, `"}": "LLC"`, `"(": "PA"`, `")": "PC"`, `".": "CA"`, `",": "CO"`, `"!": "OPN"`, etc.).

---

### 4.2. Desglose de las 11 Funciones de `lexer.py`

#### 1. `analizar_lexico(codigo_depurado, mapa_lineas)`
Es el motor principal de la Fase 3. Mantiene el diccionario `ids_por_ambito = {"global": {}}`, la variable `ambito_actual = "global"`, el contador `nivel_llaves = 0` y el `contador_ids = 1`. Recorre `codigo_depurado` con un ciclo `while i < longitud:` dividido en 9 bloques:
* **Bloque 1:** Ignora espacios `" "` y saltos `"\n"`.
* **Bloque 2 (`{` y `}`):** Al ver `{` suma 1 a `nivel_llaves` y registra `"LLA"`. Al ver `}` resta 1 a `nivel_llaves`; si `nivel_llaves <= 1`, regresa `ambito_actual = "global"` (porque salió del cuerpo de un método y volvió al nivel de la clase).
* **Bloque 3 (`"..."`):** Llama a `_leer_cadena` con `'"'`. Si cerró bien, registra `"VTS"`; si no, agrega error `"Léxico"`.
* **Bloque 4 (`'...'`):** Llama a `_leer_cadena` con `"'"` y valida con `_es_caracter_valido`. Si cumple, registra `"VTC"`; si falla (ej. `'AB'`), agrega error `"Léxico"`.
* **Bloque 5:** Revisa si `codigo_depurado[i : i + 2]` está en `OPERADORES_DOBLES` y avanza `i += 2`.
* **Bloque 6:** Si `actual.isdigit()`, lee toda la secuencia con `_leer_secuencia_numerica` y la evalúa con `_clasificar_numero`. Registra `"VTE"`, `"VTD"` o `"VTF"`, o bien un error `"Léxico"` si devolvió `None`.
* **Bloque 7:** Si inicia con letra o `"_"`, extrae la palabra con `_leer_palabra` y verifica en orden:
  1. Si es `"main"` y `_es_firma_main` es `True` $\rightarrow$ registra `"PMAIN"` y cambia `ambito_actual = "main"`.
  2. Si está en `PALABRAS_RESERVADAS` $\rightarrow$ registra su token reservado.
  3. Si está en `IDS_BASE_JAVA` $\rightarrow$ registra token `"ID"` sin número de programador (`id_num=""`).
  4. Si `nivel_llaves == 1` y `_es_declaracion_metodo` es `True` $\rightarrow$ registra el nombre del método en `"global"` y cambia `ambito_actual = lexema`.
  5. En cualquier otro caso $\rightarrow$ llama a `_registrar_identificador`.
* **Bloque 8:** Si está en `SIMBOLOS_SIMPLES`, registra su token y avanza `i += 1`.
* **Bloque 9:** Cualquier carácter desconocido (ej. `@`, `#`, `$`) se registra en `errores` como `"Léxico"`.

#### 2. `_registrar_token_y_simbolo(lexema, tipo_token, linea, tokens, tabla_simbolos)`
Agrega un token estándar a `tokens` y una fila a `tabla_simbolos` con `id_num=""` (sin numeración de variable).

#### 3. `_registrar_identificador(lexema, linea, ambito_actual, tokens, tabla_simbolos, ids_por_ambito, contador_ids)`
Resuelve los **Incisos 3a y 3b** diferenciando variables globales y locales:
* Primero consulta `es_declaracion = _es_declaracion_variable(tokens)`.
* **En ámbito `"global"`:** Si el `lexema` no está en `mapa_global`, le asigna `contador_ids` (ej. `"1"`) y muestra su nombre real; si ya estaba, deja `id_num=""` y muestra `f"ID{num_id}"`.
* **Dentro de un método con `es_declaracion == True`:** Si la variable se está declarando con un tipo antes (ej. `int cantidad`), crea una entrada nueva en `mapa_local` con un nuevo `contador_ids`, aunque ya existiera otro `cantidad` en `"global"` o en otro método.
* **Dentro de un método con `es_declaracion == False` (uso de variable):** Busca primero en `mapa_local` y luego en `mapa_global`, reemplazando el lexema por su enlace `f"ID{num_id}"`.

#### 4. `_es_declaracion_variable(tokens_previos)`
Inspecciona el último token leído (`tokens_previos[-1]`) para saber si el `ID` actual está siendo declarado. Retorna `True` si el token previo es `"TD"`, `"STR"`, `"ID"` (como en `Tienda tienda`) o la secuencia `STR COA COC` (`String[]` en `main`).

#### 5. `_es_declaracion_metodo(tokens_previos, codigo, indice_post_id)`
Cuando `nivel_llaves == 1`, distingue entre un atributo global y un método comprobando si los dos tokens previos son `MA` + tipo (`TD`, `STR`, `TM` o `ID`) y el siguiente carácter no blanco después del nombre es `"("`.

#### 6. `_es_firma_main(tokens_previos, codigo, indice_post_main)`
Verifica que antes de `"main"` existan exactamente los tokens `"public"`, `"static"` y `"void"`, y después siga `"("`. Solo así se le asigna el token `PMAIN`.

#### 7. `_leer_cadena(codigo, inicio, delimitador)`
Recorre desde `inicio + 1` hasta encontrar el `delimitador` de cierre (`"` o `'`) en la misma línea, saltando caracteres escapados con `"\\"`. Retorna `(lexema_con_comillas, nuevo_indice, cerrado_correctamente)`.

#### 8. `_es_caracter_valido(lexema)`
Extrae el interior de las comillas simples (`contenido = lexema[1:-1]`) y verifica que mida exactamente 1 carácter (o 2 si inicia con `"\\"`).

#### 9. `_leer_secuencia_numerica(codigo, inicio)`
Lee todos los dígitos, puntos `.` y letras pegadas a partir de un número. **Importante:** Lee también letras para capturar errores léxicos completos como `"1variable"` y evitar que se separen en `1` (`VTE`) + `variable` (`ID`).

#### 10. `_clasificar_numero(lexema)`
Evalúa la cadena numérica:
* Si `lexema.isdigit()` es `True` $\rightarrow$ retorna `"VTE"`.
* Si no tiene punto `"."` $\rightarrow$ retorna `None` (atrapa `"1variable"` como error léxico).
* Divide con `lexema.split(".")`. Si `len(partes) != 2` $\rightarrow$ retorna `None` (atrapa `"3.14.16"`).
* Si la parte decimal termina en `"f"` o `"F"` y los caracteres previos son dígitos $\rightarrow$ retorna `"VTF"`.
* Si la parte decimal son solo dígitos $\rightarrow$ retorna `"VTD"`.

#### 11. `_leer_palabra(codigo, inicio)`
Avanza mientras los caracteres sean alfanuméricos o `"_"` y devuelve la palabra extraída junto con el nuevo índice.

---

## 5. Módulo `backend/parser.py`: Fases 2, 4, 5 y 6 (Sintáctico y Semántico)

### 5.1. El Patrón Maestro de las Funciones `_parse_...()`
Casi todos los métodos de instrucciones del parser aplican la misma estructura de 4 pasos:
```python
inicio: int = self.pos                      # 1. Posición donde inicia la sentencia
errores_previos: int = len(self.errores)    # 2. Conteo de errores antes de analizarla
# ... consumo de tokens según la GLC y validación de tipos ...
es_valida: bool = len(self.errores) == errores_previos  # 3. ¿Hubo errores nuevos?
self._registrar_instruccion(inicio, self.pos, "REGLA_GLC", es_valida)  # 4. Registro
```

---

### 5.2. Bloque 0: Constantes Semánticas y Función Puente
* **`JERARQUIA_ENTEROS = {"VTE": 0, "byte": 1, "short": 2, "char": 2, "int": 3, "long": 4}`:** Define el rango de almacenamiento de los tipos enteros. Una asignación entre enteros solo es válida si `rango_destino >= rango_origen` (por eso un `long` de rango 4 no cabe en un `int` de rango 3 sin casteo).
* **`TIPOS_ENTEROS` y `TIPOS_NUMERICOS`:** Conjuntos usados para validar operaciones aritméticas, relacionales y lógicas. Incluyen `"char"` porque los caracteres `VTC` pueden sumarse y restarse con enteros.
* **`analizar_sintactico_semantico(tokens, tabla_simbolos)`:** Instancia `AnalizadorSintacticoSemantico` y ejecuta `.ejecutar()`.

---

### 5.3. Bloque 1: Inicialización y Fase 2 (Métodos 1 a 3)
1. **`__init__(self, tokens, tabla_simbolos)`:** Inicializa el cursor `self.pos = 0`, las listas de salida, el diccionario de ámbitos `self.ambitos = {"global": {}}` y el registro de retornos `self.metodos = {}`.
2. **`ejecutar(self)`:** Llama primero a `_validar_estructura_principal()`. Si retorna `False`, vacía `self.tabla_simbolos` y `self.instrucciones_evaluadas` y termina de inmediato para cumplir el **Inciso 2**. Si retorna `True`, invoca `self._parse_java()`.
3. **`_validar_estructura_principal(self)`:** Verifica 5 requisitos obligatorios:
   * Que los primeros 3 tokens sean `package ID ;` (`PCK ID FI`).
   * Salta cualquier sentencia `import` (`IMP`).
   * Que siga el encabezado `public class ID {` (`MA CL ID LLA`).
   * Que exista la secuencia de 11 tokens `public static void main ( String [ ] ID ) {` (`MA ST TM PMAIN PA STR COA COC ID PC LLA`).
   * Que todas las llaves `{` (`LLA`) y `}` (`LLC`) estén balanceadas y cierren en `0`.

---

### 5.4. Bloque 2: Utilidades de Navegación y Recuperación (Métodos 4 a 14)
4. **`_actual(self)`:** Retorna `self.tokens[self.pos]` o `None` si llegó al final.
5. **`_mirar(self, desplazamiento)`:** Permite inspeccionar tokens hacia adelante (`self.pos + desplazamiento`) sin consumirlos (*lookahead*).
6. **`_fin(self)`:** Retorna `True` si `self.pos >= len(self.tokens)`.
7. **`_avanzar(self)`:** Incrementa `self.pos += 1` y retorna el token consumido.
8. **`_coincide(self, *tipos_esperados)`:** Retorna `True` si el token actual coincide con alguno de los tipos pasados como argumento.
9. **`_consumir(self, tipo_esperado)`:**
   * Si el token actual es `tipo_esperado`, avanza `self.pos += 1` y retorna `True`.
   * **Detección exacta de falta de `;` (`FI`):** Si `tipo_esperado == "FI"` y no se encontró, mira el token anterior (`self.tokens[self.pos - 1]`) y registra `ErrorCompilador(tok_previo.linea, ";", "Sintáctico")`. De esta forma reporta la línea donde faltó el `;` en lugar de culpar a la primera palabra de la línea siguiente.
10. **`_error_actual(self)`:** Registra un error `"Sintáctico"` en el token actual.
11. **`_agregar_error(self, linea, error, tipo)`:** Añade un `ErrorCompilador` a `self.errores`.
12. **`_sincronizar_hasta_fi(self)`:** Avanza hasta encontrar `;` (`FI`) o `}` (`LLC`), pero se detiene inmediatamente si ve que el cursor ya está en el inicio de una nueva sentencia (`TD`, `STR`, `PRIF`, `PRW`, `RTN`, `ID` en nueva línea, etc.) para no comerse la siguiente instrucción.
13. **`_sincronizar_en_cuerpo(self)`:** Avanza de forma segura cuando una instrucción dentro de un bloque no se reconoce.
14. **`_registrar_instruccion(self, indice_inicio, indice_fin, regla_glc, es_valida)`:** Reconstruye el texto de los tokens en el rango `[indice_inicio:indice_fin]` y agrega el objeto `Instruccion` a `self.instrucciones_evaluadas`.

---

### 5.5. Bloque 3: Reglas Estructurales de la GLC v7 (Métodos 15 a 25)
15. **`_parse_java(self)`:** Ejecuta `JAVA ::= DPACKAGE IMPORTS CLASE`.
16. **`_parse_dpackage(self)`:** Ejecuta `DPACKAGE ::= PCK ID FI`.
17. **`_parse_imports(self)`:** Ejecuta `IMPORT ::= IMP ID CA ID FI` (exige importación simple con un solo punto `.` según las consideraciones de la GLC v7).
18. **`_parse_clase(self)`:** Ejecuta `CLASE ::= MA CL ID LLA CONTENT LLC`.
19. **`_parse_content(self)`:** Ejecuta `VARIOS ::= MAIN | METODO | DECS_GLOB`. Usa `_mirar()` para distinguir `main`, rechazar miembros `static` fuera de `main` (prohibidos por la GLC v7), abrir métodos secundarios o procesar atributos globales.
20. **`_parse_main(self)`:** Cambia `self.ambito_actual = "main"`, consume la firma `MAIN`, registra `args` como `"String[]"` inicializado, ejecuta `_parse_cuerpo()` y restaura `self.ambito_actual = "global"`.
21. **`_parse_metodo(self)`:** Guarda el tipo de retorno en `self.metodos[nombre_metodo]`, abre el ámbito local del método, procesa `_parse_params()`, `_parse_cuerpo()` y `_parse_ree()`, y restaura el ámbito global.
22. **`_parse_params(self)`:** Procesa la lista de parámetros separados por coma (`CO`).
23. **`_parse_un_parametro(self)`:** Consume `TY ID` y registra el parámetro en el ámbito del método con `inicializada=True`.
24. **`_parse_ree(self, tipo_retorno, linea_metodo)`:** Evalúa `REE ::= RTN FI | RTN EXP FI | ε`. Verifica que un método `void` no retorne valores y que un método con tipo (`int`, `double`, etc.) tenga obligatoriamente un `return` con expresión compatible.
25. **`_parse_d_glob(self)`:** Procesa atributos de clase (`D_GLOB ::= MAO TY ID FI | MAO TY ID ODA EXP FI | OBJ`).

---

### 5.6. Bloque 4: Cuerpo e Instrucciones Simples (Métodos 26 a 32)
26. **`_parse_cuerpo(self)`:** Ejecuta un ciclo `while` llamando a `_parse_inst()` mientras no encuentre `}` (`LLC`), `return` (`RTN`), `case` (`CS`), `default` (`DF`) o `break` (`BR`).
27. **`_parse_inst(self)`:** Dirige el flujo a la regla correspondiente según el token inicial de la sentencia.
28. **`_parse_dec(self, inicio, es_global, consumir_fi)`:** Procesa declaraciones `DEC ::= TY ID FI | TY ID ODA EXP FI`. Si tiene `= EXP`, valida compatibilidad de tipos y marca `inicializada=True`. Si no tiene `=`, marca `inicializada=es_global` (las globales inician en `0` automáticamente; las locales quedan sin inicializar).
29. **`_parse_asig(self, inicio, consumir_fi)`:** Procesa `ASIG ::= ID ODA EXP FI`. Verifica que la variable haya sido declarada, valida la compatibilidad de tipos y marca `simbolo.inicializada = True`.
30. **`_parse_obj(self, inicio)`:** Procesa `OBJ ::= ID ID ODA NW ID PA ARGS PC FI` (ej. `Tienda tienda = new Tienda();`), verificando que la clase izquierda coincida con el constructor después de `new`.
31. **`_parse_acc_instruccion(self, inicio)`:** Procesa llamadas a método como instrucción (`System.out.println(precio);`) bajo la regla `ACC ::= CLA OT`.
32. **`_parse_inc_dec_instruccion(self, inicio, consumir_fi)`:** Procesa `i++;` o `++i;` bajo la regla `EXPU ::= OPU VAL`.

---

### 5.7. Bloque 5: Estructuras de Control (Métodos 33 a 37)
33. **`_parse_ifel(self)`:** Procesa `IFEL ::= PRIF PA EXPBOO PC LLA INST LLC CLOS`, exigiendo que la condición dentro del `if` evalúe a `"boolean"`. Soporta bloques `else` (`PRE`).
34. **`_parse_while(self)`:** Procesa `WHILE ::= PRW PA EXP PC STATMNT_B`, validando condición `"boolean"`.
35. **`_parse_do(self)`:** Procesa `DO ::= PRDO STATMNT_B PRW PA EXP PC FI`, validando condición `"boolean"`.
36. **`_parse_for(self)`:** Procesa las 3 secciones del encabezado del `for` (inicialización, condición booleana y paso) y su cuerpo entre llaves.
37. **`_parse_switch(self)`:** Procesa `SWITCH`, cada bloque `CASE` (verificando que el tipo del valor en `case` sea compatible con la variable del `switch`), el bloque `C_DEF` (`default:` / `deafult:`) y sus instrucciones `BREAK ::= BR FI`.

---

### 5.8. Bloque 6: Expresiones, Casteos y Accesos (Métodos 38 a 42)
38. **`_parse_exp(self)`:** Elimina la recursividad izquierda de `EXPC ::= EXP OP EXP` transformándola en la forma iterativa `TERMINO (OP TERMINO)*`. Retorna un `str` con el tipo resultante de la expresión.
39. **`_parse_termino(self)`:** Evalúa un operando individual:
    * **Casteo explícito `(TD) Termino`:** Si detecta `PA` + `TD` + `PC` (ej. `(int) decimal`), consume el casteo, verifica que el operando sea numérico y devuelve el tipo convertido.
    * **Agrupación `(EXP)`:** Evalúa la subexpresión entre paréntesis.
    * **Unarios prefijos (`!activo`, `-5`, `++i`):** Si es `!` (`OPN`), exige que el operando sea `"boolean"`.
    * **Accesos (`ACC`) o valores simples (`VAL`):** Llama a `_parse_acc()` o `_parse_val()`.
40. **`_parse_val(self)`:** Traduce cada literal a su tipo (`VTE` $\rightarrow$ `"VTE"`, `VTD` $\rightarrow$ `"double"`, `VTF` $\rightarrow$ `"float"`, `VTC` $\rightarrow$ `"char"`, `VTS` $\rightarrow$ `"String"`, `VTB` $\rightarrow$ `"boolean"`). Si es un `"ID"`, verifica que exista en el ámbito actual o global y que `simbolo.inicializada` sea `True`; de lo contrario, emite error `"Semántico"`.
41. **`_parse_acc(self, es_instruccion)`:** Procesa cadenas de acceso con punto `.` (`CA`) y llamadas con paréntesis `( ARGS )` como `texto.length()` o `System.out.println(precio)`.
42. **`_parse_args(self)`:** Evalúa la lista de argumentos separados por coma `,` (`CO`) dentro de una llamada a método o constructor.

---

### 5.9. Bloque 7: Métodos de Validación Semántica — Inciso 5 (Métodos 43 a 47)
43. **`_registrar_variable_semantica(self, nombre, tipo_dato, linea, inicializada)`:** Verifica si `nombre` ya existe en `self.ambitos[self.ambito_actual]`. Si ya existe, reporta error `"Semántico"` por redeclaración; si no, la guarda en el ámbito actual.
44. **`_buscar_variable_semantica(self, nombre)`:** Busca primero en el diccionario del método actual (`self.ambito_actual`) y, si no está, busca en `self.ambitos["global"]`.
45. **`_verificar_variable_numerica_usada(self, tok_id)`:** Comprueba que la variable usada con `++` o `--` haya sido declarada, esté inicializada y pertenezca a `TIPOS_NUMERICOS`.
46. **`_combinar_tipos_operacion(self, tipo_izq, tok_op, tipo_der)`:**
    * **Aritméticos (`OPA`):** Permite concatenar con `+` si hay un `"String"`. Si ambos son `TIPOS_NUMERICOS` (incluyendo `char` con `int`), promueve al tipo de mayor precisión (`double` > `float` > `long` > `int`).
    * **Relacionales (`OPR`):** `<`, `>`, `<=`, `>=` exigen que ambos sean `TIPOS_NUMERICOS` y devuelven `"boolean"`. `==` y `!=` permiten comparar numéricos entre sí o tipos idénticos y devuelven `"boolean"`.
    * **Lógicos (`OPL`, `XOR`):** Si ambos son `"boolean"`, devuelven `"boolean"`.
47. **`_validar_compatibilidad_tipos(self, tipo_destino, tipo_origen, linea, lexema_error)`:**
    * Si `tipo_destino == "float"` y `tipo_origen == "double"`, reporta error `"Semántico"` (un `VTD` de 64 bits sin sufijo `f` no cabe en un `float` de 32 bits).
    * Si ambos están en `JERARQUIA_ENTEROS`, exige que `JERARQUIA_ENTEROS[tipo_destino] >= JERARQUIA_ENTEROS[tipo_origen]` (impidiendo asignar un `long` a un `int` o un `int` a un `byte`/`short`).

---

## 6. Guía Rápida de Cambios Síncronos en Vivo (Inciso G de la Rúbrica)

Durante la revisión de 20 minutos, la docente puede pedirte realizar un cambio en vivo en el código:

1. **Agregar una nueva palabra reservada o cambiar el nombre de un token:**
   * **Dónde:** `backend/lexer.py` $\rightarrow$ diccionario `PALABRAS_RESERVADAS` (o `SIMBOLOS_SIMPLES` / `OPERADORES_DOBLES`).
2. **Agregar un método o clase nativa de Java para que no reciba número de ID:**
   * **Dónde:** `backend/lexer.py` $\rightarrow$ conjunto `IDS_BASE_JAVA`.
3. **Hacer que `package` sea opcional en vez de obligatorio:**
   * **Dónde:** `backend/parser.py` $\rightarrow$ en `_validar_estructura_principal()`, reemplazar el bloqueo del paso 1 por:
     ```python
     idx: int = 3 if (n >= 3 and self.tokens[0].tipo_token == "PCK") else 0
     ```
     Y en `_parse_dpackage()`, envolver el código dentro de `if self._coincide("PCK"):`.
4. **Prohibir que `char` (`VTC`) se sume con números enteros:**
   * **Dónde:** `backend/parser.py` $\rightarrow$ eliminar `"char"` de `JERARQUIA_ENTEROS`, `TIPOS_ENTEROS` y `TIPOS_NUMERICOS` al inicio del archivo.
5. **Cambiar el tiempo de respuesta de la Actualización Continua:**
   * **Dónde:** `ui_analizador.py` $\rightarrow$ método `_al_escribir_codigo()`, modificar el valor `300` en `self.after(300, self.ejecutar_analisis)`.