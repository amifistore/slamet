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
        self.qris_statis_default = qris_statis or "00020101021126610014COM.GO-JEK.WWW01189360091434506469550210G4506469550303UMI51440014ID.CO.QRIS.WWW0215ID10243341364120303UMI5204569753033605802ID5923Amifi Store, Kmb, TLGSR6009BONDOWOSO61056827262070703A01630431E8"
    
    def _fix_base64_padding(self, base64_string: str) -> str:
        """Perbaiki padding base64"""
        if not base64_string:
            return ""
        
        cleaned = re.sub(r'\s+', '', base64_string)
        padding = len(cleaned) % 4
        if padding == 1:
            cleaned = cleaned[:-1]
            padding = len(cleaned) % 4
        
        if padding == 2:
            cleaned += '=='
        elif padding == 3:
            cleaned += '='
        
        return cleaned
    
    def generate_qris(self, nominal: Union[int, str], qris_statis: Optional[str] = None) -> Dict[str, Any]:
        """Generate QRIS dinamis"""
        if not qris_statis:
            qris_statis = self.qris_statis_default
        
        if not qris_statis:
            return {"status": "error", "message": "QRIS statis tidak tersedia"}
        
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
            response = requests.post(
                self.api_url, 
                json=payload, 
                headers=headers, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, dict) and data.get("status") == "success" and "qris_base64" in data:
                fixed_base64 = self._fix_base64_padding(data["qris_base64"])
                
                return {
                    "status": "success",
                    "message": data.get("message", "QRIS berhasil digenerate"),
                    "qris_base64": fixed_base64,
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
        """Generate QRIS dan simpan ke file temporary"""
        result = self.generate_qris(nominal, qris_statis)
        
        if result["status"] != "success":
            print(f"[QRIS] Gagal generate: {result['message']}")
            return None
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_path = temp_file.name
            
            qris_base64 = result["qris_base64"]
            
            try:
                qris_bytes = base64.b64decode(qris_base64, validate=True)
            except:
                qris_bytes = base64.b64decode(qris_base64, validate=False)
            
            with open(temp_path, "wb") as f:
                f.write(qris_bytes)
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                return temp_path
            else:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return None
            
        except Exception as e:
            print(f"[QRIS] Error create temp file: {e}")
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            return None

class TelegramQRISSender:
    """Class untuk handle pengiriman QRIS ke Telegram dengan approach yang benar"""
    
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
    
    def send_photo_correct(self, chat_id: str, photo_path: str, caption: str = "") -> Dict[str, Any]:
        """
        Method yang benar untuk kirim photo ke Telegram API
        """
        try:
            if not os.path.exists(photo_path):
                return {"ok": False, "description": "File tidak ditemukan"}
            
            file_size = os.path.getsize(photo_path)
            if file_size == 0:
                return {"ok": False, "description": "File kosong"}
            
            print(f"[Telegram] Sending photo: {file_size} bytes")
            
            # Baca file sebagai binary
            with open(photo_path, 'rb') as f:
                photo_data = f.read()
            
            # Approach yang paling benar menurut dokumentasi Telegram
            files = {'photo': ('qris.png', photo_data, 'multipart/form-data')}
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
            
            return response.json()
            
        except Exception as e:
            print(f"[Telegram] Error: {e}")
            return {"ok": False, "description": str(e)}
    
    def send_photo_alternative(self, chat_id: str, photo_path: str, caption: str = "") -> Dict[str, Any]:
        """
        Alternative approach - gunakan method yang lebih sederhana
        """
        try:
            with open(photo_path, 'rb') as photo:
                # Gunakan approach langsung
                files = {'photo': photo}
                data = {
                    'chat_id': str(chat_id),
                    'caption': caption
                }
                
                response = requests.post(
                    f"{self.base_url}/sendPhoto",
                    files=files,
                    data=data,
                    timeout=30
                )
                
                return response.json()
                
        except Exception as e:
            return {"ok": False, "description": str(e)}
    
    def send_photo_with_upload(self, chat_id: str, photo_path: str, caption: str = "") -> Dict[str, Any]:
        """
        Gunakan approach upload yang berbeda
        """
        try:
            import mimetypes
            mime_type, _ = mimetypes.guess_type(photo_path)
            mime_type = mime_type or 'image/png'
            
            with open(photo_path, 'rb') as photo:
                files = {'photo': ('qris.png', photo, mime_type)}
                data = {'chat_id': str(chat_id), 'caption': caption}
                
                response = requests.post(
                    f"{self.base_url}/sendPhoto",
                    files=files,
                    data=data,
                    timeout=30
                )
                
                return response.json()
                
        except Exception as e:
            return {"ok": False, "description": str(e)}
    
    def send_photo_manual_multipart(self, chat_id: str, photo_path: str, caption: str = "") -> Dict[str, Any]:
        """
        Manual multipart form data - paling mendekati spesifikasi Telegram
        """
        try:
            import mimetypes
            from requests_toolbelt.multipart.encoder import MultipartEncoder
            
            mime_type = mimetypes.guess_type(photo_path)[0] or 'image/png'
            
            with open(photo_path, 'rb') as f:
                photo_data = f.read()
            
            multipart_data = MultipartEncoder(
                fields={
                    'chat_id': str(chat_id),
                    'caption': caption,
                    'photo': ('qris.png', photo_data, mime_type)
                }
            )
            
            headers = {
                'Content-Type': multipart_data.content_type
            }
            
            response = requests.post(
                f"{self.base_url}/sendPhoto",
                data=multipart_data,
                headers=headers,
                timeout=30
            )
            
            return response.json()
            
        except ImportError:
            print("[Telegram] requests_toolbelt not available, using fallback")
            return self.send_photo_correct(chat_id, photo_path, caption)
        except Exception as e:
            return {"ok": False, "description": str(e)}
    
    def send_qris_to_telegram(self, chat_id: str, nominal: Union[int, str], 
                            caption: str = "", qris_statis: Optional[str] = None) -> Dict[str, Any]:
        """
        Kirim QRIS ke Telegram dengan berbagai approach
        """
        print(f"[QRIS] Memulai proses untuk nominal: Rp {nominal:,}")
        
        # Verify bot token
        if not self.verify_bot_token():
            return {"status": "error", "message": "Bot token tidak valid"}
        
        # Generate QRIS file
        temp_file_path = self.qris_generator.generate_qris_image_file(nominal, qris_statis)
        
        if not temp_file_path or not os.path.exists(temp_file_path):
            return {"status": "error", "message": "Gagal generate QRIS image"}
        
        file_size = os.path.getsize(temp_file_path)
        print(f"[QRIS] File generated: {file_size} bytes")
        
        if file_size == 0:
            os.unlink(temp_file_path)
            return {"status": "error", "message": "File QRIS kosong"}
        
        # Format caption
        formatted_nominal = f"Rp {int(nominal):,}".replace(",", ".")
        final_caption = caption or f"💳 QRIS Payment\n💵 Nominal: {formatted_nominal}\n⏰ Berlaku 24 jam"
        
        methods = [
            ("Manual Multipart", self.send_photo_manual_multipart),
            ("Correct Method", self.send_photo_correct),
            ("Alternative", self.send_photo_alternative),
            ("With Upload", self.send_photo_with_upload),
        ]
        
        for method_name, method_func in methods:
            print(f"[Telegram] Trying {method_name}...")
            try:
                response = method_func(chat_id, temp_file_path, final_caption)
                
                if response.get("ok"):
                    print(f"✅ Success with {method_name}")
                    os.unlink(temp_file_path)
                    return {
                        "status": "success",
                        "message": f"QRIS berhasil dikirim ({method_name})",
                        "response": response
                    }
                else:
                    print(f"❌ {method_name} failed: {response.get('description')}")
                    
            except Exception as e:
                print(f"❌ {method_name} error: {e}")
        
        # Semua method gagal
        os.unlink(temp_file_path)
        return {
            "status": "error",
            "message": "Semua method pengiriman gagal"
        }

# =============================================================================
# SOLUTION: GUNAKAN TELEGRAM LIBRARY YANG RESMI
# =============================================================================

class TelegramOfficialSender:
    """
    Gunakan python-telegram-bot library yang official
    Ini adalah solusi paling reliable
    """
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.qris_generator = QRISGenerator()
        
    def send_qris_using_library(self, chat_id: str, nominal: Union[int, str], 
                               caption: str = "", qris_statis: Optional[str] = None) -> Dict[str, Any]:
        """
        Gunakan python-telegram-bot library yang lebih reliable
        """
        try:
            from telegram import Bot
            from telegram.error import TelegramError
            
            bot = Bot(token=self.bot_token)
            
            # Generate QRIS file
            temp_file_path = self.qris_generator.generate_qris_image_file(nominal, qris_statis)
            
            if not temp_file_path:
                return {"status": "error", "message": "Gagal generate QRIS image"}
            
            try:
                # Kirim photo menggunakan library official
                with open(temp_file_path, 'rb') as photo:
                    bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=caption or f"QRIS Payment - Rp {int(nominal):,}",
                        parse_mode='HTML'
                    )
                
                os.unlink(temp_file_path)
                return {"status": "success", "message": "QRIS berhasil dikirim"}
                
            except TelegramError as e:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                return {"status": "error", "message": f"Telegram error: {str(e)}"}
            
        except ImportError:
            return {"status": "error", "message": "python-telegram-bot library tidak terinstall"}
        except Exception as e:
            return {"status": "error", "message": f"Error: {str(e)}"}

