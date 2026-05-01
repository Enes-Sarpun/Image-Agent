"""
LLM Vision Tool: Gemini ile görsel analizi.
"""

import os
import json
from pathlib import Path

import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

from config import (
    MODEL_NAME,
    MAX_TOKENS,
    TEMPERATURE,
    SYSTEM_PROMPT,
    USER_PROMPT,
    SUPPORTED_FORMATS,
)


class LLMVisionTool:
    """Gemini Vision API ile görsel analizi yapar."""

    def __init__(self):
        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_PROMPT,
            generation_config={
                "max_output_tokens": MAX_TOKENS,
                "temperature": TEMPERATURE,
            }
        )

    def _validate(self, image_path: Path) -> None:
        suffix = image_path.suffix.lower()
        if suffix not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {suffix}")

    def _parse_json(self, raw_text: str) -> dict:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[-1].strip().startswith("```"):
                cleaned = "\n".join(lines[1:-1])
            else:
                cleaned = "\n".join(lines[1:])

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON:\n{raw_text}") from e

    def analyze(self, image_path: Path) -> dict:
        """
        Görseli Gemini'ye gönder ve analiz al.
        
        Returns:
            {
                "verdict": "ai" veya "real",
                "confidence": float,
                "reasoning": str,
                "key_indicators": list,
                "raw_response": str
            }
        """
        self._validate(image_path)
        image = Image.open(image_path)
        response = self.model.generate_content([USER_PROMPT, image])
        raw = response.text
        parsed = self._parse_json(raw)
        parsed["raw_response"] = raw
        return parsed