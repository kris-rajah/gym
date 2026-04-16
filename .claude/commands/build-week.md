---
name: build-week
description: Regenerate docs/week-NN.html (or all weeks) from the current schedule.yaml.
---

# /build-week

Thin wrapper around `gym/scripts/build_site.py`. Run it whenever
`plan/schedule.yaml` or `plan/meta.yaml` changes so the published pages
reflect the current plan.

## Usage

- `/build-week` — rebuild all 18 weeks.
- `/build-week 2` — rebuild week 2 only.
- `/build-week 1 3 5` — rebuild weeks 1, 3, 5.

## Steps

1. Decide which weeks to rebuild based on args (default: `all`).
2. From the repo root (`gym/`), run:
   ```bash
   python3 scripts/build_site.py [week_numbers...]
   ```
3. Print the list of files written (the script already echoes this).
4. Remind the user to commit + push if they want the GitHub Pages site
   updated:
   ```bash
   cd gym && git add docs plan && git commit -m "rebuild week(s)" && git push
   ```

## When to run this

- After `/adjust-week` modifies the schedule.
- After editing `plan/meta.yaml` (blueprints, day_overrides, PRs).
- After editing `plan/calendar.yaml` (blocked dates) and re-running
  `scripts/schedule.py`.
- After any edit to `samples/exercise_bank.csv` or `samples/generator.py`
  followed by a `scripts/schedule.py` rebuild.

## Notes

- `build_site.py` is self-contained — it reads `plan/schedule.yaml` +
  `plan/meta.yaml` and writes `docs/week-NN.html`. No other inputs.
- The `docs/index.html` landing page is hand-maintained; it does **not**
  auto-regenerate. Edit that file manually if weeks gain/lose blocked
  days or the dates shift.
- If a week number is out of range (< 1 or > 18) the script prints a
  "no entries" message and skips.
