"""
Image Agent: Ana orkestratör.
Tool'ları sırayla kullanarak akıllı karar verir.
"""

import time
from pathlib import Path
from typing import Union

from config import WATERMARK_CONFIDENCE_THRESHOLD, LLM_CONFIDENCE_THRESHOLD
from result import AnalysisResult

from tools.image_hasher import compute_hash
from tools.exif_reader import read_exif, is_likely_real_camera
from tools.watermark_detector import detect_gemini_sparkle
from tools.llm_vision import LLMVisionTool
from tools.llm_with_search import LLMWithSearchTool

from cache.sqlite_cache import SQLiteCache


class ImageAgent:
    """
    Akıllı görsel analiz agent'ı.
    
    Akış:
    1. Cache check
    2. EXIF + Watermark
    3. LLM vision (gerekirse)
    4. LLM + web search (hâlâ belirsizse)
    """

    def __init__(self):
        self.cache = SQLiteCache()
        self.llm_vision = LLMVisionTool()
        self.llm_search = LLMWithSearchTool()

    def analyze(self, image_path: Union[str, Path], use_cache: bool = True) -> AnalysisResult:
        """Bir görseli analiz et."""
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        start_time = time.perf_counter()

        # ─────────────────────────────────────
        # KATMAN 1: Hash + Cache check
        # ─────────────────────────────────────
        print("  [1/4] Computing image hash...")
        image_hash = compute_hash(image_path)

        if use_cache:
            cached = self.cache.get(image_hash)
            if cached:
                cached.elapsed_ms = (time.perf_counter() - start_time) * 1000
                print("  ✓ Cache hit!")
                return cached

        # ─────────────────────────────────────
        # KATMAN 2: EXIF + Watermark (hızlı kontroller)
        # ─────────────────────────────────────
        print("  [2/4] Checking EXIF and watermark...")
        exif = read_exif(image_path)
        watermark = detect_gemini_sparkle(image_path)

        # Watermark yüksek confidence ile bulunduysa direkt karar ver
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
        # KATMAN 3: LLM Vision Analysis
        # ─────────────────────────────────────
        print("  [3/4] Running LLM vision analysis...")
        try:
            llm_result = self.llm_vision.analyze(image_path)
        except Exception as e:
            raise RuntimeError(f"LLM vision failed: {e}")

        # EXIF ipuçlarını gerekçeye ekle
        extra_indicators = []
        if is_likely_real_camera(exif):
            extra_indicators.append(
                f"EXIF: real camera detected ({exif['camera_make']} {exif['camera_model']})"
            )
        if not exif["has_exif"]:
            extra_indicators.append("EXIF: no metadata (common in AI images)")

        result = AnalysisResult(
            verdict=llm_result["verdict"],
            confidence=float(llm_result["confidence"]),
            reasoning=llm_result["reasoning"],
            key_indicators=llm_result.get("key_indicators", []) + extra_indicators,
            source="llm",
            raw_response=llm_result.get("raw_response", "")
        )

        # LLM yeterince güveniyorsa cache'le ve dön
        if result.confidence >= LLM_CONFIDENCE_THRESHOLD:
            result.elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.cache.set(image_hash, result)
            return result

        # ─────────────────────────────────────
        # KATMAN 4: LLM + Web Search (derinlemesine)
        # ─────────────────────────────────────
        print("  [4/4] Low confidence, running web search analysis...")
        try:
            search_result = self.llm_search.analyze(image_path)
            result = AnalysisResult(
                verdict=search_result["verdict"],
                confidence=float(search_result["confidence"]),
                reasoning=search_result["reasoning"],
                key_indicators=search_result.get("key_indicators", []) + extra_indicators,
                source="llm_search",
                raw_response=search_result.get("raw_response", "")
            )
        except Exception as e:
            # Search başarısız olursa, normal LLM sonucuyla yetin
            print(f"  ⚠ Web search failed, using LLM-only result: {e}")
            result.source = "llm (search_failed)"

        result.elapsed_ms = (time.perf_counter() - start_time) * 1000
        self.cache.set(image_hash, result)
        return result

