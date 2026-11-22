#!/usr/bin/env python3
"""
arsmagna3.py -- anagrams, put in order and ranked by how much they read like English.

Named for Michael Morton (Apple, Google), who introduced Stuart Cooley to Ars Magna.

Step 1  SOLVE   finds complete anagrams (every letter used once), via arsmagna.py.
Step 2  ORDER   an anagram is only a bag of words. For each bag, every word order is
                tried (4 words = 24 orders) and the best-reading order is kept.
Step 3  RANK    each ordered phrase is scored on two things:
                  grammar    -- how plausible is this sequence of word types
                                (noun, verb, adjective, adverb ...)? Learned from the
                                Brown Corpus, where every word is hand-tagged.
                  phrasing   -- how much more often do these word pairs occur together
                                than chance would predict? Learned from ~3 million words
                                of books and web text.
                The best are shown as a top 10, with the top 3 starred.

Usage
    python3 arsmagna3.py "DYMPHNA BARLOCO"
    python3 arsmagna3.py "STUART ALAN COOLEY" --best 3
    python3 arsmagna3.py "HOWARD LUTNICK" --slang      # slang + shorthand, flagged with meanings
    python3 arsmagna3.py "YOUR NAME" --time 15 --rank-time 10

Needs model.json.gz beside this file (python3 build_model.py makes it).

HONEST LIMIT: the score measures how *fluent* a phrase is, not whether it is *meaningful*.
It cannot know that "anchor body palm" suits a particular person. It narrows thousands of
anagrams to a short list; the final choice is a human one.
"""
import argparse
import gzip
import json
import math
import os
import sys
import time
from itertools import combinations, permutations

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arsmagna as base  # noqa: E402  (the solver)

NTAGS = 13  # 12 word types + END

# Search ladder. If a level finds fewer than --min-results anagrams, the next one relaxes the
# guardrails: shorter words and rarer words allowed, then the full 370,000-word dictionary.
#          name        min_word  min_count  max_words  rich
LEVELS = [("standard", 3, 15, 4, False),
          ("relaxed",  2,  3, 4, False),
          ("loose",    3,  0, 5, True)]
# Letters a name might carry in real life (--titles): each is tried as a spare word's worth of letters.
TITLES = ["Mr", "Mrs", "Ms", "Miss", "Dr", "Don", "Lord", "Lady", "Sir", "AG", "Jr", "Sr", "II"]


