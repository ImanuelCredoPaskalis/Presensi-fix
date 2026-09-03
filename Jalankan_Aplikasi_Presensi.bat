@echo off
title Sistem Presensi Mahasiswa & Kelas (Web App) - Lab Micro Teaching FisMat
cd /d "%~dp0"
echo ====================================================
echo   MEMULAI APLIKASI WEB PRESENSI MAHASISWA & KELAS
echo   Lab Micro Teaching FisMat (Streamlit)
echo ====================================================
echo.
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Terjadi kesalahan saat menjalankan aplikasi.
    pause
)
