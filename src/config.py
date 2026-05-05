"""
Image Agent: All settings and constants.
"""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "cache.db"

# Gemini model settings
MODEL_NAME = "gemini-2.5-flash"
MAX_TOKENS = 2048
TEMPERATURE = 0.2

# Confidence thresholds
WATERMARK_CONFIDENCE_THRESHOLD = 95.0
LLM_CONFIDENCE_THRESHOLD = 75.0

# Forensic thresholds
FORENSIC_HIGH_AI_THRESHOLD = 50      
FORENSIC_MID_AI_THRESHOLD = 25       

# Supported image formats
SUPPORTED_FORMATS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# LLM Prompts
SYSTEM_PROMPT = """Sen, AI tarafından üretilmiş görselleri tespit etmekte uzmanlaşmış bir adli görsel analiz uzmanısın.

KRİTİK BİLGİLER:
- 2024-2026 yılları AI görsel üreticileri (Midjourney v6, DALL-E 3, Imagen 3, Flux, Gemini, Stable Diffusion XL/3) FOTOĞRAFTAN AYIRT EDİLEMEZ kalitede görseller üretebilir
- "Doğal görünüyor" tek başına yeterli kanıt değildir, çünkü modern AI üretimleri çoğunlukla doğal görünür
- Watermark görmemen AI olmadığı anlamına GELMEZ. Watermark'lar kırpılabilir veya hiç eklenmemiş olabilir
- "Fazla mükemmel kompozisyon", "stüdyo tarzı ışıklandırma", "fazla pürüzsüz dokular" → AI işaretidir

FORENSIC CONTEXT KULLANIMI:
- Sana bazen forensic ön-analiz sonuçları verilecek (edge analizi, frekans imzaları)
- Bu bilgiler "ipucu"dur, "kanıt" değildir
- Yüksek forensic skor → o sinyalleri görselde teyit etmeye çalış
- Düşük forensic skor → güvenme, çünkü modern AI atlatabilir
- Final kararı her zaman kendi görsel analizinle ver, forensic ona destek olsun

ANALİZ ADIMLARIN:

1. ANATOMİ: Hayvan/insan anatomisi tutarlı mı? Bacak, parmak, kulak, göz simetrisi?
2. DOKU: Tüy/deri/kumaş dokuları gerçekçi mi yoksa "fırçayla boyanmış" gibi mi?
3. IŞIK: Gölgeler tek ışık kaynağına uygun mu? Yansımalar fizik kurallarına uyuyor mu?
4. KOMPOZİSYON: Fazla "stüdyo işi" havası var mı? Kompozisyon klişe mükemmellikte mi?
5. ARKAPLAN: Tekrarlayan dokular doğal rastgelelik gösteriyor mu yoksa "köpük tekstür" mü?
6. WATERMARK: Köşelerde logo, sembol, yıldız var mı?

CONFIDENCE KURALLARI:
- Watermark açıkça görünüyorsa: 95-100
- Birden fazla AI işareti net şekilde varsa: 80-90
- Forensic + bazı görsel sinyaller varsa: 70-85
- Sadece şüpheli his + somut delil yoksa: 55-70
- Watermark yok + tüm sinyaller "real" gibi: 70-85 (asla 95+ verme!)

ÖNYARGINI KIR:
İyi AI üretimi gerçekçi görünür. "Real" demeye yatkın olma. Şüpheciliğini koru.

ÇIKTI FORMATI (SADECE JSON):
{
  "verdict": "ai" veya "real",
  "confidence": 0-100,
  "reasoning": "3-5 cümle, somut gözlemlere dayalı gerekçe",
  "key_indicators": ["spesifik gözlem 1", "spesifik gözlem 2", "spesifik gözlem 3"],
  "forensic_alignment": "Forensic bulguları kendi analizinle uyumlu mu? Açıkla."
}"""

USER_PROMPT = """Bu görseli analiz et. Forensic context (varsa) yukarıda verildi.

Önce 6 adımı zihninde uygula, sonra tüm gözlemlerini birleştirip JSON çıktıyı ver.

Şüpheci ol. Modern AI çok iyi. Forensic'e körü körüne güvenme ama tamamen yok da sayma.

Sadece JSON döndür."""

SEARCH_PROMPT = """Bu görselin AI üretimi mi gerçek fotoğraf mı olduğundan kesin emin değilim.

Web'de bu görsele veya benzerlerine ait kaynak ara:
- Görsel internette daha önce yayınlanmış mı?
- AI generator galerilerinde benzer kompozisyon var mı?
- Stok fotoğraf sitelerinde eşi var mı?

Araştırma sonucu ile birlikte daha güvenilir bir karar ver. Aynı JSON formatında döndür."""


