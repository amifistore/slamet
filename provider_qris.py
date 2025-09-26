import requests
import json
import os
import base64
import io
import tempfile
from typing import Dict, Optional, Union, Any

class QRISGenerator:
    """QRIS Generator class untuk handle pembuatan QRIS dinamis"""
    
    def __init__(self, qris_statis: str = None, api_url: str = "https://qrisku.my.id/api", timeout: int = 30):
        self.api_url = api_url
        self.timeout = timeout
        # Gunakan QRIS statis yang diberikan atau default dari string Anda
        self.qris_statis_default = qris_statis or "00020101021126610014COM.GO-JEK.WWW01189360091434506469550210G4506469550303UMI51440014ID.CO.QRIS.WWW0215ID10243341364120303UMI5204569753033605802ID5923Amifi Store, Kmb, TLGSR6009BONDOWOSO61056827262070703A01630431E8"
    
    def generate_qris(self, nominal: Union[int, str], qris_statis: Optional[str] = None) -> Dict[str, Any]:
        """Generate QRIS dinamis"""
        if not qris_statis:
            qris_statis = self.qris_statis_default
        
        if not qris_statis:
            return {"status": "error", "message": "QRIS statis tidak tersedia"}
        
        # Validasi nominal
        try:
            nominal_int = int(nominal)
            if nominal_int < 1000:
                return {"status": "error", "message": "Nominal minimal Rp 1.000"}
        except (ValueError, TypeError):
            return {"status": "error", "message": "Nominal harus berupa angka"}
        
        payload = {
            "amount": str(nominal),
            "qris_statis": qris_statis.strip()
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            print(f"[QRIS] Request ke API dengan nominal: Rp {nominal_int:,}")
            print(f"[QRIS] QRIS Statis: {qris_statis[:50]}...")  # Print sebagian saja
            
            response = requests.post(
                self.api_url, 
                json=payload, 
                headers=headers, 
                timeout=self.timeout
            )
            print(f"[QRIS] Response status: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            print(f"[QRIS] API Response: {data}")
            
            if isinstance(data, dict) and data.get("status") == "success" and "qris_base64" in data:
                return {
                    "status": "success",
                    "message": data.get("message", "QRIS berhasil digenerate"),
                    "qris_base64": data["qris_base64"],
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
        """
        Generate QRIS dan simpan ke file temporary, return path file
        """
        result = self.generate_qris(nominal, qris_statis)
        
        if result["status"] != "success":
            print(f"[QRIS] Gagal generate: {result['message']}")
            return None
        
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_path = temp_file.name
            temp_file.close()
            
            # Decode base64 dan save ke file
            qris_base64 = result["qris_base64"]
            cleaned_base64 = qris_base64.strip().replace('\n', '').replace('\r', '')
            
            # Fix padding
            missing_padding = len(cleaned_base64) % 4
            if missing_padding:
                cleaned_base64 += '=' * (4 - missing_padding)
            
            qris_bytes = base64.b64decode(cleaned_base64)
            
            with open(temp_path, "wb") as f:
                f.write(qris_bytes)
            
            print(f"[QRIS] File created: {temp_path} ({len(qris_bytes)} bytes)")
            return temp_path
            
        except Exception as e:
            print(f"[QRIS] Error create temp file: {e}")
            return None

class TelegramQRISSender:
    """Class untuk handle pengiriman QRIS ke Telegram"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.qris_generator = QRISGenerator()  # Gunakan QRIS statis default
    
    def send_photo_simple(self, chat_id: str, photo_path: str, caption: str = "") -> Dict[str, Any]:
        """
        Kirim photo ke Telegram dengan approach paling sederhana
        """
        try:
            print(f"[Telegram] Sending photo: {photo_path}")
            
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
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
                
                print(f"[Telegram] Response: {response.status_code}")
                return response.json()
                
        except Exception as e:
            print(f"[Telegram] Error: {e}")
            return {"ok": False, "description": str(e)}
    
    def send_qris_to_telegram(self, chat_id: str, nominal: Union[int, str], 
                            caption: str = "", qris_statis: Optional[str] = None) -> Dict[str, Any]:
        """
        Kirim QRIS ke Telegram
        """
        print(f"[QRIS] Starting process for nominal: Rp {nominal:,}")
        
        # Generate QRIS dan simpan ke file
        temp_file_path = self.qris_generator.generate_qris_image_file(nominal, qris_statis)
        
        if not temp_file_path or not os.path.exists(temp_file_path):
            return {
                "status": "error", 
                "message": "Gagal generate QRIS image"
            }
        
        # Format caption
        formatted_nominal = f"Rp {int(nominal):,}".replace(",", ".")
        final_caption = caption or f"💳 QRIS Payment\n💵 Nominal: {formatted_nominal}\n⏰ Berlaku 24 jam"
        
        try:
            print(f"[Telegram] Sending to chat_id: {chat_id}")
            
            # Kirim photo ke Telegram
            response = self.send_photo_simple(chat_id, temp_file_path, final_caption)
            
            # Clean up temporary file
            try:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    print(f"[QRIS] Temporary file cleaned: {temp_file_path}")
            except Exception as e:
                print(f"[QRIS] Error cleaning temp file: {e}")
            
            if response.get("ok"):
                return {
                    "status": "success",
                    "message": "QRIS berhasil dikirim ke Telegram",
                    "response": response
                }
            else:
                error_msg = response.get("description", "Unknown error")
                print(f"[Telegram] API Error: {error_msg}")
                return {
                    "status": "error",
                    "message": f"Telegram API error: {error_msg}",
                    "response": response
                }
                
        except Exception as e:
            # Clean up temporary file jika error
            try:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            except:
                pass
            
            print(f"[Telegram] Exception: {e}")
            return {
                "status": "error",
                "message": f"Error saat mengirim ke Telegram: {str(e)}"
            }

# =============================================================================
# FUNGSI LEGACY UNTUK COMPATIBILITY
# =============================================================================

def get_qris_statis() -> str:
    """Legacy function"""
    generator = QRISGenerator()
    return generator.qris_statis_default

def generate_qris(nominal: Union[int, str], qris_statis: Optional[str] = None) -> Dict[str, Any]:
    """Legacy function"""
    generator = QRISGenerator()
    return generator.generate_qris(nominal, qris_statis)

def qris_base64_to_bytesio(qris_base64: str) -> Optional[io.BytesIO]:
    """Legacy function"""
    if not qris_base64:
        return None
        
    try:
        cleaned_base64 = qris_base64.strip().replace('\n', '').replace('\r', '')
        
        missing_padding = len(cleaned_base64) % 4
        if missing_padding:
            cleaned_base64 += '=' * (4 - missing_padding)
        
        qris_bytes = base64.b64decode(cleaned_base64)
        
        bio = io.BytesIO(qris_bytes)
        bio.name = "qris.png"
        bio.seek(0)
        
        return bio
        
    except Exception as e:
        print(f"[QRIS] Error decode base64: {e}")
        return None

QRIS_STATIS_DEFAULT = "00020101021126610014COM.GO-JEK.WWW01189360091434506469550210G4506469550303UMI51440014ID.CO.QRIS.WWW0215ID10243341364120303UMI5204569753033605802ID5923Amifi Store, Kmb, TLGSR6009BONDOWOSO61056827262070703A01630431E8"

# =============================================================================
# FUNGSI TEST LANGSUNG
# =============================================================================

def test_direct():
    """Test langsung tanpa config"""
    print("🚀 TEST LANGSUNG QRIS GENERATOR")
    print("=" * 60)
    
    # Test 1: Generate QRIS saja
    print("1. Testing QRIS Generation...")
    qris_gen = QRISGenerator()  # Otomatis pakai QRIS statis dari string
    
    nominal = 10000
    result = qris_gen.generate_qris(nominal)
    
    print(f"Nominal: Rp {nominal:,}")
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    
    if result["status"] == "success":
        print("✅ QRIS berhasil digenerate!")
        
        # Test 2: Simpan ke file
        print("\n2. Testing File Creation...")
        file_path = qris_gen.generate_qris_image_file(nominal)
        if file_path and os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"✅ File berhasil dibuat: {file_path}")
            print(f"📁 File size: {file_size} bytes")
            
            # Cleanup
            os.unlink(file_path)
            print("🧹 File temporary dibersihkan")
        else:
            print("❌ Gagal membuat file")
    
    return result["status"] == "success"

def test_telegram_integration(bot_token: str, chat_id: str):
    """Test integrasi dengan Telegram"""
    print(f"\n3. Testing Telegram Integration...")
    
    if not bot_token or bot_token == "YOUR_BOT_TOKEN":
        print("❌ Bot token tidak valid")
        return False
    
    if not chat_id or chat_id == "YOUR_CHAT_ID":
        print("❌ Chat ID tidak valid")
        return False
    
    sender = TelegramQRISSender(bot_token)
    
    result = sender.send_qris_to_telegram(
        chat_id=chat_id,
        nominal=10000,
        caption="🔰 TEST QRIS LANGSUNG - Silakan scan untuk pembayaran"
    )
    
    if result["status"] == "success":
        print("✅ QRIS berhasil dikirim ke Telegram!")
        return True
    else:
        print(f"❌ Gagal: {result['message']}")
        return False

def quick_test():
    """Test cepat tanpa Telegram"""
    print("⚡ QUICK TEST - QRIS Generation Only")
    print("=" * 50)
    
    # Gunakan QRIS statis langsung
    QRIS_STATIS = "00020101021126610014COM.GO-JEK.WWW01189360091434506469550210G4506469550303UMI51440014ID.CO.QRIS.WWW0215ID10243341364120303UMI5204569753033605802ID5923Amifi Store, Kmb, TLGSR6009BONDOWOSO61056827262070703A01630431E8"
    
    # Test dengan nominal berbeda
    test_cases = [10000, 25000, 50000]
    
    for nominal in test_cases:
        print(f"\n💰 Testing nominal: Rp {nominal:,}")
        
        # Langsung call API
        url = "https://qrisku.my.id/api"
        payload = {
            "amount": str(nominal),
            "qris_statis": QRIS_STATIS
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            data = response.json()
            
            if data.get("status") == "success":
                print("✅ Success")
                print(f"📊 Message: {data.get('message')}")
            else:
                print(f"❌ Failed: {data.get('message')}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🎯 QRIS DIRECT TEST (Without config.json)")
    print("=" * 60)
    
    # Pilih test mode
    print("Pilih test mode:")
    print("1. Quick API Test")
    print("2. Full Generation Test")
    print("3. Telegram Integration Test")
    
    choice = input("Pilihan (1/2/3): ").strip()
    
    if choice == "1":
        quick_test()
    elif choice == "2":
        test_direct()
    elif choice == "3":
        bot_token = input("Masukkan bot token: ").strip()
        chat_id = input("Masukkan chat ID: ").strip()
        test_direct()  # Test generation dulu
        test_telegram_integration(bot_token, chat_id)
    else:
        # Default test
        test_direct()
