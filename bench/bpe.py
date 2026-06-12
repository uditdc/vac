"""Minimal word-level byte-pair-encoding tokenizer (no dependencies).

Same algorithm family as GPT/Claude tokenizers: a regex pre-tokenizer splits
text into words / numbers / punctuation / whitespace runs, then BPE learns the
most frequent adjacent symbol pairs and merges them. Training a tokenizer on a
language's own corpus is what makes its keywords single tokens.
"""

import re
from collections import Counter

# Standard GPT-style pretokenizer: letters, digits, whitespace, punctuation.
PRETOK = re.compile(r"[A-Za-z_]+|[0-9]+|\s+|[^A-Za-z0-9_\s]+")

# Vāc-matched pretokenizer: a case suffix is a *bound* morpheme, so a numeral
# plus its trailing case letters is ONE host (`48m`, `0.1ena`, `5aya`) — the
# direct analogue of GPT's pretokenizer fusing English `'s` / `n't`.
VAC_PRETOK = re.compile(
    r"[0-9]+(?:\.[0-9]+)?[A-Za-z_]*|[A-Za-z_][A-Za-z0-9_]*|\s+|[^A-Za-z0-9_\s]+")


def pretokenize(text, pretok=PRETOK):
    return pretok.findall(text)


def _pair_stats(corpus):
    pairs = Counter()
    for word, freq in corpus.items():
        for a, b in zip(word, word[1:]):
            pairs[(a, b)] += freq
    return pairs


def _merge(word, pair, new):
    out, i = [], 0
    while i < len(word):
        if i < len(word) - 1 and word[i] == pair[0] and word[i + 1] == pair[1]:
            out.append(new)
            i += 2
        else:
            out.append(word[i])
            i += 1
    return tuple(out)


def train(text, num_merges, pretok=PRETOK):
    """Learn up to num_merges merge rules from text. Returns the ordered list."""
    corpus = {tuple(w): c for w, c in Counter(pretokenize(text, pretok)).items()}
    merges = []
    for _ in range(num_merges):
        stats = _pair_stats(corpus)
        if not stats:
            break
        best, count = max(stats.items(), key=lambda kv: (kv[1], kv[0]))
        if count < 2:
            break
        new = best[0] + best[1]
        merges.append(best)
        corpus = {_merge(w, best, new): c for w, c in corpus.items()}
    return merges


class Tokenizer:
    def __init__(self, merges, pretok=PRETOK):
        self.rank = {pair: i for i, pair in enumerate(merges)}
        self.pretok = pretok
        self._cache = {}

    def _encode_word(self, w):
        word = tuple(w)
        while len(word) > 1:
            best, best_rank = None, None
            for pair in zip(word, word[1:]):
                r = self.rank.get(pair)
                if r is not None and (best_rank is None or r < best_rank):
                    best, best_rank = pair, r
            if best is None:
                break
            word = _merge(word, best, best[0] + best[1])
        return word

    def count(self, text):
        total = 0
        for w in pretokenize(text, self.pretok):
            n = self._cache.get(w)
            if n is None:
                n = len(self._encode_word(w))
                self._cache[w] = n
            total += n
        return total

    @property
    def vocab_size(self):
        chars = set()
        for pair in self.rank:
            chars.update(pair)
        return len(self.rank) + len(chars)
