---
name: log-session
description: Scaffold today's (or a given date's) freeform session log from schedule.yaml so the user can fill in actuals.
---

# /log-session

Create a pre-filled markdown log file in `gym/plan/logs/` for a scheduled training day.

## Usage

- `/log-session` — scaffold today's session (if today is a training day).
- `/log-session 2026-04-21` — scaffold the session for a specific date.

## Steps

1. Determine the target date.
   - If the user passed one, use it.
   - Otherwise use today.
2. Look up the entry in `gym/plan/schedule.yaml`.
   - If the entry is `type: rest` or `type: blocked`, tell the user there's nothing to log and stop.
3. Pick the output path: `gym/plan/logs/YYYY-MM-DD.md`.
   - If it already exists, read it back and print a reminder instead of overwriting.
4. Otherwise, write a template like:

```markdown
# {Day} {date} — {session upper} (load {load}/4, {minutes} min)

## Results

- {Exercise 1}: _<actuals e.g. 2 wu @ 60,65 / 3 × 15 @ 70 easy>_
- {Exercise 2}: _<actuals>_
...

## Notes

- (mood, sleep, soreness, environment)
- (any pain / tweaks — name the muscle if you know it)
- (anything you swapped, skipped, or added)
```

Pre-fill the exercise bullets with each entry from the scheduled workout in order (power → large → medium → light → conditioning). Leave the after-colon content blank for the user to fill in.

5. Print the path of the created file so the user can open it.

## Edge cases

- Two scheduled workouts on the same date (shouldn't happen, but if adjust-week ever doubles up): list both, separated by a `---`.
- No scheduled workout at all: tell the user this date isn't in the plan; don't create a file.
