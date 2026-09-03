"""
View Web: Terminal Presensi Mahasiswa Otomatis (Murni Berbasis Nama Mahasiswa)
Mendukung Multi-Sesi Kelas, Tugas Luar, dan 6 Waktu Presensi
"""
import streamlit as st
import datetime
import database
from config import load_config

def get_indonesian_date_str():
    now = datetime.datetime.now()
    days_id = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    months_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                 "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    day_name = days_id[now.weekday()]
    month_name = months_id[now.month - 1]
    return f"📅 {day_name}, {now.day} {month_name} {now.year}"

@st.dialog("🏫 Keterangan Jam Ke Kelas")
def modal_jam_ke_kelas(pegawai):
    riwayat = database.get_riwayat_kelas_today(pegawai["id"])
    next_sesi = len(riwayat) + 1
    st.write(f"**Mahasiswa:** {pegawai['nama']}")
    st.write(f"Masukkan Nama Kelas / Mata Kuliah / Ruangan untuk **Sesi #{next_sesi}**:")
    default_ket = f"Kegiatan Belajar Mengajar / Kelas (Sesi #{next_sesi})"
    ket_input = st.text_input("Nama Kelas / Mata Kuliah / Ruangan:", value=default_ket, placeholder="Contoh: Micro Teaching A / Kelas Teori R.201 / Praktikum")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("✅ Mulai Sesi Kelas", type="primary", use_container_width=True):
            clean_ket = ket_input.strip() if ket_input.strip() else default_ket
            success, msg, rec = database.record_attendance(pegawai["id"], "kelas", clean_ket)
            if success:
                st.session_state["presensi_alert"] = {"type": "success", "msg": msg}
            else:
                st.session_state["presensi_alert"] = {"type": "error", "msg": msg}
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()

@st.dialog("🚗 Keterangan Tugas Luar Kampus")
def modal_tugas_keluar(pegawai):
    st.write(f"**Mahasiswa:** {pegawai['nama']}")
    st.write("Masukkan Tujuan & Keterangan Tugas Luar:")
    default_ket = "Tugas Luar Kampus"
    ket_input = st.text_input("Tujuan / Keterangan Tugas:", value=default_ket, placeholder="Contoh: Observasi Sekolah Mitra / Survey Lapangan / Kunjungan")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("✅ Mulai Tugas Luar", type="primary", use_container_width=True):
            clean_ket = ket_input.strip() if ket_input.strip() else default_ket
            success, msg, rec = database.record_attendance(pegawai["id"], "tugas_keluar", clean_ket)
            if success:
                st.session_state["presensi_alert"] = {"type": "success", "msg": msg}
            else:
                st.session_state["presensi_alert"] = {"type": "error", "msg": msg}
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()

@st.dialog("🔍 Rincian Sesi Kelas Hari Ini")
def modal_rincian_sesi_kelas(pegawai):
    st.markdown(f"### 📚 Rincian Sesi Kelas Hari Ini: {pegawai['nama']}")
    riwayat_kelas = database.get_riwayat_kelas_today(pegawai["id"])
    total_dur = database.calculate_total_kelas_duration(riwayat_kelas)
    st.caption(f"Total: **{len(riwayat_kelas)} Sesi Kelas** • Total Durasi: **{total_dur}**")

    if not riwayat_kelas:
        st.info("Belum ada sesi kelas hari ini.")
    else:
        table_data = []
        for idx, r in enumerate(riwayat_kelas, 1):
            m = r.get("jam_masuk_kelas") or "-"
            k = r.get("jam_kembali_kelas") or "(Sedang di Kelas)"
            dur = database.calculate_time_diff_hours(r.get("jam_masuk_kelas"), r.get("jam_kembali_kelas"))
            ket = r.get("keterangan") or "-"
            table_data.append({
                "Sesi #": f"Sesi #{idx}",
                "Jam Masuk": m,
                "Jam Kembali": k,
                "Durasi": dur,
                "Nama Kelas / Mata Kuliah / Ruangan": ket
            })
        st.table(table_data)

    if st.button("Tutup", use_container_width=True):
        st.rerun()

