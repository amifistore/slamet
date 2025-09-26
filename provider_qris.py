import requests
import base64
import re
from typing import Dict, Optional, Union, Any
import io
import tempfile
import os

class QRISGenerator:
    """
    QRIS Generator untuk handle pembuatan QRIS dinamis/statik.
    Bisa menghasilkan base64, BytesIO (untuk upload Telegram), atau file PNG sementara.
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
        """Membersihkan dan memperbaiki base64 (whitespace, padding, karakter non-base64)."""
        if not base64_string:
            return ""
        cleaned = re.sub(r'[^A-Za-z0-9+/]', '', base64_string)
        padding_needed = len(cleaned) % 4
        if padding_needed:
            cleaned += '=' * (4 - padding_needed)
        return cleaned

    def generate_qris(
        self,
        nominal: Union[int, str],
        qris_statis: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate QRIS dinamis dengan nominal tertentu.
        """
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

    def get_qris_bytesio(self, nominal: Union[int, str], qris_statis: Optional[str] = None) -> Optional[io.BytesIO]:
        """
        Generate QRIS dan return BytesIO PNG (siap upload Telegram).
        Return None jika gagal.
        """
        result = self.generate_qris(nominal, qris_statis)
        if result["status"] != "success":
            print(f"[QRIS] Gagal generate: {result['message']}")
            return None
        qris_base64 = result["qris_base64"]
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

    def generate_qris_image_file(self, nominal: Union[int, str], qris_statis: Optional[str] = None) -> Optional[str]:
        """
        Generate QRIS dan simpan ke file temporary (PNG), return path file.
        Return None jika gagal.
        """
        bio = self.get_qris_bytesio(nominal, qris_statis)
        if not bio:
            return None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_path = temp_file.name
                temp_file.write(bio.read())
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

# Fungsi global agar bisa di-import langsung dari file lain!
def generate_qris(nominal: Union[int, str], qris_statis: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate QRIS dinamis (return dict base64, nominal, dsb).
    """
    return QRISGenerator().generate_qris(nominal, qris_statis)

def get_qris_bytesio(nominal: Union[int, str], qris_statis: Optional[str] = None) -> Optional[io.BytesIO]:
    """
    Generate QRIS dan return BytesIO PNG (siap upload Telegram).
    """
    return QRISGenerator().get_qris_bytesio(nominal, qris_statis)

def generate_qris_image_file(nominal: Union[int, str], qris_statis: Optional[str] = None) -> Optional[str]:
    """
    Generate QRIS dan simpan ke file temporary (PNG), return path file.
    """
    return QRISGenerator().generate_qris_image_file(nominal, qris_statis)
