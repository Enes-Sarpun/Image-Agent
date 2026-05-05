# Image Agent

Gemini API kullanarak görsellerin AI tarafından mı üretildiğini yoksa gerçek fotoğraf mı olduğunu tespit eden akıllı agent. Forensic edge analysis ve LLM vision'ı birleştirerek karar verir.

## Özellikler

- 🔍 Multi-stage analysis pipeline
- 📊 SQLite cache 
- 🎯 Forensic edge pattern detection
- 🤖 Gemini Vision API entegrasyonu
- 🔎 Web search fallback 

## Kurulum

\`\`\`bash
python -m venv venv
venv\Scripts\activate    # Windows
pip install -r requirements.txt
\`\`\`

`.env` dosyası oluştur:
\`\`\`
GEMINI_API_KEY=your_key_here
\`\`\`

## Kullanım

\`\`\`bash
python src/main.py path/to/image.jpg
\`\`\`

## Mimari

1. Cache check (SQLite)
2. EXIF + Watermark hızlı kontroller
3. Forensic edge analysis
4. LLM Vision (forensic context ile)
5. Web search fallback

