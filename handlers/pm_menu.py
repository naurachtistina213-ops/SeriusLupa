"""
Menu utama di PM (/start atau /menu). Nampilin tombol beda-beda
tergantung role orang yang chat: karyawan biasa, admin team, atau superadmin.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from sheets.admin import get_admin_info
from sheets.users import find_member


async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return  # menu ini cuma buat PM, biar nggak spam di grup

    user = update.effective_user
    admin_info = get_admin_info(user.id)
    member_info = find_member(user.id, user.username)

    nama = (admin_info or member_info or {}).get("nama", user.first_name)

    buttons = [
        [InlineKeyboardButton("\U0001F4DD Lapor Tugas", callback_data="menu_lapor")],
        [InlineKeyboardButton("\u274C Batalkan Laporan", callback_data="menu_batalkan")],
        [InlineKeyboardButton("\U0001F624 Ajukan Keluhan", callback_data="menu_keluhan")],
    ]

    if admin_info:
        buttons.append([InlineKeyboardButton("\U0001F517 Lihat Link Team", callback_data="menu_link")])
        buttons.append([InlineKeyboardButton("\u2753 Help", callback_data="menu_help")])

    if admin_info and admin_info.get("managed_team") == "all":
        buttons.append([InlineKeyboardButton("\U0001F4CB Lihat Keluhan", callback_data="menu_lihatkeluhan")])
        buttons.append([InlineKeyboardButton("\u2795 Tambah Command Baru", callback_data="menu_tambahcommand")])
        buttons.append([InlineKeyboardButton("\u23F0 Reminder", callback_data="menu_reminder")])
        buttons.append([InlineKeyboardButton("\U0001F6AB Revoke Akses", callback_data="menu_revoke")])
        buttons.append([InlineKeyboardButton("\U0001F465 Anggota", callback_data="menu_anggota")])

    greeting = f"Hi {nama}, ada yang bisa saya bantu?\n\nPilih menu di bawah ini:"
    await update.message.reply_text(greeting, reply_markup=InlineKeyboardMarkup(buttons))


async def menu_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router utama buat semua tombol menu. Detail tiap flow (lapor, keluhan,
    dst) ada di handler masing-masing - ini cuma titik masuknya."""
    query = update.callback_query
    await query.answer()

    # Import lokal biar nggak circular-import antar handler
    from handlers.addcommand_pm import start_addcommand_flow
    from handlers.anggota_admin import start_anggota_flow
    from handlers.batalkan import start_batalkan_flow
    from handlers.help import start_help_flow
    from handlers.keluhan import start_keluhan_flow
    from handlers.lapor import start_lapor_flow
    from handlers.link_pm import start_link_flow
    from handlers.reminder_admin import start_reminder_menu
    from handlers.revoke import start_revoke_flow

    routes = {
        "menu_lapor": start_lapor_flow,
        "menu_batalkan": start_batalkan_flow,
        "menu_keluhan": start_keluhan_flow,
        "menu_reminder": start_reminder_menu,
        "menu_help": start_help_flow,
        "menu_revoke": start_revoke_flow,
        "menu_link": start_link_flow,
        "menu_tambahcommand": start_addcommand_flow,
        "menu_anggota": start_anggota_flow,
        # menu_lihatkeluhan: TODO
    }

    handler = routes.get(query.data)
    if handler:
        await handler(update, context)
    else:
        await query.edit_message_text("Fitur ini masih dalam pengembangan.")
