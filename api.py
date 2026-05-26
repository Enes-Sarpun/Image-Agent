import os
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent import ImageAgent
from config import SUPPORTED_FORMATS

MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB
MAX_DIMENSION = 4096

agent: ImageAgent


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Get a free key at https://aistudio.google.com/apikey"
        )
    global agent
    agent = ImageAgent()
    yield


app = FastAPI(
    title="Image Agent API",
    description="Detect AI-generated images via a 6-layer analysis pipeline.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(image: UploadFile = File(...), use_cache: bool = Form(True)):
    contents = image.file.read()

    if len(contents) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size: 20MB")

    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported format. Supported: {', '.join(SUPPORTED_FORMATS.keys())}",
        )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            tmp_path = Path(tmp.name)

        try:
            with Image.open(tmp_path) as img:
                img.verify()
        except (UnidentifiedImageError, Exception):
            raise HTTPException(status_code=422, detail="Unsupported or corrupted image file")

        try:
            with Image.open(tmp_path) as img:
                w, h = img.size
        except Exception:
            raise HTTPException(status_code=422, detail="Could not read image dimensions")

        if w > MAX_DIMENSION or h > MAX_DIMENSION:
            raise HTTPException(
                status_code=422,
                detail=f"Image too large. Maximum resolution: {MAX_DIMENSION}x{MAX_DIMENSION}px",
            )

        try:
            result = agent.analyze(tmp_path, use_cache=use_cache)
        except Exception as e:
            raise HTTPException(status_code=500, detail={"error": "Analysis failed", "detail": str(e)})

        return JSONResponse(content={
            "verdict": result.verdict,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "key_indicators": result.key_indicators,
            "source": result.source,
            "elapsed_ms": result.elapsed_ms,
        })

    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


# Static files — mount AFTER all API routes
app.mount("/", StaticFiles(directory=str(PROJECT_ROOT), html=True), name="static")
