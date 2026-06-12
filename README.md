# worklog — Claude Code skill for real-time timesheets

A [Claude Code](https://claude.com/claude-code) skill that logs your work to a Google
Sheet **as you work** — one row per day per project, with a concise summary of what you
did, an effort estimate in hours, the date, and the project name. No more reconstructing a
timesheet from git history at the end of the month.

## How it works

```
Claude in a work project
  ├─ SessionStart hook  ──▶ nudge + today's date (only in tracked projects)
  ├─ Skill `worklog` (brain): resolve project, summarize work, estimate hours, confirm row
  └─ worklog CLI (engine, Python + gspread)
       • upsert by (date, project): exists → hours += , text appended; else → new row
       • regenerates the whole formatted sheet: MONTH YEAR headers, per-month totals,
         GRAND TOTAL — data rows are the single source of truth
       └─ service account ▼
   Google Sheet: one formatted timesheet (month blocks + totals), exactly like the manual one
```

- **Hours** are Claude's effort estimate by volume of work (rounded to 0.5), not wall-clock.
- **Semi-automatic:** Claude logs at natural breakpoints, plus a manual `/worklog` command.
- **Per-project opt-in:** run `worklog init "<Project>"` in a repo to start tracking it.
- **Auth:** a Google Cloud service account; the sheet is shared with its email.

## Engine commands

| Command | Purpose |
| --- | --- |
| `worklog init "<Project>"` | Onboard the current repo (marker + instruction in `CLAUDE.md`) |
| `worklog add --project "<P>" --hours <n> --text "<...>"` | Upsert a day's entry |
| `worklog show [--date DD.MM.YYYY]` | Show entries for a day |
| `worklog projects` | List tracked projects |
| `worklog flush` | Resend entries buffered while offline |

All commands support `--dry-run`.

## Status

Engine, skill, and hook implemented and unit-tested (`pytest` — 28 tests). Pending: the
one-time Google Cloud setup (service account + shared sheet).

- Design spec: [`docs/superpowers/specs/2026-06-12-worklog-skill-design.md`](docs/superpowers/specs/2026-06-12-worklog-skill-design.md)
- Implementation plan: [`docs/superpowers/plans/2026-06-12-worklog-skill.md`](docs/superpowers/plans/2026-06-12-worklog-skill.md)

## Setup

See [`docs/SETUP.md`](docs/SETUP.md) — Google Cloud service account, sheet template
(`Log` + `Report`), `./install.sh`, and SessionStart hook registration.

## Development

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```
