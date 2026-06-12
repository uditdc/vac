"""Tokenizer-aware keyword selection.

For a target tokenizer, pick the surface form of each Vāc keyword that costs the
fewest tokens — choosing among Sanskrit synonyms in both Devanagari and romanized
script. No tokenizer training: we exploit the surface forms the tokenizer already
encodes cheaply (common Devanagari words are often single tokens on multilingual
tokenizers, while ad-hoc romanizations never are).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from vac import SYNONYMS


def cost(enc, word):
    """In-context token cost: keywords appear preceded by space/newline."""
    return len(enc.encode(" " + word))


def select(enc):
    """Return (profile, report). profile maps canonical -> chosen surface for
    every keyword whose cheapest form differs from the default romanized one."""
    profile, report = {}, []
    for canon, surfaces in SYNONYMS.items():
        candidates = [canon] + surfaces
        # min tokens, tie broken by preference order (canonical first)
        ranked = sorted((cost(enc, c), i, c) for i, c in enumerate(candidates))
        best_cost, _, chosen = ranked[0]
        base_cost = cost(enc, canon)
        if chosen != canon:
            profile[canon] = chosen
        report.append({
            "canon": canon, "base": base_cost,
            "chosen": chosen, "cost": best_cost, "saved": base_cost - best_cost,
        })
    return profile, report
