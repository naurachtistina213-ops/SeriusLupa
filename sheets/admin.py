"""
Baca sheet 'admin_whitelist'. Nentuin apakah seseorang admin/superadmin,
dan team apa yang jadi scope dia.
"""
from config import SUPERADMIN_IDS
from sheets.client import get_or_create_worksheet
from sheets.setup import SHEET_SCHEMAS


def _ws():
    return get_or_create_worksheet("admin_whitelist", SHEET_SCHEMAS["admin_whitelist"])


def get_admin_info(user_id: int):
    """Return dict {nama, managed_team} kalau user_id ini admin/whitelisted,
    atau None kalau bukan.

    Superadmin dari env (SUPERADMIN_IDS) otomatis dianggap scope 'all',
    walau belum sempat dicatat di sheet."""
    if user_id in SUPERADMIN_IDS:
        return {"user_id": user_id, "nama": "Superadmin", "managed_team": "all"}

    ws = _ws()
    for row in ws.get_all_records():
        if str(row.get("user_id", "")) == str(user_id) and str(row.get("is_whitelisted", "")).upper() == "TRUE":
            return row
    return None


def is_superadmin(user_id: int) -> bool:
    info = get_admin_info(user_id)
    return bool(info) and info.get("managed_team") == "all"


def get_all_superadmin_ids() -> set[int]:
    """Gabungan superadmin dari env SUPERADMIN_IDS + yang kedaftar di
    sheet admin_whitelist dengan managed_team='all'. Dipakai buat notif
    (misal ada user belum terdaftar coba PM bot)."""
    ids = set(SUPERADMIN_IDS)
    for row in _ws().get_all_records():
        if str(row.get("managed_team", "")).lower() == "all" and str(row.get("is_whitelisted", "")).upper() == "TRUE":
            uid = str(row.get("user_id", "")).strip()
            if uid.isdigit():
                ids.add(int(uid))
    return ids


_COL_IS_WHITELISTED = 3


def list_whitelisted() -> list[dict]:
    """Semua admin/leader yang lagi aktif whitelisted (is_whitelisted=TRUE),
    dikasih '_row_index' buat keperluan revoke_access(). CATATAN: superadmin
    dari env SUPERADMIN_IDS nggak ikut muncul di sini (mereka nggak
    tersimpan sebagai baris di sheet ini)."""
    result = []
    for i, row in enumerate(_ws().get_all_records(), start=2):
        if str(row.get("is_whitelisted", "")).upper() == "TRUE":
            row["_row_index"] = i
            result.append(row)
    return result


def revoke_access(row_index: int):
    """Cabut akses - set is_whitelisted jadi FALSE (bukan hapus baris,
    biar riwayatnya tetap ada)."""
    _ws().update_cell(row_index, _COL_IS_WHITELISTED, "FALSE")


def can_manage_team(user_id: int, team_name: str) -> bool:
    """Superadmin bisa manage semua team. Admin biasa cuma team dia sendiri.
    Case-insensitive biar nggak kena masalah 'team1' vs 'Team1'."""
    info = get_admin_info(user_id)
    if not info:
        return False
    managed = str(info.get("managed_team", ""))
    return managed == "all" or managed.lower() == team_name.lower()
