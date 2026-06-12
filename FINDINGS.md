# Findings — does a Sanskrit-principled language save LLM tokens?

Measured on 6 equivalent program pairs (`bench/compare.py`).

## Result: it depends entirely on the tokenizer

| Mode | What it measures | Vāc vs Python |
|---|---|---|
| **[1] LLM tokens** (tiktoken `cl100k_base`) | real cost to an LLM today | **1.37× — Vāc loses** |
| **[2] Structural lexemes** (each language's own lexer) | grammar density, tokenizer-neutral | **0.85× — Vāc wins** |

> Mode [2] improved from 1.02× to **0.85×** after the density redesign:
> bracket-free statement calls, `athava` (elif), and high-arity kāraka calls.
> The high-arity `pricing` program reaches **0.71×** — role suffixes replace
> Python's commas, parens, and `name=` labels entirely.

## Why

**The entire token penalty is vocabulary, not grammar.** A GPT/Claude-family BPE
tokenizer is trained on English+code, so every Python keyword is **one** token:

```
def → ['def']   while → ['while']   return → ['return']   print → ['print']
```

Every romanized Sanskrit word is **out-of-vocabulary** and shatters into garbage
subwords:

```
bhavati → ['bh','av','ati']      mahattama → ['mah','att','ama']
yavat   → ['y','av','at']        gunanfala → ['gun','an','f','ala']
```

So `[48m 18ena mahattama]` = 10 tokens where `gcd(48, 18)` = 7 — not because the
clause is less dense, but because `mahattama` alone burns 3 tokens.

**Once you normalize for vocabulary (mode [2]), the grammar is *denser* than
Python — by 15% overall and 29% on argument-heavy calls.** A 4-argument call is
`100m 0.1ena 5aya 3e mulya` (no commas, no parens, no `name=`) versus
`price(base=100, tax=0.1, discount=5, qty=3)`. The kāraka suffix *is* the
keyword, in 1–2 characters, and order is free.

## Matched tokenizer — the fair experiment (`bench/tokenizer_compare.py`)

The 1.37× penalty is a *tokenizer* artifact, not a language property. To prove
it, we trained a BPE tokenizer on a Vāc corpus and another on an equal-sized
Python corpus (same merge budget — the fairness control), then re-counted.

| Tokenizer | Vāc | Python | ratio |
|---|---|---|---|
| cl100k_base (today; Vāc never seen) | 350 | 256 | **1.37×** |
| matched BPE, ~400 vocab | 378 | 394 | **0.96×** |
| structural ceiling (1 token / lexeme) | 177 | 208 | **0.85×** |

**The result flips.** Once the tokenizer has seen the language, every Vāc
keyword and frequent root is a single token (verified: `bhavati`, `mahattama`,
`samkalana` → 1 token each), and Vāc goes from **+37% tokens to −4%**.

It lands at 0.96× rather than the 0.85× ceiling because a ~400-token tokenizer
saturates on our small corpus: rare identifiers (`chut`, `next`) and the
embedded-call brackets in `gcd` (which regresses to 1.09×) stay multi-token. A
larger corpus/vocab trends toward the 0.85× ceiling. A *matched pretokenizer*
that binds the case morpheme to its host (`48m` as one unit, like GPT fusing
English `'s`/`n't`) adds a further ~0.5%.

## The two real conclusions

1. **The token penalty is entirely tokenizer vocabulary — and it is fixable.**
   On a stock English-trained tokenizer any romanized (or Devanagari) Sanskrit
   is out-of-vocabulary and loses (1.37×). On a *matched* tokenizer the same
   programs win (0.96×, trending to 0.85×). The grammar was never the problem.

2. **With a perfect tokenizer, the design now wins (0.85×), and the win grows
   with program realism.** The density redesign exploited three levers:
   - **kāraka replacing keyword args:** the win grows with arity — the
     4-argument `pricing` call drops commas, parens and `name=` labels (0.71×)
   - **bracket-free statement calls:** `"namaste" vada` (2 lexemes) vs
     `print("namaste")` (4); `am bena f` (3) vs `f(a, b)` (6)
   - **`athava` (elif)** and short verb-final clauses cut branching ceremony
   - still on the table: **samāsa compounding** (multi-word names → one root)

## Known limitation (and why it's interesting)

Fused case suffixes collide with stem-final vowels: the param `chutaya`
(discount, dative) splits to stem `chut` + `aya`, not `chuta` + `aya`. Real
Sanskrit resolves exactly this with **sandhi** (euphonic vowel-merging rules) —
which we deliberately skipped as "principle-inspired, not Pāṇinian." Adding a
sandhi layer would make morphology seamless at the cost of parser complexity.

## Caveat on the metric itself

Raw token count may be the wrong target. Sanskrit's structural advantage is
**reduced ambiguity** (roles are explicit, order is free), which should reduce
*LLM errors* and correction round-trips — plausibly more valuable than a few
tokens saved. That deserves its own experiment: correctness-per-attempt, not
characters-per-program.
