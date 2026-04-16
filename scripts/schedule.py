"""Build the 90-day training schedule.

Reads:
  gym/plan/meta.yaml       — goal, dates, split, periodization, PRs
  gym/plan/calendar.yaml   — blocked dates

Writes:
  gym/plan/schedule.yaml   — one entry per date from start_date to end_date,
                             with the full workout prescription serialized.

Calls samples/generator.generate_workout once per training day.
"""
from __future__ import annotations

import datetime as dt
import sys
from dataclasses import asdict
from pathlib import Path

# Make the samples/ generator importable without packaging the repo.
HERE = Path(__file__).parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "samples"))

import yaml  # type: ignore[import-not-found]

from generator import generate_workout  # noqa: E402


META_PATH = REPO / "plan" / "meta.yaml"
CAL_PATH = REPO / "plan" / "calendar.yaml"
OUT_PATH = REPO / "plan" / "schedule.yaml"

WEEKDAY_NAME = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}


def _load_yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def _daterange(start: dt.date, end: dt.date):
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


def _workout_to_dict(workout, prs: dict[str, float | int]) -> list[dict]:
    """Serialize a Workout's prescribed sets to plain dicts for YAML."""
    rows = []
    for p in workout.prescribed:
        ex = p.exercise
        prescribed_weight = prs.get(ex.name)  # None if unknown — user fills later
        rows.append(
            {
                "exercise": ex.name,
                "tier": ex.tier,
                "primary_muscle": ex.primary_muscle,
                "warmup_sets": p.warmup_sets,
                "working_sets": p.working_sets,
                "reps": p.reps,
                "rest_sec": p.rest_sec,
                "weight_kg": prescribed_weight,
                "equipment": ex.equipment,
                "notes": p.notes or "",
            }
        )
    return rows


def _calendar_week_mon(d: dt.date, plan_start: dt.date) -> dt.date:
    """Monday of the Mon-Sun calendar week containing d (aligned to plan_start's week)."""
    # All Mondays are the same Mon-Sun; doesn't depend on plan_start here, but
    # kept for consistency.
    return d - dt.timedelta(days=d.weekday())


def _load_exercise_bank() -> dict[str, dict]:
    """Return {name: row-as-dict} for the exercise bank."""
    import csv
    out: dict[str, dict] = {}
    bank_path = REPO / "samples" / "exercise_bank.csv"
    with bank_path.open() as f:
        for row in csv.DictReader(f):
            out[row["name"]] = row
    return out


def _enforce_required_weekly(schedule: list[dict], required: list[dict]) -> list[tuple[str, str, str]]:
    """For each calendar week, ensure each required exercise appears on its
    target session day. If missing, swap in by replacing a same-tier exercise
    that shares the required lift's primary muscle.

    Returns a log of swaps: (date, from_name, to_name).
    """
    if not required:
        return []

    bank = _load_exercise_bank()
    swaps: list[tuple[str, str, str]] = []

    # Group training entries by calendar week (Mon-Sun).
    weeks: dict[dt.date, list[dict]] = {}
    for entry in schedule:
        if entry.get("type") != "training":
            continue
        date = dt.date.fromisoformat(entry["date"])
        mon = _calendar_week_mon(date, None)  # plan_start unused
        weeks.setdefault(mon, []).append(entry)

    for mon, entries in weeks.items():
        for req in required:
            name = req["name"]
            target_session = req.get("session")
            target_prefix = req.get("session_prefix")
            # Already present anywhere this week?
            already = any(
                any(x["exercise"] == name for x in e["exercises"])
                for e in entries
            )
            if already:
                continue

            # Need to swap in. Find a session of the right type in this week.
            if target_prefix:
                candidate_sessions = [e for e in entries if e["session"].startswith(target_prefix)]
            else:
                candidate_sessions = [e for e in entries if e["session"] == target_session]
            if not candidate_sessions:
                continue  # no push/legs day this week — can't enforce

            # Find the exercise to swap out: same tier + same primary_muscle
            # as the required lift.
            req_row = bank.get(name)
            if not req_row:
                continue
            req_tier = req_row["tier"]
            req_primary = req_row["primary_muscle"]

            swap_done = False
            for session_entry in candidate_sessions:
                for i, x in enumerate(session_entry["exercises"]):
                    if x["tier"] == req_tier and x["primary_muscle"] == req_primary:
                        old_name = x["exercise"]
                        # Build the replacement entry, preserving set/rep/rest shape.
                        new_entry = dict(x)
                        new_entry["exercise"] = name
                        new_entry["primary_muscle"] = req_primary
                        new_entry["equipment"] = req_row["equipment"]
                        new_entry["notes"] = req_row["notes"]
                        session_entry["exercises"][i] = new_entry
                        swaps.append((session_entry["date"], old_name, name))
                        swap_done = True
                        break
                if swap_done:
                    break
    return swaps


