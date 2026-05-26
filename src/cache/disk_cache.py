import json
from pathlib import Path
from typing import Optional

import diskcache

from result import AnalysisResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "cache"


class DiskCache:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = diskcache.Cache(str(cache_dir))
        self._recent: diskcache.Deque = diskcache.Deque(
            directory=str(cache_dir / "recent")
        )

    def get(self, image_hash: str) -> Optional[AnalysisResult]:
        raw = self._cache.get(image_hash)
        if raw is None:
            return None
        data = json.loads(raw)
        return AnalysisResult(
            verdict=data["verdict"],
            confidence=data["confidence"],
            reasoning=data.get("reasoning", ""),
            key_indicators=data.get("key_indicators", []),
            source="cache",
            elapsed_ms=data.get("elapsed_ms", 0.0),
            timestamp=data.get("timestamp", ""),
            raw_response=data.get("raw_response", ""),
        )

    def set(self, image_hash: str, result: AnalysisResult):
        data = {
            "verdict": result.verdict,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "key_indicators": result.key_indicators,
            "source": result.source,
            "elapsed_ms": result.elapsed_ms,
            "timestamp": result.timestamp,
            "raw_response": result.raw_response,
        }
        self._cache[image_hash] = json.dumps(data, ensure_ascii=False)
        self._recent.append(image_hash)

    def clear(self):
        self._cache.clear()
        try:
            while True:
                self._recent.popleft()
        except IndexError:
            pass

    def size(self) -> int:
        return len(self._cache)

    def get_recent(self, n: int) -> list:
        all_hashes = list(self._recent)
        recent_hashes = all_hashes[-n:] if len(all_hashes) >= n else all_hashes
        recent_hashes = list(reversed(recent_hashes))
        results = []
        for h in recent_hashes:
            result = self.get(h)
            if result is not None:
                results.append(result)
        return results
