"""Job archive harian - jalan sekali per hari, mindahin baris >4 bulan
ke tab '_archive' masing-masing sheet."""
import logging

from sheets.archive import archive_all

logger = logging.getLogger(__name__)


async def run_archive_job():
    result = archive_all()
    total = sum(v for v in result.values() if v > 0)
    if total:
        logger.info("Archive job selesai: %s (total %d baris dipindah)", result, total)


def register_archive_job(scheduler):
    scheduler.add_job(run_archive_job, "interval", hours=24)
