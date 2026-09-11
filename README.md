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
- **8 Tombol Aksi Intuitif**:
  - **Jam Masuk**: Mencatat kehadiran datang lab/kampus.
  - **Jam Ke Kelas**: Input nama kelas/ruangan/mata kuliah dan mencatat mulai kelas.
  - **Kembali Kelas**: Mencatat kepulangan dari kelas kembali ke lab.
  - **Tugas Keluar**: Input tujuan tugas luar kampus (misal: observasi sekolah mitra).
  - **Kembali Tugas**: Mencatat selesai tugas luar.
  - **Izin Keluar**: Input alasan izin sementara keluar lab (misal: keperluan pribadi, makan).
  - **Kembali Shift**: Mencatat waktu kembali ke lab untuk melanjutkan shift.
  - **Jam Keluar**: Mencatat jam kepulangan / selesai.
- **Live Status Badge & Feedback Alert**: Menampilkan status mahasiswa secara visual dan real-time.

### 2. Dashboard & Live Monitoring
- **7 Kartu Metrik Kehadiran Hari Ini**: Total Mahasiswa, Hadir di Lab, Sedang di Kelas, Sedang Tugas, Sedang Izin, Sudah Pulang, Belum Absen.
- **Tabel Live Real-Time**: Memantau status seluruh mahasiswa hari ini beserta seluruh kolom jam.
- Filter pencarian nama mahasiswa.

### 3. Data Mahasiswa Ringkas
- Tambah mahasiswa baru dengan mudah: **Nama Lengkap Mahasiswa** (dan no. telepon/WA opsional).
- Edit data dan nama mahasiswa.
- Hapus data mahasiswa (dengan proteksi integritas data).

### 4. Rekapitulasi & Laporan Presensi
- Filter berdasarkan rentang tanggal dan nama mahasiswa.
- Perhitungan otomatis **Durasi Jam Kelas**, **Durasi Izin Keluar**, dan **Durasi Shift Mahasiswa** (Total Kehadiran dikurang Durasi Kelas dan Durasi Izin).
- **Ekspor ke Excel (.xlsx)** dan **Ekspor ke CSV**.

### 5. Pengaturan Sistem
- Ganti Nama Laboratorium & Alamat / Ruangan Lab.
- Atur Jam Masuk Standar dan Jam Pulang Standar.
- Mode Tampilan (Dark Mode / Light Mode).
- Tombol Reset Database Bersih.

---

## 🗄️ Penyimpanan Data: Mode Ganda (Google Sheets Cloud & SQLite Lokal)

Aplikasi ini mendukung **penyimpanan hybrid berkecepatan tinggi**:
1. **Google Sheets (Cloud Online)**:
   - Data otomatis tersinkronisasi dua arah secara *real-time* ke **Google Spreadsheet** di Google Drive Anda.
   - Siapapun yang presensi dari HP/laptop melalui link Streamlit Cloud, datanya langsung tercatat permanen di Google Sheets.
   - Tidak akan hilang meski server Streamlit Cloud tertidur (*sleep*) atau di-restart.
2. **SQLite Lokal (`presensi.db`)**:
   - Berfungsi sebagai *local cache* berkecepatan tinggi sehingga antarmuka Streamlit berjalan instan tanpa jeda loading.
   - Tetap dapat digunakan 100% secara *offline* di laptop/komputer lab tanpa internet.

---

## ☁️ Cara Menghubungkan Google Sheets (Hanya 2 Menit)

1. Buka [Google Drive](https://drive.google.com), lalu unggah file:
   ```text
   migrasi_data_presensi_google_sheets.xlsx
   ```
   *(Seluruh data 5 mahasiswa dan 39 riwayat presensi yang sudah ada akan otomatis masuk)*.
2. Buka file tersebut dengan **Google Spreadsheet**.
3. Klik menu **Ekstensi (Extensions)** > **Apps Script**.
4. Hapus semua kode default, lalu tempel (paste) seluruh isi file [`google_apps_script.js`](./google_apps_script.js).
5. Klik **Terapkan (Deploy)** > **Penerapan Baru (New Deployment)**:
   - Pilih jenis: **Aplikasi Web (Web App)**
   - Jalankan sebagai: **Saya (Email Anda)**
   - Siapa yang memiliki akses: **Siapa saja (Anyone)**
6. Klik **Terapkan**, lalu salin **URL Aplikasi Web** yang muncul.
7. Tempelkan URL tersebut ke:
   - Menu **Pengaturan** di dalam aplikasi, ATAU
   - Di menu **Settings > Secrets** di Streamlit Community Cloud:
     ```toml
     gsheets_webhook_url = "https://script.google.com/macros/s/AKfycb.../exec"
     ```

