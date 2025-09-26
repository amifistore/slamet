import json
from provider import list_product, cek_stock_akrab

def get_produk_list():
    """
    Ambil list produk dan stok dari provider, merge berdasarkan kode produk.
    Jika gagal ambil dari provider, kembalikan list kosong dengan pesan error.
    """
    produk_raw = list_product()
    stok_raw = cek_stock_akrab()
    produk_list = []

    # Tangani error response
    try:
        stok_data = json.loads(stok_raw) if isinstance(stok_raw, str) else stok_raw
        slot_map = {item["type"].lower(): item["sisa_slot"] for item in stok_data.get("data", [])}
    except Exception:
        slot_map = {}

    if not produk_raw or not isinstance(produk_raw, list):
        # Jika gagal ambil produk, kembalikan produk error
        return [{
            "kode": "-",
            "nama": "Gagal ambil produk dari provider",
            "harga": 0,
            "deskripsi": "Pastikan API_KEY benar dan server provider aktif.",
            "kuota": 0
        }]

    for p in produk_raw:
        kode = p.get("kode", "").lower()
        produk_list.append({
            "kode": kode,
            "nama": p.get("nama", "-"),
            "harga": int(p.get("harga", 0)),
            "deskripsi": p.get("deskripsi", "-"),
            "kuota": slot_map.get(kode, 0)
        })
    return produk_list

def get_produk_by_kode(kode):
    kode = kode.lower()
    for produk in get_produk_list():
        if produk["kode"] == kode:
            return produk
    return None

def edit_produk(*args, **kwargs):
    # Tidak bisa edit produk jika produk mengikuti provider.
    pass
