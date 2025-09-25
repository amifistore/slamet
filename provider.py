import requests
from config import get_config

cfg = get_config()

def get_products():
    """
    Ambil daftar produk dari KHFY Store.
    Return: list produk (dict) atau [] jika gagal.
    """
    try:
        url = f"{cfg['BASE_URL']}list_product?api_key={cfg['API_KEY']}"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get('data', [])
    except Exception as e:
        print(f"[PROVIDER][get_products] Error: {e}")
        return []

def get_product_detail(kode_produk):
    """
    Ambil detail produk tertentu (jika API support).
    Return: dict produk atau None.
    """
    try:
        url = f"{cfg['BASE_URL']}cek_harga?api_key={cfg['API_KEY']}&kode={kode_produk}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get('data')
    except Exception as e:
        print(f"[PROVIDER][get_product_detail] Error: {e}")
        return None

def create_transaction(produk, tujuan, reff_id):
    """
    Kirim permintaan transaksi ke provider.
    Return: dict response API atau {} jika error.
    """
    try:
        url = f"{cfg['BASE_URL']}trx"
        params = {
            "produk": produk,
            "tujuan": tujuan,
            "reff_id": reff_id,
            "api_key": cfg["API_KEY"]
        }
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[PROVIDER][create_transaction] Error: {e}")
        return {}

def get_history(refid):
    """
    Cek status transaksi ke provider.
    Return: dict response API atau {} jika error.
    """
    try:
        url = f"{cfg['BASE_URL']}history?api_key={cfg['API_KEY']}&refid={refid}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[PROVIDER][get_history] Error: {e}")
        return {}

def get_saldo():
    """
    Cek saldo provider.
    Return: float saldo, atau None jika error.
    """
    try:
        url = f"{cfg['BASE_URL']}cek_saldo?api_key={cfg['API_KEY']}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        # Sesuai dokumentasi, field saldo bisa bernama 'saldo' atau dalam 'data'
        if 'saldo' in data:
            return float(data['saldo'])
        if 'data' in data and 'saldo' in data['data']:
            return float(data['data']['saldo'])
        return None
    except Exception as e:
        print(f"[PROVIDER][get_saldo] Error: {e}")
        return None

def cek_harga_produk(kode_produk):
    """
    Cek harga produk tertentu.
    Return: dict (harga, kode, nama), atau None jika error.
    """
    try:
        url = f"{cfg['BASE_URL']}cek_harga?api_key={cfg['API_KEY']}&kode={kode_produk}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get('data')
    except Exception as e:
        print(f"[PROVIDER][cek_harga_produk] Error: {e}")
        return None
