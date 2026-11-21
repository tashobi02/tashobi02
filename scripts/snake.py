#!/usr/bin/env python3
"""Render an animated snake that eats the GitHub contribution grid and grows as it eats.

Usage:
  python scripts/snake.py <user> <out_dir> [calendar.json]

Without calendar.json the calendar is fetched from the GitHub GraphQL API using $GITHUB_TOKEN.
Writes <out_dir>/github-snake-dark.svg and <out_dir>/github-snake.svg. No dependencies.
"""
import json
import math
import os
import sys
import urllib.request

CELL, GAP = 11, 2
STEP = CELL + GAP
PAD_X, PAD_Y = 16, 14
DT = 0.075            # seconds per grid step
BASE_LEN = 4          # starting length in segments
MAX_LEN = 45          # final length after eating everything
SUB = 2               # body segments per cell; overlapping circles read as one smooth body
ENTRY = BASE_LEN + 2  # head starts this many cells left of the grid

LEVELS = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]
THEMES = {
    "github-snake-dark.svg": {
        "grid": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
        "body": "#38bdf8", "band": "#1793d1", "belly": "#7dd3fc", "eye": "#0d1117",
    },
    "github-snake.svg": {
        "grid": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
        "body": "#1793d1", "band": "#0f5f8a", "belly": "#5ab8e8", "eye": "#0d1117",
    },
}

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
weeks{contributionDays{contributionCount contributionLevel weekday}}}}}}"""


def fetch(user):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def grid_from(data):
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    cells = {}
    for col, week in enumerate(weeks):
        for day in week["contributionDays"]:
            cells[(col, day["weekday"])] = LEVELS.index(day["contributionLevel"])
    return cells, len(weeks)


def plan(cells, cols):
    """Greedy nearest-food walk. Returns path of cells and the step index at which each food is eaten."""
    food = {c for c, lvl in cells.items() if lvl > 0}
    pos: tuple[int, int] = (-ENTRY, 3)
    path: list[tuple[int, int]] = [pos]
    eaten_at: dict[tuple[int, int], int] = {}
    while food:
        tx, ty = min(food, key=lambda f: (abs(f[0] - pos[0]) + abs(f[1] - pos[1]), f[0], f[1]))
        while pos != (tx, ty):
            x, y = pos
            pos = (x + (tx > x) - (tx < x), y) if x != tx else (x, y + (ty > y) - (ty < y))
            path.append(pos)
            if pos in food:
                food.discard(pos)
                eaten_at[pos] = len(path) - 1
    # leave the grid to the right, far enough that the whole body exits before the loop restarts
    while path[-1][0] < cols + MAX_LEN + 2:
        path.append((path[-1][0] + 1, path[-1][1]))
    return path, eaten_at


def xy(c):
    return PAD_X + c[0] * STEP + CELL / 2, PAD_Y + c[1] * STEP + CELL / 2


def pct(i, total):
    return f"{100 * i / total:.3f}%"


def render(cells, cols, path, eaten_at, theme):
    n = len(path)
    dur = n * DT
    total_food = len(eaten_at)
    grow = min(1.0, (MAX_LEN - BASE_LEN) / max(total_food, 1))
    w, h = PAD_X * 2 + cols * STEP - GAP, PAD_Y * 2 + 7 * STEP - GAP
    css, body = [], []

    # head heading in degrees, unwrapped so turns are always +-90
    angles, a = [], 0.0
    for i in range(n):
        p, q = path[max(i - 1, 0)], path[i] if i else path[1]
        target = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])) if i else 0.0
        while target - a > 180:
            target -= 360
        while target - a < -180:
            target += 360
        a = target
        angles.append(a)

    css.append("@keyframes h{" + "".join(
        f"{pct(i, n)}{{transform:translate({xy(c)[0]:.1f}px,{xy(c)[1]:.1f}px) rotate({angles[i]:.0f}deg)}}"
        for i, c in enumerate(path)) + "}")
    css.append("@keyframes m{" + "".join(
        f"{pct(i, n)}{{transform:translate({xy(c)[0]:.1f}px,{xy(c)[1]:.1f}px)}}" for i, c in enumerate(path)) + "}")

    # grid: eaten cells fade to empty at the moment the head reaches them
    g = theme["grid"]
    for (cx, cy), lvl in sorted(cells.items()):
        x, y = PAD_X + cx * STEP, PAD_Y + cy * STEP
        if lvl and (cx, cy) in eaten_at:
            k = f"e{cx}_{cy}"
            t = eaten_at[(cx, cy)]
            css.append(f"@keyframes {k}{{0%,{pct(t, n)}{{fill:{g[lvl]}}}{pct(t + 0.6, n)},100%{{fill:{g[0]}}}}}")
            body.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{g[lvl]}" style="animation:{k} {dur:.2f}s linear infinite"/>')
        else:
            body.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{g[lvl]}"/>')

    # body segments: each follows the head's path i steps behind; extra segments appear as food is eaten
    eat_steps = sorted(eaten_at.values())
    segs = []
    for j in range(MAX_LEN * SUB, 0, -1):
        i = j / SUB  # distance behind the head, in cells
        if i < BASE_LEN:
            show = 0
        else:
            need = math.ceil((i - BASE_LEN + 1) / grow)  # foods needed before this segment exists
            if need > total_food:
                continue
            show = eat_steps[need - 1]
        color = theme["band"] if j % 6 in (0, 1) else theme["body"]  # dorsal stripes
        r = 7.0 - 2.6 * max(0.0, (BASE_LEN - i) / BASE_LEN - 0.5) if not show else 7.0  # small taper on the starting tail
        circle = f'<circle r="{r:.1f}" fill="{color}"'
        if show:
            # a new segment pops in small and swells, so the tail is tapered while the snake is growing
            k = f"s{j}"
            css.append(f"@keyframes {k}{{0%,{pct(show, n)}{{opacity:0;transform:scale(.35)}}"
                       f"{pct(show + 0.01, n)}{{opacity:1;transform:scale(.35)}}"
                       f"{pct(show + 8, n)},100%{{opacity:1;transform:scale(1)}}}}")
            circle += f' style="transform-origin:0 0;animation:{k} {dur:.2f}s linear infinite"'
        segs.append(f'<g style="animation:m {dur:.2f}s linear {j * DT / SUB:.4f}s infinite backwards">{circle}/></g>')

    head = (f'<g style="animation:h {dur:.2f}s linear infinite">'
            f'<g class="tongue"><path d="M8 0H14.5M14.5 0l2.5-2M14.5 0l2.5 2" stroke="#f7768e" stroke-width="1.2" fill="none" stroke-linecap="round"/></g>'
            f'<ellipse rx="9.4" ry="7.8" fill="{theme["body"]}"/>'
            f'<ellipse cx="-1.5" cy="0" rx="4" ry="2.4" fill="{theme["belly"]}" opacity=".45"/>'
            f'<circle cx="3.6" cy="-3.9" r="2.3" fill="#fff"/><circle cx="4.3" cy="-3.9" r="1.2" fill="{theme["eye"]}"/>'
            f'<circle cx="3.6" cy="3.9" r="2.3" fill="#fff"/><circle cx="4.3" cy="3.9" r="1.2" fill="{theme["eye"]}"/>'
            f'</g>')

    style = (".tongue{transform-origin:8px 0;animation:t .9s ease-in-out infinite}"
             "@keyframes t{0%,55%,100%{transform:scaleX(0)}70%,85%{transform:scaleX(1)}}"
             "@media (prefers-reduced-motion:reduce){*{animation-play-state:paused!important}}"
             + "".join(css))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="A snake eating the contribution graph, growing longer with every box it eats">'
            f'<style>{style}</style>{"".join(body)}{"".join(segs)}{head}</svg>')


def main():
    user, out = sys.argv[1], sys.argv[2]
    data = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else fetch(user)
    cells, cols = grid_from(data)
    path, eaten_at = plan(cells, cols)

    # self-check: every move is one grid step and every contribution box gets eaten
    assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(path, path[1:]))
    assert set(eaten_at) == {c for c, lvl in cells.items() if lvl > 0}

    os.makedirs(out, exist_ok=True)
    for name, theme in THEMES.items():
        with open(os.path.join(out, name), "w") as f:
            f.write(render(cells, cols, path, eaten_at, theme))
    print(f"{len(eaten_at)} boxes, {len(path)} steps, {len(path) * DT:.1f}s loop -> {out}")


if __name__ == "__main__":
    main()
