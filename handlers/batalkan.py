"""
Flow 'Batalkan Laporan' - nampilin laporan terakhir milik user (link
ATAU email, kategori apapun) yang bisa dibatalin. Laporan nggak dihapus
dari sheet, cuma status-nya diubah jadi 'dibatalkan' (biar tetep ada
jejak audit).
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from sheets.email_reports import cancel_email_report, get_recent_email_reports_by_user
from sheets.task_reports import cancel_report, get_recent_reports_by_user

MAX_ITEMS = 5


async def start_batalkan_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    task_reports = get_recent_reports_by_user(user.id, limit=MAX_ITEMS)
    email_reports = get_recent_email_reports_by_user(user.id, limit=MAX_ITEMS)

    items = []
    for r in task_reports:
        label = f"{r.get('jenis_tugas', '?')} - {str(r.get('timestamp', ''))[:16]}"
        items.append((r.get("timestamp", ""), label, f"batalkan_pick:task:{r['_row_index']}"))
    for r in email_reports:
        label = f"Email ({r.get('email', '?')}) - {str(r.get('timestamp', ''))[:16]}"
        items.append((r.get("timestamp", ""), label, f"batalkan_pick:email:{r['_row_index']}"))

    items.sort(key=lambda x: x[0], reverse=True)
    items = items[:MAX_ITEMS]

    if not items:
        await update.callback_query.edit_message_text("Belum ada laporan tugas yang bisa dibatalin.")
        return

    buttons = [[InlineKeyboardButton(label, callback_data=cb)] for _, label, cb in items]
    await update.callback_query.edit_message_text(
        "Pilih laporan yang mau dibatalin (5 laporan terakhir kamu):",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def batalkan_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, source, row_index_str = query.data.split(":")
    row_index = int(row_index_str)
    user = update.effective_user

    if source == "task":
        ok = cancel_report(row_index, user.id)
    else:
        ok = cancel_email_report(row_index, user.id)

    if ok:
        await query.edit_message_text("\u2705 Laporan berhasil dibatalin.")
    else:
        await query.edit_message_text(
            "Gagal batalin - laporan ini kelihatannya bukan punya kamu, "
            "atau udah nggak ada."
        )
