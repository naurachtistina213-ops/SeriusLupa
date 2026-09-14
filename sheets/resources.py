"""
Sistem resource-lookup generik: /link, /sosmed, /email (dst) semua pakai
mekanisme yang sama. 'link' selalu aktif dari awal (built-in) tanpa perlu
registrasi. Tipe lain ditambahin superadmin lewat command /tambahtipe.

Data disimpen format panjang di sheet 'data_resource' - 1 baris = 1 item
(bukan digabung banyak baris dalam 1 cell), biar nambah/edit/hapus 1 item
gampang. Nomor urut (1. 2. 3.) di-generate bot pas nampilin ke user, BUKAN
disimpen di sheet.
"""
from sheets.client import get_or_create_worksheet
from sheets.setup import SHEET_SCHEMAS

BUILTIN_TYPES = {"link"}


def _resource_commands_ws():
    return get_or_create_worksheet("resource_commands", SHEET_SCHEMAS["resource_commands"])


def _data_resource_ws():
    return get_or_create_worksheet("data_resource", SHEET_SCHEMAS["data_resource"])


def is_resource_command(command_name: str) -> bool:
    command_name = command_name.lower().lstrip("/")
    if command_name in BUILTIN_TYPES:
        return True
    for row in _resource_commands_ws().get_all_records():
        if row.get("command", "").lower() == command_name:
            return True
    return False


def get_active_types() -> list[str]:
    """Semua tipe resource-lookup yang aktif (built-in + yang didaftarin
    superadmin lewat /tambahtipe) - dipakai buat /help."""
    types = set(BUILTIN_TYPES)
    for row in _resource_commands_ws().get_all_records():
        cmd = row.get("command", "").lower()
        if cmd:
            types.add(cmd)
    return sorted(types)


def register_resource_type(tipe: str, dibuat_oleh: int, keterangan: str = "") -> str:
    """Daftarin tipe/command baru (misal 'sosmed'). Return 'created',
    'exists' (udah ada), atau 'reserved' (nabrak nama built-in)."""
    tipe = tipe.lower().lstrip("/")
    if tipe in BUILTIN_TYPES:
        return "reserved"

    ws = _resource_commands_ws()
    for row in ws.get_all_records():
        if row.get("command", "").lower() == tipe:
            return "exists"

    ws.append_row([tipe, tipe, dibuat_oleh, keterangan])
    return "created"


def get_categorized_data(team_name: str, tipe: str, brand: str | None = None) -> dict[str, list[str]]:
    """Return {kategori: [isi, isi, ...]} buat 1 team + 1 tipe tertentu.
    Kalau brand dikasih, difilter lagi cuma yang brand-nya cocok. Kalau
    brand=None, semua baris diambil tanpa mandang brand (dipakai buat
    team/tipe yang belum pakai sistem brand sama sekali)."""
    result: dict[str, list[str]] = {}
    for row in _data_resource_ws().get_all_records():
        if row.get("team_name", "").lower() != team_name.lower():
            continue
        if row.get("tipe", "").lower() != tipe.lower():
            continue
        if brand is not None:
            row_brand = (row.get("brand") or "").strip()
            if row_brand.lower() != brand.strip().lower():
                continue
        kategori = row.get("kategori") or "Lainnya"
        result.setdefault(kategori, []).append(row.get("isi", ""))
    return result


def get_brands_for_team_tipe(team_name: str, tipe: str) -> list[str]:
    """Daftar nama brand (unik, case asli) yang punya data buat 1
    team + 1 tipe tertentu. Kosong berarti team/tipe ini belum pakai
    sistem brand (semua data-nya dianggap 1 kelompok aja)."""
    seen: dict[str, str] = {}
    for row in _data_resource_ws().get_all_records():
        if row.get("team_name", "").lower() != team_name.lower():
            continue
        if row.get("tipe", "").lower() != tipe.lower():
            continue
        b = (row.get("brand") or "").strip()
        if b and b.lower() not in seen:
            seen[b.lower()] = b
    return list(seen.values())


def get_brands_for_team(team_name: str) -> list[str]:
    """Daftar semua nama brand yang ada buat 1 team, lintas semua tipe
    (link/sosmed/dll) - dipakai buat command /brand."""
    seen: dict[str, str] = {}
    for row in _data_resource_ws().get_all_records():
        if row.get("team_name", "").lower() != team_name.lower():
            continue
        b = (row.get("brand") or "").strip()
        if b and b.lower() not in seen:
            seen[b.lower()] = b
    return list(seen.values())


def format_categorized_reply(tipe: str, team_name: str, data: dict[str, list[str]],
                              brand: str | None = None) -> str:
    """Sengaja TANPA parse_mode Markdown - link/isi sering ada karakter
    spesial (underscore, kurung, dll) yang bikin Telegram nolak kirim
    pesan kalau dipaksa parse sebagai Markdown."""
    label = f"{team_name} ({brand})" if brand else team_name
    if not data:
        return f"Belum ada data '{tipe}' buat {label}."

    lines = [f"\U0001F517 {tipe.capitalize()} - {label}\n"]
    for kategori, items in data.items():
        lines.append(f"\u2014 {kategori} \u2014")
        for idx, item in enumerate(items, start=1):
            lines.append(f"{idx}. {item}")
        lines.append("")
    return "\n".join(lines).strip()
