"""
Image Agent: All settings and constants.
"""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "cache.db"

# Gemini model settings
MODEL_NAME = "gemini-2.5-flash"
MAX_TOKENS = 1024
TEMPERATURE = 0.2

# Confidence thresholds
WATERMARK_CONFIDENCE_THRESHOLD = 95.0
LLM_CONFIDENCE_THRESHOLD = 75.0

# Supported image formats
SUPPORTED_FORMATS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# LLM Prompts
SYSTEM_PROMPT = """Sen, görsellerin AI tarafından mı üretildiğini yoksa gerçek bir fotoğraf mı olduğunu tespit eden uzman bir görsel analiz asistanısın.

Görevin:
- Verilen görseli dikkatle incele
- AI üretimi olduğuna dair ipuçları ara: anatomi tutarsızlıkları, ışık/gölge anomalileri, aşırı pürüzsüz dokular, watermark veya AI imzaları, kompozisyon "fazla mükemmelliği"
- Gerçek fotoğraf işaretlerini ara: doğal kusurlar, optik tutarsızlıklar, gerçek kamera artifact'ları, doğal kompozisyon
- Sonucu yapılandırılmış JSON formatında döndür

Çıktı formatı (SADECE JSON, başka metin yok):
{
  "verdict": "ai" veya "real",
  "confidence": 0-100 arası bir sayı,
  "reasoning": "2-3 cümlelik gerekçe",
  "key_indicators": ["ipucu1", "ipucu2", "ipucu3"]
}

Önemli kurallar:
- Sadece JSON döndür, başka açıklama yapma
- Kararsızsan confidence değerini 50-60 aralığında tut
- key_indicators somut detaylar olsun
- Gerekçeyi Türkçe yaz"""

USER_PROMPT = "Bu görseli analiz et ve AI üretimi mi yoksa gerçek fotoğraf mı olduğunu belirt."

SEARCH_PROMPT = """Bu görselin AI üretimi mi gerçek fotoğraf mı olduğundan emin değilim.
Web'de bu görsele benzer kaynaklar ara, AI generator'larından üretilip üretilmediğine dair ipuçları bul.
Reverse image search benzeri bir yaklaşımla, görselin orijinal kaynağını veya benzerlerini araştır.
Sonucu yine aynı JSON formatında döndür."""