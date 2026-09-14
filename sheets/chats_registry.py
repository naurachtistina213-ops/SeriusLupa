"""
Baca/tulis sheet 'chats_registry'. Ini yang nyimpen semua chat_id + topic_id
yang pernah 'ketemu' bot, otomatis - admin cukup isi kolom team_name-nya aja
manual di spreadsheet buat masing-masing baris baru yang muncul.
"""

from sheets.client import get_or_create_worksheet, to_int
from sheets.setup import SHEET_SCHEMAS
from utils.timezone import now_str

# Cache in-memory biar nggak query sheet tiap ada pesan masuk (bisa rame
# banget kalau grupnya aktif). Key: (chat_id, topic_id_or_none).
_known_cache: set[tuple[int, int | None]] = set()
_cache_loaded = False


def _ws():
    return get_or_create_worksheet("chats_registry", SHEET_SCHEMAS["chats_registry"])


def _load_cache_if_needed():
    global _cache_loaded
    if _cache_loaded:
        return
    ws = _ws()
    for row in ws.get_all_records():
        chat_id = to_int(row.get("chat_id"))
        if chat_id is None:
            continue
        _known_cache.add((chat_id, to_int(row.get("topic_id"))))
    _cache_loaded = True


def reset_cache():
    """Kosongin cache in-memory, biar data ke-load ulang fresh dari sheet.
    Dipanggil dari command /sync (khusus superadmin)."""
    global _cache_loaded
    _known_cache.clear()
    _cache_loaded = False


def is_known(chat_id: int, topic_id: int | None) -> bool:
    _load_cache_if_needed()
    return (chat_id, topic_id) in _known_cache


def register_chat(chat_id: int, topic_id: int | None, nama_grup: str = "",
                   nama_topik: str = ""):
    """Catat kombinasi chat_id+topic_id baru ke sheet, kalau belum ada.
    Kolom team_name dikosongin sengaja - itu yang diisi manual sama admin."""
    _load_cache_if_needed()
    key = (chat_id, topic_id)
    if key in _known_cache:
        return  # udah pernah tercatat, nggak usah dobel

    ws = _ws()
    ws.append_row([
        chat_id,
        topic_id if topic_id is not None else "",
        nama_grup,
        nama_topik,
        now_str(),
        "",  # team_name - diisi manual oleh admin
    ])
    _known_cache.add(key)
