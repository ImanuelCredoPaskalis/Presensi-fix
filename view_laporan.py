"""
View Web: Rekapitulasi & Laporan Presensi Mahasiswa (Murni Berbasis Nama Mahasiswa)
Mendukung Multi-Sesi Kelas, Rincian Jam Kelas, Durasi Akumulatif, dan Ekspor Excel/CSV
"""
import streamlit as st
import datetime
import database
import export_utils

@st.dialog("🔍 Rincian Sesi Kelas")
def modal_rincian_laporan(presensi_record):
    st.markdown(f"### 📚 Rincian Sesi Kelas: {presensi_record.get('nama')}")
    riwayat_kelas = presensi_record.get("riwayat_kelas_list", [])
    total_dur = presensi_record.get("durasi_total_kelas", "-")
    st.caption(f"Tanggal: **{presensi_record.get('tanggal')}** • Total: **{len(riwayat_kelas)} Sesi Kelas** • Total Durasi: **{total_dur}**")

    if not riwayat_kelas:
        st.info("Tidak ada aktivitas kelas pada tanggal ini.")
    else:
        tbl_data = []
        for idx, r in enumerate(riwayat_kelas, 1):
            m = r.get("jam_masuk_kelas") or "-"
            k = r.get("jam_kembali_kelas") or "(Sedang di Kelas)"
            dur = database.calculate_time_diff_hours(r.get("jam_masuk_kelas"), r.get("jam_kembali_kelas"))
            ket = r.get("keterangan") or "-"
            tbl_data.append({
                "Sesi #": f"Sesi #{idx}",
                "Jam Masuk": m,
                "Jam Kembali": k,
                "Durasi": dur,
                "Nama Kelas / Mata Kuliah / Ruangan": ket
            })
        st.table(tbl_data)

    if st.button("Tutup", use_container_width=True):
        st.rerun()

@st.dialog("☕ Rincian Sesi Izin Keluar")
def modal_rincian_izin_laporan(presensi_record):
    st.markdown(f"### ☕ Rincian Sesi Izin: {presensi_record.get('nama')}")
    riwayat_izin = presensi_record.get("riwayat_izin_list", [])
    total_dur = presensi_record.get("durasi_total_izin", "-")
    st.caption(f"Tanggal: **{presensi_record.get('tanggal')}** • Total: **{len(riwayat_izin)} Sesi Izin** • Total Durasi Izin: **{total_dur}**")

    if not riwayat_izin:
        st.info("Tidak ada aktivitas izin keluar pada tanggal ini.")
    else:
        tbl_data = []
        for idx, r in enumerate(riwayat_izin, 1):
            m = r.get("jam_izin_keluar") or "-"
            k = r.get("jam_kembali_izin") or "(Sedang Izin Keluar)"
            dur = database.calculate_time_diff_hours(r.get("jam_izin_keluar"), r.get("jam_kembali_izin"))
            ket = r.get("keterangan") or "-"
            tbl_data.append({
                "Sesi #": f"Sesi #{idx}",
                "Jam Izin": m,
                "Jam Kembali Shift": k,
                "Durasi": dur,
                "Alasan / Keperluan": ket
            })
        st.table(tbl_data)

    if st.button("Tutup", use_container_width=True, key="btn_close_modal_izin"):
        st.rerun()

