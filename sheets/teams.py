"""Baca sheet 'teams'. Termasuk resolve 'chat ini punya team apa'."""
from sheets.client import get_or_create_worksheet, to_int
from sheets.setup import SHEET_SCHEMAS


def _ws():
    return get_or_create_worksheet("teams", SHEET_SCHEMAS["teams"])


def get_all_teams() -> list[dict]:
    return _ws().get_all_records()


def team_exists(team_name: str) -> bool:
    return get_canonical_name(team_name) is not None


def get_canonical_name(team_name: str) -> str | None:
    """Cari nama tim asli (case yang bener, misal 'Team1') dari input yang
    bisa aja beda huruf besar/kecil (misal user ketik 'team1'). Sumbernya
    sheet 'anggota' (list_team_names) - itu daftar tim yang beneran punya
    anggota, BUKAN sheet 'teams' (yang cuma soal chat_id mana punya tim
    apa, dan bisa aja belum lengkap kalau suatu tim belum punya grup
    sendiri, kayak yang sempet bikin /bank team2 salah sasaran)."""
    from sheets.users import list_team_names
    for name in list_team_names():
        if name.lower() == team_name.lower():
            return name
    return None


def get_chat_for_team(team_name: str) -> tuple[int, int | None] | None:
    """Kebalikan dari get_team_by_chat - cari chat_id/topic_id ASLI milik
    1 team (dari sheet 'teams'), berdasarkan nama team-nya. Dipakai buat
    nge-redirect pesan command ke grup team target, bukan ke grup tempat
    command itu diketik."""
    for row in get_all_teams():
        if row.get("team_name", "").lower() == team_name.lower():
            chat_id = to_int(row.get("chat_id"))
            if chat_id is None:
                continue
            return chat_id, to_int(row.get("topic_id"))
    return None


def get_team_by_chat(chat_id: int, topic_id: int | None) -> dict | None:
    """Cari baris team yang chat_id (+topic_id kalau ada) nya cocok sama
    chat tempat pesan ini dikirim. Ini yang bikin command tanpa argumen tim
    otomatis tau 'chat ini punya team apa'."""
    for row in get_all_teams():
        if to_int(row.get("chat_id")) != chat_id:
            continue
        if to_int(row.get("topic_id")) == topic_id:
            return row
    return None
