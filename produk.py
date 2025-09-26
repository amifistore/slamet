import json
from provider import cek_stock_akrab

# Daftar produk tetap (urutan, nama, harga, dan deskripsi bisa kamu rubah sesuai keinginan)
LIST_PRODUK_TETAP = [
    {"kode": "bpal1",    "nama": "Bonus Akrab L - 1 hari",   "harga": 5000,  "deskripsi": "Paket harian murah"},
    {"kode": "bpal11",   "nama": "Bonus Akrab L - 11 hari",  "harga": 50000, "deskripsi": "Paket 11 hari hemat"},
    {"kode": "bpal13",   "nama": "Bonus Akrab L - 13 hari",  "harga": 60000, "deskripsi": "Paket 13 hari"},
    {"kode": "bpal15",   "nama": "Bonus Akrab L - 15 hari",  "harga": 70000, "deskripsi": "Paket 15 hari"},
    {"kode": "bpal17",   "nama": "Bonus Akrab L - 17 hari",  "harga": 80000, "deskripsi": "Paket 17 hari"},
    {"kode": "bpal19",   "nama": "Bonus Akrab L - 19 hari",  "harga": 90000, "deskripsi": "Paket 19 hari"},
    {"kode": "bpal3",    "nama": "Bonus Akrab L - 3 hari",   "harga": 13000, "deskripsi": "Paket 3 hari"},
    {"kode": "bpal5",    "nama": "Bonus Akrab L - 5 hari",   "harga": 20000, "deskripsi": "Paket 5 hari"},
    {"kode": "bpal7",    "nama": "Bonus Akrab L - 7 hari",   "harga": 30000, "deskripsi": "Paket 7 hari"},
    {"kode": "bpal9",    "nama": "Bonus Akrab L - 9 hari",   "harga": 40000, "deskripsi": "Paket 9 hari"},
    {"kode": "bpaxxl1",  "nama": "Bonus Akrab XXL - 1 hari", "harga": 8000,  "deskripsi": "XXL 1 hari"},
    {"kode": "bpaxxl11", "nama": "Bonus Akrab XXL - 11 hari","harga": 80000, "deskripsi": "XXL 11 hari"},
    {"kode": "bpaxxl13", "nama": "Bonus Akrab XXL - 13 hari","harga": 90000, "deskripsi": "XXL 13 hari"},
    {"kode": "bpaxxl15", "nama": "Bonus Akrab XXL - 15 hari","harga": 100000,"deskripsi": "XXL 15 hari"},
    {"kode": "bpaxxl19", "nama": "Bonus Akrab XXL - 19 hari","harga": 120000,"deskripsi": "XXL 19 hari"},
    {"kode": "bpaxxl3",  "nama": "Bonus Akrab XXL - 3 hari", "harga": 20000, "deskripsi": "XXL 3 hari"},
    {"kode": "bpaxxl5",  "nama": "Bonus Akrab XXL - 5 hari", "harga": 30000, "deskripsi": "XXL 5 hari"},
    {"kode": "bpaxxl7",  "nama": "Bonus Akrab XXL - 7 hari", "harga": 40000, "deskripsi": "XXL 7 hari"},
    {"kode": "bpaxxl9",  "nama": "Bonus Akrab XXL - 9 hari", "harga": 50000, "deskripsi": "XXL 9 hari"},
    {"kode": "XLA14",    "nama": "SuperMini",                "harga": 15000, "deskripsi": "SuperMini murah"},
    {"kode": "XLA32",    "nama": "Mini",                     "harga": 30000, "deskripsi": "Mini paket"},
    {"kode": "XLA39",    "nama": "Big",                      "harga": 39000, "deskripsi": "Big paket"},
    {"kode": "XLA51",    "nama": "Jumbo V2",                 "harga": 51000, "deskripsi": "Jumbo paket"},
    {"kode": "XLA65",    "nama": "JUMBO",                    "harga": 65000, "deskripsi": "Jumbo paket spesial"},
    {"kode": "XLA89",    "nama": "MegaBig",                  "harga": 89000, "deskripsi": "MegaBig super paket"},
]

def get_list_stok_fixed():
    """Ambil stok dari provider dan gabungkan ke list produk tetap."""
    stok_raw = cek_stock_akrab()
    try:
        stok_data = json.loads(stok_raw) if isinstance(stok_raw, str) else stok_raw
        slot_map = {item["type"].lower(): item.get("sisa_slot", 0) for item in stok_data.get("data", [])}
    except Exception:
        slot_map = {}

    output = []
    for p in LIST_PRODUK_TETAP:
        kode = p["kode"].lower()
        produk = p.copy()
        produk["sisa_slot"] = slot_map.get(kode, 0)
        output.append(produk)
    return output

def format_list_stok_fixed():
    """Format hasil get_list_stok_fixed untuk Telegram."""
    items = get_list_stok_fixed()
    msg = "<b>Kode      | Nama                | Harga   | Sisa Slot</b>\n<pre>"
    for item in items:
        kode = item['kode'].ljust(8)
        nama = item['nama'].ljust(20)
        harga = str(item['harga']).rjust(7)
        slot = str(item['sisa_slot']).rjust(4)
        msg += f"{kode} | {nama} | {harga} | {slot}\n"
    msg += "</pre>"
    return msg

def get_produk_by_kode(kode):
    """Cari produk di list tetap berdasarkan kode, hasilkan detail + stok."""
    kode = kode.lower()
    stok_map = {p['kode']: p['sisa_slot'] for p in get_list_stok_fixed()}
    for produk in LIST_PRODUK_TETAP:
        if produk["kode"].lower() == kode:
            data = produk.copy()
            data["sisa_slot"] = stok_map.get(kode, 0)
            return data
    return None

def edit_produk(*args, **kwargs):
    # Tidak bisa edit produk jika produk mengikuti provider/daftar tetap.
    pass