class Model:
    def __init__(self, path):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            m = json.load(f)
        self.uni, self.bi, self.wt = m["uni"], m["bi"], m["wt"]
        self.tt, self.t1 = m["tt"], m["t1"]
        self.N = sum(self.uni.values())
        self.V = len(self.uni)
        tag_totals = {}
        for counts in self.wt.values():
            for t, c in counts.items():
                tag_totals[t] = tag_totals.get(t, 0) + c
        grand = sum(tag_totals.values())
        self.tag_prior = {t: c / grand for t, c in tag_totals.items()}
        self._emit, self._lt, self._struct = {}, {}, {}
        self.slang = {}          # word -> entry from slang.json (only when --slang)

    def set_slang(self, db):
        self.slang = db
        self._emit.clear()
        self._struct.clear()

    def show(self, w, cap=True):
        """How a word is written: slang entries carry their own spelling (Fo', D'oh, SMH)."""
        e = self.slang.get(w)
        if e:
            return e["d"] if cap else e["d"].lower() if e["k"] != "text shorthand" else e["d"]
        return w.capitalize() if cap else w

    def word_penalty(self, words):
        """Unseen-in-text words and slang cost a little, so loose searches don't promote junk."""
        p = 0.0
        for w in words:
            if w in self.slang:
                p += 0.2
            elif self.uni.get(w, 0) == 0:
                p += 0.5
        return p

    # ---- phrasing: how much likelier is b after a than chance?
    def p_uni(self, w):
        return (self.uni.get(w, 0) + 1) / (self.N + self.V)

    def lift(self, a, b):
        ca = self.uni.get(a, 0)
        pu = self.p_uni(b)
        lam = 0.6 if ca else 0.0
        pab = self.bi.get(f"{a} {b}", 0) / ca if ca else 0.0
        return math.log((lam * pab + (1 - lam) * pu) / pu)

    # ---- grammar: word types
    def emit(self, w):
        """{tag: log-score} for the few tags this word plausibly has."""
        if w in self._emit:
            return self._emit[w]
        counts = self.wt.get(w)
        if w in self.slang:
            probs = {self.slang[w]["p"]: 0.9}
        elif counts:
            tot = sum(counts.values())
            probs = {t: c / tot for t, c in counts.items() if c / tot >= 0.04}
        else:  # unseen word: guess from its ending
            if w.endswith("ly"):
                probs = {"ADV": .7, "ADJ": .3}
            elif w.endswith("ing"):
                probs = {"V": .4, "N": .3, "ADJ": .3}
            elif w.endswith("ed"):
                probs = {"V": .5, "ADJ": .4, "N": .1}
            elif w.endswith(("ous", "ful", "ive", "able", "al", "ic", "ish", "less")):
                probs = {"ADJ": .7, "N": .3}
            elif w.endswith("s") and len(w) > 3:
                probs = {"N": .6, "V": .4}
            else:
                probs = {"N": .6, "V": .2, "ADJ": .2}
        out = {t: math.log(p) - math.log(self.tag_prior.get(t, 0.01)) for t, p in probs.items()}
        self._emit[w] = out
        return out

    def lt(self, a, b):
        k = (a, b)
        v = self._lt.get(k)
        if v is None:
            v = math.log((self.tt.get(f"{a} {b}", 0) + 0.5) / (self.t1.get(a, 0) + 0.5 * NTAGS))
            self._lt[k] = v
        return v

    def grammar(self, words):
        """Best word-type path through the phrase.
        Returns (score per step, list of word types); higher score = more grammatical."""
        prev = {"START": (0.0, [])}
        for w in words:
            cur = {}
            for t, e in self.emit(w).items():
                pt, (p, path) = max(((pt, v) for pt, v in prev.items()),
                                    key=lambda x: x[1][0] + self.lt(x[0], t))
                cur[t] = (p + self.lt(pt, t) + e, path + [t])
            prev = cur
        best = max(((p + self.lt(t, "END"), path) for t, (p, path) in prev.items()),
                   key=lambda x: x[0])
        return best[0] / (len(words) + 1), best[1]

    FUNCTION = {"DET", "PREP", "CONJ", "TO", "AUX", "PRON"}

    @staticmethod
    def shape_bonus(tags):
        """Reward recognisable shapes: a clause (noun + verb), or a tidy noun phrase
        such as ADJ N, ADV ADJ N, N N N."""
        if "V" in tags and ("N" in tags or "PRON" in tags) and tags[-1] in ("N", "V", "ADV", "ADJ"):
            return 0.35
        if tags[-1] == "N" and all(t in ("DET", "ADJ", "ADV", "N", "NUM") for t in tags):
            return 0.25
        return 0.0

    def struct(self, grp):
        """Structure score of a word group on its own: grammar + phrasing + shape bonus."""
        v = self._struct.get(grp)
        if v is None:
            g, tags = self.grammar(grp)
            lifts = [self.lift(a, b) for a, b in zip(grp, grp[1:])]
            phr = sum(lifts) / len(lifts) if lifts else 0.0
            v = (g + 0.6 * phr + self.shape_bonus(tags), tags)
            self._struct[grp] = v
        return v

    def score(self, words, detail=False):
        g, tags = self.grammar(words)
        lifts = [self.lift(a, b) for a, b in zip(words, words[1:])]
        phr = sum(lifts) / len(lifts) if lifts else 0.0
        k = len(words)
        avg_len = sum(len(w) for w in words) / k
        filler = sum(1 for w, t in zip(words, tags) if t in self.FUNCTION or len(w) <= 2)
        s = (g + 0.6 * phr + self.shape_bonus(tags)
             + 0.25 * (avg_len - 4)      # prefer substantial words
             - 0.35 * filler             # ... over little filler words
             - 0.45 * max(0, k - 2)      # ... and fewer words over more
             - self.word_penalty(words))
        return (s, tags) if detail else s


def best_order(model, bag):
    """Try every distinct word order. The order is chosen on grammar + phrasing alone
    (the penalties for filler and length are the same for any order of the same words);
    the full ranking score is then computed once for the winning order."""
    best = None
    for perm in set(permutations(bag)):
        g, _ = model.grammar(perm)
        lifts = [model.lift(a, b) for a, b in zip(perm, perm[1:])]
        s = g + 0.6 * (sum(lifts) / len(lifts) if lifts else 0.0)
        if best is None or s > best[0]:
            best = (s, perm)
    return model.score(best[1]), best[1]


