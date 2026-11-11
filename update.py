#!/usr/bin/env python3
"""Builds assets/terminal.svg (the neofetch-style card) and refreshes GitHub stats.

Edit the CONFIG block to change anything about the card. Stats come from the GitHub
API and fall back to stats_cache.json if the API is unreachable.
Run locally:  python update.py --offline   (uses sample numbers, no token needed)
"""
import json, os, sys, time, urllib.request
from datetime import date
from html import escape

# ───────────────────────── CONFIG ─────────────────────────
USER = "kaioboyle"
HANDLE = "kaio@atlas"
BIRTHDAY = date(2009, 10, 11)          # used for the "Uptime" line — edit to your real date
COLORS = {
    "bg": "#0d1117", "border": "#2d2650",
    "handle": "#c084fc",    # purple
    "key": "#a78bfa",       # light purple
    "value": "#7dd3fc",     # sky blue
    "dots": "#4b5563",      # grey
    "art_from": "#a78bfa", "art_to": "#60a5fa",
}
# (section title, [(key, value), ...]) — blank title = no header line
INFO = [
    (None, [
        ("OS", "Windows 11, Ubuntu, macOS"),
        ("Uptime", "{uptime}"),
        ("Host", "Worcestershire, West Midlands"),
        ("Kernel", "Student Software Developer"),
        ("IDE", "VSCode, IntelliJ IDEA, PyCharm, Spyder"),
    ]),
    (None, [
        ("Languages.Programming", "Python, Java, JavaScript, C++"),
        ("Languages.Real", "English"),
    ]),
    (None, [
        ("Focus.AI", "Automation, AI"),
        ("Focus.Web", "Web, Full-Stack"),
        ("Focus.Build", "Software, Electronics"),
    ]),
    ("Contact", [
        ("Email", "kaioboyle.music@gmail.com"),
        ("LinkedIn", "kai-o-boyle-253859321"),
    ]),
    ("GitHub Stats", [
        ("Repos", "{repos} {{Contributed: {contrib}}} | Stars: {stars}"),
        ("Commits", "{commits} | Followers: {followers}"),
        ("Lines of Code", "{loc} ( {add}++, {dele}-- )"),
    ]),
]
LINE_WIDTH = 62          # characters per info line (dot-leaders pad to this)
# ──────────────────────────────────────────────────────────

API = "https://api.github.com"
TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")


