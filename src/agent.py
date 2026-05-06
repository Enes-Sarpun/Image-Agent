"""
Image Agent: Ana orkestratör.
Cache → Watermark → Forensic → LLM → Multi-Pass → Web Search
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
from tools.multi_pass_analyzer import MultiPassAnalyzer
from tools.llm_with_search import LLMWithSearchTool

from cache.sqlite_cache import SQLiteCache


class ImageAgent:
    """
    Akıllı görsel analiz agent'ı.

    Akış:
    1. Cache check
    2. EXIF + Watermark
    3. Forensic preprocessing
    4. LLM vision (forensic context ile)
    5. Düşük confidence → Multi-pass reasoning
    6. Hâlâ düşük → Web search
    """

    def __init__(self):
        self.cache = SQLiteCache()
        self.forensic = ForensicAnalyzer()
        self.llm_vision = LLMVisionTool()
        self.multi_pass = MultiPassAnalyzer()
        self.llm_search = LLMWithSearchTool()

    def analyze(self, image_path: Union[str, Path], use_cache: bool = True) -> AnalysisResult:
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        start_time = time.perf_counter()

        # ─────────────────────────────────────
        # KATMAN 1: Cache check
        # ─────────────────────────────────────
        print("  [1/6] Computing image hash...")
        image_hash = compute_hash(image_path)

        if use_cache:
            cached = self.cache.get(image_hash)
            if cached:
                cached.elapsed_ms = (time.perf_counter() - start_time) * 1000
                print("  ✓ Cache hit!")
                return cached

        # ─────────────────────────────────────
        # KATMAN 2: EXIF + Watermark
        # ─────────────────────────────────────
        print("  [2/6] EXIF + watermark check...")
        exif = read_exif(image_path)
        watermark = detect_gemini_sparkle(image_path)

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
        print("  [3/6] Forensic edge analysis...")
        try:
            forensic_result = self.forensic.analyze_all(image_path)
            ai_score = forensic_result["ai_likelihood"]["ai_score"]
            print(f"      Forensic AI score: {ai_score}/100")
        except Exception as e:
            print(f"      ⚠ Forensic failed: {e}")
            forensic_result = None

        # EXIF ipuçlarını topla
        extra_indicators = []
        if is_likely_real_camera(exif):
            extra_indicators.append(
                f"EXIF: real camera detected ({exif['camera_make']} {exif['camera_model']})"
            )
        if not exif["has_exif"]:
            extra_indicators.append("EXIF: no metadata (common in AI images)")
        if forensic_result:
            for signal in forensic_result["ai_likelihood"]["signals"]:
                extra_indicators.append(f"Forensic: {signal}")

        # ─────────────────────────────────────
        # KATMAN 4: LLM Vision (tek pass)
        # ─────────────────────────────────────
        print("  [4/6] LLM vision analysis...")
        try:
            llm_result = self.llm_vision.analyze(
                image_path,
                forensic_result=forensic_result
            )
        except Exception as e:
            raise RuntimeError(f"LLM vision failed: {e}")

        result = AnalysisResult(
            verdict=llm_result["verdict"],
            confidence=float(llm_result["confidence"]),
            reasoning=llm_result["reasoning"],
            key_indicators=llm_result.get("key_indicators", []) + extra_indicators,
            source="llm+forensic" if forensic_result else "llm",
            raw_response=llm_result.get("raw_response", "")
        )

        # Yüksek confidence varsa direkt dön
        if result.confidence >= LLM_CONFIDENCE_THRESHOLD:
            result.elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.cache.set(image_hash, result)
            return result

        # ─────────────────────────────────────
        # KATMAN 5: Multi-Pass Reasoning (düşük confidence)
        # ─────────────────────────────────────
        print("  [5/6] Low confidence — running multi-pass analysis...")
        try:
            mp_result = self.multi_pass.analyze(
                image_path,
                forensic_result=forensic_result
            )

            # Multi-pass kanıtlarını indicators'a ekle
            mp_indicators = list(mp_result.get("key_indicators", []))
            if mp_result.get("ai_evidence"):
                for ev in mp_result["ai_evidence"][:3]:
                    mp_indicators.append(f"AI evidence: {ev}")
            if mp_result.get("real_evidence"):
                for ev in mp_result["real_evidence"][:3]:
                    mp_indicators.append(f"Real evidence: {ev}")

            result = AnalysisResult(
                verdict=mp_result["verdict"],
                confidence=float(mp_result["confidence"]),
                reasoning=mp_result["reasoning"],
                key_indicators=mp_indicators + extra_indicators,
                source="multi_pass+forensic",
                raw_response=mp_result.get("raw_response", "")
            )
        except Exception as e:
            print(f"      ⚠ Multi-pass failed, keeping LLM result: {e}")

        # Multi-pass yeterince güveniyorsa dön
        if result.confidence >= LLM_CONFIDENCE_THRESHOLD:
            result.elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.cache.set(image_hash, result)
            return result

        # ─────────────────────────────────────
        # KATMAN 6: Web Search (son çare)
        # ─────────────────────────────────────
        print("  [6/6] Still low confidence — running web search...")
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
            print(f"  ⚠ Web search failed: {e}")
            result.source = result.source + " (search_failed)"

        result.elapsed_ms = (time.perf_counter() - start_time) * 1000
        self.cache.set(image_hash, result)
        return result
    

    