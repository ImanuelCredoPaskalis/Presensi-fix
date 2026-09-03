# ⚡ Sistem Presensi Mahasiswa & Kelas (Lab Micro Teaching FisMat) - Web App

Aplikasi web modern berbasis **Streamlit** untuk pencatatan presensi kehadiran mahasiswa dan aktivitas kelas secara praktis dan otomatis: **murni berbasis Nama Mahasiswa (tanpa NIM/Barcode/PIN yang rumit)**.

Fokus penuh pada pencatatan **6 waktu utama**:
1. 🟢 **Jam Masuk** (Datang Lab / Kampus)
2. 🏫 **Jam Ke Kelas** (Masuk / Mulai Kelas / Praktikum)
3. 🏢 **Jam Kembali Kelas** (Selesai Kelas / Kembali ke Lab)
4. 🚗 **Jam Tugas Keluar** (Tugas Luar Kampus / Observasi Sekolah)
5. 🏢 **Jam Kembali Tugas** (Selesai Tugas Luar)
6. 🚪 **Jam Keluar** (Selesai / Pulang)

---

## 🚀 Cara Menjalankan Aplikasi

### Cara 1 (Paling Mudah):
Cukup **Double-Click** file:
```
Jalankan_Aplikasi_Presensi.bat
```
*Browser web Anda akan terbuka secara otomatis.*

### Cara 2 (Via Terminal / CMD / PowerShell):
```bash
python main.py
```
atau
```bash
streamlit run web_app.py
```
*Aplikasi dapat diakses di browser pada: `http://localhost:8501`*

---

## ✨ Fitur-Fitur Unggulan

### 1. Terminal Presensi Mahasiswa & Jam Digital Real-Time
- Tampilan **Jam Digital Besar (Detik & Kalender Indonesia)** real-time.
- **Pencarian Nama & Dropdown Mahasiswa**: Cukup ketik nama atau pilih langsung dari daftar mahasiswa.
- **6 Tombol Aksi Intuitif**:
  - **Jam Masuk**: Mencatat kehadiran datang lab/kampus.
  - **Jam Ke Kelas**: Input nama kelas/ruangan/mata kuliah dan mencatat mulai kelas.
  - **Kembali Kelas**: Mencatat kepulangan dari kelas kembali ke lab.
  - **Tugas Keluar**: Input tujuan tugas luar kampus (misal: observasi sekolah mitra).
  - **Kembali Tugas**: Mencatat selesai tugas luar.
  - **Jam Keluar**: Mencatat jam kepulangan / selesai.
- **Live Status Badge & Feedback Alert**: Menampilkan status mahasiswa secara visual dan real-time.

### 2. Dashboard & Live Monitoring
- **6 Kartu Metrik Kehadiran Hari Ini**: Total Mahasiswa, Hadir di Lab, Sedang di Kelas, Sedang Tugas Luar, Sudah Pulang, Belum Absen.
- **Tabel Live Real-Time**: Memantau status seluruh mahasiswa hari ini beserta seluruh kolom jam.
- Filter pencarian nama mahasiswa.

### 3. Data Mahasiswa Ringkas
- Tambah mahasiswa baru dengan mudah: **Nama Lengkap Mahasiswa** (dan no. telepon/WA opsional).
- Edit data dan nama mahasiswa.
- Hapus data mahasiswa (dengan proteksi integritas data).

### 4. Rekapitulasi & Laporan Presensi
- Filter berdasarkan rentang tanggal dan nama mahasiswa.
- Perhitungan otomatis **Durasi Jam Kelas** dan **Durasi Total Kehadiran**.
- **Ekspor ke Excel (.xlsx)** dan **Ekspor ke CSV**.

### 5. Pengaturan Sistem
- Ganti Nama Laboratorium & Alamat / Ruangan Lab.
- Atur Jam Masuk Standar dan Jam Pulang Standar.
- Mode Tampilan (Dark Mode / Light Mode).
- Tombol Reset Database Bersih.

---

## 🗄️ Database Lokal (SQLite)
Database disimpan lokal di file `presensi.db` tanpa memerlukan koneksi internet ataupun server database terpisah.
