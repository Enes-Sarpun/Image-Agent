"""
Image Agent: AnalysisResult dataclass.
"""

from dataclasses import dataclass, field, asdict
from typing import List
from datetime import datetime


@dataclass
class AnalysisResult:
    """Görsel analizinin yapılandırılmış sonucu."""

    verdict: str
    confidence: float
    reasoning: str
    key_indicators: List[str] = field(default_factory=list)

    # Agent metadata
    source: str = "unknown"           # "cache", "watermark", "llm", "llm_search"
    elapsed_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    raw_response: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def is_ai(self) -> bool:
        return self.verdict.lower() == "ai"

    def is_high_confidence(self, threshold: float = 75.0) -> bool:
        return self.confidence >= threshold
    

    