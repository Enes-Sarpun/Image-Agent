"""
Image Agent — Modern Web Arayüzü (Gradio v2)

Başlatmak için:
    python app.py
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import sqlite3
import json
import warnings
from pathlib import Path
from io import BytesIO

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import gradio as gr
from PIL import Image

warnings.filterwarnings("ignore", category=FutureWarning, module="google")

from agent import ImageAgent
from config import DB_PATH

agent = ImageAgent()

GITHUB_URL = "https://github.com/Enes-Sarpun/Image-Agent"


# ══════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ══════════════════════════════════════════════════════════════

def _get_cache_history(limit: int = 10) -> list[list]:
    if not DB_PATH.exists():
        return []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                """SELECT verdict, confidence, source, timestamp, reasoning
                   FROM analysis_cache
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (limit,)
            ).fetchall()
        result = []
        for r in rows:
            verdict, conf, source, ts, reasoning = r
            icon = "🤖 AI" if verdict == "ai" else "📸 Gerçek"
            result.append([
                icon,
                f"%{conf:.1f}",
                source or "—",
                (ts or "")[:16].replace("T", " "),
                (reasoning or "")[:80] + ("…" if len(reasoning or "") > 80 else ""),
            ])
        return result
    except Exception:
        return []


def _confidence_color(verdict: str, confidence: float) -> str:
    if verdict == "ai":
        if confidence >= 80: return "#ef4444"
        elif confidence >= 60: return "#f97316"
        else: return "#eab308"
    else:
        if confidence >= 80: return "#22c55e"
        elif confidence >= 60: return "#84cc16"
        else: return "#eab308"


def _build_verdict_html(verdict: str, confidence: float, source: str, elapsed_ms: float) -> str:
    color = _confidence_color(verdict, confidence)
    icon = "🤖" if verdict == "ai" else "📸"
    label = "AI ÜRETİMİ" if verdict == "ai" else "GERÇEK FOTOĞRAF"
    bar_pct = int(confidence)

    source_map = {
        "watermark":           "🏷️ Watermark Tespiti",
        "llm":                 "🧠 LLM Analizi",
        "llm+forensic":        "🧠 LLM + Forensic",
        "multi_pass+forensic": "🔁 Multi-Pass + Forensic",
        "llm_search+forensic": "🔎 LLM + Web Search",
        "cache":               "💾 Önbellekten",
    }
    source_label = source_map.get(source, source)

    return f"""
    <div class="verdict-card" style="
        background: linear-gradient(135deg, #1e1e2e 0%, #16213e 100%);
        border: 2px solid {color};
        border-radius: 20px;
        padding: 32px 36px;
        font-family: 'Inter', 'Segoe UI', sans-serif;
        box-shadow: 0 0 40px {color}33, 0 8px 32px rgba(0,0,0,0.4);
        animation: fadeScaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        position: relative;
        overflow: hidden;
    ">
        <div style="
            position: absolute; top: -40px; right: -40px;
            width: 160px; height: 160px;
            background: radial-gradient(circle, {color}22 0%, transparent 70%);
            border-radius: 50%;
        "></div>

        <div style="display:flex; align-items:center; gap:20px; margin-bottom:24px; position:relative;">
            <div style="
                font-size:56px;
                filter: drop-shadow(0 0 12px {color}88);
                animation: pulse 2s ease-in-out infinite;
            ">{icon}</div>
            <div>
                <div style="color:{color}; font-size:30px; font-weight:800; letter-spacing:1px;
                            text-shadow: 0 0 20px {color}66;">{label}</div>
                <div style="color:#64748b; font-size:13px; margin-top:6px;">
                    {source_label} &nbsp;·&nbsp; ⚡ {elapsed_ms:.0f} ms
                </div>
            </div>
        </div>

        <div style="position:relative;">
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:#94a3b8; font-size:13px; font-weight:600; letter-spacing:0.5px;">
                    GÜVEN SKORU
                </span>
                <span style="color:{color}; font-size:20px; font-weight:800;">%{confidence:.1f}</span>
            </div>
            <div style="background:#1e293b; border-radius:999px; height:12px; overflow:hidden;
                        box-shadow: inset 0 2px 4px rgba(0,0,0,0.4);">
                <div style="
                    width:{bar_pct}%;
                    height:100%;
                    background: linear-gradient(90deg, {color}66, {color});
                    border-radius:999px;
                    box-shadow: 0 0 12px {color}88;
                    animation: barFill 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
                "></div>
            </div>
        </div>
    </div>
    <style>
        @keyframes fadeScaleIn {{
            from {{ opacity: 0; transform: scale(0.92) translateY(12px); }}
            to   {{ opacity: 1; transform: scale(1) translateY(0); }}
        }}
        @keyframes barFill {{
            from {{ width: 0%; }}
            to   {{ width: {bar_pct}%; }}
        }}
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.08); }}
        }}
    </style>
    """


