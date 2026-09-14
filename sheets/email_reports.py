"""Baca/tulis sheet 'email_reports'.

CATATAN KEAMANAN: sheet ini nyimpen password dalam bentuk plaintext (nggak
di-encrypt) karena keterbatasan Google Sheets. Pastikan sharing spreadsheet
ini SANGAT dibatasi (cuma superadmin + service account), dan pertimbangkan
proteksi range/sheet khusus di Google Sheets (Data > Protected sheets and
ranges) buat sheet ini biar nggak sembarangan orang bisa lihat walau
punya akses edit ke spreadsheet."""
from sheets.client import get_or_create_worksheet, to_int
from sheets.setup import SHEET_SCHEMAS
from utils.timezone import now_str

_COL_USER_ID = 3
_COL_STATUS = 10


def _ws():
    return get_or_create_worksheet("email_reports", SHEET_SCHEMAS["email_reports"])


def save_email_report(team_name: str, user_id: int, nama: str, email: str,
                       password: str, email_pemulihan: str = "",
                       no_hp_pemulihan: str = "", kode_auth: str = "",
                       shortlink: str = ""):
    ws = _ws()
    ws.append_row([
        now_str(),
        team_name,
        user_id,
        nama,
        email,
        password,
        email_pemulihan,
        no_hp_pemulihan,
        kode_auth,
        "valid",
        shortlink,
    ])


def get_recent_email_reports_by_user(user_id: int, limit: int = 5) -> list[dict]:
    """Ambil laporan email milik 1 user, terbaru dulu, yang belum
    dibatalin. Tiap dict dikasih tambahan '_row_index' buat keperluan
    cancel_email_report() nanti."""
    ws = _ws()
    rows = ws.get_all_records()
    result = []
    for i, row in enumerate(rows, start=2):
        if to_int(row.get("user_id")) == user_id and row.get("status") != "dibatalkan":
            row["_row_index"] = i
            result.append(row)
    result.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return result[:limit]


def cancel_email_report(row_index: int, expected_user_id: int) -> bool:
    """Set status jadi 'dibatalkan'. Return False kalau baris itu ternyata
    bukan punya expected_user_id."""
    ws = _ws()
    actual_user_id = to_int(ws.cell(row_index, _COL_USER_ID).value)
    if actual_user_id != expected_user_id:
        return False
    ws.update_cell(row_index, _COL_STATUS, "dibatalkan")
    return True
