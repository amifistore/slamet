import requests
from config import get_config

cfg = get_config()

def get_products():
    url = f"{cfg['BASE_URL']}list_product?api_key={cfg['API_KEY']}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get('data', [])

def create_transaction(produk, tujuan, reff_id):
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

def get_history(refid):
    url = f"{cfg['BASE_URL']}history?api_key={cfg['API_KEY']}&refid={refid}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()
