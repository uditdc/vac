#!/usr/bin/env python3
"""Vāc — a Sanskrit-principled programming language.

Lexer -> Pratt-ish recursive-descent parser -> tree-walking interpreter.
The distinctive feature is kāraka (case-role) argument marking: function
arguments carry a morphological suffix naming their semantic role, so calls
are order-independent and self-describing.
"""

import sys


# --------------------------------------------------------------------------- #
# Kāraka: the case-suffix table. Longest suffixes first so matching is greedy. #
# --------------------------------------------------------------------------- #
CASE_SUFFIXES = [
    ("ena", "karana"),       # instrumental  — "by means of"
    ("aya", "sampradana"),   # dative        — "to / for"
    ("sya", "sambandha"),    # genitive      — "of"
    ("at", "apadana"),       # ablative      — "from"
    ("m", "karma"),          # accusative    — direct object
    ("e", "adhikarana"),     # locative      — "in / at"
]

KEYWORDS = {
    "karya", "phala", "yadi", "anyatha", "athava", "yavat", "bhavati",
    "satya", "asatya", "sunya", "ca", "va", "na",
}

# Surface synonyms per canonical word — alternative Sanskrit forms (Devanagari
# and romanized) that all mean the same construct. Tokenizer-aware keyword
# selection (bench/keyword_select.py) picks whichever form is cheapest for a
# given tokenizer; every form here is accepted by the lexer, so the chosen
# dialect still runs. The canonical (first key) is the default romanized form.
SYNONYMS = {
    "bhavati": ["भव", "भवति", "अस्तु", "स्यात्", "astu", "syat"],
    "yavat":   ["यावत्", "यदा"],
    "yadi":    ["यदि", "चेत्", "cet"],
    "athava":  ["अथवा", "अथ", "atha"],
    "anyatha": ["अन्यथा"],
    "karya":   ["कार्य", "विधि", "क्रिया", "vidhi", "kriya"],
    "phala":   ["फल", "अर्पय", "arpaya"],
    "satya":   ["सत्य"],
    "asatya":  ["असत्य", "मिथ्या", "mithya"],
    "sunya":   ["शून्य", "रिक्त", "rikta"],
    "ca":      ["च"],
    "va":      ["वा"],
    "na":      ["न"],
    "vada":    ["वद", "ब्रूहि", "लिख", "bruhi", "likha"],
    "yoga":    ["योग", "संकलन"],
    "viyoga":  ["वियोग", "अन्तर", "antara"],
    "guna":    ["गुण", "गुणन"],
    "bhaga":   ["भाग", "हर", "hara"],
}
ALIASES = {surf: canon for canon, surfs in SYNONYMS.items() for surf in surfs}


def _is_word_start(c):
    return c.isalpha() or c == "_" or "ऀ" <= c <= "ॿ"


def _is_word_cont(c):
    return c.isalnum() or c == "_" or "ऀ" <= c <= "ॿ"


def split_case(word, names):
    """Split a fused word into (stem, case) using the longest case suffix whose
    stem is a known name. Returns (word, 'kartr') if nothing matches."""
    for suffix, case in CASE_SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix):
            stem = word[: -len(suffix)]
            if stem in names:
                return stem, case
    return word, "kartr"


# --------------------------------------------------------------------------- #
# Lexer                                                                        #
# --------------------------------------------------------------------------- #
class Token:
    __slots__ = ("kind", "value", "case", "line")

    def __init__(self, kind, value, line, case=None):
        self.kind = kind        # NUMBER STRING WORD OP PUNCT KW NEWLINE INDENT DEDENT EOF
        self.value = value
        self.case = case        # for literals/groups carrying a fused case suffix
        self.line = line

    def __repr__(self):
        return f"{self.kind}:{self.value!r}" + (f"<{self.case}>" if self.case else "")


OPERATORS = ["==", "!=", "<=", ">=", "+", "-", "*", "/", "%", "<", ">"]
PUNCT = set("()[]:,")


def lex(src):
    tokens = []
    indents = [0]
    lines = src.split("\n")
    for lineno, raw in enumerate(lines, 1):
        # strip comments (# to end of line, but not inside strings)
        line = _strip_comment(raw)
        stripped = line.strip()
        if not stripped:
            continue  # blank / comment-only line: no NEWLINE, no indent change

        indent = len(line) - len(line.lstrip(" "))
        if indent > indents[-1]:
            indents.append(indent)
            tokens.append(Token("INDENT", indent, lineno))
        while indent < indents[-1]:
            indents.pop()
            tokens.append(Token("DEDENT", indent, lineno))

        _lex_line(stripped, lineno, tokens)
        tokens.append(Token("NEWLINE", None, lineno))

    while len(indents) > 1:
        indents.pop()
        tokens.append(Token("DEDENT", 0, len(lines)))
    tokens.append(Token("EOF", None, len(lines)))
    return tokens


