"""Helper hitung masa kerja dari tanggal join, dukung beberapa format
tanggal umum (angka maupun nama bulan). Dipakai bareng sama menu Anggota
(PM) dan command /id."""
from datetime import datetime

_DATE_FORMATS = [
    "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d",
    "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y", "%d %B %Y",
]


def parse_date(value: str):
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def describe_tenure(join_date: datetime) -> str:
    days = (datetime.now() - join_date).days
    if days < 0:
        return "-"
    tahun, sisa_hari = divmod(days, 365)
    bulan = sisa_hari // 30
    parts = []
    if tahun:
        parts.append(f"{tahun} tahun")
    if bulan:
        parts.append(f"{bulan} bulan")
    return " ".join(parts) if parts else "< 1 bulan"
