import requests
import json
import os
import base64
import io

# Path ke config.json (asumsi satu folder dengan file ini)
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def get_qris_statis():
    """
    Ambil nilai QRIS statis dari config.json.
    Key harus 'QRIS_STATIS' sesuai dengan config user.
    """
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("QRIS_STATIS", "")
    except Exception as e:
        print(f"[QRIS] Gagal baca QRIS_STATIS dari config: {e}")
        return ""

QRIS_STATIS_DEFAULT = get_qris_statis()

def generate_qris(nominal, qris_statis=None):
    """
    Memanggil API QRIS Dinamis Generator untuk membuat QR berbasis nominal & QRIS statis merchant.
    Args:
        nominal (int|str): Nominal dalam rupiah, minimal 10000.
        qris_statis (str|None): QRIS statis merchant, jika None ambil dari config.
    Returns:
        dict: Hasil request, minimal ada key: status, message, qris_base64 (jika sukses)
    """
    url = "https://qrisku.my.id/api"
    if not qris_statis:
        qris_statis = QRIS_STATIS_DEFAULT
    if not qris_statis:
        return {"status": "error", "message": "QRIS statis tidak tersedia di config.json"}
    payload = {
        "amount": str(nominal),
        "qris_statis": qris_statis.strip()
    }
    headers = {
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            return {"status": "error", "message": "Invalid response format from QRIS API"}
        if data.get("status") == "success" and "qris_base64" in data:
            return {
                "status": "success",
                "message": data.get("message", ""),
                "qris_base64": data["qris_base64"]
            }
        return {
            "status": "error",
            "message": data.get("message", "Unknown error from QRIS API")
        }
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Timeout saat menghubungi server QRIS"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Gagal request QRIS API: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Error: {str(e)}"}

def qris_base64_to_bytesio(qris_base64: str):
    """
    Utility untuk decode base64 QRIS menjadi objek BytesIO siap kirim ke Telegram.
    """
    try:
        qris_bytes = base64.b64decode(qris_base64)
        bio = io.BytesIO(qris_bytes)
        bio.name = "qris.png"
        bio.seek(0)
        return bio
    except Exception as e:
        print(f"[QRIS] Error decode base64: {e}")
        return None
