import requests
import os
from dotenv import load_dotenv

load_dotenv()
PROVIDER_BASE_URL = os.getenv("PROVIDER_BASE_URL")
PROVIDER_API_KEY = os.getenv("PROVIDER_API_KEY")

def get_products():
    try:
        url = f"{PROVIDER_BASE_URL}list_product?api_key={PROVIDER_API_KEY}"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get('data', [])
    except Exception as e:
        print(f"[PROVIDER][get_products] Error: {e}")
        return []

def create_transaction(produk, tujuan, reff_id):
    try:
        url = f"{PROVIDER_BASE_URL}trx"
        params = {
            "produk": produk,
            "tujuan": tujuan,
            "reff_id": reff_id,
            "api_key": PROVIDER_API_KEY
        }
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[PROVIDER][create_transaction] Error: {e}")
        return {}

def get_history(refid):
    try:
        url = f"{PROVIDER_BASE_URL}history?api_key={PROVIDER_API_KEY}&refid={refid}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[PROVIDER][get_history] Error: {e}")
        return {}