def splits(perm, max_chunks=3):
    """Every way to cut an ordered phrase into up to max_chunks contiguous groups."""
    k = len(perm)
    for ncut in range(max_chunks):
        for cuts in combinations(range(1, k), ncut):
            idx = (0,) + cuts + (k,)
            yield [perm[idx[i]:idx[i + 1]] for i in range(len(idx) - 1)]


def chunk_best(model, bag):
    """Free use of punctuation. Tries every word order and every way of breaking the words
    into groups separated by commas; a two-word group may be hyphenated when the pair
    behaves like a compound (low-rank). Each group is scored as its own little phrase, so
    'Daily Low Dutch Rank' can become 'Daily Dutch, Low-rank'. Commas cost a little, so
    punctuation only wins when it genuinely reads better. Returns (score, order, text)."""
    k = len(bag)
    best = None
    for perm in set(permutations(bag)):
        for groups in splits(perm):
            tags, total, hyph, pieces = [], 0.0, 0, []
            for grp in groups:
                v, t = model.struct(grp)
                total += len(grp) * v
                tags += t
                if (len(grp) == 2 and t[0] in ("N", "ADJ") and t[1] == "N"
                        and model.bi.get(f"{grp[0]} {grp[1]}", 0) >= 3 and model.lift(*grp) > 1.0):
                    pieces.append(model.show(grp[0]) + "-" + model.show(grp[1], False))
                    hyph += 1
                else:
                    pieces.append(" ".join(model.show(w) for w in grp))
            struct = total / k - 0.3 * (len(groups) - 1) + 0.1 * hyph
            avg_len = sum(len(w) for w in perm) / k
            filler = sum(1 for w, t in zip(perm, tags) if t in Model.FUNCTION or len(w) <= 2)
            s = (struct + 0.25 * (avg_len - 4) - 0.35 * filler - 0.45 * max(0, k - 2)
                 - model.word_penalty(perm))
            if best is None or s > best[0]:
                best = (s, perm, ", ".join(pieces))
    return best


def load_slang(path):
    if not os.path.exists(path):
        sys.exit("slang.json not found beside the program (needed for --slang).")
    with open(path, encoding="utf-8") as f:
        return {e["w"]: e for e in json.load(f)}


