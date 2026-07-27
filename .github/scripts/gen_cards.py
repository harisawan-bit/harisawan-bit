#!/usr/bin/env python3
"""Self-hosted GitHub stats + top-languages cards (theme-aware, no 3rd-party).

Renders stats-dark.svg / stats-light.svg / toplangs-dark.svg / toplangs-light.svg
into dist/, matching the profile's navy/cyan/violet/emerald theme. Published to the
`output` branch by the snake workflow's pages step.

Falls back to a minimal card if the API is unreachable so the README never breaks.
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
USER = os.environ.get("STATS_USER", os.environ.get("GITHUB_REPOSITORY_OWNER", "")).split("/")[0]

THEMES = {
    "dark": dict(
        BG="#0A101F", PANEL="#0C1426", STROKE="rgba(34,211,238,0.28)", TITLE="#22D3EE",
        TEXT="#F8FAFC", MUTED="#94A3B8", DIM="#64748B",
        BAR=["#22D3EE", "#A78BFA", "#10B981", "#6366F1", "#818CF8", "#94A3B8"]),
    "light": dict(
        BG="#FFFFFF", PANEL="#F8FAFC", STROKE="rgba(8,145,178,0.30)", TITLE="#0891B2",
        TEXT="#0F172A", MUTED="#475569", DIM="#94A3B8",
        BAR=["#0891B2", "#7C3AED", "#059669", "#6366F1", "#6366F1", "#94A3B8"]),
}


def api(path, accept="application/vnd.github+json"):
    req = urllib.request.Request(API + path)
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "gh-profile-cards")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def main():
    user, repos, commits, lang_bytes = {}, [], 0, {}
    created = ""
    try:
        user = api(f"/users/{USER}") or {}
        created = (user.get("created_at") or "")[:4]
        repos = api(f"/users/{USER}/repos?per_page=100&type=public") or []
        try:
            commits = api("/search/commits?q=author:" + USER,
                          "application/vnd.github.cloak-preview+json").get("total_count", 0) or 0
        except Exception:
            commits = 0
        for r in repos[:50]:
            try:
                langs = api(f"/repos/{r['full_name']}/languages")
                for k, v in langs.items():
                    lang_bytes[k] = lang_bytes.get(k, 0) + v
            except Exception:
                pass
    except Exception as e:
        print(f"[warn] API error: {e}", file=sys.stderr)

    if not lang_bytes:
        for r in repos:
            l = r.get("language")
            if l:
                lang_bytes[l] = lang_bytes.get(l, 0) + 1

    followers = user.get("followers", 0) or 0
    following = user.get("following", 0) or 0
    public_repos = user.get("public_repos", 0) or 0
    stars = sum(r.get("stargazers_count", 0) or 0 for r in repos)
    forks = sum(r.get("forks_count", 0) or 0 for r in repos)

    total = sum(lang_bytes.values()) or 1
    top_langs = sorted(lang_bytes.items(), key=lambda x: -x[1])[:7]
    top3 = ", ".join(l for l, _ in sorted(lang_bytes.items(), key=lambda x: -x[1])[:3]) or "—"

    metrics = [
        ("Repos", public_repos), ("Stars", stars), ("Followers", followers),
        ("Following", following), ("Forks", forks), ("Commits", commits),
    ]

    os.makedirs("dist", exist_ok=True)
    for name, t in THEMES.items():
        write_stats(t, name, metrics, created, top3)
        write_toplangs(t, name, top_langs, total)
    print(f"wrote stats + toplangs cards for {USER} ({len(top_langs)} langs)")


def write_stats(t, theme, metrics, created, top3):
    w, h = 500, 205
    col = (w - 40) / 3
    cells = ""
    for i, (label, val) in enumerate(metrics):
        cx = 20 + col * (i % 3) + 8
        ry = 92 if i < 3 else 142
        colr = t["BAR"][i % len(t["BAR"])]
        cells += (
            f'<text x="{cx:.0f}" y="{ry}" font-size="26" font-weight="700" fill="{colr}">{val}</text>'
            f'<text x="{cx:.0f}" y="{ry+18}" font-size="12" fill="{t["MUTED"]}">{esc(label)}</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" role="img" aria-label="GitHub stats">'
        f'<rect width="{w}" height="{h}" rx="12" fill="{t["PANEL"]}" stroke="{t["STROKE"]}"/>'
        f'<text x="20" y="30" font-size="15" font-weight="700" fill="{t["TITLE"]}">GitHub Stats &#183; @{esc(USER)}</text>'
        f'<line x1="20" y1="42" x2="{w-20}" y2="42" stroke="{t["STROKE"]}" stroke-width="1"/>'
        f'{cells}'
        f'<text x="20" y="{h-14}" font-size="11" fill="{t["DIM"]}">Member since {esc(created)} &#183; Top: {esc(top3)}</text>'
        f'</svg>'
    )
    with open(f"dist/stats-{theme}.svg", "w", encoding="utf-8") as f:
        f.write(svg)


def write_toplangs(t, theme, top_langs, total):
    w, h = 500, 205
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" role="img" aria-label="Top languages">',
        f'<rect width="{w}" height="{h}" rx="12" fill="{t["PANEL"]}" stroke="{t["STROKE"]}"/>',
        f'<text x="20" y="30" font-size="15" font-weight="700" fill="{t["TITLE"]}">Top Languages</text>',
        f'<line x1="20" y1="42" x2="{w-20}" y2="42" stroke="{t["STROKE"]}" stroke-width="1"/>',
    ]
    max_bar = 250
    y = 64
    for i, (lang, v) in enumerate(top_langs):
        frac = v / total
        bw = max(frac * max_bar, 3)
        colr = t["BAR"][i % len(t["BAR"])]
        svg.append(f'<text x="20" y="{y+4}" font-size="12" fill="{t["TEXT"]}">{esc(lang)}</text>')
        svg.append(f'<rect x="115" y="{y-8}" width="{max_bar}" height="12" rx="6" fill="{t["STROKE"]}" opacity="0.35"/>')
        svg.append(f'<rect x="115" y="{y-8}" width="{bw:.1f}" height="12" rx="6" fill="{colr}"/>')
        svg.append(f'<text x="{115+max_bar+8}" y="{y+4}" font-size="12" fill="{t["MUTED"]}">{frac*100:.0f}%</text>')
        y += 22
    svg.append('</svg>')
    with open(f"dist/toplangs-{theme}.svg", "w", encoding="utf-8") as f:
        f.write("".join(svg))


if __name__ == "__main__":
    main()
