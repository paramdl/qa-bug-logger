"""
Where screenshots and videos go. Returns one link (or path) per file for the bug record.

  local  copied into <folder>/<project>/<bug-id>/ (default)
  drive  uploaded to Google Drive under <parent>/<project>/; private unless share_public is true
"""
import mimetypes
import shutil
from pathlib import Path


class LocalEvidenceStore:
    def __init__(self, folder: str = "evidence"):
        self.folder = Path(folder)

    def store(self, files: list, project: str, bug_id: str) -> list:
        target = self.folder / project / bug_id
        links = []
        for f in map(Path, files):
            if not f.is_file():
                print(f"  Skipped (not found): {f}")
                continue
            target.mkdir(parents=True, exist_ok=True)
            dest = target / f.name
            shutil.copy2(f, dest)
            links.append(dest.as_posix())
        return links


def drive_query_literal(value: str) -> str:
    """Escape a value for a Drive 'q' string literal; an unescaped quote breaks or alters the query."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


class DriveEvidenceStore:
    def __init__(self, parent_folder_id: str, share_public: bool = False,
                 token_file: str = ".google_token.json", client_secrets: str = "client_secrets.json"):
        from googleapiclient.discovery import build  # optional dependency
        from .google_auth import get_credentials
        self.parent = parent_folder_id
        self.share_public = share_public
        self.service = build("drive", "v3", credentials=get_credentials(token_file, client_secrets))

    def _folder(self, name: str, parent: str) -> str:
        q = (f"name='{drive_query_literal(name)}' and mimeType='application/vnd.google-apps.folder' "
             f"and '{drive_query_literal(parent)}' in parents and trashed=false")
        found = self.service.files().list(q=q, fields="files(id)").execute().get("files", [])
        if found:
            return found[0]["id"]
        meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent]}
        return self.service.files().create(body=meta, fields="id").execute()["id"]

    def store(self, files: list, project: str, bug_id: str) -> list:
        from googleapiclient.http import MediaFileUpload
        folder = self._folder(project, self.parent)
        links = []
        for f in map(Path, files):
            if not f.is_file():
                print(f"  Skipped (not found): {f}")
                continue
            mime = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            meta = {"name": f"{bug_id}_{f.name}", "parents": [folder]}
            up = self.service.files().create(body=meta, media_body=MediaFileUpload(str(f), mimetype=mime, resumable=True),
                                             fields="id,webViewLink").execute()
            # Evidence often shows user data: link sharing is opt-in, not the default.
            if self.share_public:
                self.service.permissions().create(fileId=up["id"], body={"type": "anyone", "role": "reader"}).execute()
            links.append(up.get("webViewLink", f"https://drive.google.com/file/d/{up['id']}/view"))
        return links


def make_evidence_store(config: dict):
    kind = config.get("evidence", "local")
    if kind == "local":
        return LocalEvidenceStore(config.get("evidence_folder", "evidence"))
    if kind == "drive":
        return DriveEvidenceStore(config["drive_parent_folder_id"], bool(config.get("share_public", False)),
                                  config.get("token_file", ".google_token.json"),
                                  config.get("client_secrets", "client_secrets.json"))
    raise ValueError(f"unknown evidence store {kind!r} (use 'local' or 'drive')")
