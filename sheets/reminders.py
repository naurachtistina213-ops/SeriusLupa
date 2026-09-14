"""Baca sheet 'reminders' dan sheet 'teams' (buat resolve target)."""
from sheets.client import get_or_create_worksheet, to_int
from sheets.setup import SHEET_SCHEMAS

_COL = {"id": 1, "pesan": 2, "waktu": 3, "recurrence": 4, "target": 5, "status": 6}


def _reminders_ws():
    return get_or_create_worksheet("reminders", SHEET_SCHEMAS["reminders"])


def _teams_ws():
    return get_or_create_worksheet("teams", SHEET_SCHEMAS["teams"])


def get_active_reminders() -> list[dict]:
    ws = _reminders_ws()
    return [r for r in ws.get_all_records() if r.get("status") == "aktif"]


def get_all_reminders_with_index() -> list[dict]:
    """Semua reminder (aktif maupun nggak), tiap dict dikasih tambahan
    '_row_index' - dipakai buat menu edit/matikan reminder di PM."""
    ws = _reminders_ws()
    result = []
    for i, row in enumerate(ws.get_all_records(), start=2):  # baris 1 = header
        row["_row_index"] = i
        result.append(row)
    return result


def get_next_reminder_id() -> str:
    """Auto-generate ID baru (angka), biar superadmin nggak perlu mikirin
    ID unik sendiri pas nambah reminder dari PM."""
    max_id = 0
    for row in _reminders_ws().get_all_records():
        try:
            max_id = max(max_id, int(row.get("id")))
        except (TypeError, ValueError):
            continue
    return str(max_id + 1)


def add_reminder(pesan: str, waktu: str, target: str, recurrence: str = "harian",
                  status: str = "aktif") -> str:
    """Tambah reminder baru, ID di-generate otomatis. Return ID yang dipakai."""
    new_id = get_next_reminder_id()
    _reminders_ws().append_row([new_id, pesan, waktu, recurrence, target, status])
    return new_id


def update_reminder_field(row_index: int, field: str, value: str) -> bool:
    col = _COL.get(field)
    if not col:
        return False
    _reminders_ws().update_cell(row_index, col, value)
    return True


def set_reminder_status(row_index: int, status: str) -> bool:
    return update_reminder_field(row_index, "status", status)


def resolve_targets(target_field: str) -> list[dict]:
    """target_field bisa "main", nama 1 team, atau beberapa team dipisah koma.
    Return list of {"chat_id": ..., "topic_id": ... atau None}.

    "main" butuh chat_id grup utama - untuk skeleton ini diambil dari baris
    teams dengan team_name == "main" (isi manual di sheet), topic_id
    dikosongin biar jatuh ke General."""
    teams_ws = _teams_ws()
    teams_by_name = {row["team_name"]: row for row in teams_ws.get_all_records()}

    targets = []
    for name in [t.strip() for t in target_field.split(",")]:
        row = teams_by_name.get(name)
        if not row:
            continue
        chat_id = to_int(row.get("chat_id"))
        if chat_id is None:
            continue
        targets.append({
            "chat_id": chat_id,
            "topic_id": to_int(row.get("topic_id")),
        })
    return targets
