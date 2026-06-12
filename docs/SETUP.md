# Worklog setup

## 1. Google Cloud service account
1. https://console.cloud.google.com → create / pick a project.
2. APIs & Services → Library → enable **Google Sheets API**.
3. APIs & Services → Credentials → Create credentials → **Service account**.
4. Open the service account → Keys → Add key → JSON → download.
5. Save it as `~/.config/worklog/service-account.json`.
6. Copy the service account **email** (looks like `name@project.iam.gserviceaccount.com`).

## 2. The spreadsheet
1. Create a Google Sheet. Copy its ID from the URL
   (`https://docs.google.com/spreadsheets/d/<THIS>/edit`).
2. Add a tab named **`Log`** with header row: `Date | Hours | What I did | Project`.
3. Add a **`Report`** tab that aggregates `Log` by month with `SUMIF` totals (template
   formulas below).
4. **Share** the spreadsheet with the service account email as **Editor**.
5. Put the ID into `~/.config/worklog/config.json` → `spreadsheet_id`.
6. (RU comma decimals) File → Settings → Locale → a comma-decimal locale, so `0.5`
   shows as `0,5`.

### Report tab formulas (one-time)
- Total hours: `=SUM(Log!B2:B)`.
- Per-project total: `=SUMIF(Log!D:D, A2, Log!B:B)` (with the project name in `A2`).
- Per-month total: easiest via a Pivot table (Insert → Pivot table) over `Log`, grouped by
  month (group the Date field) and Project, summing Hours — this reproduces the manual
  monthly-totals report exactly.

## 3. Install
Run `./install.sh`, then add `worklog` to PATH and register the hook (below).

## 4. Register the SessionStart hook
In `~/.claude/settings.json`:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /ABSOLUTE/PATH/claude-worklog-skill/hooks/session_start.py"
          }
        ]
      }
    ]
  }
}
```

## 5. Verify
```bash
cd /some/work/repo
worklog init "Test Project"
worklog add --project "Test Project" --hours 1 --text "setup verification" --dry-run
worklog add --project "Test Project" --hours 1 --text "setup verification"
worklog show
```
