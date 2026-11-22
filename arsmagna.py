#!/usr/bin/env python3
"""
arsmagna.py -- complete-anagram solver (every letter used exactly once).

Named for Michael Morton, who introduced Stuart Cooley to Ars Magna in the 1980s,
and for Ramon Llull's 13th-century combinatorial "Ars Magna".

What changed from v1
  * Real dictionary instead of a ~300-word hand-typed list
      common.txt : ~10,000 common English words, ranked by frequency
      words.txt  : ~370,000 words (obscure; only used with --rich)
    Both are downloaded automatically on first run and cached beside this script.
  * "Rarest letter first" search: at each step, pick the remaining letter that
    fewest words contain and branch only on words containing it. This is the
    classic trick that makes the search tractable and avoids re-finding the
    same phrase in every word order.
  * Ranking by readability: fewer words, longer words, more common words.

Usage
    python3 arsmagna.py "STILL IN IT"
    python3 arsmagna.py "STUART ALAN COOLEY" --max-words 4 --time 20
    python3 arsmagna.py "DYMPHNA DOLORES BARLOCO" --rich --time 30
    python3 arsmagna.py "NAME" --must holy      # phrase must contain a word
    python3 arsmagna.py "NAME" --min-word 4     # no little filler words
"""
import argparse
import os
import sys
import time
import urllib.request
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = {
    "common.txt": "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt",
    "words.txt": "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt",
}
# Short words are where junk hides ("nab", "hoon", "moly"). Allow only these.
SHORT_OK = set("a i".split()) | set(
    "am an as at be by do go he if in is it me my no of oh on or so to up us we".split()
)


def fetch(name):
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        print(f"  downloading {name} ...", file=sys.stderr)
        urllib.request.urlretrieve(SOURCES[name], path)
    with open(path, encoding="utf-8", errors="ignore") as f:
        return [w.strip().lower() for w in f if w.strip().isalpha()]


def load_words(rich, min_word):
    """Return {word: rank}; lower rank = more common."""
    common = fetch("common.txt")
    rank = {}
    for i, w in enumerate(common):
        rank.setdefault(w, i)
    if rich:
        for w in fetch("words.txt"):
            if len(w) >= 4:
                rank.setdefault(w, 100_000)

    def ok(w):
        if len(w) < min_word and not (min_word <= 2):
            return False
        if len(w) <= 2:
            return w in SHORT_OK
        if len(w) == 3:
            # 3-letter words only if reasonably common (cuts nab/cob/hoon junk)
            return rank[w] < 3000
        return True

    return {w: r for w, r in rank.items() if ok(w)}


def solve(target, rank, time_limit, max_words, must, cap):
    letters = "".join(c for c in target.lower() if c.isalpha())
    total = Counter(letters)
    n = len(letters)

    # Keep only words formable from the target's letters.
    usable = []
    for w, r in rank.items():
        if len(w) <= n:
            c = Counter(w)
            if all(total[ch] >= k for ch, k in c.items()):
                usable.append((w, c, r))
    usable.sort(key=lambda t: t[2])

    # Index words by each letter they contain.
    by_letter = {}
    for entry in usable:
        for ch in entry[1]:
            by_letter.setdefault(ch, []).append(entry)

    found, deadline = set(), time.time() + time_limit
    nodes = [0]
    vowels = set("aeiouy")

    def search(rem, chosen, left):
        nodes[0] += 1
        if len(found) >= cap or time.time() > deadline:
            return
        size = sum(rem.values())
        if size == 0:
            found.add(tuple(sorted(chosen)))
            return
        if left == 0:
            return
        if not (vowels & set(k for k, v in rem.items() if v)):
            return  # leftovers with no vowel can't make words
        # Rarest remaining letter = fewest candidate words. Branch on those only.
        pivot = min((ch for ch, v in rem.items() if v),
                    key=lambda ch: len(by_letter.get(ch, ())))
        for w, c, _ in by_letter.get(pivot, ()):
            if len(w) > size:
                continue
            if all(rem.get(ch, 0) >= k for ch, k in c.items()):
                nxt = dict(rem)
                for ch, k in c.items():
                    nxt[ch] -= k
                search(nxt, chosen + [w], left - 1)

    search(dict(total), [], max_words)
    phrases = [p for p in found if not must or any(m in p for m in must)]
    return phrases, nodes[0], len(usable), time.time() > deadline


def score(phrase, rank):
    """Lower is better."""
    k = len(phrase)
    avg = sum(len(w) for w in phrase) / k
    rarity = sum(min(rank[w], 20000) / 20000 for w in phrase)
    return k * 2 - avg * 1.5 + rarity


def main():
    ap = argparse.ArgumentParser(description="Complete anagram solver")
    ap.add_argument("target")
    ap.add_argument("--time", "-t", type=float, default=10, help="seconds (default 10)")
    ap.add_argument("--max-words", "-w", type=int, default=4)
    ap.add_argument("--min-word", "-m", type=int, default=2)
    ap.add_argument("--rich", action="store_true", help="include 370k-word dictionary")
    ap.add_argument("--must", nargs="*", default=[], help="phrase must contain one of these words")
    ap.add_argument("--top", "-n", type=int, default=25)
    ap.add_argument("--cap", type=int, default=200_000, help="stop after this many raw hits")
    a = ap.parse_args()

    rank = load_words(a.rich, a.min_word)
    t0 = time.time()
    phrases, nodes, nwords, timed_out = solve(
        a.target, rank, a.time, a.max_words, [m.lower() for m in a.must], a.cap)
    phrases.sort(key=lambda p: score(p, rank))

    letters = sum(c.isalpha() for c in a.target)
    print(f"\n{a.target.upper()}  ({letters} letters)")
    print(f"{nwords:,} candidate words | {nodes:,} nodes | {time.time()-t0:.1f}s"
          f"{' | STOPPED AT TIME LIMIT (results partial)' if timed_out else ' | search complete'}")
    print(f"{len(phrases):,} complete anagrams\n")
    for p in phrases[: a.top]:
        print("  " + " ".join(w.upper() for w in sorted(p, key=lambda x: -len(x))))
    print("\n  (word order is yours to choose -- same letters either way)")


if __name__ == "__main__":
    main()
