# Lemburabadibot

Bot Telegram buat reminder, lapor tugas, keluhan, dan berbagai command
kerja tim (mention, resource lookup, dll). Database-nya Google Sheets,
code-nya di GitHub, hosting-nya di Railway.

---

## Daftar isi
1. [Setup dari nol](#setup-dari-nol)
2. [Struktur sheet](#struktur-sheet) - isi tiap tab, kolomnya apa aja
3. [Daftar command](#daftar-command) - semua command yang ada
4. [Menu PM](#menu-pm) - fitur yang diakses lewat tombol, bukan command
5. [Arsitektur singkat](#arsitektur-singkat)
6. [Belum diimplementasi](#belum-diimplementasi)

---

## Setup dari nol

1. **Bikin bot Telegram**
   - Chat `@BotFather`, `/newbot`, catat tokennya.

2. **Bikin service account Google**
   - [Google Cloud Console](https://console.cloud.google.com/) → project baru
   - Aktifkan **Google Sheets API** dan **Google Drive API**
   - IAM & Admin → Service Accounts → bikin baru → tab **Keys** → **Add Key** → **JSON**
   - Encode file JSON itu ke base64 dalam 1 baris:
     ```bash
     base64 -w0 credentials.json
     ```
     (Wajib pakai `-w0` biar nggak ada baris baru nyelip - baris baru/spasi
     yang nyelip pas copy-paste adalah sumber error base64 paling umum.)

3. **Bikin spreadsheet**
   - Bikin 1 Google Sheet kosong di akun Google kamu sendiri (bukan punya service account - service account nggak punya storage quota buat bikin file sendiri)
   - Share ke email service account (field `client_email` di JSON) dengan akses **Editor**
   - Copy ID-nya dari URL: `docs.google.com/spreadsheets/d/<ID_INI>/edit`

4. **Isi environment variable** (Railway → tab Variables, atau `.env` lokal):
   - `TELEGRAM_BOT_TOKEN`
   - `SPREADSHEET_ID`
   - `GOOGLE_CREDENTIALS_BASE64`
   - `SUPERADMIN_IDS` - user_id superadmin, dipisah koma kalau lebih dari 1
   - `DEFAULT_TIMEZONE` - contoh `Asia/Jakarta` (WIB), `Asia/Colombo` (Sri Lanka), `Asia/Makassar` (WITA)

5. **Jalanin**
   ```bash
   pip install -r requirements.txt
   python main.py
   ```
   Semua tab di spreadsheet otomatis dibuat pas pertama kali jalan.

6. **Deploy ke Railway** - push ke GitHub, connect repo di Railway, isi
   environment variables yang sama, Railway otomatis jalanin `python main.py`.

7. **Isi data awal manual di spreadsheet** (lihat bagian di bawah buat
   format tiap sheet):
   - `teams` - chat_id/topic_id tiap grup kerja
   - `anggota` - data karyawan per team
   - `admin_whitelist` - admin/leader tambahan (superadmin dari
     `SUPERADMIN_IDS` otomatis aktif, nggak perlu dicatat di sini)

---

## Struktur sheet

Semua tab ini **otomatis dibuat** bot pas pertama kali jalan (header-nya
juga otomatis diisi) - kolom di bawah cuma referensi biar tau harus isi
apa. Kalau ada tab yang header-nya nggak cocok sama daftar di bawah
(misal karena update kode), bot bakal nulis **warning di log**, bukan
auto-fix - perbaiki manual atau hapus tab-nya biar dibuat ulang dari nol.

### `reminders` - **diisi manual**
Reminder yang dikirim otomatis tiap hari/minggu.

| Kolom | Isi | Contoh |
|---|---|---|
| `id` | ID unik, bebas asal nggak sama | `1` |
| `pesan` | Teks yang dikirim | `Jangan lupa isi laporan!` |
| `waktu` | Jam `HH:MM` (24 jam), dicek tiap menit | `09:00` |
| `recurrence` | Kosong/`harian` = tiap hari. Nama hari (`senin`, `selasa`, dst) = mingguan di hari itu | `senin` |
| `target` | `main`, nama team, atau beberapa dipisah koma | `team1,team2` |
| `status` | `aktif` = jalan, apa aja selain itu = nonaktif | `aktif` |

Bisa dikelola lewat menu PM **⏰ Reminder** (superadmin) tanpa buka
spreadsheet - lihat bagian Menu PM.

### `teams` - **diisi manual**
Mapping 1 team ke 1 grup/topik Telegram + timezone-nya.

| Kolom | Isi | Contoh |
|---|---|---|
| `team_name` | Nama team, bebas | `Team1`, `main` |
| `chat_id` | ID grup Telegram (negatif, angka besar) | `-1004345835973` |
| `topic_id` | ID topik kalau grup pakai fitur Forum, kosongin kalau nggak | `5` |
| `timezone` | Timezone team ini (informasional, jadwal ikut `DEFAULT_TIMEZONE`) | `Asia/Jakarta` |

`chat_id`/`topic_id` bisa didapat otomatis dari tab `chats_registry`
(lihat di bawah), nggak perlu dicari manual lewat API.

Nama team **`main`** itu keyword khusus buat "grup utama" (dipakai di
reminder & command dengan target `main`).

### `anggota` - **diisi manual**
Roster karyawan per team - ini sumber kebenaran soal "team apa aja yang
ada" buat seluruh sistem (bukan sheet `teams`).

| Kolom | Isi | Contoh |
|---|---|---|
| `team_name` | Harus sama kayak di sheet `teams` (case-insensitive) | `Team1` |
| `user_id` | Telegram user ID | `5822534798` |
| `username` | Username Telegram (dipakai buat mention) | `@tanoto80` |
| `nama` | Nama biar gampang dikenalin | `Budi T` |

**1 orang cuma boleh 1 team** - kalau ada yang pindah team, edit
`team_name`-nya, jangan bikin baris dobel.

### `admin_whitelist` - **diisi manual**
Siapa aja yang punya akses admin/leader, dan scope-nya sejauh mana.

| Kolom | Isi | Contoh |
|---|---|---|
| `user_id` | Telegram user ID | `1135748338` |
| `nama` | Nama | `Akbar` |
| `is_whitelisted` | Harus `TRUE` (kapital) biar aktif | `TRUE` |
| `managed_team` | `all` = superadmin, atau nama team = leader team itu doang | `all` |

Superadmin dari environment variable `SUPERADMIN_IDS` otomatis aktif
walau nggak ada baris di sini. Cabut akses lewat menu PM **🚫 Revoke
Akses** (nge-set `is_whitelisted` jadi `FALSE`, bukan hapus baris).

### `custom_commands` - **otomatis** (dari `@bot /cmd <pesan>`)
Command mention custom kayak `/hp`, `/bank`, dll.

| Kolom | Isi |
|---|---|
| `command` | Nama command (tanpa slash) |
| `pesan` | Teks yang dikirim pas command dipanggil |
| `target_team` | Kosong = dinamis (ikut team pemilik chat), atau nama team fix (kalau nama command = nama team) |
| `mention_all` | Legacy, selalu `TRUE` |
| `dibuat_oleh` | user_id yang daftarin |
| `chat_id` | Chat tempat command ini di-lock (cuma jalan di sini) |
| `dibuat_pada` | Timestamp |

Command di-scope ke 1 `chat_id` - leader yang daftarin di grup mereka
otomatis ke-lock cuma di grup itu.

### `resource_commands` - **otomatis** (dari `/tambahtipe`)
Daftar tipe command lookup yang aktif (`link` selalu aktif built-in,
nggak butuh baris di sini).

| Kolom | Isi |
|---|---|
| `tipe` | Nama tipe (= nama command) |
| `command` | Sama kayak `tipe` |
| `dibuat_oleh` | user_id superadmin yang daftarin |
| `keterangan` | Deskripsi bebas |

### `data_resource` - **diisi manual**
Data buat command `/link`, `/sosmed`, dst. Format panjang - 1 baris = 1
item, biar gampang tambah/edit/hapus.

| Kolom | Isi | Contoh |
|---|---|---|
| `team_name` | Nama team | `Team1` |
| `tipe` | `link`, `sosmed`, dst (harus match sheet `resource_commands` atau built-in) | `link` |
| `kategori` | Label pengelompokan, bebas | `Link Film 1` |
| `isi` | Isinya (URL, dll) | `contohlink.com` |
| `brand` | Opsional - kalau diisi, command bakal nyuruh pilih brand dulu lewat tombol | `Brand A` |

Kalau 1 team+tipe pakai `brand`, isi konsisten semua baris (jangan
campur ada yang kosong ada yang keisi - baris kosong jadi "ketutup").

### `task_reports` - **otomatis** (dari menu Lapor Tugas)
Laporan tugas kategori link (Backlink, Sosmed, TikTok, Tugas Lain).

| Kolom | Isi |
|---|---|
| `timestamp`, `team_name`, `user_id`, `nama` | Info pelapor |
| `jenis_tugas` | Kategori tugas |
| `link` | Link bukti |
| `is_custom` | `TRUE` kalau dari kategori "Tugas Lain" |
| `status_validasi` | `valid` atau `dibatalkan` (lewat menu Batalkan Laporan) |

### `email_reports` - **otomatis** (dari Lapor Tugas kategori Email/Shortlink)
| Kolom | Isi |
|---|---|
| `timestamp`, `team_name`, `user_id`, `nama` | Info pelapor |
| `email`, `password` | Kredensial akun (plaintext, batasi akses sheet ini) |
| `email_pemulihan`, `no_hp_pemulihan`, `kode_auth` | Opsional, bisa di-skip pas lapor |
| `status` | `valid` atau `dibatalkan` |
| `shortlink` | Keisi kalau kategorinya "Shortlink", kosong kalau "Email" biasa |

### `keluhan` - **otomatis** (dari menu Ajukan Keluhan)
| Kolom | Isi |
|---|---|
| `timestamp`, `team_name`, `user_id`, `nama` | Info pelapor (bukan anonim) |
| `isi_keluhan` | Isi keluhan |
| `status` | `belum ditindak` (cuma superadmin yang bisa lihat sheet ini) |

### `chats_registry` - **otomatis** (auto-detect)
Bot nyatet sendiri tiap ada grup/topik baru yang belum pernah "ketemu".

| Kolom | Isi |
|---|---|
| `chat_id`, `topic_id` | Auto-terisi |
| `nama_grup`, `nama_topik` | Auto-terisi (kalau ada) |
| `pertama_terdeteksi` | Timestamp pertama ketemu |
| `team_name` | **Diisi manual** - superadmin cocokin baris ini ke team mana |

### `logs` - **jangan diedit manual**
Internal doang - anti-reminder-dobel-kirim, dan log akses ditolak.
Diarsipin otomatis tiap 4 bulan (lihat `/archive`).

### `shifts` - **belum dipakai**
Skema udah ada (`user_id`, `nama_shift`, `jam_mulai`, `jam_selesai`),
tapi belum ada logic yang bacanya. Reserved buat fitur jadwal-per-shift
yang masih di-skip.

### Tab `*_archive`
Dibuat otomatis pas pertama kali ada data yang diarsipkan (header sama
kayak sheet aslinya). Isinya baris-baris lama yang dipindah, bukan
dihapus.

---

## Daftar command

### Command grup
| Command | Siapa yang bisa | Fungsi |
|---|---|---|
| `@bot /namacmd <pesan>` | Leader team chat itu / superadmin | Daftar/update custom command, di-lock ke chat ini |
| `/namacmd` | Leader team target / superadmin | Jalanin command, mention team pemilik chat (dinamis) |
| `/namacmd team2` | Leader team2 / superadmin | Jalanin, mention team2 spesifik + kirim juga ke grup asli team2 kalau beda chat |
| `/namacmd all` atau `semua` | Superadmin | Broadcast ke SEMUA grup team, masing-masing mention anggotanya sendiri |
| `/namacmd main` | Superadmin | Target ke "main" (gabungan semua team) |
| `/link <team>` | Leader team target / superadmin | Lihat data link (built-in, nggak perlu didaftarin) |
| `/<tipe> <team>` | Leader team target / superadmin | Lihat data resource lookup lain yang udah didaftarin lewat `/tambahtipe` |
| `/link <team> <brand>` | sda | Skip menu pilihan, langsung tampil brand tertentu |
| `/brand <team>` | Leader team target / superadmin | List nama brand yang ada buat 1 team |
| `/listcommand` | Siapa aja | List semua custom command + resource-lookup yang aktif di chat ini |

### Command PM (semua user terdaftar)
| Command | Fungsi |
|---|---|
| `/start`, `/menu` | Buka menu utama (tombol-tombol, beda per role) |

### Command PM (khusus superadmin)
| Command | Fungsi |
|---|---|
| `/tambahtipe <tipe> <keterangan>` | Daftarin tipe resource-lookup baru (misal `sosmed`) |
| `/sync` | Reset cache internal (worksheet cache, chats_registry cache) |
| `/archive` | Trigger manual auto-archive (biar nggak perlu nunggu jadwal harian) |

Semua command di atas cuma dianggap valid kalau pengirimnya lolos
gatekeeper (ada di sheet `anggota` atau `admin_whitelist`) - kalau
belum terdaftar, PM ke bot langsung ditolak dan superadmin dinotif.

---

## Menu PM

Diakses lewat `/start` atau `/menu`, tombol beda-beda tergantung role:

**Semua user terdaftar:**
- Lapor Tugas - kategori Backlink/Sosmed FB/Sosmed IG/TikTok/Email/Shortlink/Tugas Lain, dengan validasi link + konfirmasi
- Batalkan Laporan - batalin laporan sendiri (5 terakhir, link maupun email)
- Ajukan Keluhan - cuma superadmin yang bisa lihat isinya

**Leader team + superadmin:**
- Lihat Link Team *(belum ada handler - masih TODO)*
- Help - command yang relevan buat scope mereka

**Khusus superadmin:**
- Lihat Keluhan *(belum ada handler - masih TODO)*
- Tambah Command Baru *(belum ada handler - masih TODO, sementara pakai `@bot /cmd <pesan>` langsung di grup)*
- Reminder - Tambah / Daftar (+edit) / Matikan reminder
- Revoke Akses - cabut akses admin/leader

---

## Arsitektur singkat

```
lemburabadibot/
├── main.py          # entry point, wiring semua handler
├── config.py         # load env vars
├── sheets/           # semua akses Google Sheets, 1 file per tab
├── handlers/          # logic per fitur (PM flow, group command, dst)
├── scheduler/         # job berkala (reminder, archive, lock anti-dobel)
└── utils/             # helper lintas fitur (mention, timezone, recurrence, validasi link)
```

- **Google Sheets** = database utama, dibuat manual sekali (spreadsheet
  kosong + share ke service account), sisanya (tab & header) auto-generate
- **Worksheet + header dicache** di memory per proses (`sheets/client.py`)
  buat ngirit API call - reset pakai `/sync` kalau ada tab yang
  dihapus/diedit manual pas bot lagi jalan
- **Angka besar (chat_id) dari Sheets** dibaca pakai `to_int()`
  (`sheets/client.py`), bukan `int()` polos - Google Sheets kadang
  nyimpen angka gede sebagai float/scientific notation

---

## Belum diimplementasi

Fitur yang pernah dibahas tapi disepakati untuk di-skip dulu:
- Jadwal reminder berbasis shift per-orang (sheet `shifts` reserved, belum ada logic)
- Snooze/re-reminder otomatis kalau belum direspon
- Tracking konfirmasi via reply/reaction ke reminder
- Backup otomatis spreadsheet ke file terpisah

Placeholder di menu PM yang belum ada handler-nya:
- Lihat Link Team (PM)
- Lihat Keluhan (PM)
- Tambah Command Baru (PM) - sementara pakai `@bot /cmd <pesan>` di grup
