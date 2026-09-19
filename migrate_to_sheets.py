"""
Migrate to Sheets Utility
Membaca seluruh data dari Google Sheets dan mengekspornya ke format multi-sheet Excel (.xlsx)
untuk diunggah langsung ke Google Drive / Google Sheets.
"""
import os
import requests
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from config import load_config

OUTPUT_EXCEL = "migrasi_data_presensi_google_sheets.xlsx"

TABLES_TO_EXPORT = [
    ("mahasiswa", "mahasiswa"),
    ("presensi", "presensi"),
    ("riwayat_kelas", "riwayat_kelas"),
    ("riwayat_izin", "riwayat_izin"),
    ("riwayat_tugas_luar", "riwayat_tugas_luar")
]

def get_webhook_url():
    """Ambil URL webhook dari config.json."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "gsheets_webhook_url" in st.secrets:
            value = str(st.secrets["gsheets_webhook_url"]).strip()
            if value:
                return value
    except Exception:
        pass
    return str(load_config().get("gsheets_webhook_url", "") or "").strip()


def get_sheet_data(sheet_name):
    """Ambil data dari Google Sheets."""
    url = get_webhook_url()
    if not url:
        return []
    try:
        resp = requests.get(url, params={"action": "get_table", "table": sheet_name}, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if data.get("status") != "success":
            return []
        return data.get("data") or []
    except Exception:
        return []


def export_sheets_to_excel(output_file=OUTPUT_EXCEL):
    """Ekspor semua data dari Google Sheets ke file Excel."""
    url = get_webhook_url()
    if not url:
        print("[ERROR] Google Sheets Webhook URL belum diatur!")
        return False

    wb = Workbook()
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

    for sheet_name, _ in TABLES_TO_EXPORT:
        rows = get_sheet_data(sheet_name)
        if not rows:
            print(f"[WARNING] Tidak ada data di sheet '{sheet_name}'")
            continue

        stats[sheet_name] = len(rows)
        df = pd.DataFrame(rows)

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

    wb.save(output_file)
    print(f"[SUCCESS] Seluruh data Google Sheets berhasil diekspor ke: {output_file}")
    for sheet_name, count in stats.items():
        print(f" - Tab '{sheet_name}': {count} baris data")
    return True

if __name__ == "__main__":
    export_sheets_to_excel()
