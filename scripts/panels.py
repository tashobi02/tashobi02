#!/usr/bin/env python3
"""Render the README section panels (About, Research, Tech Stack, Analytics header) as SVGs
in the same console-home style as the banner. Edit the content below, then run:

  python3 scripts/panels.py        # writes assets/panels/*.svg (needs network once for skillicons)
"""
import os
import random
import re
import urllib.request
from xml.sax.saxutils import escape

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "panels")
W = 1200
FONT = "'Segoe UI', 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif"
TXT, MUTED, BOLD = "#c9d5ee", "#9fb3d9", "#ffffff"

# ---------- content (text in **bold** segments is highlighted) ----------
ABOUT = [
    ("cap", "**Computer Science Senior** pursuing a B.Sc. in CSE at **Islamic University of Technology (IUT)**, Dhaka", "Class of 2027"),
    ("work", "Completed **Industrial Training on Applied AI** at **Battery Low Interactive**", "Sep – Oct 2026"),
    ("lift", "Into **fitness and bodybuilding**", None),
    ("swim", "Off the keyboard, I enjoy **swimming** and **driving**", None),
    ("pad", "Big fan of **Soulsborne games**", None),
    ("lock", "Currently building **something I can't show yet**. It's still compiling in the dark, and the reveal is coming soon", None),
    ("mail", "Reach me at **obiditbd@gmail.com**", None),
]
FUN_FACT = "**Fun Fact:** I have one of the rarest names in the world."
RESEARCH = [
    ("net", "Affective Game Computing", "Adaptive NPC behaviour, player modelling, and emotion-driven game AI (SSL, IUT)"),
    ("rot", "Continual Model Editing & Unlearning", "Sequential LLM editing via null-space–projected Cayley rotations that preserve weight geometry"),
    ("chat", "Bengali NLP", "Hallucination detection and safety evaluation in Bengali LLMs"),
]
ACHIEVEMENTS = [
    ("Top 20", "Finalist (Top 20 / 400+)", "IUT Agentic AI Hackathon (built AgriSense AI)"),
    ("4th", "4th Place (50+ teams)", "HerWILL × UAP Safe Social Media Datathon 2026 (Macro F1 = 0.748)"),
    ("9th", "9th Place", "Bengali LLM Hallucination-Detection Datathon (Team Lead, F1 = 0.910)"),
]
SKILLS = "cpp,c,py,java,ts,js,html,css,react,nextjs,vite,tailwind,pytorch,supabase,postgres,docker,git,linux,arch,latex,vscode"

# ---------- icon glyphs, drawn in a 0..84 box ----------
ST = 'stroke="#e6f0ff" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"'
GLYPHS = {
    "cap":  f'<g {ST}><path d="M10 34L42 20L74 34L42 48Z"/><path d="M24 41V56C32 64 52 64 60 56V41M74 34V52"/></g>',
    "work": f'<g {ST}><rect x="16" y="28" width="52" height="38" rx="5"/><path d="M32 28V20H52V28M16 44H68"/></g>',
    "lift": f'<g {ST}><path d="M26 42H58"/><rect x="16" y="30" width="8" height="24" rx="2"/><rect x="60" y="30" width="8" height="24" rx="2"/><path d="M10 36V48M74 36V48"/></g>',
    "swim": f'<g {ST}><path d="M12 40C20 34 27 34 34 40S48 46 56 40 66 34 72 40M12 54C20 48 27 48 34 54S48 60 56 54 66 48 72 54"/></g><circle cx="58" cy="24" r="6" fill="#e6f0ff"/>',
    "pad":  f'<g {ST}><path d="M24 30H60C68 30 72 40 74 52C76 62 68 66 62 58L56 50H28L22 58C16 66 8 62 10 52C12 40 16 30 24 30Z"/><path d="M26 40V48M22 44H30"/></g><circle cx="56" cy="40" r="3" fill="#e6f0ff"/><circle cx="62" cy="46" r="3" fill="#e6f0ff"/>',
    "lock": f'<g {ST}><rect x="24" y="38" width="36" height="28" rx="6"/><path d="M31 38V29C31 16 53 16 53 29V38"/></g><circle cx="42" cy="51" r="4" fill="#e6f0ff"/>',
    "mail": f'<g {ST}><rect x="14" y="22" width="56" height="40" rx="6"/><path d="M16 26L42 46L68 26"/></g>',
    "bolt": '<path d="M46 10L20 48H40L36 74L64 34H44Z" fill="#e6f0ff"/>',
    "net":  '<g stroke="#e6f0ff" stroke-width="3" fill="none"><path d="M20 24L42 42L64 24M20 60L42 42L64 60M20 24L20 60M64 24L64 60"/></g>'
            '<g fill="#e6f0ff"><circle cx="20" cy="24" r="6"/><circle cx="20" cy="60" r="6"/><circle cx="42" cy="42" r="7"/><circle cx="64" cy="24" r="6"/><circle cx="64" cy="60" r="6"/></g>',
    "rot":  f'<g {ST}><path d="M62 30A24 24 0 1 0 66 50"/><path d="M62 16V30H48"/><rect x="34" y="34" width="16" height="16" rx="2"/></g>',
    "chat": f'<g {ST}><path d="M14 22H70V54H40L26 66V54H14Z"/><path d="M26 34H58M26 43H48"/></g>',
}
TILE_BG = [("#1e3a8a", "#0e7490"), ("#0f766e", "#134e4a"), ("#3730a3", "#1e1b4b"), ("#0369a1", "#082f49"),
           ("#334155", "#0f172a"), ("#1793d1", "#0b3a66"), ("#475569", "#1e293b"), ("#111827", "#030712")]


