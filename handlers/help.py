"""
Flow 'Help' via PM - scoped per role:
- Leader/admin team biasa: cuma liat command yang relevan buat team dia
- Superadmin: liat semua team dikelompokkin, + command khusus admin
"""
from telegram import Update
from telegram.ext import ContextTypes

from sheets.admin import get_admin_info
from sheets.custom_commands import get_all_commands
from sheets.resources import get_active_types
from sheets.teams import get_chat_for_team
from sheets.users import list_team_names


def _commands_for_team(team_name: str) -> list[str]:
    """Custom command yang relevan buat 1 team: yang target_team-nya
    eksplisit team ini, ATAU yang didaftarin di grup team ini sendiri
    (target_team kosong = dinamis ngikutin chat)."""
    team_chat = get_chat_for_team(team_name)
    team_chat_id = team_chat[0] if team_chat else None

    lines = []
    for c in get_all_commands():
        target = (c.get("target_team") or "").lower()
        chat_match = team_chat_id is not None and str(c.get("chat_id")) == str(team_chat_id)
        if target == team_name.lower() or (not target and chat_match):
            keterangan = c.get("pesan") or "(mention team)"
            lines.append(f"/{c.get('command')} - {keterangan}")
    return lines


def _resource_lines(team_name: str) -> list[str]:
    return [f"/{t} {team_name}" for t in get_active_types()]


def build_team_section(team_name: str) -> str:
    custom = _commands_for_team(team_name)
    resource = _resource_lines(team_name)

    lines = [f"\U0001F4D6 {team_name}"]
    if custom:
        lines.append("Custom command:")
        lines.extend(f"  {c}" for c in custom)
    if resource:
        lines.append("Resource lookup:")
        lines.extend(f"  {r}" for r in resource)
    if not custom and not resource:
        lines.append("  (belum ada command khusus)")
    return "\n".join(lines)


async def start_help_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    admin_info = get_admin_info(user.id)

    if not admin_info:
        await query.edit_message_text("Menu ini cuma buat admin/leader.")
        return

    if admin_info.get("managed_team") == "all":
        team_names = list_team_names()
        sections = [build_team_section(t) for t in team_names] if team_names else ["(belum ada team kedaftar)"]
        admin_bagian = (
            "\n\n\U0001F511 Command khusus superadmin:\n"
            "/sync - reset cache\n"
            "/tambahtipe <tipe> <keterangan> - nambah tipe resource-lookup baru\n"
            "/brand <team> - lihat daftar brand 1 team\n"
            "Menu PM: Reminder, Lihat Keluhan, Tambah Command Baru, Revoke Akses"
        )
        teks = "\n\n".join(sections) + admin_bagian
    else:
        teks = build_team_section(admin_info.get("managed_team", ""))

    # Jaga-jaga batas panjang pesan Telegram (4096 karakter)
    await query.edit_message_text(teks[:4000])
