import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import re

# ==========================================
# 1. MODELO (TOKEN Y ERRORES)
# ==========================================

class TokenType:
    # Palabras Clave [cite: 46]
    IF = 'IF'
    ELSE = 'ELSE'
    WHILE = 'WHILE'
    INT = 'INT'
    FLOAT = 'FLOAT'
    STRING = 'STRING'
    BOOL = 'BOOL'
    VOID = 'VOID'
    RETURN = 'RETURN'
    TRUE = 'TRUE'
    FALSE = 'FALSE'
    READ = 'READ'
    WRITE = 'WRITE'
    
    # Literales e Identificadores [cite: 39]
    ID = 'ID'
    NUMBER_INT = 'NUMBER_INT'
    NUMBER_FLOAT = 'NUMBER_FLOAT'
    STRING_LITERAL = 'STRING_LITERAL'
    
    # Operadores y Símbolos [cite: 48]
    PLUS = '+'
    MINUS = '-'
    MULTIPLY = '*'
    DIVIDE = '/'
    MODULO = '%'
    GT = '>'
    LT = '<'
    GTE = '>='
    LTE = '<='
    EQUAL = '=='
    NOT_EQUAL = '!='
    ASSIGN = '='
    LPAREN = '('
    RPAREN = ')'
    LBRACE = '{'
    RBRACE = '}'
    COLON = ':'
    COMMA = ','
    SEMICOLON = ';'
    
    # Control [cite: 19, 18]
    NEWLINE = 'NEWLINE'
    INDENT = 'INDENT'
    DEDENT = 'DEDENT'
    EOF = 'EOF'
    UNKNOWN = 'UNKNOWN'

class Token:
    def __init__(self, type_, value, line, col_start, col_end):
        self.type = type_
        self.value = value
        self.line = line
        self.col_start = col_start
        self.col_end = col_end

    def __str__(self):
        # Formato para el archivo .out 
        return f"Line: {self.line}, Col: {self.col_start}-{self.col_end}, Type: {self.type}, Value: {self.value}"

class LexicalError:
    def __init__(self, line, col, message):
        self.line = line
        self.col = col
        self.message = message

    def __str__(self):
        # Formato de error [cite: 73]
        return f"Line {self.line}, col {self.col}: ERROR {self.message}"

# ==========================================
# 2. LÓGICA DEL SCANNER (LEXER)
# ==========================================

