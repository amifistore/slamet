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
    
    def save_qris_to_file(self, nominal: Union[int, str], filename: str = "qris.png", qris_statis: Optional[str] = None) -> bool:
        """Save QRIS ke file PNG"""
        result = self.generate_qris(nominal, qris_statis)
        
        if result["status"] != "success":
            print(f"[QRIS] Gagal generate: {result['message']}")
            return False
        
        try:
            qris_base64 = result["qris_base64"]
            cleaned_base64 = qris_base64.strip().replace('\n', '').replace('\r', '')
            
            # Fix padding
            missing_padding = len(cleaned_base64) % 4
            if missing_padding:
                cleaned_base64 += '=' * (4 - missing_padding)
            
            # Decode dan save ke file
            qris_bytes = base64.b64decode(cleaned_base64)
            
            with open(filename, "wb") as f:
                f.write(qris_bytes)
            
            print(f"[QRIS] QRIS disimpan sebagai: {filename}")
            return True
            
        except Exception as e:
            print(f"[QRIS] Error save to file: {e}")
            return False

class TelegramQRISSender:
    """Class untuk handle pengiriman QRIS ke Telegram"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.qris_generator = QRISGenerator()
    
    def _send_photo_with_file(self, chat_id: str, photo_path: str, caption: str = "") -> Dict[str, Any]:
        """Kirim photo menggunakan file path"""
        try:
            with open(photo_path, 'rb') as photo_file:
                files = {'photo': photo_file}
                data = {
                    'chat_id': chat_id,
                    'caption': caption,
                    'parse_mode': 'HTML'
                }
                
                response = requests.post(
                    f"{self.base_url}/sendPhoto",
                    files=files,
                    data=data,
                    timeout=30
                )
                
                return response.json()
                
        except Exception as e:
            return {"ok": False, "description": f"Error: {str(e)}"}
    
    def _send_photo_with_base64(self, chat_id: str, base64_data: str, caption: str = "") -> Dict[str, Any]:
        """Kirim photo menggunakan base64 langsung"""
        try:
            # Clean base64 data
            cleaned_base64 = base64_data.strip().replace('\n', '').replace('\r', '')
            
            # Fix padding
            missing_padding = len(cleaned_base64) % 4
            if missing_padding:
                cleaned_base64 += '=' * (4 - missing_padding)
            
            # Decode base64
            file_data = base64.b64decode(cleaned_base64)
            
            # Create file-like object
            files = {'photo': ('qris.png', file_data, 'image/png')}
            data = {
                'chat_id': chat_id,
                'caption': caption,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(
                f"{self.base_url}/sendPhoto",
                files=files,
                data=data,
                timeout=30
            )
            
            return response.json()
            
        except Exception as e:
            return {"ok": False, "description": f"Base64 Error: {str(e)}"}
    
    def send_qris_to_telegram(self, chat_id: str, nominal: Union[int, str], 
                            caption: str = "", qris_statis: Optional[str] = None) -> Dict[str, Any]:
        """
        Kirim QRIS ke chat Telegram dengan multiple approaches
        """
        # Generate QRIS
        result = self.qris_generator.generate_qris(nominal, qris_statis)
        
        if result["status"] != "success":
            return {
                "status": "error", 
                "message": f"Gagal generate QRIS: {result['message']}"
            }
        
        formatted_nominal = f"Rp {int(nominal):,}".replace(",", ".")
        default_caption = f"💳 QRIS Payment\n💵 Nominal: {formatted_nominal}\n⏰ Berlaku 24 jam"
        final_caption = caption or default_caption
        
        qris_base64 = result["qris_base64"]
        
        # Approach 1: Coba dengan base64 langsung
        print("[Telegram] Mencoba kirim dengan base64...")
        response = self._send_photo_with_base64(chat_id, qris_base64, final_caption)
        
        if response.get("ok"):
            return {
                "status": "success",
                "message": "QRIS berhasil dikirim ke Telegram",
                "response": response
            }
        
        # Approach 2: Simpan ke file temporary lalu kirim
        print("[Telegram] Mencoba kirim dengan file...")
        try:
            temp_file = "temp_qris.png"
            if self.qris_generator.save_qris_to_file(nominal, temp_file, qris_statis):
                response = self._send_photo_with_file(chat_id, temp_file, final_caption)
                
                # Clean up temporary file
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                
                if response.get("ok"):
                    return {
                        "status": "success",
                        "message": "QRIS berhasil dikirim ke Telegram",
                        "response": response
                    }
                else:
                    error_msg = response.get("description", "Unknown error")
                    return {
                        "status": "error",
                        "message": f"Telegram API error: {error_msg}",
                        "response": response
                    }
            else:
                return {
                    "status": "error",
                    "message": "Gagal menyimpan QRIS ke file temporary"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error dengan file approach: {str(e)}"
            }
        
        # Jika semua approach gagal
        error_msg = response.get("description", "Unknown error")
        return {
            "status": "error",
            "message": f"Gagal kirim ke Telegram: {error_msg}",
            "response": response
        }
    
    def send_qris_simple(self, chat_id: str, nominal: Union[int, str], 
                        caption: str = "", qris_statis: Optional[str] = None) -> bool:
        """
        Simplified version untuk kirim QRIS
        """
        result = self.send_qris_to_telegram(chat_id, nominal, caption, qris_statis)
        return result["status"] == "success"

# Fungsi utility untuk testing
def test_qris_generation():
    """Test QRIS generation saja"""
    print("🔍 Testing QRIS Generation...")
    
    qris_gen = QRISGenerator()
    
    # Test dengan nominal berbeda
    test_nominals = [10000, 25000, 50000]
    
    for nominal in test_nominals:
        print(f"\n💰 Testing nominal: Rp {nominal:,}")
        result = qris_gen.generate_qris(nominal)
        
        if result["status"] == "success":
            print("✅ QRIS berhasil digenerate")
            print(f"📊 Message: {result['message']}")
            # Test save to file
            filename = f"test_qris_{nominal}.png"
            if qris_gen.save_qris_to_file(nominal, filename):
                print(f"💾 QRIS disimpan sebagai: {filename}")
            else:
                print("❌ Gagal save QRIS ke file")
        else:
            print(f"❌ Gagal: {result['message']}")

def test_telegram_send(bot_token: str, chat_id: str):
    """Test kirim ke Telegram"""
    print(f"\n📱 Testing Telegram Send...")
    
    if bot_token == "YOUR_BOT_TOKEN" or chat_id == "YOUR_CHAT_ID":
        print("❌ Silakan set BOT_TOKEN dan CHAT_ID yang valid")
        return
    
    sender = TelegramQRISSender(bot_token)
    
    # Test dengan nominal kecil dulu
    result = sender.send_qris_to_telegram(
        chat_id=chat_id,
        nominal=10000,
        caption="🔰 TEST QRIS - Silakan scan QRIS berikut untuk pembayaran"
    )
    
    if result["status"] == "success":
        print("✅ QRIS berhasil dikirim ke Telegram!")
    else:
        print(f"❌ Gagal: {result['message']}")

# Contoh penggunaan
if __name__ == "__main__":
    print("🚀 QRIS Generator Test Suite")
    print("=" * 50)
    
    # Test QRIS generation
    test_qris_generation()
    
    # Test Telegram send (ganti dengan token dan chat ID Anda)
    BOT_TOKEN = "YOUR_BOT_TOKEN"  # Ganti dengan token bot Anda
    CHAT_ID = "YOUR_CHAT_ID"      # Ganti dengan chat ID Anda
    
    test_telegram_send(BOT_TOKEN, CHAT_ID)
