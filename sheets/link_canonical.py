"""Baca/tulis sheet 'link_canonical' - link penting lintas team, dikelola
khusus superadmin lewat menu PM. Beda dari '/link' per-team (yang
sumbernya sheet 'data_resource') - ini lebih ke repository umum, nggak
harus terikat ke 1 team."""
from sheets.client import get_or_create_worksheet
from sheets.setup import SHEET_SCHEMAS
from utils.timezone import now_str


def _ws():
    return get_or_create_worksheet("link_canonical", SHEET_SCHEMAS["link_canonical"])


def get_all_links() -> list[dict]:
    return _ws().get_all_records()


def add_link(team_name: str, kategori: str, link: str, keterangan: str, ditambahkan_oleh: int):
    _ws().append_row([team_name, kategori, link, keterangan, ditambahkan_oleh, now_str()])


def format_all_links() -> str:
    rows = get_all_links()
    if not rows:
        return "Belum ada link canonical yang ditambahin."

    grouped: dict[str, list[dict]] = {}
    for r in rows:
        team = r.get("team_name") or "Umum"
        grouped.setdefault(team, []).append(r)

    lines = ["\U0001F517 Link Canonical\n"]
    for team, items in grouped.items():
        lines.append(f"\U0001F4CC {team}")
        for it in items:
            kategori = it.get("kategori") or "-"
            link = it.get("link", "")
            keterangan = it.get("keterangan", "")
            baris = f"- [{kategori}] {link}"
            if keterangan:
                baris += f" ({keterangan})"
            lines.append(baris)
        lines.append("")
    return "\n".join(lines).strip()
