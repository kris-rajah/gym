# Sample-Bank Schema

Files in this folder act as a **banks-and-rules** reference for a workout generator. Source PDFs: `shortcut-to-shred.pdf` (Stoppani) and `12-week-trainer-overview-*.pdf` (Gethin).

---

## `exercise_bank.csv`

Tagged library of unique exercises found across both programs.

| Column | Type | Values |
|---|---|---|
| `name` | string | Exercise name (canonical spelling). |
| `primary_muscle` | enum | `chest`, `back` (whole posterior chain: erectors + mid-back), `lats`, `traps`, `shoulders_front`, `shoulders_side`, `shoulders_rear`, `biceps`, `triceps`, `quads`, `hamstrings`, `glutes`, `calves`, `abs`, `obliques`, `forearms`, `hip_flexors`, `full_body`. |
| `secondary_muscle` | string | `;`-separated list of the same enum, or blank. |
| `movement` | enum | `push_horizontal`, `push_vertical`, `pull_horizontal`, `pull_vertical`, `hinge`, `squat`, `lunge`, `isolation`, `carry`, `core`, `cardio`. |
| `equipment` | enum | `barbell`, `dumbbell`, `cable`, `machine`, `smith`, `bodyweight`, `ez_bar`, `kettlebell`, `mixed`. |
| `compound` | bool | `true` for multi-joint, `false` for isolation. |
| `unilateral` | bool | `true` if one limb at a time. |
| `rep_low` | int | Recommended rep-range floor. |
| `rep_high` | int | Recommended rep-range ceiling. |
| `complexity` | enum | `low` (easy to set up, low skill), `med`, `high` (heavy compound, technique-demanding). |
| `notes` | string | Cues, variation notes, source mentions. |

### Generator filters
- Muscle group match → filter by `primary_muscle` (± `secondary_muscle`).
- Equipment filter → filter by `equipment`.
- Load level → pick rep target inside `[rep_low, rep_high]` (heavy = lower, light = higher).
- Complexity gate → for short sessions or warm-up positions, prefer `low`/`med`.

---

## `techniques.csv`

Loading / intensity techniques observed in the source programs.

| Column | Type | Values |
|---|---|---|
| `name` | string | Identifier used in workout output. |
| `description` | string | What the technique is, in ≤2 sentences. |
| `typical_use` | string | Where it fits (main lift, finisher, isolation block, etc.). |
| `time_multiplier` | float | Relative wall-clock cost vs. straight sets (1.0 = same, 1.3 = 30% longer, 0.7 = shorter because cardio replaces rest). |
| `intensity` | enum | `low`, `moderate`, `high`, `extreme`. |
| `rest_sec` | int or blank | Typical between-set rest. Blank = replaced by another activity. |

---

## `templates.md`

Prose summary of workout archetypes (splits, session shapes, phase logic) distilled from the two sample programs. Read by the generator logic and by future agents to understand standard structures.

---

## `generator.py`

Python CLI. Inputs:
- `--muscles` — comma-separated primary muscle groups to hit.
- `--minutes` — target session length.
- `--load` — `light` | `moderate` | `heavy` (maps to rep target + technique selection).
- `--equipment` — comma-separated allowed equipment, or `all`.
- `--goal` — `hypertrophy` | `strength` | `fat_loss` | `conditioning`.
- `--seed` — optional RNG seed for reproducibility.

Outputs a workout plan: warm-up → main lifts → accessories → finishers → cardio block, with exercise names, sets × reps, rest, and technique annotations.

Selection rules live in `generator.py` and rely on `exercise_bank.csv` + `techniques.csv` + the archetypes described in `templates.md`.
