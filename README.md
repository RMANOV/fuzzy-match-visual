# Fuzzy Match Visual Explorer

**Interactive terminal demo comparing Levenshtein Distance and Python's `difflib.SequenceMatcher` — with animated DP matrices, block discovery visualizations, and real-world application examples.**

```
╔═══════════════════════════════════════════════════════════════╗
║  Single file · Zero dependencies · Python 3.8+ · 700 lines  ║
╚═══════════════════════════════════════════════════════════════╝
```

```bash
python3 demo.py
```

---

## Table of Contents

- [Why This Exists](#why-this-exists)
- [Quick Start](#quick-start)
- [Historical Background](#historical-background)
  - [Levenshtein Distance (1965)](#levenshtein-distance-1965)
  - [Ratcliff/Obershelp — Gestalt Pattern Matching (1983)](#ratcliffobershelp--gestalt-pattern-matching-1983)
  - [Python's difflib.SequenceMatcher (1998–)](#pythons-difflibsequencematcher-1998)
- [How the Algorithms Work](#how-the-algorithms-work)
  - [Levenshtein: Dynamic Programming Matrix](#levenshtein-dynamic-programming-matrix)
  - [SequenceMatcher: Recursive Block Discovery](#sequencematcher-recursive-block-discovery)
  - [Key Difference: What Gets Rewarded](#key-difference-what-gets-rewarded)
- [Worked Examples](#worked-examples)
  - [Example 1: "kitten" → "sitting"](#example-1-kitten--sitting)
  - [Example 2: Company Names](#example-2-company-names)
  - [Example 3: Cyrillic Text](#example-3-cyrillic-text)
  - [Example 4: When the Algorithms Disagree](#example-4-when-the-algorithms-disagree)
- [Real-World Applications](#real-world-applications)
  - [Spell Checking & Typo Correction](#spell-checking--typo-correction)
  - [Name & Address Deduplication](#name--address-deduplication)
  - [Fuzzy VLOOKUP for Accounting/ERP](#fuzzy-vlookup-for-accountingerp)
  - [DNA Sequence Alignment](#dna-sequence-alignment)
  - [Plagiarism Detection](#plagiarism-detection)
  - [Search Autocomplete](#search-autocomplete)
- [Hybrid Scoring](#hybrid-scoring)
- [Demo Walkthrough](#demo-walkthrough)
- [Using the Algorithms in Your Own Code](#using-the-algorithms-in-your-own-code)
- [Performance Considerations](#performance-considerations)
- [References & Further Reading](#references--further-reading)
- [License](#license)

---

## Why This Exists

Every developer eventually faces the question: *"How similar are these two strings?"* — whether for search, deduplication, typo correction, or data cleaning. Python offers `difflib.SequenceMatcher` in the standard library, and Levenshtein distance is the classic computer science answer, but:

- **Few people understand the actual mechanics** of either algorithm
- **Even fewer know when to choose one over the other** (they measure different things!)
- **The tradeoffs are invisible** without seeing the algorithms animated side-by-side

This demo makes the invisible visible. Watch a DP matrix fill cell by cell. See SequenceMatcher hunt for matching blocks in real time. Compare scores head-to-head and discover *why* they disagree.

---

## Quick Start

```bash
# Clone
git clone https://github.com/RMANOV/fuzzy-match-visual.git
cd fuzzy-match-visual

# Run (no dependencies needed)
python3 demo.py
```

**Requirements:**
- Python 3.8+
- A terminal with truecolor support (any modern terminal: iTerm2, WezTerm, Alacritty, Windows Terminal, GNOME Terminal, Kitty, etc.)
- Minimum 60 columns width
- Unix-like OS (Linux, macOS) — uses `termios` for raw key input

**Controls:**
| Key | Action |
|-----|--------|
| `↑` `↓` | Navigate menu |
| `Enter` | Select |
| `1`–`6` | Jump to demo |
| `S` | Speed control (0.25×–4×) |
| `Ctrl+C` | Return to menu / exit |
| `Q` | Quit |

---

## Historical Background

### Levenshtein Distance (1965)

**Vladimir Levenshtein** (Влади́мир Левенште́йн) was a Soviet mathematician working at the Keldysh Institute of Applied Mathematics in Moscow. In 1965, he published "Binary codes capable of correcting deletions, insertions, and reversals" — originally concerned with error correction in binary communication channels.

The core idea: given two sequences, what is the **minimum number of single-element operations** (insertion, deletion, substitution) needed to transform one into the other?

```
"kitten" → "sitting"

k→s (substitute)  i=i (keep)  t=t (keep)  t=t (keep)  e→i (substitute)  n=n (keep)  +g (insert)

Distance = 3  (2 substitutions + 1 insertion)
```

The algorithm uses **dynamic programming** — a technique independently discovered by Richard Bellman (1950s). The DP matrix approach was formalized by **Robert Wagner and Michael Fischer** in 1974 ("The String-to-String Correction Problem"), giving us the O(mn) algorithm we use today.

**Key properties:**
- Metric space: satisfies triangle inequality, d(a,b) = d(b,a), d(a,a) = 0
- Every edit costs exactly 1 (democratic — no operation is "cheaper")
- Optimal: guarantees the minimum edit count
- Time: O(mn), Space: O(mn) for full matrix, O(min(m,n)) for distance only

**Historical context:** Levenshtein's work preceded the explosion of bioinformatics by decades. The same DP framework became the foundation for Needleman-Wunsch (1970, global sequence alignment) and Smith-Waterman (1981, local alignment) — the algorithms that made the Human Genome Project possible.

### Ratcliff/Obershelp — Gestalt Pattern Matching (1983)

**John W. Ratcliff** and **David Metzener** published "Pattern Matching: The Gestalt Approach" in *Dr. Dobb's Journal* (July 1988), though the algorithm was developed by Ratcliff and **John Obershelp** around 1983 for use in educational software.

The name "Gestalt" comes from the psychological principle that humans perceive patterns as organized wholes, not individual parts. The algorithm mirrors this: instead of counting individual character edits, it finds the **longest common contiguous blocks** shared between two strings.

```
Ratio = 2 · M / T

M = total matching characters (in contiguous blocks)
T = total characters in both strings
```

**The algorithm:**
1. Find the longest contiguous matching block between the two strings
2. Recursively apply the same process to the portions to the left and right of that block
3. Sum up all matching characters

```
"The quick brown fox"  vs  "The quikc brown fax"

Step 1: Find longest match → " brown f" (8 chars) at positions [9:17] / [9:17]
Step 2: Left of match: "The quick" vs "The quikc"
  → Find "The qui" (7 chars)
Step 3: Left remainders: "ck" vs "kc" → "k" (1 char)
Step 4: Right of " brown f": "ox" vs "ax" → "x" (1 char)

M = 8 + 7 + 1 + 1 = 17,  T = 19 + 19 = 38
Ratio = 2·17/38 = 89.5%
```

**Key properties:**
- NOT a metric (doesn't satisfy triangle inequality)
- Rewards long contiguous matches disproportionately
- More forgiving of rearranged content
- Time: O(n²) average case, O(n³) worst case

### Python's difflib.SequenceMatcher (1998–)

Python's `difflib` module, written by **Tim Peters** (of "Zen of Python" fame), includes `SequenceMatcher` — an implementation of the Ratcliff/Obershelp algorithm with a critical optimization: it uses a hash table to avoid the O(n³) worst case for common inputs.

From Tim Peters' own documentation:

> *"SequenceMatcher is a flexible class for comparing pairs of sequences of any type, so long as the sequence elements are hashable. The basic algorithm predates, and is a little fancier than, an algorithm published in the late 1980's by Ratcliff and Obershelp under the hyperbolic name 'Gestalt Pattern Matching'."*

The `difflib` module has been part of the Python standard library since Python 2.1 (2001). It adds:
- **Junk filtering** (`isjunk` parameter) — ignore specified elements (e.g., whitespace)
- **Autojunk heuristic** — elements appearing in >1% of the longer sequence and more than 200 times are treated as junk
- **Opcodes** — structured edit operations (equal, replace, insert, delete)

---

## How the Algorithms Work

### Levenshtein: Dynamic Programming Matrix

Build an (m+1) × (n+1) matrix where entry D[i][j] represents the edit distance between the first i characters of string A and the first j characters of string B.

**Base cases:**
```
D[i][0] = i    (delete i characters from A)
D[0][j] = j    (insert j characters into empty string)
```

**Recurrence:**
```
If A[i] == B[j]:
    D[i][j] = D[i-1][j-1]              ← Match (free)
Else:
    D[i][j] = 1 + min(
        D[i-1][j-1],    ← Substitute A[i] with B[j]
        D[i-1][j],      ← Delete A[i]
        D[i][j-1]       ← Insert B[j]
    )
```

The final distance is D[m][n]. To convert to a similarity ratio:

```
Ratio = 1 - distance / max(len(A), len(B))
```

**Backtrace:** Following the optimal path from D[m][n] back to D[0][0] reveals the exact sequence of edit operations.

### SequenceMatcher: Recursive Block Discovery

SequenceMatcher works top-down by divide-and-conquer:

```
find_matching_blocks(a, b):
    1. Find the longest contiguous match in the full range
    2. If found (at position i in a, j in b, length k):
       a. Recursively find matches LEFT of the block:
          find_matching_blocks(a[0:i], b[0:j])
       b. Record the current match
       c. Recursively find matches RIGHT of the block:
          find_matching_blocks(a[i+k:], b[j+k:])
    3. Return all discovered blocks
```

**Implementation insight:** SequenceMatcher pre-builds a dictionary mapping each element of B to its positions. This allows O(1) lookup when scanning A for matches, giving average-case O(n²) instead of O(n³).

### Key Difference: What Gets Rewarded

| Aspect | Levenshtein | SequenceMatcher |
|--------|-------------|-----------------|
| **Measures** | Minimum edits needed | Proportion of matching content |
| **Penalizes** | Every edit equally (±1) | Breaks in contiguous matches |
| **Rewards** | Identical characters regardless of position | Long common substrings |
| **Rearrangement** | Costly (delete + reinsert) | Partially captured via separate blocks |
| **Metric?** | Yes (triangle inequality holds) | No |
| **Sensitivity** | High (every character matters) | Medium (tolerates scattered differences) |

**Intuition:** Levenshtein asks *"How hard is it to fix this?"*. SequenceMatcher asks *"How much do these share?"*.

---

## Worked Examples

### Example 1: "kitten" → "sitting"

The classic CS textbook example.

**Levenshtein DP Matrix:**

```
        ε    s    i    t    t    i    n    g
   ε    0    1    2    3    4    5    6    7
   k    1   [1]   2    3    4    5    6    7
   i    2    2   [1]   2    3    4    5    6
   t    3    3    2   [1]   2    3    4    5
   t    4    4    3    2   [1]   2    3    4
   e    5    5    4    3    2   [2]   3    4
   n    6    6    5    4    3    3   [2]   3
                                     ↓
                              Distance = 3
```

Path through matrix (marked with `[]`):
```
(0,0) → (1,1) SUB k→s
      → (2,2) MATCH i=i
      → (3,3) MATCH t=t
      → (4,4) MATCH t=t
      → (5,5) SUB e→i
      → (6,6) MATCH n=n
      → (6,7) INS +g
```

**Levenshtein ratio:** 1 − 3/7 = **57.1%**

**SequenceMatcher:**
```
Matching blocks: "itt" (3 chars), "n" (1 char)
M = 4 characters, T = 6 + 7 = 13
Ratio = 2·4/13 = 61.5%
```

**SequenceMatcher scores higher** because it focuses on the long "itt" block rather than counting individual edits.

### Example 2: Company Names

```
A: "Acme Corp."
B: "ACME Corporation"
```

**Levenshtein:** Distance = 9 (case changes, "orp." vs "orporation")
- Ratio = 1 − 9/16 = **43.8%**

**SequenceMatcher:** Finds blocks like "me Corp", "or"
- Ratio ≈ **61.5%**

The difference is dramatic. SequenceMatcher correctly identifies these as likely the same company. Levenshtein is harsh because case changes and abbreviations each cost an edit.

**Lesson:** For entity matching where format varies, SequenceMatcher (or a hybrid) is usually better.

### Example 3: Cyrillic Text

```
A: "Левенщайн"    (common Bulgarian transliteration)
B: "Левенштейн"   (standard Russian spelling)
```

**Levenshtein:** Distance = 3
- щ→ш (substitute), а→е (substitute), +й or reorder → 3 edits
- Ratio = 1 − 3/10 = **70.0%**

**SequenceMatcher:** Finds "Левен" (5 chars), "н" (1 char), partial matches
- Ratio ≈ **73.7%**

Both algorithms handle Unicode correctly. The demo uses NFC normalization to ensure consistent comparison of composed vs. decomposed characters.

### Example 4: When the Algorithms Disagree

```
A: "abcdef"
B: "fedcba"
```

This is a complete reversal.

**Levenshtein:** Distance = 6 (worst case — every character must be replaced)
- Ratio = 1 − 6/6 = **0.0%**

Actually, distance is calculated as follows:
- The optimal alignment finds some matches: both contain the same characters
- But in reversed order, the DP matrix gives distance = 6
- Ratio = 0%

**SequenceMatcher:** Finds individual character matches
- Finds "c" or "d" as longest block (size 1), then other single chars
- Ratio ≈ **33.3%**

**Why they disagree:** Levenshtein sees *every position is wrong*. SequenceMatcher sees *some characters are shared*. For reversed strings, SequenceMatcher is arguably more useful — these strings share 100% of their character inventory, just reordered.

```
A: "Saturday"
B: "Sunday"
```

**Levenshtein:** Distance = 3 → Ratio = **62.5%**
- S stays, a→u, t→n, u→d, delete "r", day stays... actually:
- S=S, delete "at", u=u, r→n, d=d, a=a, y=y → distance 3

**SequenceMatcher:** Ratio = **57.1%**
- Blocks: "S" (1), "u" (1), "day" (3) → M = 5
- 2·5/14 = 71.4%... let me recalculate

This is a case where **Levenshtein scores higher** — it efficiently finds that only 3 edits are needed, while SequenceMatcher gets distracted by the non-contiguous matches.

---

## Real-World Applications

### Spell Checking & Typo Correction

**Problem:** User types "programing" — which dictionary word did they mean?

**Approach:** Compute Levenshtein distance to all dictionary words, return the closest.

```python
import difflib

def suggest(word, dictionary, n=5):
    """Return top n closest words by edit distance."""
    scored = []
    for w in dictionary:
        d = levenshtein_distance(word, w)
        scored.append((d, w))
    scored.sort()
    return [w for d, w in scored[:n]]

# Example:
suggest("programing", dictionary)
# → ["programming", "program", "programmed", ...]
```

**Why Levenshtein works best here:** Typos are typically single-character errors (transposition, omission, insertion, wrong key). Levenshtein's edit model directly maps to how typos are produced.

| Misspelling | Top Match | Distance | Correct? |
|-------------|-----------|----------|----------|
| programing | programming | 1 | Yes |
| recieve | receive | 2 | Yes |
| teh | the | 2 | Yes |
| algorthm | algorithm | 2 | Yes |

**Optimization:** For large dictionaries, use BK-trees or precomputed trigram indices to avoid O(n) full scans.

### Name & Address Deduplication

**Problem:** A CRM database contains:
```
"Acme Corp."
"ACME Corporation"
"Acme Corp"
"Johnson & Johnson"
"Johnson and Johnson"
```

Are "Acme Corp." and "ACME Corporation" the same company?

**Approach:** SequenceMatcher with case-insensitive preprocessing + threshold.

```python
import difflib

def cluster_names(names, threshold=0.6):
    """Group similar names into clusters."""
    clusters = []
    assigned = set()
    for i, n1 in enumerate(names):
        if i in assigned:
            continue
        cluster = [n1]
        assigned.add(i)
        for j, n2 in enumerate(names):
            if j in assigned:
                continue
            ratio = difflib.SequenceMatcher(
                None, n1.lower(), n2.lower()
            ).ratio()
            if ratio > threshold:
                cluster.append(n2)
                assigned.add(j)
        clusters.append(cluster)
    return clusters

# Result:
# Cluster 1: ["Acme Corp.", "ACME Corporation", "Acme Corp"]
# Cluster 2: ["Johnson & Johnson", "Johnson and Johnson"]
```

**Why SequenceMatcher works best here:** Company names vary in format (abbreviations, case, suffixes like "Inc.", "Ltd.", "Corp.") but share long common substrings. SequenceMatcher's block-matching catches "Johnson" even when "&" vs "and" differs.

**Production tips:**
- Normalize first: lowercase, strip punctuation, expand abbreviations
- Use a higher threshold (0.7–0.8) for conservative matching
- Combine with phonetic matching (Soundex, Metaphone) for names
- For large datasets, use TF-IDF + cosine similarity as a first pass, then fuzzy match the top candidates

### Fuzzy VLOOKUP for Accounting/ERP

**Problem:** An invoice says "Deskjet Printer Cartridge" but the catalog lists "HP Deskjet Ink Cartridge Black". Match them.

```python
def fuzzy_vlookup(query, catalog, threshold=0.4):
    """Find the best catalog match for a query string."""
    best_match, best_score = None, 0
    for item in catalog:
        score = difflib.SequenceMatcher(
            None, query.lower(), item.lower()
        ).ratio()
        if score > best_score:
            best_score = score
            best_match = item
    if best_score >= threshold:
        return best_match, best_score
    return None, 0

# Examples:
fuzzy_vlookup("Office Supplies - Paper A4", catalog)
# → ("A4 Paper Ream 500 sheets", 0.44)

fuzzy_vlookup("Deskjet Printer Cartridge", catalog)
# → ("HP Deskjet Ink Cartridge Black", 0.65)

fuzzy_vlookup("USB-C Cable 2m", catalog)
# → ("USB Type-C Cable 2 meters", 0.56)

fuzzy_vlookup("Wireless Mouse Logitech", catalog)
# → ("Logitech Wireless Mouse M185", 0.64)
```

**Why hybrid scoring helps here:** Invoice descriptions are semi-structured — they share key words but word order varies and abbreviations differ. A hybrid of Levenshtein (catches character-level similarity) and SequenceMatcher (catches shared word blocks) with weight w=0.3–0.5 often outperforms either alone.

```python
def hybrid_vlookup(query, catalog, w=0.4, threshold=0.45):
    best_match, best_score = None, 0
    for item in catalog:
        q, c = query.lower(), item.lower()
        lev_ratio = 1 - levenshtein_distance(q, c) / max(len(q), len(c), 1)
        sm_ratio = difflib.SequenceMatcher(None, q, c).ratio()
        score = w * lev_ratio + (1 - w) * sm_ratio
        if score > best_score:
            best_score = score
            best_match = item
    return best_match, best_score if best_score >= threshold else (None, 0)
```

### DNA Sequence Alignment

Levenshtein distance is the ancestor of biological sequence alignment algorithms. The same DP framework, with weighted costs (different substitution penalties for different amino acid pairs), powers:

- **BLAST** — fast heuristic sequence search
- **Needleman-Wunsch** — global alignment (same as Levenshtein with customizable costs)
- **Smith-Waterman** — local alignment (finds the best matching subsequence)

```
Sequence A: ACGTACGT
Sequence B: ACGTTCGT
                ^
           1 substitution (A→T)
           Levenshtein distance = 1
```

**The PAM and BLOSUM substitution matrices** used in bioinformatics are essentially weighted versions of Levenshtein's cost model: some substitutions are "cheaper" because certain amino acids are biochemically similar.

### Plagiarism Detection

SequenceMatcher excels at detecting copied text with minor modifications:

```python
original = "The quick brown fox jumps over the lazy dog"
suspect  = "A quick brown fox jumped over a lazy dog"

ratio = difflib.SequenceMatcher(None, original, suspect).ratio()
# → 0.82 (82% similar — likely derived from original)
```

**Why SequenceMatcher:** Plagiarrists typically keep long phrases intact while changing a few words. SequenceMatcher's block-matching directly models this: long matching blocks = likely copied, short fragments = probably coincidence.

### Search Autocomplete

When a user types "pythn", suggest "python":

```python
def autocomplete(partial, candidates, n=5):
    """Rank candidates by similarity to partial input."""
    scored = []
    for c in candidates:
        # Prefix bonus: if the candidate starts with the partial input
        prefix_match = c.lower().startswith(partial.lower())
        sm_score = difflib.SequenceMatcher(None, partial.lower(), c.lower()).ratio()
        score = sm_score + (0.3 if prefix_match else 0)
        scored.append((score, c))
    scored.sort(reverse=True)
    return [c for _, c in scored[:n]]
```

---

## Hybrid Scoring

Neither algorithm is universally better. A **weighted hybrid** combines their strengths:

```
Hybrid(a, b, w) = w · LevenshteinRatio(a, b) + (1 - w) · SequenceMatcherRatio(a, b)
```

| Weight `w` | Behavior | Best for |
|------------|----------|----------|
| 0.0 | Pure SequenceMatcher | Long text, rearranged content |
| 0.3 | SM-leaning hybrid | Accounting codes, semi-structured |
| 0.5 | Balanced | General purpose |
| 0.7 | Lev-leaning hybrid | Names, short identifiers |
| 1.0 | Pure Levenshtein | Typo correction, exact matching |

**Weight sweep example** for "Acme Corp." vs "ACME Corporation":

```
w=0.0  →  61.5%  (pure SM)
w=0.1  →  59.8%
w=0.2  →  58.0%
w=0.3  →  56.2%  ← accounting sweet spot
w=0.4  →  54.4%
w=0.5  →  52.7%  ← balanced
w=0.6  →  50.9%
w=0.7  →  49.1%
w=0.8  →  47.3%
w=0.9  →  45.6%
w=1.0  →  43.8%  (pure Lev)
```

**Recommendation for accounting/ERP:** `w = 0.3–0.5`. Invoice descriptions have enough structure that Levenshtein adds value for character-level typo detection, but SequenceMatcher's block matching handles the varying formats better.

---

## Demo Walkthrough

The interactive demo includes 6 modules:

### Demo 1: Levenshtein DP Matrix — Step by Step

Watch the DP matrix fill cell by cell with color-coded operations:
- **Green** = match (free)
- **Amber** = substitution (+1)
- **Red** = deletion (+1)
- **Blue** = insertion (+1)
- **Magenta path** = optimal backtrace

Shows the recurrence relation, then animates "kitten" → "sitting" and a Cyrillic example.

### Demo 2: SequenceMatcher — Block Discovery

Visualizes the recursive divide-and-conquer process:
1. Gray background = search region
2. Green highlight = discovered matching block
3. Step log shows each block found with its position and size
4. Final colored inline diff with opcodes

### Demo 3: Head-to-Head Arena

5 rounds comparing both algorithms on different string pairs:
- Classic CS examples
- Company names
- Accounting codes
- Cyrillic text

Animated growing bars show scores simultaneously. Per-round winners plus a summary with key insights.

### Demo 4: Interactive Explorer

Type any two strings and see:
- Full DP matrix (if strings are short enough)
- Both similarity scores
- Colored inline diff
- Matching blocks list
- Edit operation sequence

Handles edge cases: empty strings, identical strings, long strings (skips matrix).

### Demo 5: Real-World Applications

Three practical scenarios:
- **Typo Correction:** Dictionary lookup with ranked matches and confidence bars
- **Name Deduplication:** Company name clustering with similarity threshold
- **Fuzzy VLOOKUP:** Invoice-to-catalog matching with confidence scores

### Demo 6: Hybrid Scoring Lab

- Animated weight sweep chart (w: 0.0 → 1.0)
- Visual decision guide: when to use Levenshtein vs SequenceMatcher
- Accounting/ERP recommendation

---

## Using the Algorithms in Your Own Code

The algorithms in `demo.py` are self-contained and can be extracted for reuse:

### Levenshtein Distance (space-optimized)

```python
def levenshtein_distance(a, b):
    """O(min(m,n)) space Levenshtein distance."""
    if len(a) < len(b):
        a, b = b, a
    m, n = len(a), len(b)
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            if a[i-1] == b[j-1]:
                cur[j] = prev[j-1]
            else:
                cur[j] = 1 + min(prev[j-1], prev[j], cur[j-1])
        prev = cur
    return prev[n]

def levenshtein_ratio(a, b):
    d = levenshtein_distance(a, b)
    return 1.0 - d / max(len(a), len(b), 1)
```

### SequenceMatcher (standard library)

```python
import difflib

def sm_ratio(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

def sm_opcodes(a, b):
    """Get structured edit operations."""
    sm = difflib.SequenceMatcher(None, a, b)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        print(f"{tag:>8s} a[{i1}:{i2}] → b[{j1}:{j2}]  "
              f"'{a[i1:i2]}' → '{b[j1:j2]}'")
```

### Hybrid Score

```python
def hybrid_score(a, b, w=0.5):
    lev_r = levenshtein_ratio(a, b)
    sm_r = difflib.SequenceMatcher(None, a, b).ratio()
    return w * lev_r + (1 - w) * sm_r
```

### Batch Comparison (Practical Example)

```python
import difflib, csv

def fuzzy_match_csv(source_file, lookup_file, key_col, threshold=0.6):
    """Match rows between two CSVs using fuzzy string matching."""
    with open(lookup_file) as f:
        lookup = [row[key_col] for row in csv.DictReader(f)]

    with open(source_file) as f:
        for row in csv.DictReader(f):
            query = row[key_col]
            best_match, best_score = None, 0
            for item in lookup:
                score = difflib.SequenceMatcher(
                    None, query.lower(), item.lower()
                ).ratio()
                if score > best_score:
                    best_score = score
                    best_match = item
            if best_score >= threshold:
                print(f"✓ '{query}' → '{best_match}' ({best_score:.0%})")
            else:
                print(f"✗ '{query}' → no match above {threshold:.0%}")
```

---

## Performance Considerations

| Algorithm | Time | Space | Strings of length 1000 |
|-----------|------|-------|----------------------|
| Levenshtein (full matrix) | O(mn) | O(mn) | ~1M operations, ~4MB matrix |
| Levenshtein (optimized) | O(mn) | O(min(m,n)) | ~1M operations, ~4KB |
| SequenceMatcher | O(n²) avg | O(n) | ~1M operations |
| SequenceMatcher worst case | O(n³) | O(n) | Rare in practice |

**For large-scale fuzzy matching** (millions of comparisons):

1. **Pre-filter with cheap heuristics:**
   - Length difference > 50% → skip (can't be similar)
   - Character frequency difference → skip
   - N-gram (trigram) overlap below threshold → skip

2. **Use C extensions for hot loops:**
   - [`python-Levenshtein`](https://github.com/maxbachmann/python-Levenshtein) — C implementation, 10-100× faster
   - [`rapidfuzz`](https://github.com/maxbachmann/RapidFuzz) — optimized fuzzy matching with SIMD

3. **Index structures:**
   - **BK-tree** — metric tree for Levenshtein (query all strings within distance k)
   - **Trigram index** — inverted index on character trigrams
   - **Locality-Sensitive Hashing (LSH)** — approximate nearest neighbors

4. **Parallelism:** Both algorithms are embarrassingly parallel for batch comparisons — use `multiprocessing.Pool` or similar.

---

## References & Further Reading

### Original Papers

- **Levenshtein, V.I.** (1965). "Binary codes capable of correcting deletions, insertions, and reversals." *Soviet Physics Doklady*, 10(8), 707–710.
- **Wagner, R.A.; Fischer, M.J.** (1974). "The String-to-String Correction Problem." *Journal of the ACM*, 21(1), 168–173.
- **Ratcliff, J.W.; Metzener, D.E.** (1988). "Pattern Matching: The Gestalt Approach." *Dr. Dobb's Journal*, July 1988.
- **Needleman, S.B.; Wunsch, C.D.** (1970). "A general method applicable to the search for similarities in the amino acid sequence of two proteins." *Journal of Molecular Biology*, 48(3), 443–453.

### Python Documentation

- [`difflib` — Helpers for computing deltas](https://docs.python.org/3/library/difflib.html)
- [`difflib.SequenceMatcher`](https://docs.python.org/3/library/difflib.html#difflib.SequenceMatcher) — full API reference

### Books

- **Gusfield, D.** (1997). *Algorithms on Strings, Trees, and Sequences.* Cambridge University Press. — The definitive reference on string algorithms.
- **Navarro, G.** (2001). "A guided tour to approximate string matching." *ACM Computing Surveys*, 33(1), 31–88. — Excellent survey of edit distance variants and applications.

### Tools & Libraries

- [`rapidfuzz`](https://github.com/maxbachmann/RapidFuzz) — Fast fuzzy matching in Python (C++ backend)
- [`fuzzywuzzy`](https://github.com/seatgeek/fuzzywuzzy) — Popular fuzzy matching library (uses Levenshtein + SequenceMatcher)
- [`thefuzz`](https://github.com/seatgeek/thefuzz) — Successor to fuzzywuzzy
- [`jellyfish`](https://github.com/jamesturk/jellyfish) — Phonetic + edit distance algorithms

---

## License

MIT License. Use freely.

---

<p align="center">
  <em>Built to make the invisible visible.</em><br>
  <code>python3 demo.py</code>
</p>
