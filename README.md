# Gym — 18-week cut

Personal training plan. Site at https://kris-rajah.github.io/gym/.

## Structure

- `samples/` — workout generator, exercise bank (tiered), technique catalogue.
- `plan/` — the active plan: `meta.yaml` (dates, split, periodization, PRs),
  `calendar.yaml` (blocked dates), generated `schedule.yaml`, freeform session
  `logs/`, markdown `rendered/` views.
- `scripts/` — `schedule.py` builds `plan/schedule.yaml` from meta + calendar;
  `render.py` writes weekly markdown; `build_site.py` writes `docs/week-NN.html`.
- `docs/` — static HTML site (served by GitHub Pages).
- `.claude/commands/` — slash commands (`/adjust-week`, `/build-week`,
  `/log-session`) for weekly updates via Claude Code.

## Rebuild flow

```bash
python3 scripts/schedule.py          # rebuild schedule.yaml
python3 scripts/build_site.py        # rebuild docs/*.html
git add -A && git commit -m "..." && git push
```
