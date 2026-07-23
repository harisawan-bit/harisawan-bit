#!/usr/bin/env python3
"""Self-hosted GitHub stats SVG generator.

Pulls public profile metrics via the GitHub REST API (works with the
repo GITHUB_TOKEN in Actions) and renders a single SVG card. No third-party
stat service required, so it can never 503/402 on us.
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
USER = os.environ.get("STATS_USER", os.environ.get("GITHUB_REPOSITORY_OWNER", "")).split("/")[0]


def api(path, accept="application/vnd.github+json"):
    req = urllib.request.Request(API + path)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "gh-profile-stats")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def safe(fn, default=None):
    try:
        return fn()
    except Exception as e:
        print(f"[warn] {fn.__name__}: {e}", file=sys.stderr)
        return default


def main():
    user = safe(lambda: api(f"/users/{USER}"), {})
    followers = user.get("followers", 0) or 0
    following = user.get("following", 0) or 0
    public_repos = user.get("public_repos", 0) or 0
    created = user.get("created_at", "")[:4]

    repos = safe(lambda: api(f"/users/{USER}/repos?per_page=100&type=public"), []) or []
    stars = sum(r.get("stargazers_count", 0) or 0 for r in repos)
    forks = sum(r.get("forks_count", 0) or 0 for r in repos)

    # top languages
    lang_counter = {}
    for r in repos:
        l = r.get("language")
        if l:
            lang_counter[l] = lang_counter.get(l, 0) + 1
    top_langs = sorted(lang_counter.items(), key=lambda x: -x[1])[:4]
    langs_str = ", ".join(f"{l}({c})" for l, c in top_langs) or "—"

    # total commits (search API; may be unavailable)
    commits = safe(
        lambda: api("/search/commits?q=author:" + USER,
                    "application/vnd.github.cloak-preview+json").get("total_count"),
        0,
    ) or 0

    metrics = [
        ("Repos", public_repos),
        ("Stars", stars),
        ("Followers", followers),
        ("Following", following),
        ("Forks", forks),
        ("Commits", commits),
    ]

    # ---- render SVG ----
    w, h = 900, 150
    items = metrics
    col_w = w / len(items)
    cells = ""
    bar_colors = ["#6a11cb", "#2575fc", "#00c6ff", "#ff6a00", "#11998e", "#fc466b"]
    for i, (label, val) in enumerate(items):
        cx = col_w * i + col_w / 2
        col = bar_colors[i % len(bar_colors)]
        cells += f'''
    <g transform="translate({cx:.0f},55)">
      <text x="0" y="0" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="34" font-weight="bold" fill="{col}">{val}</text>
      <text x="0" y="26" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="#8b949e">{label}</text>
    </g>'''
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <linearGradient id="cardbg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#161b22"/>
      <stop offset="100%" stop-color="#0d1117"/>
    </linearGradient>
  </defs>
  <rect width="{w}" height="{h}" rx="12" fill="url(#cardbg)" stroke="#30363d"/>
  <text x="{w/2:.0f}" y="26" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="bold" fill="#e6edf3">GitHub Stats · member since {created}</text>
  <line x1="20" y1="38" x2="{w-20}" y2="38" stroke="#30363d" stroke-width="1"/>{cells}
  <text x="{w/2:.0f}" y="{h-12}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="#6e7681">Top languages: {langs_str}</text>
</svg>'''
    os.makedirs("dist", exist_ok=True)
    with open("dist/stats.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote dist/stats.svg ({len(svg)} bytes) for {USER}")


if __name__ == "__main__":
    main()
