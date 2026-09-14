"""
Flow 'Revoke Akses' - khusus superadmin. List semua admin/leader yang
lagi whitelisted, pilih 1, dicabut aksesnya (is_whitelisted -> FALSE,
bukan dihapus barisnya, biar riwayatnya tetap ada).

CATATAN: superadmin yang didefinisikan lewat SUPERADMIN_IDS di
environment variable nggak muncul di daftar ini dan nggak bisa di-revoke
lewat menu ini - itu emang harus diubah manual di Railway.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from sheets.admin import is_superadmin, list_whitelisted, revoke_access


async def start_revoke_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    admins = list_whitelisted()
    if not admins:
        await query.edit_message_text("Nggak ada admin yang kedaftar di sheet admin_whitelist.")
        return

    buttons = [
        [InlineKeyboardButton(
            f"{a.get('nama', '?')} ({a.get('managed_team', '?')})",
            callback_data=f"revoke_pick:{a['_row_index']}",
        )]
        for a in admins
    ]
    await query.edit_message_text(
        "Pilih admin yang mau dicabut aksesnya:\n\n"
        "(Superadmin dari environment variable nggak muncul di sini, "
        "itu diubah manual di Railway)",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def revoke_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    row_index = int(query.data.split(":")[1])
    revoke_access(row_index)
    await query.edit_message_text("\u2705 Akses berhasil dicabut.")
