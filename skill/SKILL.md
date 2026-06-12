---
name: worklog
description: Log work to the Google Sheet timesheet. Use at natural breakpoints after substantial work (~1h+) in a tracked project, on wrap-up phrases ("на сегодня всё", "закоммитил"), or when the user runs /worklog. Records one row per day per project with an effort-estimate in hours and a concise English summary.
---

# Worklog

Record what was accomplished this session into the Google Sheet timesheet via the
`worklog` CLI engine. One row per **day per project**; same-day work accumulates.

## When to act

- The user runs `/worklog` (optionally `/worklog <hours> "<text>"` to override).
- A substantial chunk of work (~1h+) finished in a **tracked** project, and you are at a
  natural breakpoint (commit made, task done, user says they're wrapping up).
- Do NOT log trivial actions (a single tiny edit, answering a question). Minimum 0.5h.

## Steps

1. **Resolve the project.** Run `worklog projects` and check the repo. The engine resolves
   automatically from `CLAUDE.md` → `.claude/worklog.local.json` → folder alias. If it
   prints "No project resolved", ask the user once for the name, then run
   `worklog init "<Name>"` to remember it.
2. **Summarize the work** in one concise English phrase in the user's terse style — name
   concrete things: fixes, deploys, investigations, files. Example style:
   "deployed TB pipeline, fixed broken /api/redirect/, 7-day filter".
3. **Estimate hours** by volume of work (commit count, number/complexity of edits), rounded
   to 0.5. Use the user's override if they gave one.
4. **Show the user the proposed row** and the date, and let them confirm or edit hours/text.
5. **Write it:**
   ```
   worklog add --project "<Project>" --hours <n> --text "<summary>"
   ```
   Use `--dry-run` first if unsure. Date defaults to today (`DD.MM.YYYY`).
6. If the engine says the entry was **buffered** (offline), tell the user; it will flush
   on the next `worklog flush` or next successful `add`.

## Notes

- Hours are an **effort estimate**, not wall-clock. Round to 0.5, minimum 0.5.
- Same project, same day → the engine accumulates hours and appends text. Don't create a
  second row yourself.
- The sheet is a single formatted timesheet: the engine writes the `MONTH YEAR` headers,
  per-month total rows, and `GRAND TOTAL` automatically (regenerated on every write). Never
  edit those rows by hand and never add them via the CLI — just `worklog add` data.
