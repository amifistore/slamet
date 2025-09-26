import requests
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def get_qris_statis():
    """Ambil nilai QRIS statis dari config.json."""
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
    Mengirim permintaan ke API QRIS Dinamis Generator untuk membuat kode QRIS base64.
    Args:
        nominal (int|str): Nominal top up (minimal 10000, dalam satuan rupiah)
        qris_statis (str): Kode QRIS statis merchant (jika None, pakai dari config)
    Returns:
        dict: response JSON, misal:
            {
                "status": "success",
                "message": "QRIS berhasil dihasilkan",
                "qris_base64": "BASE64_ENCODED_QR_CODE_HERE"
            }
            atau:
            {
                "status": "error",
                "message": "..."
            }
    """
    url = "https://qrisku.my.id/api"
    if not qris_statis:
        qris_statis = QRIS_STATIS_DEFAULT
    if not qris_statis:
        return {"status": "error", "message": "QRIS statis tidak tersedia di config.json"}
    payload = {
        "amount": str(nominal),
        "qris_statis": qris_statis
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
