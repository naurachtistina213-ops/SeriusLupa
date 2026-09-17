"""
Entry point bot. Jalanin ini di Railway (Start Command: python main.py).
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import (Application, CallbackQueryHandler, ChatMemberHandler,
                           CommandHandler, ContextTypes, MessageHandler, filters)

from config import TELEGRAM_BOT_TOKEN, validate_config
from sheets.admin import is_superadmin
from sheets.anggota_detail import find_user_id_by_field, get_details
from sheets.chats_registry import reset_cache as reset_chats_registry_cache
from sheets.client import reset_worksheet_cache, to_int
from sheets.resources import register_resource_type
from sheets.users import find_member_by_id, find_member_by_username
from utils.tenure import describe_tenure, parse_date
from handlers.access_control import gatekeeper_callback, gatekeeper_message
from handlers.addcommand_pm import addcommand_pick_team_callback, handle_addcommand_text
from handlers.anggota_admin import (handle_addfield_text, pick_member_callback,
                                     start_addfield_flow)
from handlers.anggota_admin import pick_team_callback as anggota_pick_team_callback
from handlers.batalkan import batalkan_pick_callback
from handlers.group import (handle_bot_added_to_group,
                             handle_group_message_for_topic_detection)
from handlers.group_commands import (brand_command, handle_group_text,
                                      listcommand_command, reslink_pick_callback)
from handlers.keluhan import handle_keluhan_text, keluhan_confirm_callback
from handlers.lapor import (handle_lapor_text, lapor_category_callback,
                             lapor_confirm_callback, lapor_skip_callback)
from handlers.link_canonical_admin import (handle_add_text as handle_lcanon_add_text,
                                            list_links_callback, start_add_flow)
from handlers.link_pm import pick_brand_callback, pick_team_callback, pick_tipe_callback
from handlers.pm_menu import menu_callback_router, start_menu
from handlers.reminder_admin import (add_reminder_confirm_callback, edit_field_callback,
                                      edit_reminder_callback, handle_remind_add_text,
                                      handle_remind_edit_text, list_reminders_callback,
                                      start_add_reminder_flow, turn_off_confirm_callback,
                                      turn_off_list_callback)
from handlers.revoke import revoke_confirm_callback
from scheduler.archive_job import register_archive_job
from scheduler.reminder_loop import register_reminder_job
from sheets.archive import archive_all
from sheets.setup import ensure_all_sheets_exist

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def tambahtipe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Superadmin nambah tipe resource-lookup baru, misal:
    /tambahtipe sosmed Akun sosmed team
    Setelah ini, command /sosmed <team> langsung aktif di semua grup."""
    user = update.effective_user
    if not is_superadmin(user.id):
        await update.message.reply_text("Command ini cuma buat superadmin.")
        return

    args = (update.message.text or "").split(maxsplit=2)
    if len(args) < 2:
        await update.message.reply_text(
            "Format: /tambahtipe <nama_tipe> <keterangan opsional>\n"
            "Contoh: /tambahtipe sosmed Akun sosmed team"
        )
        return

    tipe = args[1]
    keterangan = args[2] if len(args) > 2 else ""

    result = register_resource_type(tipe, dibuat_oleh=user.id, keterangan=keterangan)
    if result == "created":
        await update.message.reply_text(f"\u2705 Command /{tipe.lower()} sekarang aktif di semua grup.")
    elif result == "exists":
        await update.message.reply_text(f"'/{tipe.lower()}' udah ada sebelumnya.")
    else:
        await update.message.reply_text(f"'/{tipe.lower()}' nggak bisa dipakai (nabrak nama bawaan).")


