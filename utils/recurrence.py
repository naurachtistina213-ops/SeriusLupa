"""
Helper buat kolom 'recurrence' di sheet reminders. Nilai yang valid:
- kosong / "harian"        -> reminder jalan tiap hari
- nama hari (senin, dst)   -> reminder cuma jalan mingguan, di hari itu

Jam ('waktu') tetap bebas beda-beda per reminder, nggak terikat sama
recurrence-nya - jadi 1 reminder harian jam 09:00, reminder lain mingguan
tiap Senin jam 15:00, dua-duanya bisa hidup bareng tanpa saling ganggu.
"""
DAY_MAP = {
    "senin": 0, "selasa": 1, "rabu": 2, "kamis": 3,
    "jumat": 4, "sabtu": 5, "minggu": 6,
}

RECURRENCE_HINT = "\"harian\", atau nama hari (senin/selasa/rabu/kamis/jumat/sabtu/minggu)"


def is_valid_recurrence(value: str) -> bool:
    v = (value or "").strip().lower()
    return v in ("", "harian") or v in DAY_MAP


def normalize_recurrence(value: str) -> str:
    v = (value or "").strip().lower()
    return "harian" if v == "" else v


def matches_today(recurrence: str, weekday: int) -> bool:
    """weekday: 0=Senin ... 6=Minggu, sesuai datetime.weekday()."""
    r = (recurrence or "").strip().lower()
    if not r or r == "harian":
        return True
    return DAY_MAP.get(r) == weekday


def describe(recurrence: str) -> str:
    r = (recurrence or "").strip().lower()
    if not r or r == "harian":
        return "Harian"
    return f"Mingguan ({r.capitalize()})"
