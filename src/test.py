"""
Forensic analyzer'ı test et.
"""

import sys
from pathlib import Path

from tools.forensic_analyzer import ForensicAnalyzer


def main():
    if len(sys.argv) < 2:
        print("Kullanım: python src/test_forensic.py <image_path>")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    if not image_path.exists():
        print(f"Görsel bulunamadı: {image_path}")
        sys.exit(1)

    output_dir = Path(__file__).parent.parent / "forensic_output"
    output_dir.mkdir(exist_ok=True)

    print(f"\nForensic analiz başlatılıyor: {image_path.name}")
    print("=" * 60)

    analyzer = ForensicAnalyzer()
    result = analyzer.analyze_all(image_path)

    # Görselleri kaydet
    base_name = image_path.stem
    result["ela_image"].save(output_dir / f"{base_name}_ela.png")
    result["fft_image"].save(output_dir / f"{base_name}_fft.png")
    result["edge_image"].save(output_dir / f"{base_name}_edges.png")

    # Metrikleri yazdır
    print("\n📊 Metrics:")
    for key, value in result["metrics"].items():
        print(f"  {key:25s}: {value:.4f}")

    # AI likelihood skoru
    ai_info = result["ai_likelihood"]
    print(f"\n🎯 AI Likelihood Score: {ai_info['ai_score']}/{ai_info['max_score']}")
    print(f"   Yorum: {ai_info['interpretation']}")
    
    if ai_info["signals"]:
        print("\n🚨 Tespit Edilen Sinyaller:")
        for signal in ai_info["signals"]:
            print(f"   • {signal}")
    else:
        print("\n   ℹ️  Belirgin AI sinyali bulunamadı")

    print(f"\n💾 Görseller kaydedildi: {output_dir}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

    