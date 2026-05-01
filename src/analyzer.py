"""
Image Agent: Gemini API ile görsel analizi.
"""

import os
import json
from pathlib import Path
from typing import Union

import google.generativeai as genai
from PIL import Image
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
    """Görselleri Gemini API kullanarak AI/Real olarak sınıflandırır."""

    def __init__(self, model: str = MODEL_NAME):
        load_dotenv()

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY bulunamadı. .env dosyasını kontrol et."
            )

        # Gemini SDK'yı yapılandır
        genai.configure(api_key=api_key)

        # Modeli oluştur (system instruction ile)
        self.model = genai.GenerativeModel(
            model_name=model,
            system_instruction=SYSTEM_PROMPT,
            generation_config={
                "max_output_tokens": MAX_TOKENS,
                "temperature": 0.2,  # Tutarlı sonuçlar için düşük
            }
        )

    def _validate_image(self, image_path: Path) -> None:
        """Görsel formatının desteklenip desteklenmediğini kontrol et."""
        suffix = image_path.suffix.lower()
        if suffix not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Desteklenmeyen format: {suffix}. "
                f"Desteklenen: {', '.join(SUPPORTED_FORMATS.keys())}"
            )

    def _parse_response(self, raw_text: str) -> dict:
        """LLM yanıtından JSON çıkar."""
        cleaned = raw_text.strip()

        # ```json ... ``` ile sarılmışsa temizle
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
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

        self._validate_image(image_path)

        # PIL ile görseli yükle (Gemini SDK PIL Image obje kabul ediyor)
        image = Image.open(image_path)

        # Gemini'ye gönder
        response = self.model.generate_content([USER_PROMPT, image])

        raw_response = response.text
        parsed = self._parse_response(raw_response)

        return AnalysisResult(
            verdict=parsed["verdict"],
            confidence=float(parsed["confidence"]),
            reasoning=parsed["reasoning"],
            key_indicators=parsed.get("key_indicators", []),
            raw_response=raw_response,
        )