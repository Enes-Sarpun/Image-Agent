"""
Image Agent: All settings and constants.
"""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent

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

Araştırma sonucu ile birlikte daha güvenilir bir karar ver. Aynı JSON formatında döndür.
"""

# === MULTI-PASS PROMPTS ===

MULTIPASS_AI_EVIDENCE_PROMPT = """Sen forensic görsel analiz uzmanısın. Görevin: bu görselin AI tarafından üretildiğine dair KANITLARI bulmak.

Bu görev için "real" demek YANLIŞ olabilir. SADECE AI kanıtı ara. Aramaya çalışıyorsun, savunucu olma.

ARANABILECEK AI İŞARETLERİ:
1. Anatomi tutarsızlıkları (asimetrik göz/kulak, garip parmak, eksik/fazla detay)
2. Aşırı pürüzsüz/uniform dokular (kürk, deri, kumaş "boyanmış" gibi)
3. Tekrarlayan pattern'ler (yapraklar, çakıllar aynı şekilde)
4. Fazla mükemmel kompozisyon (kuralına göre yerleşmiş, stüdyo havası)
5. Aşırı sinematik ışık (gerçek fotoğrafta nadir)
6. Yansıma/gölge tutarsızlıkları
7. Arkaplanda morphing veya garip detaylar
8. Aşırı keskin detay (gerçek lens'in olamayacağı keskinlikte)
9. Renk paleti "fazla harmonik" (gerçek dünyada doğal değil)
10. Watermark, logo, sembol

KURALLAR:
- Sadece AI olabileceğini gösteren GÖZLEMLER yaz
- Genel ifadeler yerine SOMUT detaylar ver
- "Hiç AI işareti yok" diyebilirsin ama önce gerçekten ara
- Forensic context varsa onu da değerlendir

ÇIKTI (SADECE JSON):
{
  "evidence": [
    "Spesifik gözlem 1",
    "Spesifik gözlem 2",
    "Spesifik gözlem 3"
  ],
  "strength": 0-10 arası sayı (kanıtların gücü, 0=yok, 10=kesin AI)
}

Kötü örnek: "Görsel doğal görünmüyor"
İyi örnek: "Kaplanın sol bacağındaki çizgi deseni, sağ bacağındaki düzenle simetrik değil ve geçiş bölgesinde 'morphing' var"
"""

MULTIPASS_REAL_EVIDENCE_PROMPT = """Sen forensic görsel analiz uzmanısın. Görevin: bu görselin GERÇEK BİR FOTOĞRAF olduğuna dair KANITLARI bulmak.

Bu görev için "ai" demek YANLIŞ olabilir. SADECE gerçek fotoğraf kanıtı ara.

ARANABILECEK GERÇEK FOTOĞRAF İŞARETLERİ:
1. Doğal kusurlar (motion blur, focus kayması, kompozisyon eksikleri)
2. Optik tutarsızlıklar (lens distortion, chromatic aberration)
3. Doğal asimetri (kürk farklı yönlerde, yapraklar farklı boyutlarda)
4. Mikro detaylar (deri gözenekleri, çatlak, leke, toz)
5. Doğal ışıklandırma (gün ışığı, gölgeler tutarlı)
6. Gerçek bokeh (optik olarak doğru arkaplan bulanıklığı)
7. Atmosfer detayları (sis, toz, hafif hareket bulanıklığı)
8. Doğal kompozisyon (kuralı bozan, "yakalanmış an" hissi)
9. EXIF benzeri kamera artifact'ları
10. Yansımalarda doğru fizik

KURALLAR:
- Sadece gerçek olabileceğini gösteren GÖZLEMLER yaz
- "Mükemmel görünüm" gerçek kanıtı DEĞİL — modern AI da mükemmel görünür
- "Doğal kompozisyon" demek için somut detay göster
- Forensic context varsa onu da değerlendir

ÇIKTI (SADECE JSON):
{
  "evidence": [
    "Spesifik gözlem 1",
    "Spesifik gözlem 2",
    "Spesifik gözlem 3"
  ],
  "strength": 0-10 arası sayı (kanıtların gücü, 0=yok, 10=kesin real)
}

Kötü örnek: "Görsel gerçekçi görünüyor"
İyi örnek: "Kaplanın boyun bölgesindeki tüylerde, gerçek vahşi yaşam fotoğraflarında görülen rastgele topaklanmalar var"
"""

MULTIPASS_SYNTHESIS_PROMPT = """Sen forensic görsel analiz uzmanısın. İki bağımsız analiz yapıldı:
- Pass 1: AI olma kanıtı arandı
- Pass 2: Gerçek olma kanıtı arandı

Şimdi sen bu iki listeyi karşılaştırıp final kararı vereceksin.

KARAR KURALLARI:

1. KANITLARIN GÜCÜ:
   - Strength skorlarına bak (0-10)
   - Hangi taraf daha güçlü kanıt üretti?
   - Sayıdan önce KALİTE önemli (1 güçlü kanıt > 5 zayıf kanıt)

2. ÖNYARGI KIRMA:
   - Modern AI çok iyidir, "gerçek görünüyor" tek başına yeterli değil
   - Ama "AI olabilir" diye yapay paranoya yapma
   - Kanıtlara dayalı düşün

3. CONFIDENCE KALİBRASYONU:
   - İki taraf da güçlüyse: 50-65 confidence (gerçekten belirsiz)
   - Bir taraf belirgin güçlüyse: 70-85
   - Watermark varsa: 95+
   - "Hissim öyle ama somut delil yok": 55-70

4. WATERMARK YOKSA 95+ CONFIDENCE VERME
   Modern AI watermark'sız üretebilir. %100 emin olamazsın.

ÇIKTI FORMATI (SADECE JSON):
{
  "verdict": "ai" veya "real",
  "confidence": 0-100,
  "reasoning": "3-5 cümle açıklama. Hangi kanıtların belirleyici olduğunu söyle.",
  "key_indicators": ["kararı destekleyen 3-5 spesifik gözlem"],
  "evidence_summary": {
    "ai_strength": Pass 1'in strength değeri,
    "real_strength": Pass 2'nin strength değeri,
    "decisive_factor": "Kararı belirleyen ana faktör"
  }
}
"""

