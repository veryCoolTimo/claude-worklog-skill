# Worklog Skill — Design Spec

**Date:** 2026-06-12
**Status:** Approved design, pending implementation plan

## Problem

The user manually maintains a work-hours timesheet (Google Sheet) by reviewing git
commits and memory at the end of a period. They want Claude Code to do this
incrementally and semi-automatically while working: append/update a row per day per
project with what was done, an effort estimate in hours, the date, and the project name.

Reference of the current manual table (columns and style to reproduce):

```
Date         Hours  What I did                                              Project
06.03.2026   0,5    Studied post-actor-main architecture, reviewed pipelines  Tracking Brief
13.03.2026   3      Tracking Brief plan (CDL trucking news), analyzed ...     Tracking Brief
...
March total  19     10 days
April total  63,5   28 days
GRAND TOTAL  119,5  61 active days
```

## Decisions (from brainstorming)

- **Centerpiece is a Claude skill.** Everything else serves the skill.
- **Hours = Claude's effort estimate** by volume of work (rounded to 0.5 steps, like the
  examples), user can correct. NOT wall-clock session time.
- **Trigger = semi-automatic.** Claude logs at natural breakpoints / wrap-up, prompted by
  a lightweight nudge, plus a manual `/worklog` command. No forced/blocking hooks.
- **Google Sheets auth = service account** (Google Cloud), sheet shared with its email.
- **Project name = hybrid resolution** (see below).
- **Engine = a small Python CLI** (deterministic logic in code), not a generic Sheets MCP
  and not a custom MCP server.
- **Sheet layout = flat `Log` tab + auto `Report` tab** (formulas), not direct writes into
  a hand-formatted report.

## Architecture

```
Claude in a work project
  ├─ SessionStart hook  ──▶ injects nudge + today's date (only in tracked projects)
  ├─ Skill `worklog` (BRAIN)
  │    • resolve project (hybrid)
  │    • summarize session work into one concise English phrase (user's style)
  │    • estimate hours by volume
  │    • show the proposed row → user confirms/edits
  │    └─ calls via Bash ▼
  └─ worklog CLI (ENGINE, Python + gspread)
       • upsert by (date, project): exists → hours += , text appended; else → new row
       • date format DD.MM.YYYY, same-day accumulation
       └─ service account ▼
   Google Sheet:  [Log] flat journal  ──SUMIF formulas──▶  [Report] monthly view + totals
```

## Components

### 1. Skill `worklog` (the brain)

- Location: `~/.claude/skills/worklog/` (global → available in every work project).
- `SKILL.md` describes: when to activate, hybrid project resolution, text/hours rules,
  how to call the engine, and showing the row for confirmation.
- Triggers:
  - Manual: `/worklog` (also `/worklog 2 "text"` to override hours/text).
  - Proactive: at natural pauses / wrap-up phrases ("на сегодня всё", "закоммитил"),
    enabled by the SessionStart nudge. Semi-automatic, never forced.
- Only acts in **tracked** projects (those onboarded via `worklog init`).

### 2. Engine `worklog` CLI (Python + gspread)

Located next to the skill (e.g. `~/.claude/skills/worklog/bin/worklog.py`). Commands:

- `worklog init "<Project Name>"` — onboard the current repo:
  1. write marker `worklog-project: "<Name>"` into the repo `CLAUDE.md` and
     `.claude/worklog.local.json`;
  2. add a short instruction block to `CLAUDE.md`: "this project tracks work hours — use
     the `worklog` skill to record substantial work to the timesheet";
  3. register the project in the central config's known-projects list.
- `worklog add --project "<Name>" --hours <n> --text "<...>" [--date DD.MM.YYYY] [--dry-run]`
  — upsert into `Log`: if a row for (date, project) exists, add hours and append text with
  `; ` (skip exact-duplicate text); else create a new row.
- `worklog show [--date DD.MM.YYYY]` — print rows for today / given date.
- `worklog projects` — list known/tracked projects.
- `worklog flush` — resend any entries buffered in `pending.jsonl`.
- Global `--dry-run` prints the intended change without writing.

