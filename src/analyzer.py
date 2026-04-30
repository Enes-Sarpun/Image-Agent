"""
Image Agent: Claude API ile görsel analizi.
"""

import os
import base64
import json
from pathlib import Path
from typing import Union

from anthropic import Anthropic
from dotenv import load_dotenv

from config import (
    MODEL_NAME,
    MAX_TOKENS,
    SYSTEM_PROMPT,
    USER_PROMPT,
    SUPPORTED_FORMATS,
)
from result import AnalysisResult


class ImageAnalyzer:
    """Görselleri Claude API kullanarak AI/Real olarak sınıflandırır."""

    def __init__(self, model: str = MODEL_NAME):
        load_dotenv()

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY bulunamadı. .env dosyasını kontrol et."
            )

        self.client = Anthropic(api_key=api_key)
        self.model = model

    def _encode_image(self, image_path: Path) -> tuple[str, str]:
        """Görseli base64'e çevir ve media type'ı belirle."""
        suffix = image_path.suffix.lower()

        if suffix not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Desteklenmeyen format: {suffix}. "
                f"Desteklenen: {', '.join(SUPPORTED_FORMATS.keys())}"
            )

        media_type = SUPPORTED_FORMATS[suffix]

        with open(image_path, "rb") as f:
            encoded = base64.standard_b64encode(f.read()).decode("utf-8")

        return encoded, media_type

    def _parse_response(self, raw_text: str) -> dict:
        """LLM yanıtından JSON çıkar."""
        cleaned = raw_text.strip()

        # ```json ... ``` ile sarılmışsa temizle
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # İlk satırı (```json) ve son satırı (```) at
            if lines[-1].strip().startswith("```"):
                cleaned = "\n".join(lines[1:-1])
            else:
                cleaned = "\n".join(lines[1:])

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"LLM yanıtı JSON olarak parse edilemedi:\n{raw_text}"
            ) from e

    def analyze(self, image_path: Union[str, Path]) -> AnalysisResult:
        """Bir görseli analiz et ve sonuç döndür."""
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Görsel bulunamadı: {image_path}")

        # Görseli encode et
        image_data, media_type = self._encode_image(image_path)

        # Claude'a gönder
        message = self.client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": USER_PROMPT,
                        },
                    ],
                }
            ],
        )

        # Yanıtı parse et
        raw_response = message.content[0].text
        parsed = self._parse_response(raw_response)

        return AnalysisResult(
            verdict=parsed["verdict"],
            confidence=float(parsed["confidence"]),
            reasoning=parsed["reasoning"],
            key_indicators=parsed.get("key_indicators", []),
            raw_response=raw_response,
        )