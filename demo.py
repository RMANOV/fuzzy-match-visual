#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║  Fuzzy Match Visual Explorer                                  ║
║  Interactive Levenshtein vs difflib.SequenceMatcher demo      ║
║  Single file · Zero dependencies · Python 3.8+               ║
╚═══════════════════════════════════════════════════════════════╝
"""

import sys, os, time, math, colorsys, unicodedata, signal, termios, tty, difflib

# ════════════════════════════════════════════════════════════════════════════════
# §1  TERMINAL ENGINE
# ════════════════════════════════════════════════════════════════════════════════

SPEED = 1.0
TW, TH = 80, 24

def _rsz(*_):
    global TW, TH
    try: s = os.get_terminal_size(); TW, TH = s.columns, s.lines
    except OSError: pass

signal.signal(signal.SIGWINCH, _rsz); _rsz()

# -- ANSI --
def fg(r, g, b): return f"\033[38;2;{r};{g};{b}m"
def bg(r, g, b): return f"\033[48;2;{r};{g};{b}m"
RST = "\033[0m"; BLD = "\033[1m"; DIM = "\033[2m"
HIDE = "\033[?25l"; SHOW = "\033[?25h"
AON = "\033[?1049h"; AOFF = "\033[?1049l"
def at(r, c): return f"\033[{r};{c}H"
def cls(): sys.stdout.write("\033[2J\033[H"); sys.stdout.flush()
def W(*p): sys.stdout.write("".join(p)); sys.stdout.flush()
def sl(s): time.sleep(max(0, s / SPEED) if SPEED > 0 else s)

def dw(s):
    return sum(2 if unicodedata.east_asian_width(c) in ('F', 'W') else 1 for c in s)

def _hsv(h):
    r, g, b = colorsys.hsv_to_rgb(h % 1, 0.85, 1.0)
    return fg(int(r * 255), int(g * 255), int(b * 255))

def rainbow(text, row=None, col=None):
    buf = []
    if row is not None: buf.append(at(row, col))
    n = max(len(text), 1)
    for i, c in enumerate(text):
        buf.append(f"{_hsv(i / n)}{c}")
    buf.append(RST); W("".join(buf))

def typewr(text, row=None, col=None, d=0.015, clr=""):
    if row is not None: W(at(row, col))
    for c in text:
        W(f"{clr}{c}{RST}" if clr else c)
        if c.strip(): sl(d)

_HB = " ▏▎▍▌▋▊▉█"
def hbar(w, f, clr):
    f = max(0, min(1, f)); fl = int(f * w); p = int((f * w - fl) * 8)
    s = "█" * fl
    if fl < w: s += _HB[p] if p else " "; s += " " * (w - fl - 1)
    return f"{clr}{s}{RST}"

def bx(row, col, bw, bh, title="", dbl=False):
    tl, tr, bl, br, hz, vt = ("╔","╗","╚","╝","═","║") if dbl else ("┌","┐","└","┘","─","│")
    inn = bw - 2; top = hz * inn
    if title:
        t = f" {title} "; lp = (inn - len(t)) // 2
        top = hz * max(0, lp) + t + hz * max(0, inn - lp - len(t))
    buf = [f"{at(row, col)}{tl}{top}{tr}"]
    for i in range(1, bh - 1): buf.append(f"{at(row + i, col)}{vt}{' ' * inn}{vt}")
    buf.append(f"{at(row + bh - 1, col)}{bl}{hz * inn}{br}"); W("".join(buf))

def rkey():
    fd = sys.stdin.fileno(); old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd); c = sys.stdin.read(1)
        if c == '\x1b':
            c2 = sys.stdin.read(1)
            if c2 == '[':
                c3 = sys.stdin.read(1)
                return {'A': 'UP', 'B': 'DOWN', 'C': 'RIGHT', 'D': 'LEFT'}.get(c3, c3)
            return 'ESC'
        if c == '\x03': raise KeyboardInterrupt
        return 'ENTER' if c == '\r' else c
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def sinput(prompt=""):
    W(SHOW)
    try: return unicodedata.normalize('NFC', input(prompt))
    except (EOFError, KeyboardInterrupt): return ""
    finally: W(HIDE)

def pause(msg="Press any key to continue..."):
    W(f"\n  {DIM}{msg}{RST}"); rkey()

# ════════════════════════════════════════════════════════════════════════════════
# §2  ALGORITHMS
# ════════════════════════════════════════════════════════════════════════════════

def lev_full(a, b):
    """Full Levenshtein: DP matrix, operation tags, backtrace path."""
    m, n = len(a), len(b)
    D = [[0] * (n + 1) for _ in range(m + 1)]
    op = [[' '] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1): D[i][0] = i; op[i][0] = 'D'
    for j in range(1, n + 1): D[0][j] = j; op[0][j] = 'I'
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                D[i][j] = D[i - 1][j - 1]; op[i][j] = 'M'
            else:
                ch = [(D[i-1][j-1]+1, 'S'), (D[i-1][j]+1, 'D'), (D[i][j-1]+1, 'I')]
                D[i][j], op[i][j] = min(ch, key=lambda x: x[0])
    path = []; i, j = m, n
    while i > 0 or j > 0:
        path.append((i, j)); o = op[i][j]
        if o in ('M', 'S'): i -= 1; j -= 1
        elif o == 'D': i -= 1
        else: j -= 1
    path.append((0, 0)); path.reverse()
    dist = D[m][n]; mx = max(m, n, 1)
    return dict(dist=dist, ratio=1 - dist / mx, matrix=D, ops=op, path=path)

def lev_dist(a, b):
    """Space-optimized Levenshtein distance."""
    if len(a) < len(b): a, b = b, a
    m, n = len(a), len(b); prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cur[j] = prev[j-1] if a[i-1] == b[j-1] else 1 + min(prev[j-1], prev[j], cur[j-1])
        prev = cur
    return prev[n]

def sm_full(a, b):
    """SequenceMatcher with step-by-step block discovery simulation."""
    sm = difflib.SequenceMatcher(None, a, b)
    ratio = sm.ratio(); blocks = sm.get_matching_blocks(); opcodes = sm.get_opcodes()
    steps = []; q = [(0, len(a), 0, len(b))]
    while q:
        alo, ahi, blo, bhi = q.pop(0)
        m = sm.find_longest_match(alo, ahi, blo, bhi)
        if m.size == 0:
            steps.append(dict(region=(alo, ahi, blo, bhi), match=None)); continue
        steps.append(dict(region=(alo, ahi, blo, bhi), match=(m.a, m.b, m.size)))
        if alo < m.a and blo < m.b: q.append((alo, m.a, blo, m.b))
        if m.a + m.size < ahi and m.b + m.size < bhi:
            q.append((m.a + m.size, ahi, m.b + m.size, bhi))
    return dict(ratio=ratio, blocks=blocks, opcodes=opcodes, steps=steps)

def hybrid(a, b, w=0.5):
    lr = 1 - lev_dist(a, b) / max(len(a), len(b), 1)
    sr = difflib.SequenceMatcher(None, a, b).ratio()
    return w * lr + (1 - w) * sr

PAIRS = [
    ("kitten", "sitting", "Classic CS textbook"),
    ("Saturday", "Sunday", "Day names"),
    ("Acme Corp.", "ACME Corporation", "Company names"),
    ("Invoice #12345", "Inv. 12345", "Accounting codes"),
    ("Левенщайн", "Левенштейн", "Cyrillic: Levenshtein"),
    ("The quick brown fox", "The quikc brown fax", "Typo correction"),
    ("Robert Johnson", "Rob. Johnson Jr.", "Name variation"),
    ("algorithm", "altruistic", "Different words"),
]

# ════════════════════════════════════════════════════════════════════════════════
# §3  RENDERERS
# ════════════════════════════════════════════════════════════════════════════════

# Palette
CM  = fg(100, 255, 100)   # match
CS  = fg(255, 200, 50)    # substitute
CD  = fg(255, 80, 80)     # delete
CI  = fg(80, 150, 255)    # insert
CP  = bg(100, 50, 150)    # path
CHL = bg(60, 60, 80)      # cell highlight
BGM = bg(30, 80, 30);  BGD = bg(80, 30, 30)
BGI = bg(30, 30, 80);  BGS = bg(80, 60, 20)
BGHL = bg(50, 50, 70)
CLev = fg(80, 200, 255)   # Levenshtein color
CSm  = fg(255, 160, 80)   # SequenceMatcher color
CTT  = fg(255, 220, 100)  # title color

def _opcol(o):
    return {'M': CM, 'S': CS, 'D': CD, 'I': CI}.get(o, '')

def render_matrix(res, a, b, br=3, bc=3, cw=4, anim=True):
    """Draw DP matrix with optional cell-by-cell animation."""
    m, n = len(a), len(b)
    D, ops, pset = res['matrix'], res['ops'], set(res['path'])
    # Header row (string b)
    hdr = f"{at(br, bc)}{fg(200,200,255)}{'ε':>{cw}}"
    for j in range(n): hdr += f"{b[j]:>{cw}}"
    W(hdr + RST)
    # Fill matrix
    for i in range(m + 1):
        lb = a[i - 1] if i else "ε"
        W(f"{at(br + 1 + i, bc)}{fg(200,200,255)}{lb:>{cw}}{RST}")
        for j in range(n + 1):
            cp = bc + cw + j * cw; v = D[i][j]; o = ops[i][j]
            clr = _opcol(o); bgc = CP if (i, j) in pset else ""
            if anim and (i > 0 or j > 0):
                W(f"{at(br+1+i, cp)}{CHL}{v:>{cw}}{RST}"); sl(0.025)
            W(f"{at(br+1+i, cp)}{bgc}{clr}{v:>{cw}}{RST}")
    if anim:
        sl(0.2)
        for (i, j) in res['path']:
            cp = bc + cw + j * cw
            W(f"{at(br+1+i, cp)}{CP}{BLD}{_opcol(ops[i][j])}{D[i][j]:>{cw}}{RST}")
            sl(0.06)

def render_ops_inline(opcodes, a, b, row, col=3):
    """Render colored inline diff from opcodes."""
    la, lb = [], []
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'equal':
            la.append(f"{CM}{a[i1:i2]}{RST}"); lb.append(f"{CM}{b[j1:j2]}{RST}")
        elif tag == 'replace':
            la.append(f"{BGS}{CS}{a[i1:i2]}{RST}"); lb.append(f"{BGS}{CS}{b[j1:j2]}{RST}")
        elif tag == 'delete':
            la.append(f"{BGD}{CD}{a[i1:i2]}{RST}"); lb.append(f"{DIM}{'·'*(i2-i1)}{RST}")
        elif tag == 'insert':
            la.append(f"{DIM}{'·'*(j2-j1)}{RST}"); lb.append(f"{BGI}{CI}{b[j1:j2]}{RST}")
    W(f"{at(row, col)}  a: {''.join(la)}")
    W(f"{at(row+1, col)}  b: {''.join(lb)}")
    return row + 2

def render_bars(items, row, col=3, bw=30):
    """Render horizontal bars. items = [(label, frac, color), ...]"""
    for i, (label, frac, clr) in enumerate(items):
        W(f"{at(row+i, col)}{label:>20s} {hbar(bw, frac, clr)} {frac*100:5.1f}%")
    return row + len(items)

def render_blocks_anim(a, b, steps, row, col=3):
    """Animate SequenceMatcher block discovery on two string rows."""
    bcol = col + 5  # after "  a: " or "  b: "
    W(f"{at(row, col)}  a: {DIM}{a}{RST}")
    W(f"{at(row+1, col)}  b: {DIM}{b}{RST}")
    lr = row + 3; ma_set, mb_set = set(), set()
    for si, step in enumerate(steps):
        alo, ahi, blo, bhi = step['region']
        # Flash search region
        for idx in range(alo, min(ahi, len(a))):
            if idx not in ma_set: W(f"{at(row, bcol+idx)}{BGHL}{a[idx]}{RST}")
        for idx in range(blo, min(bhi, len(b))):
            if idx not in mb_set: W(f"{at(row+1, bcol+idx)}{BGHL}{b[idx]}{RST}")
        sl(0.35)
        # Remove highlight
        for idx in range(alo, min(ahi, len(a))):
            if idx not in ma_set: W(f"{at(row, bcol+idx)}{DIM}{a[idx]}{RST}")
        for idx in range(blo, min(bhi, len(b))):
            if idx not in mb_set: W(f"{at(row+1, bcol+idx)}{DIM}{b[idx]}{RST}")
        if step['match']:
            ma, mb, ms = step['match']; txt = a[ma:ma+ms]
            for off in range(ms):
                W(f"{at(row, bcol+ma+off)}{BGM}{CM}{a[ma+off]}{RST}")
                W(f"{at(row+1, bcol+mb+off)}{BGM}{CM}{b[mb+off]}{RST}")
                ma_set.add(ma + off); mb_set.add(mb + off); sl(0.03)
            W(f"{at(lr+si, col)}  {CM}Step {si+1}: found '{txt}' ({ms} ch) "
              f"a[{ma}:{ma+ms}] b[{mb}:{mb+ms}]{RST}")
        else:
            W(f"{at(lr+si, col)}  {CD}Step {si+1}: no match in region{RST}")
        sl(0.25)
    return lr + len(steps) + 1

def anim_bars(row, lr, sr, bw=30):
    """Animate two bars growing simultaneously."""
    for s in range(31):
        t = s / 30.0
        W(f"{at(row, 3)}{'Levenshtein':>18s} {hbar(bw, lr*t, CLev)} {lr*t*100:5.1f}%")
        W(f"{at(row+1, 3)}{'SequenceMatcher':>18s} {hbar(bw, sr*t, CSm)} {sr*t*100:5.1f}%")
        sl(0.018)

# ════════════════════════════════════════════════════════════════════════════════
# §4  DEMOS
# ════════════════════════════════════════════════════════════════════════════════

def _dtitle(n, name):
    cls(); _rsz()
    rainbow(f"  Demo {n}: {name}", 1, 1)
    W(f"{at(2, 3)}{DIM}{'─' * min(56, TW - 4)}{RST}")
    return 3

def _show_edit_ops(res, a, b, row, col=3):
    """Render edit operations from backtrace path."""
    parts = []
    for k in range(1, len(res['path'])):
        ci, cj = res['path'][k]; o = res['ops'][ci][cj]
        if o == 'M':   parts.append(f"{CM}{a[ci-1]}={b[cj-1]}{RST}")
        elif o == 'S': parts.append(f"{CS}{a[ci-1]}→{b[cj-1]}{RST}")
        elif o == 'D': parts.append(f"{CD}−{a[ci-1]}{RST}")
        else:          parts.append(f"{CI}+{b[cj-1]}{RST}")
    W(f"{at(row, col)}{CTT}Distance: {BLD}{res['dist']}{RST}  "
      f"{CTT}Ratio: {BLD}{res['ratio']*100:.1f}%{RST}")
    W(f"{at(row+1, col)}Edits: {' '.join(parts)}")
    return row + 2

# ──────────────────────────────────────────────────────────────────────────────
def demo_1():
    """Levenshtein DP Matrix — Step by Step"""
    a, b = "kitten", "sitting"
    r = _dtitle(1, "Levenshtein DP Matrix")
    typewr("Minimum single-character edits to transform one string into another.", r + 1, 3, 0.01, DIM)
    r += 3
    W(f"{at(r, 3)}{CTT}Recurrence:{RST}")
    W(f"{at(r+1, 5)}{CM}D[i,j] = D[i-1,j-1]            if a[i]=b[j]  (match){RST}")
    W(f"{at(r+2, 5)}{CS}       = min(D[i-1,j-1]+1,      substitute){RST}")
    W(f"{at(r+3, 5)}{CD}            D[i-1,j  ]+1,       delete){RST}")
    W(f"{at(r+4, 5)}{CI}            D[i,  j-1]+1)       insert){RST}")
    r += 6
    W(f"{at(r, 3)}{BLD}\"{a}\" → \"{b}\"{RST}"); r += 2
    res = lev_full(a, b)
    render_matrix(res, a, b, br=r, bc=3, cw=4, anim=True)
    r += len(a) + 3
    _show_edit_ops(res, a, b, r)
    pause()
    # Page 2: Cyrillic
    a2, b2 = "Левенщайн", "Левенштейн"
    r = _dtitle(1, "Levenshtein — Cyrillic")
    W(f"{at(r+1, 3)}{BLD}\"{a2}\" → \"{b2}\"{RST}"); r += 3
    res2 = lev_full(a2, b2)
    fits = (r + len(a2) + 5 < TH) and ((len(b2) + 2) * 4 + 8 < TW)
    if fits:
        render_matrix(res2, a2, b2, br=r, bc=3, cw=4, anim=True)
        r += len(a2) + 3
    _show_edit_ops(res2, a2, b2, r)
    pause()

# ──────────────────────────────────────────────────────────────────────────────
def demo_2():
    """SequenceMatcher — Block Discovery"""
    a, b = "The quick brown fox", "The quikc brown fax"
    r = _dtitle(2, "SequenceMatcher Block Discovery")
    typewr("Gestalt pattern matching: Ratio = 2·M / T", r + 1, 3, 0.015, DIM)
    typewr("(M = matching characters, T = total characters in both strings)", r + 2, 3, 0.01, DIM)
    r += 4
    W(f"{at(r, 3)}{BLD}\"{a}\"{RST}")
    W(f"{at(r+1, 3)}{BLD}\"{b}\"{RST}"); r += 3
    res = sm_full(a, b)
    # Animate block discovery
    lr = render_blocks_anim(a, b, res['steps'], r)
    lr += 1
    # Show final opcodes
    W(f"{at(lr, 3)}{CTT}Opcodes (inline diff):{RST}"); lr += 1
    lr = render_ops_inline(res['opcodes'], a, b, lr)
    lr += 1
    W(f"{at(lr, 3)}{CTT}Ratio: {BLD}{res['ratio']*100:.1f}%{RST}")
    M = sum(m.size for m in res['blocks'])
    T = len(a) + len(b)
    W(f"{at(lr+1, 3)}{DIM}2·{M}/{T} = {2*M/T*100:.1f}%{RST}")
    pause()
    # Page 2: kitten/sitting
    a2, b2 = "kitten", "sitting"
    r = _dtitle(2, "SequenceMatcher — Second Example")
    W(f"{at(r+1, 3)}{BLD}\"{a2}\" → \"{b2}\"{RST}"); r += 3
    res2 = sm_full(a2, b2)
    lr = render_blocks_anim(a2, b2, res2['steps'], r)
    lr += 1
    W(f"{at(lr, 3)}{CTT}Opcodes:{RST}"); lr += 1
    lr = render_ops_inline(res2['opcodes'], a2, b2, lr); lr += 1
    W(f"{at(lr, 3)}{CTT}Ratio: {BLD}{res2['ratio']*100:.1f}%{RST}")
    pause()

# ──────────────────────────────────────────────────────────────────────────────
def demo_3():
    """Head-to-Head Arena"""
    arena_pairs = PAIRS[:5]
    results = []
    for a, b, label in arena_pairs:
        lr = 1 - lev_dist(a, b) / max(len(a), len(b), 1)
        sr = difflib.SequenceMatcher(None, a, b).ratio()
        results.append((a, b, label, lr, sr))

    r = _dtitle(3, "Head-to-Head Arena")
    typewr("Levenshtein ratio vs SequenceMatcher — who scores higher?", r + 1, 3, 0.01, DIM)
    r += 3
    bw = min(30, TW - 35)
    lev_wins, sm_wins = 0, 0
    for ri, (a, b, label, lr, sr) in enumerate(results):
        W(f"{at(r, 3)}{BLD}Round {ri+1}: {RST}{DIM}{label}{RST}")
        W(f"{at(r+1, 3)}{DIM}\"{a}\" vs \"{b}\"{RST}")
        r += 2
        anim_bars(r, lr, sr, bw)
        winner = "Lev" if lr > sr else ("SM" if sr > lr else "Tie")
        wclr = CLev if lr > sr else (CSm if sr > lr else DIM)
        W(f"{at(r+2, 3)}{wclr}{BLD}  {'':>18s} ◆ Winner: {winner}{RST}")
        if lr > sr: lev_wins += 1
        elif sr > lr: sm_wins += 1
        r += 4
        # If we'd overflow, paginate
        if r + 6 > TH and ri < len(results) - 1:
            pause(); r = _dtitle(3, "Head-to-Head Arena (cont.)")
            r += 1
    # Summary
    if r + 5 > TH:
        pause(); r = _dtitle(3, "Arena — Summary"); r += 1
    W(f"{at(r, 3)}{BLD}{'─'*40}{RST}")
    W(f"{at(r+1, 3)}{CLev}{BLD}Levenshtein wins: {lev_wins}{RST}")
    W(f"{at(r+2, 3)}{CSm}{BLD}SequenceMatcher wins: {sm_wins}{RST}")
    r += 4
    bx(r, 3, min(60, TW - 4), 5, "Key Insight", dbl=True)
    W(f"{at(r+1, 5)}Levenshtein penalizes every edit equally.")
    W(f"{at(r+2, 5)}SequenceMatcher rewards long common blocks,")
    W(f"{at(r+3, 5)}making it more forgiving for rearrangements.")
    pause()

# ──────────────────────────────────────────────────────────────────────────────
def demo_4():
    """Interactive Explorer"""
    while True:
        r = _dtitle(4, "Interactive Explorer")
        W(f"{at(r+1, 3)}{DIM}Enter two strings to compare (empty to return to menu){RST}")
        W(f"{at(r+3, 3)}String A: "); a = sinput()
        if not a: return
        W(f"{at(r+4, 3)}String B: "); b = sinput()
        if not b: return

        a = unicodedata.normalize('NFC', a)
        b = unicodedata.normalize('NFC', b)
        r += 6

        if a == b:
            W(f"{at(r, 3)}{CM}{BLD}Strings are identical! Distance=0, Ratio=100%{RST}")
            pause(); continue

        lres = lev_full(a, b)
        sres = sm_full(a, b)

        # DP Matrix (if short enough)
        if len(a) <= 12 and len(b) <= 12 and r + len(a) + 5 < TH:
            render_matrix(lres, a, b, br=r, bc=3, cw=4, anim=len(a) <= 8)
            r += len(a) + 3
        else:
            W(f"{at(r, 3)}{DIM}(strings too long for matrix display){RST}"); r += 2

        # Scores
        W(f"{at(r, 3)}{CLev}{BLD}Levenshtein:{RST}  distance={lres['dist']}  "
          f"ratio={lres['ratio']*100:.1f}%")
        W(f"{at(r+1, 3)}{CSm}{BLD}SequenceMatcher:{RST}  ratio={sres['ratio']*100:.1f}%")
        r += 3

        # Opcodes
        W(f"{at(r, 3)}{CTT}Inline diff:{RST}"); r += 1
        r = render_ops_inline(sres['opcodes'], a, b, r); r += 1

        # Matching blocks
        W(f"{at(r, 3)}{CTT}Matching blocks:{RST}"); r += 1
        for blk in sres['blocks']:
            if blk.size > 0:
                W(f"{at(r, 5)}{CM}a[{blk.a}:{blk.a+blk.size}] = "
                  f"b[{blk.b}:{blk.b+blk.size}] = \"{a[blk.a:blk.a+blk.size]}\"{RST}")
                r += 1

        # Edit operations
        r += 1
        _show_edit_ops(lres, a, b, r)
        pause()

# ──────────────────────────────────────────────────────────────────────────────
def demo_5():
    """Real-World Applications"""
    # 5a: Typo Correction
    r = _dtitle(5, "Real-World: Typo Correction")
    dictionary = [
        "programming", "program", "progress", "problem", "process",
        "receive", "recipe", "recent", "record", "recover",
        "the", "they", "their", "there", "then", "these",
        "algorithm", "alternative", "although", "already", "always",
    ]
    typos = [("programing", "programming"), ("recieve", "receive"),
             ("teh", "the"), ("algorthm", "algorithm")]
    typewr("Find the closest dictionary word for each misspelling.", r + 1, 3, 0.01, DIM)
    r += 3
    bw = min(25, TW - 45)
    for typo, expected in typos:
        scored = [(w, 1 - lev_dist(typo, w) / max(len(typo), len(w), 1),
                   difflib.SequenceMatcher(None, typo, w).ratio()) for w in dictionary]
        scored.sort(key=lambda x: -x[2])
        W(f"{at(r, 3)}{BLD}\"{typo}\"{RST} → top matches:")
        r += 1
        for w, lr, sr in scored[:3]:
            marker = f" {CM}✓{RST}" if w == expected else ""
            W(f"{at(r, 5)}{w:>15s} {hbar(bw, sr, CSm)} {sr*100:4.1f}%{marker}")
            r += 1
        r += 1
        if r + 6 > TH: pause(); r = _dtitle(5, "Typo Correction (cont.)"); r += 1
    pause()

    # 5b: Name Deduplication
    r = _dtitle(5, "Real-World: Name Deduplication")
    names = [
        "Acme Corp.", "ACME Corporation", "Acme Corp",
        "Johnson & Johnson", "Johnson and Johnson",
        "Int'l Business Machines", "IBM Corp.",
    ]
    typewr("Cluster similar company names using SM ratio > 0.6", r + 1, 3, 0.01, DIM)
    r += 3
    clusters = []
    assigned = set()
    for i, n1 in enumerate(names):
        if i in assigned: continue
        cluster = [n1]; assigned.add(i)
        for j, n2 in enumerate(names):
            if j in assigned: continue
            if difflib.SequenceMatcher(None, n1.lower(), n2.lower()).ratio() > 0.6:
                cluster.append(n2); assigned.add(j)
        clusters.append(cluster)
    for ci, cluster in enumerate(clusters):
        h = ci / max(len(clusters), 1)
        clr = _hsv(h * 0.7)
        W(f"{at(r, 3)}{clr}{BLD}Cluster {ci+1}:{RST}")
        r += 1
        for name in cluster:
            W(f"{at(r, 5)}{clr}  ▸ {name}{RST}"); r += 1
        r += 1
    pause()

    # 5c: Fuzzy VLOOKUP
    r = _dtitle(5, "Real-World: Fuzzy VLOOKUP")
    invoices = [
        "Office Supplies - Paper A4",
        "Deskjet Printer Cartridge",
        "USB-C Cable 2m",
        "Wireless Mouse Logitech",
    ]
    catalog = [
        "A4 Paper Ream 500 sheets", "HP Deskjet Ink Cartridge Black",
        "USB Type-C Cable 2 meters", "Logitech Wireless Mouse M185",
        "Mechanical Keyboard Cherry MX", "Monitor Stand Adjustable",
    ]
    typewr("Match invoice lines to catalog items.", r + 1, 3, 0.01, DIM)
    r += 3; bw = min(20, TW - 55)
    for inv in invoices:
        best_w, best_s = "", 0.0
        for cat in catalog:
            s = difflib.SequenceMatcher(None, inv.lower(), cat.lower()).ratio()
            if s > best_s: best_s = s; best_w = cat
        conf = CM if best_s > 0.5 else (CS if best_s > 0.35 else CD)
        W(f"{at(r, 3)}{DIM}{inv}{RST}")
        W(f"{at(r+1, 5)}→ {conf}{best_w} {hbar(bw, best_s, conf)} {best_s*100:.0f}%{RST}")
        r += 3
    pause()

# ──────────────────────────────────────────────────────────────────────────────
def demo_6():
    """Hybrid Scoring Lab"""
    r = _dtitle(6, "Hybrid Scoring Lab")
    typewr("Hybrid = w·Levenshtein + (1-w)·SequenceMatcher", r + 1, 3, 0.015, DIM)
    r += 3

    a, b = "Acme Corp.", "ACME Corporation"
    lr = 1 - lev_dist(a, b) / max(len(a), len(b), 1)
    sr = difflib.SequenceMatcher(None, a, b).ratio()

    W(f"{at(r, 3)}{BLD}\"{a}\" vs \"{b}\"{RST}")
    W(f"{at(r+1, 3)}{CLev}Lev ratio: {lr*100:.1f}%{RST}  "
      f"{CSm}SM ratio: {sr*100:.1f}%{RST}")
    r += 3

    # Weight sweep chart
    W(f"{at(r, 3)}{CTT}Weight sweep w: 0.0 → 1.0{RST}"); r += 1
    bw = min(30, TW - 35)
    sweep = []
    for wi in range(11):
        w = wi / 10.0
        h = w * lr + (1 - w) * sr
        sweep.append((w, h))

    for wi, (wv, hv) in enumerate(sweep):
        lbl = f"w={wv:.1f}"
        # Color gradient from CSm (w=0) to CLev (w=1)
        cr = int(80 + wv * (80 - 80))
        cg = int(150 + wv * (200 - 150))
        cb = int(255 + wv * (255 - 255))
        clr = fg(int(80 + wv * 0), int(150 + wv * 50), int(255 - wv * 95))
        W(f"{at(r + wi, 3)}{lbl:>8s} {hbar(bw, hv, clr)} {hv*100:5.1f}%")
        sl(0.06)

    r += 13
    # Decision tree
    if r + 8 > TH: pause(); r = _dtitle(6, "Hybrid — Decision Guide"); r += 1
    bx(r, 3, min(58, TW - 4), 9, "When to use what?", dbl=True)
    W(f"{at(r+1, 5)}{CLev}Levenshtein (w→1.0):{RST}")
    W(f"{at(r+2, 5)}  • Typo detection, spell checking")
    W(f"{at(r+3, 5)}  • Short strings, character-level edits")
    W(f"{at(r+4, 5)}{CSm}SequenceMatcher (w→0.0):{RST}")
    W(f"{at(r+5, 5)}  • Document similarity, long text")
    W(f"{at(r+6, 5)}  • Rearranged content, block moves")
    W(f"{at(r+7, 5)}{fg(200,255,150)}{BLD}Accounting/ERP: w=0.3–0.5 recommended{RST}")
    pause()

# ════════════════════════════════════════════════════════════════════════════════
# §5  SPLASH · MENU · MAIN
# ════════════════════════════════════════════════════════════════════════════════

def splash():
    cls()
    t = "Fuzzy Match Visual Explorer"
    sub = "Levenshtein Distance  ·  difflib.SequenceMatcher"
    tr = max(1, TH // 2 - 3)
    tc = max(1, (TW - dw(t)) // 2)
    sc = max(1, (TW - dw(sub)) // 2)
    # Sweep-in
    for i in range(len(t)):
        W(f"{at(tr, tc + i)}{_hsv(i / len(t))}{BLD}{t[i]}{RST}")
        sl(0.035)
    sl(0.2)
    # Rainbow shimmer
    for frame in range(20):
        buf = [at(tr, tc)]
        for i, c in enumerate(t):
            buf.append(f"{_hsv((i / len(t) + frame * 0.05) % 1)}{BLD}{c}")
        buf.append(RST); W("".join(buf)); sl(0.04)
    typewr(sub, tr + 2, sc, 0.02, DIM)
    W(f"{at(tr + 5, max(1, (TW - 22) // 2))}{DIM}Press any key to start{RST}")
    rkey()

def speed_ctl():
    global SPEED
    spds = [0.25, 0.5, 1.0, 2.0, 4.0]
    lbls = ["0.25× Slow", "0.5×", "1.0× Normal", "2.0×", "4.0× Fast"]
    sel = min(range(len(spds)), key=lambda i: abs(spds[i] - SPEED))
    while True:
        cls()
        W(f"{at(2, 3)}{CTT}{BLD}Animation Speed{RST}")
        W(f"{at(3, 3)}{DIM}{'─' * 30}{RST}")
        for i, lb in enumerate(lbls):
            pf = f"{fg(100, 255, 200)}▸ " if i == sel else "  "
            st = BLD if i == sel else ""
            W(f"{at(5 + i, 3)}{pf}{st}{lb}{RST}")
        W(f"{at(12, 3)}{DIM}↑↓ select  Enter: apply  Esc: back{RST}")
        k = rkey()
        if k == 'UP': sel = (sel - 1) % len(spds)
        elif k == 'DOWN': sel = (sel + 1) % len(spds)
        elif k == 'ENTER': SPEED = spds[sel]; return
        elif k in ('ESC', 'q'): return

def menu():
    items = [
        ("1", "Levenshtein DP Matrix — Step by Step"),
        ("2", "SequenceMatcher — Block Discovery"),
        ("3", "Head-to-Head Arena"),
        ("4", "Interactive Explorer"),
        ("5", "Real-World Applications"),
        ("6", "Hybrid Scoring Lab"),
        ("S", "Speed Control"),
        ("Q", "Quit"),
    ]
    demos = [demo_1, demo_2, demo_3, demo_4, demo_5, demo_6]
    sel = 0
    while True:
        cls(); _rsz()
        rainbow("  Fuzzy Match Visual Explorer", 2, 1)
        W(f"{at(3, 3)}{DIM}{'─' * 42}{RST}")
        for i, (key, label) in enumerate(items):
            pf = f"{fg(100, 255, 200)}▸ " if i == sel else "  "
            st = BLD if i == sel else ""
            W(f"{at(5 + i, 3)}{pf}{st}[{key}] {label}{RST}")
        W(f"{at(5 + len(items) + 2, 3)}{DIM}↑↓ navigate  Enter: select  q: quit{RST}")
        W(f"{at(5 + len(items) + 3, 3)}{DIM}Speed: {SPEED}×{RST}")
        k = rkey()
        if k == 'UP': sel = (sel - 1) % len(items)
        elif k == 'DOWN': sel = (sel + 1) % len(items)
        elif k in ('ENTER', ' '):
            if sel == len(items) - 1: return
            elif sel == len(items) - 2: speed_ctl()
            elif sel < 6:
                try: demos[sel]()
                except KeyboardInterrupt: pass
        elif k in ('q', 'Q'): return
        elif k in '123456':
            try: demos[int(k) - 1]()
            except KeyboardInterrupt: pass
        elif k in ('s', 'S'): speed_ctl()

def main():
    if not sys.stdout.isatty():
        print("Error: requires an interactive terminal (TTY).", file=sys.stderr)
        sys.exit(1)
    _rsz()
    if TW < 60:
        print(f"Terminal too narrow ({TW} cols, need ≥60).", file=sys.stderr)
        sys.exit(1)
    W(AON + HIDE)
    try:
        splash()
        menu()
    except KeyboardInterrupt:
        pass
    finally:
        W(SHOW + AOFF)

if __name__ == "__main__":
    main()
