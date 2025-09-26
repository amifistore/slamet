import requests
import json
import os
import base64
import io
from typing import Dict, Optional, Union, Any

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

class QRISGenerator:
    """QRIS Generator class untuk handle pembuatan QRIS dinamis"""
    
    def __init__(self, api_url: str = "https://qrisku.my.id/api", timeout: int = 30):
        self.api_url = api_url
        self.timeout = timeout
        self.qris_statis_default = self._get_qris_statis()
    
    def _get_qris_statis(self) -> str:
        """Ambil nilai QRIS statis dari config.json"""
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                qris_statis = config.get("QRIS_STATIS", "").strip()
                if not qris_statis:
                    print("[QRIS] Warning: QRIS_STATIS kosong di config.json")
                return qris_statis
        except Exception as e:
            print(f"[QRIS] Gagal baca QRIS_STATIS: {e}")
            return ""
    
    def generate_qris(self, nominal: Union[int, str], qris_statis: Optional[str] = None) -> Dict[str, Any]:
        """Generate QRIS dinamis"""
        if not qris_statis:
            qris_statis = self.qris_statis_default
        
        if not qris_statis:
            return {"status": "error", "message": "QRIS statis tidak tersedia"}
        
        try:
            nominal_str = str(nominal).strip()
            if not nominal_str.isdigit():
                return {"status": "error", "message": "Nominal harus angka"}
            
            nominal_int = int(nominal_str)
            if nominal_int < 1000:
                return {"status": "error", "message": "Nominal minimal Rp 1.000"}
                
        except Exception as e:
            return {"status": "error", "message": f"Format nominal invalid: {e}"}
        
        payload = {
            "amount": nominal_str,
            "qris_statis": qris_statis.strip()
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(
                self.api_url, 
                json=payload, 
                headers=headers, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, dict):
                return {"status": "error", "message": "Invalid response format"}
            
            if data.get("status") == "success" and "qris_base64" in data:
                return {
                    "status": "success",
                    "message": data.get("message", "QRIS berhasil digenerate"),
                    "qris_base64": data["qris_base64"],
                    "nominal": nominal_int
                }
            
            error_message = data.get("message", "Unknown error from QRIS API")
            return {"status": "error", "message": f"API Error: {error_message}"}
            
        except requests.exceptions.Timeout:
            return {"status": "error", "message": f"Timeout ({self.timeout}s)"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Network error: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}
    
    def generate_qris_image(self, nominal: Union[int, str], qris_statis: Optional[str] = None) -> Optional[io.BytesIO]:
        """
        Generate QRIS dan langsung return BytesIO object untuk Telegram
        """
        result = self.generate_qris(nominal, qris_statis)
        
        if result["status"] == "success":
            return self._base64_to_bytesio(result["qris_base64"])
        else:
            print(f"[QRIS] Gagal generate: {result['message']}")
            return None
    
    def _base64_to_bytesio(self, qris_base64: str) -> Optional[io.BytesIO]:
        """Convert base64 to BytesIO untuk Telegram"""
        if not qris_base64:
            return None
            
        try:
            # Clean base64 string
            cleaned_base64 = qris_base64.strip().replace('\n', '').replace('\r', '')
            
            # Fix padding
            missing_padding = len(cleaned_base64) % 4
            if missing_padding:
                cleaned_base64 += '=' * (4 - missing_padding)
            
            # Decode
            qris_bytes = base64.b64decode(cleaned_base64)
            
            # Create BytesIO
            bio = io.BytesIO(qris_bytes)
            bio.name = "qris.png"
            bio.seek(0)
            
            return bio
            
        except Exception as e:
            print(f"[QRIS] Error decode base64: {e}")
            return None

class TelegramQRISSender:
    """Class untuk handle pengiriman QRIS ke Telegram"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.qris_generator = QRISGenerator()
    
    def send_qris_to_telegram(self, chat_id: str, nominal: Union[int, str], 
                            caption: str = "", qris_statis: Optional[str] = None) -> Dict[str, Any]:
        """
        Kirim QRIS ke chat Telegram
        
        Args:
            chat_id: ID chat Telegram
            nominal: Nominal pembayaran
            caption: Keterangan gambar
            qris_statis: QRIS statis (optional)
        """
        # Generate QRIS image
        qris_image = self.qris_generator.generate_qris_image(nominal, qris_statis)
        
        if not qris_image:
            return {
                "status": "error", 
                "message": "Gagal generate QRIS image"
            }
        
        # Prepare data untuk Telegram
        formatted_nominal = f"Rp {int(nominal):,}".replace(",", ".")
        default_caption = f"QRIS Payment\nNominal: {formatted_nominal}"
        final_caption = caption or default_caption
        
        try:
            # Kirim photo ke Telegram
            files = {"photo": qris_image}
            data = {
                "chat_id": chat_id,
                "caption": final_caption,
                "parse_mode": "HTML"
            }
            
            response = requests.post(
                f"{self.base_url}/sendPhoto",
                files=files,
                data=data,
                timeout=30
            )
            
            response_data = response.json()
            
            if response_data.get("ok"):
                return {
                    "status": "success",
                    "message": "QRIS berhasil dikirim ke Telegram",
                    "response": response_data
                }
            else:
                error_description = response_data.get("description", "Unknown error")
                return {
                    "status": "error",
                    "message": f"Telegram API error: {error_description}",
                    "response": response_data
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": f"Network error saat kirim ke Telegram: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Unexpected error: {str(e)}"
            }
        finally:
            # Pastikan BytesIO ditutup
            if qris_image:
                qris_image.close()

# Fungsi legacy untuk backward compatibility
def get_qris_statis() -> str:
    generator = QRISGenerator()
    return generator.qris_statis_default

QRIS_STATIS_DEFAULT = get_qris_statis()

def generate_qris(nominal: Union[int, str], qris_statis: Optional[str] = None) -> Dict[str, Any]:
    generator = QRISGenerator()
    return generator.generate_qris(nominal, qris_statis)

def qris_base64_to_bytesio(qris_base64: str) -> Optional[io.BytesIO]:
    generator = QRISGenerator()
    return generator._base64_to_bytesio(qris_base64)

# Contoh penggunaan
if __name__ == "__main__":
    # Contoh 1: Generate QRIS saja
    qris_gen = QRISGenerator()
    result = qris_gen.generate_qris(10000)
    
    if result["status"] == "success":
        print("✅ QRIS berhasil dibuat!")
        qris_image = qris_gen.generate_qris_image(10000)
        if qris_image:
            print("📸 QRIS image siap dikirim")
            qris_image.close()  # Jangan lupa close
    else:
        print(f"❌ Error: {result['message']}")
    
    # Contoh 2: Kirim langsung ke Telegram
    # Ganti dengan bot token dan chat ID Anda
    BOT_TOKEN = "YOUR_BOT_TOKEN"
    CHAT_ID = "YOUR_CHAT_ID"
    
    if BOT_TOKEN != "YOUR_BOT_TOKEN":
        sender = TelegramQRISSender(BOT_TOKEN)
        telegram_result = sender.send_qris_to_telegram(
            chat_id=CHAT_ID,
            nominal=25000,
            caption="Pembayaran layanan - Silakan scan QRIS berikut:"
        )
        
        if telegram_result["status"] == "success":
            print("✅ QRIS berhasil dikirim ke Telegram!")
        else:
            print(f"❌ Gagal kirim ke Telegram: {telegram_result['message']}")
