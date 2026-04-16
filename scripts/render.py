"""Render weekly markdown views of the schedule.

Usage:
  python3 scripts/render.py week 1          # render ISO-week-1 relative to start
  python3 scripts/render.py week all        # render every week
  python3 scripts/render.py day 2026-04-21  # render a single day

Output: plan/rendered/week-NN.md (or day-YYYY-MM-DD.md).
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import yaml  # type: ignore[import-not-found]

HERE = Path(__file__).parent
REPO = HERE.parent
META_PATH = REPO / "plan" / "meta.yaml"
SCHED_PATH = REPO / "plan" / "schedule.yaml"
OUT_DIR = REPO / "plan" / "rendered"

LOAD_LABEL = {1: "deload", 2: "moderate", 3: "heavy", 4: "max"}


def _load(path: Path):
    with path.open() as f:
        return yaml.safe_load(f)


def _parse_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def _plan_week_start(start_date: dt.date) -> dt.date:
    """Monday of the calendar week containing the plan start."""
    return start_date - dt.timedelta(days=start_date.weekday())


def _week_number(entry_date: dt.date, start_date: dt.date) -> int:
    """1-indexed Mon-Sun calendar week number relative to the plan start week."""
    week_zero_mon = _plan_week_start(start_date)
    return ((entry_date - week_zero_mon).days // 7) + 1


def _render_training_day(entry: dict) -> list[str]:
    load = entry["load"]
    label = LOAD_LABEL[load]
    lines = [
        f"### {entry['day'].capitalize()} {entry['date']} — {entry['session'].upper()}  "
        f"(load {load}/4 {label}, {entry['minutes']} min)",
        "",
    ]
    if entry.get("cardio_warmup"):
        lines.append(f"_Warm-up cardio:_ {entry['cardio_warmup']}")
        lines.append("")
    lines.append("| Tier | Exercise | Warm-up | Working × Reps | Rest | Weight | Notes |")
    lines.append("|---|---|---|---|---|---|---|")
    for ex in entry["exercises"]:
        weight = ex.get("weight_kg")
        weight_s = f"{weight} kg" if weight else "_fill in_"
        warmup = ex["warmup_sets"] if ex["warmup_sets"] else "—"
        rest = f"{ex['rest_sec']}s" if ex.get("rest_sec") else "—"
        notes = ex.get("notes") or ""
        lines.append(
            f"| {ex['tier']} | {ex['exercise']} | {warmup} | "
            f"{ex['working_sets']} × {ex['reps']} | {rest} | {weight_s} | {notes} |"
        )
    if entry.get("cardio_tail"):
        lines.append("")
        lines.append(f"_Cardio tail:_ {entry['cardio_tail']}")
    lines.append("")
    return lines


def _render_nontraining_day(entry: dict) -> list[str]:
    kind = entry["type"]
    reason = entry.get("reason", "")
    return [
        f"### {entry['day'].capitalize()} {entry['date']} — **{kind.upper()}** ({reason})",
        "",
    ]


def render_week(n: int, schedule: list[dict], start_date: dt.date) -> str:
    entries = [e for e in schedule if _week_number(_parse_date(e["date"]), start_date) == n]
    if not entries:
        return f"# Week {n}\n\n_No entries._\n"
    first = _parse_date(entries[0]["date"])
    last = _parse_date(entries[-1]["date"])
    lines = [
        f"# Week {n}  ({first} → {last})",
        "",
    ]
    for e in entries:
        if e["type"] == "training":
            lines.extend(_render_training_day(e))
        else:
            lines.extend(_render_nontraining_day(e))
    return "\n".join(lines)


def render_day(date_str: str, schedule: list[dict]) -> str:
    for e in schedule:
        if e["date"] == date_str:
            if e["type"] == "training":
                return "\n".join(_render_training_day(e))
            return "\n".join(_render_nontraining_day(e))
    return f"_No entry for {date_str}._\n"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render schedule.yaml into weekly markdown views.")
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("week", help="Render one week (by number) or 'all'.")
    w.add_argument("which", help="Week number (1-based) or 'all'.")

    d = sub.add_parser("day", help="Render a single day.")
    d.add_argument("date", help="YYYY-MM-DD")

    return p.parse_args()


def main() -> None:
    args = _parse_args()
    meta = _load(META_PATH)
    schedule = _load(SCHED_PATH)
    start = meta["start_date"]
    if isinstance(start, str):
        start = dt.date.fromisoformat(start)
    end = meta["end_date"]
    if isinstance(end, str):
        end = dt.date.fromisoformat(end)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.cmd == "week":
        if args.which == "all":
            max_week = _week_number(end, start)
            for n in range(1, max_week + 1):
                out = OUT_DIR / f"week-{n:02d}.md"
                out.write_text(render_week(n, schedule, start))
                print(f"wrote {out.relative_to(REPO)}")
        else:
            n = int(args.which)
            out = OUT_DIR / f"week-{n:02d}.md"
            out.write_text(render_week(n, schedule, start))
            print(f"wrote {out.relative_to(REPO)}")
    elif args.cmd == "day":
        out = OUT_DIR / f"day-{args.date}.md"
        out.write_text(render_day(args.date, schedule))
        print(f"wrote {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
