"""
View Web: Manajemen Master Data Mahasiswa (Murni Nama Mahasiswa)
Tambah, Edit, dan Hapus Mahasiswa dengan Modal Dialog
"""
import streamlit as st
import database

@st.dialog("➕ Tambah Mahasiswa Baru")
def modal_tambah_mahasiswa():
    st.write("Silakan masukkan data mahasiswa baru:")
    nama_input = st.text_input("Nama Lengkap Mahasiswa *", placeholder="Contoh: Budi Santoso")
    telp_input = st.text_input("No. Telepon / WhatsApp (Opsional)", placeholder="Contoh: 081234567890")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("💾 Simpan Data", type="primary", use_container_width=True):
            clean_nama = nama_input.strip()
            if not clean_nama:
                st.error("Nama Lengkap Mahasiswa wajib diisi!")
            else:
                success, msg, _ = database.add_pegawai(clean_nama, telepon=telp_input.strip())
                if success:
                    st.session_state["pegawai_alert"] = {"type": "success", "msg": msg}
                else:
                    st.session_state["pegawai_alert"] = {"type": "error", "msg": msg}
                st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()

@st.dialog("✏️ Edit Nama Mahasiswa")
def modal_edit_mahasiswa(all_pegawai):
    if not all_pegawai:
        st.warning("Belum ada data mahasiswa untuk diedit.")
        if st.button("Tutup", use_container_width=True):
            st.rerun()
        return

    student_names = [p["nama"] for p in all_pegawai]
    selected_name = st.selectbox("Pilih Mahasiswa yang Ingin Diedit:", student_names)
    target_p = next((p for p in all_pegawai if p["nama"] == selected_name), None)

    if target_p:
        nama_input = st.text_input("Nama Lengkap Mahasiswa *", value=target_p["nama"])
        telp_input = st.text_input("No. Telepon / WhatsApp (Opsional)", value=target_p["telepon"] or "")
        status_option = st.selectbox("Status Keaktifan:", ["Aktif", "Non-Aktif"], index=0 if target_p["status_aktif"] == 1 else 1)

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("💾 Simpan Perubahan", type="primary", use_container_width=True):
                clean_nama = nama_input.strip()
                if not clean_nama:
                    st.error("Nama Lengkap Mahasiswa wajib diisi!")
                else:
                    status_val = 1 if status_option == "Aktif" else 0
                    success, msg = database.update_pegawai(target_p["id"], clean_nama, telepon=telp_input.strip(), status_aktif=status_val)
                    if success:
                        st.session_state["pegawai_alert"] = {"type": "success", "msg": msg}
                    else:
                        st.session_state["pegawai_alert"] = {"type": "error", "msg": msg}
                    st.rerun()
        with col2:
            if st.button("Batal", use_container_width=True):
                st.rerun()

@st.dialog("🗑️ Hapus Data Mahasiswa")
def modal_hapus_mahasiswa(all_pegawai):
    if not all_pegawai:
        st.warning("Belum ada data mahasiswa untuk dihapus.")
        if st.button("Tutup", use_container_width=True):
            st.rerun()
        return

    student_names = [p["nama"] for p in all_pegawai]
    selected_name = st.selectbox("Pilih Mahasiswa yang Ingin Dihapus:", student_names)
    target_p = next((p for p in all_pegawai if p["nama"] == selected_name), None)

    if target_p:
        st.warning(f"Apakah Anda yakin ingin menghapus data mahasiswa:\n\n**{target_p['nama']}**?")
        st.caption("ℹ️ Jika mahasiswa memiliki riwayat presensi, sistem akan mengubah status menjadi Non-Aktif agar riwayat tetap terjaga.")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🗑️ Ya, Hapus Mahasiswa", type="primary", use_container_width=True):
                success, msg = database.delete_pegawai(target_p["id"])
                if success:
                    st.session_state["pegawai_alert"] = {"type": "success", "msg": msg}
                else:
                    st.session_state["pegawai_alert"] = {"type": "error", "msg": msg}
                st.rerun()
        with col2:
            if st.button("Batal", use_container_width=True):
                st.rerun()

def render_pegawai_view():
    all_pegawai = database.get_all_pegawai(only_active=False)

    # Header & Action buttons
    h_col1, h_col2, h_col3, h_col4 = st.columns([5, 2.3, 2, 1.7])
    with h_col1:
        st.markdown("### 🎓 Manajemen Data Mahasiswa")
    with h_col2:
        if st.button("➕ Tambah Mahasiswa", type="primary", use_container_width=True):
            modal_tambah_mahasiswa()
    with h_col3:
        if st.button("✏️ Edit Nama", use_container_width=True):
            modal_edit_mahasiswa(all_pegawai)
    with h_col4:
        if st.button("🗑️ Hapus", use_container_width=True):
            modal_hapus_mahasiswa(all_pegawai)

    # Feedback alert
    if "pegawai_alert" in st.session_state:
        alert_data = st.session_state["pegawai_alert"]
        if alert_data["type"] == "success":
            st.success(alert_data["msg"])
        else:
            st.error(alert_data["msg"])
        del st.session_state["pegawai_alert"]

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Filter bar
    f_col1, f_col2 = st.columns([7, 3])
    with f_col1:
        st.markdown(f"**Total: {len(all_pegawai)} Mahasiswa Terdaftar**")
    with f_col2:
        search_q = st.text_input("🔍", placeholder="Cari Nama Mahasiswa...", label_visibility="collapsed", key="pegawai_search_input")

    filtered = all_pegawai
    if search_q.strip():
        sq = search_q.strip().lower()
        filtered = [p for p in all_pegawai if sq in p["nama"].lower() or (p.get("telepon") and sq in p["telepon"])]

    if not filtered:
        st.info("Tidak ada data mahasiswa yang cocok dengan pencarian.")
    else:
        table_rows = []
        for idx, p in enumerate(filtered, 1):
            status_str = "Aktif" if p["status_aktif"] == 1 else "Non-Aktif"
            table_rows.append({
                "No": idx,
                "Nama Lengkap Mahasiswa": p["nama"],
                "No. Telepon / WhatsApp": p["telepon"] or "-",
                "Status": status_str
            })

        st.dataframe(table_rows, width="stretch", hide_index=True)
