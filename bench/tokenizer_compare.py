#!/usr/bin/env python3
"""Fair token comparison under *matched* tokenizers.

Trains a BPE tokenizer on a Vāc corpus and another on an equal Python corpus
(same merge budget — the fairness control), then counts tokens for the 6 test
programs under each language's own matched tokenizer. The cl100k_base row shows
the unfair status quo (a tokenizer that has never seen Vāc).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpe
import corpus_gen
from compare import (PAIRS, VAC_DIR, PY_DIR, read,
                     strip_comments_vac, strip_comments_py, count as cl100k_count)

MERGE_BUDGETS = [0, 128, 256, 512, 1024]


def load_programs():
    progs = []
    for name in PAIRS:
        vac = strip_comments_vac(read(os.path.join(VAC_DIR, f"{name}.vac")))
        py = strip_comments_py(read(os.path.join(PY_DIR, f"{name}.py")))
        progs.append((name, vac, py))
    return progs


def totals(programs, vac_tok, py_tok):
    tv = sum(vac_tok.count(v) for _, v, _ in programs)
    tp = sum(py_tok.count(p) for _, _, p in programs)
    return tv, tp


def main():
    vac_corpus, py_corpus = corpus_gen.generate()
    programs = load_programs()

    print(f"corpus: Vāc {len(vac_corpus)} chars / Python {len(py_corpus)} chars")
    print(f"test programs: {len(programs)}\n")

    def train_pair(m, vac_pretok):
        vt = bpe.Tokenizer(bpe.train(vac_corpus, m, vac_pretok), vac_pretok)
        pt = bpe.Tokenizer(bpe.train(py_corpus, m))
        return vt, pt

    for vac_pretok, label in ((bpe.PRETOK, "standard pretokenizer"),
                              (bpe.VAC_PRETOK, "Vāc-matched pretokenizer "
                                               "(case morpheme bound to host)")):
        print(f"matched BPE, {label}:")
        header = f"{'merges':>8}{'vocab~':>8}{'Vāc':>8}{'Python':>9}{'ratio':>9}"
        print(header)
        print("-" * len(header))
        for m in MERGE_BUDGETS:
            vac_tok, py_tok = train_pair(m, vac_pretok)
            tv, tp = totals(programs, vac_tok, py_tok)
            vocab = (vac_tok.vocab_size + py_tok.vocab_size) // 2
            tag = "  (char-level)" if m == 0 else ""
            print(f"{m:>8}{vocab:>8}{tv:>8}{tp:>9}{tv / tp if tp else 0:>8.2f}x{tag}")
        print("-" * len(header))
        print()

    bv = sum(cl100k_count(v) for _, v, _ in programs)
    bp = sum(cl100k_count(p) for _, _, p in programs)
    print(f"status quo cl100k_base (Vāc never seen): "
          f"Vāc {bv} / Python {bp}  ->  {bv / bp:.2f}x\n")

    print("per-program at 1024 merges (Vāc-matched pretokenizer):")
    vac_tok, py_tok = train_pair(1024, bpe.VAC_PRETOK)
    h2 = f"{'program':<12}{'Vāc':>8}{'Python':>9}{'ratio':>9}"
    print(h2)
    print("-" * len(h2))
    for name, v, p in programs:
        cv, cp = vac_tok.count(v), py_tok.count(p)
        print(f"{name:<12}{cv:>8}{cp:>9}{cv / cp if cp else 0:>8.2f}x")


if __name__ == "__main__":
    main()
