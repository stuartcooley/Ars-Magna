# Ars Magna

A complete-anagram solver: finds phrases that use **every letter** of a name exactly once.

Named for Michael Morton (Apple, Google), who introduced the author to an early
anagram program called Ars Magna in the 1980s, and for Ramon Llull's 13th-century
combinatorial work of the same name.

## Run it

    python3 arsmagna.py "STUART ALAN COOLEY" --max-words 4 --time 20
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

  ## Smart version: `arsmagna3.py`

Finds complete anagrams, puts each set of words into its best reading order, and ranks them
by how much they read like English. The top three are starred.

    python3 arsmagna3.py "STUART ALAN COOLEY"
    python3 arsmagna3.py "YOUR NAME" --best 3
    python3 arsmagna3.py "YOUR NAME" --slang --titles --time 20

Needs these files in the same folder: `arsmagna.py`, `arsmagna3.py`, `model.json.gz`,
`common.txt`, `words.txt` and (for `--slang`) `slang.json`.

### How it ranks
1. **Order:** every word order is tried; the best by grammar (noun, verb, adjective...) and
   word-pair likelihood is kept.
2. **Punctuation:** commas and hyphens are tried, so "Daily Low Dutch Rank" can become
   "Daily Dutch, Low-rank".
3. **Score:** fluent phrases with substantial words beat filler words and long word lists.
   The score measures fluency, not meaning. The final choice is yours.

### Guardrails relax automatically
If a search finds fewer than 5 anagrams, the program loosens up and says which level it used:

| Level | Words allowed |
|---|---|
| standard | 3+ letters, common in text, up to 4 words |
| relaxed | 2-letter words and rarer words |
| loose | full 370,000-word dictionary, up to 5 words |

`--strict` never relaxes. `--loose` starts there. `--min-results N` changes the threshold.

### Options
| Option | Meaning |
|---|---|
| `--best N` | how many results to show (default 10) |
| `--time S` | seconds of search per level (default 8) |
| `--slang` | allow text shorthand, slang, interjections and dialect from `slang.json` |
| `--add w1 w2` | extra words to allow |
| `--titles` | also try the name with Mr, Mrs, Ms, Miss, Dr, Don, Lord, Lady, Sir, AG, Jr, Sr, II |
| `--initial` | also try the name plus one middle initial |
| `--hide-self` | hide the name if it is an anagram of itself |
| `--no-punct` | switch off commas and hyphens |
| `--must w1 w2` | every phrase must contain one of these words |

### Slang is flagged
With `--slang`, any word from `slang.json` is flagged under its result with its kind and meaning:

    > SMH (text shorthand): shaking my head; disappointment or disbelief

`slang.json` holds curated entries with original definitions, not scraped from anywhere.
Add your own: each entry has a word (`w`), display spelling (`d`), kind (`k`), meaning (`m`)
and word type (`p`: N, V, ADJ, ADV, PREP, PRON, AUX, CONJ or X).

### Rebuilding the model
`python3 build_model.py` rebuilds `model.json.gz` from the Brown, Gutenberg and webtext
corpora. Check each corpus's license before redistributing the derived model.

Check each project's license before redistributing the lists.

## Author

Stuart Alan Cooley, 2026.
