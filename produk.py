import json
import os
import logging
from provider import cek_stock_akrab

# Setup logger
logger = logging.getLogger(__name__)

LIST_PRODUK_TETAP = [
    {"kode": "bpal1",    "nama": "Bonus Akrab L - 1 hari",   "harga": 5000,  "deskripsi": "Paket harian murah", "kuota": 0},
    {"kode": "bpal11",   "nama": "Bonus Akrab L - 11 hari",  "harga": 50000, "deskripsi": "Paket 11 hari hemat", "kuota": 0},
    {"kode": "bpal13",   "nama": "Bonus Akrab L - 13 hari",  "harga": 60000, "deskripsi": "Paket 13 hari", "kuota": 0},
    {"kode": "bpal15",   "nama": "Bonus Akrab L - 15 hari",  "harga": 70000, "deskripsi": "Paket 15 hari", "kuota": 0},
    {"kode": "bpal17",   "nama": "Bonus Akrab L - 17 hari",  "harga": 80000, "deskripsi": "Paket 17 hari", "kuota": 0},
    {"kode": "bpal19",   "nama": "Bonus Akrab L - 19 hari",  "harga": 90000, "deskripsi": "Paket 19 hari", "kuota": 0},
    {"kode": "bpal3",    "nama": "Bonus Akrab L - 3 hari",   "harga": 13000, "deskripsi": "Paket 3 hari", "kuota": 0},
    {"kode": "bpal5",    "nama": "Bonus Akrab L - 5 hari",   "harga": 20000, "deskripsi": "Paket 5 hari", "kuota": 0},
    {"kode": "bpal7",    "nama": "Bonus Akrab L - 7 hari",   "harga": 30000, "deskripsi": "Paket 7 hari", "kuota": 0},
    {"kode": "bpal9",    "nama": "Bonus Akrab L - 9 hari",   "harga": 40000, "deskripsi": "Paket 9 hari", "kuota": 0},
    {"kode": "bpaxxl1",  "nama": "Bonus Akrab XXL - 1 hari", "harga": 8000,  "deskripsi": "XXL 1 hari", "kuota": 0},
    {"kode": "bpaxxl11", "nama": "Bonus Akrab XXL - 11 hari","harga": 80000, "deskripsi": "XXL 11 hari", "kuota": 0},
    {"kode": "bpaxxl13", "nama": "Bonus Akrab XXL - 13 hari","harga": 90000, "deskripsi": "XXL 13 hari", "kuota": 0},
    {"kode": "bpaxxl15", "nama": "Bonus Akrab XXL - 15 hari","harga": 100000,"deskripsi": "XXL 15 hari", "kuota": 0},
    {"kode": "bpaxxl19", "nama": "Bonus Akrab XXL - 19 hari","harga": 120000,"deskripsi": "XXL 19 hari", "kuota": 0},
    {"kode": "bpaxxl3",  "nama": "Bonus Akrab XXL - 3 hari", "harga": 20000, "deskripsi": "XXL 3 hari", "kuota": 0},
    {"kode": "bpaxxl5",  "nama": "Bonus Akrab XXL - 5 hari", "harga": 30000, "deskripsi": "XXL 5 hari", "kuota": 0},
    {"kode": "bpaxxl7",  "nama": "Bonus Akrab XXL - 7 hari", "harga": 40000, "deskripsi": "XXL 7 hari", "kuota": 0},
    {"kode": "bpaxxl9",  "nama": "Bonus Akrab XXL - 9 hari", "harga": 50000, "deskripsi": "XXL 9 hari", "kuota": 0},
    {"kode": "XLA14",    "nama": "SuperMini",                "harga": 15000, "deskripsi": "SuperMini murah", "kuota": 0},
    {"kode": "XLA32",    "nama": "Mini",                     "harga": 30000, "deskripsi": "Mini paket", "kuota": 0},
    {"kode": "XLA39",    "nama": "Big",                      "harga": 39000, "deskripsi": "Big paket", "kuota": 0},
    {"kode": "XLA51",    "nama": "Jumbo V2",                 "harga": 51000, "deskripsi": "Jumbo paket", "kuota": 0},
    {"kode": "XLA65",    "nama": "JUMBO",                    "harga": 65000, "deskripsi": "Jumbo paket spesial", "kuota": 0},
    {"kode": "XLA89",    "nama": "MegaBig",                  "harga": 89000, "deskripsi": "MegaBig super paket", "kuota": 0}
]

CUSTOM_FILE = "produk_custom.json"

