"""
Multi-Pass Analyzer: 3 aşamalı LLM analizi.

Pass 1: AI kanıtı arama
Pass 2: Real kanıtı arama
Pass 3: Kanıtları karşılaştırarak karar verme

Tek pass'in "real bias"ını kırmak için kullanılır.
"""

import os
import json
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

from config import (
    MODEL_NAME,
    MAX_TOKENS,
    TEMPERATURE,
    MULTIPASS_AI_EVIDENCE_PROMPT,
    MULTIPASS_REAL_EVIDENCE_PROMPT,
    MULTIPASS_SYNTHESIS_PROMPT,
    SUPPORTED_FORMATS,
)


class MultiPassAnalyzer:
    """3 aşamalı LLM analizi yapar."""

    def __init__(self):
        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")

        genai.configure(api_key=api_key)
        # Multi-pass için system prompt yok — her pass kendi prompt'unu taşır
        self.model = genai.GenerativeModel(
            model_name=MODEL_NAME,
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

    def _build_forensic_context(self, forensic_result: Optional[dict]) -> str:
        """Forensic bilgisini metne çevir."""
        if not forensic_result:
            return ""

        ai_info = forensic_result.get("ai_likelihood", {})
        score = ai_info.get("ai_score", 0)
        signals = ai_info.get("signals", [])

        context = f"\n\nForensic AI Score: {score}/100\n"
        if signals:
            context += "Forensic sinyaller:\n"
            for signal in signals:
                context += f"  • {signal}\n"
        return context

    def pass_1_find_ai_evidence(
        self,
        image: Image.Image,
        forensic_context: str = ""
    ) -> dict:
        """Pass 1: AI olduğuna dair kanıt ara."""
        prompt = MULTIPASS_AI_EVIDENCE_PROMPT + forensic_context
        response = self.model.generate_content([prompt, image])
        return self._parse_json(response.text)

    def pass_2_find_real_evidence(
        self,
        image: Image.Image,
        forensic_context: str = ""
    ) -> dict:
        """Pass 2: Gerçek olduğuna dair kanıt ara."""
        prompt = MULTIPASS_REAL_EVIDENCE_PROMPT + forensic_context
        response = self.model.generate_content([prompt, image])
        return self._parse_json(response.text)

    def pass_3_synthesize(
        self,
        image: Image.Image,
        ai_evidence: dict,
        real_evidence: dict,
        forensic_context: str = ""
    ) -> dict:
        """Pass 3: Kanıtları karşılaştır, karar ver."""
        ai_text = "\n".join([f"  • {e}" for e in ai_evidence.get("evidence", [])])
        real_text = "\n".join([f"  • {e}" for e in real_evidence.get("evidence", [])])

        synthesis_input = f"""
PASS 1'DE BULUNAN AI KANITLARI:
{ai_text if ai_text else "  (kanıt bulunamadı)"}

AI evidence_strength: {ai_evidence.get("strength", "unknown")}/10

PASS 2'DE BULUNAN GERÇEK KANITLARI:
{real_text if real_text else "  (kanıt bulunamadı)"}

Real evidence_strength: {real_evidence.get("strength", "unknown")}/10

{forensic_context}

Şimdi bu iki kanıt listesini karşılaştır ve final kararı ver.
"""

        prompt = MULTIPASS_SYNTHESIS_PROMPT + "\n\n" + synthesis_input
        response = self.model.generate_content([prompt, image])
        result = self._parse_json(response.text)
        result["raw_response"] = response.text
        result["ai_evidence"] = ai_evidence.get("evidence", [])
        result["real_evidence"] = real_evidence.get("evidence", [])
        return result

    def analyze(
        self,
        image_path: Path,
        forensic_result: Optional[dict] = None
    ) -> dict:
        """3 pass'i sırayla çalıştır, final sonucu döndür."""
        self._validate(image_path)
        image = Image.open(image_path)
        forensic_context = self._build_forensic_context(forensic_result)

        # Pass 1
        print("      Pass 1: AI kanıtı aranıyor...")
        ai_evidence = self.pass_1_find_ai_evidence(image, forensic_context)

        # Pass 2
        print("      Pass 2: Gerçek kanıtı aranıyor...")
        real_evidence = self.pass_2_find_real_evidence(image, forensic_context)

        # Pass 3
        print("      Pass 3: Kanıtlar karşılaştırılıyor...")
        final = self.pass_3_synthesize(
            image,
            ai_evidence,
            real_evidence,
            forensic_context
        )

        return final
    

    