"""
Validasi link bukti tugas: format URL valid, domain sesuai kategori,
link hidup (fetch check), dan anti-duplikat.
"""
import re
from urllib.parse import urlparse

import requests

# Mapping kategori -> domain yang wajib ada di link. Sesuaikan/tambah sendiri.
DOMAIN_RULES = {
    "tiktok": ["tiktok.com"],
    "sosmed fb": ["facebook.com", "fb.com"],
    "sosmed ig": ["instagram.com"],
    "email": [],       # nggak ada rule domain spesifik
    "backlink": [],     # bebas domain apa aja
    "tugas lain": [],
}

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def is_valid_url(text: str) -> bool:
    return bool(_URL_RE.match(text.strip()))


def domain_matches_category(url: str, kategori: str) -> bool:
    rules = DOMAIN_RULES.get(kategori.lower(), [])
    if not rules:
        return True  # kategori ini nggak punya rule domain -> lolos
    host = urlparse(url).netloc.lower()
    return any(domain in host for domain in rules)


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def is_link_alive(url: str, timeout: int = 8) -> bool:
    """Cek link hidup. Banyak situs (Quora, prnt.sc, dll) balikin 403/401/429
    ke request tanpa User-Agent browser - itu bukan berarti link-nya mati,
    cuma anti-bot. Jadi selama server ADA yang merespon (kode apapun),
    dianggap hidup. Cuma ditolak kalau beneran gagal connect/timeout/DNS
    error total (linknya emang nggak bisa dijangkau sama sekali)."""
    try:
        requests.head(url, timeout=timeout, allow_redirects=True, headers=_HEADERS)
        return True
    except requests.RequestException:
        pass
    try:
        requests.get(url, timeout=timeout, stream=True, headers=_HEADERS)
        return True
    except requests.RequestException:
        return False


def is_duplicate_link(url: str, existing_links: list[str]) -> bool:
    return url.strip().rstrip("/") in [l.strip().rstrip("/") for l in existing_links]
