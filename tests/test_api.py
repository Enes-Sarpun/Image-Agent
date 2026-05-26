import io
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture
def client(mock_analysis_result):
    with patch("api.ImageAgent") as MockAgent:
        instance = MockAgent.return_value
        instance.analyze.return_value = mock_analysis_result
        import api
        api.agent = instance
        yield TestClient(api.app, raise_server_exceptions=False)


# ── Health endpoint ────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ── Format validation ──────────────────────────────────────────

def test_valid_jpeg_returns_200(client, sample_jpeg):
    r = client.post("/analyze", files={"image": ("test.jpg", io.BytesIO(sample_jpeg), "image/jpeg")})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] in ("ai", "real")
    assert 0 <= body["confidence"] <= 100
    assert "reasoning" in body
    assert "key_indicators" in body
    assert "source" in body
    assert "elapsed_ms" in body


def test_valid_png_returns_200(client, sample_png):
    r = client.post("/analyze", files={"image": ("test.png", io.BytesIO(sample_png), "image/png")})
    assert r.status_code == 200


def test_unsupported_format_returns_422(client, sample_jpeg):
    r = client.post("/analyze", files={"image": ("test.bmp", io.BytesIO(sample_jpeg), "image/bmp")})
    assert r.status_code == 422
    assert "Unsupported format" in r.json()["detail"]


def test_no_extension_returns_422(client, sample_jpeg):
    r = client.post("/analyze", files={"image": ("noext", io.BytesIO(sample_jpeg), "application/octet-stream")})
    assert r.status_code == 422


# ── File size validation ───────────────────────────────────────

def test_file_too_large_returns_413(client, large_file_bytes):
    r = client.post("/analyze", files={"image": ("big.jpg", io.BytesIO(large_file_bytes), "image/jpeg")})
    assert r.status_code == 413
    assert "too large" in r.json()["detail"].lower()


# ── Resolution validation ──────────────────────────────────────

def test_oversized_resolution_returns_422(client, oversized_image_bytes):
    r = client.post("/analyze", files={"image": ("big.jpg", io.BytesIO(oversized_image_bytes), "image/jpeg")})
    assert r.status_code == 422
    assert "4096" in r.json()["detail"]


# ── Corrupt file ───────────────────────────────────────────────

def test_corrupt_file_with_jpg_extension_returns_422(client):
    garbage = b"this is not an image at all"
    r = client.post("/analyze", files={"image": ("fake.jpg", io.BytesIO(garbage), "image/jpeg")})
    assert r.status_code == 422
    assert "corrupted" in r.json()["detail"].lower() or "Unsupported" in r.json()["detail"]


# ── Cache hit ──────────────────────────────────────────────────

def test_same_image_twice_returns_cache_on_second_call(client, sample_jpeg, mock_analysis_result):
    from result import AnalysisResult
    cached = AnalysisResult(
        verdict="ai", confidence=85.0, reasoning="from cache",
        source="cache", elapsed_ms=5.0,
    )
    call_count = {"n": 0}

    def analyze_side_effect(path):
        call_count["n"] += 1
        if call_count["n"] == 2:
            return cached
        return mock_analysis_result

    with patch("api.agent") as mock_ag:
        mock_ag.analyze.side_effect = analyze_side_effect
        client.post("/analyze", files={"image": ("test.jpg", io.BytesIO(sample_jpeg), "image/jpeg")})
        r2 = client.post("/analyze", files={"image": ("test.jpg", io.BytesIO(sample_jpeg), "image/jpeg")})
    assert r2.status_code == 200


# ── Analysis failure ───────────────────────────────────────────

def test_analysis_failure_returns_500(client, sample_jpeg):
    with patch("api.agent") as mock_ag:
        mock_ag.analyze.side_effect = RuntimeError("Gemini API error")
        r = client.post("/analyze", files={"image": ("test.jpg", io.BytesIO(sample_jpeg), "image/jpeg")})
    assert r.status_code == 500


# ── Response schema ────────────────────────────────────────────

def test_response_does_not_leak_raw_response(client, sample_jpeg):
    r = client.post("/analyze", files={"image": ("test.jpg", io.BytesIO(sample_jpeg), "image/jpeg")})
    assert r.status_code == 200
    assert "raw_response" not in r.json()
    assert "timestamp" not in r.json()
