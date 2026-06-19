"""Google Sheets authentication and spreadsheet access."""
from __future__ import annotations

import os

import gspread
from gspread import Client, Spreadsheet
from oauth2client.service_account import ServiceAccountCredentials

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def get_gspread_client() -> Client:
    creds_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not creds_path:
        raise OSError(
            "GOOGLE_SERVICE_ACCOUNT_JSON not set. "
            "Set it in .env or environment to the path of your service account JSON file."
        )
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, SCOPES)
    return gspread.authorize(creds)


def get_spreadsheet_id() -> str:
    spreadsheet_id = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    if not spreadsheet_id:
        raise OSError(
            "GOOGLE_SHEETS_SPREADSHEET_ID not set. "
            "Run 'ozon-agent sheets setup' to create a new spreadsheet."
        )
    return spreadsheet_id


def open_spreadsheet(client: Client, spreadsheet_id: str | None = None) -> Spreadsheet:
    sid = spreadsheet_id or get_spreadsheet_id()
    return client.open_by_key(sid)


def create_spreadsheet(client: Client, title: str) -> Spreadsheet:
    return client.create(title)
