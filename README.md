# Image Agent

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-purple)](LICENSE)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-orange?logo=google)](https://ai.google.dev)
[![Open Source](https://img.shields.io/badge/Open%20Source-%E2%9D%A4-red)](https://github.com/Enes-Sarpun/Image-Agent)

Bir görselin **AI tarafından mı üretildiğini** yoksa **gerçek fotoğraf mı** olduğunu tespit eden akıllı Python agent'ı. Gemini Vision, forensic analiz ve multi-pass reasoning'i birleştirerek çok katmanlı bir karar mekanizması sunar.

---

## Neden Image Agent?

Midjourney, Stable Diffusion, Imagen ve Flux gibi modeller artık insan gözünü kolayca yanıltıyor. Image Agent bu soruna çok katmanlı, LLM destekli bir yanıt sunuyor: forensic tekniklerini (ELA, FFT, edge analizi) doğrudan Gemini Vision'a bağlayarak, modelin sayısal ipuçlarıyla desteklenen bir yargıya ulaşmasını sağlıyor.

---

## Özellikler

| Özellik | Açıklama |
|---|---|
| 🔍 7 Katmanlı Pipeline | Cache → EXIF/Watermark → Forensic → LLM → Multi-Pass → Search → Calibration |
| 🧠 Multi-Pass Reasoning | 3 aşamalı çapraz sorgulama: AI kanıtı → Gerçek kanıtı → Sentez |
| 🔬 Forensic Analiz | ELA, FFT frekans haritası, edge density — AI imzalarını sayısal olarak yakalar |
| ⚖️ Confidence Calibration | Ham LLM skoru 5 kuralla kalibre edilir; yanlış cevaplar düşük güvenle işaretlenir |
| 💾 SQLite Cache | Perceptual hash ile — aynı görsel ~100ms'de önbellekten döner |
| 🏷️ Watermark Tespiti | Gemini sparkle watermark'ı pixel analizi ile yakalar |
| 🌐 Web Arayüzü | Gradio tabanlı modern UI: `python app.py` |
| 📦 Batch İşleme | Klasör analizi, CSV + JSON çıktı: `--batch <folder>` |

---

## Mimari

```
Image input
  ↓
[1] Perceptual hash → Cache check         (~100ms, cache hit)
[2] EXIF + Watermark tespiti              (~300ms, watermark bulunursa erken dönüş)
[3] Forensic preprocessing (ELA+FFT+Edge) (~1-2s)
[4] LLM Vision — Gemini 2.5 Flash        (~5-10s)
[5] Düşük confidence → Multi-Pass (3x)   (~15-20s)
[6] Hâlâ düşük → Google Search fallback  (~30s)
[7] Confidence Calibration               (her path'te son adım)
  ↓
Cache'e yaz + return
```

### Proje Yapısı

```
Image Agent/
├── .env                         # GEMINI_API_KEY
├── requirements.txt
├── app.py                       # Gradio web arayüzü
├── landing/
│   └── index.html               # Statik landing page
├── data/
│   └── cache.db                 # SQLite cache
├── results/                     # Batch çıktıları (otomatik oluşur)
└── src/
    ├── config.py                # Ayarlar, prompt'lar, eşikler
    ├── result.py                # AnalysisResult dataclass
    ├── agent.py                 # Ana orkestratör
    ├── main.py                  # CLI giriş noktası
    ├── tools/
    │   ├── image_hasher.py
    │   ├── exif_reader.py
    │   ├── watermark_detector.py
    │   ├── forensic_analyzer.py
    │   ├── llm_vision.py
    │   ├── multi_pass_analyzer.py
    │   ├── confidence_calibrator.py
    │   └── llm_with_search.py
    └── cache/
        └── sqlite_cache.py
```

---

## Kurulum

### Gereksinimler
- Python 3.10+
- Gemini API anahtarı ([buradan ücretsiz al](https://aistudio.google.com/app/apikey))

### Adımlar

```bash
# 1. Repoyu klonla
git clone https://github.com/Enes-Sarpun/Image-Agent.git
cd Image-Agent

# 2. Sanal ortam oluştur ve etkinleştir
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Gradio arayüzü için (isteğe bağlı)
pip install gradio tqdm
```

`.env` dosyası oluştur (proje kökünde):
```
GEMINI_API_KEY=your_api_key_here
```

---

## Kullanım

### Web Arayüzü (önerilen)

```bash
python app.py
```

Tarayıcıda `http://127.0.0.1:7860` açılır. Görseli sürükle-bırak ile yükle, sonucu anında gör.

### CLI — Tek Görsel

```bash
python src/main.py path/to/image.jpg

# Cache'i devre dışı bırak (zorla yeniden analiz)
python src/main.py path/to/image.jpg --no-cache
```

### CLI — Batch (Klasör)

```bash
python src/main.py --batch path/to/folder/

# Cache'siz batch
python src/main.py --batch path/to/folder/ --no-cache
```

Çıktı: `results/batch_YYYYMMDD_HHMMSS.csv` ve `.json`

---

## Örnek CLI Çıktısı

```
============================================================
  🔍  IMAGE AGENT — Akıllı Görsel Analizi
============================================================

  🔄 Analiz ediliyor: test_image.jpg

  [1/6] Computing image hash...
  [2/6] EXIF + watermark check...
  [3/6] Forensic edge analysis...
      Forensic AI score: 72/100
  [4/6] LLM vision analysis...
      Calibration: 95.0 → 80.0 (-15)

────────────────────────────────────────────────────────────
  📁 Görsel: test_image.jpg
────────────────────────────────────────────────────────────

  🤖  Tahmin: AI ÜRETİMİ
  📊 Güven: %80.0
  🔧 Karar: 🧠 LLM + Forensic
  ⚡ Süre: 8340ms
  ✅ Yüksek güven

  💭 Gerekçe:
     Görsel uniform tekstür ve tekrarlanan pattern imzaları içeriyor...

  🔍 İpuçları:
     • EXIF: no metadata (common in AI images)
     • Forensic: high uniformity detected
     • Calibration: raw=95.0% → calibrated=80.0% (delta=-15)

────────────────────────────────────────────────────────────
```

---

## Sınırlamalar

- Yeni nesil watermark'sız modeller (Imagen 3, Flux, Midjourney v6) tespit zorlaşabilir
- Sonuçlar %100 kesin değildir; karar destek aracı olarak kullanılmalıdır
- Gemini API ücretsiz tier: dakikada 10 istek, günde 250 istek

---

## Teknolojiler

- [Google Gemini 2.5 Flash](https://ai.google.dev) — LLM vision
- [OpenCV](https://opencv.org) — Görsel işleme
- [NumPy](https://numpy.org) + [SciPy](https://scipy.org) — Forensic hesaplamalar
- [Pillow](https://python-pillow.org) — Görsel yükleme
- [Gradio](https://gradio.app) — Web arayüzü
- [SQLite](https://sqlite.org) — Cache

---

## Geliştirici

**Enes Sarpün** — [GitHub](https://github.com/Enes-Sarpun) · [enessarpun63@gmail.com](mailto:enessarpun63@gmail.com)

---

## Lisans

[MIT](LICENSE)
