# Findings — does a Sanskrit-principled language save LLM tokens?

Measured on 6 equivalent program pairs (`bench/compare.py`,
`bench/keyword_select.py`, `bench/tokenizer_compare.py`).

## Methodology: only the *language* differs, never the names

Identifiers (`gcd`, `base`, `price`, …) are arbitrary and user-chosen, so both
languages use the **same** identifier names. This isolates what the language
*imposes* — keywords, case suffixes, verb-final structure, brackets — from what
the programmer happens to name. (An earlier version paired Sanskrit names on the
Vāc side against English names on the Python side, which unfairly charged Vāc for
its naming; controlling that removed ~8–11% of the apparent gap.)

## Headline: fairly measured, Vāc lands near parity with Python

| Measurement | Vāc vs Python | reading |
|---|---|---|
| Structural lexemes (tokenizer-neutral) | **0.85×** | grammar is genuinely denser |
| cl100k_base (today, Vāc unseen) | **1.26×** | Sanskrit keywords out-of-vocabulary |
| o200k_base (modern, multilingual) | **1.19×** | better Devanagari/coverage |
| o200k + tokenizer-aware keywords | **1.07×** | ≈ parity, zero training |
| matched BPE (~400 vocab) | **1.02×** | ≈ parity |

The honest summary: **the kāraka grammar is ~15% denser in lexemes, but real
tokenizers erode that to roughly parity.** It is not a decisive token win — but
with the right keyword choices or a matched tokenizer it is no longer a penalty
either.

## Why the 0.85× lexeme density doesn't reach the tokenizer

Two effects dilute the structural advantage when an actual BPE tokenizer counts:

1. **Whitespace.** Real tokenizers count indentation/newline tokens; the lexeme
   counter ignores them. Both languages pay similar whitespace, pulling the ratio
   toward 1.0×.
2. **Case-suffix subtokenization.** The lexer fuses `48m` / `basem` into one
   lexeme, but a standard BPE splits the suffix off (`base` + `m`), so each
   kāraka-marked operand costs ~1 extra token vs the idealized lexeme count.

Where the grammar *does* still help: the 4-argument `pricing` call
`100m 0.1ena 5aya 3e price` drops commas, parens and `name=` labels — its lexeme
ratio is 0.71×, the strongest structural win, because kāraka role suffixes are
the keyword in 1–2 characters and order is free.

## Why today's tokenizers penalize Vāc (and how to fix it)

A GPT/Claude-family BPE is trained on English+code, so every Python keyword is
**one** token (`def`, `while`, `return`, `print`). Romanized Sanskrit is
out-of-vocabulary and fragments (`bhavati` → `bh·av·ati`). Two fixes:

**Strategy 1 — matched tokenizer** (`bench/tokenizer_compare.py`). Train a BPE on
a Vāc corpus and an equal one on Python (same merge budget). Every Vāc keyword
becomes a single token; the result moves from 1.26× to **1.02×** (parity). Script
becomes irrelevant — `bhavati` and `भव` both collapse to one token.

**Strategy 2 — tokenizer-aware keyword selection** (`bench/keyword_select.py`),
the focus here. Without any training, *pick the keyword surface form the target
tokenizer already encodes cheaply*, choosing among Sanskrit synonyms in both
scripts. `vac.py` accepts every form via an alias layer, so the chosen dialect
still runs.

| | cl100k_base | o200k_base |
|---|---|---|
| Vāc romanized | 1.26× | 1.19× |
| Vāc keyword-optimized | **1.20×** | **1.07×** |

What the selector finds on o200k: the high-frequency assignment `bhavati` → `भव`
(2→1 token), plus `यदि फल लिख भाग सत्य अथ` — common Devanagari words that are
single tokens (an ad-hoc romanization never is). On cl100k (poor Devanagari
coverage) it picks romanized synonyms `astu`/`cet`/`antara` instead. The chosen
dialect executes: `gcd(48, 18)` written with `भव`/`फल`/`लिख` runs and prints `6`.

**Three things strategy 2 taught us:**
1. **Keywords are a minority of tokens**, so optimizing them alone buys ~5–11% —
   real, but it only brings Vāc *to* parity, not past it.
2. **Case suffixes are already 1 token each** (`m`, `ena`, `aya`…), exactly like
   Python's `,` `(` `=`. Kāraka marking is **token-neutral, not a penalty**.
3. **Both strategies converge on the same ceiling** — every keyword a single
   token — reached either by training (strategy 1) or by selecting in-vocabulary
   forms (strategy 2). Strategy 2 needs no training but is bounded by how many
   single-token Sanskrit forms a given tokenizer happens to contain.

## The real conclusion

Fairly measured — identifiers controlled — a Sanskrit-principled grammar is
**marginally denser than Python in lexemes (0.85×) but only reaches parity
(~1.0–1.07×) on real tokenizers**, because whitespace and case-suffix
subtokenization eat the structural lead. The earlier "Vāc wins" numbers were
optimistic: they either ignored whitespace (lexeme mode) or benefited from unfair
Sanskrit-vs-English identifier pairing. The token-efficiency case for Sanskrit is
therefore **modest, not dramatic** — and it hinges on keyword/tokenizer choices,
not on grammatical elegance.

## Known limitation (and why it's interesting)

Fused case suffixes collide with stem-final vowels: the param `discaya` (dative)
splits cleanly to `disc` + `aya`, but a stem already ending in a vowel (`chuta` +
`aya`) over-strips. Real Sanskrit resolves exactly this with **sandhi** (euphonic
vowel-merging) — deliberately skipped here as "principle-inspired, not Pāṇinian."

## Caveat on the metric itself

Raw token count may be the wrong target. Sanskrit's structural advantage is
**reduced ambiguity** — roles are explicit and order is free — which should
reduce *LLM errors* and correction round-trips, plausibly more valuable than a
few tokens. That deserves its own experiment: correctness-per-attempt, not
characters-per-program.
