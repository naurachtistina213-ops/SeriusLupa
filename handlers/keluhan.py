"""
Flow 'Ajukan Keluhan'. Isi keluhan tetap tercatat siapa yang lapor,
tapi akses lihat/kelola dibatasin superadmin aja (dicek di handler admin).
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import SUPERADMIN_IDS
from sheets.keluhan import save_keluhan
from sheets.users import find_member


async def start_keluhan_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["flow"] = "keluhan"
    context.user_data["step"] = "await_text"
    await update.callback_query.edit_message_text(
        "Tulis keluhan kamu di bawah ini. Keluhan ini cuma akan dilihat "
        "superadmin, bukan leader team kamu."
    )


async def handle_keluhan_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")
    text = update.message.text.strip()

    if step == "await_text":
        context.user_data["isi_keluhan"] = text
        context.user_data["step"] = "await_confirm"
        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("\u2705 Sudah benar", callback_data="keluhan_confirm:yes"),
            InlineKeyboardButton("\u270F\uFE0F Koreksi", callback_data="keluhan_confirm:no"),
        ]])
        await update.message.reply_text(
            f"Konfirmasi dulu ya, isi keluhan kamu:\n\n\"{text}\"\n\nSudah benar?",
            reply_markup=buttons,
        )
        return


async def keluhan_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    jawaban = query.data.split(":", 1)[1]

    if jawaban == "no":
        context.user_data["step"] = "await_text"
        await query.edit_message_text("Oke, tulis ulang keluhan kamu.")
        return

    user = update.effective_user
    member = find_member(user.id, user.username)
    team_name = member.get("team_name") if member else "unknown"
    nama = member.get("nama") if member else user.first_name

    save_keluhan(
        team_name=team_name,
        user_id=user.id,
        nama=nama,
        isi=context.user_data.get("isi_keluhan", ""),
    )

    # Notifikasi langsung ke semua superadmin (keluhan = urgent, bukan cuma dicatat)
    for admin_id in SUPERADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"\U0001F6A8 Keluhan baru dari {nama} ({team_name}):\n\n{context.user_data.get('isi_keluhan', '')}",
            )
        except Exception:
            pass  # kalau admin belum pernah start bot, kirim PM bisa gagal - ini oke, nggak fatal

    context.user_data.clear()
    await query.edit_message_text("\u2705 Keluhan kamu udah diterima dan diteruskan ke superadmin.")
