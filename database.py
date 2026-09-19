"""
Database Module - Google Sheets sebagai Data Utama untuk Sistem Presensi Mahasiswa & Kelas
Semua operasi CRUD langsung ke Google Sheets via Webhook API.
Menggunakan caching untuk efisiensi - semua data dalam satu panggilan Sheets.
"""
import datetime
import requests

from config import load_config
from sheets_sync import get_webhook_url, is_sheets_enabled

try:
    import zoneinfo
    WIB_TZ = zoneinfo.ZoneInfo("Asia/Jakarta")
except Exception:
    WIB_TZ = datetime.timezone(datetime.timedelta(hours=7), name="WIB")


def get_wib_now():
    """Mengembalikan datetime saat ini dalam Waktu Indonesia Barat (WIB / UTC+7)."""
    return datetime.datetime.now(WIB_TZ)


# ===================== CACHING DATA =====================
# Module-level cache: semua data Sheets disimpan di sini setelah pertama kali diambil.
# Fungsi-fungsi view dan business logic membaca dari cache ini, bukan dari SQLite.

_SHEETS_CACHE = {}
_CACHE_TIMESTAMP = None
_CACHE_STALE_SECONDS = 30  # Cache akan refresh setelah 30 detik


def _now_seconds():
    return datetime.datetime.now().timestamp()


def _is_cache_stale():
    if _CACHE_TIMESTAMP is None:
        return True
    return (_now_seconds() - _CACHE_TIMESTAMP) > _CACHE_STALE_SECONDS


def _refresh_cache():
    """
    Ambil semua tabel dari Google Sheets sekaligus dan simpan di cache.
    Mengembalikan True jika berhasil, False jika gagal.
    """
    global _SHEETS_CACHE, _CACHE_TIMESTAMP
    data = _fetch_all_sheets()
    if data is not None:
        _SHEETS_CACHE = data
        _CACHE_TIMESTAMP = _now_seconds()
        return True
    return False


def _get_cache():
    """
    Dapatkan data dari cache. Jika cache kosong atau kedaluwarsa, refresh.
    Selalu coba fetch jika ada URL webhook.
    """
    if _is_cache_stale() or not _SHEETS_CACHE:
        _refresh_cache()
    return _SHEETS_CACHE


def _fetch_all_sheets():
    """
    Panggil Google Sheets Webhook untuk mengambil semua tabel sekaligus.
    Mengembalikan dict {sheet_name: [rows]} atau None jika gagal.
    """
    url = get_webhook_url()
    if not url:
        return None
    try:
        resp = requests.get(url, params={"action": "get_all"}, timeout=30)
        if resp.status_code != 200:
            return None
        result = resp.json()
        if result.get("status") != "success":
            return None
        return result.get("data") or {}
    except Exception:
        return None


