"""
Watermark Detector: Görselde Gemini sparkle watermark'ı arar.
Gemini'nin sağ alt köşesine eklediği dört uçlu yıldız işareti.
"""

from pathlib import Path
import numpy as np
from PIL import Image


def detect_gemini_sparkle(image_path: Path) -> dict:
    """
    Gemini'nin dört uçlu yıldız watermark'ını ara.
    Genelde sağ alt köşede beyaz/açık renkli olur.
    
    Bu basit bir heuristic — sağ alt köşede yüksek parlaklık + 
    karakteristik şekil kombinasyonu arar.
    
    Returns:
        {
            "found": bool,
            "confidence": float (0-100),
            "location": str,
            "details": str
        }
    """
    result = {
        "found": False,
        "confidence": 0.0,
        "location": None,
        "details": ""
    }

    try:
        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        
        # Sağ alt köşeyi al (görselin %15'lik bir kısmı)
        crop_size = int(min(width, height) * 0.15)
        right_bottom = image.crop((
            width - crop_size,
            height - crop_size,
            width,
            height
        ))
        
        arr = np.array(right_bottom)
        
        # Watermark karakteristiği:
        # - Yüksek parlaklık (beyaz/açık)
        # - Küçük, yoğun bir bölge (yıldız şekli)
        # - Çevresinden belirgin şekilde ayrışır
        
        gray = arr.mean(axis=2)
        
        # Çok parlak pikselleri bul (>200/255)
        bright_mask = gray > 200
        bright_ratio = bright_mask.sum() / bright_mask.size
        
        # Watermark tipik olarak %0.5 - %5 arasında parlak piksel içerir
        if 0.005 < bright_ratio < 0.05:
            # Parlak piksellerin dağılımına bak (yoğunluk merkezde olmalı)
            bright_coords = np.argwhere(bright_mask)
            if len(bright_coords) > 10:
                std_y, std_x = bright_coords.std(axis=0)
                # Kompakt bir yapı varsa (dağınık değilse) watermark olabilir
                compactness = 1.0 / (1.0 + (std_x + std_y) / crop_size)
                
                if compactness > 0.5:
                    result["found"] = True
                    result["confidence"] = min(95.0, compactness * 100)
                    result["location"] = "bottom-right"
                    result["details"] = "Possible Gemini sparkle watermark detected"

    except Exception as e:
        result["details"] = f"Detection failed: {e}"

    return result