async def archive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trigger manual buat archive job (biar nggak perlu nunggu 24 jam
    pas mau tes). Khusus superadmin."""
    user = update.effective_user
    if not is_superadmin(user.id):
        await update.message.reply_text("Command ini cuma buat superadmin.")
        return

    result = archive_all()
    lines = ["\U0001F4E6 Hasil archive:"]
    for name, count in result.items():
        if count < 0:
            lines.append(f"- {name}: gagal")
        else:
            lines.append(f"- {name}: {count} baris dipindah")
    await update.message.reply_text("\n".join(lines))


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/id <username_telegram atau UID_kantor> - khusus superadmin, cari
    profil siapa aja (nggak cuma diri sendiri). Bisa dipanggil di PM
    maupun grup."""
    user = update.effective_user
    if not is_superadmin(user.id):
        await update.message.reply_text("Command ini cuma buat superadmin.")
        return

    parts = (update.message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Format: /id <username_telegram atau UID_kantor>")
        return

    query = parts[1].strip()

    member = find_member_by_username(query)
    if not member:
        found_id = find_user_id_by_field("uid_kantor", query)
        if found_id:
            member = find_member_by_id(found_id)

    if not member:
        await update.message.reply_text(f"Nggak ketemu orang dengan username/UID Kantor '{query}'.")
        return

    member_user_id = to_int(member.get("user_id"))
    details = get_details(member_user_id)
    uid_kantor = details.get("uid_kantor", "-")
    tanggal_join = details.get("tanggal_join", "-")

    masa_kerja = "-"
    if tanggal_join != "-":
        join_date = parse_date(tanggal_join)
        if join_date:
            masa_kerja = describe_tenure(join_date)

    username = member.get("username", "")
    lines = [
        f"\U0001F464 {member.get('nama', '?')}",
        f"Username: @{username.lstrip('@')}" if username else "Username: -",
        f"Uid Kantor: {uid_kantor}",
        f"Tanggal Join: {tanggal_join}",
        f"Masa Kerja: {masa_kerja}",
    ]
    await update.message.reply_text("\n".join(lines))


async def sync_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset cache in-memory (chats_registry, dkk). Custom_commands, teams,
    anggota, dll SELALU baca live dari sheet tiap kali, jadi nggak perlu
    di-sync - cuma yang eksplisit di-cache (chats_registry) yang perlu ini."""
    user = update.effective_user
    if not is_superadmin(user.id):
        await update.message.reply_text("Command ini cuma buat superadmin.")
        return

    reset_chats_registry_cache()
    reset_worksheet_cache()
    await update.message.reply_text(
        "\u2705 Cache berhasil di-reset. Data chat/topic baru bakal ke-load "
        "ulang dari sheet."
    )


async def route_pm_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router text biasa di PM (bukan command), tergantung flow yang lagi
    aktif di context.user_data. Kalau nggak ada flow aktif, diamkan aja."""
    if update.effective_chat.type != "private":
        return

    flow = context.user_data.get("flow")
    if flow == "lapor":
        await handle_lapor_text(update, context)
    elif flow == "keluhan":
        await handle_keluhan_text(update, context)
    elif flow == "remind_edit":
        await handle_remind_edit_text(update, context)
    elif flow == "remind_add":
        await handle_remind_add_text(update, context)
    elif flow == "addcmd":
        await handle_addcommand_text(update, context)
    elif flow == "anggota_addfield":
        await handle_addfield_text(update, context)
    elif flow == "lcanon_add":
        await handle_lcanon_add_text(update, context)
    # kalau flow lain (settings, dll) ditambah nanti, tinggal nambah elif di sini


async def on_startup(application: Application):
    logger.info("Mastiin semua sheet udah ada...")
    ensure_all_sheets_exist()

    scheduler = AsyncIOScheduler()
    register_reminder_job(scheduler, application.bot)
    register_archive_job(scheduler)
    scheduler.start()
    logger.info("Scheduler reminder jalan.")


def main():
    validate_config()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(on_startup).build()

    # Gatekeeper PM - HARUS di group=-1 biar keduluan dari semua handler
    # PM lain (start_menu, menu buttons, flow lapor/keluhan, dst). User
    # yang belum terdaftar langsung ke-block di sini, nggak nyampe ke
    # handler manapun.
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE, gatekeeper_message), group=-1)
    app.add_handler(CallbackQueryHandler(gatekeeper_callback), group=-1)

    # Menu utama PM
    app.add_handler(CommandHandler("start", start_menu))
    app.add_handler(CommandHandler("menu", start_menu))
    app.add_handler(CommandHandler("sync", sync_command))
    app.add_handler(CommandHandler("tambahtipe", tambahtipe_command))
    app.add_handler(CommandHandler("archive", archive_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CallbackQueryHandler(menu_callback_router, pattern="^menu_"))

    # Flow lapor tugas
    app.add_handler(CallbackQueryHandler(lapor_category_callback, pattern="^lapor_cat:"))
    app.add_handler(CallbackQueryHandler(lapor_confirm_callback, pattern="^lapor_confirm:"))
    app.add_handler(CallbackQueryHandler(lapor_skip_callback, pattern="^lapor_skip:"))

    # Flow keluhan
    app.add_handler(CallbackQueryHandler(keluhan_confirm_callback, pattern="^keluhan_confirm:"))

    # Flow batalkan laporan
    app.add_handler(CallbackQueryHandler(batalkan_pick_callback, pattern="^batalkan_pick:"))

    # Flow atur reminder (khusus superadmin)
    app.add_handler(CallbackQueryHandler(start_add_reminder_flow, pattern="^remind_add$"))
    app.add_handler(CallbackQueryHandler(add_reminder_confirm_callback, pattern="^remind_add_confirm:"))
    app.add_handler(CallbackQueryHandler(list_reminders_callback, pattern="^remind_list$"))
    app.add_handler(CallbackQueryHandler(turn_off_list_callback, pattern="^remind_off_list$"))
    app.add_handler(CallbackQueryHandler(edit_reminder_callback, pattern="^remind_edit:"))
    app.add_handler(CallbackQueryHandler(edit_field_callback, pattern="^remind_editfield:"))
    app.add_handler(CallbackQueryHandler(turn_off_confirm_callback, pattern="^remind_turnoff:"))

    # Flow revoke akses (khusus superadmin)
    app.add_handler(CallbackQueryHandler(revoke_confirm_callback, pattern="^revoke_pick:"))

    # Flow Lihat Link Team (PM)
    app.add_handler(CallbackQueryHandler(pick_team_callback, pattern="^linkpm_team:"))
    app.add_handler(CallbackQueryHandler(pick_tipe_callback, pattern="^linkpm_tipe:"))
    app.add_handler(CallbackQueryHandler(pick_brand_callback, pattern="^linkpm_brand:"))

    # Flow Tambah Command Baru (PM, khusus superadmin)
    app.add_handler(CallbackQueryHandler(addcommand_pick_team_callback, pattern="^addcmd_team:"))

    # Flow Anggota (PM, khusus superadmin)
    app.add_handler(CallbackQueryHandler(anggota_pick_team_callback, pattern="^anggota_team:"))
    app.add_handler(CallbackQueryHandler(pick_member_callback, pattern="^anggota_pick:"))
    app.add_handler(CallbackQueryHandler(start_addfield_flow, pattern="^anggota_addfield:"))

    # Flow Link Canonical (PM, khusus superadmin)
    app.add_handler(CallbackQueryHandler(list_links_callback, pattern="^lcanon_list$"))
    app.add_handler(CallbackQueryHandler(start_add_flow, pattern="^lcanon_add$"))

    # Resource lookup (/link, /sosmed, dst) - pilih brand via tombol
    app.add_handler(CallbackQueryHandler(reslink_pick_callback, pattern="^reslink_pick:"))

    # Text biasa di PM (input link, isi keluhan, dst)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, route_pm_text))

    # /brand <team> - didaftarin SEBELUM handle_group_text di bawah, biar
    # keduluan diproses buat command ini spesifik (dua-duanya di group 0,
    # yang pertama match yang jalan).
    app.add_handler(CommandHandler("brand", brand_command))
    app.add_handler(CommandHandler("listcommand", listcommand_command))

    # Custom command grup: registrasi ("@bot /cmd <pesan>") & eksekusi
    # ("/cmd" atau "/cmd team2"). Ini di group 0 (default), terpisah dari
    # handler deteksi topik yang ada di group 1 - dua-duanya tetap jalan.
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_group_text))

    # Auto-detect chat_id/topic_id baru. Handler ini dikasih group=1 (bukan
    # default 0) biar nanti kalau ada handler command grup lain (custom
    # command, dll) yang juga register di group 0, dua-duanya tetap
    # kejalan bareng - nggak ada yang keblokir satu sama lain.
    app.add_handler(ChatMemberHandler(handle_bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS, handle_group_message_for_topic_detection), group=1)

    logger.info("Bot mulai jalan (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
