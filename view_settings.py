"""
View Web: Pengaturan Jam & Konfigurasi Sistem Presensi Mahasiswa
Simpan Konfigurasi, Integrasi Aman Google Sheets, dan Proteksi PIN Admin
"""
import streamlit as st
from config import load_config, save_config
import database
import sheets_sync
import os

def get_admin_pin(config):
    try:
        if hasattr(st, "secrets") and "admin_pin" in st.secrets:
            return str(st.secrets["admin_pin"]).strip()
    except Exception:
        pass
    return str(config.get("admin_pin", "admin123")).strip()

def render_settings_view():
    config = load_config()

    # ================= 0. PROTEKSI PIN ADMIN =================
    if not st.session_state.get("admin_authenticated", False):
        st.markdown("### 🔒 Akses Pengaturan Dibatasi")
        st.caption("Halaman Pengaturan & Konfigurasi Sistem hanya dapat diakses oleh Pengelola / Administrator Lab.")
        
        col_p1, col_p2 = st.columns([3, 1])
        with col_p1:
            input_pin = st.text_input(
                "Masukkan PIN Admin:", 
                type="password", 
                placeholder="Masukkan PIN Admin (Bawaan: admin123)",
                key="settings_pin_prompt"
            )
        with col_p2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🔓 Buka Akses", type="primary", use_container_width=True):
                if input_pin.strip() == get_admin_pin(config):
                    st.session_state["admin_authenticated"] = True
                    st.rerun()
                else:
                    st.error("⚠️ PIN Admin salah! Akses ditolak.")
        return

    # Header Bar (dengan tombol Kunci Kembali)
    h_col1, h_col2 = st.columns([7, 3])
    with h_col1:
        st.markdown("### ⚙️ Pengaturan Aplikasi Presensi Mahasiswa")
    with h_col2:
        if st.button("🔒 Kunci / Keluar Admin", use_container_width=True):
            st.session_state["admin_authenticated"] = False
            st.rerun()

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

    # ================= BAGIAN 3: TEMA & KEAMANAN =================
    st.markdown("#### 🎨 Tampilan & Keamanan PIN")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        current_theme = config.get("theme_mode", "dark")
        theme_idx = 0 if current_theme == "dark" else 1
        selected_theme = st.selectbox("Mode Tema Utama:", ["dark", "light"], index=theme_idx)
    with col_t2:
        current_pin = config.get("admin_pin", "admin123")
        new_pin_input = st.text_input("Ganti PIN Admin (Bawaan: admin123):", value=current_pin, type="password")

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # ================= BAGIAN 4: GOOGLE SHEETS CLOUD INTEGRATION =================
    st.markdown("#### ☁️ Integrasi Google Sheets (Penyimpanan Cloud Online)")

    sheets_active = sheets_sync.is_sheets_enabled()
    from_secrets = sheets_sync.is_from_secrets()
    webhook_url_effective = sheets_sync.get_webhook_url()

    if from_secrets:
        st.success("🟢 **Google Sheets Terhubung Aman via Streamlit Secrets**")
        st.caption("🔒 *URL Webhook API dikelola secara privat di server Streamlit Secrets dan TIDAK PERNAH diekspos ke publik/browser pengguna.*")
        webhook_to_save = webhook_url_effective
    elif sheets_active:
        st.success("🟢 **Google Sheets Terhubung (Mode Lokal)**")
        with st.expander("⚙️ Konfigurasi URL Webhook (Disamarkan)"):
            webhook_custom = st.text_input(
                "Ganti URL Webhook Google Apps Script:",
                value="",
                type="password",
                placeholder="••••••••••••••••••••••••••••••••••••••••",
                help="URL Webhook disamarkan demi privasi dan keamanan."
            )
            webhook_to_save = webhook_custom.strip() if webhook_custom.strip() else webhook_url_effective
    else:
        st.info("🟡 **Google Sheets Belum Terhubung**: Masukkan URL Webhook untuk mengaktifkan sinkronisasi cloud.")
        with st.expander("⚙️ Hubungkan Google Sheets"):
            webhook_custom = st.text_input(
                "URL Webhook Google Apps Script:",
                value="",
                type="password",
                placeholder="https://script.google.com/macros/s/.../exec",
                help="Masukkan URL Webhook yang didapatkan dari Google Sheets. Input disamarkan demi keamanan."
            )
            webhook_to_save = webhook_custom.strip()

    # Tombol Kontrol Sinkronisasi
    gs_col1, gs_col2 = st.columns(2)
    with gs_col1:
        if st.button("🔍 Uji Koneksi Sheets", use_container_width=True):
            ok, msg = sheets_sync.test_connection()
            if ok:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")

    with gs_col2:
        if st.button("📥 Tarik Data dari Sheets", use_container_width=True):
            st.info("Fitur tarik data diaktifkan melalui database.py (Google Sheets sebagai sumber utama).")
            st.rerun()

    # Tombol Download File Excel Migrasi (hanya jika ada file)
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
            new_config["admin_pin"] = new_pin_input.strip() if new_pin_input.strip() else "admin123"

            if not from_secrets:
                new_config["gsheets_webhook_url"] = webhook_to_save

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
        st.warning("⚠️ Semua data tersimpan di Google Sheets.\nTidak ada database lokal yang bisa di-reset.")
