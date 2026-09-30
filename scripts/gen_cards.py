#!/usr/bin/env python3
"""
Terminal-themed profile cards for github.com/Suyash2527.

Generates (into ./assets):
  header.svg   animated terminal intro
  stats.svg    neofetch-style live GitHub stats
  langs.svg    top languages
  contrib.svg  contribution heatmap + streaks

Runs inside GitHub Actions with the built-in GITHUB_TOKEN, so there are
no third-party services and no rate limits. `--mock file.json` renders
from saved data for local previews.
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from html import escape

USER = os.environ.get("GH_USER", "Suyash2527")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

# ── palette ────────────────────────────────────────────────────────────
BG, BAR, BORDER = "#0d1117", "#161b22", "#30363d"
TXT, DIM, FAINT = "#c9d1d9", "#8b949e", "#484f58"
GREEN, NEON, CYAN, AMBER, PINK = "#39d353", "#00ff9c", "#22d3ee", "#f59e0b", "#f472b6"
HEAT = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
FONT = "'JetBrains Mono','Fira Code','SF Mono',Consolas,'Liberation Mono',Menlo,monospace"

# ── data ───────────────────────────────────────────────────────────────
QUERY = """
query($login:String!){
  user(login:$login){
    login createdAt
    followers{totalCount}
    pullRequests{totalCount}
    issues{totalCount}
    repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST,ISSUE,REPOSITORY]){totalCount}
    repositories(ownerAffiliations:OWNER,isFork:false,first:100,privacy:PUBLIC){
      totalCount
      nodes{ stargazerCount forkCount
        languages(first:10,orderBy:{field:SIZE,direction:DESC}){ edges{ size node{ name color } } } }
    }
    contributionsCollection{
      totalCommitContributions
      contributionYears
      contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } }
    }
  }
}"""


def gql(query, variables, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": USER},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]


def fetch(token):
    u = gql(QUERY, {"login": USER}, token)["user"]
    years = u["contributionsCollection"]["contributionYears"]
    parts = [
        f'y{y}: contributionsCollection(from:"{y}-01-01T00:00:00Z",to:"{y}-12-31T23:59:59Z"){{contributionCalendar{{totalContributions}}}}'
        for y in years
    ]
    yq = "query($login:String!){user(login:$login){" + " ".join(parts) + "}}"
    yd = gql(yq, {"login": USER}, token)["user"] if parts else {}
    all_time = sum(v["contributionCalendar"]["totalContributions"] for v in yd.values())

    langs = {}
    stars = 0
    for r in u["repositories"]["nodes"]:
        stars += r["stargazerCount"]
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            langs.setdefault(n, {"size": 0, "color": e["node"]["color"] or DIM})
            langs[n]["size"] += e["size"]

    days = [d for w in u["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    return {
        "joined": u["createdAt"][:4],
        "repos": u["repositories"]["totalCount"],
        "stars": stars,
        "followers": u["followers"]["totalCount"],
        "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "contributed_to": u["repositoriesContributedTo"]["totalCount"],
        "commits_year": u["contributionsCollection"]["totalCommitContributions"],
        "contrib_year": u["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "contrib_all": all_time,
        "langs": langs,
        "days": days,
    }


def streaks(days):
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    cur, i = 0, len(counts) - 1
    if i >= 0 and counts[i] == 0:  # today not counted yet
        i -= 1
    while i >= 0 and counts[i]:
        cur += 1
        i -= 1
    return cur, longest


# ── svg helpers ────────────────────────────────────────────────────────
def window(w, h, title, body, extra_css=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">
<style>
text{{font-family:{FONT};}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
@keyframes blink{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
.f{{opacity:0;animation:fade .45s ease-out forwards}}
.cur{{animation:blink 1s step-end infinite}}
{extra_css}
</style>
<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="10" fill="{BG}" stroke="{BORDER}"/>
<path d="M0.5 36V10.5a10 10 0 0 1 10-10h{w-21}a10 10 0 0 1 10 10V36z" fill="{BAR}"/>
<line x1="0.5" y1="36" x2="{w-0.5}" y2="36" stroke="{BORDER}"/>
<circle cx="20" cy="18" r="6" fill="#ff5f57"/><circle cx="40" cy="18" r="6" fill="#febc2e"/><circle cx="60" cy="18" r="6" fill="#28c840"/>
<text x="{w/2}" y="23" text-anchor="middle" font-size="12.5" fill="{DIM}">{escape(title)}</text>
{body}
</svg>"""


def t(x, y, s, fill=TXT, size=14, weight="normal", cls="", delay=None, anchor="start"):
    style = f' style="animation-delay:{delay:.2f}s"' if delay is not None else ""
    c = f' class="{cls}"' if cls else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}" xml:space="preserve"{c}{style}>{s}</text>')


