import requests
from config import QRIS_STATIS

def generate_qris(amount, qris_statis=QRIS_STATIS):
    url = "https://qrisku.my.id/api"
    payload = {"amount": str(amount), "qris_statis": qris_statis}
    try:
        resp = requests.post(url, json=payload, timeout=20)
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": f"Request error: {e}"}
