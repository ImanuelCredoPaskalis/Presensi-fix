"""
Web App Utama: Sistem Presensi Mahasiswa & Kelas (Lab Micro Teaching FisMat)
Berbasis Streamlit - Konversi Penuh dari Aplikasi Desktop
"""
import streamlit as st
import database
from config import load_config
from view_presensi import render_presensi_view
from view_dashboard import render_dashboard_view
from view_pegawai import render_pegawai_view
from view_laporan import render_laporan_view
from view_settings import render_settings_view

# Pastikan koneksi Google Sheets terkonfigurasi
database.init_db()

# Load Konfigurasi
config = load_config()

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title=f"{config.get('app_title', 'Sistem Presensi Mahasiswa & Kelas')} - {config.get('company_name', 'Lab Micro Teaching FisMat')}",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling CSS
custom_css = """
<style>
    /* Styling Tombol Aksi Presensi */
    div.st-key-btn_masuk > button {
        background-color: #10B981 !important;
        color: white !important;
        border: none !important;
        min-height: 58px !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(16, 185, 129, 0.2);
    }
    div.st-key-btn_masuk > button:hover {
        background-color: #059669 !important;
    }

    div.st-key-btn_kelas > button {
        background-color: #F59E0B !important;
        color: white !important;
        border: none !important;
        min-height: 58px !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(245, 158, 11, 0.2);
    }
    div.st-key-btn_kelas > button:hover {
        background-color: #D97706 !important;
    }

    div.st-key-btn_kembali_kelas > button {
        background-color: #6366F1 !important;
        color: white !important;
        border: none !important;
        min-height: 58px !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(99, 102, 241, 0.2);
    }
    div.st-key-btn_kembali_kelas > button:hover {
        background-color: #4F46E5 !important;
    }

    div.st-key-btn_tugas > button {
        background-color: #3B82F6 !important;
        color: white !important;
        border: none !important;
        min-height: 58px !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
    }
    div.st-key-btn_tugas > button:hover {
        background-color: #2563EB !important;
    }

    div.st-key-btn_kembali_tugas > button {
        background-color: #8B5CF6 !important;
        color: white !important;
        border: none !important;
        min-height: 58px !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(139, 92, 246, 0.2);
    }
    div.st-key-btn_kembali_tugas > button:hover {
        background-color: #7C3AED !important;
    }

    div.st-key-btn_keluar > button {
        background-color: #EF4444 !important;
        color: white !important;
        border: none !important;
        min-height: 58px !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(239, 68, 68, 0.2);
    }
    div.st-key-btn_keluar > button:hover {
        background-color: #DC2626 !important;
    }

    /* Sidebar Branding */
    .sidebar-brand-title {
        font-size: 20px;
        font-weight: 800;
        color: #2563EB;
        margin-bottom: 2px;
        letter-spacing: -0.5px;
    }
    .sidebar-brand-sub {
        font-size: 12px;
        color: #64748B;
        margin-bottom: 24px;
        line-height: 1.3;
    }
    .sidebar-footer {
        font-size: 11px;
        color: #94A3B8;
        margin-top: 50px;
        text-align: center;
        border-top: 1px solid #E2E8F0;
        padding-top: 12px;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ================= SIDEBAR NAVIGASI =================
with st.sidebar:
    st.markdown('<div class="sidebar-brand-title">⚡ PRESENSI MAHASISWA</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-brand-sub">Sistem Presensi & Kelas Mahasiswa</div>', unsafe_allow_html=True)

    nav_options = [
        "🕒  Presensi Mahasiswa",
        "📊  Dashboard Live",
        "🎓  Data Mahasiswa",
        "📑  Rekap & Laporan",
        "⚙️  Pengaturan"
    ]

    selected_menu = st.radio(
        "Menu Navigasi",
        options=nav_options,
        index=0,
        label_visibility="collapsed"
    )

    st.markdown('<div class="sidebar-footer">Versi 1.0 • Web Edition<br>Lab Micro Teaching FisMat</div>', unsafe_allow_html=True)

# ================= KONTEN HALAMAN =================
if selected_menu == "🕒  Presensi Mahasiswa":
    render_presensi_view()
elif selected_menu == "📊  Dashboard Live":
    render_dashboard_view()
elif selected_menu == "🎓  Data Mahasiswa":
    render_pegawai_view()
elif selected_menu == "📑  Rekap & Laporan":
    render_laporan_view()
elif selected_menu == "⚙️  Pengaturan":
    render_settings_view()
