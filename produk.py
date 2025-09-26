import json
from provider import list_product, cek_stock_akrab

def get_produk_list():
    """
    Ambil list produk dan stok dari provider, merge berdasarkan kode produk.
    """
    # Ambil data produk (nama, harga, deskripsi) dan data stok (sisa_slot)
    produk_raw = list_product()
    stok_raw = cek_stock_akrab()
    try:
        stok_data = json.loads(stok_raw) if isinstance(stok_raw, str) else stok_raw
        slot_map = {item["type"].lower(): item["sisa_slot"] for item in stok_data.get("data", [])}
    except Exception:
        slot_map = {}

    produk_list = []
    if isinstance(produk_raw, list):
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
    # Fungsi ini tetap ada agar tidak error jika dipanggil handler admin, tapi tidak melakukan apapun.
    pass
