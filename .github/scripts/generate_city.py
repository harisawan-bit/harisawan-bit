#!/usr/bin/env python3
"""Generate an original isometric 3D Contribution City SVG from GitHub activity."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import math
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DAY_RE = re.compile(
    r'<td\b[^>]*\bdata-date="(\d{4}-\d{2}-\d{2})"[^>]*\bid="([^"]+)"[^>]*\bdata-level="([0-4])"'
    r'|<td\b[^>]*\bid="([^"]+)"[^>]*\bdata-date="(\d{4}-\d{2}-\d{2})"[^>]*\bdata-level="([0-4])"'
    r'|<td\b[^>]*\bdata-date="(\d{4}-\d{2}-\d{2})"[^>]*\bdata-level="([0-4])"[^>]*\bid="([^"]+)"'
)
TOOLTIP_RE = re.compile(
    r'<tool-tip\b[^>]*\bfor="([^"]+)"[^>]*>(.*?)</tool-tip>', re.DOTALL
)
COUNT_RE = re.compile(r"(\d[\d,]*)\s+contribution")

# (top, left, right) face colors per GitHub contribution level 0..4
PALETTE = {
    0: ("#172136", "#101829", "#0b111e"),
    1: ("#0e7490", "#0b586e", "#083d4d"),
    2: ("#10b981", "#059669", "#047857"),
    3: ("#34d399", "#10b981", "#059669"),
    4: ("#a7f3d0", "#34d399", "#059669"),
}


@dataclass(frozen=True)
class DayStat:
    date: str
    level: int
    count: int


def fetch_contributions_html(username: str) -> str:
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "contribution-city/1.0",
            "Accept": "text/html",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_contributions(page_html: str) -> list[DayStat]:
    counts_by_id: dict[str, int] = {}
    for cell_id, text in TOOLTIP_RE.findall(page_html):
        m = COUNT_RE.search(text)
        counts_by_id[cell_id] = int(m.group(1).replace(",", "")) if m else 0

    days: list[DayStat] = []
    for m in DAY_RE.finditer(page_html):
        g = m.groups()
        if g[0]:
            date_s, cell_id, level_s = g[0], g[1], g[2]
        elif g[3]:
            cell_id, date_s, level_s = g[3], g[4], g[5]
        else:
            date_s, level_s, cell_id = g[6], g[7], g[8]
        level = int(level_s)
        count = counts_by_id.get(cell_id, level * 3)
        days.append(DayStat(date=date_s, level=level, count=count))

    days.sort(key=lambda d: d.date)
    return days


def demo_contributions() -> list[DayStat]:
    """Deterministic 53-week skyline for offline preview and testing."""
    start = dt.date(2025, 11, 16)
    days: list[DayStat] = []
    for i in range(371):
        d = start + dt.timedelta(days=i)
        # Wave + bursts to form a realistic city skyline
        wave = math.sin(i * 0.17) + math.cos(i * 0.043)
        spike = 18 if (i % 29 == 0 or i % 47 == 0) else 0
        raw = max(0, int((wave + 1.1) * 5.2) + spike - (4 if d.weekday() >= 5 else 0))
        if raw == 0:
            lvl = 0
        elif raw <= 4:
            lvl = 1
        elif raw <= 9:
            lvl = 2
        elif raw <= 16:
            lvl = 3
        else:
            lvl = 4
        days.append(DayStat(date=d.isoformat(), level=lvl, count=raw))
    return days


def compute_stats(days: list[DayStat]) -> dict[str, object]:
    total = sum(d.count for d in days)
    active = sum(1 for d in days if d.count > 0)
    peak = max(days, key=lambda d: d.count, default=DayStat("", 0, 0))

    longest = 0
    cur = 0
    for d in days:
        if d.count > 0:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0

    # Current streak from the latest day (allow today to be 0 if yesterday was active)
    current = 0
    idx = len(days) - 1
    if idx >= 0 and days[idx].count == 0:
        idx -= 1
    while idx >= 0 and days[idx].count > 0:
        current += 1
        idx -= 1

    return {
        "total": total,
        "active": active,
        "peak_count": peak.count,
        "peak_date": peak.date,
        "longest_streak": longest,
        "current_streak": current,
    }


def iso_project(week: int, day: int, origin_x: float, origin_y: float) -> tuple[float, float]:
    step_x, step_y = 12.0, 6.0
    x = origin_x + (week - day) * step_x
    y = origin_y + (week + day) * step_y
    return x, y


def building_svg(cx: float, cy: float, h: float, level: int) -> str:
    hw, hh = 5.1, 2.55
    top_c, left_c, right_c = PALETTE[level]

    # Top diamond (shifted up by h)
    ty = cy - h
    top_pts = f"{cx:.1f},{ty - hh:.1f} {cx + hw:.1f},{ty:.1f} {cx:.1f},{ty + hh:.1f} {cx - hw:.1f},{ty:.1f}"
    left_pts = f"{cx - hw:.1f},{ty:.1f} {cx:.1f},{ty + hh:.1f} {cx:.1f},{cy + hh:.1f} {cx - hw:.1f},{cy:.1f}"
    right_pts = f"{cx:.1f},{ty + hh:.1f} {cx + hw:.1f},{ty:.1f} {cx + hw:.1f},{cy:.1f} {cx:.1f},{cy + hh:.1f}"

    parts = [
        f'<polygon points="{left_pts}" fill="{left_c}" stroke="#060a13" stroke-width="0.45"/>',
        f'<polygon points="{right_pts}" fill="{right_c}" stroke="#060a13" stroke-width="0.45"/>',
        f'<polygon points="{top_pts}" fill="{top_c}" stroke="#060a13" stroke-width="0.45"/>',
    ]

    # Lit window specks on taller buildings
    if h >= 22:
        rows = min(5, int((h - 10) // 12))
        for r in range(rows):
            wy = ty + 7 + r * 11
            parts.append(
                f'<rect x="{cx - 3.2:.1f}" y="{wy:.1f}" width="1.6" height="2.2" rx="0.4" fill="#ecfdf5" fill-opacity="0.42"/>'
            )
            parts.append(
                f'<rect x="{cx + 1.6:.1f}" y="{wy + 0.6:.1f}" width="1.6" height="2.2" rx="0.4" fill="#ecfdf5" fill-opacity="0.24"/>'
            )

    return "".join(parts)


def render_svg(username: str, days: list[DayStat]) -> str:
    if not days:
        raise ValueError("No contribution days to render")

    stats = compute_stats(days)
    max_count = max(1, int(stats["peak_count"]))

    # Map each day into (week_index, sunday_0_weekday)
    first_date = dt.date.fromisoformat(days[0].date)
    # GitHub calendar columns start on Sunday
    start_sunday = first_date - dt.timedelta(days=(first_date.weekday() + 1) % 7)

    grid_cells: list[tuple[int, int, DayStat]] = []
    for d in days:
        cur_date = dt.date.fromisoformat(d.date)
        offset = (cur_date - start_sunday).days
        week = offset // 7
        weekday = offset % 7
        if 0 <= week < 54:
            grid_cells.append((week, weekday, d))

    # Painter's algorithm: back-to-front by (week + weekday)
    grid_cells.sort(key=lambda item: (item[0] + item[1], item[0]))

    origin_x, origin_y = 210.0, 148.0
    buildings: list[str] = []
    for week, weekday, d in grid_cells:
        cx, cy = iso_project(week, weekday, origin_x, origin_y)
        if d.level == 0 or d.count == 0:
            h = 2.6
        else:
            h = 8.0 + ((d.count / max_count) ** 0.72) * 86.0
        buildings.append(building_svg(cx, cy, h, d.level))

    # Subtle background stars
    stars = "".join(
        f'<circle cx="{(i * 97 + 41) % 940 + 10}" cy="{(i * 53 + 19) % 150 + 18}" '
        f'r="{0.7 + (i % 3) * 0.45:.2f}" fill="#94a3b8" fill-opacity="{0.15 + (i % 4) * 0.08:.2f}"/>'
        for i in range(36)
    )

    legend_items = "".join(
        f'<rect x="{64 + i * 16}" y="505" width="11" height="11" rx="2.5" fill="{PALETTE[i][0]}"/>'
        for i in range(5)
    )

    safe_user = html.escape(username)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540" role="img" aria-label="Contribution City for @{safe_user}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#060a14"/>
      <stop offset="55%" stop-color="#0b1222"/>
      <stop offset="100%" stop-color="#070c17"/>
    </linearGradient>
    <radialGradient id="glow" cx="52%" cy="56%" r="50%">
      <stop offset="0%" stop-color="#10b981" stop-opacity="0.14"/>
      <stop offset="100%" stop-color="#10b981" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <rect width="960" height="540" rx="18" fill="url(#bg)"/>
  <rect width="960" height="540" rx="18" fill="url(#glow)"/>
  <rect x="0.5" y="0.5" width="959" height="539" rx="17.5" fill="none" stroke="#1e293b"/>
  {stars}

  <!-- Header -->
  <text x="34" y="38" fill="#34d399" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="11" font-weight="700" letter-spacing="2">CONTRIBUTION CITY // 365-DAY SKYLINE</text>
  <text x="34" y="68" fill="#f8fafc" font-family="system-ui, -apple-system, Segoe UI, sans-serif" font-size="26" font-weight="700">@{safe_user}</text>

  <!-- Stat Pills -->
  <g font-family="ui-monospace, SFMono-Regular, Menlo, monospace">
    <rect x="444" y="24" width="112" height="50" rx="10" fill="#0f172a" stroke="#1e293b"/>
    <text x="458" y="42" fill="#64748b" font-size="9.5" letter-spacing="1">TOTAL</text>
    <text x="458" y="63" fill="#f8fafc" font-size="17" font-weight="700">{stats["total"]:,}</text>

    <rect x="566" y="24" width="142" height="50" rx="10" fill="#0f172a" stroke="#1e293b"/>
    <text x="580" y="42" fill="#64748b" font-size="9.5" letter-spacing="1">STREAK</text>
    <text x="580" y="63" fill="#34d399" font-size="17" font-weight="700">{stats["current_streak"]}d <tspan fill="#64748b" font-size="11" font-weight="400">({stats["longest_streak"]}d max)</tspan></text>

    <rect x="718" y="24" width="100" height="50" rx="10" fill="#0f172a" stroke="#1e293b"/>
    <text x="732" y="42" fill="#64748b" font-size="9.5" letter-spacing="1">PEAK DAY</text>
    <text x="732" y="63" fill="#f8fafc" font-size="17" font-weight="700">{stats["peak_count"]}</text>

    <rect x="828" y="24" width="100" height="50" rx="10" fill="#0f172a" stroke="#1e293b"/>
    <text x="842" y="42" fill="#64748b" font-size="9.5" letter-spacing="1">ACTIVE</text>
    <text x="842" y="63" fill="#f8fafc" font-size="17" font-weight="700">{stats["active"]}d</text>
  </g>

  <!-- Isometric Skyline -->
  <g>
    {"".join(buildings)}
  </g>

  <!-- Footer -->
  <text x="34" y="514" fill="#64748b" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5">Less</text>
  {legend_items}
  <text x="150" y="514" fill="#64748b" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5">More</text>
  <text x="926" y="514" text-anchor="end" fill="#64748b" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10.5">github.com/{safe_user}</text>
</svg>
"""


