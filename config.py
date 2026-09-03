"""
Konfigurasi Sistem Presensi Mahasiswa & Kelas
"""
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "presensi.db")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "app_title": "Sistem Presensi Mahasiswa & Kelas",
    "company_name": "Lab Micro Teaching FisMat",
    "company_address": "Program Studi Pendidikan Matematika",
    "work_start_time": "08:00",
    "work_end_time": "17:00",
    "theme_mode": "dark",  # "dark" or "light"
    "color_theme": "blue"   # "blue", "green", "dark-blue"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False
