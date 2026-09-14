"""
Custom command di grup - 2 mode:

1. REGISTRASI: "@namabot /namaperintah <pesan opsional>"
   - Kalau admin yang kirim, command ini didaftarin, di-scope KE CHAT INI
     AJA (jadi leader team otomatis ke-lock ke grup mereka sendiri;
     superadmin bebas daftarin di grup manapun yang dia mau).
   - Kalau nama command-nya sama persis kayak nama team yang ada
     (misal "/team2"), otomatis jadi shortcut: command itu SELALU mention
     team2, dari chat manapun dia didaftarin/dipanggil (bukan cuma team
     yang punya chat ini).
   - Kalau bukan nama team, command itu default mention team yang PUNYA
     chat ini (dihitung ulang tiap dipanggil, dinamis).

2. EKSEKUSI: "/namaperintah" atau "/namaperintah team2" (argumen tim
   override target, dipakai buat command generik kayak "/bank team2").
   - Cuma bisa dieksekusi di chat_id yang sama tempat dia didaftarin.
   - Cuma admin (leader tim target, atau superadmin) yang bisa jalanin -
   siapa aja yang chat cuma command biasa nggak akan ke-trigger apa-apa.
"""
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from sheets.admin import can_manage_team, is_superadmin
from sheets.client import to_int
from sheets.custom_commands import find_command, list_commands_for_chat, save_or_update_command
from sheets.resources import (format_categorized_reply, get_active_types, get_brands_for_team,
                               get_brands_for_team_tipe, get_categorized_data,
                               is_resource_command)
from sheets.teams import get_all_teams, get_canonical_name, get_chat_for_team, get_team_by_chat
from sheets.users import get_all_members, get_team_members
from utils.mention import build_mentions_for_members

RESERVED_COMMANDS = {"start", "menu", "help", "getid", "listcommand", "lapor", "keluhan", "sync", "tambahtipe", "brand", "archive"}
ALL_KEYWORDS = {"all", "semua"}
MAIN_KEYWORD = "main"

_REGISTER_RE = re.compile(r"^/(\w+)\s*(.*)$", re.DOTALL)


async def handle_group_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    text = (message.text or "").strip()
    if not text.startswith("/") and f"@{context.bot.username}" not in text:
        return

    bot_mention = f"@{context.bot.username}"
    is_registration = bot_mention in text

    if is_registration:
        await _handle_registration(update, context, text.replace(bot_mention, "").strip())
        return

    parts = text.split()
    command_name = parts[0].lstrip("/").lower()

    if is_resource_command(command_name):
        await _handle_resource_lookup(update, context, command_name, parts[1:])
        return

    await _handle_execution(update, context, text)


