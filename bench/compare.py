#!/usr/bin/env python3
"""Token-count comparison: Vāc vs Python for equivalent programs.

Counts tokens with tiktoken (cl100k_base, the GPT-4 family encoding) when
available, otherwise a whitespace/punctuation approximation. The point is the
*relative* difference between equivalent programs, not absolute accuracy.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VAC_DIR = os.path.join(HERE, "..", "examples")
PY_DIR = os.path.join(HERE, "py")
PAIRS = ["hello", "factorial", "fibonacci", "gcd", "fizzbuzz", "pricing"]

try:
    import tiktoken

    _enc = tiktoken.get_encoding("cl100k_base")
    def count(text):
        return len(_enc.encode(text))
    METHOD = "tiktoken/cl100k_base"
except Exception:  # pragma: no cover
    import re
    def count(text):
        return len(re.findall(r"\w+|[^\w\s]", text))
    METHOD = "regex approximation (tiktoken not installed)"


sys.path.insert(0, os.path.join(HERE, ".."))


def lexemes_vac(src):
    """Structural token count: each Vāc lexeme = 1 (kāraka suffix is free)."""
    import vac
    skip = {"NEWLINE", "INDENT", "DEDENT", "EOF"}
    return sum(1 for t in vac.lex(src) if t.kind not in skip)


def lexemes_py(src):
    """Structural token count via Python's own tokenizer."""
    import io
    import tokenize
    skip = {tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT,
            tokenize.ENCODING, tokenize.ENDMARKER, tokenize.COMMENT}
    n = 0
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type not in skip and tok.string != "":
            n += 1
    return n


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def strip_comments_vac(src):
    out = []
    for line in src.split("\n"):
        s, in_str = [], False
        for i, c in enumerate(line):
            if c == '"' and (i == 0 or line[i - 1] != "\\"):
                in_str = not in_str
            if c == "#" and not in_str:
                break
            s.append(c)
        if "".join(s).strip():
            out.append("".join(s).rstrip())
    return "\n".join(out)


def strip_comments_py(src):
    out = []
    for line in src.split("\n"):
        s, in_str = [], False
        for i, c in enumerate(line):
            if c == '"' and (i == 0 or line[i - 1] != "\\"):
                in_str = not in_str
            if c == "#" and not in_str:
                break
            s.append(c)
        if "".join(s).strip():
            out.append("".join(s).rstrip())
    return "\n".join(out)


def _table(title, count_vac, count_py):
    print(title)
    header = f"{'program':<12}{'Vāc':>8}{'Python':>9}{'Δ':>7}{'ratio':>9}"
    print(header)
    print("-" * len(header))
    tv = tp = 0
    for name in PAIRS:
        vac = strip_comments_vac(read(os.path.join(VAC_DIR, f"{name}.vac")))
        py = strip_comments_py(read(os.path.join(PY_DIR, f"{name}.py")))
        cv, cp = count_vac(vac), count_py(py)
        tv += cv
        tp += cp
        ratio = cv / cp if cp else 0
        print(f"{name:<12}{cv:>8}{cp:>9}{cv - cp:>+7}{ratio:>8.2f}x")
    print("-" * len(header))
    ratio = tv / tp if tp else 0
    print(f"{'TOTAL':<12}{tv:>8}{tp:>9}{tv - tp:>+7}{ratio:>8.2f}x\n")


def main():
    _table(f"[1] LLM tokens ({METHOD}) — vocabulary coverage matters:",
           count, count)
    _table("[2] Structural lexemes (each language's own tokenizer) — "
           "isolates grammar density:",
           lexemes_vac, lexemes_py)
    print("(comments stripped from both before counting)")


if __name__ == "__main__":
    sys.exit(main())
