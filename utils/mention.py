"""
Smart mention: pakai @username yang udah diisi manual di sheet 'anggota'
langsung, fallback ke mention berbasis user_id cuma kalau kolom username
di sheet itu emang kosong. Nggak ada verifikasi live ke Telegram API lagi
di sini (versi sebelumnya cek get_chat_member dulu, tapi itu bisa gagal
buat member yang jarang keliatan aktif ke bot, hasilnya malah fallback ID
padahal username-nya di sheet valid) - jadi data sheet dianggap sumber
kebenaran, dan admin yang jaga sheet-nya tetap update.
"""
from telegram import Bot


def build_mention_from_member(member: dict) -> str:
    """member: 1 row dari sheet 'anggota' (dict dengan key user_id, username, nama)."""
    username = (member.get("username") or "").strip().lstrip("@")
    if username:
        return f"@{username}"

    # Fallback: kolom username di sheet kosong -> mention berbasis ID
    nama = member.get("nama") or "User"
    user_id = member.get("user_id")
    return f"[{nama}](tg://user?id={user_id})"


async def build_mention(bot: Bot, chat_id: int, user_id: int, nama: str) -> str:
    """Dipertahankan buat kompatibilitas kode lain yang manggil per-user
    tanpa data sheet lengkap. Langsung pakai ID (nggak ada username
    tersedia di titik ini)."""
    safe_name = nama or "User"
    return f"[{safe_name}](tg://user?id={user_id})"


async def build_mentions_for_members(bot: Bot, chat_id: int, members: list[dict]) -> str:
    """members: list of row dari sheet 'anggota' - {"user_id", "username", "nama"}.
    Return semua mention digabung jadi 1 string dipisah spasi."""
    return " ".join(build_mention_from_member(m) for m in members)
