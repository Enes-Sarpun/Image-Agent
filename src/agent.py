"""
Image Agent: Ana orkestratör.
Forensic preprocessing + LLM + Web Search.
"""

import time
from pathlib import Path
from typing import Union

from config import (
    WATERMARK_CONFIDENCE_THRESHOLD,
    LLM_CONFIDENCE_THRESHOLD,
)
from result import AnalysisResult

from tools.image_hasher import compute_hash
from tools.exif_reader import read_exif, is_likely_real_camera
from tools.watermark_detector import detect_gemini_sparkle
from tools.forensic_analyzer import ForensicAnalyzer
from tools.llm_vision import LLMVisionTool
from tools.llm_with_search import LLMWithSearchTool

from cache.sqlite_cache import SQLiteCache


class ImageAgent:
    """
    Akıllı görsel analiz agent'ı.

    Akış:
    1. Cache check
    2. Hızlı kontroller (EXIF, watermark)
    3. Forensic preprocessing (edge analizi)
    4. LLM vision (forensic context ile)
    5. Confidence düşükse → web search
    """

    def __init__(self):
        self.cache = SQLiteCache()
        self.forensic = ForensicAnalyzer()
        self.llm_vision = LLMVisionTool()
        self.llm_search = LLMWithSearchTool()

    def analyze(self, image_path: Union[str, Path], use_cache: bool = True) -> AnalysisResult:
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        start_time = time.perf_counter()

        # ─────────────────────────────────────
        # KATMAN 1: Cache check
        # ─────────────────────────────────────
        print("  [1/5] Computing image hash...")
        image_hash = compute_hash(image_path)

        if use_cache:
            cached = self.cache.get(image_hash)
            if cached:
                cached.elapsed_ms = (time.perf_counter() - start_time) * 1000
                print("  ✓ Cache hit!")
                return cached

        # ─────────────────────────────────────
        # KATMAN 2: Hızlı kontroller
        # ─────────────────────────────────────
        print("  [2/5] EXIF + watermark check...")
        exif = read_exif(image_path)
        watermark = detect_gemini_sparkle(image_path)

        # Watermark varsa direkt karar
        if watermark["found"] and watermark["confidence"] >= WATERMARK_CONFIDENCE_THRESHOLD:
            result = AnalysisResult(
                verdict="ai",
                confidence=watermark["confidence"],
                reasoning=f"AI watermark tespit edildi: {watermark['details']}",
                key_indicators=[
                    f"Watermark location: {watermark['location']}",
                    "Likely Gemini-generated image"
                ],
                source="watermark"
            )
            result.elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.cache.set(image_hash, result)
            return result

        # ─────────────────────────────────────
        # KATMAN 3: Forensic preprocessing
        # ─────────────────────────────────────
        print("  [3/5] Forensic edge analysis...")
        try:
            forensic_result = self.forensic.analyze_all(image_path)
            ai_score = forensic_result["ai_likelihood"]["ai_score"]
            print(f"      Forensic AI score: {ai_score}/100")
        except Exception as e:
            print(f"      ⚠ Forensic failed: {e}")
            forensic_result = None

        # ─────────────────────────────────────
        # KATMAN 4: LLM Analysis (forensic context ile)
        # ─────────────────────────────────────
        print("  [4/5] LLM vision analysis (with forensic context)...")
        try:
            llm_result = self.llm_vision.analyze(
                image_path,
                forensic_result=forensic_result
            )
        except Exception as e:
            raise RuntimeError(f"LLM vision failed: {e}")

        # EXIF ve forensic ipuçlarını sonuca ekle
        extra_indicators = []
        
        if is_likely_real_camera(exif):
            extra_indicators.append(
                f"EXIF: real camera detected ({exif['camera_make']} {exif['camera_model']})"
            )
        if not exif["has_exif"]:
            extra_indicators.append("EXIF: no metadata (common in AI images)")

        if forensic_result:
            forensic_signals = forensic_result["ai_likelihood"]["signals"]
            for signal in forensic_signals:
                extra_indicators.append(f"Forensic: {signal}")

        result = AnalysisResult(
            verdict=llm_result["verdict"],
            confidence=float(llm_result["confidence"]),
            reasoning=llm_result["reasoning"],
            key_indicators=llm_result.get("key_indicators", []) + extra_indicators,
            source="llm+forensic" if forensic_result else "llm",
            raw_response=llm_result.get("raw_response", "")
        )

        # Yeterince güveniyorsa cache'le ve dön
        if result.confidence >= LLM_CONFIDENCE_THRESHOLD:
            result.elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.cache.set(image_hash, result)
            return result

        # ─────────────────────────────────────
        # KATMAN 5: Web Search (fallback)
        # ─────────────────────────────────────
        print("  [5/5] Low confidence, running web search...")
        try:
            search_result = self.llm_search.analyze(image_path)
            result = AnalysisResult(
                verdict=search_result["verdict"],
                confidence=float(search_result["confidence"]),
                reasoning=search_result["reasoning"],
                key_indicators=search_result.get("key_indicators", []) + extra_indicators,
                source="llm_search+forensic",
                raw_response=search_result.get("raw_response", "")
            )
        except Exception as e:
            print(f"  ⚠ Web search failed, keeping LLM result: {e}")
            result.source = "llm+forensic (search_failed)"

        result.elapsed_ms = (time.perf_counter() - start_time) * 1000
        self.cache.set(image_hash, result)
        return result
    

    