def build_schedule(meta: dict, calendar: dict) -> list[dict]:
    start_date = meta["start_date"]
    end_date = meta["end_date"]
    if isinstance(start_date, str):
        start_date = dt.date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = dt.date.fromisoformat(end_date)

    load_wave = meta["load_wave"]
    wave_len = meta["wave_length_weeks"]
    lifting_day_map = meta.get("lifting_day_map") or {}
    lifting_days = set(lifting_day_map.keys()) or set(meta.get("lifting_days") or [])
    conditioning_days = set(meta["conditioning_days"])
    rest_days = set(meta["rest_days"])
    rotation = meta.get("lifting_rotation") or []
    sessions_spec = meta["sessions"]
    default_minutes = meta.get("minutes_per_session", 60)
    day_overrides = meta.get("day_overrides") or {}
    prs = meta.get("prs") or {}

    # Blocked dates -> set of dt.date for fast lookup.
    blocked = {}
    for entry in (calendar.get("blocked") or []):
        d = entry["date"]
        if isinstance(d, str):
            d = dt.date.fromisoformat(d)
        blocked[d] = entry.get("reason", "blocked")

    rotation_idx = 0  # used only if legacy lifting_rotation is defined
    # Per-weekday counters for the day-map variant alternation.
    weekday_alt_idx: dict[str, int] = {d: 0 for d in lifting_day_map}
    schedule: list[dict] = []

    for date in _daterange(start_date, end_date):
        day_name = WEEKDAY_NAME[date.weekday()]
        entry: dict = {"date": date.isoformat(), "day": day_name}

        # 1. Blocked days — schedule-level skip, no workout.
        if date in blocked:
            entry.update({"type": "blocked", "reason": blocked[date]})
            schedule.append(entry)
            continue

        # 2. Weekly rest days.
        if day_name in rest_days:
            entry.update({"type": "rest", "reason": "weekly rest"})
            schedule.append(entry)
            continue

        # 3. Training day — compute load from wave, session from slot type.
        week_idx = (date - start_date).days // 7  # 0-indexed
        load = load_wave[week_idx % wave_len]

        if day_name in conditioning_days:
            session_name = "conditioning"
        elif day_name in lifting_day_map:
            variants = lifting_day_map[day_name]
            session_name = variants[weekday_alt_idx[day_name] % len(variants)]
            weekday_alt_idx[day_name] += 1
        elif day_name in lifting_days and rotation:
            session_name = rotation[rotation_idx % len(rotation)]
            rotation_idx += 1
        else:
            # Should never hit — day is neither lifting, conditioning, nor rest.
            entry.update({"type": "rest", "reason": "unmapped day"})
            schedule.append(entry)
            continue

        spec = sessions_spec[session_name]
        override = day_overrides.get(day_name, {})
        minutes = override.get("minutes", default_minutes)
        include_conditioning = override.get(
            "include_conditioning", spec.get("include_conditioning", False)
        )
        # Seed reproducibly off the date so rebuilds are stable.
        seed = int(date.strftime("%Y%m%d"))

        # Prefer blueprint if the session defines one for this minute budget.
        blueprint = None
        session_blueprints = spec.get("blueprint") or {}
        # YAML keys may be integers (60) or strings ("60"); try both.
        for key in (minutes, str(minutes)):
            if key in session_blueprints:
                blueprint = session_blueprints[key]
                break
        if blueprint is None and session_blueprints:
            # Fall back to the closest available budget.
            available = sorted(int(k) for k in session_blueprints.keys())
            nearest = min(available, key=lambda m: abs(m - minutes))
            blueprint = session_blueprints[nearest] if nearest in session_blueprints else session_blueprints[str(nearest)]

        if blueprint:
            workout = generate_workout(
                blueprint=dict(blueprint),
                minutes=minutes,
                load=load,
                include_conditioning=bool(include_conditioning),
                seed=seed,
            )
        else:
            workout = generate_workout(
                muscle_groups=list(spec.get("muscles") or []),
                minutes=minutes,
                load=load,
                include_conditioning=bool(include_conditioning),
                seed=seed,
            )
        entry.update(
            {
                "type": "training",
                "session": session_name,
                "load": load,
                "minutes": minutes,
                "location": override.get("location", "home"),
                "exercises": _workout_to_dict(workout, prs),
            }
        )
        if workout.cardio_warmup:
            entry["cardio_warmup"] = workout.cardio_warmup
        if workout.cardio_tail:
            entry["cardio_tail"] = workout.cardio_tail
        schedule.append(entry)

    return schedule


def main() -> None:
    meta = _load_yaml(META_PATH)
    calendar = _load_yaml(CAL_PATH)
    schedule = build_schedule(meta, calendar)
    swaps = _enforce_required_weekly(schedule, meta.get("required_weekly") or [])
    with OUT_PATH.open("w") as f:
        yaml.safe_dump(schedule, f, sort_keys=False, default_flow_style=False)
    total = len(schedule)
    training = sum(1 for e in schedule if e.get("type") == "training")
    blocked = sum(1 for e in schedule if e.get("type") == "blocked")
    rest = sum(1 for e in schedule if e.get("type") == "rest")
    print(f"wrote {OUT_PATH.relative_to(REPO)}")
    print(f"  total days:    {total}")
    print(f"  training:      {training}")
    print(f"  weekly rest:   {rest}")
    print(f"  blocked:       {blocked}")
    if swaps:
        print(f"  required_weekly swaps: {len(swaps)}")
        for date, from_name, to_name in swaps[:10]:
            print(f"    {date}: {from_name} → {to_name}")
        if len(swaps) > 10:
            print(f"    ... and {len(swaps) - 10} more")


if __name__ == "__main__":
    main()
