"""
SQLite database for provider.db.
Standalone database for external model benchmarks.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager
import json
from datetime import datetime, timezone
from datetime import datetime

from .models import ModelBenchmark, AliasRecord, Metadata


class ProviderDB:
    """
    Interface to provider.db - a standalone SQLite database containing
    benchmark data for remote/cloud models.
    """
    
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        
    def initialize(self) -> None:
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            self._create_schema(conn)
            # Handle migrations for existing databases
            self._migrate_schema(conn)
            conn.commit()
    
    def _migrate_schema(self, conn: sqlite3.Connection) -> None:
        """Migrate existing database to add new columns."""
        cursor = conn.cursor()
        
        # Add archived column if it doesn't exist
        cursor.execute("PRAGMA table_info(model_benchmarks)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'archived' not in columns:
            cursor.execute("ALTER TABLE model_benchmarks ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _create_schema(self, conn: sqlite3.Connection) -> None:
        """Create schema matching RouterEngine expectations."""
        cursor = conn.cursor()
        
        # PRIMARY TABLE: model_benchmarks
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_benchmarks (
            model_id TEXT PRIMARY KEY,
            reasoning_score REAL NOT NULL DEFAULT 0.0,
            coding_score REAL NOT NULL DEFAULT 0.0,
            general_score REAL NOT NULL DEFAULT 0.0,
            elo_rating INTEGER NOT NULL DEFAULT 1000,
            last_updated TIMESTAMP NOT NULL,
            archived INTEGER NOT NULL DEFAULT 0
        )
        """)
        
        # Index for fast lookup
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_id ON model_benchmarks(model_id)")
        
        # Alias table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS aliases (
            alias TEXT PRIMARY KEY,
            canonical_id TEXT NOT NULL,
            confidence REAL DEFAULT 1.0
        )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alias ON aliases(alias)")
        
        # Metadata table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)
        
        # Compatibility View: Aliases model_id as ollama_name
        # This allows SmarterRouter to query provider.db using its existing schema expectations
        cursor.execute("""
        CREATE VIEW IF NOT EXISTS router_compatibility_view AS
        SELECT 
            model_id as ollama_name,
            reasoning_score,
            coding_score,
            general_score,
            elo_rating,
            last_updated,
            archived
        FROM model_benchmarks
        """)
    
    # ==================== MODEL BENCHMARKS ====================
    
    def upsert_benchmark(self, model_id: str, reasoning_score: float = 0.0,
                        coding_score: float = 0.0, general_score: float = 0.0,
                        elo_rating: int = 1000, archived: bool = False) -> None:
        """Insert or update a model benchmark with validation."""
        from .utils import sanitize_model_id, validate_score_range, validate_elo_rating
        
        # Sanitize model_id to prevent injection
        sanitized_id = sanitize_model_id(model_id)
        
        # Validate scores are in proper range
        validated_reasoning = validate_score_range(reasoning_score, "reasoning_score")
        validated_coding = validate_score_range(coding_score, "coding_score")
        validated_general = validate_score_range(general_score, "general_score")
        validated_elo = validate_elo_rating(elo_rating)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO model_benchmarks
            (model_id, reasoning_score, coding_score, general_score, elo_rating, last_updated, archived)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sanitized_id, validated_reasoning, validated_coding, validated_general, validated_elo, datetime.now(timezone.utc), int(archived)))
            conn.commit()
    
    def get_benchmark(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get benchmark for a single model."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM model_benchmarks WHERE model_id = ?", (model_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_benchmarks_for_models(self, model_ids: list[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get benchmarks for multiple models.
        This is the KEY method RouterEngine will call!
        
        Returns: {model_id: {reasoning_score, coding_score, general_score, elo_rating}}
        """
        if not model_ids:
            return {}
        
        placeholders = ','.join('?' * len(model_ids))
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM model_benchmarks WHERE model_id IN ({placeholders})", model_ids)
            return {row['model_id']: dict(row) for row in cursor.fetchall()}
    
    def list_all_benchmarks(self) -> list[Dict[str, Any]]:
        """List all model benchmarks."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM model_benchmarks")
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== ALIASES ====================
    
    def upsert_alias(self, alias: str, canonical_id: str, confidence: float = 1.0) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO aliases (alias, canonical_id, confidence) VALUES (?, ?, ?)",
                          (alias, canonical_id, confidence))
            conn.commit()
    
    def get_canonical_id(self, alias: str) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT canonical_id FROM aliases WHERE alias = ?", (alias,))
            row = cursor.fetchone()
            return row['canonical_id'] if row else None
    
    # ==================== METADATA ====================
    
    def set_metadata(self, key: str, value: Any) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                          (key, json.dumps(value) if isinstance(value, (dict, list)) else str(value)))
            conn.commit()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM metadata WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row['value'])
                except (json.JSONDecodeError, TypeError):
                    return row['value']
            return default
    
    def vacuum(self) -> None:
        with self._get_connection() as conn:
            conn.execute("VACUUM")
    
    def get_stats(self) -> Dict[str, int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as c FROM model_benchmarks")
            models = cursor.fetchone()['c']
            
            # Handle databases without archived column
            try:
                cursor.execute("SELECT COUNT(*) as c FROM model_benchmarks WHERE archived = 1")
                archived = cursor.fetchone()['c']
            except sqlite3.OperationalError:
                archived = 0
            
            cursor.execute("SELECT COUNT(*) as c FROM aliases")
            aliases = cursor.fetchone()['c']
            return {'total_models': models, 'archived_models': archived, 'total_aliases': aliases}
    
    def get_active_model_ids(self) -> set[str]:
        """Get all non-archived model IDs currently in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Handle databases without archived column
            try:
                cursor.execute("SELECT model_id FROM model_benchmarks WHERE archived = 0")
            except sqlite3.OperationalError:
                cursor.execute("SELECT model_id FROM model_benchmarks")
            return {row[0] for row in cursor.fetchall()}
    
    def archive_model(self, model_id: str) -> None:
        """Mark a model as archived (no longer in OpenRouter)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE model_benchmarks SET archived = 1 WHERE model_id = ?", (model_id,))
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Column doesn't exist in old databases
    
    def unarchive_model(self, model_id: str) -> None:
        """Mark a model as active (back in OpenRouter)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE model_benchmarks SET archived = 0 WHERE model_id = ?", (model_id,))
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Column doesn't exist in old databases
            conn.commit()
