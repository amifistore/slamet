import requests
import json

# Load config dari file config.json
with open("config.json") as f:
    CONFIG = json.load(f)

API_KEY = CONFIG.get("API_KEY", "")
BASE_URL = "https://panel.khfy-store.com/api_v2"
BASE_URL_V3 = "https://panel.khfy-store.com/api_v3"

def list_product():
    try:
        url = f"{BASE_URL}/list_product"
        params = {"api_key": API_KEY}
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        return data.get("data", []) if isinstance(data, dict) else []
    except Exception as e:
        print("Error list_product:", e)
        return []

def create_trx(produk, tujuan, reff_id=None):
    try:
        import uuid
        if not reff_id:
            reff_id = str(uuid.uuid4())
        url = f"{BASE_URL}/trx"
        params = {
            "produk": produk,
            "tujuan": tujuan,
            "reff_id": reff_id,
            "api_key": API_KEY
        }
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        return data
    except Exception as e:
        print("Error create_trx:", e)
        return {"status": "error", "message": str(e)}

def history(refid):
    try:
        url = f"{BASE_URL}/history"
        params = {
            "api_key": API_KEY,
            "refid": refid
        }
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        return data
    except Exception as e:
        print("Error history:", e)
        return {"status": "error", "message": str(e)}

def cek_stock_akrab():
    try:
        url = f"{BASE_URL_V3}/cek_stock_akrab"
        params = {"api_key": API_KEY}
        resp = requests.get(url, params=params, timeout=15)
        return resp.text
    except Exception as e:
        print("Error cek_stock_akrab:", e)
        return ""
