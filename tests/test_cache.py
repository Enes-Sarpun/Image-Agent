import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cache.disk_cache import DiskCache
from result import AnalysisResult


def _make_result(verdict="ai", confidence=80.0, source="llm") -> AnalysisResult:
    return AnalysisResult(
        verdict=verdict,
        confidence=confidence,
        reasoning="test reasoning",
        key_indicators=["indicator"],
        source=source,
        elapsed_ms=100.0,
    )


@pytest.fixture
def cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield DiskCache(cache_dir=Path(tmpdir))


# ── get: cache miss ────────────────────────────────────────────

def test_get_miss_returns_none(cache):
    assert cache.get("nonexistent-hash") is None


# ── set + get: cache hit ───────────────────────────────────────

def test_set_and_get_returns_result(cache):
    result = _make_result(verdict="real", confidence=75.0)
    cache.set("hash-abc", result)
    retrieved = cache.get("hash-abc")
    assert retrieved is not None
    assert retrieved.verdict == "real"
    assert retrieved.confidence == 75.0
    assert retrieved.source == "cache"


def test_get_preserves_key_indicators(cache):
    result = _make_result()
    result.key_indicators = ["a", "b", "c"]
    cache.set("hash-xyz", result)
    retrieved = cache.get("hash-xyz")
    assert retrieved.key_indicators == ["a", "b", "c"]


# ── get_recent ─────────────────────────────────────────────────

def test_get_recent_returns_newest_first(cache):
    cache.set("hash-1", _make_result(confidence=60.0))
    cache.set("hash-2", _make_result(confidence=70.0))
    cache.set("hash-3", _make_result(confidence=80.0))
    recent = cache.get_recent(2)
    assert len(recent) == 2
    assert recent[0].confidence == 80.0
    assert recent[1].confidence == 70.0


def test_get_recent_zero_returns_empty(cache):
    cache.set("hash-1", _make_result())
    assert cache.get_recent(0) == []


def test_get_recent_more_than_stored_returns_all(cache):
    cache.set("hash-1", _make_result())
    cache.set("hash-2", _make_result())
    recent = cache.get_recent(100)
    assert len(recent) == 2


# ── clear ──────────────────────────────────────────────────────

def test_clear_empties_cache(cache):
    cache.set("hash-1", _make_result())
    cache.set("hash-2", _make_result())
    cache.clear()
    assert cache.size() == 0
    assert cache.get("hash-1") is None
    assert cache.get_recent(10) == []


# ── size ───────────────────────────────────────────────────────

def test_size_reflects_entries(cache):
    assert cache.size() == 0
    cache.set("hash-1", _make_result())
    assert cache.size() == 1
    cache.set("hash-2", _make_result())
    assert cache.size() == 2
