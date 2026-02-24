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
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _migrate_old_schema_if_needed(self, conn: sqlite3.Connection) -> None:
        """Migrate from old schema with last_updated and archived columns."""
        cursor = conn.cursor()
        
        # Check if old columns exist
        cursor.execute("PRAGMA table_info(model_benchmarks)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'last_updated' not in columns and 'archived' not in columns:
            # Already migrated
            return
        
        print(f"Migrating old schema with columns: {columns}")
        
        # Drop view first (depends on old table)
        cursor.execute("DROP VIEW IF EXISTS router_compatibility_view")
        
        # Create new table without old columns
        cursor.execute("""
        CREATE TABLE model_benchmarks_new (
            model_id TEXT PRIMARY KEY,
            reasoning_score REAL,
            coding_score REAL,
            general_score REAL,
            elo_rating INTEGER
        )
        """)
        
        # Copy data, ignoring last_updated and archived columns
        cursor.execute("""
        INSERT INTO model_benchmarks_new 
        (model_id, reasoning_score, coding_score, general_score, elo_rating)
        SELECT model_id, reasoning_score, coding_score, general_score, elo_rating
        FROM model_benchmarks
        """)
        
        # Drop old table
        cursor.execute("DROP TABLE model_benchmarks")
        
        # Rename new table
        cursor.execute("ALTER TABLE model_benchmarks_new RENAME TO model_benchmarks")
        
        # Recreate index
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_id ON model_benchmarks(model_id)")
        
        print("Migration completed successfully")

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        """Create schema matching RouterEngine expectations."""
        self._migrate_old_schema_if_needed(conn)
        cursor = conn.cursor()
        
        # PRIMARY TABLE: model_benchmarks - Exact schema RouterEngine expects
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_benchmarks (
            model_id TEXT PRIMARY KEY,
            reasoning_score REAL,
            coding_score REAL,
            general_score REAL,
            elo_rating INTEGER
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
            NULL as last_updated,
            0 as archived
        FROM model_benchmarks
        """)
    
    # ==================== MODEL BENCHMARKS ====================
    
    def upsert_benchmark(self, model_id: str, reasoning_score: float = 0.0,
                        coding_score: float = 0.0, general_score: float = 0.0,
                        elo_rating: int = 1000) -> None:
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
            (model_id, reasoning_score, coding_score, general_score, elo_rating)
            VALUES (?, ?, ?, ?, ?)
            """, (sanitized_id, validated_reasoning, validated_coding, validated_general, validated_elo))
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
        
        # FIXED: Use parameterized query with tuple expansion to prevent SQL injection
        placeholders = ','.join(['?'] * len(model_ids))
        query = f"SELECT * FROM model_benchmarks WHERE model_id IN ({placeholders})"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, model_ids)
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
            
            cursor.execute("SELECT COUNT(*) as c FROM aliases")
            aliases = cursor.fetchone()['c']
            return {'total_models': models, 'total_aliases': aliases}
    
    def get_all_model_ids(self) -> set[str]:
        """Get all model IDs currently in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT model_id FROM model_benchmarks")
            return {row[0] for row in cursor.fetchall()}
