"""
Image Agent: CLI giriş noktası.

Kullanım:
    python src/main.py <image_path>
    python src/main.py <image_path> --no-cache
    python src/main.py --batch <folder>
    python src/main.py --batch <folder> --no-cache
"""

import sys
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from agent import ImageAgent
from result import AnalysisResult
from config import SUPPORTED_FORMATS


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

    source_labels = {
        "cache": "💾 Önbellekten",
        "watermark": "🏷️  Watermark Tespiti",
        "llm": "🧠 LLM Analizi",
        "llm+forensic": "🧠 LLM + Forensic",
        "multi_pass+forensic": "🔁 Multi-Pass + Forensic",
        "llm_search+forensic": "🔎 LLM + Web Search",
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


def run_batch(folder_path: Path, use_cache: bool):
    """Klasördeki tüm desteklenen görselleri analiz eder."""
    images = sorted([
        p for p in folder_path.iterdir()
        if p.is_file() and p.suffix.lower() in set(SUPPORTED_FORMATS.keys())
    ])

    if not images:
        print(f"\n  ❌ Hata: '{folder_path}' klasöründe desteklenen görsel bulunamadı.\n")
        print(f"     Desteklenen formatlar: {', '.join(set(SUPPORTED_FORMATS.keys()))}\n")
        sys.exit(1)

    print(f"\n  📂 Klasör: {folder_path}")
    print(f"  🖼️  Toplam: {len(images)} görsel")
    if not use_cache:
        print(f"  ⚙️  Cache devre dışı")
    print()

    # Çıktı klasörünü hazırla
    results_dir = Path(__file__).resolve().parent.parent / "results"
    results_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path  = results_dir / f"batch_{timestamp}.csv"
    json_path = results_dir / f"batch_{timestamp}.json"

    agent = ImageAgent()
    records = []
    errors  = []

    ai_count   = 0
    real_count = 0
    batch_start = time.perf_counter()

    try:
        from tqdm import tqdm
        iterator = tqdm(images, desc="  Analiz", unit="görsel", ncols=60)
    except ImportError:
        iterator = images
        print("  (tqdm bulunamadı — ilerleme çubuğu devre dışı)\n")

    for img_path in iterator:
        try:
            result = agent.analyze(img_path, use_cache=use_cache)

            if result.is_ai():
                ai_count += 1
            else:
                real_count += 1

            records.append({
                "file":       img_path.name,
                "verdict":    result.verdict,
                "confidence": round(result.confidence, 2),
                "source":     result.source,
                "elapsed_ms": round(result.elapsed_ms, 0),
                "reasoning":  result.reasoning,
                "indicators": result.key_indicators,
                "timestamp":  result.timestamp,
            })

        except Exception as e:
            errors.append({"file": img_path.name, "error": str(e)})
            if hasattr(iterator, "write"):
                iterator.write(f"  ⚠ Atlandı: {img_path.name} — {e}")
            else:
                print(f"  ⚠ Atlandı: {img_path.name} — {e}")

    total_ms = (time.perf_counter() - batch_start) * 1000
    avg_conf = (
        sum(r["confidence"] for r in records) / len(records)
        if records else 0
    )

    # ── CSV çıktısı ────────────────────────────────────────────
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "file", "verdict", "confidence", "source", "elapsed_ms", "timestamp"
        ])
        writer.writeheader()
        for r in records:
            writer.writerow({k: r[k] for k in writer.fieldnames})

    # ── JSON çıktısı ───────────────────────────────────────────
    output = {
        "summary": {
            "total":           len(images),
            "analyzed":        len(records),
            "errors":          len(errors),
            "ai_count":        ai_count,
            "real_count":      real_count,
            "avg_confidence":  round(avg_conf, 2),
            "total_ms":        round(total_ms, 0),
        },
        "results": records,
        "errors":  errors,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # ── Özet rapor ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  📊  BATCH SONUÇLARI")
    print("=" * 60)
    print(f"  🖼️  Toplam görsel : {len(images)}")
    print(f"  ✅  Analiz edildi : {len(records)}")
    if errors:
        print(f"  ⚠️   Atlanan       : {len(errors)}")
    print(f"  🤖  AI üretimi    : {ai_count}")
    print(f"  📸  Gerçek fotoğraf: {real_count}")
    print(f"  📊  Ort. güven    : %{avg_conf:.1f}")
    print(f"  ⚡  Toplam süre   : {total_ms/1000:.1f}s")
    print()
    print(f"  💾  CSV  → {csv_path}")
    print(f"  💾  JSON → {json_path}")
    print("=" * 60 + "\n")


def main():
    print_banner()

    args = sys.argv[1:]

    if not args:
        print("\n  Kullanım:")
        print("    python src/main.py <image_path> [--no-cache]")
        print("    python src/main.py --batch <folder> [--no-cache]\n")
        sys.exit(1)

    use_cache = "--no-cache" not in args

    # ── Batch modu ─────────────────────────────────────────────
    if "--batch" in args:
        idx = args.index("--batch")
        if idx + 1 >= len(args):
            print("\n  ❌ Hata: --batch parametresinden sonra klasör yolu gerekli.\n")
            sys.exit(1)
        folder_path = Path(args[idx + 1])
        if not folder_path.is_dir():
            print(f"\n  ❌ Hata: '{folder_path}' bir klasör değil veya bulunamadı.\n")
            sys.exit(1)
        run_batch(folder_path, use_cache)
        return

    # ── Tekli görsel modu ──────────────────────────────────────
    image_path = Path(args[0])
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
