"""
Loop yang jalan tiap menit, cek reminder mana yang jatuh tempo dan kirim.

Asumsi format kolom 'waktu' di sheet reminders untuk versi awal ini: "HH:MM"
(reminder harian). TODO: kembangkan buat dukung jadwal per-shift (bandingin
ke sheet 'shifts' per user, bukan cuma 1 jam fix per reminder).
"""
import logging
from datetime import datetime

import pytz
from telegram import Bot
from telegram.error import TelegramError

from config import DEFAULT_TIMEZONE
from scheduler.lock import already_sent, mark_sent
from sheets.reminders import get_active_reminders, resolve_targets
from utils.recurrence import matches_today

logger = logging.getLogger(__name__)


async def check_and_send_reminders(bot: Bot):
    tz = pytz.timezone(DEFAULT_TIMEZONE)
    now = datetime.now(tz)
    current_hhmm = now.strftime("%H:%M")
    today_str = now.strftime("%Y-%m-%d")

    for reminder in get_active_reminders():
        if not matches_today(reminder.get("recurrence"), now.weekday()):
            continue
        if reminder.get("waktu") != current_hhmm:
            continue

        reminder_id = str(reminder.get("id"))
        slot = f"{today_str} {current_hhmm}"

        if already_sent(reminder_id, slot):
            continue

        targets = resolve_targets(reminder.get("target", "main"))
        for t in targets:
            try:
                await bot.send_message(
                    chat_id=t["chat_id"],
                    message_thread_id=t["topic_id"],  # None -> jatuh ke General/grup biasa
                    text=reminder.get("pesan", ""),
                )
                mark_sent(reminder_id, slot, t["chat_id"])
            except TelegramError as e:
                logger.error("Gagal kirim reminder %s ke %s: %s", reminder_id, t["chat_id"], e)


def register_reminder_job(scheduler, bot: Bot):
    """Daftarin job ke APScheduler, jalan tiap menit."""
    scheduler.add_job(check_and_send_reminders, "interval", minutes=1, args=[bot])
