from utils import load_harga_produk, save_harga_produk

# Static produk default (bisa diubah/ditambah via admin)
STATIC_BUY_PRODUCTS = [
    {"kode": "bpal1", "nama": "Bonus Akrab L - 1 hari", "kuota": 999, "harga": 9000, "deskripsi": "Default"},
    {"kode": "bpal11", "nama": "Bonus Akrab L - 11 hari", "kuota": 999, "harga": 11000, "deskripsi": "Default"},
    {"kode": "bpal13", "nama": "Bonus Akrab L - 13 hari", "kuota": 999, "harga": 13000, "deskripsi": "Default"},
    {"kode": "XLA14", "nama": "SuperMini", "kuota": 999, "harga": 14000, "deskripsi": "Default"},
    # Tambahkan produk lain sesuai kebutuhan
]

def get_produk_list():
    produk_db = load_harga_produk()
    result = []
    for p in STATIC_BUY_PRODUCTS:
        kode = p["kode"]
        custom = produk_db.get(kode)
        if custom:
            result.append({
                "kode": kode,
                "nama": custom.get("nama", p["nama"]),
                "kuota": custom.get("kuota", p["kuota"]),
                "harga": custom.get("harga", p["harga"]),
                "deskripsi": custom.get("deskripsi", p["deskripsi"])
            })
        else:
            result.append(p)
    return result

def edit_produk(kode, field, value):
    produk_db = load_harga_produk()
    if kode not in produk_db:
        produk_db[kode] = {}
    produk_db[kode][field] = value
    save_harga_produk(produk_db)

def get_produk_by_kode(kode):
    produk_list = get_produk_list()
    for p in produk_list:
        if p["kode"] == kode:
            return p
    return None
