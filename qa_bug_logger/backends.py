"""
Where bugs are stored. Every backend offers the same three operations, so the CLI and the
retest runner never care which one is in use.

  csv     one CSV file per project under a folder (no account needed)
  sheets  one tab per project in a Google Sheet (needs requirements-google.txt)
"""
import csv
from pathlib import Path

from .model import HEADERS, Bug, now

STATUS_COL, RETEST_DATE_COL = HEADERS.index("Status"), HEADERS.index("Retest Date")


class CsvBackend:
    def __init__(self, folder: str):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def _file(self, project: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in project)
        return self.folder / f"{safe}.csv"

    def _read(self, project: str) -> list:
        f = self._file(project)
        if not f.exists():
            return [HEADERS]
        with open(f, newline="", encoding="utf-8") as fh:
            return list(csv.reader(fh))

    def _write(self, project: str, rows: list) -> None:
        with open(self._file(project), "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(rows)

    def log_bug(self, bug: Bug) -> int:
        rows = self._read(bug.project)
        if any(r and r[0] == bug.bug_id for r in rows[1:]):
            raise ValueError(f"{bug.bug_id} already exists in project {bug.project!r}")
        rows.append(bug.to_row())
        self._write(bug.project, rows)
        return len(rows)  # 1-based row number, header is row 1

    def get_open_bugs(self, project: str) -> list:
        rows = self._read(project)
        return [dict(zip(HEADERS, r)) for r in rows[1:] if r[STATUS_COL].strip().lower() == "open"]

    def update_retest(self, bug_id: str, project: str, result: str, notes: str) -> bool:
        rows = self._read(project)
        for r in rows[1:]:
            if r[0] == bug_id:
                r[RETEST_DATE_COL:RETEST_DATE_COL + 3] = [now(), result, notes]
                if result == "Pass":
                    r[STATUS_COL] = "Resolved"
                self._write(project, rows)
                return True
        return False


class SheetsBackend:
    """Google Sheets, one tab per project, header row bold and frozen on first use."""

    def __init__(self, spreadsheet_id: str, token_file: str = ".google_token.json",
                 client_secrets: str = "client_secrets.json"):
        from googleapiclient.discovery import build  # optional dependency
        from .google_auth import get_credentials
        self.spreadsheet_id = spreadsheet_id
        self.service = build("sheets", "v4", credentials=get_credentials(token_file, client_secrets))

    def _values(self):
        return self.service.spreadsheets().values()

    def _ensure_tab(self, tab: str) -> None:
        meta = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        sheets = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
        if tab in sheets:
            return
        reply = self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": tab}}}]},
        ).execute()
        sheet_id = reply["replies"][0]["addSheet"]["properties"]["sheetId"]
        self._values().update(spreadsheetId=self.spreadsheet_id, range=f"'{tab}'!A1",
                              valueInputOption="RAW", body={"values": [HEADERS]}).execute()
        self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body={"requests": [
            {"repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat"}},
            {"updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount"}},
        ]}).execute()

    def log_bug(self, bug: Bug) -> int:
        self._ensure_tab(bug.project)
        result = self._values().append(
            spreadsheetId=self.spreadsheet_id, range=f"'{bug.project}'!A1", valueInputOption="RAW",
            insertDataOption="INSERT_ROWS", body={"values": [bug.to_row()]},
        ).execute()
        updated = result["updates"]["updatedRange"]           # e.g. 'Proj'!A12:Q12
        return int("".join(ch for ch in updated.split("!")[1].split(":")[0] if ch.isdigit()))

    def _rows(self, project: str) -> list:
        data = self._values().get(spreadsheetId=self.spreadsheet_id, range=f"'{project}'!A:Q").execute()
        return data.get("values", [])

    def get_open_bugs(self, project: str) -> list:
        rows = self._rows(project)
        out = []
        for r in rows[1:]:
            r = r + [""] * (len(HEADERS) - len(r))
            if r[STATUS_COL].strip().lower() == "open":
                out.append(dict(zip(HEADERS, r)))
        return out

    def update_retest(self, bug_id: str, project: str, result: str, notes: str) -> bool:
        for i, r in enumerate(self._rows(project)[1:], start=2):
            if r and r[0] == bug_id:
                self._values().update(spreadsheetId=self.spreadsheet_id, range=f"'{project}'!O{i}:Q{i}",
                                      valueInputOption="RAW", body={"values": [[now(), result, notes]]}).execute()
                if result == "Pass":
                    self._values().update(spreadsheetId=self.spreadsheet_id, range=f"'{project}'!K{i}",
                                          valueInputOption="RAW", body={"values": [["Resolved"]]}).execute()
                return True
        return False


def make_backend(config: dict):
    kind = config.get("backend", "csv")
    if kind == "csv":
        return CsvBackend(config.get("csv_folder", "bug-logs"))
    if kind == "sheets":
        return SheetsBackend(config["spreadsheet_id"], config.get("token_file", ".google_token.json"),
                             config.get("client_secrets", "client_secrets.json"))
    raise ValueError(f"unknown backend {kind!r} (use 'csv' or 'sheets')")
