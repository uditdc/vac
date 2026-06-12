"""Generate parallel Vāc / Python corpora for training matched tokenizers.

Every program is emitted in both languages with the same structure, so the two
tokenizers train on corpora of equal size and complexity — the fairness control
for the comparison. Seeded, so the corpus is deterministic.
"""

import os
import random

# Sanskrit-derived stems (Vāc) paired with English names (Python). Both are
# "vocabulary a matched tokenizer would have seen"; neither side gets an edge.
NAMES = [
    ("phala", "result"), ("mulya", "price"), ("ganana", "count"),
    ("sankhya", "number"), ("adhara", "base"), ("kara", "tax"),
    ("yoga", "total"), ("bala", "force"), ("vega", "speed"),
    ("kala", "time"), ("mana", "measure"), ("tejas", "energy"),
    ("mitra", "friend"), ("vidya", "score"), ("artha", "value"),
    ("dhana", "amount"), ("kshetra", "area"), ("samaya", "moment"),
    ("gati", "rate"), ("shakti", "power"), ("varsha", "year"),
    ("masa", "month"), ("divasa", "day"), ("matra", "unit"),
]
VERBS = [
    ("samkalana", "add_up"), ("gunanfala", "product"), ("antara", "diff"),
    ("bhaga", "divide"), ("mahattama", "gcd"), ("sthana", "place"),
    ("parivartana", "convert"), ("samasti", "aggregate"),
]
# karma -m, karaṇa -ena, apādāna -at, adhikaraṇa -e: these round-trip cleanly
# through the case splitter (no -aya/-sya sandhi collisions in generated code).
CASES = [("m", ""), ("ena", ""), ("at", ""), ("e", "")]
OPS = ["+", "-", "*"]


def _func(rng):
    vac_name, py_name = rng.choice(VERBS)
    arity = rng.randint(2, 4)
    picks = rng.sample(NAMES, arity)
    cases = CASES[:arity]
    body_terms = []
    for (vstem, _), (suf, _) in zip(picks, cases):
        body_terms.append(vstem)
    expr_vac = f" {rng.choice(OPS)} ".join(body_terms)
    py_body = [p for _, p in picks]
    expr_py = f" {rng.choice(OPS)} ".join(py_body)

    vac_params = ", ".join(f"{v}{suf}" for (v, _), (suf, _) in zip(picks, cases))
    py_params = ", ".join(p for _, p in picks)

    args_vac = " ".join(f"{rng.randint(1, 99)}{suf}" for (suf, _) in cases)
    args_py = ", ".join(f"{n}={rng.randint(1, 99)}" for _, n in
                        [(None, p) for _, p in picks])

    vac = (f"karya {vac_name}({vac_params}):\n"
           f"    phala {expr_vac}\n"
           f"{args_vac} {vac_name} vada\n")
    py = (f"def {py_name}({py_params}):\n"
          f"    return {expr_py}\n"
          f"print({py_name}({args_py}))\n")
    return vac, py


def _while(rng):
    v, p = rng.choice(NAMES)
    limit = rng.randint(5, 30)
    vac = (f"{v} bhavati 0\n"
           f"yavat {v} < {limit}:\n"
           f"    {v} vada\n"
           f"    {v} bhavati {v} + 1\n")
    py = (f"{p} = 0\n"
          f"while {p} < {limit}:\n"
          f"    print({p})\n"
          f"    {p} = {p} + 1\n")
    return vac, py


def _branch(rng):
    v, p = rng.choice(NAMES)
    a, b = rng.randint(2, 9), rng.randint(2, 9)
    sa, sp = rng.choice([("alpa", "low"), ("madhya", "mid"), ("uchcha", "high")])
    vac = (f"{v} bhavati {rng.randint(0, 50)}\n"
           f"yadi {v} % {a} == 0:\n"
           f"    \"{sa}\" vada\n"
           f"athava {v} % {b} == 0:\n"
           f"    \"{sa}\" vada\n"
           f"anyatha:\n"
           f"    {v} vada\n")
    py = (f"{p} = {rng.randint(0, 50)}\n"
          f"if {p} % {a} == 0:\n"
          f"    print(\"{sp}\")\n"
          f"elif {p} % {b} == 0:\n"
          f"    print(\"{sp}\")\n"
          f"else:\n"
          f"    print({p})\n")
    return vac, py


def _seq(rng):
    (v1, p1), (v2, p2) = rng.sample(NAMES, 2)
    vac = (f"{v1} bhavati {rng.randint(1, 99)}\n"
           f"{v2} bhavati {v1} * {rng.randint(2, 9)}\n"
           f"{v2} vada\n")
    py = (f"{p1} = {rng.randint(1, 99)}\n"
          f"{p2} = {p1} * {rng.randint(2, 9)}\n"
          f"print({p2})\n")
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
