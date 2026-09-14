"""
Flow 'Lapor Tugas' - dari pencet tombol kategori sampe tersimpan di sheet.
State disimpan sementara di context.user_data (per-user, per-chat PM),
jadi nggak butuh database tambahan buat conversation state.

TODO produksi: state ini hilang kalau bot restart di tengah flow (lihat
catatan di percakapan soal 'konsistensi data pas bot restart') - untuk versi
awal ini diterima, tapi kalau mau lebih robust simpan state ke sheet juga.

Kategori "Email" punya sub-flow sendiri (bukan link) karena butuh beberapa
field terstruktur: email, password, dan 3 field opsional yang bisa di-skip.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from sheets.email_reports import save_email_report
from sheets.task_reports import get_all_links, save_report
from sheets.users import find_member
from utils.validators import (domain_matches_category, is_duplicate_link,
                               is_link_alive, is_valid_url)

# Kategori tugas. TODO: pindahin ke sheet 'data_resource' / 'resource_commands'
# biar superadmin bisa nambah kategori tanpa ubah kode (sesuai desain awal).
KATEGORI_TUGAS = ["Backlink", "Sosmed FB", "Sosmed IG", "TikTok", "Email", "Shortlink"]

# Contoh format link per kategori, ditampilin pas user pilih kategorinya
CONTOH_LINK = {
    "backlink": (
        "Link yang dimaksud adalah link halaman *tempat kamu menaruh backlink* "
        "(bukan cuma link ke halaman utama situs itu, dan bukan screenshot).\n\n"
        "Contoh yang benar:\n"
        "- https://forum-example.com/members/nama-kamu.123/ (halaman profil "
        "forum yang ada link balik-nya)\n"
        "- https://blog-example.com/artikel-x/#comment-456 (halaman komentar "
        "tempat backlink ditaruh)\n\n"
        "Kirim link-nya:"
    ),
    "sosmed fb": "Kirim link postingan Facebook-nya (bukan link ke profil/halaman umum):",
    "sosmed ig": "Kirim link postingan Instagram-nya (bukan link ke profil umum):",
    "tiktok": "Kirim link video TikTok-nya:",
}

# Urutan field opsional buat sub-flow Email, dan pertanyaan buat tiap step
EMAIL_OPTIONAL_STEPS = [
    ("await_email_pemulihan", "email_pemulihan", "Email pemulihan (kalau ada)"),
    ("await_hp_pemulihan", "no_hp_pemulihan", "Nomor HP pemulihan (kalau ada)"),
    ("await_kode_auth", "kode_auth", "Kode Auth (kalau ada)"),
]


def _skip_keyboard(field_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Skip \u23E9", callback_data=f"lapor_skip:{field_key}")]])


async def start_lapor_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton(k, callback_data=f"lapor_cat:{k}")]
        for k in KATEGORI_TUGAS
    ]
    buttons.append([InlineKeyboardButton("\u2795 Tugas Lain", callback_data="lapor_cat:Tugas Lain")])

    await update.callback_query.edit_message_text(
        "Tugas apa yang udah kamu selesaikan? Pilih kategorinya:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def lapor_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kategori = query.data.split(":", 1)[1]

    context.user_data["flow"] = "lapor"
    context.user_data["kategori"] = kategori

    if kategori == "Email":
        context.user_data["step"] = "await_email"
        await query.edit_message_text(
            "Kirim email akun yang kamu buat/kelola untuk tugas ini:"
        )
    elif kategori == "Shortlink":
        context.user_data["step"] = "await_shortlink"
        await query.edit_message_text("Kirim shortlink yang kamu buat:")
    elif kategori == "Tugas Lain":
        context.user_data["step"] = "await_custom_name"
        await query.edit_message_text(
            "Oke, tulis nama tugas yang kamu kerjakan (contoh: 'Bikin konten "
            "canva buat promosi')."
        )
    else:
        context.user_data["step"] = "await_link"
        contoh = CONTOH_LINK.get(kategori.lower(), "Kirim link buktinya ya (link asli, bukan acak):")
        await query.edit_message_text(f"Kategori: {kategori}\n\n{contoh}")


async def handle_lapor_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dipanggil dari main.py generic text handler kalau user_data['flow'] == 'lapor'."""
    step = context.user_data.get("step")
    text = update.message.text.strip()

    # ---------- Sub-flow kategori link biasa (Backlink, Sosmed, TikTok, Tugas Lain) ----------
    if step == "await_custom_name":
        context.user_data["jenis_tugas"] = text
        context.user_data["is_custom"] = True
        context.user_data["step"] = "await_link"
        await update.message.reply_text("Sip. Sekarang kirim link/bukti hasil kerjaannya.")
        return

    if step == "await_link":
        if not is_valid_url(text):
            await update.message.reply_text(
                "Ini kelihatannya bukan link yang valid. Kirim link yang "
                "dimulai dengan http:// atau https:// ya."
            )
            return

        kategori = context.user_data.get("kategori", "")
        if not domain_matches_category(text, kategori):
            await update.message.reply_text(
                f"Link ini kelihatannya bukan link {kategori}. Coba cek lagi "
                "dan kirim link yang sesuai."
            )
            return

        if is_duplicate_link(text, get_all_links()):
            await update.message.reply_text(
                "Link ini udah pernah dilaporkan sebelumnya. Kirim link lain "
                "buat tugas ini."
            )
            return

        if not is_link_alive(text):
            await update.message.reply_text(
                "Link ini kelihatannya nggak bisa dijangkau sama sekali "
                "(bukan diblokir, tapi beneran nggak connect). Pastikan "
                "link-nya benar, lalu kirim ulang."
            )
            return

        context.user_data["link"] = text
        context.user_data["step"] = "await_confirm"

        jenis = context.user_data.get("jenis_tugas", kategori)
        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("\u2705 Sudah benar", callback_data="lapor_confirm:yes"),
            InlineKeyboardButton("\u270F\uFE0F Koreksi", callback_data="lapor_confirm:no"),
        ]])
        await update.message.reply_text(
            f"Konfirmasi dulu ya:\n\nJenis tugas: {jenis}\nLink: {text}\n\n"
            "Sudah benar?",
            reply_markup=buttons,
        )
        return

    # ---------- Sub-flow kategori Shortlink (shortlink dulu, lanjut sama kayak Email) ----------
    if step == "await_shortlink":
        if not is_valid_url(text):
            await update.message.reply_text(
                "Ini kelihatannya bukan link yang valid. Kirim link yang "
                "dimulai dengan http:// atau https:// ya."
            )
            return
        context.user_data["shortlink"] = text
        context.user_data["step"] = "await_email"
        await update.message.reply_text(
            "Sip. Sekarang kirim email akun yang terhubung/dipakai buat "
            "shortlink ini:"
        )
        return

    # ---------- Sub-flow kategori Email ----------
    if step == "await_email":
        context.user_data["email"] = text
        context.user_data["step"] = "await_password"
        await update.message.reply_text("Kirim password akun email tersebut:")
        return

    if step == "await_password":
        context.user_data["password"] = text
        first_step, first_key, first_label = EMAIL_OPTIONAL_STEPS[0]
        context.user_data["step"] = first_step
        await update.message.reply_text(
            f"{first_label}? Kirim isinya, atau tekan Skip kalau nggak ada.",
            reply_markup=_skip_keyboard(first_key),
        )
        return

    for step_name, field_key, _label in EMAIL_OPTIONAL_STEPS:
        if step == step_name:
            context.user_data[field_key] = text
            await _advance_email_optional(update.message.reply_text, context, step_name)
            return


