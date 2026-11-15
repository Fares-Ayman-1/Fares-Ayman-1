#!/usr/bin/env python3
"""Build the animated SVG panels for the Fares-Ayman-1 GitHub profile README.

GitHub READMEs cannot run JavaScript, so every animation from the Claude Design
mock-up ("Fares GitHub Profile.dc.html") is baked into self-contained SVGs that
animate with CSS keyframes and SMIL. Fonts are subset and embedded so the panels
look the same on every machine.

    python tools/build.py static                 # hero, neofetch, training, stack, footer, buttons -> assets/
    python tools/build.py live --out dist        # stats, langs, streak, graph, snake from the GitHub API -> dist/

`live` reads a token from GITHUB_TOKEN / GH_TOKEN, falling back to `gh auth token`.
Only public, non-fork repositories count towards stars and languages.
Optional: set PROFILE_EMAIL before `static` to add an Email line to the neofetch panel.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import io
import json
import math
import os
import random
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
FONTS = TOOLS / "fonts"
W = 840

MONO = "'JBM','JetBrains Mono',Consolas,monospace"
SANS = "'SG','Space Grotesk','Segoe UI',system-ui,sans-serif"
FONT_FILES = {
    ("JBM", 400): "JetBrainsMono-Regular.ttf",
    ("JBM", 700): "JetBrainsMono-Bold.ttf",
    ("SG", 500): "SpaceGrotesk-Medium.ttf",
    ("SG", 700): "SpaceGrotesk-Bold.ttf",
    ("SORA", 700): "Sora-Bold.ttf",
}
REDUCED = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


# ---------------------------------------------------------------- helpers
def esc(s) -> str:
    return html.escape(str(s), quote=True)


def _font_face(fam: str, wt: int, text: str) -> str:
    from fontTools import subset
    from fontTools.ttLib import TTFont

    font = TTFont(FONTS / FONT_FILES[(fam, wt)])
    opts = subset.Options()
    opts.layout_features = ["kern"]  # drop ligatures so `->` etc. stay literal
    try:
        import brotli  # noqa: F401
        opts.flavor, mime = "woff2", "font/woff2"
    except ImportError:
        opts.flavor, mime = "woff", "font/woff"
    sub = subset.Subsetter(opts)
    sub.populate(text=text or " ")
    sub.subset(font)
    font.flavor = opts.flavor
    buf = io.BytesIO()
    font.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'{fam}';font-weight:{wt};src:url(data:{mime};base64,{b64}) format('{opts.flavor}')}}"


def svg(w, h, body: str, css: str = "", fonts=(), title: str = "", defs: str = "") -> str:
    text = "".join(html.unescape(m) for m in re.findall(r">([^<]+)<", body)) + "0123456789 "
    faces = "".join(_font_face(f, wt, text) for f, wt in fonts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>'
        f"<style>{faces}{css}{REDUCED}</style>"
        f"{'<defs>' + defs + '</defs>' if defs else ''}{body}</svg>"
    )


def discrete(attr: str, frames, total: float) -> str:
    """SMIL discrete animation from (time, value) frames, collapsing repeats."""
    vals, keys, last = [], [], object()
    for t, v in frames:
        if v == last:
            continue
        last = v
        vals.append(str(v))
        keys.append(f"{min(t / total, 1):.6f}")
    keys[0] = "0"
    return (
        f'<animate attributeName="{attr}" calcMode="discrete" dur="{total:.3f}s" '
        f'repeatCount="indefinite" values="{";".join(vals)}" keyTimes="{";".join(keys)}"/>'
    )


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  {path.relative_to(ROOT)}  {len(content) / 1024:.0f} KB")


def panel(w, h, fill="#0d1117", stroke="#30363d", rx=12) -> str:
    return f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{rx}" fill="{fill}" stroke="{stroke}"/>'


def blink_css() -> str:
    return ".caret{animation:blink 1s step-end infinite}@keyframes blink{50%{opacity:0}}"


# ---------------------------------------------------------------- static: hero
ROLES = ["AI Engineer", "Building LLM agents", "Shipping RAG systems",
         "Training neural networks", "Computer vision tinkerer"]


def hero() -> str:
    h, cw, step, hold = 160, 12.0, 0.07, 1.75
    x0 = 28 + 2 * cw
    frames, t = [], 0.0
    for i, r in enumerate(ROLES):
        for c in range(len(r) + 1):
            frames.append((t, c * cw, i)); t += step
        t += hold
        for c in range(len(r) - 1, -1, -1):
            frames.append((t, c * cw, i)); t += step
    total = t
    width_anim = discrete("width", [(t, w) for t, w, _ in frames], total)
    caret_anim = discrete("x", [(t, round(x0 + w, 1)) for t, w, _ in frames], total)
    roles = "".join(
        f'<text x="{x0}" y="128" class="role" opacity="0">{esc(r)}'
        + discrete("opacity", [(t, 1 if i == j else 0) for t, _, j in frames], total)
        + "</text>"
        for i, r in enumerate(ROLES)
    )
    body = (
        panel(W, h)
        + '<text x="28" y="38" class="mono">Fares-Ayman-1 <tspan fill="#6e7681">/</tspan> README<tspan fill="#6e7681">.md</tspan></text>'
        + '<g class="pulse"><circle cx="760" cy="34" r="4" fill="#3fb950"/></g>'
        + '<text x="772" y="38" class="mono" fill="#3fb950" style="fill:#3fb950;font-size:12px">online</text>'
        + '<text x="28" y="88" class="title">Hi, I\'m Fares Ayman Gaber</text>'
        + '<text x="28" y="128" class="role">&gt;</text>'
        + f'<clipPath id="tc"><rect x="{x0}" y="100" height="40" width="0">{width_anim}</rect></clipPath>'
        + f'<g clip-path="url(#tc)">{roles}</g>'
        + f'<rect class="caret" x="{x0}" y="111" width="11" height="22" fill="#58d5ff">{caret_anim}</rect>'
    )
    css = (
        f".mono{{font-family:{MONO};font-size:13px;fill:#8b949e}}"
        f".title{{font-family:{SANS};font-weight:700;font-size:36px;fill:#e6edf3}}"
        f".role{{font-family:{MONO};font-size:20px;fill:#58d5ff}}" + blink_css()
        + ".pulse{transform-box:fill-box;transform-origin:center;animation:pulse 1.6s infinite}"
        "@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(.85)}}"
    )
    return svg(W, h, body, css, [("JBM", 400), ("SG", 700)], "Hi, I'm Fares Ayman Gaber, AI Engineer")


# ---------------------------------------------------------------- static: neofetch
RAMP = " .'`^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"


def ascii_rows(path: Path, cols=150, rows=90) -> list[str]:
    from PIL import Image

    img = Image.open(path).convert("RGBA")
    side = int(img.width * 0.86)  # head-and-shoulders square crop of the cut-out
    left = (img.width - side) // 2
    img = img.crop((left, 0, left + side, side))
    small = img.resize((cols, rows), Image.BOX)
    px = small.load()
    lum, alpha = [], []
    for y in range(rows):
        for x in range(cols):
            r, g, b, a = px[x, y]
            alpha.append(a)
            lum.append(0.299 * r + 0.587 * g + 0.114 * b)
    # mix histogram-equalised and linear brightness: detail in the face, dark stays dark
    lit = sorted(v for v, a in zip(lum, alpha) if a > 110)
    lo, hi = lit[int(len(lit) * 0.02)], lit[int(len(lit) * 0.99)]
    import bisect
    out = []
    for y in range(rows):
        line = []
        for x in range(cols):
            i = y * cols + x
            if alpha[i] <= 110:
                line.append((" ", 0))
                continue
            eq = bisect.bisect_left(lit, lum[i]) / len(lit)
            lin = max(0.0, min(1.0, (lum[i] - lo) / ((hi - lo) or 1)))
            n = 0.55 * eq + 0.45 * lin
            line.append((RAMP[max(1, round(n * (len(RAMP) - 1)))], min(4, int(n * 5))))
        out.append(line)
    return out


ASCII_TONES = ["#24505e", "#3f8296", "#73bdd0", "#aee6f2", "#e4fbff"]


def ascii_markup(row) -> str:
    """Row of (char, tone) -> text with one tspan per run of equal tone."""
    parts, cur, buf = [], None, ""
    for ch, tone in row:
        tone = cur if ch == " " and cur is not None else tone
        if tone != cur and buf:
            parts.append(f'<tspan class="t{cur}">{esc(buf)}</tspan>')
            buf = ""
        cur = tone
        buf += ch
    if buf:
        parts.append(f'<tspan class="t{cur}">{esc(buf)}</tspan>')
    return "".join(parts)


def neofetch_lines() -> list[tuple[str, str]]:
    email = os.environ.get("PROFILE_EMAIL", "").strip()
    contact = ([("Email: ", email)] if email else []) + [("LinkedIn: ", "in/fares-ayman-b871a8237")]
    return [
        ("fares", "@github"), ("", "─" * 30),
        ("OS: ", "Windows 11 · Linux containers"), ("Role: ", "AI Engineer"),
        ("Focus: ", "LLMs · RAG · AI Agents · Computer Vision"), ("Uptime: ", "shipping models 24/7"), ("", ""),
        ("Lang.Code: ", "Python, TypeScript, SQL, C#"), ("Lang.Spoken: ", "Arabic, English"),
        ("ML.Stack: ", "PyTorch, scikit-learn, XGBoost, LightGBM"),
        ("LLM.Stack: ", "LangChain, Claude API, Gemini API, Qdrant"),
        ("Deploy: ", "FastAPI, Django, Docker, Railway"), ("", ""),
        *contact, ("", ""),
        ("Study: ", "Computers & AI · Banha University"),
    ]


def neofetch() -> str:
    toned = ascii_rows(TOOLS / "portrait.png")
    rows = ["".join(ch for ch, _ in r) for r in toned]
    info_lines = neofetch_lines()
    cols = len(rows[0])
    top, left, fs = 58, 24, 4.0
    aw = cols * fs * 0.6
    rng = random.Random(7)
    noise = "01#@%&$<>/\\|"
    scr = lambda r: "".join(" " if ch == " " else rng.choice(noise) for ch in r)  # noqa: E731

    reveal0, rstep = 0.4, 0.022
    reveal_end = reveal0 + len(rows) * rstep
    glitch_rows = rng.sample([i for i, r in enumerate(rows) if r.strip()], 8)
    gl_period = 1.8 * len(glitch_rows)
    gl_pct = 0.11 / gl_period * 100
    art = []
    for i, r in enumerate(rows):
        y = top + (i + 1) * fs - 0.6
        d = reveal0 + i * rstep
        anim = f"animation:rv .01s linear {d + 0.044:.3f}s forwards"
        if i in glitch_rows:
            g0 = reveal_end + 1 + glitch_rows.index(i) * 1.8
            anim += f",gh {gl_period:.1f}s steps(1) {g0:.2f}s infinite"
            art.append(f'<text x="{left}" y="{y:.1f}" class="gl" style="animation-delay:{g0:.2f}s" '
                       f'textLength="{aw:.1f}">{esc(scr(r))}</text>')
        art.append(f'<text x="{left}" y="{y:.1f}" class="a" style="{anim}" textLength="{aw:.1f}">{ascii_markup(toned[i])}</text>')
        art.append(f'<text x="{left}" y="{y:.1f}" class="s" style="animation-delay:{d:.3f}s" textLength="{aw:.1f}">{esc(scr(r))}</text>')

    # right column: neofetch lines typed one character at a time, with a moving caret
    ix, iy, lh, cw, cstep = left + aw + 40, top + 16, 22, 7.8, 0.016
    t0 = t = 0.6
    lines, caret = [], []
    for n, (k, v) in enumerate(info_lines):
        y = iy + n * lh
        length = len(k) + len(v)
        dur = max(length, 1) * cstep
        if length:
            vals = ";".join(f"{c * cw:.1f}" for c in range(length + 1))
            keys = ";".join(f"{c / (length + 1):.4f}" for c in range(length + 1))
            vcol = "#30363d" if v.startswith("─") else "#c9d1d9"
            lines.append(
                f'<clipPath id="l{n}"><rect x="{ix}" y="{y - 15}" height="20" width="0">'
                f'<animate attributeName="width" calcMode="discrete" begin="{t:.3f}s" dur="{dur:.3f}s" '
                f'values="{vals}" keyTimes="{keys}" fill="freeze"/></rect></clipPath>'
                f'<text x="{ix}" y="{y}" clip-path="url(#l{n})" class="nf">'
                f'<tspan fill="#58d5ff" font-weight="700">{esc(k)}</tspan><tspan fill="{vcol}">{esc(v)}</tspan></text>'
            )
            for c in range(length + 1):
                caret.append((t + c * cstep, f"{ix + c * cw:.1f}", y - 13))
        else:
            caret.append((t, f"{ix:.1f}", y - 13))
        t += dur + 0.05
    type_end = t
    span = type_end - t0
    ckeys = ["0"] + [f"{(tt - t0) / span:.5f}" for tt, _, _ in caret[1:]]
    caret_svg = (
        f'<rect class="caret" width="8" height="16" fill="#58d5ff" x="{ix}" y="{iy - 13}" opacity="0">'
        f'<set attributeName="opacity" to="1" begin="{t0}s" fill="freeze"/>'
        f'<animate attributeName="x" calcMode="discrete" begin="{t0}s" dur="{span:.3f}s" '
        f'values="{";".join(x for _, x, _ in caret)}" keyTimes="{";".join(ckeys)}" fill="freeze"/>'
        f'<animate attributeName="y" calcMode="discrete" begin="{t0}s" dur="{span:.3f}s" '
        f'values="{";".join(str(y) for _, _, y in caret)}" keyTimes="{";".join(ckeys)}" fill="freeze"/></rect>'
    )
    by = iy + len(info_lines) * lh - 4
    blocks = "".join(
        f'<rect x="{ix + i * 22}" y="{by}" width="22" height="14" fill="{c}"/>'
        for i, c in enumerate(["#0d1117", "#ff5f57", "#3fb950", "#febc2e", "#58a6ff", "#a371f7", "#58d5ff", "#e6edf3"])
    )
    h = max(top + len(rows) * fs, by + 14) + 30

    body = (
        panel(W, h, fill="#05080c", rx=10)
        + '<path d="M1 11a10 10 0 0 1 10-10h818a10 10 0 0 1 10 10v26H1z" fill="#161b22"/>'
        + '<line x1="1" y1="37.5" x2="839" y2="37.5" stroke="#30363d"/>'
        + "".join(f'<circle cx="{20 + i * 19}" cy="19" r="5.5" fill="{c}"/>' for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]))
        + f'<text x="{W / 2}" y="23.5" text-anchor="middle" class="nf" style="fill:#8b949e;font-size:12px">fares@github: ~ $ neofetch</text>'
        + f'<g filter="url(#glow)" class="flicker">{"".join(art)}</g>'
        + f'<rect class="scan" x="{left}" y="{top}" width="{aw:.0f}" height="6" fill="#58d5ff" opacity="0"/>'
        + "".join(lines) + caret_svg
        + f'<g class="fade" style="animation-delay:{type_end:.2f}s">{blocks}</g>'
    )
    defs = (
        '<filter id="glow" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="0.7" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
    )
    css = (
        f".nf{{font-family:{MONO};font-size:13px}}"
        f".a,.s,.gl{{font-family:{MONO};font-weight:700;font-size:{fs}px;white-space:pre}}"
        ".a{fill:#d6f8ff;opacity:0}.s{fill:#a371f7;opacity:0;animation:sc .066s linear forwards}"
        + "".join(f".t{i}{{fill:{c}}}" for i, c in enumerate(ASCII_TONES))
        +
        f".gl{{fill:#c8a6ff;opacity:0;animation:gs {gl_period:.1f}s steps(1) infinite}}"
        "@keyframes rv{to{opacity:1}}@keyframes sc{0%,99%{opacity:1}100%{opacity:0}}"
        f"@keyframes gs{{0%{{opacity:1}}{gl_pct:.2f}%,100%{{opacity:0}}}}"
        f"@keyframes gh{{0%{{opacity:0}}{gl_pct:.2f}%,100%{{opacity:1}}}}"
        ".flicker{animation:fl 4s infinite}@keyframes fl{0%,92%,94%,100%{opacity:1}93%{opacity:.75}}"
        f".scan{{animation:sw {len(rows) * rstep:.2f}s linear {reveal0}s 1}}"
        f"@keyframes sw{{0%{{opacity:.5;transform:translateY(0)}}99%{{opacity:.5;transform:translateY({len(rows) * fs:.0f}px)}}100%{{opacity:0}}}}"
        + blink_css() + ".fade{opacity:0;animation:rv .4s ease forwards}"
    )
    return svg(W, h, body, css, [("JBM", 400), ("JBM", 700)],
               "neofetch: ASCII portrait of Fares and a summary of his stack", defs)


# ---------------------------------------------------------------- static: training CRT
def training() -> str:
    h, epochs, step = 340, 100, 0.45
    total = epochs * step
    rng = random.Random(42)
    losses, accs, gpus, logs = [], [], [], [">> new run · seed 4242"]
    for e in range(1, epochs + 1):
        loss = 2.4 * math.exp(-e / 14) + 0.06 + rng.random() * 0.06
        acc = min(0.985, 0.42 + 0.56 * (1 - math.exp(-e / 16)) + (rng.random() - 0.5) * 0.02)
        losses.append(loss); accs.append(acc); gpus.append(0.72 + rng.random() * 0.25)
        logs.append(f"[ep {e:03d}] loss={loss:.4f} acc={acc * 100:.2f}% lr={3e-4 * 0.97 ** e:.2e}")

    rep = f'dur="{total}s" repeatCount="indefinite"'
    ekeys = ";".join(f"{i / epochs:.4f}" for i in range(epochs))
    lx = lambda i: i / (epochs - 1) * 400  # noqa: E731
    ly = lambda v: 170 - min(1, v / 2.5) * 155  # noqa: E731
    loss_pts = " ".join(f"{lx(i):.1f},{ly(v):.1f}" for i, v in enumerate(losses))
    acc_pts = " ".join(f"{lx(i):.1f},{170 - v * 155:.1f}" for i, v in enumerate(accs))
    cx = ";".join(f"{lx(i):.1f}" for i in range(epochs)) + f";{lx(epochs - 1):.1f}"
    cy = ";".join(f"{ly(v):.1f}" for v in losses) + f";{ly(losses[-1]):.1f}"
    chart = (
        "".join(f'<line x1="0" y1="{y}" x2="400" y2="{y}" stroke="#0f3a2a"/>' for y in (45, 90, 135))
        + f'<clipPath id="cc"><rect x="-4" y="-10" height="200" width="0"><animate attributeName="width" values="0;404;404" keyTimes="0;0.99;1" {rep}/></rect></clipPath>'
        + f'<g clip-path="url(#cc)"><polyline points="{acc_pts}" fill="none" stroke="#7ee7ff" stroke-width="1.5" stroke-dasharray="4 3" opacity=".8"/>'
        + f'<polyline points="{loss_pts}" fill="none" stroke="#39d98a" stroke-width="2.2" stroke-linejoin="round" filter="url(#gg)"/></g>'
        + f'<circle r="4" fill="#b6ffd9"><animate attributeName="cx" values="{cx}" keyTimes="{ekeys};1" {rep}/>'
        + f'<animate attributeName="cy" values="{cy}" keyTimes="{ekeys};1" {rep}/></circle>'
    )

    def ticker(x, y, values):
        """A column of values clipped to one row, stepped one epoch at a time."""
        cid = f"tk{x:.0f}_{y}"
        items = "".join(f'<text x="{x}" y="{y + i * 20}" class="v">{esc(v)}</text>' for i, v in enumerate(values))
        tr = ";".join(f"0 {-i * 20}" for i in range(epochs))
        return (
            f'<clipPath id="{cid}"><rect x="{x - 2}" y="{y - 14}" width="200" height="19"/></clipPath>'
            f'<g clip-path="url(#{cid})"><g>{items}<animateTransform attributeName="transform" type="translate" '
            f'calcMode="discrete" values="{tr}" keyTimes="{ekeys}" {rep}/></g></g>'
        )

    rx, ky, vx = 480, 92, 566
    info = "".join(f'<text x="{rx}" y="{ky + i * 20}" class="k">{k}</text>'
                   for i, k in enumerate(["Engineer", "Model", "Epoch", "Loss", "Val acc", "GPU"]))
    info += f'<text x="{vx}" y="{ky}" class="v">Fares Ayman Gaber</text><text x="{vx}" y="{ky + 20}" class="v">fares-net-v3</text>'
    info += ticker(vx, ky + 40, [f"{e} / 100" for e in range(1, epochs + 1)])
    info += ticker(vx, ky + 60, [f"{v:.4f}" for v in losses])
    info += ticker(vx, ky + 80, [f"{v * 100:.2f}%" for v in accs])
    gw = ";".join(f"{g * 170:.1f}" for g in gpus)
    info += (
        f'<rect x="{vx}" y="{ky + 92}" width="170" height="8" rx="2" fill="#0f3a2a"/>'
        f'<rect x="{vx}" y="{ky + 92}" width="140" height="8" rx="2" fill="#39d98a">'
        f'<animate attributeName="width" values="{gw}" keyTimes="{ekeys}" {rep}/></rect>'
    )
    info += ticker(vx + 180, ky + 100, [f"{round(g * 100)}%" for g in gpus])

    # log window: six lines, scrolls one line per epoch; future lines stay hidden
    lh, wy, rows_vis = 17.6, 214, 6
    items = []
    for i, line in enumerate(logs):
        hide = ""
        if i >= 2:
            hide = (f'<animate attributeName="opacity" calcMode="discrete" values="0;1" '
                    f'keyTimes="0;{(i - 1) / epochs:.4f}" {rep}/>')
        items.append(f'<text x="{rx}" y="{wy + 12 + i * lh:.1f}" class="lg">{esc(line)}{hide}</text>')
    tr = ";".join(f"0 {-max(0, e + 2 - rows_vis) * lh:.1f}" for e in range(epochs))
    log = (
        f'<clipPath id="lw"><rect x="{rx}" y="{wy}" width="340" height="{rows_vis * lh:.0f}"/></clipPath>'
        f'<g clip-path="url(#lw)"><g>{"".join(items)}<animateTransform attributeName="transform" type="translate" '
        f'calcMode="discrete" values="{tr}" keyTimes="{ekeys}" {rep}/></g></g>'
    )

    body = (
        f'<rect x="1" y="1" width="{W - 2}" height="{h - 2}" rx="16" fill="#04120d" stroke="#1f5c43" stroke-width="2"/>'
        + f'<rect x="1" y="1" width="{W - 2}" height="{h - 2}" rx="16" fill="url(#glowbg)"/>'
        + '<text x="20" y="30" class="hd">fares@lab:~$ ./train --model fares-net-v3 --live</text>'
        + '<g class="pulse"><circle cx="782" cy="26" r="3.5" fill="#39d98a"/></g><text x="792" y="30" class="hd">LIVE</text>'
        + '<rect x="16.5" y="46.5" width="440" height="278" rx="10" fill="none" stroke="#1f5c43"/>'
        + '<text x="30" y="68" class="lb">LOSS.CURVE</text>'
        + f'<g transform="translate(30 80) scale(1.04)">{chart}</g>'
        + '<text x="30" y="306" class="hd" style="font-size:11px">━ train loss</text>'
        + '<text x="140" y="306" class="hd" style="font-size:11px;fill:#7ee7ff">┅ val accuracy</text>'
        + '<rect x="468.5" y="46.5" width="356" height="278" rx="10" fill="none" stroke="#1f5c43"/>'
        + f'<text x="{rx}" y="68" class="lb">SYSTEM.INFO</text>'
        + info
        + f'<line x1="{rx}" y1="208" x2="812" y2="208" stroke="#1f5c43" stroke-dasharray="3 3"/>'
        + log
        + f'<rect x="2" y="2" width="{W - 4}" height="{h - 4}" rx="15" fill="url(#scanlines)"/>'
        + f'<rect class="band" x="2" y="0" width="{W - 4}" height="{h * 0.4:.0f}" fill="url(#band)"/>'
    )
    defs = (
        '<pattern id="scanlines" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity=".25"/></pattern>'
        '<linearGradient id="band" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#39d98a" stop-opacity="0"/>'
        '<stop offset=".5" stop-color="#39d98a" stop-opacity=".07"/><stop offset="1" stop-color="#39d98a" stop-opacity="0"/></linearGradient>'
        '<radialGradient id="glowbg"><stop offset="0" stop-color="#39d98a" stop-opacity="0"/><stop offset="1" stop-color="#39d98a" stop-opacity=".06"/></radialGradient>'
        '<filter id="gg" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
    )
    css = (
        f".hd{{font-family:{MONO};font-size:12px;fill:#39d98a}}.lb{{font-family:{MONO};font-size:11px;fill:#39d98a;letter-spacing:1px}}"
        f".k{{font-family:{MONO};font-size:12px;fill:#39d98a}}.v{{font-family:{MONO};font-size:12px;fill:#b6ffd9}}"
        f".lg{{font-family:{MONO};font-size:11px;fill:#6fd3a3}}"
        ".pulse{transform-box:fill-box;transform-origin:center;animation:pulse 1s infinite}"
        "@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(.85)}}"
        f".band{{animation:scan 5s linear infinite}}@keyframes scan{{from{{transform:translateY(-{h * 0.4:.0f}px)}}to{{transform:translateY({h}px)}}}}"
    )
    return svg(W, h, body, css, [("JBM", 400)], "Animated training run: loss curve, system info and logs", defs)


# ---------------------------------------------------------------- static: stack
STACK = [
    ("Python", "#3776ab"), ("PyTorch", "#ee4c2c"), ("TensorFlow", "#ff6f00"), ("scikit-learn", "#f7931e", "#111"),
    ("XGBoost", "#189fdd"), ("LightGBM", "#2e7d32"), ("LangChain", "#1c3c3c"), ("Claude API", "#d97757"),
    ("Gemini API", "#8e75b2"), ("OpenAI API", "#10a37f"), ("Qdrant", "#dc244c"), ("OpenCV", "#5c3ee8"),
    ("MediaPipe", "#0097a7"), ("FastAPI", "#009688"), ("Django", "#0c4b33"), ("Docker", "#2496ed"),
    ("PostgreSQL", "#4169e1"), ("Redis", "#dc382d"), ("pandas", "#150458"), ("NumPy", "#4dabcf"),
    ("Jupyter", "#f37626"), ("Streamlit", "#ff4b4b"), ("n8n", "#ea4b71"), ("TypeScript", "#3178c6"),
    ("Next.js", "#e6edf3", "#111"), ("React", "#61dafb", "#111"), ("GitHub Actions", "#2088ff"),
    ("Railway", "#853bce"), ("Git", "#f05032"),
]


def stack() -> str:
    pad, gap, rh, cw = 24, 8, 34, 7.2
    x, y = pad, 62
    chips = []
    for i, item in enumerate(STACK):
        name, bg = item[0], item[1]
        fg = item[2] if len(item) > 2 else "#fff"
        w = len(name) * cw + 20
        if x + w > W - pad:
            x, y = pad, y + rh
        chips.append(
            f'<g class="chip" style="animation-delay:{0.2 + i * 0.06:.2f}s"><rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="26" rx="5" fill="{bg}"/>'
            f'<text x="{x + w / 2:.1f}" y="{y + 17.5}" text-anchor="middle" fill="{fg}">{esc(name)}</text></g>'
        )
        x += w + gap
    h = y + 26 + pad
    body = panel(W, h) + '<text x="24" y="42" class="t">When I build AI, I rely on</text>' + "".join(chips)
    css = (
        f".t{{font-family:{SANS};font-weight:700;font-size:20px;fill:#e6edf3}}"
        f".chip text{{font-family:{MONO};font-weight:700;font-size:12px}}"
        ".chip{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .45s cubic-bezier(.2,.8,.3,1.2) forwards}"
        "@keyframes pop{from{opacity:0;transform:translateY(14px) scale(.8)}to{opacity:1;transform:none}}"
    )
    return svg(W, h, body, css, [("JBM", 700), ("SG", 700)], "Tech stack: " + ", ".join(s[0] for s in STACK))


# ---------------------------------------------------------------- static: footer + buttons
def footer() -> str:
    h = 56
    msg = '$ echo "thanks for visiting"'
    cx = 24 + len(msg) * 7.8 + 2
    body = (
        panel(W, h) + f'<text x="24" y="33" class="m">{esc(msg)}</text>'
        + f'<rect class="caret" x="{cx:.1f}" y="20" width="8" height="17" fill="#58d5ff"/>'
    )
    return svg(W, h, body, f".m{{font-family:{MONO};font-size:13px;fill:#8b949e}}" + blink_css(),
               [("JBM", 400)], "thanks for visiting")


def button(label: str, bg: str, fg="#fff", border=None) -> str:
    w, h = round(len(label) * 8.4 + 28), 34
    stroke = f' stroke="{border}"' if border else ""
    body = (
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="6" fill="{bg}"{stroke}/>'
        f'<text x="{w / 2}" y="22" text-anchor="middle" class="b">{esc(label)}</text>'
    )
    return svg(w, h, body, f".b{{font-family:{SANS};font-weight:700;font-size:14px;fill:{fg}}}", [("SG", 700)], label)


def text_width(fam: str, wt: int, text: str, size: float) -> float:
    from fontTools.ttLib import TTFont

    font = TTFont(FONTS / FONT_FILES[(fam, wt)])
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    return sum(hmtx[cmap[ord(c)]][0] for c in text) * size / font["head"].unitsPerEm


def quantro_button() -> str:
    """Quantro AI lock-up from its brand system: gold spark, "Quantro" cream + "AI" gold, Sora, on navy."""
    size, h = 14, 34
    w1, w2 = text_width("SORA", 700, "Quantro ", size), text_width("SORA", 700, "AI", size)
    x0 = 14 + 12 + 7
    w = round(x0 + w1 + w2 + 14)
    spark = "M0 -6.5C.7 -2.2 2.2 -.7 6.5 0C2.2 .7 .7 2.2 0 6.5C-.7 2.2 -2.2 .7 -6.5 0C-2.2 -.7 -.7 -2.2 0 -6.5Z"
    body = (
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="6" fill="#0C1733" stroke="#3C507E"/>'
        f'<path d="{spark}" transform="translate(20 17)" fill="#D3AE6C"/>'
        f'<text x="{x0}" y="22" class="b">Quantro <tspan class="ai">AI</tspan></text>'
    )
    css = f".b{{font-family:'SORA',Sora,{SANS};font-weight:700;font-size:{size}px;fill:#F5F1EA;letter-spacing:-.01em}}.ai{{fill:#D3AE6C}}"
    return svg(w, h, body, css, [("SORA", 700)], "Quantro AI")


# ---------------------------------------------------------------- live: GitHub API
def token() -> str:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not tok:
        tok = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    return tok


def gql(query: str, variables: dict) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token()}", "User-Agent": "profile-readme-builder"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.load(r)
    if out.get("errors"):
        raise RuntimeError(out["errors"])
    return out["data"]


BASE_Q = """query($login:String!){user(login:$login){createdAt followers{totalCount}
pullRequests{totalCount} issues{totalCount}
repositoriesContributedTo(first:1,contributionTypes:[COMMIT,ISSUE,PULL_REQUEST,REPOSITORY]){totalCount}
repositories(first:100,ownerAffiliations:OWNER,privacy:PUBLIC,isFork:false){nodes{stargazerCount
languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}
contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""


def fetch(login: str) -> dict:
    base = gql(BASE_Q, {"login": login})["user"]
    start = int(base["createdAt"][:4])
    now = dt.datetime.now(dt.timezone.utc)
    parts = []
    for y in range(start, now.year + 1):
        to = f"{y}-12-31T23:59:59Z" if y < now.year else now.strftime("%Y-%m-%dT%H:%M:%SZ")
        parts.append(
            f'y{y}:contributionsCollection(from:"{y}-01-01T00:00:00Z",to:"{to}"){{totalCommitContributions '
            f"contributionCalendar{{totalContributions weeks{{contributionDays{{date contributionCount}}}}}}}}"
        )
    years = gql("query($login:String!){user(login:$login){" + " ".join(parts) + "}}", {"login": login})["user"]
    days, commits, total = {}, 0, 0
    for yv in years.values():
        commits += yv["totalCommitContributions"]
        total += yv["contributionCalendar"]["totalContributions"]
        for w in yv["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
    return {"base": base, "days": dict(sorted(days.items())), "commits": commits, "total": total}


def rank(commits, prs, issues, stars, followers):
    """github-readme-stats' rank formula (MIT), so the grade means what people expect."""
    exp = lambda x: 1 - 2 ** -x  # noqa: E731
    lgn = lambda x: x / (1 + x)  # noqa: E731
    score = (2 * exp(commits / 250) + 3 * exp(prs / 50) + exp(issues / 25)
             + 4 * lgn(stars / 50) + lgn(followers / 10)) / 12
    pct = (1 - score) * 100
    for th, lv in zip([1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100], ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]):
        if pct <= th:
            return lv, pct
    return "C", pct


CARD, PINK = "#11161d", "#ff6b9a"


def stats_card(data, name) -> str:
    b = data["base"]
    stars = sum(r["stargazerCount"] for r in b["repositories"]["nodes"])
    prs, issues = b["pullRequests"]["totalCount"], b["issues"]["totalCount"]
    level, pct = rank(data["commits"], prs, issues, stars, b["followers"]["totalCount"])
    rows = [("☆", "Total stars", stars), ("◷", "Total commits", data["commits"]), ("⇄", "Total PRs", prs),
            ("⊙", "Total issues", issues), ("⌂", "Contributed to", b["repositoriesContributedTo"]["totalCount"])]
    w, h = 412, 200
    body = panel(w, h, CARD, rx=10) + f'<text x="22" y="36" class="t">{esc(name)}\' GitHub Stats</text>'
    for i, (ic, label, val) in enumerate(rows):
        y = 70 + i * 26
        body += (
            f'<g class="row" style="animation-delay:{0.15 + i * 0.12:.2f}s"><text x="22" y="{y}" class="ic">{ic}</text>'
            f'<text x="42" y="{y}" class="l">{label}:</text><text x="262" y="{y}" class="n" text-anchor="end">{val:,}</text></g>'
        )
    off = 251.3 * (pct / 100)
    body += (
        '<g transform="translate(336 108) rotate(-90)"><circle r="40" fill="none" stroke="#2a1820" stroke-width="7"/>'
        f'<circle r="40" fill="none" stroke="{PINK}" stroke-width="7" stroke-linecap="round" stroke-dasharray="251.3" class="ring"/></g>'
        f'<text x="336" y="116" text-anchor="middle" class="g">{level}</text>'
    )
    css = (
        f".t{{font-family:{SANS};font-weight:700;font-size:17px;fill:{PINK}}}"
        f".l,.ic{{font-family:{SANS};font-weight:500;font-size:13.5px;fill:#c9d1d9}}.ic{{fill:{PINK}}}"
        f".n{{font-family:{SANS};font-weight:700;font-size:13.5px;fill:#e6edf3}}"
        f".g{{font-family:{SANS};font-weight:700;font-size:24px;fill:#e6edf3;opacity:0;animation:fi .6s ease 1.4s forwards}}"
        ".row{opacity:0;animation:fi .5s ease forwards}@keyframes fi{to{opacity:1}}"
        ".ring{stroke-dashoffset:251.3;animation:ring 2s cubic-bezier(.2,.8,.2,1) .3s forwards}"
        f"@keyframes ring{{to{{stroke-dashoffset:{off:.1f}}}}}"
    )
    return svg(w, h, body, css, [("SG", 500), ("SG", 700)], f"GitHub stats: {stars} stars, {data['commits']} commits, rank {level}")


HIDE_LANGS = {"HTML", "CSS", "SCSS", "MDX"}  # markup, not programming languages


def langs_card(data) -> str:
    sizes, colors = {}, {}
    for r in data["base"]["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            if n in HIDE_LANGS:
                continue
            sizes[n] = sizes.get(n, 0) + e["size"]
            colors[n] = e["node"]["color"] or "#8b949e"
    top = sorted(sizes.items(), key=lambda kv: -kv[1])[:6]
    tot = sum(v for _, v in top) or 1
    w, h = 412, 200
    body = panel(w, h, CARD, rx=10) + '<text x="22" y="36" class="t">Most used languages</text>'
    body += ('<clipPath id="bar"><rect x="22" y="54" width="368" height="10" rx="5"/></clipPath>'
             '<g clip-path="url(#bar)"><rect x="22" y="54" width="368" height="10" fill="#21262d"/><g class="grow">')
    x = 22.0
    for n, v in top:
        bw = v / tot * 368
        body += f'<rect x="{x:.2f}" y="54" width="{bw + 0.5:.2f}" height="10" fill="{colors[n]}"/>'
        x += bw
    body += "</g></g>"
    for i, (n, v) in enumerate(top):
        cx, cy = 22 + (i % 2) * 190, 98 + (i // 2) * 28
        body += (
            f'<g class="row" style="animation-delay:{0.5 + i * 0.1:.1f}s"><circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{colors[n]}"/>'
            f'<text x="{cx + 16}" y="{cy}" class="l">{esc(n)} <tspan style="fill:#8b949e">{v / tot * 100:.1f}%</tspan></text></g>'
        )
    css = (
        f".t{{font-family:{SANS};font-weight:700;font-size:17px;fill:{PINK}}}"
        f".l{{font-family:{SANS};font-weight:500;font-size:13px;fill:#c9d1d9}}"
        ".grow{transform-origin:22px 0;transform:scaleX(0);animation:gr 1.6s cubic-bezier(.2,.8,.2,1) .2s forwards}"
        "@keyframes gr{to{transform:scaleX(1)}}.row{opacity:0;animation:fi .5s ease forwards}@keyframes fi{to{opacity:1}}"
    )
    return svg(w, h, body, css, [("SG", 500), ("SG", 700)], "Most used languages: " + ", ".join(n for n, _ in top))


def _fmt(d: dt.date, year=False) -> str:
    day = "%#d" if os.name == "nt" else "%-d"
    return d.strftime(f"%b {day}, %Y" if year else f"%b {day}")


def streak_card(data) -> str:
    today = dt.datetime.now(dt.timezone.utc).date()
    days = [(dt.date.fromisoformat(k), v) for k, v in data["days"].items()]
    days = [d for d in days if d[0] <= today]
    longest = run = 0
    best, run_start = (None, None), None
    for d, v in days:
        if v > 0:
            run_start = run_start or d
            run += 1
            if run > longest:
                longest, best = run, (run_start, d)
        else:
            run, run_start = 0, None
    # current streak counts back from today, or from yesterday while today is still empty
    current, i = 0, len(days) - 1
    if i >= 0 and days[i][1] == 0:
        i -= 1
    end = days[i][0] if i >= 0 else today
    while i >= 0 and days[i][1] > 0:
        current += 1
        i -= 1
    cur_range = (_fmt(end) if current == 1 else f"{_fmt(end - dt.timedelta(days=current - 1))} – {_fmt(end)}") if current else "start one today"
    first = next((d for d, v in days if v > 0), today)
    best_range = f"{_fmt(best[0])} – {_fmt(best[1])}" if longest else ""
    h = 170
    ring_off = 263.9 * (1 - min(1, current / max(longest, 1)))
    body = panel(W, h, CARD, rx=10)
    body += f'<line x1="280" y1="24" x2="280" y2="{h - 24}" stroke="#30363d"/><line x1="560" y1="24" x2="560" y2="{h - 24}" stroke="#30363d"/>'
    body += (
        f'<g class="col"><text x="140" y="78" class="big">{data["total"]:,}</text><text x="140" y="106" class="lab">Total contributions</text>'
        f'<text x="140" y="128" class="sub">{first.strftime("%b %Y")} – present</text></g>'
        '<g transform="translate(420 74) rotate(-90)"><circle r="42" fill="none" stroke="#2a1820" stroke-width="5"/>'
        f'<circle r="42" fill="none" stroke="{PINK}" stroke-width="5" stroke-linecap="round" stroke-dasharray="263.9" class="ring"/></g>'
        '<text x="420" y="38" class="fire">🔥</text>'
        f'<text x="420" y="84" class="big" style="font-size:26px">{current}</text>'
        f'<text x="420" y="138" class="lab" style="fill:{PINK}">Current streak</text><text x="420" y="156" class="sub">{cur_range}</text>'
        f'<g class="col" style="animation-delay:.3s"><text x="700" y="78" class="big">{longest}</text><text x="700" y="106" class="lab">Longest streak</text>'
        f'<text x="700" y="128" class="sub">{best_range}</text></g>'
    )
    css = (
        f".big{{font-family:{SANS};font-weight:700;font-size:28px;fill:#e6edf3;text-anchor:middle}}"
        f".lab{{font-family:{SANS};font-weight:500;font-size:13.5px;fill:#c9d1d9;text-anchor:middle}}"
        f".sub{{font-family:{SANS};font-weight:500;font-size:11.5px;fill:#8b949e;text-anchor:middle}}"
        ".fire{font-size:18px;text-anchor:middle;animation:fl 1.6s ease-in-out infinite}@keyframes fl{50%{transform:translateY(-4px)}}"
        ".col{opacity:0;animation:fi .6s ease .1s forwards}@keyframes fi{to{opacity:1}}"
        ".ring{stroke-dashoffset:263.9;animation:ring 1.8s cubic-bezier(.2,.8,.2,1) .3s forwards}"
        f"@keyframes ring{{to{{stroke-dashoffset:{ring_off:.1f}}}}}"
    )
    return svg(W, h, body, css, [("SG", 500), ("SG", 700)],
               f"{data['total']} total contributions, current streak {current} days, longest {longest} days")


def graph_card(data, name) -> str:
    today = dt.datetime.now(dt.timezone.utc).date()
    span = [today - dt.timedelta(days=30 - i) for i in range(31)]
    vals = [data["days"].get(d.isoformat(), 0) for d in span]
    top = math.ceil(max(4, max(vals)) / 4) * 4
    gx = lambda i: 52 + i * (748 / 30)  # noqa: E731
    gy = lambda v: 200 - v * (160 / top)  # noqa: E731
    line = " ".join(("M" if i == 0 else "L") + f"{gx(i):.1f} {gy(v):.1f}" for i, v in enumerate(vals))
    length = sum(math.hypot(gx(i) - gx(i - 1), gy(vals[i]) - gy(vals[i - 1])) for i in range(1, 31))
    h = 250
    body = panel(W, h, "#0f1520", rx=10)
    body += f'<text x="{W / 2}" y="32" text-anchor="middle" class="t">{esc(name)}\' Contribution Graph</text>'
    for k in range(5):
        y = 200 - k * 40
        body += f'<line x1="52" y1="{y}" x2="800" y2="{y}" stroke="{"#30405a" if k == 0 else "#1f2a3a"}"/>'
        body += f'<text x="42" y="{y + 4}" class="ax" text-anchor="end">{top * k // 4}</text>'
    body += (
        f'<path d="{line} L{gx(30):.1f} 200 L52 200 Z" fill="url(#area)" class="area"/>'
        f'<path d="{line}" fill="none" stroke="#79c0ff" stroke-width="2.5" stroke-linejoin="round" filter="url(#lg)" '
        f'stroke-dasharray="{length:.0f}" stroke-dashoffset="{length:.0f}" class="ln"/>'
    )
    for i, v in enumerate(vals):
        body += f'<circle cx="{gx(i):.1f}" cy="{gy(v):.1f}" r="3.2" fill="#e6edf3" class="dot" style="animation-delay:{0.2 + i * 2.6 / 30:.2f}s"/>'
    body += f'<text x="52" y="226" class="ax">{_fmt(span[0])}</text><text x="800" y="226" class="ax" text-anchor="end">{_fmt(span[-1])}</text>'
    body += f'<text x="{W / 2}" y="226" class="ax" text-anchor="middle">last 31 days · {sum(vals)} contributions</text>'
    defs = (
        '<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#79c0ff" stop-opacity=".35"/>'
        '<stop offset="1" stop-color="#79c0ff" stop-opacity="0"/></linearGradient>'
        '<filter id="lg" x="-5%" y="-20%" width="110%" height="140%"><feGaussianBlur stdDeviation="3" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
    )
    css = (
        f".t{{font-family:{SANS};font-weight:700;font-size:16px;fill:#79c0ff}}.ax{{font-family:{MONO};font-size:11px;fill:#8b949e}}"
        ".ln{animation:draw 2.6s linear .2s forwards}@keyframes draw{to{stroke-dashoffset:0}}"
        ".area{opacity:0;animation:fi 2.6s ease .2s forwards}.dot{opacity:0;animation:fi .2s ease forwards}@keyframes fi{to{opacity:1}}"
    )
    return svg(W, h, body, css, [("JBM", 400), ("SG", 700)], f"Contributions over the last 31 days: {sum(vals)}", defs)


LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
CELL = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]


def snake_card(data) -> str:
    cal = data["base"]["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"][-53:]
    C, R, S = len(weeks), 7, 14
    grid = [[0] * R for _ in range(C)]
    for x, wk in enumerate(weeks):
        for d in wk["contributionDays"]:
            wd = (dt.date.fromisoformat(d["date"]).weekday() + 1) % 7  # Sunday first, like GitHub
            grid[x][wd] = LEVEL.get(d["contributionLevel"], 0)
    path = [(x, (R - 1 - k) if x % 2 else k) for x in range(C) for k in range(R)]
    order = {p: i for i, p in enumerate(path)}
    step, seg = 0.055, 8
    n_steps = len(path) + seg + 20
    total = n_steps * step
    gw = C * S - 3
    ox, oy = (W - gw) / 2, 58
    cells = []
    for x in range(C):
        for y in range(R):
            lv = grid[x][y]
            r = f'<rect x="{ox + x * S:.1f}" y="{oy + y * S}" width="11" height="11" rx="2" fill="{CELL[lv]}"'
            if lv:
                kt = (order[(x, y)] + 1) * step / total
                r += (f'><animate attributeName="fill" calcMode="discrete" values="{CELL[lv]};{CELL[0]}" '
                      f'keyTimes="0;{kt:.5f}" dur="{total:.2f}s" repeatCount="indefinite"/></rect>')
            else:
                r += "/>"
            cells.append(r)
    snake = []
    for k in range(seg):
        vals, keys, last = [], [], None
        for hstep in range(n_steps):
            idx = hstep - 1 - k
            if 0 <= idx < len(path):
                px, py = path[idx]
                v = f"{ox + px * S - 1:.1f} {oy + py * S - 1}"
            else:
                v = "-60 -60"
            if v != last:
                vals.append(v); keys.append(f"{hstep * step / total:.5f}"); last = v
        keys[0] = "0"
        fill = "#e2c5ff" if k == 0 else f"rgba(163,113,247,{1 - k * 0.11:.2f})"
        glow = ' filter="url(#sg)"' if k == 0 else ""
        snake.append(
            f'<rect width="13" height="13" rx="4" fill="{fill}"{glow}>'
            f'<animateTransform attributeName="transform" type="translate" calcMode="discrete" values="{";".join(vals)}" '
            f'keyTimes="{";".join(keys)}" dur="{total:.2f}s" repeatCount="indefinite"/></rect>'
        )
    h = oy + R * S + 44
    ly = h - 20
    legend_x = ox + gw - 5 * 14 - 34
    legend = (
        f'<text x="{legend_x - 6}" y="{ly}" class="ax" text-anchor="end">Less</text>'
        + "".join(f'<rect x="{legend_x + i * 14}" y="{ly - 9}" width="10" height="10" rx="2" fill="{c}"/>' for i, c in enumerate(CELL))
        + f'<text x="{legend_x + 5 * 14 + 2}" y="{ly}" class="ax">More</text>'
    )
    body = (
        panel(W, h) + '<text x="24" y="36" class="t">Contribution activity</text>'
        + "".join(cells) + "".join(reversed(snake))
        + f'<text x="{ox}" y="{ly}" class="ax">{cal["totalContributions"]:,} contributions in the last year</text>' + legend
    )
    defs = '<filter id="sg" x="-50%" y="-50%" width="200%" height="200%"><feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#a371f7"/></filter>'
    css = f".t{{font-family:{SANS};font-weight:700;font-size:20px;fill:#e6edf3}}.ax{{font-family:{MONO};font-size:12px;fill:#8b949e}}"
    return svg(W, h, body, css, [("JBM", 400), ("SG", 700)],
               f"Contribution graph with a snake eating {cal['totalContributions']} contributions from the last year", defs)


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", choices=["static", "live", "all"])
    ap.add_argument("--user", default="Fares-Ayman-1")
    ap.add_argument("--name", default="Fares")
    ap.add_argument("--out", default="dist")
    a = ap.parse_args()
    if a.target in ("static", "all"):
        print("static -> assets/")
        out = ROOT / "assets"
        write(out / "hero.svg", hero())
        write(out / "neofetch.svg", neofetch())
        write(out / "training.svg", training())
        write(out / "stack.svg", stack())
        write(out / "footer.svg", footer())
        write(out / "btn-linkedin.svg", button("LinkedIn", "#0a66c2"))
        write(out / "btn-gmail.svg", button("Gmail", "#ea4335"))
        write(out / "btn-portfolio.svg", button("Portfolio", "#21262d", "#e6edf3", "#30363d"))
        write(out / "btn-kaggle.svg", button("Kaggle", "#20BEFF", "#0d1117"))
        write(out / "btn-quantro.svg", quantro_button())
    if a.target in ("live", "all"):
        out = ROOT / a.out
        print(f"live ({a.user}) -> {a.out}/")
        data = fetch(a.user)
        write(out / "stats.svg", stats_card(data, a.name))
        write(out / "langs.svg", langs_card(data))
        write(out / "streak.svg", streak_card(data))
        write(out / "graph.svg", graph_card(data, a.name))
        write(out / "snake.svg", snake_card(data))


if __name__ == "__main__":
    main()
