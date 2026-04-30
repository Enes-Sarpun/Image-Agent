"""
Image Agent: Analiz sonucu için veri sınıfı.
"""

from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class AnalysisResult:
    """Görsel analizinin yapılandırılmış sonucu."""

    verdict: str                              # "ai" veya "real"
    confidence: float                         # 0-100
    reasoning: str                            # Açıklama
    key_indicators: List[str] = field(default_factory=list)
    raw_response: str = ""                    # Ham LLM yanıtı (debug)

    def to_dict(self) -> dict:
        """Dict'e çevir (JSON kaydetmek için)."""
        return asdict(self)

    def is_ai(self) -> bool:
        """AI üretimi mi?"""
        return self.verdict.lower() == "ai"

    def is_high_confidence(self, threshold: float = 75.0) -> bool:
        """Güven yüksek mi?"""
        return self.confidence >= threshold