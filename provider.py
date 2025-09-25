import requests
from config import API_KEY, BASE_URL, BASE_URL_AKRAB

def list_product():
    url = f"{BASE_URL}list_product?api_key={API_KEY}"
    try:
        res = requests.get(url, timeout=15)
        return res.json()
    except Exception as e:
        print("[provider/list_product]", e)
        return None

def create_trx(produk, tujuan, reff_id=None):
    from uuid import uuid4
    reff_id = reff_id or str(uuid4())
    url = f"{BASE_URL}trx?produk={produk}&tujuan={tujuan}&reff_id={reff_id}&api_key={API_KEY}"
    try:
        res = requests.get(url, timeout=15)
        return res.json()
    except Exception as e:
        print("[provider/create_trx]", e)
        return None

def history(refid):
    url = f"{BASE_URL}history?api_key={API_KEY}&refid={refid}"
    try:
        res = requests.get(url, timeout=15)
        return res.json()
    except Exception as e:
        print("[provider/history]", e)
        return None

def cek_stock_akrab():
    url = f"{BASE_URL_AKRAB}cek_stock_akrab"
    try:
        res = requests.get(url, timeout=15)
        return res.text
    except Exception as e:
        print("[provider/cek_stock_akrab]", e)
        return None
