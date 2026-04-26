"""Generate docs/week-NN.html for every calendar week in schedule.yaml.

Follows the visual pattern of docs/weekly-template.html exactly — Tailwind
CDN + earth-tone palette + glass cards + timeline. Self-contained HTML per
week so GitHub Pages can serve them directly.

Usage:
  python3 scripts/build_site.py              # build all 18 weeks
  python3 scripts/build_site.py 1            # just week 1
  python3 scripts/build_site.py 1 3 5        # weeks 1, 3, 5
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import yaml  # type: ignore[import-not-found]

HERE = Path(__file__).parent
REPO = HERE.parent
META = REPO / "plan" / "meta.yaml"
SCHED = REPO / "plan" / "schedule.yaml"
DOCS = REPO / "docs"

LOAD_LABEL = {1: "Deload", 2: "Moderate", 3: "Heavy", 4: "Max"}
LOAD_REPS = {1: "12–15", 2: "9–11", 3: "6–8", 4: "2–5"}
LOAD_REST = {1: "45s", 2: "75s", 3: "120s", 4: "180s"}
LOAD_NARRATIVE = {
    1: "Deload week. Light load, high reps, tight rest — prime the nervous system and dial in form.",
    2: "Moderate hypertrophy block. Cleanest growth range; hit every working set with intent.",
    3: "Heavy block. Push intensity while keeping technique honest; longer rests.",
    4: "Max-effort week. Low reps, long rests. Expect PRs on bench / squat or flag retries.",
}
SESSION_BADGE_MAP = {
    "push_1": ("badge-push", "bg-blue-500", "Push 1"),
    "push_2": ("badge-push", "bg-blue-500", "Push 2"),
    "pull_1": ("badge-pull", "bg-emerald-600", "Pull 1"),
    "pull_2": ("badge-pull", "bg-emerald-600", "Pull 2"),
    "legs_1": ("badge-legs", "bg-th-accent", "Legs 1"),
    "legs_2": ("badge-legs", "bg-th-accent", "Legs 2"),
    "conditioning": ("badge-conditioning", "bg-amber-600", "Conditioning"),
}
TIER_LABEL = {
    "power": "Power",
    "large": "Compound",
    "medium": "Med",
    "light": "Light",
    "conditioning": "Cond",
}

MUSCLE_LABEL = {
    "chest": "Chest",
    "back": "Back",
    "lats": "Lats",
    "traps": "Traps",
    "shoulders_front": "Front Delt",
    "shoulders_side": "Side Delt",
    "shoulders_rear": "Rear Delt",
    "biceps": "Biceps",
    "triceps": "Triceps",
    "quads": "Quads",
    "hamstrings": "Hams",
    "glutes": "Glutes",
    "calves": "Calves",
    "abs": "Abs",
    "obliques": "Obliques",
    "forearms": "Forearms",
    "full_body": "Full Body",
    "hip_flexors": "Hip Flexors",
}

DAY_NAMES = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
    4: "Friday", 5: "Saturday", 6: "Sunday",
}


HEAD_TMPL = """<!DOCTYPE html>
<html class="scroll-smooth" lang="en">
<head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
    <title>Week {n} &mdash; Gym Plan</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet"/>
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        "th-sand": "#f4f1ee",
                        "th-beige": "#e8e4e0",
                        "th-charcoal": "#1a1a1a",
                        "th-clay": "#d9c5b2",
                        "th-sage": "#b7c4b6",
                        "th-accent": "#e67e5f",
                    }},
                    fontFamily: {{
                        "display": ["Space Grotesk", "sans-serif"],
                        "sans": ["Inter", "sans-serif"],
                        "mono": ["IBM Plex Mono", "monospace"],
                    }},
                }},
            }},
        }}
    </script>
    <style type="text/tailwindcss">
        @layer base {{ body {{ @apply bg-th-sand text-th-charcoal font-sans antialiased; }} }}
        .glass-card {{
            background: rgba(255, 255, 255, 0.4);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(0, 0, 0, 0.05);
        }}
        .glass-card:hover {{ background: rgba(255, 255, 255, 0.6); border-color: rgba(0, 0, 0, 0.1); }}
        .mono-label {{ font-family: 'IBM Plex Mono', monospace; text-transform: uppercase; letter-spacing: 0.1em; font-size: 0.7rem; }}
        .tier-pill {{ font-family: 'IBM Plex Mono', monospace; text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.6rem; padding: 0.15rem 0.5rem; border-radius: 9999px; display: inline-block; line-height: 1.1rem; }}
        .tier-power {{ background: rgba(230, 126, 95, 0.15); color: #b8462a; }}
        .tier-large {{ background: #1a1a1a; color: #f4f1ee; }}
        .tier-medium {{ background: rgba(183, 196, 182, 0.45); color: #3a4a38; }}
        .tier-light {{ background: rgba(232, 228, 224, 0.9); color: rgba(26, 26, 26, 0.55); }}
        .tier-conditioning {{ background: rgba(217, 119, 6, 0.12); color: #a16207; }}
        .muscle-pill {{ font-family: 'IBM Plex Mono', monospace; text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.6rem; padding: 0.15rem 0.5rem; border-radius: 9999px; background: rgba(26, 26, 26, 0.04); color: rgba(26, 26, 26, 0.6); border: 1px solid rgba(0, 0, 0, 0.06); display: inline-block; line-height: 1.1rem; }}
        .session-badge {{ font-family: 'IBM Plex Mono', monospace; text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.65rem; padding: 0.2rem 0.6rem; border-radius: 9999px; border: 1px solid; display: inline-block; }}
        .badge-push {{ background: rgba(59, 130, 246, 0.08); color: #2563eb; border-color: rgba(59,130,246,0.2); }}
        .badge-pull {{ background: rgba(5, 150, 105, 0.08); color: #059669; border-color: rgba(5,150,105,0.2); }}
        .badge-legs {{ background: rgba(230, 126, 95, 0.1); color: #b8462a; border-color: rgba(230,126,95,0.25); }}
        .badge-conditioning {{ background: rgba(217, 119, 6, 0.08); color: #a16207; border-color: rgba(217,119,6,0.2); }}
        .badge-rest {{ background: rgba(26, 26, 26, 0.04); color: rgba(26,26,26,0.45); border-color: rgba(0,0,0,0.08); }}
        .badge-blocked {{ background: rgba(239, 68, 68, 0.06); color: #b91c1c; border-color: rgba(239,68,68,0.2); }}
        .load-chip {{ font-family: 'IBM Plex Mono', monospace; text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.65rem; padding: 0.25rem 0.75rem; border-radius: 9999px; border: 1px solid rgba(0, 0, 0, 0.08); }}
        .load-1 {{ background: rgba(183, 196, 182, 0.3); color: #3a4a38; }}
        .load-2 {{ background: rgba(59, 130, 246, 0.08); color: #2563eb; }}
        .load-3 {{ background: rgba(217, 119, 6, 0.08); color: #a16207; }}
        .load-4 {{ background: rgba(239, 68, 68, 0.08); color: #b91c1c; }}
        .exercise-row + .exercise-row {{ border-top: 1px solid rgba(0,0,0,0.05); }}
        @media print {{ .no-print {{ display: none !important; }} .glass-card {{ background: white !important; border: 1px solid #ccc !important; }} body {{ background: white !important; }} }}
    </style>
</head>
<body>

<header class="sticky top-0 z-50 w-full bg-th-sand/80 backdrop-blur-md border-b border-black/5 no-print">
    <div class="max-w-5xl mx-auto px-6 md:px-8 h-16 flex items-center justify-between">
        <div class="flex items-center gap-3">
            <a href="index.html" class="font-display font-semibold text-lg tracking-tight hover:text-th-accent transition">Kris&nbsp;Rajah</a>
            <span class="text-th-charcoal/25">/</span>
            <a href="index.html" class="mono-label text-th-charcoal/50 hover:text-th-charcoal/80 transition">Gym&nbsp;Plan</a>
            <span class="text-th-charcoal/25">/</span>
            <span class="mono-label text-th-charcoal/70">Week&nbsp;{n}</span>
        </div>
        <nav class="flex items-center gap-3 text-sm">
            {prev_link}
            {next_link}
        </nav>
    </div>
</header>
"""

HERO_TMPL = """
<section class="relative py-12 md:py-16 px-6 md:px-8">
    <div class="max-w-4xl mx-auto">
        <div class="inline-block px-3 py-1.5 rounded-full border border-black/10 mb-6">
            <span class="mono-label text-th-charcoal/60">Week&nbsp;{n}&nbsp;of&nbsp;17</span>
        </div>
        <h1 class="text-4xl md:text-6xl font-display font-medium tracking-tight mb-4">
            {date_range}
        </h1>
        <div class="flex flex-wrap gap-2 mb-6">
            <span class="load-chip load-{load}">Load&nbsp;{load}/4&nbsp;&middot;&nbsp;{load_label}</span>
            <span class="load-chip">{reps}&nbsp;reps</span>
            <span class="load-chip">{rest}&nbsp;rest</span>
        </div>
        <p class="text-lg md:text-xl text-th-charcoal/60 font-light leading-relaxed max-w-3xl">
            {narrative}
        </p>
    </div>
</section>
"""

TIMELINE_TMPL = """
<section class="max-w-5xl mx-auto px-4 md:px-8 pb-16 pt-4">
    <div class="flex items-center gap-4 mb-8">
        <span class="mono-label text-th-charcoal/40">7&nbsp;days</span>
        <div class="flex-1 h-px bg-black/5"></div>
        <span class="mono-label text-th-charcoal/40">{summary}</span>
    </div>

    <div class="relative">
        <div class="absolute left-[15px] md:left-[27px] top-0 bottom-0 w-px bg-black/10"></div>
        <div class="space-y-5">
{day_blocks}
        </div>
    </div>
</section>
"""

FOOTER_TMPL = """
<footer class="max-w-5xl mx-auto px-6 md:px-8 py-12 border-t border-black/5 no-print">
    <div class="flex items-center justify-between gap-4 flex-wrap">
        <a href="index.html" class="mono-label text-th-charcoal/50 hover:text-th-accent transition">&larr;&nbsp;Overview</a>
        {footer_next}
    </div>
</footer>
</body>
</html>
"""


def _load_yaml(path: Path):
    with path.open() as f:
        return yaml.safe_load(f)


def _parse_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def _week_monday(plan_start: dt.date, week_n: int) -> dt.date:
    """Monday of calendar week N (1-indexed), relative to plan_start's Monday."""
    start_mon = plan_start - dt.timedelta(days=plan_start.weekday())
    return start_mon + dt.timedelta(days=(week_n - 1) * 7)


def _format_date_range(mon: dt.date, sun: dt.date) -> str:
    if mon.month == sun.month:
        return f"{mon:%a %-d} &ndash; {sun:%a %-d %b}"
    return f"{mon:%a %-d %b} &ndash; {sun:%a %-d %b}"


def _render_exercise_row(x: dict) -> str:
    tier = x["tier"]
    tier_class = f"tier-{tier}"
    tier_label = TIER_LABEL.get(tier, tier.title())
    muscle = x.get("primary_muscle", "")
    muscle_label = MUSCLE_LABEL.get(muscle, muscle.replace("_", " ").title()) if muscle else ""
    name = x["exercise"]
    warmup = x.get("warmup_sets") or 0
    working = x.get("working_sets", 3)
    reps = x.get("reps", "")
    rest = x.get("rest_sec")
    weight = x.get("weight_kg")
    notes = (x.get("notes") or "").strip()
    if notes.startswith("—"):
        notes = notes.lstrip("— ").strip()

    warm_prefix = f"{warmup}&nbsp;wu + " if warmup else ""
    format_line = f"{warm_prefix}{working}&nbsp;&times;&nbsp;{reps}"
    if rest is not None:
        format_line += f" &middot; {rest}s rest"
    weight_cell = f"{weight} kg" if weight is not None else "_"
    notes_html = (
        f'<div class="text-xs text-th-charcoal/40 mt-0.5 italic">{notes}</div>' if notes else ""
    )
    muscle_pill = (
        f'<span class="muscle-pill shrink-0 mt-0.5">{muscle_label}</span>' if muscle_label else ""
    )
    return f"""                            <div class="exercise-row flex items-start gap-2 py-2">
                                <div class="flex flex-col gap-1 shrink-0 mt-0.5">
                                    <span class="tier-pill {tier_class}">{tier_label}</span>
                                    {muscle_pill}
                                </div>
                                <div class="flex-1 min-w-0 ml-1">
                                    <div class="font-medium text-sm">{name}</div>
                                    <div class="text-xs text-th-charcoal/50 font-mono">{format_line}</div>
                                    {notes_html}
                                </div>
                                <div class="text-xs text-th-charcoal/40 font-mono mt-0.5">{weight_cell}</div>
                            </div>"""


def _render_training_day(entry: dict) -> str:
    date = _parse_date(entry["date"])
    session = entry["session"]
    badge_cls, dot_cls, session_label = SESSION_BADGE_MAP.get(
        session, ("badge-rest", "bg-th-charcoal/30", session.title())
    )
    location = entry.get("location", "home")
    loc_label = "Office gym" if location == "office" else "Home gym"
    minutes = entry.get("minutes", 60)
    rows = [_render_exercise_row(x) for x in entry.get("exercises", [])]
    rows_html = "\n".join(rows)
    tail_html = ""
    if entry.get("cardio_tail"):
        tail_html = f"""
                        <div class="mt-4 pt-3 border-t border-black/5 flex items-center gap-2 text-xs text-th-charcoal/60">
                            <span class="material-symbols-outlined text-sm text-amber-600">directions_run</span>
                            <span class="font-medium">Cardio tail:</span>
                            <span>{entry['cardio_tail']}</span>
                        </div>"""
    return f"""            <div class="relative flex gap-3 md:gap-8">
                <div class="relative z-10 w-8 md:w-14 shrink-0 flex flex-col items-center">
                    <span class="w-3 h-3 rounded-full {dot_cls}"></span>
                </div>
                <div class="pb-2 -mt-1 flex-1 min-w-0">
                    <div class="flex items-baseline gap-3 mb-1 flex-wrap">
                        <span class="font-display font-semibold text-sm">{DAY_NAMES[date.weekday()]}</span>
                        <span class="mono-label text-th-charcoal/40 text-[10px]">{date:%-d %b}</span>
                    </div>
                    <div class="glass-card rounded-xl p-4 md:p-5">
                        <div class="flex items-center gap-2 mb-3 flex-wrap">
                            <span class="session-badge {badge_cls}">{session_label}</span>
                            <span class="mono-label text-th-charcoal/40">{loc_label} &middot; {minutes} min</span>
                        </div>
                        <div class="divide-y divide-black/5">
{rows_html}
                        </div>{tail_html}
                    </div>
                </div>
            </div>"""


def _render_rest_day(entry: dict) -> str:
    date = _parse_date(entry["date"])
    reason = entry.get("reason", "weekly")
    return f"""            <div class="relative flex gap-3 md:gap-8">
                <div class="relative z-10 w-8 md:w-14 shrink-0 flex flex-col items-center">
                    <span class="w-3 h-3 rounded-full border-2 border-th-charcoal/20 bg-th-sand"></span>
                </div>
                <div class="pb-2 -mt-1 flex-1 min-w-0">
                    <div class="flex items-baseline gap-3 mb-1 flex-wrap">
                        <span class="font-display text-sm text-th-charcoal/50">{DAY_NAMES[date.weekday()]}</span>
                        <span class="mono-label text-th-charcoal/30 text-[10px]">{date:%-d %b}</span>
                    </div>
                    <div class="inline-block">
                        <span class="session-badge badge-rest">Rest &middot; {reason}</span>
                    </div>
                </div>
            </div>"""


def _render_blocked_day(entry: dict) -> str:
    date = _parse_date(entry["date"])
    reason = entry.get("reason", "blocked")
    return f"""            <div class="relative flex gap-3 md:gap-8">
                <div class="relative z-10 w-8 md:w-14 shrink-0 flex flex-col items-center">
                    <span class="w-3 h-3 rounded-full border-2 border-red-300 bg-th-sand"></span>
                </div>
                <div class="pb-2 -mt-1 flex-1 min-w-0">
                    <div class="flex items-baseline gap-3 mb-1 flex-wrap">
                        <span class="font-display text-sm text-th-charcoal/50">{DAY_NAMES[date.weekday()]}</span>
                        <span class="mono-label text-th-charcoal/30 text-[10px]">{date:%-d %b}</span>
                    </div>
                    <div class="inline-flex items-center gap-2">
                        <span class="session-badge badge-blocked">Blocked</span>
                        <span class="text-xs text-th-charcoal/50">{reason}</span>
                    </div>
                </div>
            </div>"""


def _render_day(entry: dict) -> str:
    t = entry.get("type")
    if t == "training":
        return _render_training_day(entry)
    if t == "blocked":
        return _render_blocked_day(entry)
    return _render_rest_day(entry)


def render_week_html(n: int, schedule: list[dict], plan_start: dt.date) -> str:
    mon = _week_monday(plan_start, n)
    sun = mon + dt.timedelta(days=6)
    by_date = {e["date"]: e for e in schedule if mon.isoformat() <= e["date"] <= sun.isoformat()}
    if not by_date:
        return ""
    # Fill all 7 days Mon-Sun. Missing dates (e.g. Mon 20 Apr before plan
    # starts or days after plan end) become synthetic "pre-plan" / "post-plan"
    # rest entries so the week always renders as a full 7-day timeline.
    plan_end = max(e["date"] for e in schedule)
    week_entries = []
    for i in range(7):
        d = mon + dt.timedelta(days=i)
        iso = d.isoformat()
        if iso in by_date:
            week_entries.append(by_date[iso])
        elif iso < plan_start.isoformat():
            week_entries.append({
                "date": iso, "day": DAY_NAMES[d.weekday()].lower(),
                "type": "rest", "reason": "before plan start",
            })
        else:
            week_entries.append({
                "date": iso, "day": DAY_NAMES[d.weekday()].lower(),
                "type": "rest", "reason": "after plan end",
            })

    training = [e for e in week_entries if e["type"] == "training"]
    rest = [e for e in week_entries if e["type"] == "rest"]
    blocked = [e for e in week_entries if e["type"] == "blocked"]
    load = training[0]["load"] if training else 1

    # Prev / next links
    prev_html = (
        f'<a href="week-{n-1:02d}.html" class="text-th-charcoal/70 hover:text-th-accent transition">&larr;&nbsp;Week&nbsp;{n-1}</a>'
        if n > 1
        else '<span class="text-th-charcoal/30 hidden sm:inline cursor-not-allowed">&larr; Prev</span>'
    )
    next_html = (
        f'<a href="week-{n+1:02d}.html" class="text-th-charcoal/70 hover:text-th-accent transition">Week&nbsp;{n+1}&nbsp;&rarr;</a>'
        if n < 17
        else '<span class="text-th-charcoal/30 hidden sm:inline cursor-not-allowed">Next &rarr;</span>'
    )
    footer_next = (
        f'<a href="week-{n+1:02d}.html" class="font-display font-semibold text-sm hover:text-th-accent transition">Week&nbsp;{n+1}&nbsp;&rarr;</a>'
        if n < 17
        else '<span class="mono-label text-th-charcoal/30">Final&nbsp;week</span>'
    )

    head = HEAD_TMPL.format(n=n, prev_link=prev_html, next_link=next_html)
    hero = HERO_TMPL.format(
        n=n,
        date_range=_format_date_range(mon, sun),
        load=load,
        load_label=LOAD_LABEL[load],
        reps=LOAD_REPS[load],
        rest=LOAD_REST[load],
        narrative=LOAD_NARRATIVE[load],
    )
    summary_parts = [f"{len(training)} training"]
    if rest:
        summary_parts.append(f"{len(rest)} rest")
    if blocked:
        summary_parts.append(f"{len(blocked)} blocked")
    summary = " &middot; ".join(summary_parts)
    day_blocks = "\n".join(_render_day(e) for e in week_entries)
    timeline = TIMELINE_TMPL.format(summary=summary, day_blocks=day_blocks)
    footer = FOOTER_TMPL.format(footer_next=footer_next)
    return head + hero + timeline + footer


def main() -> None:
    meta = _load_yaml(META)
    schedule = _load_yaml(SCHED)
    plan_start = meta["start_date"]
    if isinstance(plan_start, str):
        plan_start = dt.date.fromisoformat(plan_start)
    DOCS.mkdir(exist_ok=True)
    week_args = sys.argv[1:] or [str(n) for n in range(1, 18)]
    for w in week_args:
        n = int(w)
        html = render_week_html(n, schedule, plan_start)
        if not html:
            print(f"week-{n:02d}: no entries, skipping")
            continue
        out = DOCS / f"week-{n:02d}.html"
        out.write_text(html)
        print(f"wrote {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
