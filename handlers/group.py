"""
Auto-detect chat_id/topic_id baru:
1. Pas bot ditambahin ke grup baru -> catat chat_id-nya
2. Pas ada pesan dari topik yang belum pernah tercatat -> catat kombinasi
   chat_id + topic_id itu

Admin cukup buka sheet 'chats_registry' abis itu, isi kolom team_name
buat baris yang relevan - nggak perlu cari chat_id/topic_id manual lagi.
"""
import logging

from telegram import ChatMemberUpdated, Update
from telegram.ext import ContextTypes

from sheets.chats_registry import is_known, register_chat

logger = logging.getLogger(__name__)


def _bot_was_just_added(chat_member_update: ChatMemberUpdated) -> bool:
    """True kalau status bot berubah dari 'nggak ada di grup' jadi 'ada di grup'."""
    old_status = chat_member_update.old_chat_member.status
    new_status = chat_member_update.new_chat_member.status
    was_out = old_status in ("left", "kicked", "banned")
    is_in = new_status in ("member", "administrator", "restricted")
    return was_out and is_in


async def handle_bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trigger dari ChatMemberHandler.MY_CHAT_MEMBER - dipanggil tiap status
    bot berubah di suatu chat (ditambah, dikick, dipromote jadi admin, dll)."""
    cmu = update.my_chat_member
    if not _bot_was_just_added(cmu):
        return

    chat = cmu.chat
    if chat.type == "private":
        return  # bukan grup, skip

    if is_known(chat.id, None):
        return

    register_chat(chat.id, None, nama_grup=chat.title or "")
    logger.info("Grup baru terdeteksi: %s (%s)", chat.title, chat.id)


async def handle_group_message_for_topic_detection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trigger dari MessageHandler buat semua pesan grup. Cek apakah
    kombinasi chat_id + topic_id ini baru, kalau iya catat otomatis.

    Handler ini SENGAJA nggak nge-block/reply apapun - cuma nyatet di
    belakang, biar nggak ganggu flow command lain di grup yang sama."""
    message = update.effective_message
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return

    topic_id = message.message_thread_id  # None kalau bukan dari topik/grup nggak pakai Forum

    if is_known(chat.id, topic_id):
        return

    nama_topik = ""
    if message.forum_topic_created:
        nama_topik = message.forum_topic_created.name

    register_chat(chat.id, topic_id, nama_grup=chat.title or "", nama_topik=nama_topik)
    logger.info("Topik/chat baru terdeteksi: chat_id=%s topic_id=%s", chat.id, topic_id)
