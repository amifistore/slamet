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
    """Class untuk handle pengiriman QRIS ke Telegram dengan fix khusus"""
    
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
    
    def send_photo_safe(self, chat_id: str, photo_path: str, caption: str = "") -> Dict[str, Any]:
        """
        Kirim photo dengan method yang lebih safe untuk menghindari file identifier error
        """
        try:
            if not os.path.exists(photo_path):
                return {"ok": False, "description": "File tidak ditemukan"}
            
            file_size = os.path.getsize(photo_path)
            if file_size == 0:
                return {"ok": False, "description": "File kosong"}
            
            print(f"[Telegram] Preparing to send photo: {file_size} bytes")
            
            # Baca file sebagai binary
            with open(photo_path, 'rb') as f:
                file_content = f.read()
            
            # Pastikan file content valid
            if len(file_content) == 0:
                return {"ok": False, "description": "File content kosong"}
            
            # Method 1: Gunakan BytesIO dengan explicit filename
            file_stream = io.BytesIO(file_content)
            file_stream.name = "qris.png"  # Pastikan ada nama file
            
            files = {'photo': ('qris.png', file_stream, 'image/png')}
            data = {
                'chat_id': str(chat_id),  # Pastikan chat_id string
                'caption': caption,
                'parse_mode': 'HTML'
            }
            
            print(f"[Telegram] Sending to chat_id: {chat_id}")
            response = requests.post(
                f"{self.base_url}/sendPhoto",
                files=files,
                data=data,
                timeout=30
            )
            
            # Tutup stream
            file_stream.close()
            
            response_data = response.json()
            print(f"[Telegram] API Response: {response_data.get('ok', False)}")
            
            if not response_data.get("ok"):
                print(f"[Telegram] Error: {response_data.get('description')}")
            
            return response_data
            
        except Exception as e:
            print(f"[Telegram] Exception: {e}")
            return {"ok": False, "description": str(e)}
    
    def send_document_fallback(self, chat_id: str, file_path: str, caption: str = "") -> Dict[str, Any]:
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
    
    def send_photo_direct(self, chat_id: str, file_path: str, caption: str = "") -> Dict[str, Any]:
        """Method langsung tanpa BytesIO"""
        try:
            with open(file_path, 'rb') as photo:
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
    
    def send_qris_to_telegram(self, chat_id: str, nominal: Union[int, str], 
                            caption: str = "", qris_statis: Optional[str] = None) -> Dict[str, Any]:
        """
        Kirim QRIS ke Telegram dengan multiple strategies
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
        print(f"[QRIS] File generated: {temp_file_path} ({file_size} bytes)")
        
        if file_size == 0:
            os.unlink(temp_file_path)
            return {"status": "error", "message": "File QRIS kosong"}
        
        # Format caption
        formatted_nominal = f"Rp {int(nominal):,}".replace(",", ".")
        final_caption = caption or f"💳 QRIS Payment\n💵 Nominal: {formatted_nominal}\n⏰ Berlaku 24 jam"
        
        responses = []
        
        try:
            # Strategy 1: Safe method dengan BytesIO
            print("[Telegram] Strategy 1: Safe BytesIO method")
            response1 = self.send_photo_safe(chat_id, temp_file_path, final_caption)
            responses.append(("Safe BytesIO", response1))
            
            if response1.get("ok"):
                os.unlink(temp_file_path)
                return {
                    "status": "success",
                    "message": "QRIS berhasil dikirim ke Telegram",
                    "response": response1
                }
            
            # Strategy 2: Direct method
            print("[Telegram] Strategy 2: Direct method")
            response2 = self.send_photo_direct(chat_id, temp_file_path, final_caption)
            responses.append(("Direct", response2))
            
            if response2.get("ok"):
                os.unlink(temp_file_path)
                return {
                    "status": "success",
                    "message": "QRIS berhasil dikirim ke Telegram",
                    "response": response2
                }
            
            # Strategy 3: Sebagai document
            print("[Telegram] Strategy 3: Document fallback")
            response3 = self.send_document_fallback(chat_id, temp_file_path, final_caption)
            responses.append(("Document", response3))
            
            if response3.get("ok"):
                os.unlink(temp_file_path)
                return {
                    "status": "success", 
                    "message": "QRIS berhasil dikirim sebagai document",
                    "response": response3
                }
            
            # Semua strategy gagal
            error_msg = responses[-1][1].get("description", "Unknown error")
            return {
                "status": "error",
                "message": f"Semua method gagal: {error_msg}",
                "responses": responses
            }
                
        except Exception as e:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            return {
                "status": "error",
                "message": f"Error: {str(e)}"
            }
        finally:
            # Pastikan file dihapus
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

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
# TEST TELEGRAM SEND
# =============================================================================

def test_telegram_send():
    """Test pengiriman ke Telegram"""
    print("📱 TEST TELEGRAM SEND")
    print("=" * 50)
    
    # Ganti dengan bot token dan chat ID Anda
    BOT_TOKEN = "YOUR_BOT_TOKEN"  # Ganti dengan token bot Anda
    CHAT_ID = "YOUR_CHAT_ID"      # Ganti dengan chat ID Anda
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN" or CHAT_ID == "YOUR_CHAT_ID":
        print("❌ Silakan set BOT_TOKEN dan CHAT_ID yang valid")
        return False
    
    sender = TelegramQRISSender(BOT_TOKEN)
    
    # Test dengan nominal kecil
    result = sender.send_qris_to_telegram(
        chat_id=CHAT_ID,
        nominal=10000,
        caption="🔰 TEST QRIS - Silakan scan untuk pembayaran"
    )
    
    if result["status"] == "success":
        print("✅ QRIS berhasil dikirim ke Telegram!")
        return True
    else:
        print(f"❌ Gagal: {result['message']}")
        if "responses" in result:
            for method, resp in result["responses"]:
                print(f"   {method}: {resp.get('description')}")
        return False

def create_test_image():
    """Buat test image sederhana untuk debug Telegram"""
    from PIL import Image, ImageDraw
    
    # Buat image sederhana
    img = Image.new('RGB', (200, 200), color='white')
    d = ImageDraw.Draw(img)
    d.text((10, 10), "TEST QRIS", fill='black')
    
    # Simpan ke temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    temp_path = temp_file.name
    temp_file.close()
    
    img.save(temp_path)
    return temp_path

def test_telegram_with_simple_image():
    """Test Telegram dengan image sederhana"""
    print("🖼️ TEST WITH SIMPLE IMAGE")
    print("=" * 50)
    
    BOT_TOKEN = "YOUR_BOT_TOKEN"  # Ganti
    CHAT_ID = "YOUR_CHAT_ID"      # Ganti
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN":
        print("❌ Set BOT_TOKEN dulu")
        return
    
    # Buat test image
    test_image_path = create_test_image()
    print(f"Test image created: {test_image_path}")
    
    sender = TelegramQRISSender(BOT_TOKEN)
    
    # Test kirim image sederhana
    response = sender.send_photo_safe(CHAT_ID, test_image_path, "TEST SIMPLE IMAGE")
    
    if response.get("ok"):
        print("✅ Simple image berhasil dikirim!")
    else:
        print(f"❌ Gagal: {response.get('description')}")
    
    # Cleanup
    if os.path.exists(test_image_path):
        os.unlink(test_image_path)

if __name__ == "__main__":
    print("🎯 TELEGRAM FIX - File Identifier Error")
    print("=" * 60)
    
    print("Pilih test:")
    print("1. Test Telegram Send dengan QRIS")
    print("2. Test dengan Simple Image")
    print("3. Quick Generation Test")
    
    choice = input("Pilihan (1/2/3): ").strip() or "3"
    
    if choice == "1":
        test_telegram_send()
    elif choice == "2":
        test_telegram_with_simple_image()
    else:
        # Quick generation test
        qris_gen = QRISGenerator()
        result = qris_gen.generate_qris(10000)
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
