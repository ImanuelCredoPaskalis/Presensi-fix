"""
Google Sheets Synchronization Module
Menyediakan komunikasi dua arah antara Database SQLite lokal dan Google Sheets (via Google Apps Script Webhook atau Google Sheets API).
Memastikan presensi di Streamlit Cloud tercatat permanen di Google Sheets secara real-time.
"""
import json
import logging
import sqlite3
import requests
from config import DB_PATH, load_config, save_config

logger = logging.getLogger("sheets_sync")

def get_webhook_url():
    """
    Mendapatkan Webhook URL dari config.json, Streamlit secrets, atau Environment.
    """
    # Coba dari streamlit secrets jika sedang berjalan di Streamlit
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "gsheets_webhook_url" in st.secrets:
            return st.secrets["gsheets_webhook_url"]
    except Exception:
        pass

    # Coba dari config.json
    cfg = load_config()
    return cfg.get("gsheets_webhook_url", "").strip()

def is_from_secrets():
    """
    Mengecek apakah Webhook URL dikonfigurasi melalui Streamlit Secrets (bukan config.json lokal).
    """
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "gsheets_webhook_url" in st.secrets:
            return bool(str(st.secrets["gsheets_webhook_url"]).strip())
    except Exception:
        pass
    return False

def set_webhook_url(url):
    """
    Menyimpan Webhook URL ke config.json.
    """
    cfg = load_config()
    cfg["gsheets_webhook_url"] = url.strip()
    return save_config(cfg)

def is_sheets_enabled():
    """
    Mengecek apakah sinkronisasi Google Sheets aktif.
    """
    url = get_webhook_url()
    return bool(url and url.startswith("http"))

