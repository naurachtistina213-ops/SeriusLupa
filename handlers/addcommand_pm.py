"""
Flow 'Tambah Command Baru' via PM - khusus superadmin, alternatif dari
'@bot /cmd <pesan>' yang biasanya diketik langsung di grup. Berguna
kalau superadmin mau daftarin command tanpa harus ke grup dulu.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from sheets.admin import is_superadmin
from sheets.client import to_int
from sheets.custom_commands import save_or_update_command
from sheets.resources import is_resource_command
from sheets.teams import get_all_teams, get_canonical_name

RESERVED_COMMANDS = {
    "start", "menu", "help", "getid", "listcommand", "lapor", "keluhan",
    "sync", "tambahtipe", "brand", "archive", "id",
}


async def start_addcommand_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    teams = [t for t in get_all_teams() if to_int(t.get("chat_id")) is not None]
    if not teams:
        await query.edit_message_text("Belum ada team yang punya chat_id kedaftar di sheet 'teams'.")
        return

    context.user_data.clear()
    buttons = [
        [InlineKeyboardButton(t["team_name"], callback_data=f"addcmd_team:{t['team_name']}")]
        for t in teams
    ]
    await query.edit_message_text("Command ini buat grup team mana?", reply_markup=InlineKeyboardMarkup(buttons))


async def addcommand_pick_team_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    team = query.data.split(":", 1)[1]
    context.user_data["flow"] = "addcmd"
    context.user_data["addcmd_team"] = team
    context.user_data["step"] = "await_name"
    await query.edit_message_text(f"Team: {team}\nKetik nama command-nya (tanpa slash), contoh: hp")


async def handle_addcommand_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dipanggil dari main.py generic text handler kalau user_data['flow'] == 'addcmd'."""
    step = context.user_data.get("step")
    text = update.message.text.strip()

    if step == "await_name":
        command_name = text.lower().lstrip("/")
        if command_name in RESERVED_COMMANDS:
            await update.message.reply_text(
                f"'/{command_name}' udah dipakai sebagai command bawaan bot, pilih nama lain ya."
            )
            return
        if is_resource_command(command_name):
            await update.message.reply_text(
                f"'/{command_name}' udah dipakai sebagai command resource-lookup, pilih nama lain ya."
            )
            return
        context.user_data["addcmd_name"] = command_name
        context.user_data["step"] = "await_pesan"
        await update.message.reply_text(
            "Kirim isi pesan buat command ini (kirim \"-\" kalau nggak ada pesan tetap):"
        )
        return

    if step == "await_pesan":
        pesan = "" if text == "-" else text
        team = context.user_data.get("addcmd_team")
        command_name = context.user_data.get("addcmd_name")

        team_row = next((t for t in get_all_teams() if t.get("team_name") == team), None)
        chat_id = to_int(team_row.get("chat_id")) if team_row else None

        if chat_id is None:
            await update.message.reply_text("Chat_id team ini nggak valid, dibatalkan.")
            context.user_data.clear()
            return

        target_team = get_canonical_name(command_name) or ""

        result = save_or_update_command(
            command=command_name, pesan=pesan, target_team=target_team,
            dibuat_oleh=update.effective_user.id, chat_id=chat_id,
        )
        context.user_data.clear()
        verb = "berhasil didaftarin" if result == "created" else "berhasil di-update"
        await update.message.reply_text(f"\u2705 Command /{command_name} {verb} buat grup {team}.")
        return
