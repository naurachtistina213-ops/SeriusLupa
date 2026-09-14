"""
Auto-archive baris lama (>120 hari, ~4 bulan) dari sheet yang cepat
numpuk (task_reports, email_reports, keluhan, logs) - dipindah ke tab
'<nama>_archive' (header sama, dibuat otomatis kalau belum ada) biar
sheet aktif tetap ringan. Data TIDAK dihapus permanen, cuma dipindah.
"""
import logging
from datetime import datetime, timedelta

from sheets.client import get_or_create_worksheet
from sheets.setup import SHEET_SCHEMAS

logger = logging.getLogger(__name__)

ARCHIVE_AFTER_DAYS = 120  # ~4 bulan
ARCHIVABLE_SHEETS = ["task_reports", "email_reports", "keluhan", "logs"]


def _parse_timestamp(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


def archive_sheet(sheet_name: str) -> int:
    """Pindahin baris lama dari 1 sheet ke tab arsipnya. Return jumlah
    baris yang dipindah."""
    headers = SHEET_SCHEMAS[sheet_name]
    ws = get_or_create_worksheet(sheet_name, headers)
    archive_ws = get_or_create_worksheet(f"{sheet_name}_archive", headers)

    cutoff = datetime.now() - timedelta(days=ARCHIVE_AFTER_DAYS)
    rows = ws.get_all_records()

    old_rows = []  # list of (row_index, values sesuai urutan header)
    for i, row in enumerate(rows, start=2):  # baris 1 = header
        ts = _parse_timestamp(row.get("timestamp", ""))
        if ts and ts < cutoff:
            old_rows.append((i, [row.get(h, "") for h in headers]))

    if not old_rows:
        return 0

    archive_ws.append_rows([values for _, values in old_rows])

    # Hapus dari sheet aktif, MULAI DARI BARIS PALING BAWAH - kalau
    # dihapus dari atas, index baris di bawahnya bakal geser dan salah
    # sasaran.
    for row_index, _ in sorted(old_rows, key=lambda x: x[0], reverse=True):
        ws.delete_rows(row_index)

    logger.info("Archive: %d baris dipindah dari '%s' ke '%s_archive'",
                len(old_rows), sheet_name, sheet_name)
    return len(old_rows)


def archive_all() -> dict[str, int]:
    """Jalanin archive_sheet buat semua sheet di ARCHIVABLE_SHEETS.
    Return {nama_sheet: jumlah_baris_dipindah} (-1 kalau gagal)."""
    result = {}
    for name in ARCHIVABLE_SHEETS:
        try:
            result[name] = archive_sheet(name)
        except Exception:
            logger.exception("Gagal archive sheet '%s'", name)
            result[name] = -1
    return result
