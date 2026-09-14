"""
Helper zona waktu terpusat. Semua timestamp yang ditulis ke sheet (laporan
tugas, laporan email, keluhan, custom command, chats_registry, dst) pakai
fungsi di sini, BUKAN datetime.now() langsung - biar semuanya konsisten
ikut satu environment variable, dan gampang diubah tanpa perlu edit
banyak file satu-satu.

Cara ganti zona waktu: ubah DEFAULT_TIMEZONE di Railway (tab Variables)
atau .env, misal:
- "Asia/Jakarta"  -> WIB
- "Asia/Colombo"  -> waktu Sri Lanka
- "Asia/Makassar" -> WITA
Daftar nama timezone yang valid ada di:
https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

Redeploy/restart bot setelah ganti variable-nya biar keefek.
"""
from datetime import datetime

import pytz

from config import DEFAULT_TIMEZONE


def now() -> datetime:
    """Waktu sekarang, timezone-aware, sesuai DEFAULT_TIMEZONE."""
    tz = pytz.timezone(DEFAULT_TIMEZONE)
    return datetime.now(tz)


def now_str() -> str:
    """Format siap-tulis ke kolom timestamp di sheet: 'YYYY-MM-DD HH:MM:SS'."""
    return now().strftime("%Y-%m-%d %H:%M:%S")
