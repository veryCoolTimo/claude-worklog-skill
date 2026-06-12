from worklog.core import HEADERS
from worklog import config


class FakeBackend:
    """In-memory backend for tests and --dry-run."""

    def __init__(self, rows=None):
        self.rows = [list(r) for r in rows] if rows else [HEADERS[:]]

    def get_all_values(self):
        return [list(r) for r in self.rows]

    def replace_all(self, rows):
        self.rows = [list(r) for r in rows]


class GspreadBackend:
    """Wraps a gspread Worksheet behind the backend interface."""

    def __init__(self, worksheet):
        self.ws = worksheet

    def get_all_values(self):
        return self.ws.get_all_values()

    def replace_all(self, rows):
        # Regenerate the whole sheet: clear values, then write from A1.
        self.ws.clear()
        self.ws.update(range_name="A1", values=rows, value_input_option="USER_ENTERED")


def open_worksheet(cfg=None):
    """Open the timesheet worksheet via service-account auth. Raises on missing creds/network."""
    import gspread
    from google.oauth2.service_account import Credentials

    cfg = cfg or config.load_config()
    sa = config.service_account_path()
    if not sa.exists():
        raise FileNotFoundError(f"Service account key not found: {sa}")
    if not cfg.get("spreadsheet_id"):
        raise ValueError("spreadsheet_id is not set in config.json")

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(str(sa), scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(cfg["spreadsheet_id"])
    ws = sheet.worksheet(cfg.get("log_tab", "Log"))
    return GspreadBackend(ws)
