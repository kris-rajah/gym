"""Workout generator.

Fixed session order (5 tiers):
  POWER         -> 1 warm-up + 3 working x 3-5 reps (fresh state; plyo / olympic)
  LARGE compound-> 2 warm-up + 3 working (bench / squat / DL / BB row / mil press)
  MEDIUM compound> 1 warm-up + 3 working (DB press, pulldown, leg press, pull-ups)
  LIGHT / iso   -> 0 warm-up + 3 working (curls, flyes, extensions, raises, calves)
  CONDITIONING  -> own block, time-based; only when include_conditioning=True

Toggles:
  include_cardio=True         -> short LISS pulse-raiser + steady-state tail.
  include_conditioning=True   -> intervals / sprints / ropes block at the end.

Power tier is ALWAYS included if a matching exercise exists for the targets —
it's the CNS primer, not an opt-in.

Usage (library):
    from generator import generate_workout
    workout = generate_workout(
        muscle_groups=["back", "biceps", "shoulders"],
        minutes=50,
        load=2,                    # 1 (deload 12-15) | 2 (moderate 9-11) | 3 (heavy 6-8) | 4 (max 2-5)
        equipment="all",            # "all" or comma-string / list
        include_cardio=False,       # True = LISS pulse-raiser + tail
        include_conditioning=False, # True = sprints / ropes / intervals block
        seed=None,
    )
    print(workout.as_text())

Usage (CLI):
    python generator.py --muscles back,biceps,shoulders --minutes 50 --load 2
"""
from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).parent
BANK_PATH = HERE / "exercise_bank.csv"
TECH_PATH = HERE / "techniques.csv"

LOAD_LEVELS = (1, 2, 3, 4)
LOAD_REP_RANGES = {1: (12, 15), 2: (9, 11), 3: (6, 8), 4: (2, 5)}
LOAD_REST_SEC = {1: 45, 2: 75, 3: 120, 4: 180}
LOAD_LABEL = {1: "deload", 2: "moderate", 3: "heavy", 4: "max"}

# 5-tier ordering.
TIER_ORDER = ("power", "large", "medium", "light", "conditioning")
TIER_WARMUPS = {"power": 1, "large": 2, "medium": 1, "light": 0, "conditioning": 0}
TIER_WORKING_SETS = 3  # applies to power/large/medium/light; conditioning is time-based
POWER_REPS = "3-5"
POWER_REST_SEC = 180  # CNS recovery
# Light-tier isolation work chases a pump regardless of the session's load level.
LIGHT_REPS = "12-15"
LIGHT_MAX_REST_SEC = 60

# Session-minute budget per tier at a given load (rough).
def _mins_per_working_set(load: int) -> float:
    return (30 + LOAD_REST_SEC[load]) / 60.0

WARMUP_SET_MIN = 1.0


def _mins_per_exercise(tier: str, load: int) -> float:
    if tier == "power":
        # 1 warmup + 3 working with long CNS rest.
        return WARMUP_SET_MIN + TIER_WORKING_SETS * ((5 + POWER_REST_SEC) / 60.0)
    if tier == "conditioning":
        return 8.0  # rough block
    return TIER_WARMUPS[tier] * WARMUP_SET_MIN + TIER_WORKING_SETS * _mins_per_working_set(load)


MUSCLE_ALIASES = {
    "shoulders": ["shoulders_front", "shoulders_side", "shoulders_rear"],
    "delts": ["shoulders_front", "shoulders_side", "shoulders_rear"],
    "back": ["back", "lats", "traps"],
    "arms": ["biceps", "triceps"],
    "legs": ["quads", "hamstrings", "glutes", "calves"],
    "core": ["abs", "obliques"],
}

BIG_MUSCLES = {"chest", "back", "lats", "quads", "hamstrings", "shoulders_front"}


@dataclass
class Exercise:
    name: str
    tier: str
    primary_muscle: str
    secondary_muscle: list[str]
    movement: str
    equipment: str
    compound: bool
    unilateral: bool
    rep_low: int
    rep_high: int
    complexity: str
    notes: str


@dataclass
class PrescribedSet:
    exercise: Exercise
    warmup_sets: int
    working_sets: int
    reps: str
    rest_sec: int
    notes: str = ""


