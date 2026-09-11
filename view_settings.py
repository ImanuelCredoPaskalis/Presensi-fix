"""
View Web: Pengaturan Jam & Konfigurasi Sistem Presensi Mahasiswa
Simpan Konfigurasi dan Reset Database dengan Konfirmasi Ganda
"""
import streamlit as st
from config import load_config, save_config
import database

@st.dialog("⚠️ Konfirmasi Reset Database")
def modal_reset_database():
    st.error("### ⚠️ PERINGATAN: TINDAKAN BERISIKO TINGGI!")
    st.write(
        "Apakah Anda yakin ingin **MENGHAPUS SEMUA DATA**?\n\n"
        "Tindakan ini akan menghapus permanen:\n"
        "- Seluruh daftar mahasiswa\n"
        "- Seluruh riwayat presensi harian\n"
        "- Seluruh riwayat sesi kelas & tugas luar\n\n"
        "Database akan kembali kosong bersih seperti baru."
    )
    confirm_text = st.text_input("Ketik **RESET** untuk konfirmasi penghapusan:", placeholder="RESET")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🗑️ Ya, Kosongkan Semua Data", type="primary", use_container_width=True):
            if confirm_text.strip() != "RESET":
                st.error("Teks konfirmasi salah. Harap ketik RESET persis.")
            else:
                try:
                    conn = database.get_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM riwayat_kelas")
                    cur.execute("DELETE FROM riwayat_tugas_luar")
                    cur.execute("DELETE FROM riwayat_izin")
                    cur.execute("DELETE FROM presensi")
                    cur.execute("DELETE FROM pegawai")
                    cur.execute("DELETE FROM sqlite_sequence")
                    conn.commit()
                    conn.close()

                    st.session_state["settings_alert"] = {
                        "type": "success",
                        "msg": "Semua data berhasil dibersihkan! Database sekarang dalam keadaan kosong."
                    }
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal mengosongkan database: {str(e)}")
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()

