"""
Baca/tulis sheet 'custom_commands'. Command selalu di-scope ke 1 chat_id
(tempat command itu didaftarin) - ini yang bikin command leader team
otomatis 'ke-lock' cuma di grup mereka sendiri, dan superadmin bisa daftarin
di grup manapun yang dia mau.
"""
from sheets.client import get_or_create_worksheet, to_int
from sheets.setup import SHEET_SCHEMAS
from utils.timezone import now_str


def _ws():
    return get_or_create_worksheet("custom_commands", SHEET_SCHEMAS["custom_commands"])


def find_command(command: str, chat_id: int) -> dict | None:
    command = command.lower().lstrip("/")
    for row in _ws().get_all_records():
        if row.get("command", "").lower() == command and to_int(row.get("chat_id")) == chat_id:
            return row
    return None


def save_or_update_command(command: str, pesan: str, target_team: str,
                            dibuat_oleh: int, chat_id: int):
    """Kalau command yang sama (di chat_id yang sama) udah ada, di-update
    (bukan duplikat) - ini otomatis jadi fitur 'edit command' juga."""
    command = command.lower().lstrip("/")
    ws = _ws()
    rows = ws.get_all_records()

    for i, row in enumerate(rows, start=2):  # baris 1 = header
        if row.get("command", "").lower() == command and to_int(row.get("chat_id")) == chat_id:
            ws.update(f"A{i}:G{i}", [[
                command, pesan, target_team, "TRUE", dibuat_oleh, chat_id,
                now_str(),
            ]])
            return "updated"

    ws.append_row([
        command, pesan, target_team, "TRUE", dibuat_oleh, chat_id,
        now_str(),
    ])
    return "created"


def list_commands_for_chat(chat_id: int) -> list[dict]:
    return [r for r in _ws().get_all_records() if to_int(r.get("chat_id")) == chat_id]


def get_all_commands() -> list[dict]:
    """Semua custom command yang terdaftar, lintas semua chat - dipakai
    buat /help."""
    return _ws().get_all_records()