def _build_reasoning_html(reasoning: str, indicators: list[str]) -> str:
    main_indicators = [i for i in indicators if not i.startswith("Calibration:")]
    calibration_items = [i for i in indicators if i.startswith("Calibration:")]

    indicators_html = "".join(
        f'<li style="margin-bottom:8px; color:#cbd5e1; line-height:1.5;">'
        f'<span style="color:#6366f1; margin-right:6px;">▸</span>{ind}</li>'
        for ind in main_indicators
    )

    cal_html = ""
    if calibration_items:
        cal_html = f"""
        <div style="margin-top:20px; padding:12px 16px;
                    background: linear-gradient(135deg, #1e293b, #0f172a);
                    border-left:3px solid #6366f1; border-radius:8px;">
            <div style="color:#818cf8; font-size:11px; font-weight:700;
                        letter-spacing:1px; margin-bottom:4px;">⚖️ KALİBRASYON</div>
            <div style="color:#94a3b8; font-size:13px;">{calibration_items[0]}</div>
        </div>
        """

    return f"""
    <div style="
        background: linear-gradient(135deg, #0f172a, #0a0f1e);
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 24px 28px;
        font-family: 'Inter', 'Segoe UI', sans-serif;
        animation: fadeScaleIn 0.4s ease 0.1s both;
    ">
        <div style="margin-bottom:20px;">
            <div style="color:#64748b; font-size:11px; font-weight:700;
                        letter-spacing:1px; margin-bottom:10px;">💭 GEREKÇE</div>
            <div style="color:#e2e8f0; font-size:14px; line-height:1.8;">{reasoning}</div>
        </div>
        {'<div><div style="color:#64748b; font-size:11px; font-weight:700; letter-spacing:1px; margin-bottom:10px;">🔍 ANAHTAR İPUÇLARI</div><ul style="margin:0; padding-left:16px; list-style:none;">' + indicators_html + '</ul></div>' if indicators_html else ''}
        {cal_html}
    </div>
    """


# ══════════════════════════════════════════════════════════════
# ANALİZ FONKSİYONU
# ══════════════════════════════════════════════════════════════

def analyze_image(image, use_cache: bool):
    if image is None:
        return (
            "<div style='color:#ef4444; padding:24px; text-align:center; "
            "font-family:Inter,sans-serif; font-size:15px;'>⚠️ Lütfen bir görsel yükleyin.</div>",
            "<div></div>",
            None, None, None,
            _get_cache_history(),
        )

    tmp_path = PROJECT_ROOT / "data" / "_tmp_upload.png"
    tmp_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(image, str):
        pil_img = Image.open(image)
    else:
        pil_img = Image.fromarray(image)

    pil_img.save(tmp_path, format="PNG")

    try:
        result = agent.analyze(tmp_path, use_cache=use_cache)
    except Exception as e:
        return (
            f"<div style='color:#ef4444; padding:24px; font-family:Inter,sans-serif;'>"
            f"❌ Analiz hatası: {e}</div>",
            "<div></div>",
            None, None, None,
            _get_cache_history(),
        )

    ela_img = fft_img = edge_img = None
    try:
        forensic = agent.forensic.analyze_all(tmp_path)
        ela_img  = forensic["ela_image"]
        fft_img  = forensic["fft_image"].convert("RGB")
        edge_img = forensic["edge_image"].convert("RGB")
    except Exception:
        pass

    verdict_html   = _build_verdict_html(result.verdict, result.confidence, result.source, result.elapsed_ms)
    reasoning_html = _build_reasoning_html(result.reasoning, result.key_indicators)

    return (
        verdict_html,
        reasoning_html,
        ela_img,
        fft_img,
        edge_img,
        _get_cache_history(),
    )


def refresh_history():
    return _get_cache_history()


# ══════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body, .gradio-container {
    background: #03060f !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
    min-height: 100vh;
}

/* Hide gradio footer */
footer { display: none !important; }
.gr-prose { color: #e2e8f0 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0a0f1e; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }

/* ── Upload alanı ── */
.upload-area .wrap, .upload-area > div {
    border: 2px dashed #334155 !important;
    border-radius: 20px !important;
    background: #0a0f1e !important;
    transition: all 0.3s ease !important;
    cursor: pointer;
}
.upload-area .wrap:hover, .upload-area > div:hover {
    border-color: #6366f1 !important;
    background: #0f1729 !important;
    box-shadow: 0 0 40px #6366f122 !important;
}

/* ── Analiz butonu ── */
.analyze-btn button {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%) !important;
    border: none !important;
    border-radius: 14px !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 17px !important;
    padding: 14px 40px !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 24px #6366f144 !important;
    letter-spacing: 0.3px;
}
.analyze-btn button:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 12px 40px #6366f166 !important;
    filter: brightness(1.1) !important;
}
.analyze-btn button:active { transform: translateY(-1px) !important; }