class Scanner:
    def __init__(self, source_code):
        self.source = source_code.replace('\r\n', '\n') + '\n' # Asegurar terminación
        self.length = len(self.source)
        self.pos = 0
        self.line = 1
        self.col = 1
        
        # Pila de indentación [cite: 19, 56]
        self.indent_stack = [0] 
        
        self.tokens = []
        self.errors = []
        
        self.keywords = {
            "if": TokenType.IF, "else": TokenType.ELSE, "while": TokenType.WHILE,
            "int": TokenType.INT, "float": TokenType.FLOAT, "string": TokenType.STRING,
            "bool": TokenType.BOOL, "void": TokenType.VOID, "return": TokenType.RETURN,
            "true": TokenType.TRUE, "false": TokenType.FALSE, "read": TokenType.READ,
            "write": TokenType.WRITE
        }

    def scan(self):
        at_line_start = True # Bandera para verificar indentación al inicio de línea

        while self.pos < self.length:
            char = self.source[self.pos]

            # 1. MANEJO DE INDENTACIÓN (Solo al inicio de línea) 
            if at_line_start:
                # Ignorar líneas vacías o comentarios puros
                if char == '\n':
                    self.pos += 1
                    self.line += 1
                    self.col = 1
                    continue
                if char == '#': # Comentarios [cite: 63]
                    self.skip_comment()
                    continue
                if char.isspace():
                    spaces = self.count_indentation()
                    # Verificar si la línea tiene contenido real
                    if self.pos < self.length and self.source[self.pos] not in ['\n', '#']:
                        self.handle_indentation(spaces)
                        at_line_start = False
                    continue
                else:
                    # Nivel 0 de indentación
                    self.handle_indentation(0)
                    at_line_start = False
            
            # 2. ESPACIOS (No al inicio)
            if char.isspace():
                if char == '\n':
                    # Emitir NEWLINE si hubo contenido [cite: 65]
                    self.tokens.append(Token(TokenType.NEWLINE, "\\n", self.line, self.col, self.col))
                    self.pos += 1
                    self.line += 1
                    self.col = 1
                    at_line_start = True
                else:
                    self.pos += 1
                    self.col += 1
                continue

            # 3. COMENTARIOS (En medio de línea)
            if char == '#':
                self.skip_comment()
                continue # El \n lo procesará la siguiente iteración

            # 4. IDENTIFICADORES Y PALABRAS CLAVE
            if char.isalpha() or char == '_':
                self.scan_id()
                continue

            # 5. NÚMEROS (Int y Float) [cite: 41]
            if char.isdigit():
                self.scan_number()
                continue

            # 6. STRINGS [cite: 43]
            if char == '"':
                self.scan_string()
                continue

            # 7. OPERADORES Y SIMBOLOS [cite: 48]
            if self.scan_operator(char):
                continue

            # ERROR: Carácter desconocido [cite: 68]
            self.errors.append(LexicalError(self.line, self.col, f"Carácter inesperado '{char}'"))
            self.pos += 1
            self.col += 1

        # AL FINAL DEL ARCHIVO (EOF): Cerrar bloques pendientes [cite: 20]
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token(TokenType.DEDENT, "DEDENT", self.line, self.col, self.col))
        
        self.tokens.append(Token(TokenType.EOF, "EOF", self.line, self.col, self.col))
        return self.tokens, self.errors

    def count_indentation(self):
        count = 0
        temp_pos = self.pos
        # Calcular espacios (Tabs = 4 espacios) 
        while temp_pos < self.length and self.source[temp_pos] in [' ', '\t']:
            if self.source[temp_pos] == '\t':
                count += 4
            else:
                count += 1
            temp_pos += 1
        
        # Ajustar posición real
        chars_consumed = temp_pos - self.pos
        self.pos = temp_pos
        self.col += chars_consumed
        return count

    def handle_indentation(self, spaces):
        current_level = self.indent_stack[-1]
        
        if spaces > current_level:
            # Aumenta nivel -> INDENT [cite: 57]
            self.indent_stack.append(spaces)
            self.tokens.append(Token(TokenType.INDENT, "INDENT", self.line, 1, spaces))
        
        elif spaces < current_level:
            # Disminuye nivel -> DEDENT(s) [cite: 58]
            while spaces < self.indent_stack[-1]:
                self.indent_stack.pop()
                self.tokens.append(Token(TokenType.DEDENT, "DEDENT", self.line, 1, spaces))
                if len(self.indent_stack) == 0: # Seguridad
                    self.indent_stack.append(0)
                    break
            
            # Error de Indentación 
            if self.indent_stack[-1] != spaces:
                self.errors.append(LexicalError(self.line, 1, "Indentación inválida (no coincide con niveles previos)"))
                # Sincronización simple: ignorar y continuar con el nivel actual

    def skip_comment(self):
        # Ignorar hasta el salto de línea [cite: 63]
        while self.pos < self.length and self.source[self.pos] != '\n':
            self.pos += 1
            # Nota: No avanzamos self.col porque el comentario se ignora visualmente para el parser

    def scan_id(self):
        start_col = self.col
        start_pos = self.pos
        while self.pos < self.length and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            self.pos += 1
            self.col += 1
        
        lexeme = self.source[start_pos:self.pos]
        
        # Validación longitud máxima 31 [cite: 40, 71]
        if len(lexeme) > 31:
            self.errors.append(LexicalError(self.line, start_col, "Identificador excede 31 caracteres (truncado)"))
            lexeme = lexeme[:31] # Truncar [cite: 72]

        token_type = self.keywords.get(lexeme, TokenType.ID)
        self.tokens.append(Token(token_type, lexeme, self.line, start_col, self.col - 1))

    def scan_number(self):
        start_col = self.col
        start_pos = self.pos
        is_float = False
        
        while self.pos < self.length and self.source[self.pos].isdigit():
            self.pos += 1
            self.col += 1
            
        if self.pos < self.length and self.source[self.pos] == '.':
            is_float = True
            self.pos += 1
            self.col += 1
            # Parte decimal
            if self.pos >= self.length or not self.source[self.pos].isdigit():
                 self.errors.append(LexicalError(self.line, self.col, "Número flotante mal formado"))
            while self.pos < self.length and self.source[self.pos].isdigit():
                self.pos += 1
                self.col += 1
        
        lexeme = self.source[start_pos:self.pos]
        self.tokens.append(Token(TokenType.NUMBER_FLOAT if is_float else TokenType.NUMBER_INT, lexeme, self.line, start_col, self.col - 1))

    def scan_string(self):
        start_col = self.col
        self.pos += 1; self.col += 1 # Comilla inicial
        start_content = self.pos
        
        while self.pos < self.length and self.source[self.pos] != '"' and self.source[self.pos] != '\n':
            self.pos += 1
            self.col += 1
            
        if self.pos >= self.length or self.source[self.pos] == '\n':
            # Error: String sin cerrar 
            self.errors.append(LexicalError(self.line, start_col, "Cadena sin cerrar antes de fin de línea"))
            lexeme = self.source[start_content:self.pos]
            self.tokens.append(Token(TokenType.STRING_LITERAL, lexeme, self.line, start_col, self.col - 1))
            return

        lexeme = self.source[start_content:self.pos]
        self.pos += 1; self.col += 1 # Comilla cierre
        self.tokens.append(Token(TokenType.STRING_LITERAL, lexeme, self.line, start_col, self.col - 1))

    def scan_operator(self, char):
        start_col = self.col
        next_char = self.source[self.pos + 1] if self.pos + 1 < self.length else ''
        
        # Mapeo de operadores simples y dobles
        doubles = {
            '>=': TokenType.GTE, '<=': TokenType.LTE, 
            '==': TokenType.EQUAL, '!=': TokenType.NOT_EQUAL
        }
        singles = {
            '+': TokenType.PLUS, '-': TokenType.MINUS, '*': TokenType.MULTIPLY, '/': TokenType.DIVIDE,
            '%': TokenType.MODULO, '(': TokenType.LPAREN, ')': TokenType.RPAREN, '{': TokenType.LBRACE,
            '}': TokenType.RBRACE, ';': TokenType.SEMICOLON, ',': TokenType.COMMA, ':': TokenType.COLON,
            '>': TokenType.GT, '<': TokenType.LT, '=': TokenType.ASSIGN
        }

        # Intentar match doble primero
        combo = char + next_char
        if combo in doubles:
            self.tokens.append(Token(doubles[combo], combo, self.line, start_col, start_col + 1))
            self.pos += 2
            self.col += 2
            return True
        
        # Intentar match simple
        if char in singles:
            self.tokens.append(Token(singles[char], char, self.line, start_col, start_col))
            self.pos += 1
            self.col += 1
            return True
            
        return False

