"""
Baca/tulis sheet 'anggota_detail' - data tambahan fleksibel per
karyawan (UID kantor, tanggal lahir, tanggal join, dst). Format
key-value panjang (1 baris = 1 field per user_id), biar superadmin bisa
nambah field APA AJA ke depannya tanpa perlu ubah skema sheet.

Field 'tanggal_join' diperlakukan khusus di handler (dipakai buat
ngitung 'udah berapa lama bekerja') - selain itu semua field ditampilin
apa adanya.
"""
from sheets.client import get_or_create_worksheet, to_int
from sheets.setup import SHEET_SCHEMAS


def _ws():
    return get_or_create_worksheet("anggota_detail", SHEET_SCHEMAS["anggota_detail"])


def get_details(user_id: int) -> dict[str, str]:
    """Return {field_name: field_value} buat 1 user_id."""
    result = {}
    for row in _ws().get_all_records():
        if to_int(row.get("user_id")) == user_id:
            result[row.get("field_name", "")] = row.get("field_value", "")
    return result


def set_detail(user_id: int, field_name: str, field_value: str):
    """Upsert - update kalau field_name ini udah ada buat user_id ini,
    append baris baru kalau belum (biar nggak numpuk duplikat field yang
    sama tiap kali diupdate)."""
    ws = _ws()
    for i, row in enumerate(ws.get_all_records(), start=2):  # baris 1 = header
        if to_int(row.get("user_id")) == user_id and row.get("field_name", "").lower() == field_name.lower():
            ws.update_cell(i, 3, field_value)  # kolom ke-3 = field_value
            return
    ws.append_row([user_id, field_name, field_value])