def _strip_comment(line):
    out, in_str, i = [], False, 0
    while i < len(line):
        c = line[i]
        if c == '"' and (i == 0 or line[i - 1] != "\\"):
            in_str = not in_str
        if c == "#" and not in_str:
            break
        out.append(c)
        i += 1
    return "".join(out)


def _lex_line(s, lineno, tokens):
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == " ":
            i += 1
            continue
        if c == '"':
            j, buf = i + 1, []
            while j < n and s[j] != '"':
                if s[j] == "\\" and j + 1 < n:
                    esc = s[j + 1]
                    buf.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(esc, esc))
                    j += 2
                    continue
                buf.append(s[j])
                j += 1
            j += 1  # closing quote
            i, case = _read_case(s, j)
            tokens.append(Token("STRING", "".join(buf), lineno, case))
            continue
        if c.isdigit():
            j = i
            while j < n and (s[j].isdigit() or s[j] == "."):
                j += 1
            num = float(s[i:j]) if "." in s[i:j] else int(s[i:j])
            i, case = _read_case(s, j)
            tokens.append(Token("NUMBER", num, lineno, case))
            continue
        if _is_word_start(c):
            j = i
            while j < n and _is_word_cont(s[j]):
                j += 1
            word = ALIASES.get(s[i:j], s[i:j])
            i = j
            kind = "KW" if word in KEYWORDS else "WORD"
            tokens.append(Token(kind, word, lineno))
            continue
        two = s[i : i + 2]
        if two in OPERATORS:
            tokens.append(Token("OP", two, lineno))
            i += 2
            continue
        if c in OPERATORS:
            tokens.append(Token("OP", c, lineno))
            i += 1
            continue
        if c in PUNCT:
            # a case suffix may be fused to a closing ) or ]
            if c in ")]":
                i2, case = _read_case(s, i + 1)
                tokens.append(Token("PUNCT", c, lineno, case))
                i = i2
                continue
            tokens.append(Token("PUNCT", c, lineno))
            i += 1
            continue
        raise VacError(f"unexpected character {c!r}", lineno)
    return i


def _read_case(s, j):
    """At position j (just after a literal/group), greedily read a fused case
    suffix if the following run of letters exactly matches a known suffix."""
    n = j
    while n < len(s) and (s[n].isalnum() or s[n] == "_"):
        n += 1
    run = s[j:n]
    for suffix, case in CASE_SUFFIXES:
        if run == suffix:
            return n, case
    return j, None  # not a case suffix — leave it for the next token


# --------------------------------------------------------------------------- #
# AST                                                                          #
# --------------------------------------------------------------------------- #
class Node:
    pass


class Num(Node):
    def __init__(self, v, case): self.v, self.case = v, case
class Str(Node):
    def __init__(self, v, case): self.v, self.case = v, case
class Lit(Node):
    def __init__(self, v): self.v = v               # satya/asatya/sunya
class Var(Node):
    def __init__(self, name): self.name = name      # case resolved at eval
class Group(Node):
    def __init__(self, expr, case): self.expr, self.case = expr, case
class BinOp(Node):
    def __init__(self, op, l, r): self.op, self.l, self.r = op, l, r
class UnOp(Node):
    def __init__(self, op, e): self.op, self.e = op, e
class Clause(Node):                                  # [ args... verb ]
    def __init__(self, verb, args, case): self.verb, self.args, self.case = verb, args, case
class Bind(Node):
    def __init__(self, name, expr): self.name, self.expr = name, expr
class If(Node):
    def __init__(self, cond, then, els): self.cond, self.then, self.els = cond, then, els
class While(Node):
    def __init__(self, cond, body): self.cond, self.body = cond, body
class Func(Node):
    def __init__(self, name, params, body): self.name, self.params, self.body = name, params, body
class Return(Node):
    def __init__(self, expr): self.expr = expr
class ExprStmt(Node):
    def __init__(self, expr): self.expr = expr


# --------------------------------------------------------------------------- #
# Parser                                                                       #
# --------------------------------------------------------------------------- #
class VacError(Exception):
    def __init__(self, msg, line=None):
        super().__init__(msg)
        self.line = line