# ==========================================
# 3. INTERFAZ GRÁFICA (GUI)
# ==========================================

class MiniLangGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MiniLang Compiler 2026 - Fase 1 (Python)")
        self.root.geometry("1100x700")
        
        # --- Estilos ---
        style = ttk.Style()
        style.configure("Treeview", font=('Consolas', 10))
        style.configure("TButton", font=('Segoe UI', 10))

        # --- Layout Principal ---
        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Botones Superiores ---
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_load = tk.Button(btn_frame, text="📂 Cargar Archivo .ming", command=self.load_file, bg="#e1e1e1")
        self.btn_load.pack(side=tk.LEFT, padx=5)
        
        self.btn_run = tk.Button(btn_frame, text="▶ ANALIZAR CÓDIGO", command=self.run_analysis, bg="#90ee90", font=('Segoe UI', 10, 'bold'))
        self.btn_run.pack(side=tk.LEFT, padx=5)

        # --- Paneles Divididos (Split) ---
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # 1. Panel Izquierdo: Editor de Código
        left_frame = tk.LabelFrame(paned_window, text="Código Fuente (Entrada)", font=('Segoe UI', 10, 'bold'))
        self.txt_input = scrolledtext.ScrolledText(left_frame, font=('Consolas', 11), undo=True)
        self.txt_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        paned_window.add(left_frame, weight=1)

        # 2. Panel Derecho: Tabla de Tokens
        right_frame = tk.LabelFrame(paned_window, text="Tabla de Tokens (Salida)", font=('Segoe UI', 10, 'bold'))
        
        columns = ("line", "col", "type", "val")
        self.tree = ttk.Treeview(right_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("line", text="Línea")
        self.tree.heading("col", text="Columna")
        self.tree.heading("type", text="Tipo Token")
        self.tree.heading("val", text="Valor/Lexema")
        
        self.tree.column("line", width=50, anchor=tk.CENTER)
        self.tree.column("col", width=80, anchor=tk.CENTER)
        self.tree.column("type", width=120)
        self.tree.column("val", width=150)
        
        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        paned_window.add(right_frame, weight=1)

        # --- Panel Inferior: Errores ---
        error_frame = tk.LabelFrame(main_frame, text="Consola de Errores", font=('Segoe UI', 10, 'bold'), fg="red")
        error_frame.pack(fill=tk.X, pady=(10, 0), ipady=5)
        
        self.txt_errors = tk.Text(error_frame, height=6, font=('Consolas', 10), bg="#fff0f0", fg="#cc0000")
        self.txt_errors.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("MiniLang Files", "*.mlng"), ("Text Files", "*.txt")])
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.txt_input.delete(1.0, tk.END)
                self.txt_input.insert(tk.END, content)
            self.root.title(f"MiniLang Compiler - {file_path}")

    def run_analysis(self):
        # Limpiar GUI
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.txt_errors.config(state=tk.NORMAL)
        self.txt_errors.delete(1.0, tk.END)

        # Obtener código
        source = self.txt_input.get(1.0, tk.END)
        
        # Ejecutar Scanner
        scanner = Scanner(source)
        tokens, errors = scanner.scan()

        # Mostrar Tokens en GUI
        for t in tokens:
            self.tree.insert("", tk.END, values=(t.line, f"{t.col_start}-{t.col_end}", t.type, t.value))

        # Mostrar Errores en GUI [cite: 83]
        if errors:
            self.txt_errors.insert(tk.END, f"Se encontraron {len(errors)} errores léxicos:\n")
            for err in errors:
                self.txt_errors.insert(tk.END, str(err) + "\n")
        else:
            self.txt_errors.config(fg="green")
            self.txt_errors.insert(tk.END, "✅ Análisis exitoso. No se encontraron errores léxicos.")
            self.txt_errors.config(fg="red") # Resetear color para el futuro

        # Generar archivo de salida .out 
        try:
            with open("salida.out", "w", encoding='utf-8') as f:
                for t in tokens:
                    f.write(str(t) + "\n")
            messagebox.showinfo("Éxito", "Archivo 'salida.out' generado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el archivo de salida: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MiniLangGUI(root)

    root.mainloop()