/* ── Checkbox ── */
.gr-checkbox { accent-color: #6366f1; }
label span { color: #94a3b8 !important; font-size: 13px !important; }

/* ── Panel arka planları ── */
.gr-panel, .gr-box, .gr-form, .gr-block {
    background: transparent !important;
    border: none !important;
}

/* ── Accordion ── */
details summary {
    background: linear-gradient(135deg, #0f172a, #0a0f1e) !important;
    border: 1px solid #1e293b !important;
    border-radius: 12px !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    padding: 14px 20px !important;
    cursor: pointer;
    transition: all 0.2s ease;
}
details summary:hover {
    border-color: #334155 !important;
    color: #e2e8f0 !important;
}
details[open] summary { border-radius: 12px 12px 0 0 !important; }
details > div {
    background: #0a0f1e !important;
    border: 1px solid #1e293b !important;
    border-top: none !important;
    border-radius: 0 0 12px 12px !important;
    padding: 20px !important;
}

/* ── Forensic görseller ── */
.forensic-img img {
    border-radius: 10px !important;
    border: 1px solid #1e293b !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.forensic-img img:hover {
    transform: scale(1.02);
    box-shadow: 0 8px 32px rgba(99,102,241,0.3);
}

/* ── Tablo ── */
table {
    background: #0a0f1e !important;
    color: #cbd5e1 !important;
    border-collapse: collapse;
    width: 100%;
}
th {
    background: #0f172a !important;
    color: #64748b !important;
    font-size: 11px !important;
    letter-spacing: 1px !important;
    text-transform: uppercase;
    padding: 10px 14px !important;
}
td { padding: 10px 14px !important; border-bottom: 1px solid #1e293b !important; }
tr:hover td { background: #0f172a44 !important; }

/* ── Section divider ── */
.section-divider {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, #1e293b, transparent);
    margin: 0;
}

/* ── Animasyonlar ── */
@keyframes fadeScaleIn {
    from { opacity: 0; transform: scale(0.92) translateY(12px); }
    to   { opacity: 1; transform: scale(1)    translateY(0); }
}
@keyframes floatY {
    0%, 100% { transform: translateY(0px); }
    50%       { transform: translateY(-10px); }
}
@keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
@keyframes blobPulse {
    0%, 100% { transform: scale(1)    rotate(0deg); }
    33%       { transform: scale(1.08) rotate(5deg); }
    66%       { transform: scale(0.94) rotate(-3deg); }
}
@keyframes slideUp {
    from { opacity: 0; transform: translateY(30px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes sparkle {
    0%, 100% { opacity: 0; transform: scale(0); }
    50%       { opacity: 1; transform: scale(1); }
}

.float-anim { animation: floatY 4s ease-in-out infinite; }
.slide-up   { animation: slideUp 0.6s ease both; }
"""


# ══════════════════════════════════════════════════════════════
# HTML BÖLÜMLER
# ══════════════════════════════════════════════════════════════

HERO_HTML = """
<div style="
    position: relative;
    text-align: center;
    padding: 72px 24px 48px;
    overflow: hidden;
">
    <!-- Animated blobs -->
    <div style="
        position: absolute; top: -80px; left: -80px;
        width: 400px; height: 400px;
        background: radial-gradient(circle, #6366f122 0%, transparent 70%);
        border-radius: 50%;
        animation: blobPulse 8s ease-in-out infinite;
        pointer-events: none;
    "></div>
    <div style="
        position: absolute; top: -40px; right: -60px;
        width: 320px; height: 320px;
        background: radial-gradient(circle, #ec489922 0%, transparent 70%);
        border-radius: 50%;
        animation: blobPulse 10s ease-in-out infinite reverse;
        pointer-events: none;
    "></div>
    <div style="
        position: absolute; bottom: -60px; left: 40%;
        width: 280px; height: 280px;
        background: radial-gradient(circle, #8b5cf622 0%, transparent 70%);
        border-radius: 50%;
        animation: blobPulse 12s ease-in-out infinite 2s;
        pointer-events: none;
    "></div>

    <!-- Sparkles -->
    <div style="position:absolute; top:60px; left:15%; font-size:18px;
                animation: sparkle 3s ease-in-out infinite;">✦</div>
    <div style="position:absolute; top:40px; right:18%; font-size:12px;
                animation: sparkle 4s ease-in-out infinite 1s; color:#6366f1;">✦</div>
    <div style="position:absolute; bottom:80px; left:8%; font-size:10px;
                animation: sparkle 5s ease-in-out infinite 2s; color:#ec4899;">✦</div>

    <!-- Badge -->
    <div style="
        display: inline-flex; align-items: center; gap: 8px;
        background: linear-gradient(135deg, #6366f120, #8b5cf620);
        border: 1px solid #6366f140;
        border-radius: 999px;
        padding: 6px 18px;
        font-size: 12px; font-weight: 600; color: #818cf8;
        letter-spacing: 0.5px;
        margin-bottom: 24px;
        animation: slideUp 0.5s ease;
    ">
        ✦ &nbsp; Gemini Vision · Forensic Analysis · Multi-Pass AI
    </div>

    <!-- Ana başlık -->
    <h1 style="
        font-size: clamp(48px, 7vw, 80px);
        font-weight: 900;
        line-height: 1.05;
        margin-bottom: 20px;
        letter-spacing: -2px;
        background: linear-gradient(135deg, #e2e8f0 0%, #a5b4fc 40%, #ec4899 70%, #f97316 100%);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: gradientShift 5s ease infinite, slideUp 0.6s ease 0.1s both;
    ">
        Image Agent
    </h1>

    <!-- Tagline -->
    <p style="
        font-size: 19px;
        color: #64748b;
        font-weight: 400;
        max-width: 520px;
        margin: 0 auto 12px;
        line-height: 1.6;
        animation: slideUp 0.6s ease 0.2s both;
    ">
        Bir görsel <span style='color:#a5b4fc; font-weight:600;'>AI tarafından mı</span> üretildi,
        yoksa <span style='color:#34d399; font-weight:600;'>gerçek fotoğraf</span> mı?
    </p>
    <p style="
        font-size: 15px;
        color: #475569;
        animation: slideUp 0.6s ease 0.3s both;
        margin-bottom: 0;
    ">
        Saniyeler içinde, çok katmanlı forensic analiz ile öğren.
    </p>
</div>
"""

HOW_IT_WORKS_HTML = """
<div style="
    padding: 80px 24px;
    text-align: center;
    position: relative;
">
    <div style="
        display: inline-block;
        background: linear-gradient(135deg, #6366f120, #8b5cf620);
        border: 1px solid #6366f130;
        border-radius: 999px;
        padding: 5px 16px;
        font-size: 11px; font-weight: 700; color: #6366f1;
        letter-spacing: 2px; text-transform: uppercase;
        margin-bottom: 16px;
    ">Nasıl Çalışır?</div>

    <h2 style="
        font-size: 36px; font-weight: 800;
        color: #e2e8f0; margin-bottom: 12px;
        letter-spacing: -0.5px;
    ">7 Katmanlı Analiz Pipeline'ı</h2>
    <p style="color:#475569; font-size:15px; margin-bottom:52px;">
        Her görsel, karardan önce yedi farklı kontrol aşamasından geçer.
    </p>

    <div style="
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        max-width: 1100px;
        margin: 0 auto;
        text-align: left;
    ">
        <!-- Kart 1 -->
        <div style="
            background: linear-gradient(135deg, #0f172a, #0a0f1e);
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 24px 20px;
            position: relative;
            overflow: hidden;
            transition: border-color 0.2s, transform 0.2s;
        " onmouseover="this.style.borderColor='#334155';this.style.transform='translateY(-4px)'"
           onmouseout="this.style.borderColor='#1e293b';this.style.transform='translateY(0)'">
            <div style="font-size:28px; margin-bottom:12px;">💾</div>
            <div style="font-size:10px; color:#6366f1; font-weight:700; letter-spacing:2px; margin-bottom:6px;">ADIM 1</div>
            <div style="font-size:15px; font-weight:700; color:#e2e8f0; margin-bottom:8px;">Cache Kontrolü</div>
            <div style="font-size:13px; color:#64748b; line-height:1.6;">
                Perceptual hash ile aynı görsel daha önce analiz edilmişse ~100ms'de sonuç döner.
            </div>
        </div>

        <!-- Kart 2 -->
        <div style="
            background: linear-gradient(135deg, #0f172a, #0a0f1e);
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 24px 20px;
            transition: border-color 0.2s, transform 0.2s;
        " onmouseover="this.style.borderColor='#334155';this.style.transform='translateY(-4px)'"
           onmouseout="this.style.borderColor='#1e293b';this.style.transform='translateY(0)'">
            <div style="font-size:28px; margin-bottom:12px;">🏷️</div>
            <div style="font-size:10px; color:#8b5cf6; font-weight:700; letter-spacing:2px; margin-bottom:6px;">ADIM 2</div>
            <div style="font-size:15px; font-weight:700; color:#e2e8f0; margin-bottom:8px;">EXIF + Watermark</div>
            <div style="font-size:13px; color:#64748b; line-height:1.6;">
                Kamera EXIF verisi okunur. Gemini sparkle watermark'ı pixel analizi ile tespit edilir.
            </div>
        </div>

        <!-- Kart 3 -->
        <div style="
            background: linear-gradient(135deg, #0f172a, #0a0f1e);
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 24px 20px;
            transition: border-color 0.2s, transform 0.2s;
        " onmouseover="this.style.borderColor='#334155';this.style.transform='translateY(-4px)'"
           onmouseout="this.style.borderColor='#1e293b';this.style.transform='translateY(0)'">
            <div style="font-size:28px; margin-bottom:12px;">🔬</div>
            <div style="font-size:10px; color:#ec4899; font-weight:700; letter-spacing:2px; margin-bottom:6px;">ADIM 3</div>
            <div style="font-size:15px; font-weight:700; color:#e2e8f0; margin-bottom:8px;">Forensic Analiz</div>
            <div style="font-size:13px; color:#64748b; line-height:1.6;">
                ELA (Error Level Analysis), FFT frekans haritası ve edge pattern yoğunluğu hesaplanır.
            </div>
        </div>

        <!-- Kart 4 -->
        <div style="
            background: linear-gradient(135deg, #0f172a, #0a0f1e);
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 24px 20px;
            transition: border-color 0.2s, transform 0.2s;
        " onmouseover="this.style.borderColor='#334155';this.style.transform='translateY(-4px)'"
           onmouseout="this.style.borderColor='#1e293b';this.style.transform='translateY(0)'">
            <div style="font-size:28px; margin-bottom:12px;">🧠</div>
            <div style="font-size:10px; color:#f97316; font-weight:700; letter-spacing:2px; margin-bottom:6px;">ADIM 4</div>
            <div style="font-size:15px; font-weight:700; color:#e2e8f0; margin-bottom:8px;">LLM Vision</div>
            <div style="font-size:13px; color:#64748b; line-height:1.6;">
                Gemini 2.5 Flash, forensic context ile beslenerek görseli yorumlar.
            </div>
        </div>

        <!-- Kart 5 -->
        <div style="
            background: linear-gradient(135deg, #0f172a, #0a0f1e);
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 24px 20px;
            transition: border-color 0.2s, transform 0.2s;
        " onmouseover="this.style.borderColor='#334155';this.style.transform='translateY(-4px)'"
           onmouseout="this.style.borderColor='#1e293b';this.style.transform='translateY(0)'">
            <div style="font-size:28px; margin-bottom:12px;">🔁</div>
            <div style="font-size:10px; color:#22c55e; font-weight:700; letter-spacing:2px; margin-bottom:6px;">ADIM 5</div>
            <div style="font-size:15px; font-weight:700; color:#e2e8f0; margin-bottom:8px;">Multi-Pass Reasoning</div>
            <div style="font-size:13px; color:#64748b; line-height:1.6;">
                Düşük confidence'da 3 aşamalı çapraz sorgulama: AI kanıtı → Gerçek kanıtı → Sentez.
            </div>
        </div>

        <!-- Kart 6 -->
        <div style="
            background: linear-gradient(135deg, #0f172a, #0a0f1e);
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 24px 20px;
            transition: border-color 0.2s, transform 0.2s;
        " onmouseover="this.style.borderColor='#334155';this.style.transform='translateY(-4px)'"
           onmouseout="this.style.borderColor='#1e293b';this.style.transform='translateY(0)'">
            <div style="font-size:28px; margin-bottom:12px;">🔎</div>
            <div style="font-size:10px; color:#06b6d4; font-weight:700; letter-spacing:2px; margin-bottom:6px;">ADIM 6</div>
            <div style="font-size:15px; font-weight:700; color:#e2e8f0; margin-bottom:8px;">Web Search Fallback</div>
            <div style="font-size:13px; color:#64748b; line-height:1.6;">
                Hâlâ belirsizse Google Search grounding devreye girer, web bağlamı ile karar güçlenir.
            </div>
        </div>

        <!-- Kart 7 (tam genişlik) -->
        <div style="
            grid-column: 1 / -1;
            background: linear-gradient(135deg, #1a1040, #0a0f1e);
            border: 1px solid #6366f133;
            border-radius: 16px;
            padding: 24px 28px;
            display: flex;
            align-items: center;
            gap: 20px;
            transition: border-color 0.2s, transform 0.2s;
        " onmouseover="this.style.borderColor='#6366f166';this.style.transform='translateY(-2px)'"
           onmouseout="this.style.borderColor='#6366f133';this.style.transform='translateY(0)'">
            <div style="font-size:40px; flex-shrink:0;">⚖️</div>
            <div>
                <div style="font-size:10px; color:#6366f1; font-weight:700; letter-spacing:2px; margin-bottom:6px;">ADIM 7</div>
                <div style="font-size:16px; font-weight:700; color:#e2e8f0; margin-bottom:6px;">Confidence Calibration</div>
                <div style="font-size:13px; color:#64748b; line-height:1.6;">
                    Ham LLM skoru 5 kuralla kalibre edilir: watermark durumu, forensic çelişkisi, EXIF kamera bilgisi ve consensus boost.
                    Yanlış cevaplar artık düşük güven ile işaretlenir.
                </div>
            </div>
        </div>
    </div>
</div>
"""

ABOUT_HTML = """
<div style="
    padding: 80px 24px;
    max-width: 900px;
    margin: 0 auto;
">
    <div style="
        display: inline-block;
        background: linear-gradient(135deg, #ec489920, #f9731620);
        border: 1px solid #ec489930;
        border-radius: 999px;
        padding: 5px 16px;
        font-size: 11px; font-weight: 700; color: #f472b6;
        letter-spacing: 2px; text-transform: uppercase;
        margin-bottom: 16px;
    ">Hakkında</div>

    <h2 style="font-size:36px; font-weight:800; color:#e2e8f0; margin-bottom:20px; letter-spacing:-0.5px;">
        Neden Image Agent?
    </h2>

    <p style="color:#94a3b8; font-size:16px; line-height:1.85; margin-bottom:16px;">
        Yapay zeka üretimi görseller hızla gerçekçileşiyor. Midjourney, Stable Diffusion, Imagen ve
        Flux gibi modeller artık insan gözünü kolayca yanıltıyor. Image Agent, bu soruna
        <strong style="color:#a5b4fc;">çok katmanlı, LLM destekli</strong> bir yanıt sunuyor.
    </p>
    <p style="color:#64748b; font-size:15px; line-height:1.85; margin-bottom:40px;">
        Forensic tekniklerini (ELA, FFT, edge analizi) doğrudan Gemini Vision'a bağlayarak,
        modelin "kör" karar vermek yerine sayısal ipuçlarıyla desteklenen bir yargıya ulaşmasını sağlıyoruz.
        Yüksek belirsizlik durumlarında 3 aşamalı çapraz sorgulama ve web arama devreye giriyor.
    </p>

    <!-- Teknoloji badge'leri -->
    <div style="margin-bottom:48px;">
        <div style="color:#475569; font-size:12px; font-weight:700; letter-spacing:1px;
                    text-transform:uppercase; margin-bottom:14px;">Teknolojiler</div>
        <div style="display:flex; flex-wrap:wrap; gap:10px;">
            <span style="background:#1e293b; border:1px solid #334155; color:#94a3b8;
                         padding:6px 14px; border-radius:8px; font-size:13px; font-weight:500;">
                🤖 Gemini 2.5 Flash
            </span>
            <span style="background:#1e293b; border:1px solid #334155; color:#94a3b8;
                         padding:6px 14px; border-radius:8px; font-size:13px; font-weight:500;">
                🐍 Python 3.10+
            </span>
            <span style="background:#1e293b; border:1px solid #334155; color:#94a3b8;
                         padding:6px 14px; border-radius:8px; font-size:13px; font-weight:500;">
                👁️ OpenCV
            </span>
            <span style="background:#1e293b; border:1px solid #334155; color:#94a3b8;
                         padding:6px 14px; border-radius:8px; font-size:13px; font-weight:500;">
                📊 NumPy + SciPy
            </span>
            <span style="background:#1e293b; border:1px solid #334155; color:#94a3b8;
                         padding:6px 14px; border-radius:8px; font-size:13px; font-weight:500;">
                🎨 Gradio
            </span>
            <span style="background:#1e293b; border:1px solid #334155; color:#94a3b8;
                         padding:6px 14px; border-radius:8px; font-size:13px; font-weight:500;">
                🗄️ SQLite
            </span>
        </div>
    </div>

    <!-- Sınırlamalar -->
    <div style="
        background: linear-gradient(135deg, #1c0a0a, #0f172a);
        border: 1px solid #7f1d1d44;
        border-radius: 16px;
        padding: 24px 28px;
    ">
        <div style="color:#fca5a5; font-size:13px; font-weight:700; letter-spacing:1px;
                    text-transform:uppercase; margin-bottom:14px;">⚠️ Sınırlamalar</div>
        <ul style="list-style:none; padding:0; margin:0; color:#94a3b8; font-size:14px; line-height:2;">
            <li>▸ Yeni nesil modeller (Imagen 3, Flux, Midjourney v6) watermark'sız olduğunda tespit zorlaşabilir</li>
            <li>▸ Sonuçlar %100 kesin değildir; karar destek aracı olarak kullanılmalıdır</li>
            <li>▸ Gemini API ücretsiz tier'da dakikada 10 istek sınırı mevcuttur</li>
        </ul>
    </div>
</div>
"""

DEVELOPER_HTML = f"""
<div style="
    padding: 80px 24px;
    text-align: center;
    position: relative;
    overflow: hidden;
">
    <!-- Background glow -->
    <div style="
        position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
        width: 500px; height: 300px;
        background: radial-gradient(ellipse, #6366f10a 0%, transparent 70%);
        pointer-events: none;
    "></div>

    <div style="
        display: inline-block;
        background: linear-gradient(135deg, #22c55e20, #06b6d420);
        border: 1px solid #22c55e30;
        border-radius: 999px;
        padding: 5px 16px;
        font-size: 11px; font-weight: 700; color: #4ade80;
        letter-spacing: 2px; text-transform: uppercase;
        margin-bottom: 24px;
    ">Geliştirici</div>

    <!-- Avatar placeholder -->
    <div style="
        width: 96px; height: 96px;
        background: linear-gradient(135deg, #6366f1, #8b5cf6, #ec4899);
        border-radius: 50%;
        margin: 0 auto 20px;
        display: flex; align-items: center; justify-content: center;
        font-size: 42px;
        box-shadow: 0 0 40px #6366f144;
        animation: floatY 4s ease-in-out infinite;
    ">👨‍💻</div>

    <h2 style="font-size:28px; font-weight:800; color:#e2e8f0; margin-bottom:8px;">
        Enes Sarpün
    </h2>
    <p style="color:#64748b; font-size:15px; margin-bottom:32px; max-width:440px; margin-left:auto; margin-right:auto; line-height:1.6;">
        Python & AI/ML geliştirici. LLM agent'ları, forensic analiz ve açık kaynak araçlar üzerine çalışıyor.
    </p>

    <!-- Linkler -->
    <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap;">
        <a href="{GITHUB_URL}" target="_blank" style="
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 1px solid #334155;
            color: #94a3b8;
            padding: 10px 22px;
            border-radius: 10px;
            font-size: 14px; font-weight: 600;
            text-decoration: none;
            display: flex; align-items: center; gap: 8px;
            transition: all 0.2s ease;
        " onmouseover="this.style.borderColor='#6366f1';this.style.color='#a5b4fc'"
           onmouseout="this.style.borderColor='#334155';this.style.color='#94a3b8'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            GitHub
        </a>
        <a href="mailto:kingmazlum4321@gmail.com" style="
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 1px solid #334155;
            color: #94a3b8;
            padding: 10px 22px;
            border-radius: 10px;
            font-size: 14px; font-weight: 600;
            text-decoration: none;
            display: flex; align-items: center; gap: 8px;
            transition: all 0.2s ease;
        " onmouseover="this.style.borderColor='#ec4899';this.style.color='#f9a8d4'"
           onmouseout="this.style.borderColor='#334155';this.style.color='#94a3b8'">
            ✉️ İletişim
        </a>
    </div>
</div>
"""

GITHUB_CTA_HTML = f"""
<div style="
    padding: 72px 24px 80px;
    text-align: center;
    position: relative;
    overflow: hidden;
">
    <!-- Background glow -->
    <div style="
        position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
        width: 600px; height: 400px;
        background: radial-gradient(ellipse, #6366f10d 0%, transparent 65%);
        pointer-events: none;
    "></div>

    <div style="position:relative;">
        <h2 style="font-size:36px; font-weight:800; color:#e2e8f0; margin-bottom:12px; letter-spacing:-0.5px;">
            Açık Kaynak
        </h2>
        <p style="color:#64748b; font-size:16px; margin-bottom:36px; max-width:480px; margin-left:auto; margin-right:auto; line-height:1.6;">
            Tüm kaynak kodu GitHub'da mevcut. Katkıda bulun, fork edin veya kendi projelerinizde kullanın.
        </p>

        <a href="{GITHUB_URL}" target="_blank" style="
            display: inline-flex;
            align-items: center;
            gap: 12px;
            background: linear-gradient(135deg, #6366f1, #8b5cf6, #ec4899);
            background-size: 200% 200%;
            animation: gradientShift 4s ease infinite;
            color: white;
            padding: 18px 48px;
            border-radius: 16px;
            font-size: 18px;
            font-weight: 700;
            text-decoration: none;
            box-shadow: 0 8px 40px #6366f155;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            letter-spacing: 0.2px;
        " onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 16px 60px #6366f177'"
           onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 8px 40px #6366f155'">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            GitHub'da İncele
        </a>

        <!-- Repo URL -->
        <div style="margin-top:20px; color:#334155; font-size:13px; font-family:monospace;">
            github.com/Enes-Sarpun/Image-Agent
        </div>
    </div>
</div>
"""

FOOTER_HTML = """
<div style="
    border-top: 1px solid #0f172a;
    padding: 28px 24px;
    text-align: center;
    color: #1e293b;
    font-size: 13px;
">
    <span style="color:#334155;">© 2025 Image Agent · Enes Sarpün · MIT Lisansı</span>
    &nbsp;·&nbsp;
    <span style="color:#1e3a5f;">Gemini Vision ile güçlendirildi</span>
</div>
"""

DIVIDER_HTML = """<hr style="border:none;height:1px;
background:linear-gradient(90deg,transparent,#1e293b,transparent);margin:0;">"""


# ══════════════════════════════════════════════════════════════
# GRADIO ARAYÜZÜ
# ══════════════════════════════════════════════════════════════

with gr.Blocks(
    title="Image Agent — AI Görsel Tespiti",
    css=CUSTOM_CSS,
    theme=gr.themes.Base(
        primary_hue="violet",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
    ),
) as demo:

    # ── HERO ────────────────────────────────────────────────────
    gr.HTML(HERO_HTML)

    # ── YÜKLEME + SONUÇ ─────────────────────────────────────────
    with gr.Row(equal_height=False):

        # Sol: Yükleme
        with gr.Column(scale=1, min_width=320):
            image_input = gr.Image(
                label="",
                type="numpy",
                elem_classes=["upload-area"],
                height=300,
            )
            use_cache_checkbox = gr.Checkbox(
                label="💾 Cache kullan — aynı görsel tekrar analiz edilmez",
                value=True,
            )
            analyze_btn = gr.Button(
                "🔍  Analiz Et",
                variant="primary",
                elem_classes=["analyze-btn"],
                size="lg",
            )
            gr.HTML(
                "<div style='color:#334155; font-size:12px; margin-top:10px; text-align:center;'>"
                "JPG &nbsp;·&nbsp; PNG &nbsp;·&nbsp; GIF &nbsp;·&nbsp; WEBP"
                "</div>"
            )

        # Sağ: Sonuçlar
        with gr.Column(scale=2):
            verdict_out = gr.HTML(
                value="<div style='color:#1e293b; padding:40px; text-align:center; "
                      "font-family:Inter,sans-serif; font-size:15px;'>"
                      "Görsel yükleyin ve <b style=\"color:#334155\">Analiz Et</b> butonuna basın.</div>"
            )
            reasoning_out = gr.HTML(value="")

    # ── FORENSIC DETAYLAR ────────────────────────────────────────
    with gr.Accordion("🔬 Forensic Detaylar", open=False):
        gr.HTML(
            "<div style='color:#475569; font-size:13px; margin-bottom:14px; padding: 4px 0;'>"
            "ELA: Sıkıştırma tutarsızlıkları &nbsp;·&nbsp; "
            "FFT: Frekans domain imzası &nbsp;·&nbsp; "
            "Edge: Kenar yoğunluk haritası"
            "</div>"
        )
        with gr.Row():
            ela_out  = gr.Image(label="ELA", height=220, elem_classes=["forensic-img"])
            fft_out  = gr.Image(label="FFT Magnitude", height=220, elem_classes=["forensic-img"])
            edge_out = gr.Image(label="Edge Density Map", height=220, elem_classes=["forensic-img"])

    # ── ANALİZ GEÇMİŞİ ──────────────────────────────────────────
    with gr.Accordion("📋 Analiz Geçmişi", open=False):
        history_table = gr.Dataframe(
            headers=["Tahmin", "Güven", "Kaynak", "Zaman", "Gerekçe (özet)"],
            datatype=["str", "str", "str", "str", "str"],
            value=_get_cache_history(),
            interactive=False,
            wrap=True,
        )
        refresh_btn = gr.Button("🔄 Yenile", size="sm", variant="secondary")

    # ── BÖLÜM AYRAÇLARI + SCROLL BÖLÜMLER ───────────────────────
    gr.HTML(DIVIDER_HTML)
    gr.HTML(HOW_IT_WORKS_HTML)
    gr.HTML(DIVIDER_HTML)
    gr.HTML(ABOUT_HTML)
    gr.HTML(DIVIDER_HTML)
    gr.HTML(DEVELOPER_HTML)
    gr.HTML(DIVIDER_HTML)
    gr.HTML(GITHUB_CTA_HTML)
    gr.HTML(FOOTER_HTML)

    # ── BAĞLANTILAR ─────────────────────────────────────────────
    analyze_btn.click(
        fn=analyze_image,
        inputs=[image_input, use_cache_checkbox],
        outputs=[verdict_out, reasoning_out, ela_out, fft_out, edge_out, history_table],
    )
    refresh_btn.click(
        fn=refresh_history,
        inputs=[],
        outputs=[history_table],
    )


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import socket

    def _find_free_port(start: int = 7860, end: int = 7880) -> int:
        for port in range(start, end):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        raise OSError(f"{start}-{end} aralığında boş port bulunamadı.")

    port = _find_free_port()
    print(f"\n  [Image Agent] Web arayüzü başlatılıyor...")
    print(f"  >> http://127.0.0.1:{port}\n")
    demo.launch(
        server_name="127.0.0.1",
        server_port=port,
        inbrowser=True,
        show_error=True,
    )
