"""
Migrate to Sheets Utility
Membaca seluruh data dari database SQLite lokal (presensi.db)
dan mengekspornya ke format multi-sheet Excel (.xlsx) untuk diunggah langsung ke Google Drive / Google Sheets,
atau menyinkronkannya secara otomatis ke Google Sheets via API.
"""
import os
import sqlite3
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from config import DB_PATH

OUTPUT_EXCEL = "migrasi_data_presensi_google_sheets.xlsx"

TABLES_TO_EXPORT = [
    ("pegawai", "mahasiswa"),
    ("presensi", "presensi"),
    ("riwayat_kelas", "riwayat_kelas"),
    ("riwayat_izin", "riwayat_izin"),
    ("riwayat_tugas_luar", "riwayat_tugas_luar")
]

def export_sqlite_to_excel(db_path=DB_PATH, output_file=OUTPUT_EXCEL):
    if not os.path.exists(db_path):
        print(f"[ERROR] Database file {db_path} tidak ditemukan!")
        return False

    conn = sqlite3.connect(db_path)
    wb = Workbook()
    # Hapus sheet default pertama
    default_sheet = wb.active
    wb.remove(default_sheet)

    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    fill_header = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
    font_cell = Font(name="Segoe UI", size=10)
    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    stats = {}

    for table_name, sheet_name in TABLES_TO_EXPORT:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        stats[sheet_name] = len(df)

        ws = wb.create_sheet(title=sheet_name)
        
        # Headers
        headers = list(df.columns)
        ws.append(headers)
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border_thin

        # Rows
        for _, row in df.iterrows():
            row_vals = []
            for val in row:
                if pd.isna(val):
                    row_vals.append("")
                else:
                    row_vals.append(str(val))
            ws.append(row_vals)

        # Style all data rows
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(headers)):
            for cell in row:
                cell.font = font_cell
                cell.border = border_thin

        # Auto column width
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                val_str = str(cell.value or '')
                max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    conn.close()
    wb.save(output_file)
    print(f"[SUCCESS] Seluruh data SQLite berhasil diekspor ke: {output_file}")
    for sheet_name, count in stats.items():
        print(f" - Tab '{sheet_name}': {count} baris data")
    return True

if __name__ == "__main__":
    export_sqlite_to_excel()
