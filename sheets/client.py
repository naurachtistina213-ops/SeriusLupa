"""
Wrapper koneksi ke Google Sheets.
Semua modul lain di folder sheets/ pakai fungsi get_spreadsheet() dari sini,
biar cuma ada 1 titik koneksi (gampang di-maintain/di-debug).
"""
import base64
import json
import logging

import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS_BASE64, SPREADSHEET_ID

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

_spreadsheet = None  # cache, biar nggak auth ulang tiap panggil
_worksheet_cache: dict[str, "gspread.Worksheet"] = {}
_header_checked: set[str] = set()


def get_spreadsheet():
    """Return objek spreadsheet utama (cached)."""
    global _spreadsheet
    if _spreadsheet is not None:
        return _spreadsheet

    # Bersihin whitespace/newline yang kadang nyelip pas copy-paste ke
    # environment variable (penyebab paling umum error base64 "1 lebih
    # dari kelipatan 4").
    raw = "".join(GOOGLE_CREDENTIALS_BASE64.split())

    try:
        creds_json = base64.b64decode(raw, validate=True).decode("utf-8")
    except (base64.binascii.Error, UnicodeDecodeError) as e:
        raise RuntimeError(
            "GOOGLE_CREDENTIALS_BASE64 nggak valid/rusak (kemungkinan "
            "terpotong pas copy-paste). Generate ulang pakai "
            "`base64 -w0 credentials.json`, copy full output-nya, dan "
            "pastikan nggak ada spasi/enter nyelip di variable Railway."
        ) from e

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=_SCOPES)

    client = gspread.authorize(creds)
    _spreadsheet = client.open_by_key(SPREADSHEET_ID)
    logger.info("Terkoneksi ke spreadsheet: %s", _spreadsheet.title)
    return _spreadsheet


def to_int(value) -> int | None:
    """Konversi nilai dari sheet ke int dengan aman, buat perbandingan
    chat_id/topic_id. Google Sheets kadang nyimpen angka gede (kayak
    chat_id grup yang negatif belasan digit) sebagai float atau notasi
    scientific - kalau dibandingin pakai str() polos, hasilnya nggak match
    (contoh: "-1004345835973" vs "-1004345835973.0"). Fungsi ini
    menyamakan dua-duanya jadi int biasa sebelum dibandingkan."""
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def reset_worksheet_cache():
    """Kosongin cache worksheet + header-check. Dipanggil dari /sync -
    berguna kalau ada tab yang dihapus/dibuat ulang manual pas bot lagi
    jalan, tanpa perlu redeploy/restart."""
    _worksheet_cache.clear()
    _header_checked.clear()


def get_or_create_worksheet(title: str, headers: list[str]):
    """Ambil worksheet by nama tab. Kalau belum ada, bikin baru + isi header.
    Ini yang bikin 'sheets auto-generate' pas bot pertama kali jalan.

    Di-cache per judul tab (_worksheet_cache) - tanpa ini, SETIAP fungsi di
    manapun yang butuh akses ke 1 sheet bakal manggil ulang metadata
    spreadsheet dari awal tiap kali, dan dengan banyak fitur jalan
    bersamaan (scheduler tiap menit + command dari banyak user) itu bisa
    gampang kena rate limit Google Sheets API. Cache ini bikin fetch
    metadata + cek header cuma kejadian SEKALI per proses per tab.

    Kalau tab-nya UDAH ada tapi header di sheet nggak cocok sama schema
    yang diharapkan (misal karena schema kode berubah setelah sheet
    dibuat) - bot NGGAK auto-fix (bisa berbahaya kalau ada kolom manual
    yang user tambahin), tapi kasih warning jelas di log (sekali aja per
    proses), biar ketauan dari awal daripada data diam-diam geser kolom."""
    if title in _worksheet_cache:
        return _worksheet_cache[title]

    ss = get_spreadsheet()
    try:
        ws = ss.worksheet(title)
        if title not in _header_checked:
            actual_headers = ws.row_values(1)
            if actual_headers and actual_headers != headers:
                logger.warning(
                    "Header tab '%s' nggak cocok sama schema kode!\n"
                    "  Di sheet : %s\n"
                    "  Di kode  : %s\n"
                    "Ini bisa bikin data ketulis di kolom yang salah. Perbaiki "
                    "header row-nya manual di spreadsheet, atau hapus tab ini "
                    "biar bot bikin ulang dari nol.",
                    title, actual_headers, headers,
                )
            _header_checked.add(title)
    except gspread.exceptions.WorksheetNotFound:
        logger.info("Tab '%s' belum ada, membuat baru...", title)
        ws = ss.add_worksheet(title=title, rows=1000, cols=max(len(headers), 10))
        ws.append_row(headers)
        _header_checked.add(title)

    _worksheet_cache[title] = ws
    return ws
