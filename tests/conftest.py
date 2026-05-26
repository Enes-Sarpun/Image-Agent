import io
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

os.environ.setdefault("GEMINI_API_KEY", "test-key-placeholder")


def _make_jpeg_bytes(width=100, height=100) -> bytes:
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_png_bytes(width=100, height=100) -> bytes:
    img = Image.new("RGB", (width, height), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_jpeg() -> bytes:
    return _make_jpeg_bytes()


@pytest.fixture
def sample_png() -> bytes:
    return _make_png_bytes()


@pytest.fixture
def oversized_image_bytes() -> bytes:
    return _make_jpeg_bytes(width=5000, height=5000)


@pytest.fixture
def large_file_bytes() -> bytes:
    return b"x" * (21 * 1024 * 1024)


@pytest.fixture
def mock_analysis_result():
    from result import AnalysisResult
    return AnalysisResult(
        verdict="ai",
        confidence=85.0,
        reasoning="Test reasoning",
        key_indicators=["indicator 1", "indicator 2"],
        source="llm+forensic",
        elapsed_ms=1234.5,
    )


@pytest.fixture
def mock_agent(mock_analysis_result):
    with patch("agent.ImageAgent") as MockAgent:
        instance = MockAgent.return_value
        instance.analyze.return_value = mock_analysis_result
        yield instance
