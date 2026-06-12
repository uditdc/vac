#!/usr/bin/env python3
"""Tokenizer-aware keyword selection — report + benchmark, zero training.

For each target tokenizer: pick the cheapest surface form of every Vāc keyword,
then re-measure the example programs (current romanized vs keyword-optimized vs
Python) under that same tokenizer.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import keywords
from compare import PAIRS, VAC_DIR, PY_DIR, read, strip_comments_vac, strip_comments_py

import tiktoken

ENCODINGS = ["cl100k_base", "o200k_base"]


def apply_profile(text, profile):
    for canon, surf in profile.items():
        text = re.sub(rf"\b{re.escape(canon)}\b", surf, text)
    return text


def load():
    out = []
    for name in PAIRS:
        v = strip_comments_vac(read(os.path.join(VAC_DIR, f"{name}.vac")))
        p = strip_comments_py(read(os.path.join(PY_DIR, f"{name}.py")))
        out.append((name, v, p))
    return out


def main():
    progs = load()
    for enc_name in ENCODINGS:
        enc = tiktoken.get_encoding(enc_name)
        profile, report = keywords.select(enc)

        print(f"\n########## {enc_name} ##########\n")
        print("keyword selection (cheapest Sanskrit surface form):")
        h = f"{'concept':<10}{'romanized':>11}{'→ chosen':>14}{'tok':>5}{'saved':>7}"
        print(h)
        print("-" * len(h))
        for r in sorted(report, key=lambda r: -r["saved"]):
            mark = "" if r["chosen"] == r["canon"] else "  *"
            print(f"{r['canon']:<10}{r['base']:>11}{r['chosen']:>14}"
                  f"{r['cost']:>5}{r['saved']:>+7}{mark}")
        print(f"\nchosen non-default forms: {len(profile)} / {len(report)}")

        cur = sum(len(enc.encode(v)) for _, v, _ in progs)
        opt = sum(len(enc.encode(apply_profile(v, profile))) for _, v, _ in progs)
        py = sum(len(enc.encode(p)) for _, _, p in progs)
        print(f"\ntotal tokens over {len(progs)} programs ({enc_name}):")
        print(f"  Vāc romanized (current) : {cur:>4}   ({cur / py:.2f}x Python)")
        print(f"  Vāc keyword-optimized   : {opt:>4}   ({opt / py:.2f}x Python)")
        print(f"  Python                  : {py:>4}")


if __name__ == "__main__":
    main()
