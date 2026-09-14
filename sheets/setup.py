"""
Definisi header tiap tab, dan fungsi buat mastiin semua tab udah ada
pas bot pertama kali jalan (dipanggil sekali di main.py saat startup).

Nambah kolom baru ke tab yang udah ada? Tetap perlu nambah manual di
spreadsheet (biar data lama nggak keganggu) - fungsi ini cuma nge-handle
tab yang belum exist sama sekali.
"""
from sheets.client import get_or_create_worksheet

SHEET_SCHEMAS = {
    "reminders": [
        "id", "pesan", "waktu", "recurrence", "target", "status",
    ],
    "shifts": [
        "user_id", "nama_shift", "jam_mulai", "jam_selesai",
    ],
    "teams": [
        "team_name", "chat_id", "topic_id", "timezone",
    ],
    "anggota": [
        "team_name", "user_id", "username", "nama",
    ],
    "anggota_detail": [
        "user_id", "field_name", "field_value",
    ],
    "admin_whitelist": [
        "user_id", "nama", "is_whitelisted", "managed_team",
    ],
    "custom_commands": [
        "command", "pesan", "target_team", "mention_all", "dibuat_oleh", "chat_id", "dibuat_pada",
    ],
    "resource_commands": [
        "tipe", "command", "dibuat_oleh", "keterangan",
    ],
    "data_resource": [
        "team_name", "tipe", "kategori", "isi", "brand",
    ],
    "task_reports": [
        "timestamp", "team_name", "user_id", "nama", "jenis_tugas",
        "link", "is_custom", "status_validasi",
    ],
    "email_reports": [
        "timestamp", "team_name", "user_id", "nama", "email", "password",
        "email_pemulihan", "no_hp_pemulihan", "kode_auth", "status", "shortlink",
    ],
    "keluhan": [
        "timestamp", "team_name", "user_id", "nama", "isi_keluhan", "status",
    ],
    "chats_registry": [
        "chat_id", "topic_id", "nama_grup", "nama_topik",
        "pertama_terdeteksi", "team_name",
    ],
    "logs": [
        "timestamp", "chat_id", "user_id", "aksi", "detail",
    ],
}


def ensure_all_sheets_exist():
    """Loop semua schema di atas, bikin tab yang belum ada."""
    for sheet_name, headers in SHEET_SCHEMAS.items():
        get_or_create_worksheet(sheet_name, headers)