def prompt(x, y, cmd, delay, size=14):
    return (f'<g class="f" style="animation-delay:{delay:.2f}s">'
            f'<text x="{x}" y="{y}" font-size="{size}" xml:space="preserve">'
            f'<tspan fill="{NEON}">suyash</tspan><tspan fill="{DIM}">@</tspan><tspan fill="{CYAN}">cloud</tspan>'
            f'<tspan fill="{DIM}">:</tspan><tspan fill="{AMBER}">~</tspan><tspan fill="{DIM}">$ </tspan>'
            f'<tspan fill="{TXT}">{escape(cmd)}</tspan></text></g>')


def typed(x, y, cmd, start, uid, size=14, cps=28):
    """A prompt whose command is revealed character by character (SMIL clip)."""
    pre = 16  # len('suyash@cloud:~$ ')
    cw = size * 0.6
    total = (pre + len(cmd)) * cw + 4
    dur = max(len(cmd) / cps, 0.3)
    return (f'<clipPath id="c{uid}"><rect x="{x}" y="{y-size}" height="{size+6}" width="{pre*cw}">'
            f'<animate attributeName="width" from="{pre*cw}" to="{total}" begin="{start:.2f}s" dur="{dur:.2f}s" fill="freeze"/>'
            f'</rect></clipPath><g clip-path="url(#c{uid})">{prompt(x, y, cmd, start - 0.35, size)}</g>')


# ── pixel banner (from figlet ansi_shadow) ─────────────────────────────
BANNER = [
    "███████╗██╗   ██╗██╗   ██╗ █████╗ ███████╗██╗  ██╗",
    "██╔════╝██║   ██║╚██╗ ██╔╝██╔══██╗██╔════╝██║  ██║",
    "███████╗██║   ██║ ╚████╔╝ ███████║███████╗███████║",
    "╚════██║██║   ██║  ╚██╔╝  ██╔══██║╚════██║██╔══██║",
    "███████║╚██████╔╝   ██║   ██║  ██║███████║██║  ██║",
    "╚══════╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝",
]


SEG = {"═": "h", "║": "v", "╗": "ld", "╔": "rd", "╝": "lu", "╚": "ru"}


def banner(x0, y0, cw, ch, start, grad="g", shadow="#1f6f5a"):
    """Render ANSI-shadow figlet text as crisp pixels + line-drawn shadows."""
    out = []
    for r, line in enumerate(BANNER):
        for c, chr_ in enumerate(line):
            if chr_ == " ":
                continue
            d = start + c * 0.018
            x, y = x0 + c * cw, y0 + r * ch
            if chr_ == "█":
                out.append(f'<rect class="f" style="animation-delay:{d:.2f}s" x="{x:.1f}" y="{y:.1f}" '
                           f'width="{cw+0.8:.1f}" height="{ch+0.8:.1f}" fill="url(#{grad})"/>')
                continue
            cx, cy = x + cw / 2, y + ch / 2
            segs = SEG.get(chr_, "h")
            parts = []
            if segs == "h":
                parts.append(f"M{x:.1f} {cy:.1f}H{x+cw:.1f}")
            elif segs == "v":
                parts.append(f"M{cx:.1f} {y:.1f}V{y+ch:.1f}")
            else:
                parts.append(f"M{(x if segs[0]=='l' else x+cw):.1f} {cy:.1f}H{cx:.1f}")
                parts.append(f"M{cx:.1f} {cy:.1f}V{(y+ch if segs[1]=='d' else y):.1f}")
            out.append(f'<path class="f" style="animation-delay:{d:.2f}s" d="{" ".join(parts)}" '
                       f'stroke="{shadow}" stroke-width="2" fill="none"/>')
    return "\n".join(out)