class Parser:
    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0

    def peek(self):
        return self.toks[self.i]

    def next(self):
        t = self.toks[self.i]
        self.i += 1
        return t

    def accept(self, kind, value=None):
        t = self.peek()
        if t.kind == kind and (value is None or t.value == value):
            return self.next()
        return None

    def expect(self, kind, value=None):
        t = self.accept(kind, value)
        if not t:
            p = self.peek()
            want = value or kind
            raise VacError(f"expected {want}, got {p.kind} {p.value!r}", p.line)
        return t

    def skip_newlines(self):
        while self.peek().kind == "NEWLINE":
            self.next()

    # -- program / blocks --------------------------------------------------- #
    def parse(self):
        stmts = []
        self.skip_newlines()
        while self.peek().kind != "EOF":
            stmts.append(self.statement())
            self.skip_newlines()
        return stmts

    def block(self):
        self.expect("PUNCT", ":")
        self.expect("NEWLINE")
        self.skip_newlines()
        self.expect("INDENT")
        stmts = []
        self.skip_newlines()
        while self.peek().kind not in ("DEDENT", "EOF"):
            stmts.append(self.statement())
            self.skip_newlines()
        self.accept("DEDENT")
        return stmts

    # -- statements --------------------------------------------------------- #
    def statement(self):
        t = self.peek()
        if t.kind == "KW":
            if t.value == "karya":
                return self.func_def()
            if t.value == "phala":
                self.next()
                return Return(self.rhs())
            if t.value == "yadi":
                return self.if_stmt()
            if t.value == "yavat":
                self.next()
                cond = self.expr()
                return While(cond, self.block())
        # binding:  NAME bhavati rhs
        if t.kind == "WORD" and self.toks[self.i + 1].kind == "KW" \
                and self.toks[self.i + 1].value == "bhavati":
            name = self.next().value
            self.next()  # bhavati
            return Bind(name, self.rhs())
        return ExprStmt(self.rhs())

    def at_expr_end(self):
        t = self.peek()
        return t.kind in ("NEWLINE", "DEDENT", "EOF") or \
            (t.kind == "PUNCT" and t.value in (":", ")", "]"))

    def rhs(self):
        """An expression that, if followed by further atoms before the line
        ends, is a bracket-free verb-final clause: `arg arg … verb`. A call
        embedded *inside* arithmetic must still use [ ] — caught here."""
        first = self.expr()
        if self.at_expr_end():
            return first
        if isinstance(first, (BinOp, UnOp)):
            raise VacError("embed a call with [ ] inside an arithmetic expression",
                           self.peek().line)
        atoms = [first]
        while not self.at_expr_end():
            atoms.append(self.primary())
        if not isinstance(atoms[-1], Var):
            raise VacError("clause must end with a verb (function name)",
                           self.peek().line)
        verb_kind = atoms[-1]
        return Clause(verb_kind.name, atoms[:-1], None)

    def func_def(self):
        self.expect("KW", "karya")
        name = self.expect("WORD").value
        self.expect("PUNCT", "(")
        params = []
        if not self.accept("PUNCT", ")"):
            params.append(self.expect("WORD").value)
            while self.accept("PUNCT", ","):
                params.append(self.expect("WORD").value)
            self.expect("PUNCT", ")")
        return Func(name, params, self.block())

    def if_stmt(self):
        self.expect("KW", "yadi")
        cond = self.expr()
        then = self.block()
        els = None
        self.skip_newlines()
        nxt = self.peek()
        if nxt.kind == "KW" and nxt.value == "athava":
            self.next()
            els = [self._chained_if()]
        elif nxt.kind == "KW" and nxt.value == "anyatha":
            self.next()
            els = self.block()
        return If(cond, then, els)

    def _chained_if(self):
        """`athava` (elif): cond + block, with its own trailing athava/anyatha."""
        cond = self.expr()
        then = self.block()
        els = None
        self.skip_newlines()
        nxt = self.peek()
        if nxt.kind == "KW" and nxt.value == "athava":
            self.next()
            els = [self._chained_if()]
        elif nxt.kind == "KW" and nxt.value == "anyatha":
            self.next()
            els = self.block()
        return If(cond, then, els)

    # -- expressions (precedence climbing) ---------------------------------- #
    def expr(self):
        return self.or_expr()

    def or_expr(self):
        node = self.and_expr()
        while self.peek().kind == "KW" and self.peek().value == "va":
            self.next()
            node = BinOp("va", node, self.and_expr())
        return node

    def and_expr(self):
        node = self.not_expr()
        while self.peek().kind == "KW" and self.peek().value == "ca":
            self.next()
            node = BinOp("ca", node, self.not_expr())
        return node

    def not_expr(self):
        if self.peek().kind == "KW" and self.peek().value == "na":
            self.next()
            return UnOp("na", self.not_expr())
        return self.cmp()

    def cmp(self):
        node = self.add()
        while self.peek().kind == "OP" and self.peek().value in ("==", "!=", "<", ">", "<=", ">="):
            op = self.next().value
            node = BinOp(op, node, self.add())
        return node

    def add(self):
        node = self.mul()
        while self.peek().kind == "OP" and self.peek().value in ("+", "-"):
            op = self.next().value
            node = BinOp(op, node, self.mul())
        return node

    def mul(self):
        node = self.unary()
        while self.peek().kind == "OP" and self.peek().value in ("*", "/", "%"):
            op = self.next().value
            node = BinOp(op, node, self.unary())
        return node

    def unary(self):
        if self.peek().kind == "OP" and self.peek().value == "-":
            self.next()
            return UnOp("-", self.unary())
        return self.primary()

    def primary(self):
        t = self.peek()
        if t.kind == "NUMBER":
            self.next()
            return Num(t.value, t.case)
        if t.kind == "STRING":
            self.next()
            return Str(t.value, t.case)
        if t.kind == "KW" and t.value in ("satya", "asatya", "sunya"):
            self.next()
            return Lit({"satya": True, "asatya": False, "sunya": None}[t.value])
        if t.kind == "WORD":
            self.next()
            return Var(t.value)
        if t.kind == "PUNCT" and t.value == "(":
            self.next()
            e = self.expr()
            close = self.expect("PUNCT", ")")
            return Group(e, close.case)
        if t.kind == "PUNCT" and t.value == "[":
            return self.clause()
        raise VacError(f"unexpected {t.kind} {t.value!r} in expression", t.line)

    def clause(self):
        """[ operand* verb ] — verb-final call. Operands are atoms (each may
        carry a fused case suffix); the final token is the verb (a function
        name WORD or a builtin verb keyword such as `vada`)."""
        self.expect("PUNCT", "[")
        args, verb = [], None
        while not (self.peek().kind == "PUNCT" and self.peek().value == "]"):
            t = self.peek()
            nxt = self.toks[self.i + 1]
            if t.kind in ("WORD", "KW") and nxt.kind == "PUNCT" and nxt.value == "]":
                verb = self.next().value
                break
            args.append(self.primary())
        close = self.expect("PUNCT", "]")
        if verb is None:
            raise VacError("clause must end with a verb (function name)", close.line)
        return Clause(verb, args, close.case)


