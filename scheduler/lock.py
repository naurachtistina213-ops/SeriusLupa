"""
Cegah reminder yang sama kekirim dobel kalau Railway sempet jalanin 2
instance bersamaan pas deploy ulang.

Pendekatan simpel: catat 'reminder_id + waktu_slot' yang udah dikirim ke
sheet 'logs', dan cek dulu sebelum kirim - bukan cuma ngandelin jadwal cron.
Untuk skala kecil ini cukup; kalau makin besar, pertimbangkan Redis/lock
service beneran.
"""

from sheets.client import get_or_create_worksheet
from sheets.setup import SHEET_SCHEMAS
from utils.timezone import now_str

_sent_cache = set()  # cache in-memory per-instance, dicek dulu sebelum ke sheet


def _log_ws():
    return get_or_create_worksheet("logs", SHEET_SCHEMAS["logs"])


def _slot_key(reminder_id: str, slot: str) -> str:
    return f"{reminder_id}::{slot}"


def already_sent(reminder_id: str, slot: str) -> bool:
    key = _slot_key(reminder_id, slot)
    if key in _sent_cache:
        return True
    # cek ke sheet juga (kalau instance lain yang udah kirim & catat duluan)
    ws = _log_ws()
    for row in ws.get_all_records():
        if row.get("aksi") == "reminder_sent" and row.get("detail") == key:
            _sent_cache.add(key)
            return True
    return False


def mark_sent(reminder_id: str, slot: str, chat_id: int):
    key = _slot_key(reminder_id, slot)
    _sent_cache.add(key)
    ws = _log_ws()
    ws.append_row([
        now_str(),
        chat_id,
        "",
        "reminder_sent",
        key,
    ])
