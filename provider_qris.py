import requests
import json
import os
import base64
import io
from typing import Dict, Optional, Union, Any
from urllib.parse import urljoin

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

class QRISGenerator:
    """QRIS Generator class untuk handle pembuatan QRIS dinamis"""
    
    def __init__(self, api_url: str = "https://qrisku.my.id/api", timeout: int = 30):
        self.api_url = api_url
        self.timeout = timeout
        self.qris_statis_default = self._get_qris_statis()
    
    def _get_qris_statis(self) -> str:
        """
        Ambil nilai QRIS statis dari config.json pada key 'QRIS_STATIS'.
        
        Returns:
            str: QRIS statis value atau empty string jika error
        """
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                qris_statis = config.get("QRIS_STATIS", "").strip()
                if not qris_statis:
                    print("[QRIS] Warning: QRIS_STATIS kosong atau tidak ditemukan di config.json")
                return qris_statis
        except FileNotFoundError:
            print(f"[QRIS] Error: File config.json tidak ditemukan di {CONFIG_PATH}")
            return ""
        except json.JSONDecodeError as e:
            print(f"[QRIS] Error: Format config.json invalid - {e}")
            return ""
        except Exception as e:
            print(f"[QRIS] Gagal baca QRIS_STATIS dari config: {e}")
            return ""
    
    def generate_qris(self, nominal: Union[int, str], qris_statis: Optional[str] = None) -> Dict[str, Any]:
        """
        Request ke API QRIS Dinamis Generator untuk membuat QRIS (format base64).
        
        Args:
            nominal (int|str): Nominal dalam rupiah (minimal biasanya 1000)
            qris_statis (str|None): QRIS statis merchant, default dari config
            
        Returns:
            dict: {
                "status": "success"|"error",
                "message": str,
                "qris_base64": str (jika sukses),
                "nominal": nominal (jika sukses)
            }
        """
        # Validasi input
        if not qris_statis:
            qris_statis = self.qris_statis_default
        
        if not qris_statis:
            return {
                "status": "error", 
                "message": "QRIS statis tidak tersedia di config.json"
            }
        
        try:
            nominal_str = str(nominal).strip()
            if not nominal_str.isdigit():
                return {
                    "status": "error", 
                    "message": "Nominal harus berupa angka"
                }
            
            # Validasi nominal minimal
            nominal_int = int(nominal_str)
            if nominal_int < 1000:
                return {
                    "status": "error",
                    "message": "Nominal minimal Rp 1.000"
                }
                
        except (ValueError, TypeError) as e:
            return {
                "status": "error", 
                "message": f"Format nominal invalid: {e}"
            }
        
        # Prepare payload
        payload = {
            "amount": nominal_str,
            "qris_statis": qris_statis.strip()
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "QRIS-Generator/1.0"
        }
        
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
                return {
                    "status": "error", 
                    "message": "Invalid response format from QRIS API"
                }
            
            if data.get("status") == "success" and "qris_base64" in data:
                return {
                    "status": "success",
                    "message": data.get("message", "QRIS berhasil digenerate"),
                    "qris_base64": data["qris_base64"],
                    "nominal": nominal_int
                }
            
            # Handle berbagai kemungkinan error response
            error_message = data.get("message", "Unknown error from QRIS API")
            return {
                "status": "error",
                "message": f"API Error: {error_message}"
            }
            
        except requests.exceptions.Timeout:
            return {
                "status": "error", 
                "message": f"Timeout ({self.timeout}s) saat menghubungi server QRIS"
            }
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "Unknown"
            return {
                "status": "error", 
                "message": f"HTTP Error {status_code}: {str(e)}"
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error", 
                "message": f"Network error: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Unexpected error: {str(e)}"
            }
    
    @staticmethod
    def qris_base64_to_bytesio(qris_base64: str) -> Optional[io.BytesIO]:
        """
        Decode base64 QRIS menjadi BytesIO agar bisa dikirim ke Telegram.
        Memperbaiki padding jika perlu.
        
        Args:
            qris_base64 (str): String base64 dari gambar QRIS
            
        Returns:
            BytesIO or None: Object BytesIO yang berisi gambar QRIS
        """
        if not qris_base64 or not isinstance(qris_base64, str):
            return None
            
        try:
            # Clean the base64 string
            cleaned_base64 = qris_base64.strip().replace('\n', '').replace('\r', '')
            
            # Add padding if necessary
            missing_padding = len(cleaned_base64) % 4
            if missing_padding:
                cleaned_base64 += '=' * (4 - missing_padding)
            
            # Decode base64
            qris_bytes = base64.b64decode(cleaned_base64)
            
            # Create BytesIO object
            bio = io.BytesIO(qris_bytes)
            bio.name = "qris.png"
            bio.seek(0)
            
            return bio
            
        except base64.binascii.Error as e:
            print(f"[QRIS] Error decoding base64: {e}")
            return None
        except Exception as e:
            print(f"[QRIS] Error creating BytesIO: {e}")
            return None
    
    def validate_qris_statis(self, qris_statis: str) -> bool:
        """
        Validasi format QRIS statis (basic validation).
        
        Args:
            qris_statis (str): QRIS statis string untuk divalidasi
            
        Returns:
            bool: True jika format terlihat valid
        """
        if not qris_statis or not isinstance(qris_statis, str):
            return False
        
        qris_statis = qris_statis.strip()
        
        # Basic validation - QRIS biasanya mulai dengan kode tertentu
        if len(qris_statis) < 10:  # Panjang minimum
            return False
            
        # Bisa ditambahkan validasi lebih spesifik sesuai format QRIS
        return True

# Fungsi legacy untuk backward compatibility
def get_qris_statis() -> str:
    """Legacy function - gunakan QRISGenerator instead"""
    generator = QRISGenerator()
    return generator.qris_statis_default

QRIS_STATIS_DEFAULT = get_qris_statis()

def generate_qris(nominal: Union[int, str], qris_statis: Optional[str] = None) -> Dict[str, Any]:
    """Legacy function - gunakan QRISGenerator instead"""
    generator = QRISGenerator()
    return generator.generate_qris(nominal, qris_statis)

def qris_base64_to_bytesio(qris_base64: str) -> Optional[io.BytesIO]:
    """Legacy function - gunakan QRISGenerator instead"""
    return QRISGenerator.qris_base64_to_bytesio(qris_base64)

# Contoh penggunaan
if __name__ == "__main__":
    # Penggunaan class-based
    qris_gen = QRISGenerator()
    
    # Generate QRIS
    result = qris_gen.generate_qris(10000)
    
    if result["status"] == "success":
        print("QRIS berhasil dibuat!")
        
        # Convert to BytesIO untuk Telegram
        qris_image = qris_gen.qris_base64_to_bytesio(result["qris_base64"])
        if qris_image:
            print("QRIS siap dikirim ke Telegram")
        else:
            print("Gagal convert QRIS ke image")
    else:
        print(f"Error: {result['message']}")