def header():
    W, H = 900, 500
    x = 28
    b = []
    b.append('<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="30" x2="600" y1="0" y2="0"><stop offset="0" stop-color="#00ff9c"/>'
             '<stop offset=".55" stop-color="#22d3ee"/><stop offset="1" stop-color="#818cf8"/></linearGradient></defs>')
    b.append(typed(x, 70, "figlet -f ansi_shadow suyash", 0.4, "h0"))
    b.append(banner(x + 4, 90, 11.2, 14, 1.6))
    b.append(t(x + 590, 110, "Suyash Makrand Chaudhari", TXT, 15, "bold", "f", 2.6))
    b.append(t(x + 590, 134, "Cloud &amp; DevOps  ·  Web3", CYAN, 13, cls="f", delay=2.8))
    b.append(t(x + 590, 156, "Designer × Developer", PINK, 13, cls="f", delay=3.0))
    b.append(t(x + 590, 178, "Nashik, India  ·  IST (UTC+5:30)", DIM, 12, cls="f", delay=3.2))

    y = 222
    b.append(typed(x, y, "whoami", 3.5, "h1"))
    b.append(t(x, y + 24, "→ Engineering student who automates infra, ships dApps &amp; designs the UI too.", TXT, 14, cls="f", delay=4.0))

    y += 62
    b.append(typed(x, y, "cat status.log", 4.5, "h2"))
    rows = [
        (f'<tspan fill="{GREEN}">[ OK ]</tspan> AWS Certified Cloud Practitioner', 5.0),
        (f'<tspan fill="{GREEN}">[ OK ]</tspan> Organiser · GDG on Campus MET BKC  ·  Core Team · GDG Nashik', 5.2),
        (f'<tspan fill="{GREEN}">[ OK ]</tspan> GSSoC 2026 contributor · global rank #332', 5.4),
        (f'<tspan fill="{AMBER}">[ .. ]</tspan> AWS Solutions Architect – Associate  <tspan fill="{DIM}">(in progress)</tspan>', 5.6),
    ]
    for i, (s, d) in enumerate(rows):
        b.append(t(x, y + 24 + i * 21, s, TXT, 13.5, cls="f", delay=d))

    y += 24 + 4 * 21 + 26
    b.append(typed(x, y, "./deploy.sh --env=prod", 6.0, "h3"))
    by = y + 16
    b.append(f'<g class="f" style="animation-delay:6.6s"><rect x="{x}" y="{by}" width="420" height="14" rx="3" fill="#21262d"/>'
             f'<rect x="{x}" y="{by}" width="0" height="14" rx="3" fill="url(#g)">'
             f'<animate attributeName="width" from="0" to="420" begin="6.7s" dur="1.8s" fill="freeze"/></rect></g>')
    b.append(t(x + 436, by + 12, f'<tspan fill="{GREEN}">✔</tspan> build passed  <tspan fill="{GREEN}">✔</tspan> live in prod', TXT, 13.5, cls="f", delay=8.6))
    last = prompt(x, H - 24, "", 8.9)
    b.append(f'{last}<g class="f" style="animation-delay:8.9s">'
             f'<rect class="cur" x="{x + 16*8.4 + 2}" y="{H-37}" width="9" height="17" fill="{NEON}"/></g>')
    return window(W, H, "suyash@cloud: ~ — zsh", "\n".join(b))


# ── stats card ─────────────────────────────────────────────────────────
def stats_card(d):
    W, H = 520, 350
    cur, best = streaks(d["days"])
    b = [prompt(24, 64, "neofetch --github", 0.1, 13)]
    # monogram "S" from the banner
    b.append('<defs><linearGradient id="gs" gradientUnits="userSpaceOnUse" x1="30" x2="134" y1="0" y2="0">'
             f'<stop offset="0" stop-color="{NEON}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient></defs>')
    saved = BANNER[:]
    BANNER[:] = [row[:8] for row in saved]
    b.append(banner(30, 92, 13, 20, 0.3, grad="gs"))
    BANNER[:] = saved
    kx, vx, y = 170, 305, 92
    b.append(t(kx, y, f'<tspan fill="{NEON}" font-weight="bold">suyash</tspan><tspan fill="{DIM}">@</tspan><tspan fill="{CYAN}" font-weight="bold">github</tspan>', size=14, cls="f", delay=0.4))
    b.append(t(kx, y + 16, "─" * 22, FAINT, 12, cls="f", delay=0.45))
    rows = [
        ("Joined", f"{d['joined']}  ·  {dt.date.today().year - int(d['joined'])}y uptime"),
        ("Public repos", d["repos"]),
        ("Stars earned", d["stars"]),
        ("Commits (1y)", d["commits_year"]),
        ("Contribs (1y)", d["contrib_year"]),
        ("Contribs (all)", d["contrib_all"]),
        ("PRs · Issues", f"{d['prs']} · {d['issues']}"),
        ("Contributed to", f"{d['contributed_to']} repos"),
        ("Streak", f"{cur}d now · {best}d best"),
        ("Followers", d["followers"]),
    ]
    for i, (k, v) in enumerate(rows):
        yy = y + 40 + i * 20
        dl = 0.55 + i * 0.07
        b.append(t(kx, yy, k, CYAN, 13, "bold", "f", dl))
        b.append(t(vx, yy, escape(str(v)), TXT, 13, cls="f", delay=dl))
    for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840", CYAN, "#818cf8", PINK, NEON, TXT]):
        b.append(f'<rect class="f" style="animation-delay:1.4s" x="{30 + (i%4)*26}" y="{240 + (i//4)*26}" width="22" height="22" rx="3" fill="{c}"/>')
    b.append(t(30, 318, f"synced {dt.datetime.utcnow():%d %b %Y}", FAINT, 10.5))
    return window(W, H, "neofetch", "\n".join(b))


