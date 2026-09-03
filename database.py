"""
Database Module - Manajemen SQLite untuk Sistem Presensi Mahasiswa & Kelas
Mendukung Multi-Sesi Kelas (Bisa lebih dari 1 kelas dalam 1 hari), Tugas Luar, dan 6 Waktu Presensi
"""
import sqlite3
import datetime
from config import DB_PATH, load_config

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Tabel Mahasiswa
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pegawai (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nik TEXT UNIQUE NOT NULL,
        nama TEXT NOT NULL,
        jabatan TEXT NOT NULL,
        departemen TEXT NOT NULL,
        telepon TEXT,
        email TEXT,
        status_aktif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabel Presensi Harian
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS presensi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pegawai_id INTEGER NOT NULL,
        tanggal TEXT NOT NULL,
        jam_masuk TEXT,
        jam_masuk_kelas TEXT,
        jam_kembali_kelas TEXT,
        keterangan_kelas TEXT,
        jam_bertugas_keluar TEXT,
        jam_kembali TEXT,
        jam_keluar TEXT,
        keterangan_tugas TEXT,
        status TEXT DEFAULT 'Hadir',
        catatan TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pegawai_id) REFERENCES pegawai (id),
        UNIQUE(pegawai_id, tanggal)
    )
    """)

    # Migrasi otomatis kolom jika database sudah ada sebelumnya
    cursor.execute("PRAGMA table_info(presensi)")
    columns = [row[1] for row in cursor.fetchall()]
    if "jam_masuk_kelas" not in columns:
        cursor.execute("ALTER TABLE presensi ADD COLUMN jam_masuk_kelas TEXT")
    if "jam_kembali_kelas" not in columns:
        cursor.execute("ALTER TABLE presensi ADD COLUMN jam_kembali_kelas TEXT")
    if "keterangan_kelas" not in columns:
        cursor.execute("ALTER TABLE presensi ADD COLUMN keterangan_kelas TEXT")

    # Tabel Riwayat Detail Tugas Luar
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS riwayat_tugas_luar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        presensi_id INTEGER,
        pegawai_id INTEGER NOT NULL,
        tanggal TEXT NOT NULL,
        jam_keluar TEXT NOT NULL,
        jam_kembali TEXT,
        keterangan TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pegawai_id) REFERENCES pegawai (id),
        FOREIGN KEY (presensi_id) REFERENCES presensi (id)
    )
    """)

    # Tabel Riwayat Detail Kelas (Multi-Sesi Kelas)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS riwayat_kelas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        presensi_id INTEGER,
        pegawai_id INTEGER NOT NULL,
        tanggal TEXT NOT NULL,
        jam_masuk_kelas TEXT NOT NULL,
        jam_kembali_kelas TEXT,
        keterangan TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pegawai_id) REFERENCES pegawai (id),
        FOREIGN KEY (presensi_id) REFERENCES presensi (id)
    )
    """)

    conn.commit()
    conn.close()

# ==================== MAHASISWA CRUD ====================

def get_all_pegawai(only_active=True, search_query=None, departemen=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM pegawai WHERE 1=1"
    params = []

    if only_active:
        query += " AND status_aktif = 1"

    if departemen and departemen != "Semua Program Studi":
        query += " AND departemen = ?"
        params.append(departemen)

    if search_query:
        query += " AND (nik LIKE ? OR nama LIKE ? OR jabatan LIKE ?)"
        like_str = f"%{search_query}%"
        params.extend([like_str, like_str, like_str])

    query += " ORDER BY nama ASC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_pegawai_by_id(pegawai_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pegawai WHERE id = ?", (pegawai_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_pegawai_by_nik(nik):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pegawai WHERE LOWER(TRIM(nik)) = LOWER(TRIM(?))", (nik,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_pegawai(nama, telepon="", email="", jabatan="Mahasiswa", departemen="Pendidikan Matematika", nik=""):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        clean_nama = nama.strip()
        if not nik or not nik.strip():
            cursor.execute("SELECT COUNT(*) FROM pegawai")
            next_num = cursor.fetchone()[0] + 1
            clean_nik = f"MHS-{next_num:03d}"
        else:
            clean_nik = nik.strip()

        cursor.execute("""
            INSERT INTO pegawai (nik, nama, jabatan, departemen, telepon, email)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (clean_nik, clean_nama, jabatan.strip(), departemen.strip(), telepon.strip(), email.strip()))
        conn.commit()
        pegawai_id = cursor.lastrowid
        conn.close()
        return True, "Data mahasiswa berhasil ditambahkan!", pegawai_id
    except sqlite3.IntegrityError:
        clean_nik = f"MHS-{datetime.datetime.now().strftime('%M%S')}"
        cursor.execute("""
            INSERT INTO pegawai (nik, nama, jabatan, departemen, telepon, email)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (clean_nik, clean_nama, jabatan.strip(), departemen.strip(), telepon.strip(), email.strip()))
        conn.commit()
        pegawai_id = cursor.lastrowid
        conn.close()
        return True, "Data mahasiswa berhasil ditambahkan!", pegawai_id
    except Exception as e:
        conn.close()
        return False, f"Gagal menambahkan data: {str(e)}", None

def update_pegawai(pegawai_id, nama, telepon="", email="", jabatan="Mahasiswa", departemen="Pendidikan Matematika", nik="", status_aktif=1):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        clean_nama = nama.strip()
        if not nik or not nik.strip():
            cursor.execute("SELECT nik FROM pegawai WHERE id = ?", (pegawai_id,))
            row = cursor.fetchone()
            clean_nik = row["nik"] if row and row["nik"] else f"MHS-{pegawai_id:03d}"
        else:
            clean_nik = nik.strip()

        cursor.execute("""
            UPDATE pegawai 
            SET nik = ?, nama = ?, jabatan = ?, departemen = ?, telepon = ?, email = ?, status_aktif = ?
            WHERE id = ?
        """, (clean_nik, clean_nama, jabatan.strip(), departemen.strip(), telepon.strip(), email.strip(), status_aktif, pegawai_id))
        conn.commit()
        conn.close()
        return True, "Data mahasiswa berhasil diperbarui!"
    except Exception as e:
        conn.close()
        return False, f"Gagal memperbarui data: {str(e)}"

def delete_pegawai(pegawai_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM presensi WHERE pegawai_id = ?", (pegawai_id,))
        count = cursor.fetchone()[0]
        if count > 0:
            cursor.execute("UPDATE pegawai SET status_aktif = 0 WHERE id = ?", (pegawai_id,))
            conn.commit()
            conn.close()
            return True, "Mahasiswa memiliki riwayat presensi, status diubah menjadi Non-Aktif."
        else:
            cursor.execute("DELETE FROM pegawai WHERE id = ?", (pegawai_id,))
            conn.commit()
            conn.close()
            return True, "Data mahasiswa berhasil dihapus permanen."
    except Exception as e:
        conn.close()
        return False, f"Gagal menghapus data mahasiswa: {str(e)}"

def get_list_departemen():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT departemen FROM pegawai WHERE departemen IS NOT NULL AND departemen != '' ORDER BY departemen ASC")
    deps = [r[0] for r in cursor.fetchall()]
    conn.close()
    if not deps:
        deps = ["Pendidikan Matematika", "Fisika", "Micro Teaching", "Laboratorium"]
    return deps

# ==================== RIWAYAT MULTI-SESI KELAS ====================

def get_riwayat_kelas_by_presensi(presensi_id):
    if not presensi_id:
        return []
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM riwayat_kelas 
        WHERE presensi_id = ? 
        ORDER BY id ASC
    """, (presensi_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_riwayat_kelas_today(pegawai_id, tanggal=None):
    if not tanggal:
        tanggal = get_today_str()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM riwayat_kelas 
        WHERE pegawai_id = ? AND tanggal = ?
        ORDER BY id ASC
    """, (pegawai_id, tanggal))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def calculate_total_kelas_duration(riwayat_list):
    """
    Menghitung total durasi kumulatif seluruh sesi kelas dalam 1 hari.
    """
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
    """
    Memformat ringkasan multi-sesi kelas menjadi teks ramah baca.
    Contoh:
    1 Sesi Selesai: 08:00-09:30 (Micro Teaching A)
    2 Sesi: K1: 08:00-09:30 (Micro Teaching A) | K2: 10:00-11:30 (Geometri)
    Sedang Kelas: K2: 10:00- (Sedang di Kelas: Geometri)
    """
    if not riwayat_list:
        return "-"
    
    parts = []
    for idx, r in enumerate(riwayat_list, 1):
        start = r.get("jam_masuk_kelas") or "?"
        end = r.get("jam_kembali_kelas")
        ket = r.get("keterangan") or "Kelas"
        
        if len(start) == 8:
            start_short = start[:5]
        else:
            start_short = start
            
        if end:
            end_short = end[:5] if len(end) == 8 else end
            parts.append(f"K{idx}: {start_short}-{end_short} ({ket})")
        else:
            parts.append(f"K{idx}: {start_short}-Sedang Kelas ({ket})")
            
    return " | ".join(parts)

def format_kelas_time_display(riwayat_list):
    """
    Format kolom jam masuk kelas ringkas untuk tabel.
    """
    if not riwayat_list:
        return "-"
    if len(riwayat_list) == 1:
        r = riwayat_list[0]
        start = r.get("jam_masuk_kelas") or "-"
        end = r.get("jam_kembali_kelas")
        if end:
            return f"{start[:5]}-{end[:5]}"
        return f"{start[:5]} (Sedang Kelas)"
    else:
        # Multi-sesi
        sesi_strs = []
        for idx, r in enumerate(riwayat_list, 1):
            s = r.get("jam_masuk_kelas", "")[:5]
            e = r.get("jam_kembali_kelas", "")[:5] if r.get("jam_kembali_kelas") else "Aktif"
            sesi_strs.append(f"K{idx}: {s}-{e}")
        return f"{len(riwayat_list)} Sesi ({', '.join(sesi_strs)})"

# ==================== PRESENSI ====================

def get_today_str():
    return datetime.date.today().strftime("%Y-%m-%d")

def get_current_time_str():
    return datetime.datetime.now().strftime("%H:%M:%S")

def get_today_presence_record(pegawai_id):
    today = get_today_str()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, pg.nik, pg.nama, pg.jabatan, pg.departemen
        FROM presensi p
        JOIN pegawai pg ON p.pegawai_id = pg.id
        WHERE p.pegawai_id = ? AND p.tanggal = ?
    """, (pegawai_id, today))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

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
    - 'kelas': Jam Untuk Kelas (Masuk / Mulai Kelas - Mendukung Sesi 1, 2, 3 dst.)
    - 'kembali_kelas': Jam Kembali dari Kelas (Selesai Sesi Kelas yang Sedang Berlangsung)
    - 'tugas_keluar': Jam Bertugas Keluar (Dinas / Lapangan / Kunjungan)
    - 'kembali': Jam Kembali (Selesai Tugas Luar)
    - 'keluar': Jam Keluar (Selesai / Pulang)
    """
    today = get_today_str()
    now_time = custom_time if custom_time else get_current_time_str()
    config = load_config()

    conn = get_connection()
    cursor = conn.cursor()

    # Ambil data mahasiswa
    cursor.execute("SELECT * FROM pegawai WHERE id = ?", (pegawai_id,))
    pegawai = cursor.fetchone()
    if not pegawai:
        conn.close()
        return False, "Mahasiswa tidak ditemukan!", None

    # Ambil catatan hari ini jika sudah ada
    cursor.execute("SELECT * FROM presensi WHERE pegawai_id = ? AND tanggal = ?", (pegawai_id, today))
    existing = cursor.fetchone()

    # 1. AKSI: JAM MASUK
    if action_type == "masuk":
        if existing and existing["jam_masuk"]:
            conn.close()
            return False, f"{pegawai['nama']} sudah melakukan presensi MASUK hari ini pukul {existing['jam_masuk']}.", dict(existing)

        # Evaluasi Tepat Waktu vs Terlambat
        work_start = config.get("work_start_time", "08:00")
        
        status = "Tepat Waktu"
        try:
            cur_dt = datetime.datetime.strptime(now_time, "%H:%M:%S").time()
            start_h, start_m = parse_time_setting(work_start, 8, 0)
            limit_dt = datetime.time(start_h, start_m)
            if cur_dt > limit_dt:
                status = "Terlambat"
        except Exception:
            status = "Hadir"

        if existing:
            cursor.execute("""
                UPDATE presensi 
                SET jam_masuk = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (now_time, status, existing["id"]))
            presensi_id = existing["id"]
        else:
            cursor.execute("""
                INSERT INTO presensi (pegawai_id, tanggal, jam_masuk, status)
                VALUES (?, ?, ?, ?)
            """, (pegawai_id, today, now_time, status))
            presensi_id = cursor.lastrowid

        conn.commit()
        msg = f"Berhasil! Presensi MASUK tercatat pukul {now_time} ({status})."

    # 2. AKSI: JAM UNTUK KELAS (MASUK / MULAI KELAS - MULTI-SESI)
    elif action_type == "kelas":
        # Cek apakah ada sesi kelas yang MASIH BERLANGSUNG (belum absen kembali)
        cursor.execute("""
            SELECT * FROM riwayat_kelas 
            WHERE pegawai_id = ? AND tanggal = ? AND jam_kembali_kelas IS NULL
            ORDER BY id DESC LIMIT 1
        """, (pegawai_id, today))
        active_class = cursor.fetchone()

        if active_class:
            conn.close()
            ket_act = active_class["keterangan"] or "Kelas"
            return False, f"{pegawai['nama']} saat ini masih tercatat SEDANG DI KELAS ({ket_act}) sejak pukul {active_class['jam_masuk_kelas']}. Silakan lakukan presensi 'Kembali Kelas' terlebih dahulu sebelum memulai sesi kelas baru.", dict(existing) if existing else None

        # Hitung nomor sesi kelas ke berapa
        cursor.execute("""
            SELECT COUNT(*) FROM riwayat_kelas 
            WHERE pegawai_id = ? AND tanggal = ?
        """, (pegawai_id, today))
        sesi_num = cursor.fetchone()[0] + 1

        ket = keterangan.strip() if keterangan else f"Kegiatan Belajar Mengajar / Kelas (Sesi {sesi_num})"

        if existing:
            jam_masuk_val = existing["jam_masuk"] if existing["jam_masuk"] else now_time
            # Update presensi dengan waktu sesi kelas terbaru
            cursor.execute("""
                UPDATE presensi 
                SET jam_masuk = ?, jam_masuk_kelas = ?, jam_kembali_kelas = NULL, 
                    keterangan_kelas = ?, status = 'Sedang di Kelas', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (jam_masuk_val, now_time, ket, existing["id"]))
            presensi_id = existing["id"]
        else:
            cursor.execute("""
                INSERT INTO presensi (pegawai_id, tanggal, jam_masuk, jam_masuk_kelas, keterangan_kelas, status)
                VALUES (?, ?, ?, ?, ?, 'Sedang di Kelas')
            """, (pegawai_id, today, now_time, now_time, ket))
            presensi_id = cursor.lastrowid

        # Insert sesi kelas baru ke riwayat_kelas
        cursor.execute("""
            INSERT INTO riwayat_kelas (presensi_id, pegawai_id, tanggal, jam_masuk_kelas, keterangan)
            VALUES (?, ?, ?, ?, ?)
        """, (presensi_id, pegawai_id, today, now_time, ket))

        conn.commit()
        msg = f"Berhasil! Presensi KE KELAS (Sesi {sesi_num}) tercatat pukul {now_time}. Keterangan: {ket}."

    # 3. AKSI: JAM KEMBALI DARI KELAS (SELESAI SESI KELAS)
    elif action_type == "kembali_kelas":
        # Cari sesi kelas yang saat ini sedang aktif (jam_kembali_kelas IS NULL)
        cursor.execute("""
            SELECT * FROM riwayat_kelas 
            WHERE pegawai_id = ? AND tanggal = ? AND jam_kembali_kelas IS NULL
            ORDER BY id DESC LIMIT 1
        """, (pegawai_id, today))
        active_class = cursor.fetchone()

        if not active_class:
            conn.close()
            # Cek apakah pernah ada sesi kelas hari ini
            cursor.execute("SELECT COUNT(*) FROM riwayat_kelas WHERE pegawai_id = ? AND tanggal = ?", (pegawai_id, today))
            count_sesi = cursor.fetchone()[0]
            if count_sesi > 0:
                return False, f"{pegawai['nama']} saat ini TIDAK sedang di kelas (semua {count_sesi} sesi kelas sebelumnya sudah selesai). Silakan klik 'Jam Ke Kelas' untuk memulai sesi baru.", dict(existing) if existing else None
            else:
                return False, f"{pegawai['nama']} belum tercatat melakukan presensi 'Jam Ke Kelas' hari ini.", None

        # Update baris riwayat_kelas aktif
        cursor.execute("""
            UPDATE riwayat_kelas 
            SET jam_kembali_kelas = ? 
            WHERE id = ?
        """, (now_time, active_class["id"]))

        # Hitung nomor urut sesi ini
        cursor.execute("SELECT COUNT(*) FROM riwayat_kelas WHERE pegawai_id = ? AND tanggal = ? AND id <= ?", (pegawai_id, today, active_class["id"]))
        sesi_ke = cursor.fetchone()[0]

        durasi_sesi = calculate_time_diff_hours(active_class["jam_masuk_kelas"], now_time)

        # Update status tabel presensi harian
        if existing:
            cursor.execute("""
                UPDATE presensi 
                SET jam_kembali_kelas = ?, status = 'Hadir di Lab', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (now_time, existing["id"]))

        conn.commit()
        msg = f"Selamat Datang Kembali! Sesi Kelas #{sesi_ke} selesai pukul {now_time} (Durasi Sesi: {durasi_sesi})."

    # 4. AKSI: JAM BERTUGAS KELUAR (TUGAS LUAR)
    elif action_type == "tugas_keluar":
        if existing and existing["jam_bertugas_keluar"] and not existing["jam_kembali"]:
            conn.close()
            return False, f"{pegawai['nama']} saat ini masih tercatat SEDANG BERTUGAS KELUAR sejak pukul {existing['jam_bertugas_keluar']}. Silakan lakukan presensi 'Kembali Tugas' terlebih dahulu.", dict(existing)

        ket = keterangan.strip() if keterangan else "Tugas Luar Kampus"

        if existing:
            jam_masuk_val = existing["jam_masuk"] if existing["jam_masuk"] else now_time
            cursor.execute("""
                UPDATE presensi 
                SET jam_masuk = ?, jam_bertugas_keluar = ?, jam_kembali = NULL, 
                    keterangan_tugas = ?, status = 'Sedang Tugas Luar', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (jam_masuk_val, now_time, ket, existing["id"]))
            presensi_id = existing["id"]
        else:
            cursor.execute("""
                INSERT INTO presensi (pegawai_id, tanggal, jam_masuk, jam_bertugas_keluar, keterangan_tugas, status)
                VALUES (?, ?, ?, ?, ?, 'Sedang Tugas Luar')
            """, (pegawai_id, today, now_time, now_time, ket))
            presensi_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO riwayat_tugas_luar (presensi_id, pegawai_id, tanggal, jam_keluar, keterangan)
            VALUES (?, ?, ?, ?, ?)
        """, (presensi_id, pegawai_id, today, now_time, ket))

        conn.commit()
        msg = f"Berhasil! Presensi TUGAS KELUAR tercatat pukul {now_time}. Keterangan: {ket}."

    # 5. AKSI: JAM KEMBALI DARI TUGAS LUAR
    elif action_type == "kembali":
        if not existing or not existing["jam_bertugas_keluar"]:
            conn.close()
            return False, f"{pegawai['nama']} belum tercatat melakukan presensi 'Tugas Keluar' hari ini.", None

        if existing["jam_kembali"] and not (existing["jam_bertugas_keluar"] and not existing["jam_kembali"]):
            conn.close()
            return False, f"{pegawai['nama']} sudah mencatat jam KEMBALI TUGAS pukul {existing['jam_kembali']}.", dict(existing)

        cursor.execute("""
            UPDATE presensi 
            SET jam_kembali = ?, status = 'Hadir di Lab', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (now_time, existing["id"]))

        cursor.execute("""
            UPDATE riwayat_tugas_luar 
            SET jam_kembali = ? 
            WHERE presensi_id = ? AND jam_kembali IS NULL
        """, (now_time, existing["id"]))

        conn.commit()
        msg = f"Selamat Datang Kembali! Presensi KEMBALI TUGAS tercatat pukul {now_time}."

    # 6. AKSI: JAM KELUAR / SELESAI
    elif action_type == "keluar":
        if existing and existing["jam_keluar"]:
            conn.close()
            return False, f"{pegawai['nama']} sudah melakukan presensi KELUAR/SELESAI hari ini pukul {existing['jam_keluar']}.", dict(existing)

        if existing:
            update_fields = ["jam_keluar = ?", "status = 'Sudah Pulang'", "updated_at = CURRENT_TIMESTAMP"]
            params = [now_time]

            # Tutup otomatis sesi kelas jika masih ada yang aktif
            cursor.execute("""
                UPDATE riwayat_kelas 
                SET jam_kembali_kelas = ? 
                WHERE presensi_id = ? AND jam_kembali_kelas IS NULL
            """, (now_time, existing["id"]))

            if existing["jam_bertugas_keluar"] and not existing["jam_kembali"]:
                update_fields.append("jam_kembali = ?")
                params.append(now_time)
                cursor.execute("""
                    UPDATE riwayat_tugas_luar 
                    SET jam_kembali = ? 
                    WHERE presensi_id = ? AND jam_kembali IS NULL
                """, (now_time, existing["id"]))

            params.append(existing["id"])
            sql = f"UPDATE presensi SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(sql, params)
        else:
            cursor.execute("""
                INSERT INTO presensi (pegawai_id, tanggal, jam_masuk, jam_keluar, status)
                VALUES (?, ?, ?, ?, 'Sudah Pulang')
            """, (pegawai_id, today, now_time, now_time))

        conn.commit()
        msg = f"Sampai Jumpa! Presensi KELUAR / SELESAI tercatat pukul {now_time}."

    else:
        conn.close()
        return False, "Aksi presensi tidak valid!", None

    # Ambil data terbaru
    cursor.execute("""
        SELECT p.*, pg.nik, pg.nama, pg.jabatan, pg.departemen
        FROM presensi p
        JOIN pegawai pg ON p.pegawai_id = pg.id
        WHERE p.pegawai_id = ? AND p.tanggal = ?
    """, (pegawai_id, today))
    updated_record = cursor.fetchone()
    res_dict = dict(updated_record) if updated_record else None
    conn.close()
    return True, msg, res_dict

# ==================== SUMMARY & STATISTIK ====================

def get_today_summary():
    today = get_today_str()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM pegawai WHERE status_aktif = 1")
    total_pegawai = cursor.fetchone()[0]

    cursor.execute("SELECT * FROM presensi WHERE tanggal = ?", (today,))
    records = cursor.fetchall()

    hadir = 0
    sedang_kelas = 0
    tugas_luar = 0
    pulang = 0

    for r in records:
        if r["jam_keluar"]:
            pulang += 1
        elif r["status"] == "Sedang di Kelas":
            sedang_kelas += 1
        elif r["jam_bertugas_keluar"] and not r["jam_kembali"]:
            tugas_luar += 1
        elif r["jam_masuk"] or r["jam_kembali"] or r["jam_kembali_kelas"]:
            hadir += 1

    belum_absen = max(0, total_pegawai - (hadir + sedang_kelas + tugas_luar + pulang))

    conn.close()
    return {
        "total_pegawai": total_pegawai,
        "hadir": hadir,
        "sedang_kelas": sedang_kelas,
        "tugas_luar": tugas_luar,
        "pulang": pulang,
        "belum_absen": belum_absen,
        "tanggal": today
    }

def get_today_presence_table():
    today = get_today_str()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pg.id as pegawai_id, pg.nik, pg.nama, pg.jabatan, pg.departemen,
               p.id as presensi_id, p.tanggal, p.jam_masuk, 
               p.jam_masuk_kelas, p.jam_kembali_kelas, p.keterangan_kelas,
               p.jam_bertugas_keluar, p.jam_kembali, p.jam_keluar, 
               p.keterangan_tugas, p.status
        FROM pegawai pg
        LEFT JOIN presensi p ON pg.id = p.pegawai_id AND p.tanggal = ?
        WHERE pg.status_aktif = 1
        ORDER BY 
            CASE 
                WHEN p.status = 'Sedang di Kelas' THEN 1
                WHEN p.status = 'Sedang Tugas Luar' THEN 2
                WHEN p.jam_masuk IS NOT NULL AND p.jam_keluar IS NULL THEN 3
                WHEN p.jam_keluar IS NOT NULL THEN 4
                ELSE 5
            END,
            pg.nama ASC
    """, (today,))
    rows = [dict(r) for r in cursor.fetchall()]

    # Tambahkan data riwayat kelas untuk setiap baris
    for row in rows:
        if row.get("presensi_id"):
            cursor.execute("""
                SELECT * FROM riwayat_kelas 
                WHERE presensi_id = ? 
                ORDER BY id ASC
            """, (row["presensi_id"],))
            rk_list = [dict(r) for r in cursor.fetchall()]
        else:
            rk_list = []
        
        row["riwayat_kelas_list"] = rk_list
        row["total_sesi_kelas"] = len(rk_list)
        row["ringkasan_kelas"] = format_kelas_summary(rk_list)
        row["display_jam_kelas"] = format_kelas_time_display(rk_list)
        row["durasi_total_kelas"] = calculate_total_kelas_duration(rk_list)

    conn.close()
    return rows

