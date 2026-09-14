"""
Flow 'Lihat Link Team' via PM - reuse sistem resource-lookup yang sama
kayak /link di grup, tapi full lewat tombol. Leader nggak perlu ketik
command/nama team sendiri (langsung ke team dia); superadmin pilih team
dulu."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from sheets.admin import get_admin_info
from sheets.resources import (format_categorized_reply, get_active_types,
                               get_brands_for_team_tipe, get_categorized_data)
from sheets.users import list_team_names


async def start_link_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_info = get_admin_info(update.effective_user.id)
    if not admin_info:
        await query.edit_message_text("Menu ini cuma buat admin/leader.")
        return

    if admin_info.get("managed_team") == "all":
        teams = list_team_names()
        if not teams:
            await query.edit_message_text("Belum ada team yang kedaftar di sheet 'anggota'.")
            return
        buttons = [[InlineKeyboardButton(t, callback_data=f"linkpm_team:{t}")] for t in teams]
        await query.edit_message_text("Pilih team:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    await _show_tipe_menu(query, admin_info.get("managed_team", ""))


async def pick_team_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    team = query.data.split(":", 1)[1]
    await _show_tipe_menu(query, team)


async def _show_tipe_menu(query, team: str):
    types = get_active_types()
    if not types:
        await query.edit_message_text("Belum ada tipe resource-lookup yang aktif.")
        return
    buttons = [[InlineKeyboardButton(t, callback_data=f"linkpm_tipe:{team}:{t}")] for t in types]
    await query.edit_message_text(
        f"Team: {team}\nPilih data yang mau dilihat:", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def pick_tipe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, team, tipe = query.data.split(":", 2)

    brands = get_brands_for_team_tipe(team, tipe)
    if not brands:
        data = get_categorized_data(team, tipe, brand=None)
        await query.edit_message_text(format_categorized_reply(tipe, team, data))
        return

    if len(brands) == 1:
        data = get_categorized_data(team, tipe, brand=brands[0])
        await query.edit_message_text(format_categorized_reply(tipe, team, data, brand=brands[0]))
        return

    buttons = [
        [InlineKeyboardButton(b, callback_data=f"linkpm_brand:{team}:{tipe}:{b}")] for b in brands
    ]
    await query.edit_message_text(
        f"Pilih brand buat {tipe} - {team}:", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def pick_brand_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, team, tipe, brand = query.data.split(":", 3)
    data = get_categorized_data(team, tipe, brand=brand)
    await query.edit_message_text(format_categorized_reply(tipe, team, data, brand=brand))
