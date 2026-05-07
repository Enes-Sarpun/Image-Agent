"""
Image Agent — Gradio Web Arayüzü

Başlatmak için:
    python app.py
"""

import sys

# Windows konsolunun cp1254 encoding'i agent.py içindeki
# Unicode karakterleri (✓, ⚠ vb.) yazarken hata veriyor.
# Stdout/stderr'i UTF-8'e yönlendiriyoruz.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import sqlite3
import json
import warnings
from pathlib import Path
from io import BytesIO

# ─── Proje kökünü path'e ekle ─────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import gradio as gr
from PIL import Image

# ─── FutureWarning'i bastır (deprecated google-generativeai) ──
warnings.filterwarnings("ignore", category=FutureWarning, module="google")

from agent import ImageAgent  # noqa: E402
from config import DB_PATH    # noqa: E402

# ─── Agent (singleton) ───────────────────────────────────
agent = ImageAgent()


# ══════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ══════════════════════════════════════════════════════════════

def _pil_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _get_cache_history(limit: int = 10) -> list[list]:
    """Cache'den son analizleri çek."""
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
    """Verdict + confidence'a göre hex renk."""
    if verdict == "ai":
        if confidence >= 80:
            return "#ef4444"   # kırmızı
        elif confidence >= 60:
            return "#f97316"   # turuncu
        else:
            return "#eab308"   # sarı
    else:
        if confidence >= 80:
            return "#22c55e"   # yeşil
        elif confidence >= 60:
            return "#84cc16"   # lime
        else:
            return "#eab308"   # sarı


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
    <div style="
        background: linear-gradient(135deg, #1e1e2e 0%, #16213e 100%);
        border: 2px solid {color};
        border-radius: 16px;
        padding: 28px 32px;
        font-family: 'Segoe UI', sans-serif;
        box-shadow: 0 0 24px {color}44;
    ">
        <div style="display:flex; align-items:center; gap:16px; margin-bottom:20px;">
            <span style="font-size:48px;">{icon}</span>
            <div>
                <div style="color:{color}; font-size:28px; font-weight:800; letter-spacing:1px;">{label}</div>
                <div style="color:#94a3b8; font-size:14px; margin-top:4px;">{source_label} &nbsp;·&nbsp; ⚡ {elapsed_ms:.0f} ms</div>
            </div>
        </div>

        <div style="margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                <span style="color:#cbd5e1; font-size:14px; font-weight:600;">GÜVEN SKORU</span>
                <span style="color:{color}; font-size:18px; font-weight:800;">%{confidence:.1f}</span>
            </div>
            <div style="background:#334155; border-radius:999px; height:10px; overflow:hidden;">
                <div style="
                    width:{bar_pct}%;
                    height:100%;
                    background:linear-gradient(90deg, {color}88, {color});
                    border-radius:999px;
                    transition: width 0.5s ease;
                "></div>
            </div>
        </div>
    </div>
    """


def _build_reasoning_html(reasoning: str, indicators: list[str]) -> str:
    indicators_html = "".join(
        f'<li style="margin-bottom:6px; color:#cbd5e1;">{ind}</li>'
        for ind in indicators
        if ind and not ind.startswith("Calibration:")
    )
    calibration_items = [i for i in indicators if i.startswith("Calibration:")]
    cal_html = ""
    if calibration_items:
        cal_html = f"""
        <div style="margin-top:16px; padding:10px 16px; background:#1e293b;
                    border-left:3px solid #6366f1; border-radius:6px;">
            <div style="color:#6366f1; font-size:12px; font-weight:700; margin-bottom:4px;">⚖️ KALİBRASYON</div>
            <div style="color:#94a3b8; font-size:13px;">{calibration_items[0]}</div>
        </div>
        """

    return f"""
    <div style="
        background:#0f172a;
        border:1px solid #334155;
        border-radius:12px;
        padding:20px 24px;
        font-family:'Segoe UI', sans-serif;
    ">
        <div style="color:#e2e8f0; font-size:14px; line-height:1.7; margin-bottom:16px;">
            <span style="color:#94a3b8; font-size:12px; font-weight:700; display:block; margin-bottom:6px;">💭 GEREKÇE</span>
            {reasoning}
        </div>

        {'<div><span style="color:#94a3b8; font-size:12px; font-weight:700; display:block; margin-bottom:8px;">🔍 ANAHTAR İPUÇLARI</span><ul style="margin:0; padding-left:20px;">' + indicators_html + '</ul></div>' if indicators_html else ''}
        {cal_html}
    </div>
    """


# ══════════════════════════════════════════════════════════════
# ANA ANALİZ FONKSİYONU
# ══════════════════════════════════════════════════════════════

def analyze_image(image, use_cache: bool):
    """Gradio'dan çağrılan ana analiz fonksiyonu."""
    if image is None:
        return (
            "<div style='color:#ef4444;padding:20px;'>⚠️ Lütfen bir görsel yükleyin.</div>",
            "<div></div>",
            None, None, None,
            _get_cache_history(),
        )

    # Geçici dosyaya kaydet (agent dosya yolu bekliyor)
    tmp_path = PROJECT_ROOT / "data" / "_tmp_upload.png"
    tmp_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(image, str):
        # Gradio bazen dosya yolu verir
        pil_img = Image.open(image)
    else:
        pil_img = Image.fromarray(image)

    pil_img.save(tmp_path, format="PNG")

    try:
        result = agent.analyze(tmp_path, use_cache=use_cache)
    except Exception as e:
        return (
            f"<div style='color:#ef4444;padding:20px;'>❌ Analiz hatası: {e}</div>",
            "<div></div>",
            None, None, None,
            _get_cache_history(),
        )

    # ── Forensic görüntüleri üret ──────────────────────────────
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
# GRADIO ARAYÜZÜ
# ══════════════════════════════════════════════════════════════

CUSTOM_CSS = """
/* ── Genel arka plan ── */
body, .gradio-container {
    background: #0a0f1e !important;
    color: #e2e8f0 !important;
    font-family: 'Segoe UI', system-ui, sans-serif !important;
}

/* ── Başlık bölümü ── */
#header-area {
    text-align: center;
    padding: 32px 0 8px;
}

/* ── Upload alanı ── */
.upload-area .wrap {
    border: 2px dashed #334155 !important;
    border-radius: 16px !important;
    background: #0f172a !important;
    transition: border-color 0.2s;
}
.upload-area .wrap:hover {
    border-color: #6366f1 !important;
}

/* ── Butonlar ── */
.analyze-btn {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 16px !important;
    padding: 12px 32px !important;
    transition: transform 0.1s, box-shadow 0.2s !important;
    box-shadow: 0 4px 20px #6366f144 !important;
}
.analyze-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px #6366f188 !important;
}

/* ── Panel arka planları ── */
.gr-panel, .gr-box {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 12px !important;
}

/* ── Forensic image gallery ── */
.forensic-gallery img {
    border-radius: 8px !important;
    border: 1px solid #1e293b !important;
}

/* ── Tablo (geçmiş) ── */
.gr-dataframe table {
    background: #0f172a !important;
    color: #cbd5e1 !important;
}
.gr-dataframe th {
    background: #1e293b !important;
    color: #94a3b8 !important;
}
.gr-dataframe tr:hover {
    background: #1e293b44 !important;
}

/* ── Accordion ── */
.gr-accordion {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 12px !important;
}
"""

with gr.Blocks(
    title="Image Agent — AI Gorsel Tespiti",
) as demo:

    # ── Başlık ──────────────────────────────────────────────────
    gr.HTML("""
    <div id="header-area">
        <div style="font-size:40px; margin-bottom:8px;">🔍</div>
        <h1 style="color:#e2e8f0; font-size:32px; font-weight:800; margin:0; letter-spacing:-0.5px;">
            Image Agent
        </h1>
        <p style="color:#64748b; font-size:15px; margin-top:8px;">
            Gemini Vision · Forensic Analiz · Multi-Pass Reasoning
        </p>
        <div style="width:60px; height:3px; background:linear-gradient(90deg,#6366f1,#8b5cf6);
                    border-radius:999px; margin:16px auto 0;"></div>
    </div>
    """)

    # ── Ana içerik ───────────────────────────────────────────────
    with gr.Row(equal_height=False):

        # Sol kolon: Yükleme + Kontroller
        with gr.Column(scale=1, min_width=340):
            gr.Markdown("### 📂 Görsel Yükle")

            image_input = gr.Image(
                label="",
                type="numpy",
                elem_classes=["upload-area"],
                height=280,
            )

            use_cache_checkbox = gr.Checkbox(
                label="💾 Cache kullan (aynı görsel tekrar analiz edilmez)",
                value=True,
            )

            analyze_btn = gr.Button(
                "🔍  Analiz Et",
                variant="primary",
                elem_classes=["analyze-btn"],
                size="lg",
            )

            gr.Markdown(
                "<div style='color:#475569; font-size:12px; margin-top:8px;'>"
                "Desteklenen formatlar: JPG · PNG · GIF · WEBP"
                "</div>"
            )

        # Sağ kolon: Sonuçlar
        with gr.Column(scale=2):
            gr.Markdown("### 📊 Analiz Sonucu")

            verdict_html = gr.HTML(
                value="<div style='color:#475569; padding:20px; text-align:center;'>"
                      "Görsel yükleyin ve <b>Analiz Et</b> butonuna basın.</div>"
            )

            reasoning_html = gr.HTML(value="")

    # ── Forensic Detaylar (Accordion) ───────────────────────────
    with gr.Accordion("🔬 Forensic Detaylar", open=False):
        gr.Markdown(
            "<div style='color:#64748b; font-size:13px; margin-bottom:12px;'>"
            "ELA: Sıkıştırma tutarsızlığı &nbsp;·&nbsp; "
            "FFT: Frekans imzası &nbsp;·&nbsp; "
            "Edge: Kenar yoğunluğu"
            "</div>"
        )
        with gr.Row():
            ela_output  = gr.Image(label="ELA (Error Level Analysis)", height=220, elem_classes=["forensic-gallery"])
            fft_output  = gr.Image(label="FFT Magnitude", height=220, elem_classes=["forensic-gallery"])
            edge_output = gr.Image(label="Edge Density Map", height=220, elem_classes=["forensic-gallery"])

    # ── Geçmiş Paneli ────────────────────────────────────────────
    with gr.Accordion("📋 Analiz Geçmişi (Cache)", open=False):
        history_table = gr.Dataframe(
            headers=["Tahmin", "Güven", "Kaynak", "Zaman", "Gerekçe (özet)"],
            datatype=["str", "str", "str", "str", "str"],
            value=_get_cache_history(),
            interactive=False,
            wrap=True,
        )
        refresh_btn = gr.Button("🔄 Yenile", size="sm", variant="secondary")

    # ── Bağlantılar ─────────────────────────────────────────────
    analyze_btn.click(
        fn=analyze_image,
        inputs=[image_input, use_cache_checkbox],
        outputs=[
            verdict_html,
            reasoning_html,
            ela_output,
            fft_output,
            edge_output,
            history_table,
        ],
    )

    refresh_btn.click(
        fn=refresh_history,
        inputs=[],
        outputs=[history_table],
    )


# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import socket

    def _find_free_port(start: int = 7860, end: int = 7880) -> int:
        """Belirtilen aralıkta kullanılmayan ilk portu döndürür."""
        for port in range(start, end):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        raise OSError(f"{start}-{end} aralığında bos port bulunamadi.")

    port = _find_free_port()
    print(f"\n  [Image Agent] Web arayuzu baslatiliyor...")
    print(f"  >> http://127.0.0.1:{port}\n")
    demo.launch(
        server_name="127.0.0.1",
        server_port=port,
        inbrowser=True,
        show_error=True,
        css=CUSTOM_CSS,
        theme=gr.themes.Base(
            primary_hue="violet",
            neutral_hue="slate",
            font=gr.themes.GoogleFont("Inter"),
        ),
    )
