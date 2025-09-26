import json

with open("config.json") as f:
    cfg = json.load(f)

TOKEN = cfg["TOKEN"]
ADMIN_IDS = [int(x) for x in cfg["ADMIN_IDS"]]  # pastikan tipe integer
API_KEY = cfg["API_KEY"]
BASE_URL = cfg["BASE_URL"]
BASE_URL_AKRAB = cfg.get("BASE_URL_AKRAB", "")
SALDO_FILE = 'saldo.json'
RIWAYAT_FILE = 'riwayat_transaksi.json'
HARGA_PRODUK_FILE = 'harga_produk.json'
TOPUP_FILE = 'topup_user.json'
QRIS_STATIS = cfg["QRIS_STATIS"]
WEBHOOK_URL = cfg.get("WEBHOOK_URL", "")
WEBHOOK_PORT = cfg.get("WEBHOOK_PORT", 5000)