# ── languages card ─────────────────────────────────────────────────────
def langs_card(d, n=7):
    W, H = 370, 350
    items = sorted(d["langs"].items(), key=lambda kv: -kv[1]["size"])[:n]
    total = sum(v["size"] for _, v in items) or 1
    b = [prompt(22, 64, "gh lang --top", 0.1, 13)]
    y = 100
    for i, (name, v) in enumerate(items):
        pct = v["size"] / total * 100
        yy = y + i * 31
        dl = 0.3 + i * 0.1
        b.append(t(22, yy, escape(name), TXT, 13, cls="f", delay=dl))
        b.append(t(W - 22, yy, f"{pct:4.1f}%", DIM, 12.5, cls="f", delay=dl, anchor="end"))
        bw = (W - 44) * pct / 100
        b.append(f'<rect x="22" y="{yy+7}" width="{W-44}" height="7" rx="3.5" fill="#21262d"/>')
        b.append(f'<rect x="22" y="{yy+7}" width="{max(bw,3):.1f}" height="7" rx="3.5" fill="{v["color"]}" '
                 f'style="transform-origin:22px 0;transform:scaleX(0);animation:grow .9s ease-out {dl+0.1:.2f}s forwards"/>')
    return window(W, H, "languages", "\n".join(b))


# ── contribution heatmap ───────────────────────────────────────────────
def contrib_card(d):
    days = d["days"]
    cur, best = streaks(days)
    W, H = 900, 250
    cell, gap = 12, 3.5
    x0, y0 = 40, 92
    nz = sorted(c["contributionCount"] for c in days if c["contributionCount"])
    q = [nz[int(len(nz) * p)] for p in (0.25, 0.5, 0.75)] if nz else [1, 2, 3]

    def lvl(c):
        if not c:
            return 0
        return 1 + sum(c > t_ for t_ in q)

    first = dt.date.fromisoformat(days[0]["date"])
    off = (first.weekday() + 1) % 7  # Sunday = 0
    b = [prompt(24, 64, "git log --graph --since='1 year ago'", 0.1, 13)]
    last_month = None
    for i, day in enumerate(days):
        k = i + off
        col, row = k // 7, k % 7
        x, y = x0 + col * (cell + gap), y0 + row * (cell + gap)
        date = dt.date.fromisoformat(day["date"])
        if row == 0 or i == 0:
            if date.month != last_month and 1 < col < 52:
                b.append(t(x, y0 - 8, date.strftime("%b"), DIM, 10.5))
                last_month = date.month
        b.append(f'<rect class="f" style="animation-delay:{0.2+col*0.025:.2f}s" x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" rx="2.5" '
                 f'fill="{HEAT[lvl(day["contributionCount"])]}"><title>{day["date"]}: {day["contributionCount"]}</title></rect>')
    fy = H - 26
    b.append(t(x0, fy, f'<tspan fill="{NEON}">{d["contrib_year"]}</tspan> contributions in the last year   '
                        f'<tspan fill="{DIM}">│</tspan>   current streak <tspan fill="{AMBER}">{cur}d</tspan>   '
                        f'<tspan fill="{DIM}">│</tspan>   longest <tspan fill="{PINK}">{best}d</tspan>', TXT, 13, cls="f", delay=1.6))
    lx = W - 40 - 5 * 15
    b.append(t(lx - 8, fy, "less", DIM, 10.5, anchor="end"))
    for i, c in enumerate(HEAT):
        b.append(f'<rect x="{lx + i*15}" y="{fy-10}" width="11" height="11" rx="2" fill="{c}"/>')
    b.append(t(lx + 5 * 15 + 2, fy, "more", DIM, 10.5))
    return window(W, H, "contributions", "\n".join(b))


def main():
    os.makedirs(OUT, exist_ok=True)
    if len(sys.argv) > 2 and sys.argv[1] == "--mock":
        data = json.load(open(sys.argv[2]))
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("Set GH_TOKEN")
        data = fetch(token)
    files = {
        "header.svg": header(),
        "stats.svg": stats_card(data),
        "langs.svg": langs_card(data),
        "contrib.svg": contrib_card(data),
    }
    for name, svg in files.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print("wrote", name)


if __name__ == "__main__":
    main()