def run_self_test() -> None:
    sample = (
        '<td id="contribution-day-component-0-0" data-date="2026-01-04" data-level="2"></td>'
        '<tool-tip for="contribution-day-component-0-0">7 contributions on Jan 4.</tool-tip>'
        '<td data-date="2026-01-05" data-level="0" id="contribution-day-component-0-1"></td>'
        '<tool-tip for="contribution-day-component-0-1">No contributions on Jan 5.</tool-tip>'
    )
    parsed = parse_contributions(sample)
    assert len(parsed) == 2, f"Expected 2 days, got {len(parsed)}"
    assert parsed[0] == DayStat("2026-01-04", 2, 7)
    assert parsed[1] == DayStat("2026-01-05", 0, 0)

    demo = demo_contributions()
    assert len(demo) == 371
    svg = render_svg("test-user", demo)
    assert svg.startswith("<svg ") and "</svg>" in svg
    assert "@test-user" in svg
    print("Self-test passed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an isometric Contribution City SVG.")
    parser.add_argument("username", nargs="?", default="octocat", help="GitHub username")
    parser.add_argument("-o", "--output", default="contribution-city.svg", help="Output SVG path")
    parser.add_argument("--demo", action="store_true", help="Use deterministic demo data")
    parser.add_argument("--self-test", action="store_true", help="Run built-in assertions")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        return 0

    days = demo_contributions() if args.demo else parse_contributions(fetch_contributions_html(args.username))
    svg = render_svg(args.username, days)
    Path(args.output).write_text(svg, encoding="utf-8")
    print(f"Wrote {args.output} ({len(days)} days) for @{args.username}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
