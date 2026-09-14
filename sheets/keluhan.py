"""Baca/tulis sheet 'keluhan'. Akses lihat/kelola dibatasin superadmin
(dicek di handler, bukan di sini)."""
from sheets.client import get_or_create_worksheet
from sheets.setup import SHEET_SCHEMAS
from utils.timezone import now_str


def _ws():
    return get_or_create_worksheet("keluhan", SHEET_SCHEMAS["keluhan"])


def save_keluhan(team_name: str, user_id: int, nama: str, isi: str):
    ws = _ws()
    ws.append_row([
        now_str(),
        team_name,
        user_id,
        nama,
        isi,
        "belum ditindak",
    ])


def get_open_keluhan() -> list[dict]:
    ws = _ws()
    return [row for row in ws.get_all_records() if row.get("status") == "belum ditindak"]
