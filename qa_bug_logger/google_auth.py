"""Google OAuth for the optional Sheets/Drive backends. Tokens are stored as JSON, never pickled."""
import os

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_credentials(token_file: str, client_secrets: str):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = Credentials.from_authorized_user_file(token_file, SCOPES) if os.path.exists(token_file) else None
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not os.path.exists(client_secrets):
            raise FileNotFoundError(
                f"Missing {client_secrets}. Create an OAuth client (Desktop app) in Google Cloud Console > "
                "APIs & Services > Credentials and download it. Keep it out of git."
            )
        creds = InstalledAppFlow.from_client_secrets_file(client_secrets, SCOPES).run_local_server(port=0)
    with open(token_file, "w", encoding="utf-8") as fh:
        fh.write(creds.to_json())
    return creds
