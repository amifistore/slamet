import json

with open("config.json") as f:
    cfg = json.load(f)

TOKEN = cfg["TOKEN"]
ADMIN_IDS = cfg["ADMIN_IDS"]          # List of admin user_ids (int)
API_KEY = cfg["API_KEY"]
BASE_URL = "https://panel.khfy-store.com/api_v2/"
BASE_URL_AKRAB = "https://panel.khfy-store.com/api_v3/"
SALDO_FILE = 'saldo.json'
RIWAYAT_FILE = 'riwayat_transaksi.json'
HARGA_PRODUK_FILE = 'harga_produk.json'
TOPUP_FILE = 'topup_user.json'
QRIS_STATIS = cfg["QRIS_STATIS"]      # QRIS statis string dari merchant
