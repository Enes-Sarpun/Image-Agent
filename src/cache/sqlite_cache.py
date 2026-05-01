"""
SQLite Cache: Analiz sonuçlarını saklar.
Aynı görsel tekrar geldiğinde önbellekten döner.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional

from config import DB_PATH
from result import AnalysisResult


class SQLiteCache:
    """Görsel hash → analiz sonucu önbelleği."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Tabloyu oluştur."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    image_hash TEXT PRIMARY KEY,
                    verdict TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    reasoning TEXT,
                    key_indicators TEXT,
                    source TEXT,
                    timestamp TEXT,
                    raw_response TEXT
                )
            """)
            conn.commit()

    def get(self, image_hash: str) -> Optional[AnalysisResult]:
        """Hash ile önbellekten sonuç al, yoksa None."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM analysis_cache WHERE image_hash = ?",
                (image_hash,)
            ).fetchone()

        if not row:
            return None

        return AnalysisResult(
            verdict=row[1],
            confidence=row[2],
            reasoning=row[3] or "",
            key_indicators=json.loads(row[4]) if row[4] else [],
            source="cache",  # Cache'den geldi olarak işaretle
            timestamp=row[6] or "",
            raw_response=row[7] or "",
        )

    def set(self, image_hash: str, result: AnalysisResult):
        """Sonucu önbelleğe yaz."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO analysis_cache
                (image_hash, verdict, confidence, reasoning, 
                 key_indicators, source, timestamp, raw_response)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image_hash,
                result.verdict,
                result.confidence,
                result.reasoning,
                json.dumps(result.key_indicators, ensure_ascii=False),
                result.source,
                result.timestamp,
                result.raw_response,
            ))
            conn.commit()

    def clear(self):
        """Tüm önbelleği temizle."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM analysis_cache")
            conn.commit()

    def size(self) -> int:
        """Cache'deki kayıt sayısı."""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM analysis_cache"
            ).fetchone()[0]
        

        