"""
Flow 'Link Canonical' via PM - khusus superadmin. Repository link
penting lintas team (beda dari '/link' yang per-team).
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from sheets.admin import is_superadmin
from sheets.link_canonical import add_link, format_all_links
from utils.validators import is_valid_url


async def start_link_canonical_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    buttons = [
        [InlineKeyboardButton("\U0001F4CB Lihat Semua Link", callback_data="lcanon_list")],
        [InlineKeyboardButton("\u2795 Tambah Link", callback_data="lcanon_add")],
    ]
    await query.edit_message_text("Link Canonical - mau ngapain?", reply_markup=InlineKeyboardMarkup(buttons))


async def list_links_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    await query.edit_message_text(format_all_links()[:4000])


async def start_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    context.user_data.clear()
    context.user_data["flow"] = "lcanon_add"
    context.user_data["step"] = "await_team"
    await query.edit_message_text(
        "Link ini buat team mana? Ketik nama team, atau \"umum\" kalau nggak spesifik ke 1 team."
    )


async def handle_add_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dipanggil dari main.py generic text handler kalau
    user_data['flow'] == 'lcanon_add'."""
    step = context.user_data.get("step")
    text = update.message.text.strip()

    if step == "await_team":
        context.user_data["lcanon_team"] = "" if text.lower() == "umum" else text
        context.user_data["step"] = "await_kategori"
        await update.message.reply_text("Kategori link-nya apa? (bebas, contoh: SOP, Database, Drive)")
        return

    if step == "await_kategori":
        context.user_data["lcanon_kategori"] = text
        context.user_data["step"] = "await_link"
        await update.message.reply_text("Kirim link-nya:")
        return

    if step == "await_link":
        if not is_valid_url(text):
            await update.message.reply_text(
                "Ini kelihatannya bukan link valid. Kirim link yang dimulai http:// atau https://"
            )
            return
        context.user_data["lcanon_link"] = text
        context.user_data["step"] = "await_keterangan"
        await update.message.reply_text("Keterangan tambahan (opsional)? Kirim \"-\" kalau nggak ada.")
        return

    if step == "await_keterangan":
        keterangan = "" if text == "-" else text
        add_link(
            team_name=context.user_data.get("lcanon_team", ""),
            kategori=context.user_data.get("lcanon_kategori", ""),
            link=context.user_data.get("lcanon_link", ""),
            keterangan=keterangan,
            ditambahkan_oleh=update.effective_user.id,
        )
        context.user_data.clear()
        await update.message.reply_text("\u2705 Link berhasil ditambahin ke Link Canonical.")
        return
