#!/usr/bin/env python3
"""
ars_magna.py
============
A true anagram solver: finds all multi-word phrases that use
EVERY letter of the input exactly once.
 
Named in honor of Michael Morton, programmer for Apple and Google,
who introduced his friend Stuart Cooley to Ars Magna — one of the
earliest anagram-solving programs — in Hawaii in the 1980s.
 
The name itself honors Ramon Llull's 13th-century work on combinatorial
logic, "Ars Magna" (The Great Art), the philosophical ancestor of all
computational language tools.
 
Usage:
    python3 ars_magna.py "DYMPHNA BARLOCO"
    python3 ars_magna.py "DEDE BARLOCO" --time 5
    python3 ars_magna.py "YOUR NAME HERE" --time 10 --min-word 3
 
Author: Stuart Alan Cooley (with Claude, Anthropic, 2026)
"""
 
import sys
import time
import argparse
from collections import Counter
 
 
# ─────────────────────────────────────────────────────────────────────────────
# WORD LIST
# A curated English vocabulary weighted toward meaningful, poetic words.
# Extend this list to improve results — longer lists find more anagrams
# but require more search time.
# ─────────────────────────────────────────────────────────────────────────────
 
VOCABULARY = """
a an the and or of in to at by on as up
able ably about abroad
adore adored adores adorn adorns adorably adorable adorned adornably
all am arc are arm arms
balm balmy band bar barn baron
be bear bloom blood bloody bold bond born bore broad broadly brood
calm canal candor chord cold color coral cord corn crown
dab dare dark day dear do done door
dolor dolors dolorous
dream drool
fond for from
hand handy harbor hard hardly harm harms hold holy
honor honorably hymn hymnal
lab lady lamb lamp land lard lay
load loan loam lob lorn
lord lords lordly lore
loyal loyally loyalty
mob modal moody moon moral morals morally manor
moan mold moron
nod nomad normal normally
or oral orb orca
palm pardon parody plan plod ploy
road roan robe room royal royally
salon sand
balm band barn
harm harmony
badly baldly
ardor ardors
maroon
melody modal model
broadly harmony abandon rondo bloody brood bloom
moody moron donors lordly
ably
coral colon colony
baron balcony
random randomly
adornably
broad abroad
boa boas
cod cob mob rob
nor for
morale baron maroon
colony colon coral normal baron
random
doorman
adorably adorable
abroad
a an be do or
holm hold
by my dry pry
holy moly
hay nay
ray bay day gay lay may pay say way
boy coy joy toy soy
bar car far jar mar tar
born corn horn morn torn worn
bold cold fold gold hold mold old sold told
bond fond pond
harm farm charm alarm
hard card bard lard yard
pardon hard hardly
harmony hardly
bland blond
rondo mondo
balm calm palm
corona coral
cord word lord hoard
coral moral
baron maroon
labrador
broadly randomly
harm charm farm alarm
body mob lord
palm balm calm
cobra
maroon baboon
anchor manor
nomad
yam yap yak
map nap cap lap rap sap tap
cab dab lab nab tab
lob mob rob cob bob sob
bald bold cold fold gold hold mold old sold told
bond fond pond wand band hand land sand
boom doom loom room
moon boon loon noon soon
born horn corn morn torn worn
cord word lord hoard
bard card hard lard yard
harm farm charm alarm
holy moly roly poly
bay day gay hay jay lay may nay pay ray say way
arson mason
cordon pardon
maroon balloon cartoon
nomad
broadly
already
moral coral
baron maroon
randomly
labrador
doorman
honor donor manor
cord
nobody somebody anybody
holy body
blood bloody
blooms bloom
moody broody
broadly randomly
hardly
balmy calmy palmy
royal loyal
moral coral
nomad modal
harbor arbor
candor
harmony
broadly randomly
lard bard hard card yard
random randomly broadly hardly
honor donor manor
a an am as at
be by do go my no of on or to up us
ably amply
road roads
royal royals
bond bonds
lord lords
harm harms
land lands
hand hands
body bodies
door doors
room rooms
born morning
lamp lamps
palm palms
cord cords
hymn hymns
horn horns
barn barns
farm farms
charm charms
anchor anchors
harbor harbors
harmony harmonies
melody melodies
moral morals
color colors
manor manors
balloon balloons
maroon maroons
random randoms
colony colonies
balcony balconies
corona coronas
cobra cobras
nomad nomads
labrador labradors
doorman doormen
carol carols
broad broads
abroad
"""
 
