"""
Image Hasher: Görsel için perceptual hash üretir.
Cache anahtarı olarak kullanılır.
"""

from pathlib import Path
from PIL import Image
import imagehash


def compute_hash(image_path: Path) -> str:
    """
    Görselin perceptual hash'ini hesapla.
    Aynı görselin küçük varyasyonları (resize, JPEG yeniden sıkıştırma)
    aynı hash'i verir.
    """
    image = Image.open(image_path)
    # phash: perceptual hash - görsel içeriğe göre
    hash_value = imagehash.phash(image)
    return str(hash_value)