# Vāc — a Sanskrit-principled programming language

**Vāc** (वाच्, "speech / word") is an experimental programming language whose
syntax and semantics are derived from the structural principles of Sanskrit
grammar (Pāṇini's *Aṣṭādhyāyī*). It is general-purpose and imperative —
comparable to Python or JavaScript in expressive power — but it encodes program
structure the way Sanskrit encodes meaning: through **morphological role
marking** rather than word order.

The research question: *can an LLM express the same program in fewer tokens when
the language carries semantic roles in the grammar itself?*

## The three Sanskrit principles that drive the design

### 1. Kāraka (कारक) — semantic roles marked on the word

Sanskrit marks each noun's role in an action with a short **case suffix**
(vibhakti). Word order is therefore free: the suffix, not the position, says
what each word *does*. Vāc uses this for function arguments — arguments are
**tagged by role, not position**, so calls are order-independent and
self-documenting, and the "keyword" is a 1–2 character morpheme instead of a
long `name=` label.

| Kāraka | Role | Suffix | PL meaning |
|---|---|---|---|
| kartṛ (कर्तृ) | agent | *(bare)* | the result / bound name |
| karma (कर्म) | object | `-m` | primary input |
| karaṇa (करण) | instrument | `-ena` | "by means of" / second operand |
| sampradāna (संप्रदान) | recipient | `-aya` | destination / target |
| apādāna (अपादान) | source | `-at` | source / "from" |
| sambandha (संबंध) | relation | `-sya` | possession / field of |
| adhikaraṇa (अधिकरण) | locus | `-e` | scope / index / "in" |

### 2. SOV / verb-final — operations come last

Sanskrit clauses are verb-final. In Vāc a **clause** is written `[ operands… verb ]`
— the operands (case-marked) come first, the verb (function name) last:

```
[10m 2ena bhaga]        # divide: karma(10) by karaṇa(2)  ->  5
[2ena 10m bhaga]        # identical — order is free, roles are fixed
```

### 3. Dhātu (धातु) + samāsa (समास) — small roots, dense compounds

Operations are named with Sanskrit verbal roots (`yoga` = add, `guṇa` =
multiply, `vada` = speak/print). Identifiers compound freely like Sanskrit
nominal compounds, packing multi-word concepts into one token.

## Quick taste

```
karya samkalana(am, bena):       # function "addition" of karma a and karaṇa b
    phala a + b

x bhavati 5m 3ena samkalana      # x "becomes" the clause's result  -> 8
x vada                           # speak x

yadi x > 5:
    "mahat" vada                 # "large"
anyatha:
    "alpa" vada                  # "small"
```

A verb-final clause needs **no brackets** at statement level or as a binding's
value — the line boundary delimits it. Brackets `[ … ]` are only needed to embed
a call *inside* an arithmetic expression, e.g. `n * [(n - 1)m gunanfala]`.

## Keyword glossary

| Vāc | Sanskrit | Means |
|---|---|---|
| `karya` | कार्य | function / task |
| `phala` | फल | return ("the fruit") |
| `bhavati` | भवति | becomes (binding) |
| `yadi` | यदि | if |
| `athava` | अथवा | else-if (elif) |
| `anyatha` | अन्यथा | else |
| `yavat` | यावत् | while ("as long as") |
| `vada` | वद | print ("speak") |
| `satya` / `asatya` | सत्य / असत्य | true / false |
| `sunya` | शून्य | null / void |
| `ca` / `va` / `na` | च / वा / न | and / or / not |

## Run

```
python3 vac.py examples/factorial.vac
python3 vac.py -c '"namaste" vada'
```

## Measuring the hypothesis

- `bench/compare.py` — equivalent Vāc/Python programs, token counts under
  `tiktoken` (LLM cost today) and under each language's own lexer (grammar
  density). Vāc: **1.37×** LLM tokens but **0.85×** lexemes.
- `bench/tokenizer_compare.py` — trains a BPE tokenizer on a Vāc corpus and an
  equal one on Python (`bench/bpe.py`, `bench/corpus_gen.py`), then re-measures.
  The result flips to **0.96×**: once the tokenizer has seen the language, Vāc
  wins. This is the honest test of "can an LLM code in fewer tokens?"

| tokenizer | Vāc vs Python |
|---|---|
| cl100k_base (today, Vāc unseen) | 1.37× — loses |
| matched BPE (~400 vocab) | 0.96× — wins |
| structural ceiling (1 token/lexeme) | 0.85× — asymptote |

Full writeup in [`FINDINGS.md`](FINDINGS.md).