def build_word_list(vocabulary_string, min_len=2):
    """Parse vocabulary string into a clean deduplicated word list."""
    words = sorted(set(
        w.lower() for w in vocabulary_string.split()
        if w.isalpha() and len(w) >= min_len
    ))
    return words
 
 
# ─────────────────────────────────────────────────────────────────────────────
# CORE SOLVER
# ─────────────────────────────────────────────────────────────────────────────
 
def can_form(word, available):
    """Check if word can be formed from available letter counts."""
    word_count = Counter(word)
    return all(available.get(c, 0) >= n for c, n in word_count.items())
 
 
def subtract_letters(available, word):
    """Return new letter counts after removing word's letters."""
    result = dict(available)
    for c in word:
        result[c] -= 1
    return result
 
 
def solve(target, words, time_limit=9.0, min_word_len=2, max_words=7):
    """
    Find all complete anagrams of target using words from the word list.
 
    Rules:
      - Every letter of target must be used exactly once.
      - Each word in the result must appear in the word list.
      - Results are deduplicated (word order doesn't matter).
      - Search halts at time_limit seconds.
 
    Returns a list of anagram phrases, sorted by quality.
    """
    target_clean = target.lower().replace(" ", "").replace("-", "")
    available = Counter(target_clean)
    total_letters = sum(available.values())
 
    # Filter word list to only words formable from available letters
    usable = sorted(
        set(w for w in words
            if min_word_len <= len(w) <= total_letters
            and can_form(w, available)),
        key=lambda x: (-len(x), x)
    )
 
    results = set()
    start_time = time.time()
    stats = {"calls": 0, "pruned": 0}
 
    def search(remaining_letters, current_phrase):
        stats["calls"] += 1
 
        # Time check
        if time.time() - start_time > time_limit:
            return
 
        remaining_count = sum(remaining_letters.values())
 
        # Base case: all letters used
        if remaining_count == 0:
            results.add(tuple(sorted(current_phrase)))
            return
 
        # Pruning: too many words already
        if len(current_phrase) >= max_words:
            stats["pruned"] += 1
            return
 
        # Pruning: remaining letters fewer than minimum word length
        if remaining_count < min_word_len:
            return
 
        seen_this_level = set()
        for word in usable:
            if word in seen_this_level:
                continue
            if len(word) > remaining_count:
                continue
            if can_form(word, remaining_letters):
                seen_this_level.add(word)
                new_remaining = subtract_letters(remaining_letters, word)
                # Remove zero counts for efficiency
                new_remaining = {k: v for k, v in new_remaining.items() if v > 0}
                search(new_remaining, current_phrase + [word])
 
    search(dict(available), [])
    elapsed = time.time() - start_time
 
    # Convert to sorted phrase strings
    phrases = [" ".join(r) for r in results]
 
    # Score and sort results
    phrases.sort(key=lambda p: score_phrase(p))
 
    return phrases, elapsed, stats
 
 
# ─────────────────────────────────────────────────────────────────────────────
# QUALITY SCORING
# Lower score = more meaningful/readable phrase
# ─────────────────────────────────────────────────────────────────────────────
 
# Words that reduce phrase quality (fragments, low-meaning syllables)
WEAK_WORDS = {
    'nap', 'yap', 'yam', 'pry', 'cob', 'dab', 'hoon', 'roly', 'poly',
    'moly', 'ploy', 'plod', 'holm', 'loam', 'mar', 'nab', 'orb', 'rob',
    'sob', 'lob', 'mob', 'bro', 'boa', 'arc', 'bod', 'cod', 'coy',
    'mocha', 'lorn', 'yap', 'yam', 'hay', 'nay', 'ray', 'bay', 'say',
    'pay', 'may', 'lay', 'lap', 'cap', 'rap', 'sap', 'gap', 'cab',
    'lab', 'nab', 'tab', 'pro', 'pry', 'dry', 'ploy', 'poly', 'plod',
    'cord', 'morn', 'hoard', 'bard', 'roan', 'dory', 'boon',
}
 
