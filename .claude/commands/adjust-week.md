---
name: adjust-week
description: Ingest the last week's session logs and adjust the remaining entries in plan/schedule.yaml — progression, retries, injury swaps, missed-session rescheduling.
---

# /adjust-week

Run this at the end of each training week. You (Claude) will read the user's freeform logs from `gym/plan/logs/`, cross-reference them with `gym/plan/schedule.yaml`, apply the adjustment rules below, and rewrite schedule.yaml for the remaining days.

## Inputs

- `gym/plan/meta.yaml` — goal, PRs, active injuries, periodization
- `gym/plan/calendar.yaml` — blocked dates (read-only here; user manages)
- `gym/plan/schedule.yaml` — current plan (you'll edit the **future** entries)
- `gym/plan/logs/*.md` — the user's freeform session notes
- `gym/plan/.last_adjusted` — ISO date of last adjustment run, or missing if never run

## Step-by-step

### 1. Figure out which logs are new
- Read `gym/plan/.last_adjusted` (ISO date). If it doesn't exist, treat every log file as new.
- Any `plan/logs/YYYY-MM-DD.md` dated after `.last_adjusted` (inclusive of today) is in scope.
- List the logs you found to the user before making edits.

### 2. Parse each new log
Logs are freeform markdown but usually look like:
```
# Tue 2026-04-21 — Push (Load 1)

- Bench Press: 2 wu @ 60,65 / 3 × 15 @ 70 easy, 13 @ 72.5, 12 @ 72.5
- Incline DB Press: 3 × 12 @ 30 (last set hard)
- ...

Shoulder felt tight during laterals, skipped rear flye.
Missed cardio tail — ran out of time.
```

Extract for each exercise:
- **actual sets × reps × weight**
- **subjective effort** ("easy" / "ok" / "hard" / "failed" — infer from wording)
- any **pain / injury** mentions
- any **skipped / missed** items

If a scheduled session has no log file for that date, treat it as **missed**.

### 3. Look up the corresponding entry in schedule.yaml
For each logged exercise, find the scheduled prescription (same date + exercise name). Compare actual vs prescribed.

### 4. Apply adjustment rules to **future** entries

Only edit entries whose `date` is strictly after today's date. Never rewrite past entries.

**Rule A — Progression (hit top of rep range, subjective ≤ medium)**
- Find the next occurrence of the same exercise at the same `load` level in future entries.
- Bump `weight_kg` by:
  - Barbell lifts: **+2.5 kg**
  - Dumbbell lifts: **+2 kg** (next DB jump)
  - Bodyweight: add a **+1 rep** note or recommend adding a weight belt/vest
  - Cable / machine: **+5 kg** (one stack increment; gym-dependent so note to adjust)

**Rule B — Retry (failed to hit bottom of rep range)**
- Find the next same-exercise-same-load entry and keep `weight_kg` unchanged.
- Append `" — retry from YYYY-MM-DD"` to the `notes` field.
- Do NOT propagate failure to other exercises.

**Rule C — Hit range, subjective = hard**
- Keep weight the same on next occurrence. No note change.

**Rule D — Injury / pain note on muscle X**
- Add an entry to `meta.yaml::active_injuries`:
  ```yaml
  active_injuries:
    - muscle: shoulders_side
      since: 2026-04-21
      until: 2026-05-05   # default 14 days; shorten/extend based on log
      notes: "tight during laterals"
  ```
- For every future entry up to `until`:
  - Remove any exercise whose `primary_muscle == X` **or** where `X` is in `exercises_bank.csv::secondary_muscle` for that exercise.
  - Replace the removed slot with a safe alternate from the bank that:
    - Matches the same tier
    - Shares the same workout's session's target muscles (check schedule.yaml::session field + meta.yaml::sessions[session].muscles)
    - Does NOT hit the injured muscle
  - If no safe alternate exists, drop the slot and reduce the workout.

**Rule E — Missed session**
- If a scheduled training date has no log: mark the entry as `missed: true`.
- If the missed load was the heaviest of the wave (load 4), schedule a **make-up** session in the next available non-conflicting slot (search forward from today, skip blocked / rest days, skip dates that already have a training session).
- Otherwise, just let it slide — don't compress the whole plan for a single missed light/moderate day.

**Rule F — PR updates**
- If an actual working set's weight × reps is a new PR (compare to `meta.yaml::prs[exercise]`), update `prs`.
- New PR = heavier working weight for the same or higher rep count OR same weight with ≥2 more reps.

### 5. Write the changelog

Create `gym/plan/rendered/adjustment-{today}.md` with sections:
- **Logged sessions** (which days were processed)
- **Progressions** (bullet per weight bump)
- **Retries** (bullet per unchanged weight)
- **Injuries** (new / updated active_injuries)
- **Exercise swaps** (original → replacement, date, reason)
- **Missed sessions** (date, how handled)
- **PR updates** (lift, old → new)

### 6. Update state
- Update `gym/plan/.last_adjusted` to today's ISO date.
- Re-dump `gym/plan/schedule.yaml` (preserving order, sort_keys=False).
- Update `gym/plan/meta.yaml` with any `prs` / `active_injuries` changes.

### 7. Summarise to the user
At the end, print:
- Total edits made
- Any unresolved ambiguity (e.g. "I couldn't find a safe substitute for X — please review")
- Recommended next step (run `python3 scripts/render.py week N` to see the updated week)

## Edge cases to handle

- **Log references an exercise not in the schedule**: user did a substitution on the fly. Note it in the changelog; don't auto-add to future schedules.
- **Log has no date header**: use the filename date.
- **Multiple log files for the same date**: concatenate.
- **User logs freeform injury with no muscle name** (e.g. "knee hurts"): map common terms to muscles (knee → quads / hamstrings; shoulder → shoulders_front / shoulders_side; lower back → back / hamstrings). If ambiguous, ask the user.
- **Session was cut short**: user did primary + medium but skipped lights. Don't treat as missed; just record what was done.

## What NOT to do

- Never edit past-dated entries in schedule.yaml.
- Never invent new exercises — only swap within the bank.
- Never bump weight more than +5 kg on a single adjustment even if the set was trivial — prefer the next load-4 session for big jumps.
- Never silently drop a session — always record it in the changelog.
