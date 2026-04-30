"""
Image Agent: CLI giriş noktası.

Kullanım:
    python src/main.py <image_path>

Örnek:
    python src/main.py test_image.jpg
"""

import sys
from pathlib import Path

from analyzer import ImageAnalyzer
from result import AnalysisResult


def print_banner():
    """Açılış banner'ı."""
    print("\n" + "=" * 60)
    print("  🔍  IMAGE AGENT — AI vs Real Görsel Analizi")
    print("=" * 60)


def print_result(result: AnalysisResult, image_name: str):
    """Sonucu güzel formatta yazdır."""
    print("\n" + "─" * 60)
    print(f"  📁 Görsel: {image_name}")
    print("─" * 60)

    icon = "🤖" if result.is_ai() else "📸"
    label = "AI ÜRETİMİ" if result.is_ai() else "GERÇEK FOTOĞRAF"

    print(f"\n  {icon}  Tahmin: {label}")
    print(f"  📊 Güven: %{result.confidence:.1f}")

    # Güven seviyesi göstergesi
    if result.is_high_confidence(75):
        confidence_label = "✅ Yüksek güven"
    elif result.confidence >= 60:
        confidence_label = "⚠️  Orta güven"
    else:
        confidence_label = "❓ Düşük güven"
    print(f"  {confidence_label}")

    print(f"\n  💭 Gerekçe:")
    print(f"     {result.reasoning}")

    if result.key_indicators:
        print(f"\n  🔍 Tespit Edilen İpuçları:")
        for indicator in result.key_indicators:
            print(f"     • {indicator}")

    print("\n" + "─" * 60 + "\n")


def main():
    print_banner()

    if len(sys.argv) < 2:
        print("\n  Kullanım: python src/main.py <image_path>")
        print("  Örnek:    python src/main.py test_image.jpg\n")
        sys.exit(1)

    image_path = Path(sys.argv[1])

    if not image_path.exists():
        print(f"\n  ❌ Hata: Görsel bulunamadı: {image_path}\n")
        sys.exit(1)

    print(f"\n  🔄 Analiz ediliyor: {image_path.name}")
    print(f"  ⏳ Lütfen bekleyin...")

    try:
        analyzer = ImageAnalyzer()
        result = analyzer.analyze(image_path)
        print_result(result, image_path.name)
    except FileNotFoundError as e:
        print(f"\n  ❌ Dosya hatası: {e}\n")
        sys.exit(1)
    except ValueError as e:
        print(f"\n  ❌ Değer hatası: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ❌ Beklenmeyen hata: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()