def load_custom_produk():
    try:
        if os.path.exists(CUSTOM_FILE):
            with open(CUSTOM_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading custom produk: {e}")
        return {}

def save_custom_produk(data):
    try:
        with open(CUSTOM_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving custom produk: {e}")
        return False

def get_all_custom_produk():
    try:
        data = load_custom_produk()
        result = {}
        for k, v in data.items():
            if isinstance(v, dict):
                v_copy = v.copy()
                v_copy.pop("nama", None)
                result[k.lower()] = v_copy
        return result
    except Exception as e:
        logger.error(f"Error getting custom produk: {e}")
        return {}

def parse_stock_from_provider():
    try:
        stok_raw = cek_stock_akrab()
        if isinstance(stok_raw, dict):
            stok_data = stok_raw
        elif isinstance(stok_raw, str):
            if stok_raw.strip().lower().startswith("<html"):
                logger.warning("Provider returned HTML instead of JSON")
                return {}
            stok_data = json.loads(stok_raw)
        else:
            logger.warning(f"Unexpected stock format: {type(stok_raw)}")
            return {}
        if "data" in stok_data and isinstance(stok_data["data"], list):
            slot_map = {}
            for item in stok_data["data"]:
                if isinstance(item, dict) and "type" in item:
                    product_type = item["type"].lower()
                    sisa_slot = item.get("sisa_slot", 0)
                    try:
                        sisa_slot = int(sisa_slot) if sisa_slot not in [None, ""] else 0
                    except (ValueError, TypeError):
                        sisa_slot = 0
                    slot_map[product_type] = sisa_slot
            return slot_map
        return {}
    except Exception as e:
        logger.error(f"Error parsing stock from provider: {e}")
        return {}

def get_list_stok_fixed():
    try:
        slot_map = parse_stock_from_provider()
        custom_data = get_all_custom_produk()
        output = []
        for produk in LIST_PRODUK_TETAP:
            kode = produk["kode"].lower()
            produk_copy = produk.copy()
            if kode in custom_data:
                custom = custom_data[kode]
                if custom.get("harga") is not None:
                    try:
                        produk_copy["harga"] = int(custom["harga"])
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid harga for {kode}: {custom.get('harga')}")
                if custom.get("deskripsi"):
                    produk_copy["deskripsi"] = custom["deskripsi"]
            produk_copy["sisa_slot"] = slot_map.get(kode, 0)
            produk_copy["kuota"] = produk_copy["sisa_slot"]
            output.append(produk_copy)
        return output
    except Exception as e:
        logger.error(f"Error getting product list with stock: {e}")
        return LIST_PRODUK_TETAP.copy()

def get_produk_list():
    return get_list_stok_fixed()

def get_produk_by_kode(kode):
    if not kode:
        return None
    try:
        kode = kode.lower()
        all_products = get_list_stok_fixed()
        for produk in all_products:
            if produk["kode"].lower() == kode:
                return produk
        return None
    except Exception as e:
        logger.error(f"Error getting product by kode {kode}: {e}")
        return None

def edit_produk(kode, harga=None, deskripsi=None):
    if not kode:
        return False
    try:
        kode = kode.lower()
        custom_data = load_custom_produk()
        if kode not in custom_data:
            custom_data[kode] = {}
        if harga is not None:
            try:
                custom_data[kode]["harga"] = int(harga)
            except (ValueError, TypeError):
                return False
        if deskripsi is not None:
            custom_data[kode]["deskripsi"] = deskripsi.strip()
        return save_custom_produk(custom_data)
    except Exception as e:
        logger.error(f"Error editing product {kode}: {e}")
        return False

def format_list_stok_fixed():
    try:
        items = get_list_stok_fixed()
        msg = "<b>Daftar Produk Tersedia:</b>\n\n"
        for item in items:
            status = "✅ Tersedia" if item['sisa_slot'] > 0 else "❌ Habis"
            msg += f"<code>{item['kode']}</code> | {item['nama']}\n"
            msg += f"💰 Rp {item['harga']:,} | 📦 {item['sisa_slot']} slot | {status}\n"
            msg += f"📝 {item['deskripsi']}\n\n"
        return msg
    except Exception as e:
        logger.error(f"Error formatting product list: {e}")
        return "❌ Gagal memuat daftar produk."

def get_produk_list_for_admin():
    try:
        products = get_list_stok_fixed()
        custom_data = get_all_custom_produk()
        result = []
        for p in products:
            kode = p["kode"].lower()
            product_info = p.copy()
            product_info["is_customized"] = kode in custom_data
            result.append(product_info)
        return result
    except Exception as e:
        logger.error(f"Error getting product list for admin: {e}")
        return []

def reset_produk_custom(kode):
    try:
        kode = kode.lower()
        custom_data = load_custom_produk()
        if kode in custom_data:
            del custom_data[kode]
            return save_custom_produk(custom_data)
        return True
    except Exception as e:
        logger.error(f"Error resetting product {kode}: {e}")
        return False