def get_presensi_history(start_date=None, end_date=None, pegawai_id=None, departemen=None, search=None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT p.id as presensi_id, p.tanggal, p.jam_masuk, 
               p.jam_masuk_kelas, p.jam_kembali_kelas, p.keterangan_kelas,
               p.jam_bertugas_keluar, p.jam_kembali, p.jam_keluar, 
               p.keterangan_tugas, p.status, p.catatan,
               pg.id as pegawai_id, pg.nik, pg.nama, pg.jabatan, pg.departemen
        FROM presensi p
        JOIN pegawai pg ON p.pegawai_id = pg.id
        WHERE 1=1
    """
    params = []

    if start_date:
        query += " AND p.tanggal >= ?"
        params.append(start_date)
    if end_date:
        query += " AND p.tanggal <= ?"
        params.append(end_date)
    if pegawai_id:
        query += " AND p.pegawai_id = ?"
        params.append(pegawai_id)
    if departemen and departemen != "Semua Program Studi":
        query += " AND pg.departemen = ?"
        params.append(departemen)
    if search:
        query += " AND (pg.nik LIKE ? OR pg.nama LIKE ?)"
        like_s = f"%{search}%"
        params.extend([like_s, like_s])

    query += " ORDER BY p.tanggal DESC, p.jam_masuk DESC"

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    # Tambahkan riwayat kelas per presensi
    for row in rows:
        cursor.execute("""
            SELECT * FROM riwayat_kelas 
            WHERE presensi_id = ? 
            ORDER BY id ASC
        """, (row["presensi_id"],))
        rk_list = [dict(r) for r in cursor.fetchall()]
        
        row["riwayat_kelas_list"] = rk_list
        row["total_sesi_kelas"] = len(rk_list)
        row["ringkasan_kelas"] = format_kelas_summary(rk_list)
        row["display_jam_kelas"] = format_kelas_time_display(rk_list)
        row["durasi_total_kelas"] = calculate_total_kelas_duration(rk_list)

    conn.close()
    return rows

# ==================== PERHITUNGAN DURASI ====================

def calculate_time_diff_hours(time_start_str, time_end_str):
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