def render_presensi_view():
    config = load_config()
    
    # Inisialisasi state presensi
    if "selected_pegawai_id" not in st.session_state:
        st.session_state["selected_pegawai_id"] = None
    if "presensi_alert" not in st.session_state:
        st.session_state["presensi_alert"] = {
            "type": "info",
            "msg": "Siap mencatat presensi. Pilih nama mahasiswa lalu klik tombol aksi di bawah."
        }

    # ================= 1. HEADER KARTU: TANGGAL, LAB & JAM DIGITAL =================
    header_html = f"""
    <div style="
        background: white;
        border-radius: 12px;
        padding: 16px 24px;
        margin-bottom: 20px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 15px;
    ">
        <div>
            <div style="font-size: 18px; font-weight: 700; color: #0F172A; margin-bottom: 4px;">
                {get_indonesian_date_str()}
            </div>
            <div style="font-size: 13px; color: #64748B;">
                {config.get('company_name', 'Lab Micro Teaching FisMat')} • Jam Standar: <b>{config.get('work_start_time', '08:00')} - {config.get('work_end_time', '17:00')}</b>
            </div>
        </div>
        <div style="text-align: right;">
            <div id="live-clock" style="font-family: Consolas, monospace; font-size: 36px; font-weight: bold; color: #1D4ED8; line-height: 1.1;">
                --:--:--
            </div>
            <div style="font-size: 11px; font-weight: 700; color: #64748B; letter-spacing: 0.5px;">
                WAKTU INDONESIA BARAT (WIB)
            </div>
        </div>
    </div>
    <script>
        function updateWebClock() {{
            const now = new Date();
            const h = String(now.getHours()).padStart(2, '0');
            const m = String(now.getMinutes()).padStart(2, '0');
            const s = String(now.getSeconds()).padStart(2, '0');
            const el = document.getElementById('live-clock');
            if (el) {{
                el.innerText = `${{h}}:${{m}}:${{s}}`;
            }}
        }}
        updateWebClock();
        setInterval(updateWebClock, 1000);
    </script>
    """
    st.components.v1.html(header_html, height=95)

    # ================= 2. DUA KOLOM UTAMA (PILIH MAHASISWA & 6 TOMBOL AKSI) =================
    col_left, col_right = st.columns([5, 6], gap="large")

    all_pegawai = database.get_all_pegawai(only_active=True)

    with col_left:
        st.markdown("### 🎓 Pilih Nama Mahasiswa")
        
        # Filter Pencarian
        search_query = st.text_input("🔍 Ketik Nama untuk Menyaring:", placeholder="Ketik nama mahasiswa...", key="presensi_search_input")
        
        filtered_pegawai = all_pegawai
        if search_query.strip():
            sq = search_query.strip().lower()
            filtered_pegawai = [p for p in all_pegawai if sq in p["nama"].lower()]

        # Dropdown Mahasiswa
        options = ["-- Pilih Nama Mahasiswa --"] + [p["nama"] for p in filtered_pegawai]
        pegawai_map = {p["nama"]: p for p in filtered_pegawai}

        # Menentukan index pilihan default
        default_idx = 0
        if st.session_state["selected_pegawai_id"]:
            curr_p = database.get_pegawai_by_id(st.session_state["selected_pegawai_id"])
            if curr_p and curr_p["nama"] in options:
                default_idx = options.index(curr_p["nama"])
        elif len(filtered_pegawai) == 1 and search_query.strip():
            default_idx = 1

        selected_option = st.selectbox(
            "Pilih dari Daftar Nama:",
            options=options,
            index=default_idx,
            key="presensi_select_student"
        )

        selected_pegawai = None
        if selected_option in pegawai_map:
            selected_pegawai = pegawai_map[selected_option]
            st.session_state["selected_pegawai_id"] = selected_pegawai["id"]
        elif selected_option == "-- Pilih Nama Mahasiswa --":
            st.session_state["selected_pegawai_id"] = None

        # Profil & Badge Status
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if selected_pegawai:
            today_record = database.get_today_presence_record(selected_pegawai["id"])
            riwayat_kelas = database.get_riwayat_kelas_today(selected_pegawai["id"])
            
            masuk = today_record.get("jam_masuk") or "-" if today_record else "-"
            tugas = today_record.get("jam_bertugas_keluar") or "-" if today_record else "-"
            keluar = today_record.get("jam_keluar") or "-" if today_record else "-"
            status = today_record.get("status") or "Hadir" if today_record else "Belum Presensi"
            
            total_sesi = len(riwayat_kelas)
            total_dur_kelas = database.calculate_total_kelas_duration(riwayat_kelas)
            ringkasan_kelas = database.format_kelas_summary(riwayat_kelas)
            
            kelas_text = f"Kelas ({total_sesi} sesi): {ringkasan_kelas}" if total_sesi > 0 else "Kelas: -"
            if total_dur_kelas != "-":
                kelas_text += f" [Durasi: {total_dur_kelas}]"

            if today_record:
                status_text = f"HARI INI: [Masuk: {masuk}] [{kelas_text}] [Tugas: {tugas}] [Pulang: {keluar}] • {status.upper()}"
            else:
                status_text = "STATUS HARI INI: BELUM PRESENSI"

            # Background color badge
            if status == "Sedang di Kelas":
                badge_bg = "#FEF3C7"
                badge_color = "#92400E"
                border_color = "#FCD34D"
            elif status == "Sedang Tugas Luar":
                badge_bg = "#DBEAFE"
                badge_color = "#1E40AF"
                border_color = "#93C5FD"
            elif status == "Sudah Pulang":
                badge_bg = "#FEE2E2"
                badge_color = "#991B1B"
                border_color = "#FCA5A5"
            elif today_record:
                badge_bg = "#DCFCE7"
                badge_color = "#166534"
                border_color = "#86EFAC"
            else:
                badge_bg = "#F1F5F9"
                badge_color = "#475569"
                border_color = "#CBD5E1"

            profile_card_html = f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px;">
                <div style="font-size: 17px; font-weight: bold; color: #0F172A; margin-bottom: 8px;">
                    🎓 {selected_pegawai['nama']}
                </div>
                <div style="
                    background: {badge_bg};
                    color: {badge_color};
                    border: 1px solid {border_color};
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 11.5px;
                    font-weight: 700;
                    line-height: 1.4;
                ">
                    {status_text}
                </div>
            </div>
            """
            st.markdown(profile_card_html, unsafe_allow_html=True)
        else:
            empty_profile_html = """
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px;">
                <div style="font-size: 15px; font-weight: bold; color: #64748B; margin-bottom: 8px;">
                    Belum ada mahasiswa dipilih
                </div>
                <div style="background: #E2E8F0; color: #475569; border-radius: 6px; padding: 6px 10px; font-size: 11px; font-weight: bold;">
                    STATUS HARI INI: BELUM PRESENSI
                </div>
            </div>
            """
            st.markdown(empty_profile_html, unsafe_allow_html=True)

    with col_right:
        st.markdown("### ⚡ Pilih Aksi Presensi Mahasiswa")

        # 6 Tombol Aksi (Grid 2 Baris x 3 Kolom)
        btn_r1c1, btn_r1c2, btn_r1c3 = st.columns(3)
        with btn_r1c1:
            btn_masuk = st.button("🟢 **JAM MASUK**\n\n(Datang Lab/Kampus)", use_container_width=True, key="btn_masuk")
        with btn_r1c2:
            btn_kelas = st.button("🏫 **JAM KE KELAS**\n\n(Mulai Masuk Kelas)", use_container_width=True, key="btn_kelas")
        with btn_r1c3:
            btn_kembali_kelas = st.button("🔙 **KEMBALI KELAS**\n\n(Selesai Sesi Kelas)", use_container_width=True, key="btn_kembali_kelas")

        btn_r2c1, btn_r2c2, btn_r2c3 = st.columns(3)
        with btn_r2c1:
            btn_tugas = st.button("🚗 **TUGAS KELUAR**\n\n(Tugas Luar Kampus)", use_container_width=True, key="btn_tugas")
        with btn_r2c2:
            btn_kembali_tugas = st.button("🏢 **KEMBALI TUGAS**\n\n(Selesai Tugas Luar)", use_container_width=True, key="btn_kembali_tugas")
        with btn_r2c3:
            btn_keluar = st.button("🚪 **JAM KELUAR**\n\n(Selesai / Pulang)", use_container_width=True, key="btn_keluar")

        # Logika Penanganan Tombol
        if btn_masuk:
            if not selected_pegawai:
                st.session_state["presensi_alert"] = {"type": "error", "msg": "Harap pilih nama mahasiswa dari daftar terlebih dahulu!"}
                st.rerun()
            success, msg, rec = database.record_attendance(selected_pegawai["id"], "masuk")
            st.session_state["presensi_alert"] = {"type": "success" if success else "error", "msg": msg}
            st.rerun()

        if btn_kelas:
            if not selected_pegawai:
                st.session_state["presensi_alert"] = {"type": "error", "msg": "Harap pilih nama mahasiswa dari daftar terlebih dahulu!"}
                st.rerun()
            modal_jam_ke_kelas(selected_pegawai)

        if btn_kembali_kelas:
            if not selected_pegawai:
                st.session_state["presensi_alert"] = {"type": "error", "msg": "Harap pilih nama mahasiswa dari daftar terlebih dahulu!"}
                st.rerun()
            success, msg, rec = database.record_attendance(selected_pegawai["id"], "kembali_kelas")
            st.session_state["presensi_alert"] = {"type": "success" if success else "error", "msg": msg}
            st.rerun()

        if btn_tugas:
            if not selected_pegawai:
                st.session_state["presensi_alert"] = {"type": "error", "msg": "Harap pilih nama mahasiswa dari daftar terlebih dahulu!"}
                st.rerun()
            modal_tugas_keluar(selected_pegawai)

        if btn_kembali_tugas:
            if not selected_pegawai:
                st.session_state["presensi_alert"] = {"type": "error", "msg": "Harap pilih nama mahasiswa dari daftar terlebih dahulu!"}
                st.rerun()
            success, msg, rec = database.record_attendance(selected_pegawai["id"], "kembali")
            st.session_state["presensi_alert"] = {"type": "success" if success else "error", "msg": msg}
            st.rerun()

        if btn_keluar:
            if not selected_pegawai:
                st.session_state["presensi_alert"] = {"type": "error", "msg": "Harap pilih nama mahasiswa dari daftar terlebih dahulu!"}
                st.rerun()
            success, msg, rec = database.record_attendance(selected_pegawai["id"], "keluar")
            st.session_state["presensi_alert"] = {"type": "success" if success else "error", "msg": msg}
            st.rerun()

        # Alert Box / Feedback Toast
        alert_data = st.session_state.get("presensi_alert", {})
        alert_type = alert_data.get("type", "info")
        alert_msg = alert_data.get("msg", "")

        if alert_type == "success":
            st.success(f"✅ {alert_msg}")
        elif alert_type == "error":
            st.error(f"⚠️ {alert_msg}")
        else:
            st.info(f"ℹ️ {alert_msg}")

    # ================= 3. TABEL STATUS & RIWAYAT LIVE HARI INI =================
    st.markdown("---")
    head_t_col1, head_t_col2, head_t_col3 = st.columns([6, 2, 2])
    with head_t_col1:
        st.markdown("#### 📋 Status & Riwayat Presensi Mahasiswa Hari Ini (Live Real-Time)")
    with head_t_col2:
        if st.button("🔄 Segarkan Data", use_container_width=True, key="btn_refresh_today"):
            st.rerun()
    with head_t_col3:
        btn_details = st.button("🔍 Lihat Rincian Sesi Kelas", use_container_width=True, key="btn_detail_session")
        if btn_details:
            if selected_pegawai:
                modal_rincian_sesi_kelas(selected_pegawai)
            else:
                st.warning("Pilih salah satu mahasiswa terlebih dahulu untuk melihat rincian sesi kelas!")

    today_records = database.get_today_presence_table()
    
    if not today_records:
        st.info("Belum ada data mahasiswa terdaftar.")
    else:
        display_rows = []
        for r in today_records:
            display_rows.append({
                "Nama Mahasiswa": r.get("nama", "-"),
                "Jam Masuk": r.get("jam_masuk") or "-",
                "Sesi & Jam Kelas": r.get("display_jam_kelas") or "-",
                "Durasi Kelas": r.get("durasi_total_kelas") or "-",
                "Tugas Luar": r.get("jam_bertugas_keluar") or "-",
                "Kembali Tugas": r.get("jam_kembali") or "-",
                "Jam Keluar": r.get("jam_keluar") or "-",
                "Status Saat Ini": r.get("status") or "Belum Presensi"
            })
        
        st.dataframe(display_rows, width="stretch", hide_index=True)
