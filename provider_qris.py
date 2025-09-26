import requests
import json
import os
import base64
import io
import tempfile
import re
from typing import Dict, Optional, Union, Any

class QRISGenerator:
    """
    QRIS Generator untuk handle pembuatan QRIS dinamis dari QRISKU API.
    """

    def __init__(
        self,
        qris_statis: str = None,
        api_url: str = "https://qrisku.my.id/api",
        timeout: int = 30
    ):
        self.api_url = api_url
        self.timeout = timeout
        self.qris_statis_default = qris_statis or (
            "00020101021126610014COM.GO-JEK.WWW01189360091434506469550210G4506469550303UMI51440014ID.CO.QRIS.WWW0215"
            "ID10243341364120303UMI5204569753033605802ID5923Amifi Store, Kmb, TLGSR6009BONDOWOSO61056827262070703A01630431E8"
        )

    def _clean_base64(self, base64_string: str) -> str:
        """Bersihkan base64 string (whitespace, padding, karakter non-base64)"""
        if not base64_string:
            return ""
        cleaned = re.sub(r'[^A-Za-z0-9+/]', '', base64_string)
        padding_needed = len(cleaned) % 4
        if padding_needed:
            cleaned += '=' * (4 - padding_needed)
        return cleaned

    def generate_qris(self, nominal: Union[int, str], qris_statis: Optional[str] = None) -> Dict[str, Any]:
        """Generate QRIS dinamis dan return dict hasil API."""
        qris_statis = qris_statis or self.qris_statis_default
        if not qris_statis:
            return {"status": "error", "message": "QRIS statis tidak tersedia"}
        try:
            nominal_int = int(nominal)
            if nominal_int < 1000:
                return {"status": "error", "message": "Nominal minimal Rp 1.000"}
        except Exception:
            return {"status": "error", "message": "Nominal harus berupa angka"}
        payload = {"amount": str(nominal_int), "qris_statis": qris_statis.strip()}
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and data.get("status") == "success" and "qris_base64" in data:
                cleaned_base64 = self._clean_base64(data["qris_base64"])
                if not cleaned_base64:
                    return {"status": "error", "message": "Invalid base64 data"}
                return {
                    "status": "success",
                    "message": data.get("message", "QRIS berhasil digenerate"),
                    "qris_base64": cleaned_base64,
                    "nominal": nominal_int
                }
            error_message = data.get("message", "Unknown error from QRIS API")
            return {"status": "error", "message": f"API Error: {error_message}"}
        except requests.exceptions.Timeout:
            return {"status": "error", "message": "Timeout saat menghubungi server QRIS"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Gagal request QRIS API: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"Error: {str(e)}"}

    def get_qris_bytesio(self, nominal: Union[int, str], qris_statis: Optional[str] = None) -> Optional[io.BytesIO]:
        """Generate QRIS dan return BytesIO PNG. Return None jika gagal."""
        hasil = self.generate_qris(nominal, qris_statis)
        if hasil["status"] != "success":
            print(f"[QRIS] Gagal generate: {hasil['message']}")
            return None
        qris_base64 = hasil["qris_base64"]
        cleaned_base64 = self._clean_base64(qris_base64)
        try:
            qris_bytes = base64.b64decode(cleaned_base64)
            bio = io.BytesIO(qris_bytes)
            bio.name = "qris.png"
            bio.seek(0)
            return bio
        except Exception as e:
            print(f"[QRIS] Error decode base64: {e}")
            return None

class TelegramQRISSender:
    """
    Class untuk mengirim gambar QRIS ke Telegram (dari base64 PNG).
    """

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.qris_generator = QRISGenerator()

    def verify_bot_token(self) -> bool:
        """Cek apakah token bot valid."""
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=10)
            return response.json().get("ok", False)
        except:
            return False

    def send_photo(self, chat_id: str, image_bytesio: io.BytesIO, caption: str = "") -> dict:
        """Kirim image BytesIO sebagai foto ke Telegram."""
        files = {'photo': ('qris.png', image_bytesio, 'image/png')}
        data = {
            'chat_id': chat_id,
            'caption': caption,
            'parse_mode': 'HTML'
        }
        url = f"{self.base_url}/sendPhoto"
        try:
            resp = requests.post(url, data=data, files=files, timeout=20)
            return resp.json()
        except Exception as e:
            return {"ok": False, "description": f"Telegram request error: {str(e)}"}

    def send_document(self, chat_id: str, image_bytesio: io.BytesIO, caption: str = "") -> dict:
        """Kirim image BytesIO sebagai dokumen ke Telegram (fallback)."""
        files = {'document': ('qris.png', image_bytesio, 'image/png')}
        data = {
            'chat_id': chat_id,
            'caption': caption,
            'parse_mode': 'HTML'
        }
        url = f"{self.base_url}/sendDocument"
        try:
            resp = requests.post(url, data=data, files=files, timeout=20)
            return resp.json()
        except Exception as e:
            return {"ok": False, "description": f"Telegram request error: {str(e)}"}

    def send_qris_to_telegram(self, chat_id: str, nominal: Union[int, str], caption: str = "", qris_statis: Optional[str] = None) -> dict:
        """Generate QRIS dan langsung kirim ke Telegram. Ada fallback document."""
        if not self.verify_bot_token():
            return {"status": "error", "message": "Bot token tidak valid"}
        bio = self.qris_generator.get_qris_bytesio(nominal, qris_statis)
        if bio is None:
            return {"status": "error", "message": "Gagal generate QRIS"}
        final_caption = caption or f"💳 QRIS Payment\n💵 Nominal: Rp {int(nominal):,}\n⏰ Berlaku 24 jam"
        # Strategy 1: kirim sebagai foto
        resp = self.send_photo(chat_id, bio, final_caption)
        if resp.get("ok"):
            return {"status": "success", "message": "QRIS berhasil dikirim ke Telegram (foto)", "response": resp}
        # Fallback: kirim sebagai dokumen
        bio.seek(0)
        resp2 = self.send_document(chat_id, bio, final_caption)
        if resp2.get("ok"):
            return {"status": "success", "message": "QRIS berhasil dikirim ke Telegram (dokumen)", "response": resp2}
        return {"status": "error", "message": f"Telegram API error: {resp2.get('description', 'Unknown error')}", "response": resp2}

# =========================
# CONTOH PENGGUNAAN
# =========================

if __name__ == "__main__":
    BOT_TOKEN = "ISI_TOKEN_BOT_ANDA"
    CHAT_ID = "ISI_CHAT_ID_ANDA"

    if BOT_TOKEN.startswith("ISI_") or CHAT_ID.startswith("ISI_"):
        print("❌ Silakan isi BOT_TOKEN dan CHAT_ID yang benar!")
        exit(1)

    sender = TelegramQRISSender(BOT_TOKEN)
    res = sender.send_qris_to_telegram(
        chat_id=CHAT_ID,
        nominal=15000,
        caption="🔰 QRIS Dinamis langsung dari Python"
    )
    print(res)
