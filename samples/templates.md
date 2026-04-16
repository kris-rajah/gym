# Workout Archetypes

Distilled from the two source programs. The generator uses these shapes — not a single prescription — so sessions can flex by goal, time, and muscle focus.

## Session shape (the universal skeleton)

Every generated session has these blocks. Short sessions collapse some; long sessions expand the accessory block.

1. **Warm-up (≈5–10 min)** — pulse-raiser (2–5 min cardio) + 1–2 light ramp sets of the first main lift.
2. **Primary compound (1–2 lifts, 3–5 working sets)** — heaviest work of the day, `rep_low`-end of target range, straight sets or pyramid.
3. **Secondary compound (1–2 lifts, 3–4 sets)** — second pressing/pulling angle or second muscle group.
4. **Accessory / isolation (2–4 lifts, 3 sets)** — muscle-specific, mid rep range, supersets allowed to save time.
5. **Finisher (0–1 block)** — FST-7, drop-set, DTP pyramid, giant set, or cardio_acceleration run through a single muscle. Optional; used on load=moderate/heavy.
6. **Cardio block (optional tail, 10–25 min)** — LISS on treadmill/bike/elliptical, or swim. Skipped when `goal=strength` or time is tight.

## Time budgets (approximate minutes per block)

| Session length | Warm-up | Primary | Secondary | Accessory | Finisher | Cardio |
|---|---|---|---|---|---|---|
| 30 min | 5 | 10 | 8 | 7 | 0 | 0 |
| 45 min | 7 | 12 | 10 | 10 | 6 | 0 |
| 60 min | 8 | 15 | 12 | 15 | 5 | 5 |
| 75 min | 10 | 15 | 15 | 20 | 8 | 7 |
| 90 min | 10 | 15 | 15 | 25 | 10 | 15 |

Per-set budget (including rest):
- Compound straight set: ~90–120 s
- Accessory straight set: ~75 s
- Superset pair: ~120 s for both
- Cardio_acceleration set: ~90 s (no rest, 60 s cardio between)
- FST-7 block: ~5–6 min total

## Splits (examples, not mandates)

These are reference splits the generator can emit across a weekly plan, taken from the source programs and common practice:

- **S2S-style bro split (6 days)** — Chest+Tri multi → Shoulders+Legs multi → Back+Traps+Bi multi → Chest+Tri single → Shoulders+Legs single → Back+Traps+Bi single → rest. Cardio_acceleration throughout.
- **Gethin-style 4+1 (5 days)** — Chest+Tri → Back+Bi → rest → Legs → Shoulders+Calves+Abs. Daily AM+PM LISS cardio.
- **Push / Pull / Legs (3 or 6 days)** — classic rotation.
- **Upper / Lower (4 days)** — time-efficient for general population.
- **Full-body (3 days)** — compound-biased, one main lift per movement pattern.

The generator doesn't pick a split; the *caller* names the muscles and the generator fills one session. A higher-level planner can chain sessions into a split.

## Load-level → rep/technique mapping

- **`light`** — 12–20 reps on isolations, 10–15 on compounds. Mostly `straight_set`, some `superset`. Short rests.
- **`moderate`** — 8–12 reps on compounds, 10–15 on isolations. Straight + superset + occasional drop_set / FST-7.
- **`heavy`** — 3–6 reps on top compounds, 6–10 on secondary compounds, 8–12 on isolations. Longer rests; technique picks skew to `straight_set`, `pyramid`, `rest_pause`.

## Goal → bias

- **`strength`** — heavier load, lower reps, more compounds, fewer techniques, longer rest. Skip cardio tail.
- **`hypertrophy`** — moderate load, 8–12 reps, mix of compounds and isolations, supersets/FST-7/drops welcome.
- **`fat_loss`** — moderate load, 10–15 reps, heavy use of `cardio_acceleration` and `circuit`, append cardio tail.
- **`conditioning`** — circuits, kettlebell/bodyweight bias, time-based work, minimal traditional lifting.

## Muscle coverage rules

When `muscle_groups` includes multiple, the generator sequences large-muscle compounds first:

1. If list contains `chest`, `back`, `shoulders_front`, `quads`, or `hamstrings` → that group gets the primary compound.
2. Smaller muscles (`biceps`, `triceps`, `calves`, `abs`) placed as accessories unless they are the *only* muscles listed.
3. Antagonist supersets are preferred when two opposing muscles appear together (chest+back, biceps+triceps, quads+hamstrings).
