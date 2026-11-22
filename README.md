# Ars Magna

A complete-anagram solver: finds phrases that use **every letter** of a name exactly once.

Named for Michael Morton (Apple, Google), who introduced the author to an early
anagram program called Ars Magna in the 1980s, and for Ramon Llull's 13th-century
combinatorial work of the same name.

## Run it

    python3 arsmagna.py "DYMPHNA BARLOCO" --min-word 3
    python3 arsmagna.py "STILL IN IT" --rich --must instill
    python3 arsmagna.py "YOUR NAME" --max-words 4 --time 20

Needs Python 3 and nothing else. On first run it downloads two word lists
(or uses `common.txt` / `words.txt` if they sit beside the script).

| Option | Meaning |
|---|---|
| `--rich` | also use the 370,000-word list (more results, more obscure words) |
| `--must w1 w2` | every phrase must contain one of these words |
| `--min-word N` | drop short filler words |
| `--max-words N` | longest phrase to build (default 4) |
| `--time S` | stop after S seconds (default 10) |

## How it works

At each step it picks the remaining letter that the fewest words contain and
branches only on words containing it, so it never re-finds the same phrase in
a different word order. Results are ranked by fewer words, longer words, and
more common words. It cannot judge meaning; that part is yours.

## Word lists

- `common.txt`: google-10000-english (first20hours), ranked by frequency
- `words.txt`: english-words `words_alpha.txt` (dwyl)

Check each project's license before redistributing the lists.

## Author

Stuart Alan Cooley, 2026.