def render_settings_view():
    st.markdown("### ⚙️ Pengaturan Aplikasi Presensi Mahasiswa")

    config = load_config()

    if "settings_alert" in st.session_state:
        alert_data = st.session_state["settings_alert"]
        if alert_data["type"] == "success":
            st.success(f"✅ {alert_data['msg']}")
        else:
            st.error(f"⚠️ {alert_data['msg']}")
        del st.session_state["settings_alert"]

    # ================= BAGIAN 1: IDENTITAS LAB / KAMPUS =================
    st.markdown("#### 🏢 Profil Laboratorium / Kampus")
    col1, col2 = st.columns(2)
    with col1:
        comp_name = st.text_input("Nama Laboratorium / Program Studi:", value=config.get("company_name", "Lab Micro Teaching FisMat"))
    with col2:
        comp_addr = st.text_input("Lokasi / Ruangan Lab:", value=config.get("company_address", "Program Studi Pendidikan Matematika"))

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # ================= BAGIAN 2: JAM STANDAR =================
    st.markdown("#### ⏰ Jam Datang & Selesai Standar")
    col3, col4 = st.columns(2)
    with col3:
        work_start = st.text_input("Jam Datang Standar (HH:MM):", value=config.get("work_start_time", "08:00"))
    with col4:
        work_end = st.text_input("Jam Selesai/Pulang Standar (HH:MM):", value=config.get("work_end_time", "17:00"))

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # ================= BAGIAN 3: TEMA =================
    st.markdown("#### 🎨 Preferensi Tampilan")
    current_theme = config.get("theme_mode", "dark")
    theme_idx = 0 if current_theme == "dark" else 1
    selected_theme = st.selectbox("Mode Tema Utama:", ["dark", "light"], index=theme_idx)

    # ================= BAGIAN 4: GOOGLE SHEETS CLOUD INTEGRATION =================
    st.markdown("#### ☁️ Integrasi Google Sheets (Penyimpanan Cloud Online)")
    import sheets_sync
    import os

    sheets_active = sheets_sync.is_sheets_enabled()
    current_webhook_url = sheets_sync.get_webhook_url()

    if sheets_active:
        st.success("🟢 **Google Sheets Aktif**: Aplikasi terhubung ke Google Sheets online. Data presensi langsung tercatat permanen di cloud!")
    else:
        st.info("🟡 **Mode SQLite Lokal**: Aplikasi saat ini menggunakan database SQLite lokal. Untuk deploy di Streamlit Cloud, hubungkan dengan Google Sheets agar data tidak ter-reset.")

    webhook_input = st.text_input(
        "URL Webhook Google Apps Script:",
        value=current_webhook_url,
        placeholder="https://script.google.com/macros/s/AKfycb.../exec",
        help="Masukkan URL Webhook yang didapatkan setelah menerapkan Apps Script di Google Sheets Anda."
    )

    gs_col1, gs_col2, gs_col3 = st.columns(3)
    with gs_col1:
        if st.button("🔍 Uji Koneksi Sheets", use_container_width=True):
            if not webhook_input.strip():
                st.error("Silakan masukkan URL Webhook terlebih dahulu.")
            else:
                sheets_sync.set_webhook_url(webhook_input.strip())
                ok, msg = sheets_sync.test_connection()
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

    with gs_col2:
        if st.button("📥 Tarik Data (Pull dari Sheets)", use_container_width=True):
            if not webhook_input.strip():
                st.error("URL Webhook belum diatur.")
            else:
                sheets_sync.set_webhook_url(webhook_input.strip())
                ok, msg, stats = sheets_sync.pull_from_sheets()
                if ok:
                    st.success(f"✅ {msg} ({stats})")
                else:
                    st.error(f"❌ {msg}")

    with gs_col3:
        if st.button("📤 Upload Semua ke Sheets (Push All)", use_container_width=True):
            if not webhook_input.strip():
                st.error("URL Webhook belum diatur.")
            else:
                sheets_sync.set_webhook_url(webhook_input.strip())
                ok, msg = sheets_sync.push_all_to_sheets()
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

    # Tombol Download File Excel Migrasi
    xlsx_path = "migrasi_data_presensi_google_sheets.xlsx"
    if os.path.exists(xlsx_path):
        with open(xlsx_path, "rb") as f:
            xlsx_bytes = f.read()
        st.download_button(
            label="📄 Unduh File Migrasi Data Eksisting (.xlsx) untuk Diunggah ke Google Drive",
            data=xlsx_bytes,
            file_name="migrasi_data_presensi_google_sheets.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with st.expander("📖 Panduan Singkat Memasang Google Sheets (2 Menit)"):
        st.markdown("""
        1. **Unduh file migrasi** di atas (`migrasi_data_presensi_google_sheets.xlsx`).
        2. Buka [Google Drive](https://drive.google.com) > Klik **Baru (+)** > **Upload File** > Pilih file tersebut.
        3. Buka file tersebut dengan **Google Spreadsheet**.
        4. Di menu Google Sheets, klik **Ekstensi (Extensions)** > **Apps Script**.
        5. Salin dan tempelkan isi file `google_apps_script.js` (ada di folder proyek ini) ke dalam editor script.
        6. Klik **Terapkan (Deploy)** > **Penerapan Baru (New Deployment)**:
           - Jenis: **Aplikasi Web (Web App)**
           - Jalankan sebagai: **Saya**
           - Siapa yang memiliki akses: **Siapa saja (Anyone)**
        7. Klik **Terapkan**, lalu salin **URL Aplikasi Web** yang dihasilkan.
        8. Tempelkan URL tersebut pada kotak input di atas (atau di menu **Settings > Secrets** pada dashboard Streamlit Community Cloud).
        """)

    st.markdown("---")

    # ================= TOMBOL AKSI =================
    btn_col1, btn_col2 = st.columns([3, 3])
    with btn_col1:
        if st.button("💾 Simpan Perubahan Pengaturan", type="primary", use_container_width=True):
            new_config = config.copy()
            new_config["company_name"] = comp_name.strip()
            new_config["company_address"] = comp_addr.strip()
            new_config["work_start_time"] = work_start.strip()
            new_config["work_end_time"] = work_end.strip()
            new_config.pop("late_tolerance_minutes", None)
            new_config["theme_mode"] = selected_theme
            new_config["gsheets_webhook_url"] = webhook_input.strip()

            if save_config(new_config):
                st.session_state["settings_alert"] = {
                    "type": "success",
                    "msg": "Pengaturan sistem presensi berhasil disimpan!"
                }
            else:
                st.session_state["settings_alert"] = {
                    "type": "error",
                    "msg": "Gagal menyimpan konfigurasi ke file config.json."
                }
            st.rerun()

    with btn_col2:
        if st.button("🗑️ Kosongkan / Reset Semua Data", use_container_width=True):
            modal_reset_database()
