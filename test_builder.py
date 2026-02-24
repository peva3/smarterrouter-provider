#!/usr/bin/env python3
"""
Quick test to verify provider.db builder components work.
This tests database creation, schema, and basic operations without fetching real data.
"""

import tempfile
import sqlite3
from pathlib import Path
import sys

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

from router.provider_db.database import ProviderDB
from router.provider_db.models import ModelInfo, BenchmarkRecord, AliasRecord
from datetime import datetime


def test_database_schema():
    """Test that database schema creates correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = ProviderDB(db_path)
        db.initialize()
        
        # Check tables exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        expected = ['models', 'benchmarks', 'aliases', 'metadata']
        
        assert set(tables) == set(expected), f"Missing tables. Got: {tables}"
        print("✓ Schema created successfully")
        
        # Test model insert
        model = ModelInfo(
            id="openai/gpt-4-test",
            name="GPT-4 Test",
            provider="openai",
            context_length=8192,
            prompt_cost=0.00001,
            completion_cost=0.00003,
            supports_vision=True
        )
        db.upsert_model(model)
        
        retrieved = db.get_model("openai/gpt-4-test")
        assert retrieved is not None
        assert retrieved.name == "GPT-4 Test"
        assert retrieved.prompt_cost == 0.00001
        print("✓ Model CRUD works")
        
        # Test benchmark insert
        bench = BenchmarkRecord(
            model_id="openai/gpt-4-test",
            source="arena_ai",
            category="overall",
            score=0.85,
            raw_score=1250,
            sample_size=1000
        )
        db.upsert_benchmark(bench)
        
        benchmarks = db.get_benchmarks("openai/gpt-4-test")
        assert len(benchmarks) == 1
        assert benchmarks[0].score == 0.85
        print("✓ Benchmark CRUD works")
        
        # Test alias
        alias = AliasRecord(alias="gpt4", canonical_id="openai/gpt-4-test", confidence=1.0)
        db.upsert_alias(alias)
        
        canonical = db.get_canonical_id("gpt4")
        assert canonical == "openai/gpt-4-test"
        print("✓ Alias lookup works")
        
        # Test metadata
        db.set_metadata("test_key", {"nested": "value"})
        value = db.get_metadata("test_key")
        assert value == {"nested": "value"}
        print("✓ Metadata works")
        
        conn.close()
        print("\nAll database tests passed!")


def test_normalizer():
    """Test score normalization."""
    from router.provider_db.normalizer import ScoreNormalizer, calculate_composite_score
    
    normalizer = ScoreNormalizer()
    
    records = [
        BenchmarkRecord("m1", "arena", "overall", 0.0, 1100, 1000, datetime.utcnow()),
        BenchmarkRecord("m1", "arena", "overall", 0.0, 1300, 1000, datetime.utcnow()),
        BenchmarkRecord("m2", "swe_bench", "swe_resolved", 0.0, 50, 500, datetime.utcnow()),
        BenchmarkRecord("m2", "swe_bench", "swe_resolved", 0.0, 70, 500, datetime.utcnow()),
    ]
    
    normalized = normalizer.normalize_scores(records)
    
    # Check scores are 0-1
    for r in normalized:
        assert 0 <= r.score <= 1, f"Score {r.score} out of range"
    
    print(f"✓ Normalized {len(records)} records to 0-1 range")
    
    # Test composite score
    composite = calculate_composite_score(normalized)
    assert 0 <= composite <= 1
    print(f"✓ Composite quality score: {composite:.3f}")


def test_builder_initialization():
    """Test Builder class can be instantiated."""
    from router.provider_db.builder import Builder
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "builder_test.db"
        builder = Builder(db_path)
        assert builder.db_path == db_path.absolute()
        print("✓ Builder initialization works")


if __name__ == "__main__":
    print("Running provider.db builder tests...\n")
    
    try:
        test_database_schema()
        print()
        test_normalizer()
        print()
        test_builder_initialization()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