async def _advance_email_optional(reply_fn, context: ContextTypes.DEFAULT_TYPE, current_step: str):
    """Lanjut ke field opsional berikutnya, atau ke konfirmasi kalau udah abis."""
    idx = next(i for i, (s, _, _) in enumerate(EMAIL_OPTIONAL_STEPS) if s == current_step)
    if idx + 1 < len(EMAIL_OPTIONAL_STEPS):
        next_step, next_key, next_label = EMAIL_OPTIONAL_STEPS[idx + 1]
        context.user_data["step"] = next_step
        await reply_fn(
            f"{next_label}? Kirim isinya, atau tekan Skip kalau nggak ada.",
            reply_markup=_skip_keyboard(next_key),
        )
    else:
        context.user_data["step"] = "await_confirm_email"
        await _send_email_confirm(reply_fn, context)


async def _send_email_confirm(reply_fn, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    header = "Shortlink: " + d.get("shortlink", "") + "\n" if d.get("kategori") == "Shortlink" else ""
    ringkasan = (
        "Konfirmasi dulu ya:\n\n"
        f"{header}"
        f"Email: {d.get('email')}\n"
        f"Password: {d.get('password')}\n"
        f"Email pemulihan: {d.get('email_pemulihan') or '-'}\n"
        f"No HP pemulihan: {d.get('no_hp_pemulihan') or '-'}\n"
        f"Kode Auth: {d.get('kode_auth') or '-'}\n\n"
        "Sudah benar?"
    )
    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("\u2705 Sudah benar", callback_data="lapor_confirm:yes"),
        InlineKeyboardButton("\u270F\uFE0F Koreksi", callback_data="lapor_confirm:no"),
    ]])
    await reply_fn(ringkasan, reply_markup=buttons)


async def lapor_skip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dipencet pas user skip salah satu field opsional di sub-flow Email."""
    query = update.callback_query
    await query.answer()
    field_key = query.data.split(":", 1)[1]
    context.user_data[field_key] = ""

    step_name = next(s for s, k, _ in EMAIL_OPTIONAL_STEPS if k == field_key)
    await _advance_email_optional(query.edit_message_text, context, step_name)


async def lapor_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    jawaban = query.data.split(":", 1)[1]
    kategori = context.user_data.get("kategori", "")

    if jawaban == "no":
        if kategori == "Email":
            context.user_data["step"] = "await_email"
            await query.edit_message_text("Oke, ulangi dari awal. Kirim email akun-nya:")
        elif kategori == "Shortlink":
            context.user_data["step"] = "await_shortlink"
            await query.edit_message_text("Oke, ulangi dari awal. Kirim shortlink-nya:")
        else:
            context.user_data["step"] = "await_link"
            await query.edit_message_text("Oke, kirim ulang link yang benar.")
        return

    user = update.effective_user
    member = find_member(user.id, user.username)
    team_name = member.get("team_name") if member else "unknown"
    nama = member.get("nama") if member else user.first_name

    if kategori in ("Email", "Shortlink"):
        save_email_report(
            team_name=team_name,
            user_id=user.id,
            nama=nama,
            email=context.user_data.get("email", ""),
            password=context.user_data.get("password", ""),
            email_pemulihan=context.user_data.get("email_pemulihan", ""),
            no_hp_pemulihan=context.user_data.get("no_hp_pemulihan", ""),
            kode_auth=context.user_data.get("kode_auth", ""),
            shortlink=context.user_data.get("shortlink", "") if kategori == "Shortlink" else "",
        )
    else:
        save_report(
            team_name=team_name,
            user_id=user.id,
            nama=nama,
            jenis_tugas=context.user_data.get("jenis_tugas", kategori),
            link=context.user_data.get("link"),
            is_custom=context.user_data.get("is_custom", False),
        )

    context.user_data.clear()
    await query.edit_message_text("\u2705 Laporan tugas kamu udah tercatat. Makasih!")
