"""
Load semua konfigurasi dari environment variable.
Di Railway, isi variable ini lewat tab "Variables" di project settings.
Untuk development lokal, copy .env.example jadi .env lalu isi.
"""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
GOOGLE_CREDENTIALS_BASE64 = os.getenv("GOOGLE_CREDENTIALS_BASE64", "")
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Asia/Jakarta")

# Superadmin di-set lewat env, dipisah koma -> jadi set of int
SUPERADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("SUPERADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}


def validate_config():
    """Cek variable wajib udah keisi semua, biar error-nya jelas dari awal
    (bukan error samar-samar pas bot udah jalan)."""
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not SPREADSHEET_ID:
        missing.append("SPREADSHEET_ID")
    if not GOOGLE_CREDENTIALS_BASE64:
        missing.append("GOOGLE_CREDENTIALS_BASE64")
    if missing:
        raise RuntimeError(
            f"Environment variable belum diisi: {', '.join(missing)}. "
            "Cek .env.example buat referensi."
        )
