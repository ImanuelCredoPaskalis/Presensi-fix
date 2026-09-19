"""Sinkronisasi Google Sheets via Webhook API.
Module ini menyediakan helper untuk koneksi dan sinkronisasi data ke Google Sheets.
Semua operasi data utama kini dilakukan langsung melalui database.py yang menggunakan Sheets sebagai sumber data utama.
"""
import logging
import requests
from config import load_config, save_config

logger = logging.getLogger("sheets_sync")


def get_webhook_url():
    """Ambil URL webhook dari Streamlit Secrets atau config.json."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "gsheets_webhook_url" in st.secrets:
            value = str(st.secrets["gsheets_webhook_url"]).strip()
            if value:
                return value
    except Exception:
        pass
    return str(load_config().get("gsheets_webhook_url", "") or "").strip()


def is_from_secrets():
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "gsheets_webhook_url" in st.secrets:
            return bool(str(st.secrets["gsheets_webhook_url"]).strip())
    except Exception:
        pass
    return False


def set_webhook_url(url):
    cfg = load_config()
    cfg["gsheets_webhook_url"] = str(url or "").strip()
    return save_config(cfg)


def is_sheets_enabled():
    url = get_webhook_url()
    return bool(url and url.lower().startswith(("http://", "https://")))


def _response_json(resp):
    """Parse JSON dengan pesan error yang jelas jika Apps Script mengirim respons non-JSON."""
    try:
        return resp.json()
    except ValueError as exc:
        preview = (resp.text or "").strip().replace("\n", " ")[:300]
        raise ValueError(f"Respons webhook bukan JSON: {preview or 'kosong'}") from exc


def test_connection():
    url = get_webhook_url()
    if not url:
        return False, "URL Webhook Google Sheets belum diatur."
    try:
        resp = requests.get(url, params={"action": "ping"}, timeout=15)
        if resp.status_code != 200:
            return False, f"Server merespon dengan status code: {resp.status_code}"
        data = _response_json(resp)
        if data.get("status") == "success":
            return True, f"Berhasil terhubung ke: {data.get('title', 'Google Sheets')}"
        return False, str(data.get("message", "Respon dari Google Sheets tidak valid."))
    except requests.RequestException as exc:
        return False, f"Gagal menghubungi Google Sheets: {exc}"
    except Exception as exc:
        logger.exception("test_connection gagal")
        return False, f"Gagal memeriksa koneksi Sheets: {exc}"


def _safe_int(value, default=1):
    """Google Sheets dapat mengembalikan 1/0, TRUE/FALSE, atau string kosong."""
    if value is None or str(value).strip() == "":
        return default
    if isinstance(value, bool):
        return int(value)
    text = str(value).strip().lower()
    if text in ("true", "yes", "ya", "aktif"):
        return 1
    if text in ("false", "no", "tidak", "nonaktif", "inactive"):
        return 0
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return default


def _safe_id(value):
    """Normalisasi ID dari Sheets, termasuk angka seperti 1.0."""
    if value is None or str(value).strip() == "":
        return None
    try:
        number = float(value)
        if number.is_integer():
            return int(number)
    except (TypeError, ValueError):
        pass
    return value


def _safe_text(value, default=""):
    if value is None:
        return default
    return str(value).strip()


def sync_row_async(table_name, row_dict, key="id"):
    """Sinkronkan satu baris ke Google Sheets secara async."""
    if not is_sheets_enabled():
        return False
    try:
        requests.post(get_webhook_url(), json={"action": "upsert_row", "table": table_name, "key": key, "row": row_dict}, timeout=5)
        return True
    except Exception as exc:
        logger.warning("Gagal menyinkronkan baris ke Sheets: %s", exc)
        return False


def sync_delete_async(table_name, key="id", value=None):
    """Hapus baris dari Google Sheets secara async."""
    if not is_sheets_enabled():
        return False
    try:
        requests.post(get_webhook_url(), json={"action": "delete_row", "table": table_name, "key": key, "value": value}, timeout=5)
        return True
    except Exception as exc:
        logger.warning("Gagal menghapus baris di Sheets: %s", exc)
        return False
