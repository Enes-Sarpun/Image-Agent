"""
Image Agent: CLI giriş noktası.

Kullanım:
    python src/main.py <image_path>
    python src/main.py <image_path> --no-cache
"""

import sys
from pathlib import Path

from agent import ImageAgent
from result import AnalysisResult


def print_banner():
    print("\n" + "=" * 60)
    print("  🔍  IMAGE AGENT — Akıllı Görsel Analizi")
    print("=" * 60)


def print_result(result: AnalysisResult, image_name: str):
    print("\n" + "─" * 60)
    print(f"  📁 Görsel: {image_name}")
    print("─" * 60)

    icon = "🤖" if result.is_ai() else "📸"
    label = "AI ÜRETİMİ" if result.is_ai() else "GERÇEK FOTOĞRAF"

    print(f"\n  {icon}  Tahmin: {label}")
    print(f"  📊 Güven: %{result.confidence:.1f}")

    # Source badge
    source_labels = {
        "cache": "💾 Önbellekten",
        "watermark": "🏷️  Watermark Tespiti",
        "llm": "🧠 LLM Analizi",
        "llm_search": "🔎 LLM + Web Search",
    }
    source_label = source_labels.get(result.source, result.source)
    print(f"  🔧 Karar: {source_label}")
    print(f"  ⚡ Süre: {result.elapsed_ms:.0f}ms")

    if result.is_high_confidence(75):
        confidence_label = "✅ Yüksek güven"
    elif result.confidence >= 60:
        confidence_label = "⚠️  Orta güven"
    else:
        confidence_label = "❓ Düşük güven"
    print(f"  {confidence_label}")

    if result.reasoning:
        print(f"\n  💭 Gerekçe:")
        print(f"     {result.reasoning}")

    if result.key_indicators:
        print(f"\n  🔍 İpuçları:")
        for indicator in result.key_indicators:
            print(f"     • {indicator}")

    print("\n" + "─" * 60 + "\n")


def main():
    print_banner()

    if len(sys.argv) < 2:
        print("\n  Kullanım: python src/main.py <image_path> [--no-cache]\n")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    use_cache = "--no-cache" not in sys.argv

    if not image_path.exists():
        print(f"\n  ❌ Hata: Görsel bulunamadı: {image_path}\n")
        sys.exit(1)

    print(f"\n  🔄 Analiz ediliyor: {image_path.name}")
    if not use_cache:
        print(f"  ⚙️  Cache devre dışı")
    print()

    try:
        agent = ImageAgent()
        result = agent.analyze(image_path, use_cache=use_cache)
        print_result(result, image_path.name)
    except Exception as e:
        print(f"\n  ❌ Hata: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()