def main():
    ap = argparse.ArgumentParser(description="Ordered, ranked anagrams")
    ap.add_argument("target")
    ap.add_argument("--best", "-b", type=int, default=10, help="how many to show (default 10)")
    ap.add_argument("--time", "-t", type=float, default=8, help="seconds to search for anagrams (per level)")
    ap.add_argument("--rank-time", type=float, default=6, help="seconds to order and rank them")
    ap.add_argument("--max-words", "-w", type=int, default=None, help="override the level's word limit")
    ap.add_argument("--min-word", "-m", type=int, default=None, help="override the level's shortest word")
    ap.add_argument("--min-count", type=int, default=None,
                    help="override: drop words seen fewer times than this in the model's text")
    ap.add_argument("--min-results", type=int, default=5,
                    help="if fewer anagrams than this are found, relax the guardrails and retry (default 5)")
    ap.add_argument("--strict", action="store_true", help="never relax the guardrails")
    ap.add_argument("--loose", action="store_true", help="start with the guardrails already down")
    ap.add_argument("--pool", type=int, default=4000, help="how many anagrams to order and rank")
    ap.add_argument("--rich", action="store_true", help="always use the 370,000-word list")
    ap.add_argument("--must", nargs="*", default=[])
    ap.add_argument("--slang", action="store_true",
                    help="allow text shorthand, slang, interjections and dialect from slang.json; "
                         "they are flagged in the results with their meaning")
    ap.add_argument("--add", nargs="*", default=[], help="extra words to allow, e.g. --add lick nut")
    ap.add_argument("--titles", action="store_true",
                    help="also try the name with a title: Mr Mrs Ms Miss Dr Don Lord Lady Sir AG Jr Sr II "
                         "(search time is shared, so raise --time)")
    ap.add_argument("--initial", action="store_true",
                    help="also try the name plus one middle initial, A-Z (raise --time)")
    ap.add_argument("--hide-self", action="store_true", help="hide the name itself if it is an anagram of itself")
    ap.add_argument("--no-punct", dest="punct", action="store_false",
                    help="switch off commas and hyphens (on by default)")
    ap.add_argument("--refine", type=int, default=300,
                    help="how many top phrases get the comma/hyphen treatment (default 300)")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    mpath = os.path.join(HERE, "model.json.gz")
    if not os.path.exists(mpath):
        sys.exit("model.json.gz not found. Run:  python3 build_model.py")
    model = Model(mpath)
    db = load_slang(os.path.join(HERE, "slang.json")) if a.slang else {}
    model.set_slang(db)

    # Targets: the name itself, plus (optionally) the name with a title or a middle initial.
    targets = [("", a.target)]
    if a.titles:
        targets += [(t.upper(), f"{a.target} {t}") for t in TITLES]
    if a.initial:
        targets += [(c.upper() + ".", f"{a.target} {c}") for c in "abcdefghijklmnopqrstuvwxyz"]
    per = max(0.5, a.time / len(targets))
    must = [m.lower() for m in a.must]
    own = tuple(sorted(a.target.lower().split()))

    levels = LEVELS[:1] if a.strict else LEVELS[2:] if a.loose else LEVELS
    t0 = time.time()
    for name, mw, mc, mx, rich in levels:
        mw = a.min_word if a.min_word is not None else mw
        mc = a.min_count if a.min_count is not None else mc
        mx = a.max_words if a.max_words is not None else mx
        rich = rich or a.rich
        rank = base.load_words(rich, mw)
        if not rich and mc > 0:   # keep only words that really occur in books and edited text
            rank = {w: r for w, r in rank.items()
                    if model.uni.get(w, 0) >= mc or w in base.SHORT_OK}
        for w in list(a.add) + list(db):
            rank[w.lower()] = 900          # words you choose are always allowed
        found, timed_out = [], False
        for label, tgt in targets:
            bags, _, _, to = base.solve(tgt, rank, per, mx, must, 400_000)
            timed_out |= to
            found += [(b, label) for b in bags if not (a.hide_self and tuple(sorted(b)) == own)]
        level_note = f"{name}: words of {mw}+ letters, seen {mc}+ times, up to {mx} words" + \
                     (", full dictionary" if rich else "")
        if len(found) >= a.min_results:
            break
    t_solve = time.time() - t0

    # Most promising first (common, longer words), then order + rank within the time box.
    found.sort(key=lambda x: base.score(x[0], rank))
    pool = found[: a.pool]
    t1 = time.time()
    ranked, done = [], 0
    for bag, label in pool:
        if time.time() - t1 > a.rank_time:
            break
        s, order = best_order(model, bag)
        ranked.append((s, order, label))
        done += 1
    ranked.sort(key=lambda x: -x[0])
    plain = lambda o: " ".join(model.show(w) for w in o)
    if a.punct:   # punctuation pass on the best candidates, then re-rank them
        top = []
        for s, order, label in ranked[: a.refine]:
            s2, order2, text = chunk_best(model, order)
            top.append((s2, order2, label, text))
        top.sort(key=lambda x: -x[0])
        ranked = top + [(s, o, l, plain(o)) for s, o, l in ranked[a.refine:]]
    else:
        ranked = [(s, o, l, plain(o)) for s, o, l in ranked]

    n = sum(c.isalpha() for c in a.target)
    print(f"\n{a.target.upper()}  ({n} letters)")
    print(f"search level -- {level_note}")
    print(f"{len(found):,} anagrams found in {t_solve:.1f}s"
          f"{' (search hit time limit)' if timed_out else ''}; "
          f"{done:,} ordered and ranked in {time.time()-t1:.1f}s"
          f"{' (ranking hit time limit)' if done < len(pool) else ''}\n")
    if not found:
        print("  Nothing found even with the guardrails down. Try --titles, --initial, or --add words.")
    flagged = False
    for i, (s, order, label, text) in enumerate(ranked[: a.best], 1):
        star = "*" if i <= 3 else " "
        _, tags = model.score(order, detail=True)
        extra = f"  [+{label}]" if label else ""
        print(f" {star}{i:2}. {text:<38} {' '.join(tags):<18} score {s:5.2f}{extra}")
        for w in order:              # flag slang / shorthand and show what it means
            e = db.get(w)
            if e:
                flagged = True
                print(f"        > {e['d']} ({e['k']}): {e['m']}")
    print("\n  * = top three.  The middle column is each phrase's word-type pattern")
    print("    (N noun, V verb, ADJ adjective, ADV adverb, DET article, PREP preposition ...).")
    print("  Scores are relative: higher reads more like natural English.")
    print("  They measure fluency, not meaning -- the final choice is yours.")
    if flagged:
        print("  '>' lines flag slang, shorthand or dialect words and say what they mean.")


if __name__ == "__main__":
    main()