def gh(path, data=None):
    req = urllib.request.Request(
        f"{API}{path}", data=json.dumps(data).encode() if data else None,
        headers={"Authorization": f"bearer {TOKEN}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read() or b"null")


def fetch_stats():
    q = """query($login:String!){user(login:$login){createdAt followers{totalCount}
      repositories(ownerAffiliations:OWNER,isFork:false,first:100){totalCount nodes{name stargazerCount}}
      repositoriesContributedTo(first:1,contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){totalCount}}}"""
    _, d = gh("/graphql", {"query": q, "variables": {"login": USER}})
    u = d["data"]["user"]
    repos = u["repositories"]["nodes"]
    start = int(u["createdAt"][:4])
    commits = 0
    for yr in range(start, date.today().year + 1):
        cq = """query($login:String!,$f:DateTime!,$t:DateTime!){user(login:$login){
          contributionsCollection(from:$f,to:$t){totalCommitContributions restrictedContributionsCount}}}"""
        _, c = gh("/graphql", {"query": cq, "variables": {
            "login": USER, "f": f"{yr}-01-01T00:00:00Z", "t": f"{yr}-12-31T23:59:59Z"}})
        cc = c["data"]["user"]["contributionsCollection"]
        commits += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    add = dele = 0
    for r in repos:
        for _ in range(6):  # stats endpoint answers 202 while it computes
            try:
                st, data = gh(f"/repos/{USER}/{r['name']}/stats/contributors")
            except Exception:
                break
            if st == 200 and data:
                for a in data:
                    if a["author"] and a["author"]["login"].lower() == USER.lower():
                        add += sum(w["a"] for w in a["weeks"]); dele += sum(w["d"] for w in a["weeks"])
                break
            time.sleep(3)
    return dict(repos=u["repositories"]["totalCount"],
                contrib=u["repositoriesContributedTo"]["totalCount"],
                stars=sum(r["stargazerCount"] for r in repos), commits=commits,
                followers=u["followers"]["totalCount"], add=add, dele=dele, loc=add - dele)


def uptime():
    t = date.today()
    y = t.year - BIRTHDAY.year; m = t.month - BIRTHDAY.month; d = t.day - BIRTHDAY.day
    if d < 0:
        m -= 1
        pm = t.month - 1 or 12; py = t.year if t.month > 1 else t.year - 1
        d += (date(py + (pm == 12), pm % 12 + 1, 1) - date(py, pm, 1)).days
    if m < 0: y -= 1; m += 12
    s = lambda n, w: f"{n} {w}" + ("" if n == 1 else "s")
    return f"{s(y,'year')}, {s(m,'month')}, {s(d,'day')}"


def build_svg(stats):
    c = COLORS
    art = open(os.path.join(os.path.dirname(__file__) or ".", "art.txt")).read().split("\n")
    A_FS, A_LH, A_X, A_Y = 7.2, 8.6, 24, 40           # ASCII art metrics
    I_FS, I_LH, I_X = 13, 17.5, 430                    # info column
    CW = I_FS * 0.602                                  # monospace char width
    fmt = {k: (f"{v:,}" if isinstance(v, int) else v) for k, v in stats.items()}
    fmt["uptime"] = uptime()
    rows = [("title", HANDLE, LINE_WIDTH - len(HANDLE) - 1)]
    for title, items in INFO:
        rows.append(("gap",))
        if title: rows.append(("section", title, LINE_WIDTH - len(title) - 3))
        for k, v in items:
            rows.append(("kv", k, v.format(**fmt).replace("{{", "{").replace("}}", "}")))
    rows.append(("gap",)); rows.append(("prompt",))
    out = []
    y = 42
    for r in rows:
        if r[0] == "gap": y += I_LH * 0.55; continue
        if r[0] == "title":
            out.append(f'<text x="{I_X}" y="{y:.1f}"><tspan fill="{c["handle"]}" font-weight="bold">{escape(r[1])}</tspan>'
                       f'<tspan fill="{c["dots"]}"> {"─" * r[2]}</tspan></text>')
        elif r[0] == "section":
            out.append(f'<text x="{I_X}" y="{y:.1f}"><tspan fill="{c["dots"]}">- </tspan><tspan fill="{c["handle"]}">{escape(r[1])}</tspan>'
                       f'<tspan fill="{c["dots"]}"> {"─" * r[2]}</tspan></text>')
        elif r[0] == "kv":
            k, v = r[1], r[2]
            dots = max(2, LINE_WIDTH - len(k) - len(v) - 4)
            out.append(f'<text x="{I_X}" y="{y:.1f}" xml:space="preserve"><tspan fill="{c["dots"]}">. </tspan>'
                       f'<tspan fill="{c["key"]}">{escape(k)}</tspan><tspan fill="{c["dots"]}">: {"." * dots} </tspan>'
                       f'<tspan fill="{c["value"]}">{escape(v)}</tspan></text>')
        elif r[0] == "prompt":
            out.append(f'<text x="{I_X}" y="{y:.1f}" fill="{c["handle"]}">&gt; <tspan class="cur">█</tspan></text>')
        y += I_LH
    H = int(max(y + 24, A_Y + len(art) * A_LH + 24))
    W = int(I_X + LINE_WIDTH * CW + 30)
    art_txt = "".join(
        f'<tspan x="{A_X}" dy="{A_LH if i else 0}">{escape(l) if l.strip() else " "}</tspan>' for i, l in enumerate(art))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="{A_X}" y1="{A_Y}" x2="{A_X + 350}" y2="{A_Y + len(art) * A_LH}">
<stop offset="0" stop-color="{c["art_from"]}"/><stop offset="1" stop-color="{c["art_to"]}"/></linearGradient>
<style>text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"DejaVu Sans Mono",monospace;white-space:pre}}
.cur{{animation:b 1s steps(1) infinite}}@keyframes b{{50%{{opacity:0}}}}</style></defs>
<rect width="{W}" height="{H}" rx="12" fill="{c["bg"]}" stroke="{c["border"]}" stroke-width="2"/>
<text x="{A_X}" y="{A_Y}" font-size="{A_FS}" fill="url(#g)" xml:space="preserve">{art_txt}</text>
<g font-size="{I_FS}">{"".join(out)}</g>
</svg>'''


def main():
    here = os.path.dirname(os.path.abspath(__file__)); cache = os.path.join(here, "stats_cache.json")
    if "--offline" in sys.argv:
        stats = dict(repos=3, contrib=0, stars=7, commits=120, followers=1, add=5400, dele=900, loc=4500)
    else:
        try:
            stats = fetch_stats(); json.dump(stats, open(cache, "w"))
        except Exception as e:
            print("API failed, using cache:", e)
            stats = json.load(open(cache))
    os.makedirs(os.path.join(here, "assets"), exist_ok=True)
    open(os.path.join(here, "assets", "terminal.svg"), "w").write(build_svg(stats))
    print("wrote assets/terminal.svg")


if __name__ == "__main__":
    main()