# --------------------------------------------------------------------------- #
# Interpreter                                                                  #
# --------------------------------------------------------------------------- #
class ReturnSignal(Exception):
    def __init__(self, value): self.value = value


def _param_split(p):
    for suffix, case in CASE_SUFFIXES:
        if p.endswith(suffix) and len(p) > len(suffix):
            return (p[: -len(suffix)], case)
    return (p, "kartr")


class Interpreter:
    def __init__(self):
        self.globals = {}
        self.funcs = {}
        self.builtins = {"vada", "yoga", "viyoga", "guna", "bhaga"}

    def run(self, stmts):
        for s in stmts:
            if isinstance(s, Func):
                self.funcs[s.name] = s
        for s in stmts:
            if not isinstance(s, Func):
                self.exec(s, self.globals)

    # -- statements --------------------------------------------------------- #
    def exec(self, node, scope):
        if isinstance(node, Bind):
            scope[node.name] = self.eval(node.expr, scope)
        elif isinstance(node, ExprStmt):
            self.eval(node.expr, scope)
        elif isinstance(node, If):
            if truthy(self.eval(node.cond, scope)):
                self.exec_block(node.then, scope)
            elif node.els is not None:
                self.exec_block(node.els, scope)
        elif isinstance(node, While):
            while truthy(self.eval(node.cond, scope)):
                self.exec_block(node.body, scope)
        elif isinstance(node, Return):
            raise ReturnSignal(self.eval(node.expr, scope))
        elif isinstance(node, Func):
            self.funcs[node.name] = node
        else:
            raise VacError(f"cannot execute {type(node).__name__}")

    def exec_block(self, stmts, scope):
        for s in stmts:
            self.exec(s, scope)

    # -- expressions -------------------------------------------------------- #
    def eval(self, node, scope):
        if isinstance(node, (Num, Str)):
            return node.v
        if isinstance(node, Lit):
            return node.v
        if isinstance(node, Group):
            return self.eval(node.expr, scope)
        if isinstance(node, Var):
            stem, _ = split_case(node.name, scope)
            target = stem if stem in scope else node.name
            if target in scope:
                return scope[target]
            if node.name in scope:
                return scope[node.name]
            raise VacError(f"undefined name {node.name!r}")
        if isinstance(node, UnOp):
            v = self.eval(node.e, scope)
            return (not truthy(v)) if node.op == "na" else -v
        if isinstance(node, BinOp):
            return self.binop(node, scope)
        if isinstance(node, Clause):
            return self.call(node, scope)
        raise VacError(f"cannot evaluate {type(node).__name__}")

    def binop(self, node, scope):
        op = node.op
        if op == "ca":
            return truthy(self.eval(node.l, scope)) and truthy(self.eval(node.r, scope))
        if op == "va":
            return truthy(self.eval(node.l, scope)) or truthy(self.eval(node.r, scope))
        a, b = self.eval(node.l, scope), self.eval(node.r, scope)
        return {
            "+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b,
            "/": lambda: a / b, "%": lambda: a % b,
            "==": lambda: a == b, "!=": lambda: a != b,
            "<": lambda: a < b, ">": lambda: a > b,
            "<=": lambda: a <= b, ">=": lambda: a >= b,
        }[op]()

    # -- kāraka call: bind args to params by case role ---------------------- #
    def call(self, node, scope):
        args = []  # list of (case, value)
        for a in node.args:
            case = self.operand_case(a, scope)
            args.append((case, self.eval(a, scope)))

        if node.verb in self.builtins:
            return self.builtin(node.verb, args)

        fn = self.funcs.get(node.verb)
        if fn is None:
            raise VacError(f"unknown verb (function) {node.verb!r}")

        local = {}
        pool = list(args)
        for stem, case in (_param_split(p) for p in fn.params):
            match = next((i for i, (c, _) in enumerate(pool) if c == case), None)
            if match is None:
                match = next((i for i, (c, _) in enumerate(pool) if c == "kartr"), None)
            if match is None:
                raise VacError(f"call to {node.verb!r}: no argument for role {case} ({stem})")
            local[stem] = pool.pop(match)[1]
        try:
            self.exec_block(fn.body, local)
        except ReturnSignal as r:
            return r.value
        return None

    def operand_case(self, node, scope):
        if isinstance(node, (Num, Str, Group)):
            return node.case or "kartr"
        if isinstance(node, Var):
            _, case = split_case(node.name, scope)
            return case
        if isinstance(node, Clause):
            return node.case or "kartr"
        return "kartr"

    def builtin(self, name, args):
        vals = [v for _, v in args]
        if name == "vada":
            print(" ".join(vac_str(v) for v in vals))
            return None
        if name == "yoga":   # add (commutative): both karma
            return vals[0] + vals[1]
        if name == "guna":   # multiply (commutative)
            return vals[0] * vals[1]
        if name == "viyoga":  # subtract: karma - karana
            return _role(args, "karma") - _role(args, "karana")
        if name == "bhaga":   # divide: karma / karana
            return _role(args, "karma") / _role(args, "karana")
        raise VacError(f"unknown builtin {name!r}")


def _role(args, case):
    for c, v in args:
        if c == case:
            return v
    raise VacError(f"missing role {case}")


def truthy(v):
    return bool(v)


def vac_str(v):
    if v is True:
        return "satya"
    if v is False:
        return "asatya"
    if v is None:
        return "sunya"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


# --------------------------------------------------------------------------- #
# Entry point                                                                  #
# --------------------------------------------------------------------------- #
def run_source(src):
    tokens = lex(src)
    ast = Parser(tokens).parse()
    Interpreter().run(ast)


def main(argv):
    if len(argv) >= 2 and argv[1] == "-c":
        src = argv[2]
    elif len(argv) >= 2:
        with open(argv[1], encoding="utf-8") as f:
            src = f.read()
    else:
        print("usage: vac.py <file.vac> | vac.py -c <code>", file=sys.stderr)
        return 1
    try:
        run_source(src)
    except VacError as e:
        loc = f" (line {e.line})" if e.line else ""
        print(f"vāc error{loc}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