def text_w(s, size, bold=False):
    # ponytail: rough width estimate for system sans; leaves slack because viewers' fonts differ
    return len(s) * size * (0.53 if bold else 0.49)


def wrap(rich, size, max_w):
    """Split '**bold** text' into lines of (word, bold) runs that fit max_w."""
    words = []
    for i, part in enumerate(re.split(r"\*\*", rich)):
        words += [(w, i % 2 == 1) for w in part.split()]
    lines, cur, cur_w = [], [], 0.0
    for w, b in words:
        ww = text_w(w + " ", size, b)
        if cur and cur_w + ww > max_w:
            lines.append(cur)
            cur, cur_w = [], 0.0
        cur.append((w, b))
        cur_w += ww
    return lines + [cur] if cur else lines


def line_svg(x, y, runs, size, color=TXT):
    spans = ""
    for i, (w, b) in enumerate(runs):
        gap = "" if i == 0 or w[0] in ",.;:)" else " "  # no space before punctuation that follows a bold run
        weight = ' font-weight="600"' if b else ""
        spans += f'<tspan fill="{BOLD if b else color}"{weight}>{gap}{escape(w)}</tspan>'
    return f'<text x="{x}" y="{y}" style="font-size:{size}px">{spans}</text>'


def tile(x, y, size, glyph, k, label=None):
    a, b = TILE_BG[k % len(TILE_BG)]
    gid = f"g{abs(hash((x, y, k))) % 10**8}"
    inner = (f'<g transform="scale({size / 84:.3f})">{GLYPHS[glyph]}</g>' if glyph else
             f'<text x="{size / 2}" y="{size / 2 + 6}" text-anchor="middle" style="font-size:{size * .3:.0f}px;font-weight:700;fill:#fff">{escape(label or "")}</text>')
    return (f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>'
            f'<g transform="translate({x} {y})"><rect width="{size}" height="{size}" rx="{size * .22:.0f}" fill="url(#{gid})"/>'
            f'<rect width="{size}" height="{size}" rx="{size * .22:.0f}" fill="none" stroke="#fff" stroke-opacity=".1"/>{inner}</g>')


def glass(x, y, w, h):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="#ffffff" fill-opacity=".05" stroke="#ffffff" stroke-opacity=".12"/>'


def frame(name, h, body, label, seed):
    rnd = random.Random(seed)
    dots = "".join(
        f'<circle class="d" cx="{rnd.uniform(10, W - 10):.0f}" cy="{rnd.uniform(10, h - 10):.0f}" r="{rnd.choice([.8, 1.1, 1.5, 2])}" fill="#dbeafe" '
        f'style="--dx:{rnd.uniform(-20, 20):.0f}px;animation-duration:{rnd.uniform(6, 11):.1f}s;animation-delay:-{rnd.uniform(0, 9):.1f}s;opacity:{rnd.uniform(.2, .6):.2f}"/>'
        for _ in range(int(h / 14)))
    title_w = text_w(name, 30, True)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{escape(label)}">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#040b1f"/><stop offset=".6" stop-color="#081a45"/><stop offset="1" stop-color="#0a2d6e"/></linearGradient>
