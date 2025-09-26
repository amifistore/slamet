import requests
import json
import os
import base64
import io
import tempfile
import re
from typing import Dict, Optional, Union, Any

class QRISGenerator:
    """QRIS Generator class untuk handle pembuatan QRIS dinamis"""

    def __init__(self, qris_statis: str = None, api_url: str = "https://qrisku.my.id/api", timeout: int = 30):
        self.api_url = api_url
        self.timeout = timeout
        # Gunakan QRIS statis yang diberikan atau default
        self.qris_statis_default = qris_statis or (
            "00020101021126610014COM.GO-JEK.WWW01189360091434506469550210G4506469550303UMI51440014ID.CO.QRIS.WWW0215"
            "ID10243341364120303UMI5204569753033605802ID5923Amifi Store, Kmb, TLGSR6009BONDOWOSO61056827262070703A01630431E8"
        )

    def _clean_base64(self, base64_string: str) -> str:
        """Bersihkan dan perbaiki base64 string (whitespace, padding, dll)"""
        if not base64_string:
            return ""
        # Hapus whitespace & karakter non-base64
        cleaned = re.sub(r'[^A-Za-z0-9+/]', '', base64_string)
        # Panjang harus kelipatan 4 (fix padding)
        padding_needed = len(cleaned) % 4
        if padding_needed:
            cleaned += '=' * (4 - padding_needed)
        return cleaned

    def generate_qris(self, nominal: Union[int, str], qris_statis: Optional[str] = None) -> Dict[str, Any]:
        """Generate QRIS dinamis"""
        qris_statis = qris_statis or self.qris_statis_default
        if not qris_statis:
            return {"status": "error", "message": "QRIS statis tidak tersedia"}
        try:
            nominal_int = int(nominal)
            if nominal_int < 1000:
                return {"status": "error", "message": "Nominal minimal Rp 1.000"}
        except (ValueError, TypeError):
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
                    return {"status": "error", "message": "Invalid base64 data received"}
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

    def generate_qris_image_file(self, nominal: Union[int, str], qris_statis: Optional[str] = None) -> Optional[str]:
        """Generate QRIS dan simpan ke file temporary, return path file"""
        result = self.generate_qris(nominal, qris_statis)
        if result["status"] != "success":
            print(f"[QRIS] Gagal generate: {result['message']}")
            return None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_path = temp_file.name
            qris_base64 = result["qris_base64"]
            cleaned_base64 = self._clean_base64(qris_base64)
            try:
                qris_bytes = base64.b64decode(cleaned_base64, validate=True)
            except Exception:
                qris_bytes = base64.b64decode(cleaned_base64, validate=False)
            with open(temp_path, "wb") as f:
                f.write(qris_bytes)
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                return temp_path
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
        except Exception as e:
            print(f"[QRIS] Error create temp file: {e}")
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            return None

class TelegramQRISSender:
    """Class untuk handle pengiriman QRIS ke Telegram"""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.qris_generator = QRISGenerator()

    def verify_bot_token(self) -> bool:
        """Verify bot token is valid"""
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=10)
            return response.json().get("ok", False)
        except:
            return False

    def send_photo(self, chat_id: str, photo_path: str, caption: str = "") -> Dict[str, Any]:
        """Kirim photo ke Telegram (BytesIO)"""
        try:
            if not os.path.exists(photo_path):
                return {"ok": False, "description": "File tidak ditemukan"}
            file_size = os.path.getsize(photo_path)
            if file_size == 0:
                return {"ok": False, "description": "File kosong"}
            with open(photo_path, 'rb') as photo:
                file_content = photo.read()
            if not file_content:
                return {"ok": False, "description": "File kosong"}
            file_stream = io.BytesIO(file_content)
            file_stream.name = "qris.png"
            files = {'photo': ('qris.png', file_stream, 'image/png')}
            data = {
                'chat_id': str(chat_id),
                'caption': caption,
                'parse_mode': 'HTML'
            }
            response = requests.post(
                f"{self.base_url}/sendPhoto",
                files=files,
                data=data,
                timeout=30
            )
            file_stream.close()
            return response.json()
        except Exception as e:
            return {"ok": False, "description": str(e)}

    def send_document(self, chat_id: str, file_path: str, caption: str = "") -> Dict[str, Any]:
        """Fallback: kirim sebagai document"""
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            file_stream = io.BytesIO(file_content)
            file_stream.name = "qris.png"
            files = {'document': ('qris.png', file_stream, 'image/png')}
            data = {
                'chat_id': str(chat_id),
                'caption': caption,
                'parse_mode': 'HTML'
            }
            response = requests.post(
                f"{self.base_url}/sendDocument",
                files=files,
                data=data,
                timeout=30
            )
            file_stream.close()
            return response.json()
        except Exception as e:
            return {"ok": False, "description": str(e)}

    def send_qris_to_telegram(self, chat_id: str, nominal: Union[int, str],
                              caption: str = "", qris_statis: Optional[str] = None) -> Dict[str, Any]:
        """Kirim QRIS ke Telegram, otomatis fallback jika error"""
        print(f"[QRIS] Proses QRIS nominal: Rp {nominal:,}")
        if not self.verify_bot_token():
            return {"status": "error", "message": "Bot token tidak valid"}
        temp_file_path = self.qris_generator.generate_qris_image_file(nominal, qris_statis)
        if not temp_file_path or not os.path.exists(temp_file_path):
            return {"status": "error", "message": "Gagal generate QRIS image"}
        file_size = os.path.getsize(temp_file_path)
        if file_size == 0:
            os.unlink(temp_file_path)
            return {"status": "error", "message": "File QRIS kosong"}
        formatted_nominal = f"Rp {int(nominal):,}".replace(",", ".")
        final_caption = caption or f"💳 QRIS Payment\n💵 Nominal: {formatted_nominal}\n⏰ Berlaku 24 jam"
        try:
            # 1. Coba kirim sebagai foto
            resp = self.send_photo(chat_id, temp_file_path, final_caption)
            if resp.get("ok"):
                os.unlink(temp_file_path)
                return {"status": "success", "message": "QRIS berhasil dikirim ke Telegram", "response": resp}
            # 2. Fallback kirim sebagai dokumen
            resp2 = self.send_document(chat_id, temp_file_path, final_caption)
            os.unlink(temp_file_path)
            if resp2.get("ok"):
                return {"status": "success", "message": "QRIS berhasil dikirim sebagai document", "response": resp2}
            return {"status": "error", "message": f"Telegram API error: {resp2.get('description', 'Unknown error')}", "response": resp2}
        except Exception as e:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            return {"status": "error", "message": f"Exception: {str(e)}"}

# =========================
# CONTOH PENGGUNAAN
# =========================

if __name__ == "__main__":
    print("=== QRIS TO TELEGRAM TEST ===")
    # Isi token dan chat_id anda!
    BOT_TOKEN = "ISI_TOKEN_BOT_ANDA"
    CHAT_ID = "ISI_CHAT_ID_ANDA"
    if BOT_TOKEN.startswith("ISI_") or CHAT_ID.startswith("ISI_"):
        print("❌ Silakan isi BOT_TOKEN dan CHAT_ID yang benar!")
        exit(1)
    sender = TelegramQRISSender(BOT_TOKEN)
    res = sender.send_qris_to_telegram(
        chat_id=CHAT_ID,
        nominal=15000,
        caption="🔰 Tes QRIS dari Bot"
    )
    print(res)
