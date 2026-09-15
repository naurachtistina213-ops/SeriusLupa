"""
Baca/tulis sheet 'anggota'. Termasuk logic lookup: utamakan username,
fallback ke user_id kalau username nggak ketemu/berubah.
"""
from sheets.client import get_or_create_worksheet, to_int
from sheets.setup import SHEET_SCHEMAS


def _ws():
    return get_or_create_worksheet("anggota", SHEET_SCHEMAS["anggota"])


def find_member(user_id: int, username: str | None):
    """Cari anggota di sheet. Prioritas: username dulu, baru fallback user_id.
    Kalau ketemu lewat fallback user_id, auto-update kolom username di sheet
    (biar sheet makin lama makin akurat / 'self-healing').

    Return dict {team_name, user_id, username, nama} atau None kalau nggak
    ketemu sama sekali (artinya orang itu belum terdaftar)."""
    ws = _ws()
    rows = ws.get_all_records()

    # 1. Coba cocokin by username dulu (kalau username-nya ada)
    if username:
        for i, row in enumerate(rows, start=2):  # baris 1 = header
            if str(row.get("username", "")).lstrip("@").lower() == username.lstrip("@").lower():
                return row

    # 2. Fallback: cocokin by user_id
    for i, row in enumerate(rows, start=2):
        if to_int(row.get("user_id")) == user_id:
            # username di sheet udah nggak sinkron -> update otomatis
            if username and row.get("username") != username:
                ws.update_cell(i, 3, username)  # kolom ke-3 = username
                row["username"] = username
            return row

    return None


def find_member_by_id(user_id: int) -> dict | None:
    """Cari anggota by user_id doang (tanpa perlu tau team-nya dulu).
    Dipakai buat command /id dan menu Anggota."""
    for row in _ws().get_all_records():
        if to_int(row.get("user_id")) == user_id:
            return row
    return None


def find_member_by_username(username: str) -> dict | None:
    """Cari anggota by username Telegram ORANG LAIN (bukan diri sendiri
    kayak find_member). Dipakai buat command /id."""
    username = username.lstrip("@").lower()
    for row in _ws().get_all_records():
        if str(row.get("username", "")).lstrip("@").lower() == username:
            return row
    return None


def get_team_members(team_name: str) -> list[dict]:
    """Ambil semua anggota dari 1 team, buat keperluan mass mention.
    Case-insensitive biar nggak kena masalah 'team1' vs 'Team1'."""
    ws = _ws()
    return [row for row in ws.get_all_records() if row.get("team_name", "").lower() == team_name.lower()]


def get_all_members() -> list[dict]:
    """Ambil semua anggota dari SEMUA team. Dipakai buat target 'main' -
    bukan nyari baris team_name='main' (yang emang nggak akan ada, karena
    1 orang cuma 1 team asli), tapi diartikan sebagai gabungan semua team."""
    return _ws().get_all_records()


def list_team_names() -> list[str]:
    """Daftar semua nama team yang beneran punya anggota (case asli,
    misal 'Team1'). Ini sumber kebenaran soal 'team apa aja yang ada' -
    BUKAN sheet 'teams' (yang isinya cuma mapping chat_id, bisa aja belum
    lengkap kalau suatu team belum punya grup sendiri)."""
    ws = _ws()
    seen = {}
    for row in ws.get_all_records():
        name = row.get("team_name", "")
        if name and name.lower() not in seen:
            seen[name.lower()] = name
    return list(seen.values())


def is_member_of_team(user_id: int, username: str | None, team_name: str) -> bool:
    member = find_member(user_id, username)
    return bool(member) and member.get("team_name") == team_name
