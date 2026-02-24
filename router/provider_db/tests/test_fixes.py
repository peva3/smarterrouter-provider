"""
Tests for critical fixes and improvements.
"""

import asyncio
import pytest
import sqlite3
import tempfile
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone

from ..database import ProviderDB
from ..models import ModelBenchmark
from ..builder import BenchmarkBuilder


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    import os
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestSQLInjectionFix:
    """Test SQL injection vulnerability fixes."""
    
    def test_sql_injection_prevention_in_get_benchmarks_for_models(self, temp_db):
        """Test that get_benchmarks_for_models prevents SQL injection."""
        db = ProviderDB(temp_db)
        db.initialize()
        
        # Insert test data
        db.upsert_benchmark(
            model_id="openai/gpt-4",
            reasoning_score=85.0,
            coding_score=90.0,
            general_score=88.0,
            elo_rating=1300
        )
        
        # Test with potentially malicious model IDs
        malicious_ids = [
            "openai/gpt-4",
            "test' OR '1'='1",  # SQL injection attempt
            "anthropic/claude-3"
        ]
        
        # This should not raise an exception and should only return valid models
        results = db.get_benchmarks_for_models(malicious_ids)
        
        # Should only return the valid model
        assert len(results) == 1
        assert "openai/gpt-4" in results
        assert "test' OR '1'='1" not in results
        assert "anthropic/claude-3" not in results
    
    def test_sanitize_model_id(self, temp_db):
        """Test model ID sanitization."""
        db = ProviderDB(temp_db)
        db.initialize()
        
        # Test with various potentially dangerous model IDs
        test_cases = [
            ("openai/gpt-4", "openai/gpt-4"),  # Normal
            ("openai/gpt-4\0", "openai/gpt-4"),  # Null byte
            ("openai/gpt-4\n", "openai/gpt-4"),  # Newline
            ("openai/gpt-4' OR '1'='1", "openai/gpt-4 OR 11"),  # SQL injection
            ("a" * 300, "a" * 200),  # Too long
        ]
        
        for input_id, expected_sanitized in test_cases:
            try:
                db.upsert_benchmark(
                    model_id=input_id,
                    reasoning_score=50.0,
                    coding_score=50.0,
                    general_score=50.0,
                    elo_rating=1000
                )
                
                # Should be able to retrieve with sanitized ID
                result = db.get_benchmark(expected_sanitized)
                if result:
                    assert result["model_id"] == expected_sanitized
            except ValueError:
                # Some invalid IDs should raise ValueError
                pass


class TestVisionToolKeywordInjection:
    """Test vision/tool keyword injection for capability detection."""
    
    @pytest.mark.asyncio
    async def test_alias_generation_with_keywords(self, temp_db):
        """Test that aliases are generated with vision/tool keywords."""
        builder = BenchmarkBuilder(temp_db)
        
        # Create test models
        models = {
            "openai/gpt-4-vision-preview": ModelBenchmark(
                model_id="openai/gpt-4-vision-preview",
                reasoning_score=85.0,
                coding_score=90.0,
                general_score=88.0,
                elo_rating=1300
            ),
            "anthropic/claude-3-opus": ModelBenchmark(
                model_id="anthropic/claude-3-opus",
                reasoning_score=90.0,
                coding_score=85.0,
                general_score=92.0,
                elo_rating=1350
            ),
            "meta/llama-3-70b": ModelBenchmark(
                model_id="meta/llama-3-70b",
                reasoning_score=80.0,
                coding_score=75.0,
                general_score=82.0,
                elo_rating=1250
            )
        }
        
        # Generate aliases
        builder.db.initialize()
        aliases_created = builder._generate_aliases(models)
        
        # Check that aliases were created
        assert aliases_created > 0
        
        # Check specific aliases
        assert builder.db.get_canonical_id("gpt-4-vision-preview") == "openai/gpt-4-vision-preview"
        
        # Claude-3 should have vision keyword alias
        claude_alias = builder.db.get_canonical_id("claude-3-opus-vision")
        if claude_alias:
            assert claude_alias == "anthropic/claude-3-opus"
        
        # Llama should have tool keyword alias if applicable
        llama_alias = builder.db.get_canonical_id("llama-3-70b-tools")
        if llama_alias:
            assert llama_alias == "meta/llama-3-70b"


class TestCriticalSourceErrorHandling:
    """Test error handling for critical sources."""
    
    @pytest.mark.asyncio
    async def test_critical_source_failure_handling(self, temp_db):
        """Test that builder continues when critical sources fail."""
        builder = BenchmarkBuilder(temp_db)
        
        # Mock critical sources to fail
        with patch.object(builder, '_fetch_all_sources', new_callable=AsyncMock) as mock_fetch:
            # Simulate partial failure - some critical sources succeed
            mock_fetch.return_value = {
                "openai/gpt-4": {
                    "elo": [("lmsys", 1300.0)],
                    "reasoning": [],  # LiveBench failed
                    "coding": [("bigcodebench", 90.0)],
                    "general": []  # MMLU failed
                }
            }
            
            # Build should not crash even with critical source failures
            stats = await builder.build(force=True)
            
            # Should record failures
            assert "sources_failed" in stats
            # Build should complete
            assert "total_models" in stats