# =============================================================================
# FUNGSI COMPATIBILITY
# =============================================================================

def get_qris_statis() -> str:
    generator = QRISGenerator()
    return generator.qris_statis_default

def generate_qris(nominal: Union[int, str], qris_statis: Optional[str] = None) -> Dict[str, Any]:
    generator = QRISGenerator()
    return generator.generate_qris(nominal, qris_statis)

def qris_base64_to_bytesio(qris_base64: str) -> Optional[io.BytesIO]:
    if not qris_base64:
        return None
        
    try:
        cleaned = re.sub(r'\s+', '', qris_base64)
        padding = len(cleaned) % 4
        if padding == 2:
            cleaned += '=='
        elif padding == 3:
            cleaned += '='
        
        qris_bytes = base64.b64decode(cleaned, validate=False)
        
        bio = io.BytesIO(qris_bytes)
        bio.name = "qris.png"
        bio.seek(0)
        
        return bio
        
    except Exception as e:
        print(f"[QRIS] Error decode base64: {e}")
        return None

QRIS_STATIS_DEFAULT = "00020101021126610014COM.GO-JEK.WWW01189360091434506469550210G4506469550303UMI51440014ID.CO.QRIS.WWW0215ID10243341364120303UMI5204569753033605802ID5923Amifi Store, Kmb, TLGSR6009BONDOWOSO61056827262070703A01630431E8"