### 3. Config — `~/.config/worklog/`

- `service-account.json` — Google Cloud service account key.
- `config.json` — `spreadsheet_id`, `log_tab` name, folder→project alias map,
  known-projects list.

### 4. Google Sheet

- **`Log`** tab — machine-written: `Date | Hours | What I did | Project`.
  - `Date` stored as text `DD.MM.YYYY`. `Hours` stored numeric (sheet locale renders the
    comma decimal). Text in English, user's terse style.
- **`Report`** tab — reproduces the current human report: grouped by month with `SUMIF`
  monthly totals and a grand total. Computed from `Log`. Built once during setup.

### 5. SessionStart hook (lightweight)

- Shell command that, **only when the current repo is tracked**, prints to stdout a short
  reminder: "today is DD.MM.YYYY; if you did substantial work (>~1h) in this tracked
  project, record it via /worklog before wrapping up." Pure context nudge — forces nothing.
  This is what makes the "semi-automatic" behavior actually fire across long sessions.

## Behavior rules

**Project resolution (hybrid), in order:**
1. `worklog-project:` line in the repo `CLAUDE.md`;
2. `.claude/worklog.local.json` marker;
3. folder basename mapped via the alias map in `config.json`;
4. otherwise ask the user once and persist to `.claude/worklog.local.json`.

**Hours:** estimate by volume (commit count, number/complexity of edits), round to 0.5,
minimum 0.5. Same project same day → accumulate into the existing row (read current, add).

**Text:** one concise English phrase in the user's style, naming concrete work (fixes,
deploys, investigations). Existing same-day row → append with `; `, no duplicates.

## Reliability

- No network / missing credentials → engine never loses data: append the entry to
  `~/.config/worklog/pending.jsonl`; `worklog flush` (and the next `add`) resends it.
- Idempotency: identical text already present in today's row → not duplicated.
- `--dry-run` to preview.

## One-time setup (detailed steps go in the implementation plan)

1. Create a Google Cloud project; enable the Google Sheets API.
2. Create a service account; download its JSON key → `~/.config/worklog/service-account.json`.
3. Create the spreadsheet; add `Log` and `Report` tabs (Report with the SUMIF/monthly
   formulas).
4. Share the spreadsheet with the service account email as Editor.
5. Put `spreadsheet_id` and tab names into `~/.config/worklog/config.json`.
6. `pip install gspread` (or a pinned venv for the CLI).
7. Install the skill into `~/.claude/skills/worklog/` and register the SessionStart hook.

## Testing

- CLI is unit-testable against a dedicated test spreadsheet.
- `--dry-run` mode validates the upsert decision (new vs append, hours math, date match)
  without writing.
- Verify: new day creates a row; same day same project accumulates; duplicate text is
  skipped; offline path buffers to `pending.jsonl` and `flush` resends.

## Out of scope (YAGNI)

- Full-auto blocking hooks that force logging without user involvement.
- Maintaining month-separator rows / totals by code (handled by Report formulas).
- A custom MCP server.
- Multi-user / shared-team timesheets.

## Addendum 2026-06-12 — single-sheet layout (supersedes flat Log + Report)

Per the user's choice, the engine maintains **one formatted sheet** that reproduces the
manual timesheet exactly — `MONTH YEAR` headers, per-month total rows (`March total | 19 |
10 days`), and a `GRAND TOTAL | … | N active days`. The earlier "flat `Log` + auto
`Report`" split is dropped.

Implementation (robust, not fragile in-place insertion): the **data rows are the single
source of truth**. On each write the engine (`worklog/layout.py`) parses out the data rows
(first cell matches `DD.MM.YYYY`), merges the new entry, and **regenerates the entire
layout** (`render()`), then overwrites the sheet (`backend.replace_all`). Month/total/grand
rows are derived, never parsed back in. "Active days" = count of distinct dates. Same
(date, project) accumulates hours and appends text. Setup needs only one tab named `Log`
(no Report tab, no formulas).
```