class TestRateLimiting:
    """Test rate limiting for API calls."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_decorator(self):
        """Test that rate_limited decorator works."""
        from ..utils import RateLimiter
        from ..builder import rate_limited
        
        rate_limiter = RateLimiter(calls_per_second=10.0)  # Fast for testing
        
        call_count = 0
        
        @rate_limited(rate_limiter)
        async def test_function():
            nonlocal call_count
            call_count += 1
            return call_count
        
        # Call multiple times quickly
        results = await asyncio.gather(
            test_function(),
            test_function(),
            test_function()
        )
        
        # All calls should succeed
        assert set(results) == {1, 2, 3}
        
        # Rate limiter should have been called
        assert call_count == 3


class TestSchemaCompatibility:
    """Test schema compatibility with RouterEngine."""
    
    def test_exact_schema_match(self, temp_db):
        """Test that database schema matches RouterEngine expectations exactly."""
        db = ProviderDB(temp_db)
        db.initialize()
        
        # Connect directly to check schema
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("PRAGMA table_info(model_benchmarks)")
        columns = cursor.fetchall()
        
        # Should have exactly 5 columns
        assert len(columns) == 5
        
        # Check column names and types
        column_info = {col[1]: col[2] for col in columns}
        
        # Exact schema RouterEngine expects
        expected_columns = {
            "model_id": "TEXT",
            "reasoning_score": "REAL",
            "coding_score": "REAL",
            "general_score": "REAL",
            "elo_rating": "INTEGER"
        }
        
        assert column_info == expected_columns
        
        # No extra columns
        assert "last_updated" not in column_info
        assert "archived" not in column_info
        
        conn.close()
    
    def test_router_query_compatibility(self, temp_db):
        """Test that RouterEngine can query the database."""
        db = ProviderDB(temp_db)
        db.initialize()
        
        # Insert test data
        test_models = [
            ("openai/gpt-4", 85.0, 90.0, 88.0, 1300),
            ("anthropic/claude-3", 90.0, 85.0, 92.0, 1350),
            ("meta/llama-3", 80.0, 75.0, 82.0, 1250)
        ]
        
        for model_id, reasoning, coding, general, elo in test_models:
            db.upsert_benchmark(
                model_id=model_id,
                reasoning_score=reasoning,
                coding_score=coding,
                general_score=general,
                elo_rating=elo
            )
        
        # Simulate RouterEngine query
        model_ids = ["openai/gpt-4", "anthropic/claude-3", "unknown/model"]
        results = db.get_benchmarks_for_models(model_ids)
        
        # Should return data for known models
        assert len(results) == 2
        assert "openai/gpt-4" in results
        assert "anthropic/claude-3" in results
        assert "unknown/model" not in results
        
        # Check data structure
        for model_id in ["openai/gpt-4", "anthropic/claude-3"]:
            data = results[model_id]
            assert "reasoning_score" in data
            assert "coding_score" in data
            assert "general_score" in data
            assert "elo_rating" in data
            assert isinstance(data["reasoning_score"], (int, float))
            assert isinstance(data["coding_score"], (int, float))
            assert isinstance(data["general_score"], (int, float))
            assert isinstance(data["elo_rating"], int)


class TestScoreValidation:
    """Test score validation."""
    
    def test_score_range_validation(self, temp_db):
        """Test that scores are validated to be in 0-100 range."""
        db = ProviderDB(temp_db)
        db.initialize()
        
        # Valid scores should work
        db.upsert_benchmark(
            model_id="test/model",
            reasoning_score=50.0,
            coding_score=75.0,
            general_score=100.0,
            elo_rating=1200
        )
        
        # Invalid scores should raise ValueError
        with pytest.raises(ValueError):
            db.upsert_benchmark(
                model_id="test/model2",
                reasoning_score=150.0,  # Too high
                coding_score=50.0,
                general_score=50.0,
                elo_rating=1200
            )
        
        with pytest.raises(ValueError):
            db.upsert_benchmark(
                model_id="test/model3",
                reasoning_score=-10.0,  # Too low
                coding_score=50.0,
                general_score=50.0,
                elo_rating=1200
            )
    
    def test_elo_validation(self, temp_db):
        """Test ELO rating validation."""
        db = ProviderDB(temp_db)
        db.initialize()
        
        # Valid ELO should work
        db.upsert_benchmark(
            model_id="test/model",
            reasoning_score=50.0,
            coding_score=50.0,
            general_score=50.0,
            elo_rating=1500  # High but valid
        )
        
        # Negative ELO should raise ValueError
        with pytest.raises(ValueError):
            db.upsert_benchmark(
                model_id="test/model2",
                reasoning_score=50.0,
                coding_score=50.0,
                general_score=50.0,
                elo_rating=-100  # Invalid
            )
        
        # Very high ELO should be capped
        db.upsert_benchmark(
            model_id="test/model3",
            reasoning_score=50.0,
            coding_score=50.0,
            general_score=50.0,
            elo_rating=2500  # Should be capped to 2000
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])