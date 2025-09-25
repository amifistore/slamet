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
