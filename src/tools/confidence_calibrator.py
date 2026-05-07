"""
Confidence Calibrator: Ham LLM confidence skorunu kalibre eder.

Motivasyon:
    LLM bazen "%98 real" der ama yanılmış olur. Bu modül,
    EXIF, forensic ve watermark bilgilerini kullanarak ham skoru
    gerçekçi hale getirir.

Kurallar (sırayla uygulanır):
    1. Watermark yokken raw_confidence > 90 → max 80'e indir
    2. Forensic AI score > 50 + LLM "real" dedi → confidence -%20
    3. EXIF'te gerçek kamera var + verdict "real" → +10
    4. EXIF tamamen boş + verdict "ai" → +5
    5. Birden fazla kaynak aynı yönü gösteriyorsa → +5 (consensus boost)

Not:
    Calibration daima [0, 100] aralığında kalır.
    Her uygulanan kural bir "adjustment_log"'a kaydedilir.
"""

from typing import Optional


def calibrate(
    verdict: str,
    raw_confidence: float,
    exif: Optional[dict] = None,
    forensic_result: Optional[dict] = None,
    watermark_found: bool = False,
) -> dict:
    """
    Ham confidence'ı kalibre eder.

    Args:
        verdict:          "ai" veya "real"
        raw_confidence:   LLM'den gelen ham skor (0-100)
        exif:             read_exif() çıktısı (opsiyonel)
        forensic_result:  ForensicAnalyzer.analyze_all() çıktısı (opsiyonel)
        watermark_found:  Watermark tespit edildi mi?

    Returns:
        {
            "calibrated_confidence": float,  # Nihai skor
            "raw_confidence": float,         # Orijinal skor
            "delta": float,                  # Toplam değişim (+/-)
            "adjustment_log": list[str],     # Hangi kurallar tetiklendi
        }
    """
    confidence = float(raw_confidence)
    log = []

    # ── Yardımcı fonksiyonlar ──────────────────────────────────────
    def clamp(value: float) -> float:
        return max(0.0, min(100.0, value))

    def is_real() -> bool:
        return verdict.lower() == "real"

    def is_ai() -> bool:
        return verdict.lower() == "ai"

    # ── Forensic bilgisini çıkar ───────────────────────────────────
    forensic_ai_score = 0
    if forensic_result:
        forensic_ai_score = forensic_result.get("ai_likelihood", {}).get("ai_score", 0)

    # ── EXIF bilgisini çıkar ───────────────────────────────────────
    has_exif = bool(exif and exif.get("has_exif"))
    has_real_camera = bool(exif and exif.get("has_camera_info") and _is_known_camera(exif))

    # ══════════════════════════════════════════════════════════════
    # KURAL 1: Watermark yokken 90+ confidence çok iddialı
    # ══════════════════════════════════════════════════════════════
    if not watermark_found and confidence > 90:
        old = confidence
        confidence = min(confidence, 80.0)
        log.append(
            f"[Kural 1] Watermark yok + confidence {old:.1f} > 90 → "
            f"{confidence:.1f}'e indirildi (max 80)"
        )

    # ══════════════════════════════════════════════════════════════
    # KURAL 2: Forensic yüksek AI skoru ama LLM "real" dedi
    # ══════════════════════════════════════════════════════════════
    if forensic_ai_score > 50 and is_real():
        adjustment = -20.0
        confidence = clamp(confidence + adjustment)
        log.append(
            f"[Kural 2] Forensic AI skoru {forensic_ai_score}/100 > 50 "
            f"ama verdict=real → -{abs(adjustment):.0f} puan (çelişki cezası)"
        )

    # ══════════════════════════════════════════════════════════════
    # KURAL 3: Gerçek kamera EXIF'i + verdict "real" → boost
    # ══════════════════════════════════════════════════════════════
    if has_real_camera and is_real():
        adjustment = +10.0
        confidence = clamp(confidence + adjustment)
        camera = exif.get("camera_make", "") or ""
        log.append(
            f"[Kural 3] EXIF gerçek kamera bulundu ({camera.strip()}) "
            f"+ verdict=real → +{adjustment:.0f} puan"
        )

    # ══════════════════════════════════════════════════════════════
    # KURAL 4: EXIF tamamen boş + verdict "ai" → hafif boost
    # ══════════════════════════════════════════════════════════════
    if not has_exif and is_ai():
        adjustment = +5.0
        confidence = clamp(confidence + adjustment)
        log.append(
            f"[Kural 4] EXIF yok (AI imzası) + verdict=ai → "
            f"+{adjustment:.0f} puan"
        )

    # ══════════════════════════════════════════════════════════════
    # KURAL 5: Consensus boost — birden fazla kaynak aynı yönde
    # ══════════════════════════════════════════════════════════════
    consensus_score = _count_consensus(
        verdict=verdict,
        forensic_ai_score=forensic_ai_score,
        has_real_camera=has_real_camera,
        has_exif=has_exif,
        watermark_found=watermark_found,
    )
    if consensus_score >= 2:
        adjustment = +5.0
        confidence = clamp(confidence + adjustment)
        log.append(
            f"[Kural 5] {consensus_score} kaynak aynı yönü gösteriyor "
            f"(consensus) → +{adjustment:.0f} puan"
        )

    # ── Sonuç ─────────────────────────────────────────────────────
    confidence = clamp(confidence)
    delta = round(confidence - raw_confidence, 2)

    return {
        "calibrated_confidence": round(confidence, 2),
        "raw_confidence": round(raw_confidence, 2),
        "delta": delta,
        "adjustment_log": log,
    }


# ── Yardımcı fonksiyonlar (private) ──────────────────────────────────

def _is_known_camera(exif: dict) -> bool:
    """EXIF'teki kamera markası bilinen bir üreticiye ait mi?"""
    known_makes = {
        "canon", "nikon", "sony", "fujifilm", "panasonic",
        "olympus", "leica", "apple", "samsung", "google", "huawei",
        "xiaomi", "dji", "gopro", "pentax", "sigma",
    }
    make = (exif.get("camera_make") or "").lower()
    return any(brand in make for brand in known_makes)


def _count_consensus(
    verdict: str,
    forensic_ai_score: int,
    has_real_camera: bool,
    has_exif: bool,
    watermark_found: bool,
) -> int:
    """
    Kaç bağımsız sinyal verdict ile aynı yönü gösteriyor?

    Oy verebilecek sinyaller:
    - Forensic skoru (>50 → ai yönünde, <25 → real yönünde)
    - EXIF gerçek kamera (real yönünde)
    - EXIF boş (ai yönünde)
    - Watermark bulundu (ai yönünde)
    """
    count = 0
    is_real = verdict.lower() == "real"
    is_ai = verdict.lower() == "ai"

    # Forensic
    if is_ai and forensic_ai_score > 50:
        count += 1
    if is_real and forensic_ai_score < 25:
        count += 1

    # EXIF kamera
    if is_real and has_real_camera:
        count += 1

    # EXIF boş
    if is_ai and not has_exif:
        count += 1

    # Watermark
    if is_ai and watermark_found:
        count += 1

    return count