@dataclass
class Workout:
    muscle_groups: list[str]
    minutes: int
    load: int
    prescribed: list[PrescribedSet] = field(default_factory=list)
    cardio_warmup: str | None = None
    cardio_tail: str | None = None

    def as_text(self) -> str:
        lo, hi = LOAD_REP_RANGES[self.load]
        label = LOAD_LABEL[self.load]
        lines = [
            f"=== Workout ===",
            f"Muscles: {', '.join(self.muscle_groups)}",
            f"Time: {self.minutes} min  |  Load: {self.load}/4 {label} ({lo}-{hi} reps)",
            "",
        ]
        if self.cardio_warmup:
            lines.append(f"Warm-up cardio: {self.cardio_warmup}")
            lines.append("")
        current_tier = None
        for p in self.prescribed:
            if p.exercise.tier != current_tier:
                current_tier = p.exercise.tier
                lines.append(f"-- {current_tier.upper()} --")
            warm = f"{p.warmup_sets} warm-up + " if p.warmup_sets else ""
            note = f"  — {p.notes}" if p.notes else ""
            lines.append(
                f"  {p.exercise.name}: {warm}{p.working_sets} working x {p.reps} | {p.rest_sec}s rest{note}"
            )
        if self.cardio_tail:
            lines.append("")
            lines.append(f"Cardio tail: {self.cardio_tail}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Banks


def _parse_bool(s: str) -> bool:
    return s.strip().lower() == "true"


def load_bank(path: Path = BANK_PATH) -> list[Exercise]:
    out: list[Exercise] = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            out.append(
                Exercise(
                    name=row["name"].strip(),
                    tier=row["tier"].strip(),
                    primary_muscle=row["primary_muscle"].strip(),
                    secondary_muscle=[
                        m.strip() for m in row["secondary_muscle"].split(";") if m.strip()
                    ],
                    movement=row["movement"].strip(),
                    equipment=row["equipment"].strip(),
                    compound=_parse_bool(row["compound"]),
                    unilateral=_parse_bool(row["unilateral"]),
                    rep_low=int(row["rep_low"]) if row["rep_low"] else 0,
                    rep_high=int(row["rep_high"]) if row["rep_high"] else 0,
                    complexity=row["complexity"].strip(),
                    notes=row["notes"].strip(),
                )
            )
    return out


# ---------------------------------------------------------------------------
# Helpers


def expand_muscles(muscles: list[str]) -> list[str]:
    out: list[str] = []
    for m in muscles:
        m = m.strip().lower()
        if m in MUSCLE_ALIASES:
            out.extend(MUSCLE_ALIASES[m])
        else:
            out.append(m)
    seen = set()
    dedup = []
    for m in out:
        if m not in seen:
            seen.add(m)
            dedup.append(m)
    return dedup


def normalize_equipment(equipment: str | list[str]) -> set[str] | None:
    if equipment == "all" or equipment is None:
        return None
    if isinstance(equipment, str):
        items = [e.strip() for e in equipment.split(",") if e.strip()]
    else:
        items = [e.strip() for e in equipment if e.strip()]
    return set(items) if items else None


def hits_muscle(ex: Exercise, target: str) -> bool:
    return ex.primary_muscle == target or target in ex.secondary_muscle


def ranges_overlap(ex: Exercise, load: int) -> bool:
    if ex.rep_low == 0 and ex.rep_high == 0:
        return False
    lo, hi = LOAD_REP_RANGES[load]
    return not (hi < ex.rep_low or lo > ex.rep_high)


def reps_for(load: int) -> str:
    lo, hi = LOAD_REP_RANGES[load]
    return f"{lo}-{hi}"


def _pick_for_muscle(
    bank: list[Exercise],
    muscle: str,
    tier: str,
    load: int,
    allowed_equipment: set[str] | None,
    used: set[str],
    rng: random.Random,
    ignore_load: bool = False,
    blocked_movements: set[str] | None = None,
    require_primary: bool = False,
) -> Exercise | None:
    def eligible(e: Exercise) -> bool:
        if e.tier != tier or e.name in used:
            return False
        if allowed_equipment is not None and e.equipment not in allowed_equipment:
            return False
        if blocked_movements and e.movement in blocked_movements:
            return False
        return hits_muscle(e, muscle)

    pool = [e for e in bank if eligible(e)]
    if not pool:
        return None
    primary_match = [e for e in pool if e.primary_muscle == muscle]
    if require_primary:
        return rng.choice(primary_match) if primary_match else None
    return rng.choice(primary_match or pool)


def _pick_any(
    bank: list[Exercise],
    targets: list[str],
    tier: str,
    allowed_equipment: set[str] | None,
    used: set[str],
    rng: random.Random,
) -> Exercise | None:
    """Pick any exercise in tier that hits any target muscle (ignore load gate)."""
    pool = [
        e
        for e in bank
        if e.tier == tier
        and e.name not in used
        and (allowed_equipment is None or e.equipment in allowed_equipment)
        and any(hits_muscle(e, t) for t in targets + ["full_body"])
    ]
    if not pool:
        return None
    return rng.choice(pool)


# ---------------------------------------------------------------------------
# Time allocation


def _plan_counts(
    minutes: int,
    load: int,
    include_conditioning: bool,
    has_power_pool: bool,
) -> dict[str, int]:
    """How many exercises per tier given time budget."""
    if minutes <= 30:
        counts = {"power": 0, "large": 1, "medium": 1, "light": 2, "conditioning": 0}
    elif minutes <= 45:
        counts = {"power": 0, "large": 1, "medium": 2, "light": 2, "conditioning": 0}
    elif minutes <= 60:
        counts = {"power": 0, "large": 1, "medium": 2, "light": 3, "conditioning": 0}
    elif minutes <= 75:
        counts = {"power": 0, "large": 2, "medium": 3, "light": 3, "conditioning": 0}
    else:
        counts = {"power": 0, "large": 2, "medium": 3, "light": 4, "conditioning": 0}

    # Power is default-on when a matching exercise exists AND session is long
    # enough (≥45 min — short sessions shouldn't burn CNS on jumps).
    if has_power_pool and minutes >= 45:
        counts["power"] = 1

    if include_conditioning:
        counts["conditioning"] = 1

    if load == 4:
        counts["light"] = max(0, counts["light"] - 2)
    if load == 1:
        counts["light"] += 1
    return counts


# ---------------------------------------------------------------------------
# Generator core


def generate_workout(
    muscle_groups: list[str] | None = None,
    minutes: int = 60,
    load: int = 2,
    equipment: str | list[str] = "all",
    include_cardio: bool = False,
    include_conditioning: bool = False,
    seed: int | None = None,
    bank: list[Exercise] | None = None,
    blueprint: dict[str, dict[str, int]] | None = None,
) -> Workout:
    """Build a tiered workout.

    Two mutually-exclusive input modes:

    - `blueprint` (preferred): explicit per-muscle, per-tier counts. Shape:
          { "chest": {"large": 1, "medium": 1, "light": 1}, ... }
      The generator picks exactly the specified number of exercises for each
      muscle × tier combination. Power (if session >= 45 min and any power
      match exists) and the conditioning block (if `include_conditioning`)
      are auto-added.

    - `muscle_groups` (legacy): list of muscles; tier counts auto-computed
      from `_plan_counts(minutes, load, ...)`.
    """
    if load not in LOAD_LEVELS:
        raise ValueError(f"load must be one of {LOAD_LEVELS}")
    if not blueprint and not muscle_groups:
        raise ValueError("Must pass either blueprint or muscle_groups.")

    rng = random.Random(seed)
    bank = bank if bank is not None else load_bank()

    if blueprint:
        targets = list(blueprint.keys())
    else:
        targets = expand_muscles(muscle_groups or [])
    allowed_equipment = normalize_equipment(equipment)
    reps = reps_for(load)
    rest_sec = LOAD_REST_SEC[load]

    # Detect whether any power exercise could match.
    power_pool_exists = any(
        e.tier == "power"
        and (allowed_equipment is None or e.equipment in allowed_equipment)
        and any(hits_muscle(e, t) for t in targets + ["full_body"])
        for e in bank
    )

    if blueprint:
        # With blueprint, counts come directly from the spec per muscle/tier.
        counts = {t: 0 for t in TIER_ORDER}
        for tier_counts in blueprint.values():
            for tier, n in tier_counts.items():
                counts[tier] = counts.get(tier, 0) + n
        if minutes >= 45 and power_pool_exists:
            counts["power"] = 1
        if include_conditioning:
            counts["conditioning"] = 1
    else:
        counts = _plan_counts(minutes, load, include_conditioning, power_pool_exists)

    def covered_muscles() -> set[str]:
        hit: set[str] = set()
        for p in workout.prescribed:
            if p.exercise.primary_muscle in targets:
                hit.add(p.exercise.primary_muscle)
            for m in p.exercise.secondary_muscle:
                if m in targets:
                    hit.add(m)
        return hit

    def pick_tier(tier: str, n: int, used: set[str]) -> list[Exercise]:
        picks: list[Exercise] = []
        if n <= 0:
            return picks
        # Power + conditioning bypass the load-range filter. Light tier uses
        # a fixed pump range (12-15), so it also ignores the load filter.
        ignore_load = tier in ("power", "conditioning", "light")
        # Shuffle first for variety, then stable-sort by priority so the
        # priority bucket wins but within-bucket order is random.
        ordered = list(targets)
        rng.shuffle(ordered)
        if tier == "large":
            ordered = sorted(ordered, key=lambda m: 0 if m in BIG_MUSCLES else 1)
        elif tier == "light":
            covered = covered_muscles()
            ordered = sorted(ordered, key=lambda m: 0 if m not in covered else 1)

        # Dedupe movement patterns across large+medium to avoid e.g. two
        # hinge variants or two squat variants in the same session.
        dedupe = tier in ("large", "medium")
        blocked = used_movements if dedupe else None

        # Phase 1: strict muscle matching across all target muscles.
        muscle_idx = 0
        attempts = 0
        while len(picks) < n and attempts < n * 8:
            muscle = ordered[muscle_idx % len(ordered)]
            ex = _pick_for_muscle(
                bank, muscle, tier, load, allowed_equipment, used, rng,
                ignore_load=ignore_load, blocked_movements=blocked,
            )
            if ex is not None:
                picks.append(ex)
                used.add(ex.name)
                if dedupe:
                    used_movements.add(ex.movement)
            muscle_idx += 1
            attempts += 1

        # Phase 2: for power/conditioning only — allow full-body fallback
        # if strict matching yielded nothing (e.g. a core-only day has no
        # biceps/back power lift; fall back to a generic CNS primer).
        if not picks and tier in ("power", "conditioning"):
            ex = _pick_any(bank, targets, tier, allowed_equipment, used, rng)
            if ex is not None:
                picks.append(ex)
                used.add(ex.name)
        return picks

    used: set[str] = set()
    used_movements: set[str] = set()
    workout = Workout(muscle_groups=targets, minutes=minutes, load=load)

    if include_cardio:
        workout.cardio_warmup = "3-5 min easy (treadmill / bike / elliptical)"

    # Collect picks per tier. Blueprint path iterates (muscle, tier, count);
    # legacy path uses the old round-robin `pick_tier`.
    picks_per_tier: dict[str, list[Exercise]] = {t: [] for t in TIER_ORDER}

    if blueprint:
        # Power first (auto-added).
        if counts["power"] > 0:
            ex = None
            muscles_order = list(blueprint.keys())
            rng.shuffle(muscles_order)
            # Phase 1: strict match — power exercise whose primary or secondary
            # muscle is one of the target muscles.
            for m in muscles_order:
                ex = _pick_for_muscle(
                    bank, m, "power", load, allowed_equipment, used, rng,
                    ignore_load=True,
                )
                if ex is not None:
                    break
            # Phase 2: fall back to full_body-primary power exercises only
            # (CNS primers like Medicine Ball Slam, DB Clean, Lateral Bound).
            # This avoids legs-primary plyo (Box Jump, Lunge Jumps) landing
            # on upper-body days.
            if ex is None:
                fb_pool = [
                    e for e in bank
                    if e.tier == "power"
                    and e.primary_muscle == "full_body"
                    and e.name not in used
                    and (allowed_equipment is None or e.equipment in allowed_equipment)
                ]
                if fb_pool:
                    ex = rng.choice(fb_pool)
            if ex is not None:
                picks_per_tier["power"].append(ex)
                used.add(ex.name)

        # Main tiers in order: large -> medium -> light.
        # Dedupe only within the LARGE tier — avoid two heavy barbell
        # compounds sharing a movement pattern. Medium and light are allowed
        # to stack (e.g. Bench Press large + Decline Press medium both
        # push_horizontal is fine).
        for tier in ("large", "medium", "light"):
            for muscle, tier_counts in blueprint.items():
                n = tier_counts.get(tier, 0)
                for _ in range(n):
                    dedupe = tier == "large"
                    blocked = used_movements if dedupe else None
                    ex = _pick_for_muscle(
                        bank, muscle, tier, load, allowed_equipment, used, rng,
                        ignore_load=(tier == "light"),
                        blocked_movements=blocked,
                        require_primary=True,   # blueprint is strict
                    )
                    if ex is not None:
                        picks_per_tier[tier].append(ex)
                        used.add(ex.name)
                        if dedupe:
                            used_movements.add(ex.movement)

        # Conditioning block.
        if counts["conditioning"] > 0:
            muscles_order = list(blueprint.keys()) + ["abs", "obliques", "full_body"]
            ex = _pick_any(bank, muscles_order, "conditioning", allowed_equipment, used, rng)
            if ex is not None:
                picks_per_tier["conditioning"].append(ex)
                used.add(ex.name)
    else:
        for tier in TIER_ORDER:
            picks_per_tier[tier] = pick_tier(tier, counts[tier], used)

    for tier in TIER_ORDER:
        for ex in picks_per_tier[tier]:
            if tier == "power":
                workout.prescribed.append(
                    PrescribedSet(
                        exercise=ex,
                        warmup_sets=TIER_WARMUPS[tier],
                        working_sets=TIER_WORKING_SETS,
                        reps=POWER_REPS,
                        rest_sec=POWER_REST_SEC,
                        notes=(ex.notes or "") + " — done fresh, CNS primer",
                    )
                )
            elif tier == "conditioning":
                workout.prescribed.append(
                    PrescribedSet(
                        exercise=ex,
                        warmup_sets=0,
                        working_sets=1,
                        reps="5-10 min or 4 x 30s on / 30s off",
                        rest_sec=30,
                        notes=ex.notes,
                    )
                )
            elif tier == "light":
                # Isolation burnout: fixed pump range, shorter rest regardless of load.
                workout.prescribed.append(
                    PrescribedSet(
                        exercise=ex,
                        warmup_sets=0,
                        working_sets=TIER_WORKING_SETS,
                        reps=LIGHT_REPS,
                        rest_sec=min(rest_sec, LIGHT_MAX_REST_SEC),
                        notes=ex.notes,
                    )
                )
            else:
                # large / medium — obey the load.
                workout.prescribed.append(
                    PrescribedSet(
                        exercise=ex,
                        warmup_sets=TIER_WARMUPS[tier],
                        working_sets=TIER_WORKING_SETS,
                        reps=reps,
                        rest_sec=rest_sec,
                        notes=ex.notes,
                    )
                )

    if not workout.prescribed:
        raise ValueError(
            f"No exercises match muscles={targets} with equipment={allowed_equipment} at load={load}"
        )

    # Cardio tail rules:
    # - include_conditioning=True -> 20 min LISS tail (running / swim preferred)
    # - include_cardio=True (alone) -> short LISS tail tied to session length
    if include_conditioning:
        liss_pool = [
            e for e in bank
            if e.tier == "conditioning" and e.name not in used
            and e.name in {"Treadmill", "Swimming", "Stationary Bike", "Elliptical"}
        ]
        pick = rng.choice(liss_pool).name if liss_pool else "treadmill / swim / bike"
        workout.cardio_tail = f"20 min steady state ({pick})"
    elif include_cardio and load != 4:
        tail = {30: 0, 45: 0, 60: 5, 75: 7, 90: 15}
        mins_tail = 0
        for threshold, m in tail.items():
            if minutes >= threshold:
                mins_tail = m
        if mins_tail:
            workout.cardio_tail = f"{mins_tail} min steady state"

    return workout


# ---------------------------------------------------------------------------
# CLI


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a tiered workout from the sample bank.")
    p.add_argument("--muscles", required=True, help="Comma-separated muscle groups.")
    p.add_argument("--minutes", type=int, default=60)
    p.add_argument(
        "--load",
        type=int,
        choices=LOAD_LEVELS,
        default=2,
        help="1=deload(12-15) | 2=moderate(9-11) | 3=heavy(6-8) | 4=max(2-5)",
    )
    p.add_argument("--equipment", default="all")
    p.add_argument("--include-cardio", action="store_true", help="LISS warm-up + tail.")
    p.add_argument("--include-conditioning", action="store_true", help="Sprints / ropes / intervals block.")
    p.add_argument("--seed", type=int, default=None)
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    muscles = [m.strip() for m in args.muscles.split(",") if m.strip()]
    workout = generate_workout(
        muscle_groups=muscles,
        minutes=args.minutes,
        load=args.load,
        equipment=args.equipment,
        include_cardio=args.include_cardio,
        include_conditioning=args.include_conditioning,
        seed=args.seed,
    )
    print(workout.as_text())


if __name__ == "__main__":
    main()
