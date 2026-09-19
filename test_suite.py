"""
Automated Test Suite for Presensi Mahasiswa & Multi-Sesi Kelas System
Menggunakan Google Sheets sebagai sumber data utama.
"""
import os
import sys
import datetime
import unittest

import database
import export_utils
from config import load_config, save_config

class TestPresensiMahasiswaMultiKelasSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()

    def test_01_mahasiswa_crud(self):
        # Add mahasiswa
        success, msg, p_id = database.add_pegawai("Mahasiswa Multi Kelas Test", telepon="0812999999")
        self.assertTrue(success, f"Failed to add student: {msg}")
        self.assertIsNotNone(p_id)

        # Get by ID
        p = database.get_pegawai_by_id(p_id)
        self.assertIsNotNone(p)
        self.assertEqual(p["nama"], "Mahasiswa Multi Kelas Test")

        # Update
        success, msg = database.update_pegawai(p_id, "Mahasiswa Multi Kelas Test Updated", telepon="0812888888")
        self.assertTrue(success)
        p_updated = database.get_pegawai_by_id(p_id)
        self.assertEqual(p_updated["nama"], "Mahasiswa Multi Kelas Test Updated")

        # Delete
        success, msg = database.delete_pegawai(p_id)
        self.assertTrue(success)

    def test_02_multi_class_sessions_flow(self):
        # Add test student
        success, msg, p_id = database.add_pegawai("Mahasiswa Pengujian Multi Kelas")
        self.assertTrue(success)

        # 1. JAM MASUK
        success, msg, rec = database.record_attendance(p_id, "masuk", custom_time="07:45:00")
        self.assertTrue(success, f"Jam Masuk failed: {msg}")
        self.assertIn("07:45:00", str(rec))

        # 2. SESI KELAS #1 (08:00 - 09:30)
        success_k1, msg_k1, rec_k1 = database.record_attendance(p_id, "kelas", keterangan="Micro Teaching Matematika Kelas A", custom_time="08:00:00")
        self.assertTrue(success_k1, f"Sesi 1 failed: {msg_k1}")

        # Coba masuk kelas lagi saat Sesi #1 masih berlangsung -> harus ditolak
        success_dup, msg_dup, _ = database.record_attendance(p_id, "kelas", keterangan="Kelas Lain", custom_time="08:30:00")
        self.assertFalse(success_dup, "Harus menolak masuk kelas baru saat sesi aktif belum selesai")

        # Selesai Sesi #1 (Kembali Kelas)
        success_end1, msg_end1, rec_end1 = database.record_attendance(p_id, "kembali_kelas", custom_time="09:30:00")
        self.assertTrue(success_end1, f"Kembali Sesi 1 failed: {msg_end1}")

        # 3. SESI KELAS #2 (10:00 - 11:30)
        success_k2, msg_k2, rec_k2 = database.record_attendance(p_id, "kelas", keterangan="Geometri Analitik R.201", custom_time="10:00:00")
        self.assertTrue(success_k2, f"Sesi 2 failed: {msg_k2}")

        # Selesai Sesi #2 (Kembali Kelas)
        success_end2, msg_end2, rec_end2 = database.record_attendance(p_id, "kembali_kelas", custom_time="11:30:00")
        self.assertTrue(success_end2, f"Kembali Sesi 2 failed: {msg_end2}")

        # 4. SESI KELAS #3 (13:00 - 14:30)
        success_k3, msg_k3, rec_k3 = database.record_attendance(p_id, "kelas", keterangan="Praktikum Fisika Dasar", custom_time="13:00:00")
        self.assertTrue(success_k3, f"Sesi 3 failed: {msg_k3}")

        # Selesai Sesi #3 (Kembali Kelas)
        success_end3, msg_end3, rec_end3 = database.record_attendance(p_id, "kembali_kelas", custom_time="14:30:00")
        self.assertTrue(success_end3, f"Kembali Sesi 3 failed: {msg_end3}")

        # 5. JAM KELUAR (SELESAI / PULANG)
        success_out, msg_out, rec_out = database.record_attendance(p_id, "keluar", custom_time="17:00:00")
        self.assertTrue(success_out, f"Jam Keluar failed: {msg_out}")

        # 6. VERIFIKASI RIWAYAT & DURASI KUMULATIF
        riwayat = database.get_riwayat_kelas_today(p_id)
        self.assertEqual(len(riwayat), 3, "Harus ada tepat 3 sesi kelas")
        self.assertEqual(riwayat[0]["keterangan"], "Micro Teaching Matematika Kelas A")
        self.assertEqual(riwayat[1]["keterangan"], "Geometri Analitik R.201")
        self.assertEqual(riwayat[2]["keterangan"], "Praktikum Fisika Dasar")

        # Sesi 1: 1j 30m, Sesi 2: 1j 30m, Sesi 3: 1j 30m -> Total 4j 30m
        total_dur = database.calculate_total_kelas_duration(riwayat)
        self.assertEqual(total_dur, "4j 30m")

        # Format ringkasan
        summary_str = database.format_kelas_summary(riwayat)
        self.assertIn("Micro Teaching", summary_str)
        self.assertIn("Geometri", summary_str)
        self.assertIn("Praktikum", summary_str)

        # Verifikasi Durasi Shift: Total (07:45 - 17:00 = 9j 15m) dikurang Kelas (4j 30m) = 4j 45m
        durasi_shift = database.calculate_durasi_shift("07:45:00", "17:00:00", riwayat_kelas_list=riwayat)
        self.assertEqual(durasi_shift, "4j 45m")

    def test_03_summary_and_reports(self):
        summary = database.get_today_summary()
        self.assertIn("total_pegawai", summary)
        self.assertIn("hadir", summary)
        self.assertIn("sedang_kelas", summary)
        self.assertIn("pulang", summary)

        records = database.get_presensi_history()
        self.assertTrue(len(records) > 0)

        # Test Export Excel memuat kolom Durasi Shift dan Izin
        excel_path = "test_multi_kelas.xlsx"
        export_utils.export_to_excel(records, excel_path)
        self.assertTrue(os.path.exists(excel_path))
        import openpyxl
        wb = openpyxl.load_workbook(excel_path)
        sheet = wb.active
        headers = [cell.value for cell in sheet[4]]
        self.assertIn("Durasi Shift", headers)
        self.assertIn("Izin Keluar", headers)
        self.assertIn("Kembali Shift", headers)
        self.assertIn("Total Durasi Izin", headers)
        self.assertNotIn("Durasi Total", headers)
        wb.close()
        os.remove(excel_path)

        # Test Export CSV memuat kolom Durasi Shift dan Izin
        csv_path = "test_multi_kelas.csv"
        export_utils.export_to_csv(records, csv_path)
        self.assertTrue(os.path.exists(csv_path))
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            first_line = f.readline()
            self.assertIn("Durasi Shift", first_line)
            self.assertIn("Jam Izin Keluar", first_line)
            self.assertIn("Total Durasi Izin", first_line)
            self.assertNotIn("Durasi Total", first_line)
        os.remove(csv_path)

    def test_04_durasi_shift_edge_cases(self):
        # 1. Kasus tanpa kelas: 08:00 - 16:00 -> 8j 0m
        self.assertEqual(database.calculate_durasi_shift("08:00:00", "16:00:00"), "8j 0m")

        # 2. Kasus dengan string kelas: 08:00 - 17:00 (9j) dikurang 2j 30m -> 6j 30m
        self.assertEqual(database.calculate_durasi_shift("08:00:00", "17:00:00", durasi_kelas_str="2j 30m"), "6j 30m")

        # 3. Kasus durasi kelas lebih besar dari total durasi (clamp ke 0)
        self.assertEqual(database.calculate_durasi_shift("08:00:00", "09:00:00", durasi_kelas_str="2j 0m"), "0j 0m")

        # 4. Kasus belum keluar (jam_keluar None / '-')
        self.assertEqual(database.calculate_durasi_shift("08:00:00", None), "-")
        self.assertEqual(database.calculate_durasi_shift(None, "17:00:00"), "-")

        # 5. Kasus format waktu terbalik
        self.assertEqual(database.calculate_durasi_shift("17:00:00", "08:00:00"), "-")

        # 6. Kasus kombinasi kelas dan izin: Masuk 08:00 - Keluar 17:00 (9j 0m), Kelas 1j 30m, Izin 1j 0m -> 6j 30m
        self.assertEqual(
            database.calculate_durasi_shift("08:00:00", "17:00:00", durasi_kelas_str="1j 30m", durasi_izin_str="1j 0m"),
            "6j 30m"
        )

    def test_05_izin_keluar_flow(self):
        success, msg, p_id = database.add_pegawai("Mahasiswa Pengujian Izin")
        self.assertTrue(success)

        # 1. JAM MASUK 08:00:00
        success, msg, rec = database.record_attendance(p_id, "masuk", custom_time="08:00:00")
        self.assertTrue(success)

        # 2. IZIN KELUAR 10:00:00
        success_iz, msg_iz, rec_iz = database.record_attendance(p_id, "izin_keluar", keterangan="Keperluan Administrasi", custom_time="10:00:00")
        self.assertTrue(success_iz)
        self.assertEqual(rec_iz["status"], "Sedang Izin Keluar")

        # Coba izin lagi sebelum kembali -> harus ditolak
        dup_iz, _, _ = database.record_attendance(p_id, "izin_keluar", custom_time="10:30:00")
        self.assertFalse(dup_iz, "Harus menolak izin keluar baru saat sesi izin aktif masih berlangsung")

        # 3. KEMBALI SHIFT 11:30:00
        success_kb, msg_kb, rec_kb = database.record_attendance(p_id, "kembali_shift", custom_time="11:30:00")
        self.assertTrue(success_kb)
        self.assertEqual(rec_kb["status"], "Hadir di Lab")

        # 4. SESI KELAS 13:00 - 14:30
        database.record_attendance(p_id, "kelas", keterangan="Micro Teaching B", custom_time="13:00:00")
        database.record_attendance(p_id, "kembali_kelas", custom_time="14:30:00")

        # 5. JAM KELUAR / PULANG 17:00:00
        success_out, msg_out, rec_out = database.record_attendance(p_id, "keluar", custom_time="17:00:00")
        self.assertTrue(success_out)
        self.assertEqual(rec_out["status"], "Sudah Pulang")

        # 6. VERIFIKASI RIWAYAT IZIN & DURASI SHIFT
        riwayat_izin = database.get_riwayat_izin_today(p_id)
        self.assertEqual(len(riwayat_izin), 1)
        self.assertEqual(riwayat_izin[0]["keterangan"], "Keperluan Administrasi")
        dur_izin = database.calculate_total_izin_duration(riwayat_izin)
        self.assertEqual(dur_izin, "1j 30m")

    def test_06_wib_timezone_consistency(self):
        wib_now = database.get_wib_now()
        # Verifikasi offset WIB adalah +07:00 (7 jam dari UTC)
        tz_offset = wib_now.utcoffset()
        self.assertIsNotNone(tz_offset)
        self.assertEqual(tz_offset.total_seconds(), 7 * 3600)

        # Verifikasi get_today_str dan get_current_time_str sesuai dengan get_wib_now()
        self.assertEqual(database.get_today_str(), wib_now.strftime("%Y-%m-%d"))
        time_str = database.get_current_time_str()
        self.assertEqual(len(time_str), 8)
        self.assertEqual(time_str[:2], wib_now.strftime("%H"))

    def test_07_get_all_pegawai(self):
        all_pegawai = database.get_all_pegawai(only_active=True)
        self.assertIsInstance(all_pegawai, list)

        # Get by ID
        if all_pegawai:
            p = database.get_pegawai_by_id(all_pegawai[0]["id"])
            self.assertIsNotNone(p)
            self.assertIn("nama", p)

    def test_08_get_list_departemen(self):
        deps = database.get_list_departemen()
        self.assertIsInstance(deps, list)
        self.assertTrue(len(deps) > 0)
