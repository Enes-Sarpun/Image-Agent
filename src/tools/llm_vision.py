"""
LLM Vision Tool: Gemini ile görsel analizi.
Artık forensic context'i de prompt'a dahil ediyor.
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
    SYSTEM_PROMPT,
    USER_PROMPT,
    SUPPORTED_FORMATS,
)


class LLMVisionTool:
    """Gemini Vision API ile görsel analizi."""

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

    def _build_forensic_context(self, forensic_result: Optional[dict]) -> str:
        """Forensic analizi prompt'a eklenebilir bir metne çevir."""
        if not forensic_result:
            return ""

        ai_info = forensic_result.get("ai_likelihood", {})
        score = ai_info.get("ai_score", 0)
        signals = ai_info.get("signals", [])
        interpretation = ai_info.get("interpretation", "")

        # Forensic sinyal seviyesine göre farklı context ver
        if score >= 50:
            tone = (
                "ÖN-ANALİZ UYARISI: Forensic edge analizi bu görselde belirgin AI işaretleri tespit etti. "
                "Aşağıdaki sinyallere dikkat et ve görseli BU İPUÇLARI BAĞLAMINDA incele. "
                "ANCAK: Forensic analiz kesin kanıt değildir, kendi gözlemlerin önceliklidir."
            )
        elif score >= 25:
            tone = (
                "ÖN-ANALİZ NOTU: Forensic edge analizi karışık sinyaller buldu. "
                "Bazı AI işaretleri var ama kesin değil. Kendi analizini yap, forensic'i sadece "
                "ek bilgi olarak değerlendir."
            )
        else:
            tone = (
                "ÖN-ANALİZ NOTU: Forensic edge analizi belirgin AI işareti bulamadı. "
                "Bu görselin AI olmadığını GARANTİ ETMEZ — modern AI'lar forensic tespiti atlatabilir. "
                "Kendi görsel analizini bağımsız olarak yap."
            )

        context = f"""
═══════════════════════════════════════════
{tone}

Forensic AI Score: {score}/100 ({interpretation})

Tespit edilen sinyaller:
"""
        if signals:
            for signal in signals:
                context += f"  • {signal}\n"
        else:
            context += "  (Belirgin sinyal yok)\n"

        context += f"""
ÖNEMLI: Bu forensic bilgi, edge map analizinden geliyor. 
- Yüksek skor = "dikkat et" demektir, "kesin AI" demek değil
- Düşük skor = "ek inceleme gerek" demektir, "kesin gerçek" demek değil
- Final kararı sen kendi vision analizinle ver
═══════════════════════════════════════════
"""
        return context

    def analyze(
        self,
        image_path: Path,
        forensic_result: Optional[dict] = None
    ) -> dict:
        """
        Görseli Gemini'ye gönder.
        
        Args:
            image_path: Analiz edilecek görsel
            forensic_result: ForensicAnalyzer.analyze_all() çıktısı (opsiyonel)
        """
        self._validate(image_path)
        image = Image.open(image_path)

        # Forensic context'i hazırla
        forensic_context = self._build_forensic_context(forensic_result)

        # Tam prompt'u oluştur
        full_prompt = USER_PROMPT
        if forensic_context:
            full_prompt = forensic_context + "\n\n" + USER_PROMPT

        response = self.model.generate_content([full_prompt, image])
        raw = response.text
        parsed = self._parse_json(raw)
        parsed["raw_response"] = raw
        return parsed
    
    