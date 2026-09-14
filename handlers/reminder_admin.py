"""
Flow 'Atur Reminder' via PM - khusus superadmin. 2 sub-menu:
- Daftar Reminder: lihat semua reminder, pilih satu buat diedit (pesan,
  waktu, target, atau status)
- Matikan Reminder: nonaktifin salah satu reminder yang lagi aktif
"""
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from sheets.admin import is_superadmin
from sheets.reminders import (add_reminder, get_all_reminders_with_index,
                               set_reminder_status, update_reminder_field)
from sheets.teams import get_canonical_name
from utils.recurrence import RECURRENCE_HINT, describe, is_valid_recurrence, normalize_recurrence

_WAKTU_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

EDITABLE_FIELDS = [
    ("pesan", "Pesan"),
    ("waktu", "Waktu (format HH:MM)"),
    ("recurrence", "Jadwal (harian/nama hari)"),
    ("target", "Target (main/nama team)"),
    ("status", "Status (aktif/nonaktif)"),
]


def _short_label(r: dict) -> str:
    pesan = (r.get("pesan") or "")[:18]
    jadwal = describe(r.get("recurrence", "harian"))
    return f"{r.get('id')} - {jadwal} {r.get('waktu')} - {pesan}"


async def start_reminder_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_superadmin(user.id):
        await update.callback_query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    buttons = [
        [InlineKeyboardButton("\u2795 Tambah Reminder", callback_data="remind_add")],
        [InlineKeyboardButton("\U0001F4CB Daftar Reminder", callback_data="remind_list")],
        [InlineKeyboardButton("\U0001F534 Matikan Reminder", callback_data="remind_off_list")],
    ]
    await update.callback_query.edit_message_text(
        "Mau ngapain sama reminder?", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def start_add_reminder_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    context.user_data.clear()
    context.user_data["flow"] = "remind_add"
    context.user_data["step"] = "await_pesan"
    await query.edit_message_text("Kirim isi pesan reminder-nya:")


async def handle_remind_add_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dipanggil dari main.py generic text handler kalau user_data['flow'] == 'remind_add'."""
    step = context.user_data.get("step")
    text = update.message.text.strip()

    if step == "await_pesan":
        context.user_data["pesan"] = text
        context.user_data["step"] = "await_waktu"
        await update.message.reply_text("Jam berapa reminder ini dikirim? Format HH:MM, contoh 09:00")
        return

    if step == "await_waktu":
        if not _WAKTU_RE.match(text):
            await update.message.reply_text("Format waktu salah. Kirim dalam format HH:MM, contoh 09:00")
            return
        context.user_data["waktu"] = text
        context.user_data["step"] = "await_recurrence"
        await update.message.reply_text(
            f"Reminder ini harian atau mingguan? Ketik {RECURRENCE_HINT}."
        )
        return

    if step == "await_recurrence":
        if not is_valid_recurrence(text):
            await update.message.reply_text(f"Nggak dikenali. Ketik {RECURRENCE_HINT}.")
            return
        context.user_data["recurrence"] = normalize_recurrence(text)
        context.user_data["step"] = "await_target"
        await update.message.reply_text(
            "Reminder ini buat siapa? Ketik \"main\" (grup utama) atau nama team, "
            "boleh lebih dari 1 dipisah koma (contoh: main,team1,team2)"
        )
        return

    if step == "await_target":
        parts = [p.strip() for p in text.split(",") if p.strip()]
        resolved = []
        for p in parts:
            canonical = "main" if p.lower() == "main" else get_canonical_name(p)
            if not canonical:
                await update.message.reply_text(
                    f"Team '{p}' nggak ketemu. Ketik \"main\" atau nama team yang "
                    "valid, boleh lebih dari 1 dipisah koma (contoh: main,team1,team2)."
                )
                return
            resolved.append(canonical)

        target = ",".join(resolved)
        context.user_data["target"] = target
        context.user_data["step"] = "await_confirm_add"

        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("\u2705 Sudah benar", callback_data="remind_add_confirm:yes"),
            InlineKeyboardButton("\u270F\uFE0F Koreksi", callback_data="remind_add_confirm:no"),
        ]])
        await update.message.reply_text(
            "Konfirmasi dulu ya:\n\n"
            f"Pesan: {context.user_data['pesan']}\n"
            f"Waktu: {context.user_data['waktu']}\n"
            f"Jadwal: {describe(context.user_data.get('recurrence', 'harian'))}\n"
            f"Target: {target}\n\n"
            "Sudah benar?",
            reply_markup=buttons,
        )
        return


async def add_reminder_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    jawaban = query.data.split(":", 1)[1]
    if jawaban == "no":
        context.user_data["step"] = "await_pesan"
        await query.edit_message_text("Oke, ulangi dari awal. Kirim isi pesan reminder-nya:")
        return

    new_id = add_reminder(
        pesan=context.user_data.get("pesan", ""),
        waktu=context.user_data.get("waktu", ""),
        recurrence=context.user_data.get("recurrence", "harian"),
        target=context.user_data.get("target", "main"),
    )
    context.user_data.clear()
    await query.edit_message_text(f"\u2705 Reminder baru berhasil ditambahin (ID: {new_id}).")


async def list_reminders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    reminders = get_all_reminders_with_index()
    if not reminders:
        await query.edit_message_text("Belum ada reminder yang kedaftar.")
        return

    buttons = [
        [InlineKeyboardButton(_short_label(r), callback_data=f"remind_edit:{r['_row_index']}")]
        for r in reminders
    ]
    await query.edit_message_text("Pilih reminder yang mau diedit:", reply_markup=InlineKeyboardMarkup(buttons))


async def turn_off_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    reminders = [r for r in get_all_reminders_with_index() if r.get("status") == "aktif"]
    if not reminders:
        await query.edit_message_text("Nggak ada reminder yang lagi aktif.")
        return

    buttons = [
        [InlineKeyboardButton(_short_label(r), callback_data=f"remind_turnoff:{r['_row_index']}")]
        for r in reminders
    ]
    await query.edit_message_text(
        "Pilih reminder yang mau dimatikan:", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def turn_off_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    row_index = int(query.data.split(":")[1])
    set_reminder_status(row_index, "nonaktif")
    await query.edit_message_text("\u2705 Reminder berhasil dimatikan.")


async def edit_reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    row_index = int(query.data.split(":")[1])
    context.user_data["remind_row_index"] = row_index

    buttons = [
        [InlineKeyboardButton(label, callback_data=f"remind_editfield:{field}")]
        for field, label in EDITABLE_FIELDS
    ]
    await query.edit_message_text("Mau edit bagian mana?", reply_markup=InlineKeyboardMarkup(buttons))


async def edit_field_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    field = query.data.split(":")[1]
    context.user_data["flow"] = "remind_edit"
    context.user_data["remind_field"] = field
    label = dict(EDITABLE_FIELDS).get(field, field)
    await query.edit_message_text(f"Kirim nilai baru buat {label}:")


async def handle_remind_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dipanggil dari main.py generic text handler kalau user_data['flow'] == 'remind_edit'."""
    row_index = context.user_data.get("remind_row_index")
    field = context.user_data.get("remind_field")
    value = update.message.text.strip()

    if row_index is None or field is None:
        await update.message.reply_text("Sesi edit udah nggak valid, ulangi dari menu /menu.")
        context.user_data.clear()
        return

    update_reminder_field(row_index, field, value)
    context.user_data.clear()
    await update.message.reply_text("\u2705 Reminder berhasil diupdate.")
