"""
Flow 'Anggota' via PM - khusus superadmin. Pilih team -> pilih orang ->
lihat profil (nama, username, + semua field tambahan dari sheet
'anggota_detail', termasuk 'lama bekerja' yang dihitung otomatis dari
field 'tanggal_join' kalau ada). Ada tombol buat nambah/update field
baru, jadi ke depannya bisa nambah data apa aja tanpa ubah kode.
"""
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from sheets.admin import is_superadmin
from sheets.anggota_detail import get_details, set_detail
from sheets.users import get_team_members, list_team_names

_DATE_FORMATS = ["%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]


def _parse_date(value: str):
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _describe_tenure(join_date: datetime) -> str:
    days = (datetime.now() - join_date).days
    if days < 0:
        return "-"
    tahun, sisa_hari = divmod(days, 365)
    bulan = sisa_hari // 30
    parts = []
    if tahun:
        parts.append(f"{tahun} tahun")
    if bulan:
        parts.append(f"{bulan} bulan")
    return " ".join(parts) if parts else "< 1 bulan"


def _build_profile_text(member: dict, details: dict[str, str]) -> str:
    lines = [
        f"\U0001F464 {member.get('nama', '?')}",
        f"Username: @{member.get('username', '').lstrip('@')}" if member.get("username") else "Username: -",
        f"Team: {member.get('team_name', '-')}",
        f"User ID: {member.get('user_id', '-')}",
        "",
    ]
    if details:
        for field_name, field_value in details.items():
            if field_name.lower() == "tanggal_join":
                lines.append(f"Tanggal Join: {field_value}")
                join_date = _parse_date(field_value)
                if join_date:
                    lines.append(f"Lama Bekerja: {_describe_tenure(join_date)}")
            else:
                label = field_name.replace("_", " ").title()
                lines.append(f"{label}: {field_value}")
    else:
        lines.append("(belum ada data tambahan)")
    return "\n".join(lines)


async def start_anggota_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    teams = list_team_names()
    if not teams:
        await query.edit_message_text("Belum ada team yang kedaftar di sheet 'anggota'.")
        return

    buttons = [[InlineKeyboardButton(t, callback_data=f"anggota_team:{t}")] for t in teams]
    await query.edit_message_text("Pilih team:", reply_markup=InlineKeyboardMarkup(buttons))


async def pick_team_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    team = query.data.split(":", 1)[1]
    members = get_team_members(team)
    if not members:
        await query.edit_message_text(f"Belum ada anggota buat team {team}.")
        return

    buttons = [
        [InlineKeyboardButton(m.get("nama", str(m.get("user_id"))), callback_data=f"anggota_pick:{m['user_id']}")]
        for m in members
    ]
    await query.edit_message_text(f"Team: {team}\nPilih karyawan:", reply_markup=InlineKeyboardMarkup(buttons))


async def pick_member_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    user_id = int(query.data.split(":", 1)[1])
    member = _find_member_anywhere(user_id)
    if not member:
        await query.edit_message_text("Data karyawan ini nggak ketemu (mungkin baru dihapus).")
        return

    details = get_details(user_id)
    teks = _build_profile_text(member, details)
    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("\u2795 Tambah/Update Data", callback_data=f"anggota_addfield:{user_id}")
    ]])
    await query.edit_message_text(teks, reply_markup=buttons)


def _find_member_anywhere(user_id: int) -> dict | None:
    for team in list_team_names():
        for m in get_team_members(team):
            if int(m.get("user_id", 0)) == user_id:
                return m
    return None


async def start_addfield_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_superadmin(update.effective_user.id):
        await query.edit_message_text("Menu ini cuma buat superadmin.")
        return

    user_id = int(query.data.split(":", 1)[1])
    context.user_data.clear()
    context.user_data["flow"] = "anggota_addfield"
    context.user_data["anggota_user_id"] = user_id
    context.user_data["step"] = "await_field_name"
    await query.edit_message_text(
        "Nama field apa yang mau ditambah/diupdate? Contoh: uid_kantor, "
        "tanggal_lahir, tanggal_join, no_ktp, dst."
    )


async def handle_addfield_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dipanggil dari main.py generic text handler kalau
    user_data['flow'] == 'anggota_addfield'."""
    step = context.user_data.get("step")
    text = update.message.text.strip()

    if step == "await_field_name":
        context.user_data["anggota_field_name"] = text.lower().replace(" ", "_")
        context.user_data["step"] = "await_field_value"
        await update.message.reply_text(f"Isi buat '{text}':")
        return

    if step == "await_field_value":
        user_id = context.user_data.get("anggota_user_id")
        field_name = context.user_data.get("anggota_field_name")
        set_detail(user_id, field_name, text)
        context.user_data.clear()

        member = _find_member_anywhere(user_id)
        details = get_details(user_id)
        teks = "\u2705 Data berhasil disimpan.\n\n" + _build_profile_text(member, details)
        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("\u2795 Tambah/Update Data", callback_data=f"anggota_addfield:{user_id}")
        ]])
        await update.message.reply_text(teks, reply_markup=buttons)
        return
