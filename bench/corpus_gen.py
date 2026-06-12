"""Generate parallel Vāc / Python corpora for training matched tokenizers.

Every program is emitted in both languages with the same structure, so the two
tokenizers train on corpora of equal size and complexity — the fairness control
for the comparison. Seeded, so the corpus is deterministic.
"""

import os
import random

# Identifiers are arbitrary and user-chosen, so both languages use the SAME
# names — only the language (keywords, case suffixes, structure) differs. This
# isolates what the language imposes from what the programmer happens to name.
NAMES = [
    "result", "price", "count", "number", "base", "tax", "total", "force",
    "speed", "time", "measure", "energy", "friend", "score", "value", "amount",
    "area", "moment", "rate", "power", "year", "month", "day", "unit",
]
VERBS = ["add_up", "product", "diff", "divide", "gcd", "place",
         "convert", "aggregate"]
# karma -m, karaṇa -ena, apādāna -at, adhikaraṇa -e: these round-trip cleanly
# through the case splitter (no -aya/-sya sandhi collisions in generated code).
CASES = [("m", ""), ("ena", ""), ("at", ""), ("e", "")]
OPS = ["+", "-", "*"]


def _func(rng):
    name = rng.choice(VERBS)
    arity = rng.randint(2, 4)
    picks = rng.sample(NAMES, arity)
    cases = CASES[:arity]
    expr = f" {rng.choice(OPS)} ".join(picks)

    vac_params = ", ".join(f"{v}{suf}" for v, (suf, _) in zip(picks, cases))
    py_params = ", ".join(picks)
    args_vac = " ".join(f"{rng.randint(1, 99)}{suf}" for suf, _ in cases)
    args_py = ", ".join(f"{n}={rng.randint(1, 99)}" for n in picks)

    vac = (f"karya {name}({vac_params}):\n"
           f"    phala {expr}\n"
           f"{args_vac} {name} vada\n")
    py = (f"def {name}({py_params}):\n"
          f"    return {expr}\n"
          f"print({name}({args_py}))\n")
    return vac, py


def _while(rng):
    v = rng.choice(NAMES)
    limit = rng.randint(5, 30)
    vac = (f"{v} bhavati 0\n"
           f"yavat {v} < {limit}:\n"
           f"    {v} vada\n"
           f"    {v} bhavati {v} + 1\n")
    py = (f"{v} = 0\n"
          f"while {v} < {limit}:\n"
          f"    print({v})\n"
          f"    {v} = {v} + 1\n")
    return vac, py


def _branch(rng):
    v = rng.choice(NAMES)
    a, b = rng.randint(2, 9), rng.randint(2, 9)
    label = rng.choice(["low", "mid", "high"])
    vac = (f"{v} bhavati {rng.randint(0, 50)}\n"
           f"yadi {v} % {a} == 0:\n"
           f"    \"{label}\" vada\n"
           f"athava {v} % {b} == 0:\n"
           f"    \"{label}\" vada\n"
           f"anyatha:\n"
           f"    {v} vada\n")
    py = (f"{v} = {rng.randint(0, 50)}\n"
          f"if {v} % {a} == 0:\n"
          f"    print(\"{label}\")\n"
          f"elif {v} % {b} == 0:\n"
          f"    print(\"{label}\")\n"
          f"else:\n"
          f"    print({v})\n")
    return vac, py


def _seq(rng):
    v1, v2 = rng.sample(NAMES, 2)
    vac = (f"{v1} bhavati {rng.randint(1, 99)}\n"
           f"{v2} bhavati {v1} * {rng.randint(2, 9)}\n"
           f"{v2} vada\n")
    py = (f"{v1} = {rng.randint(1, 99)}\n"
          f"{v2} = {v1} * {rng.randint(2, 9)}\n"
          f"print({v2})\n")
    return vac, py


TEMPLATES = [_func, _while, _branch, _seq]


def generate(n=300, seed=7):
    rng = random.Random(seed)
    vac_parts, py_parts = [], []
    for _ in range(n):
        v, p = rng.choice(TEMPLATES)(rng)
        vac_parts.append(v)
        py_parts.append(p)
    return "\n".join(vac_parts), "\n".join(py_parts)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "corpus")
    os.makedirs(out, exist_ok=True)
    vac, py = generate()
    with open(os.path.join(out, "vac.txt"), "w", encoding="utf-8") as f:
        f.write(vac)
    with open(os.path.join(out, "py.txt"), "w", encoding="utf-8") as f:
        f.write(py)
    print(f"wrote corpus/vac.txt ({len(vac)} chars), corpus/py.txt ({len(py)} chars)")
