"""Sinkronisasi dua arah SQLite <-> Google Sheets melalui Apps Script webhook."""
import logging
import sqlite3
import requests
from config import DB_PATH, load_config, save_config

logger = logging.getLogger("sheets_sync")


def get_webhook_url():
    """Ambil URL webhook dari Streamlit Secrets atau config.json."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "gsheets_webhook_url" in st.secrets:
            value = str(st.secrets["gsheets_webhook_url"]).strip()
            if value:
                return value
    except Exception:
        pass
    return str(load_config().get("gsheets_webhook_url", "") or "").strip()


def is_from_secrets():
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "gsheets_webhook_url" in st.secrets:
            return bool(str(st.secrets["gsheets_webhook_url"]).strip())
    except Exception:
        pass
    return False


def set_webhook_url(url):
    cfg = load_config()
    cfg["gsheets_webhook_url"] = str(url or "").strip()
    return save_config(cfg)


def is_sheets_enabled():
    url = get_webhook_url()
    return bool(url and url.lower().startswith(("http://", "https://")))


def _response_json(resp):
    """Parse JSON dengan pesan error yang jelas jika Apps Script mengirim respons non-JSON."""
    try:
        return resp.json()
    except ValueError as exc:
        preview = (resp.text or "").strip().replace("\n", " ")[:300]
        raise ValueError(f"Respons webhook bukan JSON: {preview or 'kosong'}") from exc


def test_connection():
    url = get_webhook_url()
    if not url:
        return False, "URL Webhook Google Sheets belum diatur."
    try:
        resp = requests.get(url, params={"action": "ping"}, timeout=15)
        if resp.status_code != 200:
            return False, f"Server merespon dengan status code: {resp.status_code}"
        data = _response_json(resp)
        if data.get("status") == "success":
            return True, f"Berhasil terhubung ke: {data.get('title', 'Google Sheets')}"
        return False, str(data.get("message", "Respon dari Google Sheets tidak valid."))
    except requests.RequestException as exc:
        return False, f"Gagal menghubungi Google Sheets: {exc}"
    except Exception as exc:
        logger.exception("test_connection gagal")
        return False, f"Gagal memeriksa koneksi Sheets: {exc}"


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


def _table_rows(data, key):
    value = data.get(key, [])
    return value if isinstance(value, list) else []


def pull_from_sheets():
    """Tarik semua tabel dari Sheets ke SQLite secara atomik."""
    url = get_webhook_url()
    if not url:
        return False, "URL Webhook Google Sheets belum disetel.", {}

    conn = None
    try:
        resp = requests.get(url, params={"action": "get_all"}, timeout=30)
        if resp.status_code != 200:
            return False, f"Gagal mengambil data dari Google Sheets (HTTP {resp.status_code})", {}

        res_json = _response_json(resp)
        if res_json.get("status") != "success":
            return False, str(res_json.get("message", "Error pada Google Sheets")), {}

        data = res_json.get("data") or {}
        if not isinstance(data, dict):
            return False, "Format data Google Sheets tidak valid.", {}

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Pastikan tabel/kolom terbaru sudah tersedia ketika fungsi dipanggil langsung.
        try:
            import database
            database.init_db()
        except Exception:
            pass

        stats = {}

        # 1. Pegawai harus masuk lebih dahulu karena tabel lain memakai pegawai_id.
        mhs_list = _table_rows(data, "mahasiswa")
        for m in mhs_list:
            mid = _safe_id(m.get("id"))
            if mid is None or not _safe_text(m.get("nama")):
                logger.warning("Melewati data mahasiswa tanpa id/nama: %r", m)
                continue
            nik = _safe_text(m.get("nik")) or f"MHS-{int(mid):03d}" if isinstance(mid, int) else f"MHS-{mid}"
            cursor.execute("""
                INSERT INTO pegawai (id, nik, nama, jabatan, departemen, telepon, email, status_aktif, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    nik=excluded.nik, nama=excluded.nama, jabatan=excluded.jabatan,
                    departemen=excluded.departemen, telepon=excluded.telepon,
                    email=excluded.email, status_aktif=excluded.status_aktif
            """, (
                mid, nik, _safe_text(m.get("nama")),
                _safe_text(m.get("jabatan"), "Mahasiswa"),
                _safe_text(m.get("departemen"), "Pendidikan Matematika"),
                _safe_text(m.get("telepon")), _safe_text(m.get("email")),
                _safe_int(m.get("status_aktif"), 1),
                _safe_text(m.get("created_at")) or None
            ))
        stats["mahasiswa"] = len(mhs_list)

        # 2. Presensi.
        p_list = _table_rows(data, "presensi")
        for p in p_list:
            pid = _safe_id(p.get("id"))
            pegawai_id = _safe_id(p.get("pegawai_id"))
            tanggal = _safe_text(p.get("tanggal"))
            if pid is None or pegawai_id is None or not tanggal:
                logger.warning("Melewati presensi tidak lengkap: %r", p)
                continue
            cursor.execute("""
                INSERT INTO presensi (
                    id, pegawai_id, tanggal, jam_masuk, jam_masuk_kelas, jam_kembali_kelas,
                    keterangan_kelas, jam_bertugas_keluar, jam_kembali, jam_izin_keluar,
                    jam_kembali_izin, keterangan_izin, jam_keluar, keterangan_tugas,
                    status, catatan, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pegawai_id, tanggal) DO UPDATE SET
                    jam_masuk=excluded.jam_masuk, jam_masuk_kelas=excluded.jam_masuk_kelas,
                    jam_kembali_kelas=excluded.jam_kembali_kelas, keterangan_kelas=excluded.keterangan_kelas,
                    jam_bertugas_keluar=excluded.jam_bertugas_keluar, jam_kembali=excluded.jam_kembali,
                    jam_izin_keluar=excluded.jam_izin_keluar, jam_kembali_izin=excluded.jam_kembali_izin,
                    keterangan_izin=excluded.keterangan_izin, jam_keluar=excluded.jam_keluar,
                    keterangan_tugas=excluded.keterangan_tugas, status=excluded.status,
                    catatan=excluded.catatan, updated_at=excluded.updated_at
            """, (
                pid, pegawai_id, tanggal,
                p.get("jam_masuk") or None, p.get("jam_masuk_kelas") or None,
                p.get("jam_kembali_kelas") or None, p.get("keterangan_kelas") or None,
                p.get("jam_bertugas_keluar") or None, p.get("jam_kembali") or None,
                p.get("jam_izin_keluar") or None, p.get("jam_kembali_izin") or None,
                p.get("keterangan_izin") or None, p.get("jam_keluar") or None,
                p.get("keterangan_tugas") or None, _safe_text(p.get("status"), "Hadir"),
                p.get("catatan") or None, p.get("updated_at") or None
            ))
        stats["presensi"] = len(p_list)

        # 3-5. Tabel detail. Jika data lama punya foreign key yang tidak cocok, tampilkan error
        # yang jelas dan batalkan seluruh pull agar database lokal tidak setengah tersinkron.
        detail_specs = [
            ("riwayat_kelas", "INSERT INTO riwayat_kelas (id,presensi_id,pegawai_id,tanggal,jam_masuk_kelas,jam_kembali_kelas,keterangan,created_at) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET jam_kembali_kelas=excluded.jam_kembali_kelas,keterangan=excluded.keterangan", "jam_masuk_kelas"),
            ("riwayat_izin", "INSERT INTO riwayat_izin (id,presensi_id,pegawai_id,tanggal,jam_izin_keluar,jam_kembali_izin,keterangan,created_at) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET jam_kembali_izin=excluded.jam_kembali_izin,keterangan=excluded.keterangan", "jam_izin_keluar"),
            ("riwayat_tugas_luar", "INSERT INTO riwayat_tugas_luar (id,presensi_id,pegawai_id,tanggal,jam_keluar,jam_kembali,keterangan,created_at) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET jam_kembali=excluded.jam_kembali,keterangan=excluded.keterangan", "jam_keluar")
        ]
        for table, sql, required_field in detail_specs:
            rows = _table_rows(data, table)
            for r in rows:
                rid = _safe_id(r.get("id")); pegawai_id = _safe_id(r.get("pegawai_id"))
                tanggal = _safe_text(r.get("tanggal")); required = r.get(required_field)
                if rid is None or pegawai_id is None or not tanggal or not required:
                    logger.warning("Melewati %s tidak lengkap: %r", table, r)
                    continue
                cursor.execute(sql, (
                    rid, _safe_id(r.get("presensi_id")), pegawai_id, tanggal,
                    required, r.get("jam_kembali_kelas") if table == "riwayat_kelas" else r.get("jam_kembali_izin") if table == "riwayat_izin" else r.get("jam_kembali"),
                    r.get("keterangan"), r.get("created_at") or None
                ))
            stats[table] = len(rows)

        conn.commit()
        return True, "Data dari Google Sheets berhasil disinkronkan ke lokal.", stats
    except requests.RequestException as exc:
        if conn:
            conn.rollback()
        return False, f"Tidak dapat menghubungi Google Sheets: {exc}", {}
    except Exception as exc:
        if conn:
            conn.rollback()
        logger.exception("pull_from_sheets gagal")
        return False, f"Terjadi kesalahan saat menarik data: {exc}", {}
    finally:
        if conn:
            conn.close()


def push_all_to_sheets():
    url = get_webhook_url()
    if not url:
        return False, "URL Webhook Google Sheets belum diatur."
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        tables_data = {}
        for db_tbl, sheet_name in [
            ("pegawai", "mahasiswa"), ("presensi", "presensi"),
            ("riwayat_kelas", "riwayat_kelas"), ("riwayat_izin", "riwayat_izin"),
            ("riwayat_tugas_luar", "riwayat_tugas_luar")
        ]:
            cur.execute(f"SELECT * FROM {db_tbl}")
            tables_data[sheet_name] = [dict(r) for r in cur.fetchall()]
        conn.close()
        resp = requests.post(url, json={"action": "sync_all", "tables": tables_data}, timeout=30)
        if resp.status_code != 200:
            return False, f"Google Sheets merespon HTTP {resp.status_code}"
        data = _response_json(resp)
        if data.get("status") == "success":
            return True, "Seluruh data lokal berhasil dimigrasikan ke Google Sheets!"
        return False, str(data.get("message", "Gagal melakukan sync_all."))
    except Exception as exc:
        logger.exception("push_all_to_sheets gagal")
        return False, f"Gagal mengirim data ke Google Sheets: {exc}"


def sync_row_async(table_name, row_dict, key="id"):
    if not is_sheets_enabled():
        return False
    try:
        requests.post(get_webhook_url(), json={"action":"upsert_row","table":table_name,"key":key,"row":row_dict}, timeout=5)
        return True
    except Exception as exc:
        logger.warning("Gagal menyinkronkan baris ke Sheets: %s", exc)
        return False


def sync_delete_async(table_name, key="id", value=None):
    if not is_sheets_enabled():
        return False
    try:
        requests.post(get_webhook_url(), json={"action":"delete_row","table":table_name,"key":key,"value":value}, timeout=5)
        return True
    except Exception as exc:
        logger.warning("Gagal menghapus baris di Sheets: %s", exc)
        return False
