"""
EXIF Reader: Görsel metadata'sını okur.
Gerçek fotoğraflar genelde kamera bilgisi içerir.
"""

from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS


def read_exif(image_path: Path) -> dict:
    """
    Görselin EXIF metadata'sını oku.
    
    Returns:
        {
            "has_exif": bool,
            "has_camera_info": bool,
            "camera_make": str veya None,
            "camera_model": str veya None,
            "software": str veya None,  # AI işlemi göstergesi olabilir
            "raw_data": dict
        }
    """
    result = {
        "has_exif": False,
        "has_camera_info": False,
        "camera_make": None,
        "camera_model": None,
        "software": None,
        "raw_data": {}
    }

    try:
        image = Image.open(image_path)
        exif_data = image._getexif()

        if not exif_data:
            return result

        result["has_exif"] = True
        
        # Tag ID'lerini insan okuyabilir isimlere çevir
        readable = {TAGS.get(tag_id, tag_id): value for tag_id, value in exif_data.items()}
        result["raw_data"] = {k: str(v)[:200] for k, v in readable.items()}  # Uzun değerleri kırp

        # Önemli alanları çıkar
        result["camera_make"] = readable.get("Make")
        result["camera_model"] = readable.get("Model")
        result["software"] = readable.get("Software")

        if result["camera_make"] or result["camera_model"]:
            result["has_camera_info"] = True

    except Exception:
        # EXIF okunamazsa (bozuk dosya, format desteklemiyor) sessizce geç
        pass

    return result


def is_likely_real_camera(exif_result: dict) -> bool:
    """EXIF'e göre gerçek bir kameradan gelmiş gibi görünüyor mu?"""
    if not exif_result["has_camera_info"]:
        return False
    
    # Bilinen kamera markaları
    known_makes = {"canon", "nikon", "sony", "fujifilm", "panasonic",
                   "olympus", "leica", "apple", "samsung", "google", "huawei"}
    
    make = (exif_result.get("camera_make") or "").lower()
    return any(brand in make for brand in known_makes)