<radialGradient id="halo" cx=".85" cy=".1" r=".7"><stop offset="0" stop-color="#3b82f6" stop-opacity=".28"/><stop offset="1" stop-color="#3b82f6" stop-opacity="0"/></radialGradient>
<linearGradient id="rib" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#93c5fd" stop-opacity="0"/><stop offset=".5" stop-color="#bfdbfe" stop-opacity=".35"/><stop offset="1" stop-color="#93c5fd" stop-opacity="0"/></linearGradient>
<clipPath id="card"><rect width="{W}" height="{h}" rx="20"/></clipPath>
<filter id="soft" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="5"/></filter>
<style>text{{font-family:{FONT}}}.d{{animation:drift ease-in-out infinite alternate}}.r{{animation:sway 16s ease-in-out infinite alternate}}
@keyframes drift{{from{{transform:translate(0,0)}}to{{transform:translate(var(--dx),-14px)}}}}@keyframes sway{{from{{transform:translateX(-50px)}}to{{transform:translateX(50px)}}}}
@media (prefers-reduced-motion:reduce){{.d,.r{{animation:none}}}}</style>
</defs>
<g clip-path="url(#card)">
<rect width="{W}" height="{h}" fill="url(#bg)"/><rect width="{W}" height="{h}" fill="url(#halo)"/>
<g filter="url(#soft)"><path class="r" d="M-100 {h - 30} C 250 {h - 90}, 550 {h + 10}, 850 {h - 50} S 1180 {h - 80}, 1300 {h - 40}" stroke="url(#rib)" stroke-width="3" fill="none"/></g>
{dots}
<text x="56" y="72" style="font-size:30px;font-weight:600;fill:#fff">{escape(name)}</text>
<rect x="56" y="86" width="{title_w:.0f}" height="3" rx="1.5" fill="#fff"/>
{body}
</g></svg>'''
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{name.split()[0].lower()}.svg"), "w") as f:
        f.write(svg)
    return h


def about():
    parts, y, size = [], 124, 19
    for k, (glyph, rich, chip) in enumerate(ABOUT):
        chip_w = text_w(chip, 15) + 28 if chip else 0
        lines = wrap(rich, size, 1144 - 128 - (chip_w + 24 if chip else 0))
        parts.append(tile(56, y, 48, glyph, k))
        ty = y + 24 + 7 - (len(lines) - 1) * 13
        parts += [line_svg(124, ty + i * 26, ln, size) for i, ln in enumerate(lines)]
        if chip:
            parts.append(f'<rect x="{1144 - chip_w:.0f}" y="{y + 10}" width="{chip_w:.0f}" height="28" rx="14" fill="#fff" fill-opacity=".1" stroke="#fff" stroke-opacity=".18"/>'
                         f'<text x="{1144 - chip_w / 2:.0f}" y="{y + 29}" text-anchor="middle" style="font-size:15px;fill:#e6f0ff">{escape(chip)}</text>')
        y += max(64, 48 + len(lines) * 26 - 10)
    y += 8
    parts += [glass(56, y, 1088, 72), tile(76, y + 14, 44, "bolt", 5),
              line_svg(136, y + 43, wrap(FUN_FACT, 19, 980)[0], 19)]
    label = "About Me. " + " ".join(re.sub(r"\*\*", "", r) + (f" ({c})." if c else ".") for _, r, c in ABOUT) + " " + FUN_FACT.replace("**", "")
    return frame("About Me", y + 72 + 40, "".join(parts), label, 1)


def card(x, title, glyph, items, numbered):
    parts, w = [], 536
    parts.append(tile(x + 24, 140, 40, glyph, 0 if numbered else 2))
    parts.append(f'<text x="{x + 78}" y="{167}" style="font-size:22px;font-weight:600;fill:#fff">{escape(title)}</text>')
    y = 208
    for k, (icon, head, desc) in enumerate(items):
        parts.append(tile(x + 24, y, 44, None if numbered else icon, k + 1, icon if numbered else None))
        heads = wrap(f"**{head}**", 18, w - 110)
        descs = wrap(desc, 16, w - 110)
        ty = y + 18
        for ln in heads:
            parts.append(line_svg(x + 84, ty, ln, 18)); ty += 24
        for ln in descs:
            parts.append(line_svg(x + 84, ty, ln, 16, MUTED)); ty += 22
        y = max(ty, y + 44) + 18
    return parts, y


def research():
    left, ly = card(56, "Research Interests", "net", RESEARCH, False)
    right, ry = card(608, "Achievements", "bolt", ACHIEVEMENTS, True)
    h = max(ly, ry) + 20
    body = glass(56, 120, 536, h - 140) + glass(608, 120, 536, h - 140) + "".join(left + right)
    label = ("Research and Highlights. Research interests: " + "; ".join(f"{a}: {b}" for _, a, b in RESEARCH)
             + ". Achievements: " + "; ".join(f"{a}, {b}" for _, a, b in ACHIEVEMENTS) + ".")
    return frame("Research & Highlights", h + 20, body, label, 2)


def stack():
    req = urllib.request.Request(f"https://skillicons.dev/icons?i={SKILLS}&perline=11&theme=dark", headers={"User-Agent": "readme-panels"})
    icons = urllib.request.urlopen(req, timeout=30).read().decode()
    m = re.search(r'viewBox="([^"]+)"', icons)
    assert m, "skillicons response has no viewBox"
    vb = m.group(1)
    _, _, vw, vh = map(float, vb.split())
    inner = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", icons.strip())
    iw = 900
    ih = iw * vh / vw
    body = f'<svg x="{(W - iw) / 2:.0f}" y="122" width="{iw}" height="{ih:.0f}" viewBox="{vb}">{inner}</svg>'
    names = "C++, C, Python, Java, TypeScript, JavaScript, HTML, CSS, React, Next.js, Vite, Tailwind, PyTorch, Supabase, PostgreSQL, Docker, Git, Linux, Arch Linux, LaTeX, VS Code"
    return frame("Tech Stack", 122 + ih + 44, body, "Tech Stack: " + names, 3)


def analytics():
    return frame("GitHub Analytics", 118, "", "GitHub Analytics", 4)


if __name__ == "__main__":
    for f in (about, research, stack, analytics):
        f()
    for name in os.listdir(OUT):  # self-check: every panel is valid XML
        __import__("xml.dom.minidom").dom.minidom.parse(os.path.join(OUT, name))
    print("panels ->", sorted(os.listdir(OUT)))