async def _handle_resource_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   tipe: str, args: list[str]):
    """Handler buat command lookup generik: /link, /sosmed, dst + argumen
    nama team (+ opsional nama brand). Ini beda dari custom command biasa
    - nggak nge-mention siapapun, cuma nampilin data terkategori dari
    sheet 'data_resource', dan BUKAN di-lock ke 1 chat_id."""
    message = update.effective_message
    user = update.effective_user

    if not args:
        await message.reply_text(f"Format: /{tipe} <nama_team>, contoh: /{tipe} team1")
        return

    target_team = get_canonical_name(args[0])
    if not target_team:
        await message.reply_text(f"Team '{args[0]}' nggak ketemu.")
        return

    if not (is_superadmin(user.id) or can_manage_team(user.id, target_team)):
        await message.reply_text("Kamu nggak punya akses buat lihat data ini.")
        return

    # Brand disebut langsung sebagai argumen kedua -> skip menu, langsung tampil
    if len(args) >= 2:
        brand = args[1]
        data = get_categorized_data(target_team, tipe, brand=brand)
        await message.reply_text(
            format_categorized_reply(tipe, target_team, data, brand=brand),
        )
        return

    # Nggak ada argumen brand -> cek dulu team/tipe ini pakai sistem brand apa nggak
    brands = get_brands_for_team_tipe(target_team, tipe)
    if not brands:
        # Belum pakai brand sama sekali - tampilin semua kayak biasa (backward compatible)
        data = get_categorized_data(target_team, tipe, brand=None)
        await message.reply_text(
            format_categorized_reply(tipe, target_team, data),
        )
        return

    if len(brands) == 1:
        # Cuma 1 brand -> langsung tampil, nggak perlu nyuruh klik tombol
        # yang isinya cuma 1 pilihan doang.
        data = get_categorized_data(target_team, tipe, brand=brands[0])
        await message.reply_text(
            format_categorized_reply(tipe, target_team, data, brand=brands[0]),
        )
        return

    buttons = [
        [InlineKeyboardButton(b, callback_data=f"reslink_pick:{tipe}:{target_team}:{b}")]
        for b in brands
    ]
    await message.reply_text(
        f"Pilih brand buat /{tipe} {target_team}:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def reslink_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dipencet pas user milih 1 brand dari tombol yang muncul di
    _handle_resource_lookup. Akses dicek ulang di sini (bukan cuma
    ngandelin pengecekan pas nampilin tombol)."""
    query = update.callback_query
    await query.answer()
    _, tipe, team, brand = query.data.split(":", 3)
    user = update.effective_user

    if not (is_superadmin(user.id) or can_manage_team(user.id, team)):
        await query.edit_message_text("Kamu nggak punya akses buat lihat data ini.")
        return

    data = get_categorized_data(team, tipe, brand=brand)
    await query.edit_message_text(
        format_categorized_reply(tipe, team, data, brand=brand),
    )


async def listcommand_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/listcommand - daftar custom command yang aktif di CHAT INI (bukan
    scoped per-role kayak /help, tapi murni "command apa aja yang bisa
    dipanggil di grup ini"). Kebuka buat siapa aja, nggak dibatasin
    admin - cuma nge-list nama, nggak nunjukin data sensitif apapun."""
    message = update.effective_message
    chat = update.effective_chat

    custom_cmds = list_commands_for_chat(chat.id)
    lines = ["\U0001F4CB Command yang aktif di chat ini:\n"]
    if custom_cmds:
        lines.append("Custom command:")
        for c in custom_cmds:
            target = c.get("target_team") or "(dinamis - ikut team chat ini)"
            pesan = c.get("pesan") or ""
            lines.append(f"/{c.get('command')} - {pesan} [target: {target}]")
    else:
        lines.append("Custom command: (belum ada)")

    resource_types = get_active_types()
    if resource_types:
        lines.append("\nResource lookup (format: /<tipe> <nama_team>):")
        lines.extend(f"/{t}" for t in resource_types)

    await message.reply_text("\n".join(lines))


async def brand_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/brand <team> - list nama brand yang ada buat 1 team, lintas
    semua tipe (link/sosmed/dll), biar gampang tau apa aja yang bisa
    dipanggil tanpa buka spreadsheet."""
    message = update.effective_message
    user = update.effective_user
    args = (message.text or "").split()

    if len(args) < 2:
        await message.reply_text("Format: /brand <nama_team>, contoh: /brand team1")
        return

    target_team = get_canonical_name(args[1])
    if not target_team:
        await message.reply_text(f"Team '{args[1]}' nggak ketemu.")
        return

    if not (is_superadmin(user.id) or can_manage_team(user.id, target_team)):
        await message.reply_text("Kamu nggak punya akses buat lihat data ini.")
        return

    brands = get_brands_for_team(target_team)
    if not brands:
        await message.reply_text(f"Belum ada brand yang kedaftar buat team {target_team}.")
        return

    teks = f"\U0001F3F7\uFE0F Daftar brand - {target_team}\n\n" + "\n".join(
        f"{i}. {b}" for i, b in enumerate(brands, start=1)
    )
    await message.reply_text(teks)


async def _handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    match = _REGISTER_RE.match(text)
    if not match:
        return  # bukan format "/command <pesan>", diamkan

    command_name = match.group(1).lower()
    pesan = match.group(2).strip()

    if command_name in RESERVED_COMMANDS:
        await message.reply_text(
            f"'/{command_name}' udah dipakai sebagai command bawaan bot, "
            "pilih nama lain ya."
        )
        return

    if is_resource_command(command_name):
        await message.reply_text(
            f"'/{command_name}' udah dipakai sebagai command resource-lookup "
            "(kayak /link), pilih nama lain ya."
        )
        return

    team_row = get_team_by_chat(chat.id, message.message_thread_id)
    if not team_row:
        await message.reply_text(
            "Chat/topik ini belum terdaftar sebagai team manapun di sheet "
            "'teams'. Isi dulu chat_id + topic_id-nya (cek /getid), baru "
            "daftarin command."
        )
        return

    own_team = team_row["team_name"]
    if not (is_superadmin(user.id) or can_manage_team(user.id, own_team)):
        await message.reply_text("Kamu nggak punya akses buat daftar command di sini.")
        return

    # Kalau nama command = nama team yang valid -> jadi shortcut permanen ke team itu
    # (pakai nama tim ASLI dari sheet, misal "Team1", bukan "team1" mentah dari user)
    target_team = get_canonical_name(command_name) or ""

    result = save_or_update_command(
        command=command_name, pesan=pesan, target_team=target_team,
        dibuat_oleh=user.id, chat_id=chat.id,
    )

    verb = "berhasil didaftarin" if result == "created" else "berhasil di-update"
    await message.reply_text(f"\u2705 Command /{command_name} {verb}.")


async def _handle_execution(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    parts = text.split()
    command_name = parts[0].lstrip("/").lower()
    arg_team = parts[1].lower() if len(parts) > 1 else None

    row = find_command(command_name, chat.id)
    if not row:
        return  # bukan custom command yang terdaftar di chat ini, diamkan

    # Argumen "all"/"semua" -> broadcast pesan ini ke SETIAP grup team
    # (yang udah kedaftar di sheet 'teams'), masing-masing nge-mention
    # anggota team-nya SENDIRI di grup mereka sendiri. Ini penting -
    # mention cuma bisa notify kalau orangnya emang anggota grup itu,
    # jadi nggak bisa asal gabungin mention semua orang jadi 1 pesan di
    # 1 grup doang. Dikunci khusus superadmin karena ini nge-hit banyak
    # grup sekaligus.
    if arg_team and arg_team.lower() in ALL_KEYWORDS:
        if not is_superadmin(user.id):
            await message.reply_text("Cuma superadmin yang bisa broadcast ke semua team sekaligus.")
            return

        pesan = row.get("pesan") or "\U0001F4E2 Pengumuman!"
        team_rows = get_all_teams()
        if not team_rows:
            await message.reply_text("Belum ada team yang kedaftar di sheet 'teams'.")
            return

        terkirim, gagal = 0, 0
        for t in team_rows:
            t_chat_id = to_int(t.get("chat_id"))
            if t_chat_id is None:
                continue
            t_topic_id = to_int(t.get("topic_id"))
            members = get_team_members(t.get("team_name", ""))
            mentions = await build_mentions_for_members(context.bot, t_chat_id, members) if members else ""
            teks = f"{pesan}\n\n{mentions}" if mentions else pesan
            try:
                await context.bot.send_message(
                    chat_id=t_chat_id, message_thread_id=t_topic_id,
                    text=teks, parse_mode="Markdown",
                )
                terkirim += 1
            except Exception:
                gagal += 1

        await message.reply_text(f"\u2705 Broadcast terkirim ke {terkirim} grup team" + (f", {gagal} gagal." if gagal else "."))
        return

    # Urutan resolusi target: argumen eksplisit > target_team hasil registrasi > team pemilik chat ini
    if arg_team and arg_team.lower() == MAIN_KEYWORD:
        target_team = MAIN_KEYWORD
    else:
        canonical_arg_team = get_canonical_name(arg_team) if arg_team else None
        if canonical_arg_team:
            target_team = canonical_arg_team
        elif row.get("target_team"):
            target_team = row["target_team"]
        else:
            team_row = get_team_by_chat(chat.id, message.message_thread_id)
            target_team = team_row["team_name"] if team_row else None

    if not target_team:
        await message.reply_text("Nggak bisa nentuin team target buat command ini.")
        return

    is_main = target_team.lower() == MAIN_KEYWORD

    # "main" itu bukan team beranggota sungguhan (1 orang cuma 1 team asli)
    # - diartikan sebagai gabungan semua team, jadi dikunci khusus
    # superadmin sama kayak "all"/"semua".
    if is_main:
        if not is_superadmin(user.id):
            await message.reply_text("Cuma superadmin yang bisa jalanin command target 'main'.")
            return
        members = get_all_members()
    else:
        if not (is_superadmin(user.id) or can_manage_team(user.id, target_team)):
            await message.reply_text("Cuma admin yang bisa jalanin command ini.")
            return
        members = get_team_members(target_team)

    if not members:
        await message.reply_text(f"Belum ada anggota terdaftar buat team {target_team}.")
        return

    mentions = await build_mentions_for_members(context.bot, chat.id, members)
    label = "semua team" if is_main else f"Team {target_team}"
    pesan = row.get("pesan") or f"\U0001F4E2 {label} dipanggil!"
    teks = f"{pesan}\n\n{mentions}"

    # Selalu kirim di chat tempat command diketik (perilaku dasar)
    await context.bot.send_message(
        chat_id=chat.id,
        message_thread_id=message.message_thread_id,
        text=teks,
        parse_mode="Markdown",
    )

    # Kalau target-nya BUKAN team pemilik chat ini (misal command diketik
    # di grup main tapi target-nya team2), kirim JUGA ke grup ASLI team
    # target (dari sheet 'teams') - jadi kedua tempat sama-sama kebagian
    # pesan + mention team2, bukan cuma salah satu.
    team_chat = get_chat_for_team(target_team)
    if team_chat and team_chat[0] != chat.id:
        dest_chat_id, dest_topic_id = team_chat
        try:
            await context.bot.send_message(
                chat_id=dest_chat_id,
                message_thread_id=dest_topic_id,
                text=teks,
                parse_mode="Markdown",
            )
        except Exception:
            await message.reply_text(
                f"\u26A0\uFE0F Terkirim di sini, tapi gagal kirim ke grup {target_team}."
            )
