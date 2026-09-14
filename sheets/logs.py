"""Tulis event umum ke sheet 'logs' (akses ditolak, dll)."""
from sheets.client import get_or_create_worksheet
from sheets.setup import SHEET_SCHEMAS
from utils.timezone import now_str


def _ws():
    return get_or_create_worksheet("logs", SHEET_SCHEMAS["logs"])


def log_event(chat_id, user_id, aksi: str, detail: str = ""):
    _ws().append_row([now_str(), chat_id, user_id, aksi, detail])
