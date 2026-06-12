# Worklog setup

## 1. Google Cloud service account
1. https://console.cloud.google.com → create / pick a project.
2. APIs & Services → Library → enable **Google Sheets API**.
3. APIs & Services → Credentials → Create credentials → **Service account**.
4. Open the service account → Keys → Add key → JSON → download.
5. Save it as `~/.config/worklog/service-account.json`.
6. Copy the service account **email** (looks like `name@project.iam.gserviceaccount.com`).

## 2. The spreadsheet
The engine maintains a **single formatted sheet** — it inserts the `MONTH YEAR` headers,
the per-month total rows, and the `GRAND TOTAL` itself, regenerating them on every write.
You do **not** create a separate report tab or any formulas.

1. Create a Google Sheet. Copy its ID from the URL
   (`https://docs.google.com/spreadsheets/d/<THIS>/edit`).
2. Name the tab **`Log`** (must match `log_tab` in `config.json`). Leave it empty — the
   engine writes the header row and everything else on the first `worklog add`.
3. **Share** the spreadsheet with the service account email as **Editor**.
4. Put the ID into `~/.config/worklog/config.json` → `spreadsheet_id`.
5. (RU comma decimals) File → Settings → Locale → a comma-decimal locale, so `0.5`
   shows as `0,5`.

> Do not hand-edit the `MONTH YEAR`, `… total`, or `GRAND TOTAL` rows — they are derived
> from the data rows and rebuilt on each write. Edit only the daily data rows if you must.

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
