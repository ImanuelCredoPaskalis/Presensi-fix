"""
View Web: Dashboard & Live Monitoring Presensi Mahasiswa Hari Ini
6 Metrik Kehadiran & Tabel Pemantauan Real-Time (Mendukung Multi-Sesi Kelas)
"""
import streamlit as st
import database

def render_dashboard_view():
    # Cek koneksi Google Sheets
    if not database.is_connection_ok():
        st.warning("⚠️ **Google Sheets belum terhubung!** Pastikan URL Webhook sudah diatur di **Pengaturan**.")
        st.stop()

    # Header bar
    h_col1, h_col2 = st.columns([8, 2])
    with h_col1:
        st.markdown("### 📊 Dashboard & Pemantauan Presensi Mahasiswa Hari Ini")
    with h_col2:
        if st.button("🔄 Segarkan Data", use_container_width=True, key="dashboard_refresh_btn"):
            st.rerun()

    # Ambil data summary
    summary = database.get_today_summary()

    # Jika tidak ada data mahasiswa sama sekali
    if summary["total_pegawai"] == 0:
        st.warning("⚠️ Tidak ada data mahasiswa terdaftar. Pastikan data mahasiswa sudah ada di Google Sheets.")

    # ================= 7 KARTU METRIK KEHADIRAN =================
    m_col1, m_col2, m_col3, m_col4, m_col5, m_col6, m_col7 = st.columns(7)

    def render_metric_card(title, value, bg_color, text_color, border_color):
        return f"""
        <div style="
            background: {bg_color};
            border: 1px solid {border_color};
            border-radius: 10px;
            padding: 12px 6px;
            text-align: center;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        ">
            <div style="font-size: 24px; font-weight: 800; color: {text_color}; line-height: 1.2;">
                {value}
            </div>
            <div style="font-size: 10.5px; font-weight: 700; color: {text_color}; margin-top: 4px; white-space: nowrap;">
                {title}
            </div>
        </div>
        """

    with m_col1:
        st.markdown(render_metric_card("🎓 Total Mahasiswa", summary["total_pegawai"], "#F1F5F9", "#0F172A", "#CBD5E1"), unsafe_allow_html=True)
    with m_col2:
        st.markdown(render_metric_card("✅ Hadir di Lab", summary["hadir"], "#DCFCE7", "#15803D", "#86EFAC"), unsafe_allow_html=True)
    with m_col3:
        st.markdown(render_metric_card("🏫 Sedang di Kelas", summary.get("sedang_kelas", 0), "#FEF3C7", "#B45309", "#FDE68A"), unsafe_allow_html=True)
    with m_col4:
        st.markdown(render_metric_card("🚗 Sedang Tugas", summary["tugas_luar"], "#DBEAFE", "#1D4ED8", "#93C5FD"), unsafe_allow_html=True)
    with m_col5:
        st.markdown(render_metric_card("☕ Sedang Izin", summary.get("sedang_izin", 0), "#FFEDD5", "#9A3412", "#FDBA74"), unsafe_allow_html=True)
    with m_col6:
        st.markdown(render_metric_card("🚪 Sudah Pulang", summary["pulang"], "#F3E8FF", "#7E22CE", "#D8B4FE"), unsafe_allow_html=True)
    with m_col7:
        st.markdown(render_metric_card("⏳ Belum Absen", summary["belum_absen"], "#F8FAFC", "#475569", "#E2E8F0"), unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

    # ================= TABEL MONITORING =================
    t_col1, t_col2 = st.columns([7, 3])
    with t_col1:
        st.markdown("#### Daftar Status Kehadiran & Aktivitas Mahasiswa Hari Ini")
    with t_col2:
        search_q = st.text_input("🔍", placeholder="Cari Nama Mahasiswa...", label_visibility="collapsed", key="dashboard_search_input")

    records = database.get_today_presence_table()

    if search_q.strip():
        sq = search_q.strip().lower()
        records = [r for r in records if sq in r["nama"].lower()]

    if not records:
        if search_q.strip():
            st.info("Tidak ada data presensi yang sesuai dengan kriteria pencarian.")
        else:
            st.info("Belum ada data presensi hari ini. Pastikan mahasiswa sudah melakukan presensi atau data sudah tersinkronisasi dari Google Sheets.")
    else:
        table_rows = []
        for r in records:
            table_rows.append({
                "Nama Mahasiswa": r.get("nama", "-"),
                "Jam Masuk": r.get("jam_masuk") or "-",
                "Sesi & Jam Kelas": r.get("display_jam_kelas") or "-",
                "Durasi Kelas": r.get("durasi_total_kelas") or "-",
                "Tugas Luar": r.get("jam_bertugas_keluar") or "-",
                "Kembali Tugas": r.get("jam_kembali") or "-",
                "Izin Keluar": r.get("display_jam_izin") or "-",
                "Durasi Izin": r.get("durasi_total_izin") or "-",
                "Jam Keluar": r.get("jam_keluar") or "-",
                "Durasi Shift": r.get("durasi_shift") or "-",
                "Status": r.get("status") or "Belum Presensi"
            })

        st.dataframe(table_rows, width="stretch", hide_index=True)
