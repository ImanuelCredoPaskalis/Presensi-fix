"""
Automated Test Suite for Presensi Mahasiswa & Multi-Sesi Kelas System
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
        success, msg, p_id = database.add_pegawai("Mahasiswa Multi Kelas", telepon="0812999999")
        self.assertTrue(success, f"Failed to add student: {msg}")
        self.assertIsNotNone(p_id)

        # Get by ID
        p = database.get_pegawai_by_id(p_id)
        self.assertIsNotNone(p)
        self.assertEqual(p["nama"], "Mahasiswa Multi Kelas")

        # Update
        success, msg = database.update_pegawai(p_id, "Mahasiswa Multi Kelas Updated", telepon="0812888888")
        self.assertTrue(success)
        p_updated = database.get_pegawai_by_id(p_id)
        self.assertEqual(p_updated["nama"], "Mahasiswa Multi Kelas Updated")

    def test_02_multi_class_sessions_flow(self):
        # Gunakan mahasiswa untuk test multi-kelas
        success, msg, p_id = database.add_pegawai("Mahasiswa Pengujian Multi Kelas")
        self.assertTrue(success)

        # Reset presensi & riwayat kelas hari ini
        conn = database.get_connection()
        conn.cursor().execute("DELETE FROM presensi WHERE pegawai_id = ? AND tanggal = ?", (p_id, database.get_today_str()))
        conn.cursor().execute("DELETE FROM riwayat_kelas WHERE pegawai_id = ? AND tanggal = ?", (p_id, database.get_today_str()))
        conn.commit()
        conn.close()

        # 1. JAM MASUK
        success, msg, rec = database.record_attendance(p_id, "masuk", custom_time="07:45:00")
        self.assertTrue(success, f"Jam Masuk failed: {msg}")
        self.assertEqual(rec["jam_masuk"], "07:45:00")

        # 2. SESI KELAS #1 (08:00 - 09:30)
        success_k1, msg_k1, rec_k1 = database.record_attendance(p_id, "kelas", keterangan="Micro Teaching Matematika Kelas A", custom_time="08:00:00")
        self.assertTrue(success_k1, f"Sesi 1 failed: {msg_k1}")
        self.assertEqual(rec_k1["status"], "Sedang di Kelas")

        # Coba masuk kelas lagi saat Sesi #1 masih berlangsung -> harus ditolak
        success_dup, msg_dup, _ = database.record_attendance(p_id, "kelas", keterangan="Kelas Lain", custom_time="08:30:00")
        self.assertFalse(success_dup, "Harus menolak masuk kelas baru saat sesi aktif belum selesai")

        # Selesai Sesi #1 (Kembali Kelas)
        success_end1, msg_end1, rec_end1 = database.record_attendance(p_id, "kembali_kelas", custom_time="09:30:00")
        self.assertTrue(success_end1, f"Kembali Sesi 1 failed: {msg_end1}")
        self.assertEqual(rec_end1["status"], "Hadir di Lab")

        # 3. SESI KELAS #2 (10:00 - 11:30)
        success_k2, msg_k2, rec_k2 = database.record_attendance(p_id, "kelas", keterangan="Geometri Analitik R.201", custom_time="10:00:00")
        self.assertTrue(success_k2, f"Sesi 2 failed: {msg_k2}")
        self.assertEqual(rec_k2["status"], "Sedang di Kelas")

        # Selesai Sesi #2 (Kembali Kelas)
        success_end2, msg_end2, rec_end2 = database.record_attendance(p_id, "kembali_kelas", custom_time="11:30:00")
        self.assertTrue(success_end2, f"Kembali Sesi 2 failed: {msg_end2}")
        self.assertEqual(rec_end2["status"], "Hadir di Lab")

        # 4. SESI KELAS #3 (13:00 - 14:30)
        success_k3, msg_k3, rec_k3 = database.record_attendance(p_id, "kelas", keterangan="Praktikum Fisika Dasar", custom_time="13:00:00")
        self.assertTrue(success_k3, f"Sesi 3 failed: {msg_k3}")
        self.assertEqual(rec_k3["status"], "Sedang di Kelas")

        # Selesai Sesi #3 (Kembali Kelas)
        success_end3, msg_end3, rec_end3 = database.record_attendance(p_id, "kembali_kelas", custom_time="14:30:00")
        self.assertTrue(success_end3, f"Kembali Sesi 3 failed: {msg_end3}")
        self.assertEqual(rec_end3["status"], "Hadir di Lab")

        # 5. JAM KELUAR (SELESAI / PULANG)
        success_out, msg_out, rec_out = database.record_attendance(p_id, "keluar", custom_time="17:00:00")
        self.assertTrue(success_out, f"Jam Keluar failed: {msg_out}")
        self.assertEqual(rec_out["status"], "Sudah Pulang")

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

    def test_03_summary_and_reports(self):
        summary = database.get_today_summary()
        self.assertIn("total_pegawai", summary)
        self.assertIn("hadir", summary)
        self.assertIn("sedang_kelas", summary)
        self.assertIn("pulang", summary)

        records = database.get_presensi_history()
        self.assertTrue(len(records) > 0)

        # Test Export Excel
        excel_path = "test_multi_kelas.xlsx"
        export_utils.export_to_excel(records, excel_path)
        self.assertTrue(os.path.exists(excel_path))
        os.remove(excel_path)

        # Test Export CSV
        csv_path = "test_multi_kelas.csv"
        export_utils.export_to_csv(records, csv_path)
        self.assertTrue(os.path.exists(csv_path))
        os.remove(csv_path)

    def test_04_auto_close_active_class_on_clockout(self):
        success, msg, p_id = database.add_pegawai("Mahasiswa Auto Close Class")
        self.assertTrue(success)

        # Reset presensi hari ini
        conn = database.get_connection()
        conn.cursor().execute("DELETE FROM presensi WHERE pegawai_id = ? AND tanggal = ?", (p_id, database.get_today_str()))
        conn.cursor().execute("DELETE FROM riwayat_kelas WHERE pegawai_id = ? AND tanggal = ?", (p_id, database.get_today_str()))
        conn.commit()
        conn.close()

        # Langsung masuk kelas Sesi 1
        database.record_attendance(p_id, "kelas", keterangan="Sesi Kelas Sore", custom_time="15:00:00")
        
        # Langsung pulang jam 17:00 tanpa klik kembali kelas
        success_out, _, rec_out = database.record_attendance(p_id, "keluar", custom_time="17:00:00")
        self.assertTrue(success_out)
        self.assertEqual(rec_out["status"], "Sudah Pulang")

        # Cek sesi kelas otomatis ditutup
        riwayat = database.get_riwayat_kelas_today(p_id)
        self.assertEqual(len(riwayat), 1)
        self.assertEqual(riwayat[0]["jam_kembali_kelas"], "17:00:00")

if __name__ == "__main__":
    unittest.main(verbosity=2)