def test_connection():
    """
    Menguji koneksi ke Google Sheets Webhook.
    """
    url = get_webhook_url()
    if not url:
        return False, "URL Webhook Google Sheets belum diatur."
    
    try:
        resp = requests.get(url, params={"action": "ping"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                title = data.get("title", "Google Sheets")
                return True, f"Berhasil terhubung ke: {title}"
            return False, data.get("message", "Respon dari Google Sheets tidak valid.")
        return False, f"Server merespon dengan status code: {resp.status_code}"
    except Exception as e:
        return False, f"Gagal menghubungi Google Sheets: {str(e)}"

def pull_from_sheets():
    """
    Menarik seluruh data dari Google Sheets dan menyimpannya ke database SQLite lokal.
    """
    url = get_webhook_url()
    if not url:
        return False, "URL Webhook Google Sheets belum disetel.", {}

    try:
        resp = requests.get(url, params={"action": "get_all"}, timeout=20)
        if resp.status_code != 200:
            return False, f"Gagal mengambil data dari Google Sheets (HTTP {resp.status_code})", {}

        res_json = resp.json()
        if res_json.get("status") != "success":
            return False, res_json.get("message", "Error pada Google Sheets"), {}

        data = res_json.get("data", {})
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        stats = {}

        # 1. Mahasiswa / Pegawai
        if "mahasiswa" in data and data["mahasiswa"]:
            mhs_list = data["mahasiswa"]
            stats["mahasiswa"] = len(mhs_list)
            for m in mhs_list:
                cursor.execute("""
                    INSERT INTO pegawai (id, nik, nama, jabatan, departemen, telepon, email, status_aktif, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        nik = excluded.nik,
                        nama = excluded.nama,
                        jabatan = excluded.jabatan,
                        departemen = excluded.departemen,
                        telepon = excluded.telepon,
                        status_aktif = excluded.status_aktif
                """, (
                    m.get("id"),
                    m.get("nik", f"MHS-{m.get('id', 1):03d}"),
                    m.get("nama"),
                    m.get("jabatan", "Mahasiswa"),
                    m.get("departemen", "Pendidikan Matematika"),
                    m.get("telepon", ""),
                    m.get("email", ""),
                    int(m.get("status_aktif", 1)),
                    m.get("created_at", "")
                ))

        # 2. Presensi
        if "presensi" in data and data["presensi"]:
            p_list = data["presensi"]
            stats["presensi"] = len(p_list)
            for p in p_list:
                cursor.execute("""
                    INSERT INTO presensi (
                        id, pegawai_id, tanggal, jam_masuk, jam_masuk_kelas, jam_kembali_kelas, 
                        keterangan_kelas, jam_bertugas_keluar, jam_kembali, jam_izin_keluar, 
                        jam_kembali_izin, keterangan_izin, jam_keluar, keterangan_tugas, status, catatan, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(pegawai_id, tanggal) DO UPDATE SET
                        jam_masuk = excluded.jam_masuk,
                        jam_masuk_kelas = excluded.jam_masuk_kelas,
                        jam_kembali_kelas = excluded.jam_kembali_kelas,
                        keterangan_kelas = excluded.keterangan_kelas,
                        jam_bertugas_keluar = excluded.jam_bertugas_keluar,
                        jam_kembali = excluded.jam_kembali,
                        jam_izin_keluar = excluded.jam_izin_keluar,
                        jam_kembali_izin = excluded.jam_kembali_izin,
                        keterangan_izin = excluded.keterangan_izin,
                        jam_keluar = excluded.jam_keluar,
                        keterangan_tugas = excluded.keterangan_tugas,
                        status = excluded.status,
                        catatan = excluded.catatan,
                        updated_at = excluded.updated_at
                """, (
                    p.get("id"),
                    p.get("pegawai_id"),
                    p.get("tanggal"),
                    p.get("jam_masuk") or None,
                    p.get("jam_masuk_kelas") or None,
                    p.get("jam_kembali_kelas") or None,
                    p.get("keterangan_kelas") or None,
                    p.get("jam_bertugas_keluar") or None,
                    p.get("jam_kembali") or None,
                    p.get("jam_izin_keluar") or None,
                    p.get("jam_kembali_izin") or None,
                    p.get("keterangan_izin") or None,
                    p.get("jam_keluar") or None,
                    p.get("keterangan_tugas") or None,
                    p.get("status") or "Hadir",
                    p.get("catatan") or None,
                    p.get("updated_at") or None
                ))

        # 3. Riwayat Kelas
        if "riwayat_kelas" in data and data["riwayat_kelas"]:
            rk_list = data["riwayat_kelas"]
            stats["riwayat_kelas"] = len(rk_list)
            for rk in rk_list:
                cursor.execute("""
                    INSERT INTO riwayat_kelas (id, presensi_id, pegawai_id, tanggal, jam_masuk_kelas, jam_kembali_kelas, keterangan, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        jam_kembali_kelas = excluded.jam_kembali_kelas,
                        keterangan = excluded.keterangan
                """, (
                    rk.get("id"),
                    rk.get("presensi_id"),
                    rk.get("pegawai_id"),
                    rk.get("tanggal"),
                    rk.get("jam_masuk_kelas"),
                    rk.get("jam_kembali_kelas") or None,
                    rk.get("keterangan") or None,
                    rk.get("created_at") or None
                ))

        # 4. Riwayat Izin
        if "riwayat_izin" in data and data["riwayat_izin"]:
            ri_list = data["riwayat_izin"]
            stats["riwayat_izin"] = len(ri_list)
            for ri in ri_list:
                cursor.execute("""
                    INSERT INTO riwayat_izin (id, presensi_id, pegawai_id, tanggal, jam_izin_keluar, jam_kembali_izin, keterangan, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        jam_kembali_izin = excluded.jam_kembali_izin,
                        keterangan = excluded.keterangan
                """, (
                    ri.get("id"),
                    ri.get("presensi_id"),
                    ri.get("pegawai_id"),
                    ri.get("tanggal"),
                    ri.get("jam_izin_keluar"),
                    ri.get("jam_kembali_izin") or None,
                    ri.get("keterangan") or None,
                    ri.get("created_at") or None
                ))

        # 5. Riwayat Tugas Luar
        if "riwayat_tugas_luar" in data and data["riwayat_tugas_luar"]:
            rt_list = data["riwayat_tugas_luar"]
            stats["riwayat_tugas_luar"] = len(rt_list)
            for rt in rt_list:
                cursor.execute("""
                    INSERT INTO riwayat_tugas_luar (id, presensi_id, pegawai_id, tanggal, jam_keluar, jam_kembali, keterangan, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        jam_kembali = excluded.jam_kembali,
                        keterangan = excluded.keterangan
                """, (
                    rt.get("id"),
                    rt.get("presensi_id"),
                    rt.get("pegawai_id"),
                    rt.get("tanggal"),
                    rt.get("jam_keluar"),
                    rt.get("jam_kembali") or None,
                    rt.get("keterangan") or None,
                    rt.get("created_at") or None
                ))

        conn.commit()
        conn.close()
        return True, "Data dari Google Sheets berhasil disinkronkan ke lokal.", stats
    except Exception as e:
        return False, f"Terjadi kesalahan saat menarik data: {str(e)}", {}

def push_all_to_sheets():
    """
    Mengirim seluruh isi database SQLite ke Google Sheets (Migrasi Data Penuh).
    """
    url = get_webhook_url()
    if not url:
        return False, "URL Webhook Google Sheets belum diatur."

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        tables_data = {}
        tables_to_export = [
            ("pegawai", "mahasiswa"),
            ("presensi", "presensi"),
            ("riwayat_kelas", "riwayat_kelas"),
            ("riwayat_izin", "riwayat_izin"),
            ("riwayat_tugas_luar", "riwayat_tugas_luar")
        ]

        for db_tbl, sheet_name in tables_to_export:
            cur.execute(f"SELECT * FROM {db_tbl}")
            rows = [dict(r) for r in cur.fetchall()]
            tables_data[sheet_name] = rows

        conn.close()

        payload = {
            "action": "sync_all",
            "tables": tables_data
        }

        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            res_json = resp.json()
            if res_json.get("status") == "success":
                return True, "Seluruh data lokal berhasil dimigrasikan ke Google Sheets!"
            return False, res_json.get("message", "Gagal melakukan sync_all.")
        return False, f"Google Sheets merespon HTTP {resp.status_code}"
    except Exception as e:
        return False, f"Gagal mengirim data ke Google Sheets: {str(e)}"

def sync_row_async(table_name, row_dict, key="id"):
    """
    Mengirimkan update/insert 1 baris ke Google Sheets secara langsung.
    Jika koneksi Sheets belum diaktifkan, fungsi ini tidak melakukan apa-apa tanpa memicu error.
    """
    if not is_sheets_enabled():
        return False

    url = get_webhook_url()
    payload = {
        "action": "upsert_row",
        "table": table_name,
        "key": key,
        "row": row_dict
    }

    try:
        requests.post(url, json=payload, timeout=5)
        return True
    except Exception as e:
        logger.warning(f"Gagal menyinkronkan baris ke Google Sheets: {str(e)}")
        return False

def sync_delete_async(table_name, key="id", value=None):
    """
    Mengirimkan perintah hapus 1 baris ke Google Sheets secara langsung.
    """
    if not is_sheets_enabled():
        return False

    url = get_webhook_url()
    payload = {
        "action": "delete_row",
        "table": table_name,
        "key": key,
        "value": value
    }

    try:
        requests.post(url, json=payload, timeout=5)
        return True
    except Exception as e:
        logger.warning(f"Gagal menghapus baris di Google Sheets: {str(e)}")
        return False
