"""Baca/tulis sheet 'task_reports'."""
from sheets.client import get_or_create_worksheet, to_int
from sheets.setup import SHEET_SCHEMAS
from utils.timezone import now_str

_COL_USER_ID = 3
_COL_STATUS = 8


def _ws():
    return get_or_create_worksheet("task_reports", SHEET_SCHEMAS["task_reports"])


def get_all_links() -> list[str]:
    """Ambil semua link yang udah pernah dilaporkan, buat cek duplikat."""
    ws = _ws()
    return [row.get("link", "") for row in ws.get_all_records()]


def save_report(team_name: str, user_id: int, nama: str, jenis_tugas: str,
                 link: str, is_custom: bool):
    ws = _ws()
    ws.append_row([
        now_str(),
        team_name,
        user_id,
        nama,
        jenis_tugas,
        link,
        "TRUE" if is_custom else "FALSE",
        "valid",
    ])


def get_recent_reports_by_user(user_id: int, limit: int = 5) -> list[dict]:
    """Ambil laporan link (bukan email) milik 1 user, terbaru dulu, yang
    belum dibatalin. Tiap dict dikasih tambahan '_row_index' buat keperluan
    cancel_report() nanti."""
    ws = _ws()
    rows = ws.get_all_records()
    result = []
    for i, row in enumerate(rows, start=2):  # baris 1 = header
        if to_int(row.get("user_id")) == user_id and row.get("status_validasi") != "dibatalkan":
            row["_row_index"] = i
            result.append(row)
    result.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return result[:limit]


def cancel_report(row_index: int, expected_user_id: int) -> bool:
    """Set status_validasi jadi 'dibatalkan'. Return False kalau baris itu
    ternyata bukan punya expected_user_id (proteksi biar nggak bisa
    batalin laporan orang lain)."""
    ws = _ws()
    actual_user_id = to_int(ws.cell(row_index, _COL_USER_ID).value)
    if actual_user_id != expected_user_id:
        return False
    ws.update_cell(row_index, _COL_STATUS, "dibatalkan")
    return True