# Words that increase phrase quality
STRONG_WORDS = {
    'harmony', 'anchor', 'hymnal', 'body', 'bold', 'broad', 'broadly',
    'charm', 'holy', 'honor', 'honorably', 'hardly', 'blood', 'bloom',
    'lord', 'manor', 'born', 'bond', 'balm', 'calm', 'palm', 'royal',
    'loyal', 'moral', 'land', 'lore', 'road', 'door', 'hymn',
    'arm', 'band', 'barn', 'adorn', 'carol', 'nobody', 'somebody',
    'adorably', 'adorable', 'adornably', 'adorned', 'normal', 'random',
    'randomly', 'broadly', 'hardly', 'maroon', 'harbor', 'nomad',
    'dolor', 'dolors', 'melody', 'moral', 'colony', 'balcony',
}
 
 
def score_phrase(phrase):
    """
    Score a phrase for readability and meaning.
    Lower = better.
    """
    words = phrase.split()
    word_count = len(words)
    weak_penalty = sum(3 for w in words if w in WEAK_WORDS)
    strong_bonus = sum(5 for w in words if w in STRONG_WORDS)
    avg_len = sum(len(w) for w in words) / word_count if words else 0
    # Prefer fewer words, stronger words, longer average word length
    return (weak_penalty - strong_bonus) + word_count - avg_len
 
 
# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────────────────────────────────────────
 
def display_results(target, phrases, elapsed, stats, top_n=40):
    """Print results in a readable format."""
    total_letters = len(target.replace(" ", "").replace("-", ""))
 
    print()
    print("╔" + "═" * 58 + "╗")
    print(f"║  ARS MAGNA — Complete Anagram Solver" + " " * 21 + "║")
    print("╠" + "═" * 58 + "╣")
    print(f"║  Target : {target:<47}║")
    print(f"║  Letters: {total_letters:<47}║")
    print(f"║  Time   : {elapsed:.2f}s ({stats['calls']:,} nodes searched)" +
          " " * max(0, 20 - len(f"{elapsed:.2f}s ({stats['calls']:,} nodes searched)")) + "║")
    print(f"║  Found  : {len(phrases)} complete anagrams" +
          " " * max(0, 36 - len(f"{len(phrases)} complete anagrams")) + "║")
    print("╚" + "═" * 58 + "╝")
 
    if not phrases:
        print("\n  No complete anagrams found within time limit.")
        print("  Try: increasing --time, decreasing --min-word,")
        print("       or adding words to the VOCABULARY list.")
        return
 
    print(f"\n  Top {min(top_n, len(phrases))} results (ranked by readability):\n")
    for i, phrase in enumerate(phrases[:top_n], 1):
        words = phrase.split()
        # Capitalize for display
        display = " ".join(w.capitalize() for w in words)
        print(f"  {i:3}. {display}")
 
    if len(phrases) > top_n:
        print(f"\n  ... and {len(phrases) - top_n} more.")
 
    print()
    print("  ★  Top candidate:")
    best = phrases[0].split()
    print(f"     \"{' '.join(w.capitalize() for w in best)}\"")
    print()
 
 
# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
 
def main():
    parser = argparse.ArgumentParser(
        description="Ars Magna: Find all complete anagrams of a name or phrase.",
        epilog="Example: python3 ars_magna.py \"DYMPHNA BARLOCO\" --time 10"
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="DYMPHNA BARLOCO",
        help="The name or phrase to anagram (default: DYMPHNA BARLOCO)"
    )
    parser.add_argument(
        "--time", "-t",
        type=float,
        default=9.0,
        help="Time limit in seconds (default: 9.0)"
    )
    parser.add_argument(
        "--min-word", "-m",
        type=int,
        default=2,
        help="Minimum word length (default: 2)"
    )
    parser.add_argument(
        "--max-words", "-w",
        type=int,
        default=7,
        help="Maximum words in result phrase (default: 7)"
    )
    parser.add_argument(
        "--top", "-n",
        type=int,
        default=40,
        help="How many results to display (default: 40)"
    )
 
    args = parser.parse_args()
 
    word_list = build_word_list(VOCABULARY, min_len=args.min_word)
 
    print(f"\n  Searching '{args.target}'...")
    print(f"  Vocabulary: {len(word_list)} words | "
          f"Time limit: {args.time}s | "
          f"Min word: {args.min_word} letters")
 
    phrases, elapsed, stats = solve(
        args.target,
        word_list,
        time_limit=args.time,
        min_word_len=args.min_word,
        max_words=args.max_words
    )
 
    display_results(args.target, phrases, elapsed, stats, top_n=args.top)
 
 
if __name__ == "__main__":
    main()
 
