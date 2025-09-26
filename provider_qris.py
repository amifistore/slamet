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
        self.qris_statis_default = qris_statis or "00020101021126610014COM.GO-JEK.WWW01189360091434506469550210G4506469550303UMI51440014ID.CO.QRIS.WWW0215ID10243341364120303UMI5204569753033605802ID5923Amifi Store, Kmb, TLGSR6009BONDOWOSO61056827262070703A01630431E8"
    
    def _clean_base64(self, base64_string: str) -> str:
        """Bersihkan dan perbaiki base64 string"""
        if not base64_string:
            return ""
        
        # Hapus whitespace dan karakter non-base64
        cleaned = re.sub(r'[^A-Za-z0-9+/]', '', base64_string)
        
        # Pastikan panjang adalah kelipatan 4
        padding_needed = len(cleaned) % 4
        if padding_needed:
            cleaned += '=' * (4 - padding_needed)
        
        return cleaned
    
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
            
            response = requests.post(
                self.api_url, 
                json=payload, 
                headers=headers, 
                timeout=self.timeout
            )
            print(f"[QRIS] Response status: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            print(f"[QRIS] API Response status: {data.get('status')}")
            
            if isinstance(data, dict) and data.get("status") == "success" and "qris_base64" in data:
                # Clean the base64 data
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
        """
        Generate QRIS dan simpan ke file temporary, return path file
        """
        result = self.generate_qris(nominal, qris_statis)
        
        if result["status"] != "success":
            print(f"[QRIS] Gagal generate: {result['message']}")
            return None
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_path = temp_file.name
            
            # Decode base64 dan save ke file
            qris_base64 = result["qris_base64"]
            
            # Clean base64 lagi untuk memastikan
            cleaned_base64 = self._clean_base64(qris_base64)
            if not cleaned_base64:
                print("[QRIS] Invalid base64 after cleaning")
                return None
            
            try:
                qris_bytes = base64.b64decode(cleaned_base64, validate=True)
            except base64.binascii.Error as e:
                print(f"[QRIS] Base64 decoding error: {e}")
                # Coba decode tanpa validate
                try:
                    qris_bytes = base64.b64decode(cleaned_base64, validate=False)
                except:
                    return None
            
            with open(temp_path, "wb") as f:
                f.write(qris_bytes)
            
            # Verify file was created correctly
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                print(f"[QRIS] File created successfully: {temp_path} ({len(qris_bytes)} bytes)")
                return temp_path
            else:
                print("[QRIS] File creation failed")
                return None
            
        except Exception as e:
            print(f"[QRIS] Error create temp file: {e}")
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
    
    def send_photo_simple(self, chat_id: str, photo_path: str, caption: str = "") -> Dict[str, Any]:
        """
        Kirim photo ke Telegram dengan approach yang lebih careful
        """
        try:
            # Verify file exists and is valid
            if not os.path.exists(photo_path):
                return {"ok": False, "description": "File tidak ditemukan"}
            
            file_size = os.path.getsize(photo_path)
            if file_size == 0:
                return {"ok": False, "description": "File kosong"}
            
            print(f"[Telegram] Sending photo: {photo_path} ({file_size} bytes)")
            
            with open(photo_path, 'rb') as photo:
                # Read the file content
                file_content = photo.read()
                
                # Create a BytesIO object to ensure proper file handling
                file_stream = io.BytesIO(file_content)
                file_stream.name = "qris.png"
                
                files = {'photo': ('qris.png', file_stream, 'image/png')}
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
                
                print(f"[Telegram] Response status: {response.status_code}")
                response_data = response.json()
                print(f"[Telegram] API Response: {response_data}")
                
                return response_data
                
        except Exception as e:
            print(f"[Telegram] Error: {e}")
            return {"ok": False, "description": str(e)}
    
    def send_document_as_fallback(self, chat_id: str, file_path: str, caption: str = "") -> Dict[str, Any]:
        """
        Fallback: kirim sebagai document jika sebagai photo gagal
        """
        try:
            with open(file_path, 'rb') as doc:
                files = {'document': doc}
                data = {
                    'chat_id': chat_id, 
                    'caption': caption,
                    'parse_mode': 'HTML'
                }
                
                response = requests.post(
                    f"{self.base_url}/sendDocument",
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
        Kirim QRIS ke Telegram dengan multiple fallback strategies
        """
        print(f"[QRIS] Starting process for nominal: Rp {nominal:,}")
        
        # Verify bot token first
        if not self.verify_bot_token():
            return {
                "status": "error", 
                "message": "Bot token tidak valid"
            }
        
        # Generate QRIS dan simpan ke file
        temp_file_path = self.qris_generator.generate_qris_image_file(nominal, qris_statis)
        
        if not temp_file_path or not os.path.exists(temp_file_path):
            return {
                "status": "error", 
                "message": "Gagal generate QRIS image"
            }
        
        # Verify the generated file
        file_size = os.path.getsize(temp_file_path)
        if file_size == 0:
            os.unlink(temp_file_path)
            return {
                "status": "error", 
                "message": "File QRIS kosong"
            }
        
        # Format caption
        formatted_nominal = f"Rp {int(nominal):,}".replace(",", ".")
        final_caption = caption or f"💳 QRIS Payment\n💵 Nominal: {formatted_nominal}\n⏰ Berlaku 24 jam"
        
        try:
            print(f"[Telegram] Sending to chat_id: {chat_id}")
            
            # Strategy 1: Kirim sebagai photo
            response = self.send_photo_simple(chat_id, temp_file_path, final_caption)
            
            if response.get("ok"):
                # Clean up temporary file
                os.unlink(temp_file_path)
                return {
                    "status": "success",
                    "message": "QRIS berhasil dikirim ke Telegram",
                    "response": response
                }
            
            # Strategy 2: Kirim sebagai document (fallback)
            print("[Telegram] Photo failed, trying as document...")
            response = self.send_document_as_fallback(chat_id, temp_file_path, final_caption)
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            if response.get("ok"):
                return {
                    "status": "success", 
                    "message": "QRIS berhasil dikirim sebagai document",
                    "response": response
                }
            else:
                error_msg = response.get("description", "Unknown error")
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
    generator = QRISGenerator()
    return generator.qris_statis_default

def generate_qris(nominal: Union[int, str], qris_statis: Optional[str] = None) -> Dict[str, Any]:
    generator = QRISGenerator()
    return generator.generate_qris(nominal, qris_statis)

def qris_base64_to_bytesio(qris_base64: str) -> Optional[io.BytesIO]:
    if not qris_base64:
        return None
        
    try:
        # Clean base64 first
        cleaned = re.sub(r'[^A-Za-z0-9+/]', '', qris_base64)
        padding_needed = len(cleaned) % 4
        if padding_needed:
            cleaned += '=' * (4 - padding_needed)
        
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
# FUNGSI TEST DAN DEBUG
# =============================================================================

def debug_base64_issue():
    """Debug khusus base64 padding issue"""
    print("🔧 DEBUG BASE64 PADDING ISSUE")
    print("=" * 50)
    
    # Test base64 cleaning function
    test_strings = [
        "aGVsbG8=",  # valid
        "aGVsbG8",   # missing padding
        "aGVsbG8===", # extra padding
        "aG Vsb G8=", # with spaces
    ]
    
    qris_gen = QRISGenerator()
    
    for test in test_strings:
        cleaned = qris_gen._clean_base64(test)
        print(f"Original: {test}")
        print(f"Cleaned:  {cleaned}")
        print(f"Length: {len(test)} -> {len(cleaned)}")
        print("-" * 30)

def test_step_by_step():
    """Test step by step process"""
    print("🔍 STEP BY STEP TEST")
    print("=" * 50)
    
    qris_gen = QRISGenerator()
    nominal = 10000
    
    # Step 1: Generate QRIS
    print("1. Generating QRIS...")
    result = qris_gen.generate_qris(nominal)
    
    if result["status"] != "success":
        print(f"❌ Failed: {result['message']}")
        return False
    
    print("✅ QRIS generated successfully")
    
    # Step 2: Check base64
    base64_data = result["qris_base64"]
    print(f"2. Base64 data length: {len(base64_data)}")
    print(f"   First 50 chars: {base64_data[:50]}...")
    
    # Step 3: Create file
    print("3. Creating file...")
    file_path = qris_gen.generate_qris_image_file(nominal)
    
    if file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        print(f"✅ File created: {file_path} ({file_size} bytes)")
        
        # Cleanup
        os.unlink(file_path)
        return True
    else:
        print("❌ File creation failed")
        return False

if __name__ == "__main__":
    print("🎯 QRIS FIXED VERSION - Base64 Padding Fix")
    print("=" * 60)
    
    print("Pilih test:")
    print("1. Debug Base64 Issue")
    print("2. Step by Step Test")
    print("3. Quick Generation Test")
    
    choice = input("Pilihan (1/2/3): ").strip()
    
    if choice == "1":
        debug_base64_issue()
    elif choice == "2":
        test_step_by_step()
    else:
        # Quick test
        qris_gen = QRISGenerator()
        result = qris_gen.generate_qris(10000)
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
        
        if result["status"] == "success":
            file_path = qris_gen.generate_qris_image_file(10000)
            if file_path:
                print(f"✅ File: {file_path}")
                os.unlink(file_path)