"""
Image Agent: Ana orkestratör.
Tool'ları sırayla kullanarak akıllı karar verir.
"""

import time
from pathlib import Path
from typing import Union

from config import WATERMARK_CONFIDENCE_THRESHOLD, LLM_CONFIDENCE_THRESHOLD
from result import AnalysisResult

from tools.image_hasher import compute_hash
from tools.exif_reader import read_exif, is_likely_real_camera
from tools.watermark_detector import detect_gemini_sparkle
from tools.llm_vision import LLMVisionTool
from tools.llm_with_search import LLMWithSearchTool

from cache.sqlite_cache import SQLiteCache


class ImageAgent:
    """
    Akıllı görsel analiz agent'ı.
    
    Akış:
    1. Cache check
    2. EXIF + Watermark
    3. LLM vision (gerekirse)
    4. LLM + web search (hâlâ belirsizse)
    """

    def __init__(self):
        self.cache = SQLiteCache()
        self.llm_vision = LLMVisionTool()
        self.llm_search = LLMWithSearchTool()

    def analyze(self, image_path: Union[str, Path], use_cache: bool = True) -> AnalysisResult:
        """Bir görseli analiz et."""
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        start_time = time.perf_counter()

        # ─────────────────────────────────────
        # KATMAN 1: Hash + Cache check
        # ─────────────────────────────────────
        print("  [1/4] Computing image hash...")
        image_hash = compute_hash(image_path)

        if use_cache:
            cached = self.cache.get(image_hash)
            if cached:
                cached.elapsed_ms = (time.perf_counter() - start_time) * 1000
                print("  ✓ Cache hit!")
                return cached

        # ─────────────────────────────────────
        # KATMAN 2: EXIF + Watermark (hızlı kontroller)
        # ─────────────────────────────────────
        print("  [2/4] Checking EXIF and watermark...")
        exif = read_exif(image_path)
        watermark = detect_gemini_sparkle(image_path)

        # Watermark yüksek confidence ile bulunduysa direkt karar ver
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
        # KATMAN 3: LLM Vision Analysis
        # ─────────────────────────────────────
        print("  [3/4] Running LLM vision analysis...")
        try:
            llm_result = self.llm_vision.analyze(image_path)
        except Exception as e:
            raise RuntimeError(f"LLM vision failed: {e}")

        # EXIF ipuçlarını gerekçeye ekle
        extra_indicators = []
        if is_likely_real_camera(exif):
            extra_indicators.append(
                f"EXIF: real camera detected ({exif['camera_make']} {exif['camera_model']})"
            )
        if not exif["has_exif"]:
            extra_indicators.append("EXIF: no metadata (common in AI images)")

        result = AnalysisResult(
            verdict=llm_result["verdict"],
            confidence=float(llm_result["confidence"]),
            reasoning=llm_result["reasoning"],
            key_indicators=llm_result.get("key_indicators", []) + extra_indicators,
            source="llm",
            raw_response=llm_result.get("raw_response", "")
        )

        # LLM yeterince güveniyorsa cache'le ve dön
        if result.confidence >= LLM_CONFIDENCE_THRESHOLD:
            result.elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.cache.set(image_hash, result)
            return result

        # ─────────────────────────────────────
        # KATMAN 4: LLM + Web Search (derinlemesine)
        # ─────────────────────────────────────
        print("  [4/4] Low confidence, running web search analysis...")
        try:
            search_result = self.llm_search.analyze(image_path)
            result = AnalysisResult(
                verdict=search_result["verdict"],
                confidence=float(search_result["confidence"]),
                reasoning=search_result["reasoning"],
                key_indicators=search_result.get("key_indicators", []) + extra_indicators,
                source="llm_search",
                raw_response=search_result.get("raw_response", "")
            )
        except Exception as e:
            # Search başarısız olursa, normal LLM sonucuyla yetin
            print(f"  ⚠ Web search failed, using LLM-only result: {e}")
            result.source = "llm (search_failed)"

        result.elapsed_ms = (time.perf_counter() - start_time) * 1000
        self.cache.set(image_hash, result)
        return result