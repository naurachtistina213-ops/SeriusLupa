"""
Gatekeeper buat PM: user yang belum terdaftar di sheet 'anggota' ATAU
'admin_whitelist' (termasuk superadmin dari env SUPERADMIN_IDS) nggak
bisa interaksi apapun di PM - langsung dibales pesan penolakan, dan
update-nya di-stop (raise ApplicationHandlerStop) biar handler lain
(start_menu, flow lapor/keluhan, dst) nggak ikut kejalan buat update yang
sama.

Setiap percobaan akses yang ditolak dicatat ke sheet 'logs', dan semua
superadmin di-PM otomatis - dengan cooldown per user_id biar nggak spam
notif kalau orang yang sama coba berkali-kali dalam waktu singkat.

Ini didaftarin di group=-1 (paling awal) di main.py, buat 2 tipe update:
pesan biasa (termasuk command kayak /start) dan tombol inline (callback
query) - biar nggak ada jalur PM yang kelewat nggak ke-cek.
"""
import time

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from sheets.admin import get_admin_info, get_all_superadmin_ids
from sheets.logs import log_event
from sheets.users import find_member

PESAN_TOLAK = "User ID Anda belum ditambahkan. Silakan chat admin untuk info lebih lanjut."
_NOTIFY_COOLDOWN_SECONDS = 600  # 10 menit - biar nggak spam superadmin
_last_notified: dict[int, float] = {}


def _is_known(user_id: int, username: str | None) -> bool:
    """Dikenal kalau ada di admin_whitelist/superadmin ATAU ada di anggota."""
    if get_admin_info(user_id):
        return True
    if find_member(user_id, username):
        return True
    return False


async def _log_and_notify(context: ContextTypes.DEFAULT_TYPE, user_id: int,
                           username: str | None, nama: str | None):
    log_event(chat_id="", user_id=user_id, aksi="akses_ditolak", detail=f"@{username}" if username else "")

    now = time.time()
    last = _last_notified.get(user_id, 0)
    if now - last < _NOTIFY_COOLDOWN_SECONDS:
        return  # udah dinotif baru-baru ini, skip biar nggak spam
    _last_notified[user_id] = now

    identitas = f"@{username}" if username else str(user_id)
    pesan = (
        f"\u26A0\uFE0F User belum terdaftar coba akses bot:\n"
        f"Nama: {nama or '-'}\n"
        f"Username: {identitas}\n"
        f"User ID: {user_id}"
    )
    for admin_id in get_all_superadmin_ids():
        try:
            await context.bot.send_message(admin_id, pesan)
        except Exception:
            pass  # admin belum pernah /start bot, dilewatin aja


async def gatekeeper_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return  # gatekeeper cuma buat PM, grup nggak kena aturan ini

    user = update.effective_user
    if not _is_known(user.id, user.username):
        await update.effective_message.reply_text(PESAN_TOLAK)
        await _log_and_notify(context, user.id, user.username, user.first_name)
        raise ApplicationHandlerStop


async def gatekeeper_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    if not _is_known(user.id, user.username):
        await update.callback_query.answer(PESAN_TOLAK, show_alert=True)
        await _log_and_notify(context, user.id, user.username, user.first_name)
        raise ApplicationHandlerStop