def render_laporan_view():
    all_pegawai = database.get_all_pegawai(only_active=False)

    # Inisialisasi filter state
    today = datetime.date.today()
    default_start = today - datetime.timedelta(days=30)
    
    if "filter_start_date" not in st.session_state:
        st.session_state["filter_start_date"] = default_start
    if "filter_end_date" not in st.session_state:
        st.session_state["filter_end_date"] = today
    if "filter_pegawai_id" not in st.session_state:
        st.session_state["filter_pegawai_id"] = None

    # Header & Action buttons
    h_col1, h_col2, h_col3 = st.columns([5.5, 2.5, 2])
    with h_col1:
        st.markdown("### 📑 Rekapitulasi & Laporan Presensi Mahasiswa")

    # ================= CARD FILTER =================
    with st.container():
        f_col1, f_col2, f_col3, f_col4 = st.columns([2.5, 2.5, 3.5, 1.5])
        with f_col1:
            start_date_val = st.date_input("Mulai Tanggal:", value=st.session_state["filter_start_date"], key="laporan_start_date")
        with f_col2:
            end_date_val = st.date_input("Sampai Tanggal:", value=st.session_state["filter_end_date"], key="laporan_end_date")
        with f_col3:
            pgw_options = ["Semua Mahasiswa"] + [p["nama"] for p in all_pegawai]
            pgw_map = {p["nama"]: p["id"] for p in all_pegawai}
            
            # Default selection
            curr_sel_idx = 0
            if st.session_state["filter_pegawai_id"]:
                p_obj = database.get_pegawai_by_id(st.session_state["filter_pegawai_id"])
                if p_obj and p_obj["nama"] in pgw_options:
                    curr_sel_idx = pgw_options.index(p_obj["nama"])

            selected_pgw = st.selectbox("Pilih Nama Mahasiswa:", options=pgw_options, index=curr_sel_idx, key="laporan_pegawai_select")
        with f_col4:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("↺ Reset", use_container_width=True):
                st.session_state["filter_start_date"] = default_start
                st.session_state["filter_end_date"] = today
                st.session_state["filter_pegawai_id"] = None
                st.rerun()

    # Hitung pegawai_id untuk query
    filter_p_id = None
    if selected_pgw != "Semua Mahasiswa" and selected_pgw in pgw_map:
        filter_p_id = pgw_map[selected_pgw]

    # Query riwayat
    start_str = start_date_val.strftime("%Y-%m-%d") if start_date_val else None
    end_str = end_date_val.strftime("%Y-%m-%d") if end_date_val else None

    records = database.get_presensi_history(
        start_date=start_str,
        end_date=end_str,
        pegawai_id=filter_p_id
    )

    # Siapkan data ekspor
    today_stamp = datetime.date.today().strftime("%Y%m%d")
    with h_col2:
        if records:
            excel_bytes = export_utils.get_excel_bytes(records, start_str, end_str)
            st.download_button(
                label="📊 Ekspor ke Excel (.xlsx)",
                data=excel_bytes,
                file_name=f"Rekap_Presensi_Mahasiswa_{today_stamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.button("📊 Ekspor ke Excel (.xlsx)", disabled=True, use_container_width=True)

    with h_col3:
        if records:
            csv_bytes = export_utils.get_csv_bytes(records)
            st.download_button(
                label="📄 Ekspor ke CSV",
                data=csv_bytes,
                file_name=f"Rekap_Presensi_Mahasiswa_{today_stamp}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.button("📄 Ekspor ke CSV", disabled=True, use_container_width=True)

    st.markdown("---")

    # Info bar & tip
    i_col1, i_col2 = st.columns([6, 4])
    with i_col1:
        st.markdown(f"**Total Ditemukan: {len(records)} Catatan Presensi Mahasiswa**")
    with i_col2:
        st.caption("💡 *Tip: Gunakan opsi di bawah tabel untuk memeriksa detail sesi kelas.*")

    if not records:
        st.info("Tidak ada riwayat presensi yang ditemukan untuk filter yang dipilih.")
    else:
        table_rows = []
        for idx, r in enumerate(records, 1):
            total_sesi = r.get("total_sesi_kelas", 0)
            sesi_str = f"{total_sesi} Sesi" if total_sesi > 0 else "-"
            rincian_kelas = r.get("ringkasan_kelas") or "-"
            durasi_kelas = r.get("durasi_total_kelas") or "-"
            durasi_total_izin = r.get("durasi_total_izin") or "-"
            durasi_shift = r.get("durasi_shift")
            if not durasi_shift or durasi_shift == "-":
                durasi_shift = database.calculate_durasi_shift(
                    r.get("jam_masuk"),
                    r.get("jam_keluar"),
                    riwayat_kelas_list=r.get("riwayat_kelas_list"),
                    durasi_kelas_str=durasi_kelas,
                    riwayat_izin_list=r.get("riwayat_izin_list"),
                    durasi_izin_str=durasi_total_izin
                )

            table_rows.append({
                "No": idx,
                "Tanggal": r.get("tanggal", "-"),
                "Nama Mahasiswa": r.get("nama", "-"),
                "Jam Masuk": r.get("jam_masuk") or "-",
                "Sesi": sesi_str,
                "Rincian Jam & Nama Kelas": rincian_kelas,
                "Durasi Kelas": durasi_kelas,
                "Tugas Luar": r.get("jam_bertugas_keluar") or "-",
                "Kembali Tugas": r.get("jam_kembali") or "-",
                "Izin Keluar": r.get("display_jam_izin") or "-",
                "Durasi Izin": durasi_total_izin,
                "Jam Keluar": r.get("jam_keluar") or "-",
                "Durasi Shift": durasi_shift,
                "Status": r.get("status") or "Hadir"
            })

        st.dataframe(table_rows, width="stretch", hide_index=True)

        # Pemeriksa Rincian Sesi Kelas & Izin
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        with st.expander("🔍 **Pemeriksa Rincian Sesi Kelas & Sesi Izin Berdasarkan Catatan**"):
            inspect_options = [f"Baris #{idx}: {r.get('tanggal')} - {r.get('nama')}" for idx, r in enumerate(records, 1)]
            selected_inspect = st.selectbox("Pilih Catatan untuk Diperiksa:", inspect_options)
            sel_idx = int(selected_inspect.split(":")[0].replace("Baris #", "")) - 1
            exp_col1, exp_col2 = st.columns(2)
            with exp_col1:
                if st.button("📚 Buka Rincian Sesi Kelas", use_container_width=True):
                    modal_rincian_laporan(records[sel_idx])
            with exp_col2:
                if st.button("☕ Buka Rincian Sesi Izin", use_container_width=True):
                    modal_rincian_izin_laporan(records[sel_idx])
