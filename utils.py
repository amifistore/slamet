import os
import json
from config import SALDO_FILE, RIWAYAT_FILE, HARGA_PRODUK_FILE, TOPUP_FILE

def load_json(filename, fallback=None):
    if os.path.exists(filename):
        try:
            with open(filename) as f:
                return json.load(f)
        except Exception:
            pass
    return fallback if fallback is not None else {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_saldo():
    return load_json(SALDO_FILE, 500000)

def set_saldo(amount):
    save_json(SALDO_FILE, amount)

def load_riwayat():
    return load_json(RIWAYAT_FILE, {})

def save_riwayat(riwayat):
    save_json(RIWAYAT_FILE, riwayat)

def load_harga_produk():
    return load_json(HARGA_PRODUK_FILE, {})

def save_harga_produk(harga_produk):
    save_json(HARGA_PRODUK_FILE, harga_produk)

def load_topup():
    return load_json(TOPUP_FILE, {})

def save_topup(topup):
    save_json(TOPUP_FILE, topup)

def format_stock_akrab(json_data):
    import json as _json
    if isinstance(json_data, str):
        json_data = _json.loads(json_data)
    items = json_data.get("data", [])
    msg = "<b>📊 Cek Stok Produk Akrab:</b>\n\n"
    msg += "<b>Kode      | Nama                | Sisa Slot</b>\n"
    msg += "<pre>"
    for item in items:
        kode = item['type'].ljust(8)
        nama = item['nama'].ljust(20)
        slot = str(item['sisa_slot']).rjust(4)
        msg += f"{kode} | {nama} | {slot}\n"
    msg += "</pre>"
    return msg
