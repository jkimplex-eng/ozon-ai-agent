"""Google Sheets authentication, spreadsheet access, and write throttling."""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import gspread
from gspread import Client, Spreadsheet
from gspread.exceptions import APIError
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)

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


def _get_retry_config() -> tuple[int, int]:
    """Return (attempts, backoff_seconds) from env."""
    attempts = int(os.environ.get("SHEETS_RETRY_ATTEMPTS", "3"))
    backoff = int(os.environ.get("SHEETS_RETRY_BACKOFF_SECONDS", "30"))
    return attempts, backoff


def _is_rate_limit_error(exc: Exception) -> bool:
    """Check if exception is a 429 rate limit error."""
    if not isinstance(exc, APIError):
        return False
    try:
        status_code: int = exc.response.status_code
        return status_code == 429
    except AttributeError:
        return False


def retry_on_rate_limit(
    func: Any, *args: Any, **kwargs: Any,
) -> Any:
    """Call func with retry on 429 rate limit errors.

    Retries with exponential-ish backoff: 30s, 60s, 90s.
    """
    attempts, base_backoff = _get_retry_config()

    for attempt in range(attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if _is_rate_limit_error(e) and attempt < attempts - 1:
                delay = base_backoff * (attempt + 1)
                logger.warning(
                    "Rate limited (429), retrying in %ds (attempt %d/%d)...",
                    delay, attempt + 1, attempts,
                )
                time.sleep(delay)
            else:
                raise
    return func(*args, **kwargs)
