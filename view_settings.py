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
