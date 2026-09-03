"""
Aplikasi Web: Sistem Presensi Mahasiswa & Kelas (Lab Micro Teaching FisMat)
Titik Masuk Utama (Main Entry Point) Berbasis Streamlit
"""
import sys
import os
import database

def main():
    # Pastikan direktori kerja benar
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)

    # Inisialisasi Database SQLite
    database.init_db()

    # Jalankan Aplikasi Web Streamlit
    from streamlit.web import cli as stcli
    app_path = os.path.join(current_dir, "web_app.py")
    sys.argv = ["streamlit", "run", app_path]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