def _get_table_from_cache(table_name):
    """
    Ambil data dari cache untuk tabel tertentu.
    Jika cache tidak tersedia, fetch langsung.
    """
    cache = _get_cache()
    if table_name in cache:
        return cache[table_name]
    # Fallback: fetch langsung
    url = get_webhook_url()
    if not url:
        return []
    try:
        resp = requests.get(url, params={"action": "get_table", "table": table_name}, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if data.get("status") != "success":
            return []
        return data.get("data") or []
    except Exception:
        return []


# ===================== HELPER FUNCTIONS =====================

def _safe_int(value, default=1):
    """Google Sheets dapat mengembalikan 1/0, TRUE/FALSE, atau string kosong."""
    if value is None or str(value).strip() == "":
        return default
    if isinstance(value, bool):
        return int(value)
    text = str(value).strip().lower()
    if text in ("true", "yes", "ya", "aktif"):
        return 1
    if text in ("false", "no", "tidak", "nonaktif", "inactive"):
        return 0
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return default


def _safe_id(value):
    """Normalisasi ID dari Sheets, termasuk angka seperti 1.0."""
    if value is None or str(value).strip() == "":
        return None
    try:
        number = float(value)
        if number.is_integer():
            return int(number)
    except (TypeError, ValueError):
        pass
    return value


def _safe_text(value, default=""):
    if value is None:
        return default
    return str(value).strip()


def _find_row(rows, key, value):
    """Cari baris dalam list of dict berdasarkan key dan value."""
    for row in rows:
        if str(row.get(key)) == str(value):
            return row
    return None


def _invalidate_cache():
    """Invalidasi cache agar data berikutnya diambil langsung dari Google Sheets."""
    
    _CACHE_TIMESTAMP = None


def _upsert_row_in_sheets(table_name, row_dict, key="id"):
    """Upsert (insert atau update) baris ke Google Sheets."""
    url = get_webhook_url()
    if not url:
        return False
    try:
        resp = requests.post(url, json={
            "action": "upsert_row",
            "table": table_name,
            "key": key,
            "row": row_dict
        }, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def _delete_row_in_sheets(table_name, key, value):
    """Hapus baris dari Google Sheets."""
    url = get_webhook_url()
    if not url:
        return False
    try:
        resp = requests.post(url, json={
            "action": "delete_row",
            "table": table_name,
            "key": key,
            "value": value
        }, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def _call_sheets(action, params=None, json_body=None):
    """Helper untuk memanggil Google Sheets Webhook API."""
    url = get_webhook_url()
    if not url:
        return None
    try:
        if json_body is not None:
            resp = requests.post(url, json=json_body, timeout=30)
        else:
            resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("status") != "success":
            return None
        return data
    except Exception:
        return None


# ===================== INISIALISASI =====================

def init_db():
    """
    Inisialisasi database. Mengambil data dari Google Sheets ke cache.
    Selalu coba fetch jika ada URL webhook.
    """
    global _SHEETS_CACHE, _CACHE_TIMESTAMP
    url = get_webhook_url()
    if not url:
        print("⚠️ Google Sheets Webhook URL belum diatur.")
        print("   Data tidak dapat ditampilkan. Atur URL webhook di Pengaturan.")
        _SHEETS_CACHE = {}
        _CACHE_TIMESTAMP = None
    else:
        success = _refresh_cache()
        if success:
            total = sum(len(v) for v in _SHEETS_CACHE.values())
            print(f"✅ Google Sheets terhubung. Data dimuat ({total} total baris).")
        else:
            print("⚠️ Gagal terhubung ke Google Sheets. Periksa URL Webhook di Pengaturan.")
            _SHEETS_CACHE = {}
            _CACHE_TIMESTAMP = None

def is_connection_ok():
    """Periksa apakah koneksi Google Sheets aktif dan data tersedia."""
    url = get_webhook_url()
    if not url:
        return False
    return _refresh_cache()

# ===================== DATA ACCESS LAYER =====================

def _get_all_pegawai_raw():
    """Ambil semua data pegawai dari Google Sheets (mahasiswa)."""
    return _get_table_from_cache("mahasiswa")


def _get_all_presensi_raw():
    """Ambil semua data presensi dari Google Sheets."""
    return _get_table_from_cache("presensi")


def _get_all_riwayat_kelas_raw():
    """Ambil semua data riwayat kelas dari Google Sheets."""
    return _get_table_from_cache("riwayat_kelas")


def _get_all_riwayat_izin_raw():
    """Ambil semua data riwayat izin dari Google Sheets."""
    return _get_table_from_cache("riwayat_izin")


def _get_all_riwayat_tugas_raw():
    """Ambil semua data riwayat tugas luar dari Google Sheets."""
    return _get_table_from_cache("riwayat_tugas_luar")


# ===================== MAHASISWA (PEGAWAI) CRUD =====================

def get_all_pegawai(only_active=True, search_query=None, departemen=None):
    """Ambil semua data mahasiswa dari Google Sheets."""
    all_pegawai = _get_all_pegawai_raw()
    rows = []
    for p in all_pegawai:
        if only_active and _safe_int(p.get("status_aktif"), 1) != 1:
            continue
        rows.append({
            "id": _safe_id(p.get("id")),
            "nik": _safe_text(p.get("nik")),
            "nama": _safe_text(p.get("nama")),
            "jabatan": _safe_text(p.get("jabatan"), "Mahasiswa"),
            "departemen": _safe_text(p.get("departemen"), "Pendidikan Matematika"),
            "telepon": _safe_text(p.get("telepon")),
            "email": _safe_text(p.get("email")),
            "status_aktif": _safe_int(p.get("status_aktif"), 1),
            "created_at": _safe_text(p.get("created_at"))
        })

    if search_query:
        sq = search_query.strip().lower()
        rows = [p for p in rows if sq in p["nama"].lower() or sq in p.get("nik", "").lower() or sq in p.get("jabatan", "").lower()]

    if departemen and departemen != "Semua Program Studi":
        rows = [p for p in rows if p["departemen"] == departemen]

    rows.sort(key=lambda x: x["nama"])
    return rows


def get_pegawai_by_id(pegawai_id):
    """Cari mahasiswa berdasarkan ID dari Google Sheets."""
    all_pegawai = _get_all_pegawai_raw()
    row = _find_row(all_pegawai, "id", pegawai_id)
    if row:
        return {
            "id": _safe_id(row.get("id")),
            "nik": _safe_text(row.get("nik")),
            "nama": _safe_text(row.get("nama")),
            "jabatan": _safe_text(row.get("jabatan"), "Mahasiswa"),
            "departemen": _safe_text(row.get("departemen"), "Pendidikan Matematika"),
            "telepon": _safe_text(row.get("telepon")),
            "email": _safe_text(row.get("email")),
            "status_aktif": _safe_int(row.get("status_aktif"), 1),
            "created_at": _safe_text(row.get("created_at"))
        }
    return None


def get_pegawai_by_nik(nik):
    """Cari mahasiswa berdasarkan NIK dari Google Sheets."""
    all_pegawai = _get_all_pegawai_raw()
    for row in all_pegawai:
        if str(row.get("nik", "")).lower().strip() == str(nik).lower().strip():
            return {
                "id": _safe_id(row.get("id")),
                "nik": _safe_text(row.get("nik")),
                "nama": _safe_text(row.get("nama")),
                "jabatan": _safe_text(row.get("jabatan"), "Mahasiswa"),
                "departemen": _safe_text(row.get("departemen"), "Pendidikan Matematika"),
                "telepon": _safe_text(row.get("telepon")),
                "email": _safe_text(row.get("email")),
                "status_aktif": _safe_int(row.get("status_aktif"), 1),
                "created_at": _safe_text(row.get("created_at"))
            }
    return None


def add_pegawai(nama, telepon="", email="", jabatan="Mahasiswa", departemen="Pendidikan Matematika", nik=""):
    """
    Tambah mahasiswa ke Google Sheets.
    NIK otomatis di-generate jika tidak diberikan.
    """
    all_pegawai = _get_all_pegawai_raw()
    clean_nama = nama.strip()

    if not nik or not nik.strip():
        next_num = len(all_pegawai) + 1
        clean_nik = f"MHS-{next_num:03d}"
    else:
        clean_nik = nik.strip()

    # Cek duplikasi NIK
    if _find_row(all_pegawai, "nik", clean_nik):
        clean_nik = f"MHS-{get_wib_now().strftime('%M%S')}"

    new_id = len(all_pegawai) + 1
    existing_ids = [r.get("id") for r in all_pegawai]
    while str(new_id) in [str(eid) for eid in existing_ids]:
        new_id += 1

    row_data = {
        "id": new_id,
        "nik": clean_nik,
        "nama": clean_nama,
        "jabatan": jabatan.strip(),
        "departemen": departemen.strip(),
        "telepon": telepon.strip(),
        "email": email.strip(),
        "status_aktif": 1,
        "created_at": get_wib_now().strftime("%Y-%m-%d %H:%M:%S")
    }

    success = _upsert_row_in_sheets("mahasiswa", row_data, key="id")
    if success:
        # Invalidate cache agar data refresh
        
        _invalidate_cache()
        return True, "Data mahasiswa berhasil ditambahkan!", new_id
    return False, "Gagal menambahkan data ke Google Sheets.", None


def update_pegawai(pegawai_id, nama, telepon="", email="", jabatan="Mahasiswa", departemen="Pendidikan Matematika", nik="", status_aktif=1):
    """Update data mahasiswa di Google Sheets."""
    all_pegawai = _get_all_pegawai_raw()
    existing = _find_row(all_pegawai, "id", pegawai_id)
    if not existing:
        return False, "Data mahasiswa tidak ditemukan!"

    clean_nama = nama.strip()
    if not nik or not nik.strip():
        clean_nik = existing.get("nik") or f"MHS-{pegawai_id:03d}"
    else:
        clean_nik = nik.strip()

    row_data = {
        "id": pegawai_id,
        "nik": clean_nik,
        "nama": clean_nama,
        "jabatan": jabatan.strip(),
        "departemen": departemen.strip(),
        "telepon": telepon.strip(),
        "email": email.strip(),
        "status_aktif": status_aktif
    }

    success = _upsert_row_in_sheets("mahasiswa", row_data, key="id")
    if success:
        
        _invalidate_cache()
        return True, "Data mahasiswa berhasil diperbarui!"
    return False, "Gagal memperbarui data di Google Sheets."


def delete_pegawai(pegawai_id):
    """
    Hapus mahasiswa dari Google Sheets.
    Jika memiliki riwayat presensi, ubah status menjadi Non-Aktif.
    """
    all_pegawai = _get_all_pegawai_raw()
    existing = _find_row(all_pegawai, "id", pegawai_id)
    if not existing:
        return False, "Data mahasiswa tidak ditemukan!"

    # Cek apakah memiliki riwayat presensi
    all_presensi = _get_all_presensi_raw()
    has_presensi = any(str(p.get("pegawai_id")) == str(pegawai_id) for p in all_presensi)

    if has_presensi:
        row_data = {"id": pegawai_id, "status_aktif": 0}
        _upsert_row_in_sheets("mahasiswa", row_data, key="id")
        
        _invalidate_cache()
        return True, "Mahasiswa memiliki riwayat presensi, status diubah menjadi Non-Aktif."

    success = _delete_row_in_sheets("mahasiswa", "id", pegawai_id)
    if success:
        
        _invalidate_cache()
        return True, "Data mahasiswa berhasil dihapus permanen."
    return False, "Gagal menghapus data dari Google Sheets."


def get_list_departemen():
    """Ambil daftar departemen unik dari Google Sheets."""
    all_pegawai = _get_all_pegawai_raw()
    deps = set()
    for p in all_pegawai:
        d = _safe_text(p.get("departemen"))
        if d:
            deps.add(d)
    if not deps:
        deps = ["Pendidikan Matematika", "Fisika", "Micro Teaching", "Laboratorium"]
    return sorted(deps)


# ===================== RIWAYAT MULTI-SESI KELAS =====================

def get_riwayat_kelas_by_presensi(presensi_id):
    """Ambil riwayat kelas berdasarkan presensi_id."""
    if not presensi_id:
        return []
    all_rk = _get_all_riwayat_kelas_raw()
    rows = []
    for r in all_rk:
        if _safe_id(r.get("presensi_id")) == presensi_id:
            rows.append({
                "id": _safe_id(r.get("id")),
                "presensi_id": _safe_id(r.get("presensi_id")),
                "pegawai_id": _safe_id(r.get("pegawai_id")),
                "tanggal": _safe_text(r.get("tanggal")),
                "jam_masuk_kelas": _safe_text(r.get("jam_masuk_kelas")),
                "jam_kembali_kelas": _safe_text(r.get("jam_kembali_kelas")),
                "keterangan": _safe_text(r.get("keterangan")),
                "created_at": _safe_text(r.get("created_at"))
            })
    rows.sort(key=lambda x: x.get("id", 0))
    return rows


def get_riwayat_kelas_today(pegawai_id, tanggal=None):
    """Ambil riwayat kelas hari ini."""
    if not tanggal:
        tanggal = get_today_str()
    all_rk = _get_all_riwayat_kelas_raw()
    rows = []
    for r in all_rk:
        if (_safe_id(r.get("pegawai_id")) == pegawai_id and
            _safe_text(r.get("tanggal")) == tanggal):
            rows.append({
                "id": _safe_id(r.get("id")),
                "presensi_id": _safe_id(r.get("presensi_id")),
                "pegawai_id": _safe_id(r.get("pegawai_id")),
                "tanggal": _safe_text(r.get("tanggal")),
                "jam_masuk_kelas": _safe_text(r.get("jam_masuk_kelas")),
                "jam_kembali_kelas": _safe_text(r.get("jam_kembali_kelas")),
                "keterangan": _safe_text(r.get("keterangan")),
                "created_at": _safe_text(r.get("created_at"))
            })
    rows.sort(key=lambda x: x.get("id", 0))
    return rows


def calculate_total_kelas_duration(riwayat_list):
    """Menghitung total durasi kumulatif seluruh sesi kelas dalam 1 hari."""
    if not riwayat_list:
        return "-"
    total_seconds = 0
    valid_sessions = 0
    for r in riwayat_list:
        start_str = r.get("jam_masuk_kelas")
        end_str = r.get("jam_kembali_kelas")
        if start_str and end_str:
            try:
                t1 = datetime.datetime.strptime(start_str, "%H:%M:%S")
                t2 = datetime.datetime.strptime(end_str, "%H:%M:%S")
                if t2 >= t1:
                    total_seconds += int((t2 - t1).total_seconds())
                    valid_sessions += 1
            except Exception:
                pass
    if valid_sessions == 0 and total_seconds == 0:
        return "-"
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}j {minutes}m"


def format_kelas_summary(riwayat_list):
    """Memformat ringkasan multi-sesi kelas menjadi teks ramah baca."""
    if not riwayat_list:
        return "-"
    parts = []
    for idx, r in enumerate(riwayat_list, 1):
        start = r.get("jam_masuk_kelas") or "?"
        end = r.get("jam_kembali_kelas")
        ket = r.get("keterangan") or "Kelas"
        start_short = start[:5] if len(start) >= 5 else start
        if end:
            end_short = end[:5] if len(end) >= 5 else end
            parts.append(f"K{idx}: {start_short}-{end_short} ({ket})")
        else:
            parts.append(f"K{idx}: {start_short}-Sedang Kelas ({ket})")
    return " | ".join(parts)


def format_kelas_time_display(riwayat_list):
    """Format kolom jam masuk kelas ringkas untuk tabel."""
    if not riwayat_list:
        return "-"
    if len(riwayat_list) == 1:
        r = riwayat_list[0]
        start = r.get("jam_masuk_kelas") or "-"
        end = r.get("jam_kembali_kelas")
        if end:
            return f"{start[:5]}-{end[:5]}" if len(start) >= 5 and len(end) >= 5 else f"{start}-{end}"
        return f"{start[:5]} (Sedang Kelas)" if len(start) >= 5 else f"{start} (Sedang Kelas)"
    else:
        sesi_strs = []
        for idx, r in enumerate(riwayat_list, 1):
            s = (r.get("jam_masuk_kelas") or "")[:5]
            e = (r.get("jam_kembali_kelas") or "")[:5] if r.get("jam_kembali_kelas") else "Aktif"
            sesi_strs.append(f"K{idx}: {s}-{e}")
        return f"{len(riwayat_list)} Sesi ({', '.join(sesi_strs)})"


def get_riwayat_izin_today(pegawai_id, tanggal=None):
    """Ambil riwayat izin hari ini."""
    if not tanggal:
        tanggal = get_today_str()
    all_ri = _get_all_riwayat_izin_raw()
    rows = []
    for r in all_ri:
        if (_safe_id(r.get("pegawai_id")) == pegawai_id and
            _safe_text(r.get("tanggal")) == tanggal):
            rows.append({
                "id": _safe_id(r.get("id")),
                "presensi_id": _safe_id(r.get("presensi_id")),
                "pegawai_id": _safe_id(r.get("pegawai_id")),
                "tanggal": _safe_text(r.get("tanggal")),
                "jam_izin_keluar": _safe_text(r.get("jam_izin_keluar")),
                "jam_kembali_izin": _safe_text(r.get("jam_kembali_izin")),
                "keterangan": _safe_text(r.get("keterangan")),
                "created_at": _safe_text(r.get("created_at"))
            })
    rows.sort(key=lambda x: x.get("id", 0))
    return rows


def calculate_total_izin_duration(riwayat_list):
    """Menghitung total durasi kumulatif seluruh sesi izin keluar dalam 1 hari."""
    if not riwayat_list:
        return "-"
    total_seconds = 0
    valid_sessions = 0
    for r in riwayat_list:
        start_str = r.get("jam_izin_keluar")
        end_str = r.get("jam_kembali_izin")
        if start_str and end_str:
            try:
                t1 = datetime.datetime.strptime(start_str, "%H:%M:%S")
                t2 = datetime.datetime.strptime(end_str, "%H:%M:%S")
                if t2 >= t1:
                    total_seconds += int((t2 - t1).total_seconds())
                    valid_sessions += 1
            except Exception:
                pass
    if valid_sessions == 0 and total_seconds == 0:
        return "-"
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}j {minutes}m"


def format_izin_summary(riwayat_list):
    """Memformat ringkasan multi-sesi izin keluar menjadi teks ramah baca."""
    if not riwayat_list:
        return "-"
    parts = []
    for idx, r in enumerate(riwayat_list, 1):
        start = r.get("jam_izin_keluar") or "?"
        end = r.get("jam_kembali_izin")
        ket = r.get("keterangan") or "Izin Keluar"
        start_short = start[:5] if len(start) >= 5 else start
        if end:
            end_short = end[:5] if len(end) >= 5 else end
            parts.append(f"Iz{idx}: {start_short}-{end_short} ({ket})")
        else:
            parts.append(f"Iz{idx}: {start_short}-Sedang Izin ({ket})")
    return " | ".join(parts)


def format_izin_time_display(riwayat_list):
    """Format kolom jam izin keluar ringkas untuk tabel."""
    if not riwayat_list:
        return "-"
    if len(riwayat_list) == 1:
        r = riwayat_list[0]
        start = r.get("jam_izin_keluar") or "-"
        end = r.get("jam_kembali_izin")
        if end:
            return f"{start[:5]}-{end[:5]}" if len(start) >= 5 and len(end) >= 5 else f"{start}-{end}"
        return f"{start[:5]} (Sedang Izin)" if len(start) >= 5 else f"{start} (Sedang Izin)"
    else:
        sesi_strs = []
        for idx, r in enumerate(riwayat_list, 1):
            s = (r.get("jam_izin_keluar") or "")[:5]
            e = (r.get("jam_kembali_izin") or "")[:5] if r.get("jam_kembali_izin") else "Aktif"
            sesi_strs.append(f"Iz{idx}: {s}-{e}")
        return f"{len(riwayat_list)} Izin ({', '.join(sesi_strs)})"


# ===================== PRESENSI =====================

def get_today_str():
    return get_wib_now().strftime("%Y-%m-%d")


def get_current_time_str():
    return get_wib_now().strftime("%H:%M:%S")


def get_today_presence_record(pegawai_id):
    """Ambil catatan presensi hari ini untuk seorang pegawai."""
    today = get_today_str()
    all_presensi = _get_all_presensi_raw()
    for p in all_presensi:
        if (_safe_id(p.get("pegawai_id")) == pegawai_id and
            _safe_text(p.get("tanggal")) == today):
            return {
                "id": _safe_id(p.get("id")),
                "pegawai_id": _safe_id(p.get("pegawai_id")),
                "tanggal": _safe_text(p.get("tanggal")),
                "jam_masuk": _safe_text(p.get("jam_masuk")),
                "jam_masuk_kelas": _safe_text(p.get("jam_masuk_kelas")),
                "jam_kembali_kelas": _safe_text(p.get("jam_kembali_kelas")),
                "keterangan_kelas": _safe_text(p.get("keterangan_kelas")),
                "jam_bertugas_keluar": _safe_text(p.get("jam_bertugas_keluar")),
                "jam_kembali": _safe_text(p.get("jam_kembali")),
                "jam_izin_keluar": _safe_text(p.get("jam_izin_keluar")),
                "jam_kembali_izin": _safe_text(p.get("jam_kembali_izin")),
                "keterangan_izin": _safe_text(p.get("keterangan_izin")),
                "jam_keluar": _safe_text(p.get("jam_keluar")),
                "keterangan_tugas": _safe_text(p.get("keterangan_tugas")),
                "status": _safe_text(p.get("status"), "Hadir"),
                "catatan": _safe_text(p.get("catatan")),
                "updated_at": _safe_text(p.get("updated_at"))
            }
    return None


def parse_time_setting(time_str, default_hour=8, default_minute=0):
    if not time_str:
        return default_hour, default_minute
    cleaned = str(time_str).strip().replace(".", ":")
    parts = cleaned.split(":")
    try:
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return h, m
    except Exception:
        return default_hour, default_minute


def record_attendance(pegawai_id, action_type, keterangan="", custom_time=None):
    """
    Mencatat presensi untuk 6 tipe:
    - 'masuk': Jam Masuk (Datang)
    - 'kelas': Jam Untuk Kelas (Mulai Kelas - Multi-Sesi)
    - 'kembali_kelas': Jam Kembali dari Kelas
    - 'tugas_keluar': Jam Bertugas Keluar
    - 'kembali': Jam Kembali dari Tugas Luar
    - 'izin_keluar': Jam Izin Keluar
    - 'kembali_shift': Kembali dari Izin Keluar
    - 'keluar': Jam Keluar / Selesai
    """
    today = get_today_str()
    now_time = custom_time if custom_time else get_current_time_str()

    # Ambil data terkait dari cache/Sheets
    all_pegawai = _get_all_pegawai_raw()
    pegawai = _find_row(all_pegawai, "id", pegawai_id)
    if not pegawai:
        return False, "Pegawai tidak ditemukan!", None

    all_presensi = _get_all_presensi_raw()
    existing = None
    for p in all_presensi:
        if (_safe_id(p.get("pegawai_id")) == pegawai_id and _safe_text(p.get("tanggal")) == today):
            existing = p
            break

    pegawai_data = {
        "id": _safe_id(pegawai.get("id")),
        "nik": _safe_text(pegawai.get("nik")),
        "nama": _safe_text(pegawai.get("nama")),
        "jabatan": _safe_text(pegawai.get("jabatan"), "Mahasiswa"),
        "departemen": _safe_text(pegawai.get("departemen"), "Pendidikan Matematika"),
    }

    # 1. JAM MASUK
    if action_type == "masuk":
        if existing and _safe_text(existing.get("jam_masuk")):
            return False, f"{pegawai_data['nama']} sudah melakukan presensi MASUK hari ini pukul {existing['jam_masuk']}.", dict(existing) if existing else None

        if existing:
            existing["jam_masuk"] = now_time
            existing["status"] = "Tepat Waktu"
            _upsert_row_in_sheets("presensi", existing, key="id")
            presensi_id = _safe_id(existing.get("id"))
        else:
            presensi_id = len(all_presensi) + 1
            new_presensi = {
                "id": presensi_id,
                "pegawai_id": pegawai_id,
                "tanggal": today,
                "jam_masuk": now_time,
                "status": "Tepat Waktu",
                "updated_at": get_wib_now().strftime("%Y-%m-%d %H:%M:%S")
            }
            _upsert_row_in_sheets("presensi", new_presensi, key="id")

        msg = f"Berhasil! Presensi MASUK tercatat pukul {now_time} (Tepat Waktu)."
        
        _invalidate_cache()
        return True, msg, new_presensi if not existing else existing

    # 2. JAM KE KELAS (MULTI-SESI)
    elif action_type == "kelas":
        all_rk = _get_all_riwayat_kelas_raw()
        active_class = None
        for rk in all_rk:
            if (_safe_id(rk.get("pegawai_id")) == pegawai_id and
                _safe_text(rk.get("tanggal")) == today and
                not _safe_text(rk.get("jam_kembali_kelas"))):
                active_class = rk
                break

        if active_class:
            ket_act = _safe_text(active_class.get("keterangan"), "Kelas")
            return False, f"{pegawai_data['nama']} saat ini masih tercatat SEDANG DI KELAS ({ket_act}) sejak pukul {active_class['jam_masuk_kelas']}. Silakan lakukan presensi 'Kembali Kelas' terlebih dahulu.", dict(existing) if existing else None

        sesi_num = len([r for r in all_rk if _safe_id(r.get("pegawai_id")) == pegawai_id and _safe_text(r.get("tanggal")) == today]) + 1
        ket = keterangan.strip() if keterangan.strip() else f"Kegiatan Belajar Mengajar / Kelas (Sesi {sesi_num})"

        if existing:
            existing["jam_masuk"] = _safe_text(existing.get("jam_masuk")) or now_time
            existing["jam_masuk_kelas"] = now_time
            existing["keterangan_kelas"] = ket
            existing["status"] = "Sedang di Kelas"
            _upsert_row_in_sheets("presensi", existing, key="id")
            presensi_id = _safe_id(existing.get("id"))
        else:
            presensi_id = len(all_presensi) + 1
            new_presensi = {
                "id": presensi_id,
                "pegawai_id": pegawai_id,
                "tanggal": today,
                "jam_masuk": now_time,
                "jam_masuk_kelas": now_time,
                "keterangan_kelas": ket,
                "status": "Sedang di Kelas",
                "updated_at": get_wib_now().strftime("%Y-%m-%d %H:%M:%S")
            }
            _upsert_row_in_sheets("presensi", new_presensi, key="id")

        rk_id = len(all_rk) + 1
        new_rk = {
            "id": rk_id,
            "presensi_id": presensi_id,
            "pegawai_id": pegawai_id,
            "tanggal": today,
            "jam_masuk_kelas": now_time,
            "keterangan": ket
        }
        _upsert_row_in_sheets("riwayat_kelas", new_rk, key="id")
        msg = f"Berhasil! Presensi KE KELAS (Sesi {sesi_num}) tercatat pukul {now_time}. Keterangan: {ket}."
        
        _invalidate_cache()
        return True, msg, new_presensi

    # 3. JAM KEMBALI DARI KELAS
    elif action_type == "kembali_kelas":
        all_rk = _get_all_riwayat_kelas_raw()
        active_class = None
        for rk in all_rk:
            if (_safe_id(rk.get("pegawai_id")) == pegawai_id and
                _safe_text(rk.get("tanggal")) == today and
                not _safe_text(rk.get("jam_kembali_kelas"))):
                active_class = rk
                break

        if not active_class:
            count_sesi = len([r for r in all_rk if _safe_id(r.get("pegawai_id")) == pegawai_id and _safe_text(r.get("tanggal")) == today])
            if count_sesi > 0:
                return False, f"{pegawai_data['nama']} saat ini TIDAK sedang di kelas (semua {count_sesi} sesi kelas sebelumnya sudah selesai). Silakan klik 'Jam Ke Kelas' untuk memulai sesi baru.", dict(existing) if existing else None
            else:
                return False, f"{pegawai_data['nama']} belum tercatat melakukan presensi 'Jam Ke Kelas' hari ini.", None

        sesi_ke = len([r for r in all_rk if _safe_id(r.get("pegawai_id")) == pegawai_id and _safe_text(r.get("tanggal")) == today and _safe_id(r.get("id")) <= _safe_id(active_class.get("id"))])
        active_class["jam_kembali_kelas"] = now_time
        _upsert_row_in_sheets("riwayat_kelas", active_class, key="id")

        if existing:
            existing["jam_kembali_kelas"] = now_time
            existing["status"] = "Hadir di Lab"
            _upsert_row_in_sheets("presensi", existing, key="id")

        durasi_sesi = calculate_time_diff_hours(active_class.get("jam_masuk_kelas"), now_time)
        msg = f"Selamat Datang Kembali! Sesi Kelas #{sesi_ke} selesai pukul {now_time} (Durasi Sesi: {durasi_sesi})."
        
        _invalidate_cache()
        return True, msg, existing if existing else active_class

    # 4. JAM BERTUGAS KELUAR
    elif action_type == "tugas_keluar":
        if existing and _safe_text(existing.get("jam_bertugas_keluar")) and not _safe_text(existing.get("jam_kembali")):
            return False, f"{pegawai_data['nama']} saat ini masih tercatat SEDANG BERTUGAS KELUAR sejak pukul {existing['jam_bertugas_keluar']}. Silakan lakukan presensi 'Kembali Tugas' terlebih dahulu.", dict(existing) if existing else None

        ket = keterangan.strip() if keterangan.strip() else "Tugas Luar Kampus"
        if existing:
            existing["jam_masuk"] = _safe_text(existing.get("jam_masuk")) or now_time
            existing["jam_bertugas_keluar"] = now_time
            existing["jam_kembali"] = None
            existing["keterangan_tugas"] = ket
            existing["status"] = "Sedang Tugas Luar"
            _upsert_row_in_sheets("presensi", existing, key="id")
            presensi_id = _safe_id(existing.get("id"))
        else:
            presensi_id = len(all_presensi) + 1
            new_presensi = {
                "id": presensi_id,
                "pegawai_id": pegawai_id,
                "tanggal": today,
                "jam_masuk": now_time,
                "jam_bertugas_keluar": now_time,
                "keterangan_tugas": ket,
                "status": "Sedang Tugas Luar",
                "updated_at": get_wib_now().strftime("%Y-%m-%d %H:%M:%S")
            }
            _upsert_row_in_sheets("presensi", new_presensi, key="id")

        all_rt = _get_all_riwayat_tugas_raw()
        rt_id = len(all_rt) + 1
        new_rt = {
            "id": rt_id,
            "presensi_id": presensi_id,
            "pegawai_id": pegawai_id,
            "tanggal": today,
            "jam_keluar": now_time,
            "keterangan": ket
        }
        _upsert_row_in_sheets("riwayat_tugas_luar", new_rt, key="id")
        msg = f"Berhasil! Presensi TUGAS KELUAR tercatat pukul {now_time}. Keterangan: {ket}."
        
        _invalidate_cache()
        return True, msg, new_presensi

    # 5. JAM KEMBALI DARI TUGAS LUAR
    elif action_type == "kembali":
        if not existing or not _safe_text(existing.get("jam_bertugas_keluar")):
            return False, f"{pegawai_data['nama']} belum tercatat melakukan presensi 'Tugas Keluar' hari ini.", None
        if _safe_text(existing.get("jam_kembali")):
            return False, f"{pegawai_data['nama']} sudah mencatat jam KEMBALI TUGAS pukul {existing['jam_kembali']}.", dict(existing)

        existing["jam_kembali"] = now_time
        existing["status"] = "Hadir di Lab"
        _upsert_row_in_sheets("presensi", existing, key="id")

        all_rt = _get_all_riwayat_tugas_raw()
        for rt in all_rt:
            if (_safe_id(rt.get("presensi_id")) == _safe_id(existing.get("id")) and not _safe_text(rt.get("jam_kembali"))):
                rt["jam_kembali"] = now_time
                _upsert_row_in_sheets("riwayat_tugas_luar", rt, key="id")
                break

        msg = f"Selamat Datang Kembali! Presensi KEMBALI TUGAS tercatat pukul {now_time}."
        
        _invalidate_cache()
        return True, msg, existing

    # 6. JAM IZIN KELUAR
    elif action_type == "izin_keluar":
        if not existing or not _safe_text(existing.get("jam_masuk")):
            return False, f"{pegawai_data['nama']} belum melakukan presensi Masuk hari ini. Harus presensi Masuk terlebih dahulu sebelum Izin Keluar.", None
        if _safe_text(existing.get("jam_keluar")):
            return False, f"{pegawai_data['nama']} sudah melakukan presensi KELUAR/SELESAI hari ini pukul {existing['jam_keluar']}.", dict(existing)

        all_rk = _get_all_riwayat_kelas_raw()
        for rk in all_rk:
            if (_safe_id(rk.get("pegawai_id")) == pegawai_id and _safe_text(rk.get("tanggal")) == today and not _safe_text(rk.get("jam_kembali_kelas"))):
                return False, f"{pegawai_data['nama']} saat ini tercatat SEDANG DI KELAS. Selesaikan sesi kelas terlebih dahulu.", dict(existing)

        all_rt = _get_all_riwayat_tugas_raw()
        for rt in all_rt:
            if (_safe_id(rt.get("pegawai_id")) == pegawai_id and _safe_text(rt.get("tanggal")) == today and _safe_text(rt.get("jam_keluar")) and not _safe_text(rt.get("jam_kembali"))):
                return False, f"{pegawai_data['nama']} saat ini tercatat SEDANG TUGAS LUAR. Selesaikan tugas luar terlebih dahulu.", dict(existing)

        all_ri = _get_all_riwayat_izin_raw()
        for ri in all_ri:
            if (_safe_id(ri.get("pegawai_id")) == pegawai_id and _safe_text(ri.get("tanggal")) == today and not _safe_text(ri.get("jam_kembali_izin"))):
                return False, f"{pegawai_data['nama']} saat ini masih tercatat SEDANG IZIN KELUAR sejak pukul {ri['jam_izin_keluar']}. Silakan lakukan presensi 'Kembali Shift' terlebih dahulu.", dict(existing)

        sesi_izin_num = len(all_ri) + 1
        ket = keterangan.strip() if keterangan.strip() else f"Izin Keluar Sementara (Sesi #{sesi_izin_num})"

        existing["jam_izin_keluar"] = now_time
        existing["jam_kembali_izin"] = None
        existing["keterangan_izin"] = ket
        existing["status"] = "Sedang Izin Keluar"
        _upsert_row_in_sheets("presensi", existing, key="id")

        ri_id = len(all_ri) + 1
        new_ri = {
            "id": ri_id,
            "presensi_id": _safe_id(existing.get("id")),
            "pegawai_id": pegawai_id,
            "tanggal": today,
            "jam_izin_keluar": now_time,
            "keterangan": ket
        }
        _upsert_row_in_sheets("riwayat_izin", new_ri, key="id")
        msg = f"Berhasil! Presensi IZIN KELUAR tercatat pukul {now_time}. Keterangan: {ket}."
        
        _invalidate_cache()
        return True, msg, existing

    # 7. KEMBALI SHIFT (SELESAI IZIN KELUAR)
    elif action_type == "kembali_shift":
        all_ri = _get_all_riwayat_izin_raw()
        active_izin = None
        for ri in all_ri:
            if (_safe_id(ri.get("pegawai_id")) == pegawai_id and _safe_text(ri.get("tanggal")) == today and not _safe_text(ri.get("jam_kembali_izin"))):
                active_izin = ri
                break

        if not active_izin:
            return False, f"{pegawai_data['nama']} saat ini TIDAK sedang izin keluar.", dict(existing) if existing else None

        active_izin["jam_kembali_izin"] = now_time
        _upsert_row_in_sheets("riwayat_izin", active_izin, key="id")
        durasi_izin = calculate_time_diff_hours(active_izin.get("jam_izin_keluar"), now_time)

        if existing:
            existing["jam_kembali_izin"] = now_time
            existing["status"] = "Hadir di Lab"
            _upsert_row_in_sheets("presensi", existing, key="id")

        msg = f"Selamat Datang Kembali! Selesai Izin Keluar pukul {now_time} (Durasi Izin: {durasi_izin}). Shift dilanjutkan."
        
        _invalidate_cache()
        return True, msg, existing if existing else active_izin

    # 8. JAM KELUAR / SELESAI
    elif action_type == "keluar":
        if existing and _safe_text(existing.get("jam_keluar")):
            return False, f"{pegawai_data['nama']} sudah melakukan presensi KELUAR/SELESAI hari ini pukul {existing['jam_keluar']}.", dict(existing)

        if existing:
            existing["jam_keluar"] = now_time
            existing["status"] = "Sudah Pulang"
            existing["updated_at"] = get_wib_now().strftime("%Y-%m-%d %H:%M:%S")
            _upsert_row_in_sheets("presensi", existing, key="id")

            all_rk = _get_all_riwayat_kelas_raw()
            for rk in all_rk:
                if (_safe_id(rk.get("presensi_id")) == _safe_id(existing.get("id")) and not _safe_text(rk.get("jam_kembali_kelas"))):
                    rk["jam_kembali_kelas"] = now_time
                    _upsert_row_in_sheets("riwayat_kelas", rk, key="id")

            all_rt = _get_all_riwayat_tugas_raw()
            for rt in all_rt:
                if (_safe_id(rt.get("presensi_id")) == _safe_id(existing.get("id")) and _safe_text(rt.get("jam_keluar")) and not _safe_text(rt.get("jam_kembali"))):
                    rt["jam_kembali"] = now_time
                    _upsert_row_in_sheets("riwayat_tugas_luar", rt, key="id")

            all_ri = _get_all_riwayat_izin_raw()
            for ri in all_ri:
                if (_safe_id(ri.get("presensi_id")) == _safe_id(existing.get("id")) and _safe_text(ri.get("jam_izin_keluar")) and not _safe_text(ri.get("jam_kembali_izin"))):
                    ri["jam_kembali_izin"] = now_time
                    _upsert_row_in_sheets("riwayat_izin", ri, key="id")
        else:
            presensi_id = len(all_presensi) + 1
            new_presensi = {
                "id": presensi_id,
                "pegawai_id": pegawai_id,
                "tanggal": today,
                "jam_masuk": now_time,
                "jam_keluar": now_time,
                "status": "Sudah Pulang",
                "updated_at": get_wib_now().strftime("%Y-%m-%d %H:%M:%S")
            }
            _upsert_row_in_sheets("presensi", new_presensi, key="id")

        jam_masuk_awal = _safe_text(existing.get("jam_masuk")) if existing else now_time
        all_rk_closed = [r for r in _get_all_riwayat_kelas_raw() if _safe_id(r.get("presensi_id")) == (existing.get("id") if existing else presensi_id)]
        all_ri_closed = [r for r in _get_all_riwayat_izin_raw() if _safe_id(r.get("presensi_id")) == (existing.get("id") if existing else presensi_id)]
        shift_dur = calculate_durasi_shift(jam_masuk_awal, now_time, riwayat_kelas_list=all_rk_closed, riwayat_izin_list=all_ri_closed)

        msg = f"Sampai Jumpa! Presensi KELUAR / SELESAI tercatat pukul {now_time}"
        if shift_dur != "-":
            msg += f" (Durasi Shift: {shift_dur})."
        else:
            msg += "."
        
        _invalidate_cache()
        return True, msg, existing if existing else new_presensi

    else:
        return False, "Aksi presensi tidak valid!", None


# ===================== SUMMARY & STATISTIK =====================

def get_today_summary():
    """Ringkasan presensi hari ini."""
    today = get_today_str()
    all_pegawai = _get_all_pegawai_raw()
    all_presensi = _get_all_presensi_raw()

    total_pegawai = len([p for p in all_pegawai if _safe_int(p.get("status_aktif"), 1) == 1])

    hadir = 0
    sedang_kelas = 0
    tugas_luar = 0
    sedang_izin = 0
    pulang = 0

    for p in all_presensi:
        if _safe_text(p.get("tanggal")) != today:
            continue
        if _safe_text(p.get("jam_keluar")):
            pulang += 1
        elif _safe_text(p.get("status")) == "Sedang di Kelas":
            sedang_kelas += 1
        elif _safe_text(p.get("status")) == "Sedang Izin Keluar":
            sedang_izin += 1
        elif _safe_text(p.get("jam_bertugas_keluar")) and not _safe_text(p.get("jam_kembali")):
            tugas_luar += 1
        elif _safe_text(p.get("jam_masuk")) or _safe_text(p.get("jam_kembali")) or _safe_text(p.get("jam_kembali_kelas")) or _safe_text(p.get("jam_kembali_izin")):
            hadir += 1

    belum_absen = max(0, total_pegawai - (hadir + sedang_kelas + tugas_luar + sedang_izin + pulang))

    return {
        "total_pegawai": total_pegawai,
        "hadir": hadir,
        "sedang_kelas": sedang_kelas,
        "tugas_luar": tugas_luar,
        "sedang_izin": sedang_izin,
        "pulang": pulang,
        "belum_absen": belum_absen,
        "tanggal": today
    }


def get_today_presence_table():
    """Tabel presensi hari ini dengan data lengkap dari Google Sheets."""
    today = get_today_str()
    all_pegawai = _get_all_pegawai_raw()
    all_presensi = _get_all_presensi_raw()
    all_rk = _get_all_riwayat_kelas_raw()
    all_ri = _get_all_riwayat_izin_raw()
    all_rt = _get_all_riwayat_tugas_raw()

    # Buat map pegawai aktif
    pegawai_map = {}
    for p in all_pegawai:
        if _safe_int(p.get("status_aktif"), 1) == 1:
            pegawai_map[_safe_id(p.get("id"))] = p

    rows = []
    for p in all_presensi:
        if _safe_text(p.get("tanggal")) != today:
            continue
        pid = _safe_id(p.get("pegawai_id"))
        if pid not in pegawai_map:
            continue
        pg = pegawai_map[pid]

        row = {
            "pegawai_id": pid,
            "nik": _safe_text(pg.get("nik")),
            "nama": _safe_text(pg.get("nama")),
            "jabatan": _safe_text(pg.get("jabatan"), "Mahasiswa"),
            "departemen": _safe_text(pg.get("departemen"), "Pendidikan Matematika"),
            "presensi_id": _safe_id(p.get("id")),
            "tanggal": _safe_text(p.get("tanggal")),
            "jam_masuk": _safe_text(p.get("jam_masuk")),
            "jam_masuk_kelas": _safe_text(p.get("jam_masuk_kelas")),
            "jam_kembali_kelas": _safe_text(p.get("jam_kembali_kelas")),
            "keterangan_kelas": _safe_text(p.get("keterangan_kelas")),
            "jam_bertugas_keluar": _safe_text(p.get("jam_bertugas_keluar")),
            "jam_kembali": _safe_text(p.get("jam_kembali")),
            "jam_izin_keluar": _safe_text(p.get("jam_izin_keluar")),
            "jam_kembali_izin": _safe_text(p.get("jam_kembali_izin")),
            "keterangan_izin": _safe_text(p.get("keterangan_izin")),
            "status": _safe_text(p.get("status"), "Hadir"),
            "catatan": _safe_text(p.get("catatan")),
            "updated_at": _safe_text(p.get("updated_at"))
        }

        # Riwayat kelas dan izin dari cache
        rk_list = []
        for rk in all_rk:
            if _safe_id(rk.get("presensi_id")) == row["presensi_id"]:
                rk_list.append({
                    "id": _safe_id(rk.get("id")),
                    "presensi_id": _safe_id(rk.get("presensi_id")),
                    "pegawai_id": _safe_id(rk.get("pegawai_id")),
                    "tanggal": _safe_text(rk.get("tanggal")),
                    "jam_masuk_kelas": _safe_text(rk.get("jam_masuk_kelas")),
                    "jam_kembali_kelas": _safe_text(rk.get("jam_kembali_kelas")),
                    "keterangan": _safe_text(rk.get("keterangan")),
                    "created_at": _safe_text(rk.get("created_at"))
                })
        ri_list = []
        for ri in all_ri:
            if _safe_id(ri.get("presensi_id")) == row["presensi_id"]:
                ri_list.append({
                    "id": _safe_id(ri.get("id")),
                    "presensi_id": _safe_id(ri.get("presensi_id")),
                    "pegawai_id": _safe_id(ri.get("pegawai_id")),
                    "tanggal": _safe_text(ri.get("tanggal")),
                    "jam_izin_keluar": _safe_text(ri.get("jam_izin_keluar")),
                    "jam_kembali_izin": _safe_text(ri.get("jam_kembali_izin")),
                    "keterangan": _safe_text(ri.get("keterangan")),
                    "created_at": _safe_text(ri.get("created_at"))
                })

        row["riwayat_kelas_list"] = rk_list
        row["total_sesi_kelas"] = len(rk_list)
        row["ringkasan_kelas"] = format_kelas_summary(rk_list)
        row["display_jam_kelas"] = format_kelas_time_display(rk_list)
        row["durasi_total_kelas"] = calculate_total_kelas_duration(rk_list)
        row["riwayat_izin_list"] = ri_list
        row["total_sesi_izin"] = len(ri_list)
        row["ringkasan_izin"] = format_izin_summary(ri_list)
        row["display_jam_izin"] = format_izin_time_display(ri_list)
        row["durasi_total_izin"] = calculate_total_izin_duration(ri_list)
        row["total_durasi"] = calculate_time_diff_hours(row.get("jam_masuk"), row.get("jam_keluar"))
        row["durasi_shift"] = calculate_durasi_shift(
            row.get("jam_masuk"), row.get("jam_keluar"),
            riwayat_kelas_list=rk_list, riwayat_izin_list=ri_list
        )
        rows.append(row)

    # Sort: Sedang di Kelas > Sedang Tugas > Sedang Izin > Hadir > Pulang
    def sort_key(r):
        status = r.get("status", "")
        if status == "Sedang di Kelas": return 1
        if status == "Sedang Tugas Luar": return 2
        if status == "Sedang Izin Keluar": return 3
        if r.get("jam_masuk") and not r.get("jam_keluar"): return 4
        if r.get("jam_keluar"): return 5
        return 6
    rows.sort(key=sort_key)
    rows.sort(key=lambda x: x.get("nama", ""))

    return rows


def get_presensi_history(start_date=None, end_date=None, pegawai_id=None, departemen=None, search=None):
    """Riwayat presensi dengan filter dari Google Sheets."""
    all_pegawai = _get_all_pegawai_raw()
    all_presensi = _get_all_presensi_raw()
    all_rk = _get_all_riwayat_kelas_raw()
    all_ri = _get_all_riwayat_izin_raw()

    # Filter pegawai
    filtered_pegawai = {}
    for p in all_pegawai:
        pid = _safe_id(p.get("id"))
        if departemen and departemen != "Semua Program Studi":
            if _safe_text(p.get("departemen")) != departemen:
                continue
        filtered_pegawai[pid] = p

    rows = []
    for p in all_presensi:
        pid = _safe_id(p.get("pegawai_id"))
        if pid not in filtered_pegawai:
            continue
        tanggal = _safe_text(p.get("tanggal"))
        if start_date and tanggal < start_date:
            continue
        if end_date and tanggal > end_date:
            continue
        if pegawai_id and pid != pegawai_id:
            continue
        if search:
            sq = search.strip().lower()
            pg = filtered_pegawai[pid]
            if sq not in _safe_text(pg.get("nama")).lower() and sq not in _safe_text(pg.get("nik")).lower():
                continue

        pg = filtered_pegawai[pid]
        row = {
            "presensi_id": _safe_id(p.get("id")),
            "tanggal": tanggal,
            "jam_masuk": _safe_text(p.get("jam_masuk")),
            "jam_masuk_kelas": _safe_text(p.get("jam_masuk_kelas")),
            "jam_kembali_kelas": _safe_text(p.get("jam_kembali_kelas")),
            "keterangan_kelas": _safe_text(p.get("keterangan_kelas")),
            "jam_bertugas_keluar": _safe_text(p.get("jam_bertugas_keluar")),
            "jam_kembali": _safe_text(p.get("jam_kembali")),
            "jam_izin_keluar": _safe_text(p.get("jam_izin_keluar")),
            "jam_kembali_izin": _safe_text(p.get("jam_kembali_izin")),
            "keterangan_izin": _safe_text(p.get("keterangan_izin")),
            "status": _safe_text(p.get("status"), "Hadir"),
            "catatan": _safe_text(p.get("catatan")),
            "pegawai_id": pid,
            "nik": _safe_text(pg.get("nik")),
            "nama": _safe_text(pg.get("nama")),
            "jabatan": _safe_text(pg.get("jabatan"), "Mahasiswa"),
            "departemen": _safe_text(pg.get("departemen"), "Pendidikan Matematika")
        }

        rk_list = [r for r in all_rk if _safe_id(r.get("presensi_id")) == row["presensi_id"]]
        ri_list = [r for r in all_ri if _safe_id(r.get("presensi_id")) == row["presensi_id"]]
        row["riwayat_kelas_list"] = rk_list
        row["total_sesi_kelas"] = len(rk_list)
        row["ringkasan_kelas"] = format_kelas_summary(rk_list)
        row["display_jam_kelas"] = format_kelas_time_display(rk_list)
        row["durasi_total_kelas"] = calculate_total_kelas_duration(rk_list)
        row["riwayat_izin_list"] = ri_list
        row["total_sesi_izin"] = len(ri_list)
        row["ringkasan_izin"] = format_izin_summary(ri_list)
        row["display_jam_izin"] = format_izin_time_display(ri_list)
        row["durasi_total_izin"] = calculate_total_izin_duration(ri_list)
        row["total_durasi"] = calculate_time_diff_hours(row.get("jam_masuk"), row.get("jam_keluar"))
        row["durasi_shift"] = calculate_durasi_shift(
            row.get("jam_masuk"), row.get("jam_keluar"),
            riwayat_kelas_list=rk_list, riwayat_izin_list=ri_list
        )
        rows.append(row)

    rows.sort(key=lambda x: (x.get("tanggal", ""), x.get("jam_masuk", "")))
    rows.reverse()
    return rows


# ===================== PERHITUNGAN DURASI =====================

def calculate_time_diff_hours(time_start_str, time_end_str):
    """Menghitung selisih waktu dalam format 'Xj Ym'."""
    if not time_start_str or not time_end_str:
        return "-"
    try:
        t1 = datetime.datetime.strptime(time_start_str, "%H:%M:%S")
        t2 = datetime.datetime.strptime(time_end_str, "%H:%M:%S")
        if t2 < t1:
            return "-"
        diff = t2 - t1
        total_seconds = int(diff.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}j {minutes}m"
    except Exception:
        return "-"


def parse_duration_to_seconds(dur_str):
    """Mengubah format durasi 'Xj Ym' menjadi total detik."""
    if not dur_str or dur_str == "-":
        return 0
    try:
        import re
        hours = 0
        minutes = 0
        h_match = re.search(r'(\d+)\s*(?:j|jam)', dur_str, re.IGNORECASE)
        if h_match:
            hours = int(h_match.group(1))
        m_match = re.search(r'(\d+)\s*(?:m|menit)', dur_str, re.IGNORECASE)
        if m_match:
            minutes = int(m_match.group(1))
        return hours * 3600 + minutes * 60
    except Exception:
        return 0


def calculate_durasi_shift(time_start_str, time_end_str, riwayat_kelas_list=None, durasi_kelas_str=None, riwayat_izin_list=None, durasi_izin_str=None):
    """
    Menghitung durasi shift: Total durasi kehadiran dikurangi total durasi kelas dan izin.
    """
    if not time_start_str or not time_end_str:
        return "-"
    try:
        t1 = datetime.datetime.strptime(time_start_str, "%H:%M:%S")
        t2 = datetime.datetime.strptime(time_end_str, "%H:%M:%S")
        if t2 < t1:
            return "-"
        total_seconds = int((t2 - t1).total_seconds())

        kelas_seconds = 0
        if riwayat_kelas_list is not None:
            for r in riwayat_kelas_list:
                s_str = r.get("jam_masuk_kelas")
                e_str = r.get("jam_kembali_kelas")
                if s_str and e_str:
                    try:
                        k1 = datetime.datetime.strptime(s_str, "%H:%M:%S")
                        k2 = datetime.datetime.strptime(e_str, "%H:%M:%S")
                        if k2 >= k1:
                            kelas_seconds += int((k2 - k1).total_seconds())
                    except Exception:
                        pass
        elif durasi_kelas_str:
            kelas_seconds = parse_duration_to_seconds(durasi_kelas_str)

        izin_seconds = 0
        if riwayat_izin_list is not None:
            for r in riwayat_izin_list:
                s_str = r.get("jam_izin_keluar")
                e_str = r.get("jam_kembali_izin")
                if s_str and e_str:
                    try:
                        i1 = datetime.datetime.strptime(s_str, "%H:%M:%S")
                        i2 = datetime.datetime.strptime(e_str, "%H:%M:%S")
                        if i2 >= i1:
                            izin_seconds += int((i2 - i1).total_seconds())
                    except Exception:
                        pass
        elif durasi_izin_str:
            izin_seconds = parse_duration_to_seconds(durasi_izin_str)

        shift_seconds = max(0, total_seconds - kelas_seconds - izin_seconds)
        hours = shift_seconds // 3600
        minutes = (shift_seconds % 3600) // 60
        return f"{hours}j {minutes}m"
    except Exception:
        return "-"