# =============================================================================
# TEST FUNCTIONS
# =============================================================================

def test_with_requests_library():
    """Test dengan requests library"""
    print("🔧 TEST WITH REQUESTS LIBRARY")
    print("=" * 50)
    
    BOT_TOKEN = "YOUR_BOT_TOKEN"
    CHAT_ID = "YOUR_CHAT_ID"
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN":
        print("❌ Set BOT_TOKEN dulu")
        return
    
    sender = TelegramQRISSender(BOT_TOKEN)
    result = sender.send_qris_to_telegram(CHAT_ID, 10000, "TEST REQUESTS")
    
    print(f"Result: {result['status']}")
    print(f"Message: {result['message']}")

def test_with_official_library():
    """Test dengan official telegram library"""
    print("📚 TEST WITH OFFICIAL LIBRARY")
    print("=" * 50)
    
    try:
        from telegram import Bot
        from telegram.error import TelegramError
        
        BOT_TOKEN = "YOUR_BOT_TOKEN"
        CHAT_ID = "YOUR_CHAT_ID"
        
        if BOT_TOKEN == "YOUR_BOT_TOKEN":
            print("❌ Set BOT_TOKEN dulu")
            return
        
        sender = TelegramOfficialSender(BOT_TOKEN)
        result = sender.send_qris_using_library(CHAT_ID, 10000, "TEST OFFICIAL LIBRARY")
        
        print(f"Result: {result['status']}")
        print(f"Message: {result['message']}")
        
    except ImportError:
        print("❌ python-telegram-bot tidak terinstall")
        print("💡 Install dengan: pip install python-telegram-bot")

def install_telegram_library():
    """Install telegram library"""
    print("📦 Installing python-telegram-bot...")
    os.system("pip install python-telegram-bot")
    print("✅ Installation complete")

if __name__ == "__main__":
    print("🎯 ULTIMATE TELEGRAM FIX")
    print("=" * 60)
    
    print("Pilih solusi:")
    print("1. Test dengan Requests Library (current)")
    print("2. Test dengan Official Telegram Library (recommended)")
    print("3. Install Telegram Library")
    
    choice = input("Pilihan (1/2/3): ").strip() or "1"
    
    if choice == "1":
        test_with_requests_library()
    elif choice == "2":
        test_with_official_library()
    elif choice == "3":
        install_telegram_library()
