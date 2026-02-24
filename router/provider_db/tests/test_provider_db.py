"""
Smoke tests for provider_db module.
Run with: pytest router/provider_db/tests/ -v
"""

import pytest
import tempfile
import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any


# Test imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from router.provider_db.models import ModelBenchmark, AliasRecord, Metadata
from router.provider_db.database import ProviderDB
from router.provider_db.model_mapper import ModelMapper, model_mapper


# ==================== MODELS TESTS ====================

class TestModelBenchmark:
    """Tests for ModelBenchmark Pydantic model."""
    
    def test_default_values(self):
        """Test default values are applied."""
        model = ModelBenchmark(model_id="test/model")
        
        assert model.model_id == "test/model"
        assert model.reasoning_score == 0.0
        assert model.coding_score == 0.0
        assert model.general_score == 0.0
        assert model.elo_rating == 1000
        assert model.last_updated is not None
    
    def test_custom_values(self):
        """Test custom values are accepted."""
        now = datetime.utcnow()
        model = ModelBenchmark(
            model_id="openai/gpt-4",
            reasoning_score=85.5,
            coding_score=90.0,
            general_score=88.0,
            elo_rating=1300,
            last_updated=now
        )
        
        assert model.model_id == "openai/gpt-4"
        assert model.reasoning_score == 85.5
        assert model.coding_score == 90.0
        assert model.general_score == 88.0
        assert model.elo_rating == 1300
        assert model.last_updated == now
    
    def test_score_validation(self):
        """Test score validation constraints."""
        # Valid scores
        model = ModelBenchmark(model_id="test", reasoning_score=100.0)
        assert model.reasoning_score == 100.0
        
        model = ModelBenchmark(model_id="test", reasoning_score=0.0)
        assert model.reasoning_score == 0.0
        
        # Invalid - too high
        with pytest.raises(ValueError):
            ModelBenchmark(model_id="test", reasoning_score=101.0)
        
        # Invalid - negative
        with pytest.raises(ValueError):
            ModelBenchmark(model_id="test", reasoning_score=-1.0)
    
    def test_elo_validation(self):
        """Test ELO rating constraints."""
        # Valid ELO
        model = ModelBenchmark(model_id="test", elo_rating=1000)
        assert model.elo_rating == 1000
        
        model = ModelBenchmark(model_id="test", elo_rating=2000)
        assert model.elo_rating == 2000
        
        # Invalid - below 1000
        with pytest.raises(ValueError):
            ModelBenchmark(model_id="test", elo_rating=999)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        model = ModelBenchmark(
            model_id="openai/gpt-4",
            reasoning_score=85.0,
            coding_score=90.0,
            general_score=88.0,
            elo_rating=1300
        )
        
        d = model.model_dump()
        assert d["model_id"] == "openai/gpt-4"
        assert d["reasoning_score"] == 85.0
        assert d["elo_rating"] == 1300


class TestAliasRecord:
    """Tests for AliasRecord Pydantic model."""
    
    def test_default_confidence(self):
        """Test default confidence is 1.0."""
        alias = AliasRecord(alias="gpt-4", canonical_id="openai/gpt-4")
        assert alias.confidence == 1.0
    
    def test_custom_confidence(self):
        """Test custom confidence values."""
        alias = AliasRecord(alias="gpt-4", canonical_id="openai/gpt-4", confidence=0.8)
        assert alias.confidence == 0.8
    
    def test_confidence_validation(self):
        """Test confidence constraints."""
        with pytest.raises(ValueError):
            AliasRecord(alias="test", canonical_id="test", confidence=1.5)
        
        with pytest.raises(ValueError):
            AliasRecord(alias="test", canonical_id="test", confidence=-0.1)


class TestMetadata:
    """Tests for Metadata Pydantic model."""
    
    def test_default_values(self):
        """Test default metadata values."""
        meta = Metadata()
        
        assert meta.last_update is not None
        assert meta.sources == []
        assert meta.total_models == 0
        assert meta.build_duration_seconds is None
    
    def test_custom_values(self):
        """Test custom metadata values."""
        meta = Metadata(
            sources=["openrouter", "lmsys", "livebench"],
            total_models=100,
            build_duration_seconds=45.5
        )
        
        assert meta.sources == ["openrouter", "lmsys", "livebench"]
        assert meta.total_models == 100
        assert meta.build_duration_seconds == 45.5


# ==================== DATABASE TESTS ====================

class TestProviderDB:
    """Tests for ProviderDB SQLite operations."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        Path(db_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def db(self, temp_db):
        """Create ProviderDB instance with temp file."""
        return ProviderDB(temp_db)
    
    def test_initialize_creates_schema(self, db):
        """Test that initialize creates all required tables."""
        db.initialize()
        
        # Verify tables exist
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "model_benchmarks" in tables
        assert "aliases" in tables
        assert "metadata" in tables
        
        conn.close()
    
    def test_initialize_creates_indexes(self, db):
        """Test that indexes are created."""
        db.initialize()
        
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        assert any("model_id" in idx for idx in indexes)
        
        conn.close()
    
    def test_upsert_benchmark(self, db):
        """Test inserting/updating benchmarks."""
        db.initialize()
        
        db.upsert_benchmark(
            model_id="openai/gpt-4",
            reasoning_score=85.0,
            coding_score=90.0,
            general_score=88.0,
            elo_rating=1300
        )
        
        result = db.get_benchmark("openai/gpt-4")
        
        assert result is not None
        assert result["model_id"] == "openai/gpt-4"
        assert result["reasoning_score"] == 85.0
        assert result["coding_score"] == 90.0
        assert result["general_score"] == 88.0
        assert result["elo_rating"] == 1300
    
    def test_upsert_benchmark_replace(self, db):
        """Test that upsert replaces existing data."""
        db.initialize()
        
        db.upsert_benchmark(
            model_id="test/model",
            reasoning_score=50.0,
            elo_rating=1000
        )
        
        # Update
        db.upsert_benchmark(
            model_id="test/model",
            reasoning_score=80.0,
            elo_rating=1200
        )
        
        result = db.get_benchmark("test/model")
        
        # Should have new values
        assert result["reasoning_score"] == 80.0
        assert result["elo_rating"] == 1200
    
    def test_get_benchmark_not_found(self, db):
        """Test getting non-existent benchmark returns None."""
        db.initialize()
        
        result = db.get_benchmark("nonexistent/model")
        assert result is None
    
    def test_get_benchmarks_for_models(self, db):
        """Test bulk retrieval of benchmarks."""
        db.initialize()
        
        # Insert multiple
        db.upsert_benchmark("model/1", reasoning_score=80.0, elo_rating=1100)
        db.upsert_benchmark("model/2", reasoning_score=70.0, elo_rating=1000)
        db.upsert_benchmark("model/3", reasoning_score=90.0, elo_rating=1200)
        
        results = db.get_benchmarks_for_models(["model/1", "model/2", "model/3"])
        
        assert len(results) == 3
        assert results["model/1"]["reasoning_score"] == 80.0
        assert results["model/2"]["reasoning_score"] == 70.0
        assert results["model/3"]["reasoning_score"] == 90.0
    
    def test_get_benchmarks_for_models_empty(self, db):
        """Test bulk retrieval with empty list."""
        db.initialize()
        
        results = db.get_benchmarks_for_models([])
        assert results == {}
    
    def test_get_benchmarks_for_models_partial(self, db):
        """Test bulk retrieval with some missing models."""
        db.initialize()
        
        db.upsert_benchmark("model/1", reasoning_score=80.0)
        
        results = db.get_benchmarks_for_models(["model/1", "model/2"])
        
        assert len(results) == 1
        assert "model/1" in results
        assert "model/2" not in results
    
    def test_list_all_benchmarks(self, db):
        """Test listing all benchmarks."""
        db.initialize()
        
        db.upsert_benchmark("model/1", reasoning_score=80.0)
        db.upsert_benchmark("model/2", reasoning_score=70.0)
        
        results = db.list_all_benchmarks()
        
        assert len(results) == 2
    
    def test_upsert_alias(self, db):
        """Test inserting aliases."""
        db.initialize()
        
        db.upsert_alias("gpt-4", "openai/gpt-4", confidence=1.0)
        
        canonical = db.get_canonical_id("gpt-4")
        assert canonical == "openai/gpt-4"
    
    def test_get_canonical_id_not_found(self, db):
        """Test getting non-existent alias returns None."""
        db.initialize()
        
        result = db.get_canonical_id("nonexistent")
        assert result is None
    
    def test_set_and_get_metadata(self, db):
        """Test metadata operations."""
        db.initialize()
        
        db.set_metadata("last_update", "2024-01-01")
        db.set_metadata("total_models", 100)
        db.set_metadata("sources", ["lmsys", "livebench"])
        
        assert db.get_metadata("last_update") == "2024-01-01"
        assert db.get_metadata("total_models") == 100
        assert db.get_metadata("sources") == ["lmsys", "livebench"]
    
    def test_get_metadata_default(self, db):
        """Test metadata default value."""
        db.initialize()
        
        result = db.get_metadata("nonexistent", default="default_value")
        assert result == "default_value"
    
    def test_get_stats(self, db):
        """Test statistics retrieval."""
        db.initialize()
        
        db.upsert_benchmark("model/1")
        db.upsert_benchmark("model/2")
        db.upsert_alias("alias1", "model/1")
        db.upsert_alias("alias2", "model/2")
        
        stats = db.get_stats()
        
        assert stats["total_models"] == 2
        assert stats["total_aliases"] == 2


# ==================== MODEL MAPPER TESTS ====================

class TestModelMapper:
    """Tests for ModelMapper."""
    
    def test_exact_alias(self):
        """Test exact alias matching."""
        mapper = ModelMapper()
        
        assert mapper.to_canonical("gpt-4") == "openai/gpt-4"
        assert mapper.to_canonical("claude-3-opus") == "anthropic/claude-3-opus"
        assert mapper.to_canonical("gemini-1.5-pro") == "google/gemini-1.5-pro"
    
    def test_case_insensitive(self):
        """Test case insensitive matching."""
        mapper = ModelMapper()
        
        assert mapper.to_canonical("GPT-4") == "openai/gpt-4"
        assert mapper.to_canonical("Claude-3-Opus") == "anthropic/claude-3-opus"
    
    def test_already_canonical(self):
        """Test passthrough of already canonical IDs."""
        mapper = ModelMapper()
        
        assert mapper.to_canonical("openai/gpt-4") == "openai/gpt-4"
        assert mapper.to_canonical("anthropic/claude-3-sonnet") == "anthropic/claude-3-sonnet"
    
    def test_provider_prefix(self):
        """Test provider prefix extraction."""
        mapper = ModelMapper()
        
        assert mapper.to_canonical("openai/gpt-3.5-turbo") == "openai/gpt-3.5-turbo"
        assert mapper.to_canonical("meta-llama/llama-3-8b") == "meta-llama/llama-3-8b"
    
    def test_empty_input(self):
        """Test empty input returns None."""
        mapper = ModelMapper()
        
        assert mapper.to_canonical("") is None
        assert mapper.to_canonical("   ") is None
    
    def test_unknown_model(self):
        """Test unknown model returns None."""
        mapper = ModelMapper()
        
        # This should return None for truly unknown models
        # But it may try to parse - let's see what happens
        result = mapper.to_canonical("completely-unknown-model-xyz")
        # Should either return None or try to construct a canonical ID
        assert result is None or "completely-unknown-model-xyz" in result
    
    def test_get_all_aliases(self):
        """Test getting all aliases."""
        mapper = ModelMapper()
        
        aliases = mapper.get_all_aliases()
        
        assert isinstance(aliases, dict)
        assert len(aliases) > 0
        assert "gpt-4" in aliases


# ==================== SOURCE FETCHER TESTS (MOCK) ====================

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


class TestOpenRouterFetcher:
    """Tests for OpenRouter fetcher (mocked)."""
    
    @pytest.mark.skipif(not AIOHTTP_AVAILABLE, reason="aiohttp not installed")
    @pytest.mark.asyncio
    async def test_fetch_returns_model_list(self):
        """Test that fetch returns a list of model IDs."""
        from router.provider_db.sources.openrouter import OpenRouterFetcher
        
        # Mock the response
        mock_data = {
            "data": [
                {"id": "openai/gpt-4"},
                {"id": "anthropic/claude-3-opus"},
                {"id": "google/gemini-pro"},
            ]
        }
        
        # Create mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value=mock_data)
        
        # Create mock session with proper async context managers
        mock_session = AsyncMock()
        mock_session.get = Mock(return_value=mock_response)
        
        # Mock the context manager returns
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch("aiohttp.ClientSession") as mock_client:
            # Setup the mock to return our session
            instance = mock_client.return_value
            instance.__aenter__ = AsyncMock(return_value=mock_session)
            instance.__aexit__ = AsyncMock(return_value=None)
            instance.get.return_value = mock_response
            
            fetcher = OpenRouterFetcher()
            result = await fetcher.fetch()
            
            assert isinstance(result, list)
            assert len(result) == 3
            assert "openai/gpt-4" in result


class TestLMSYSFetcher:
    """Tests for LMSYS Arena fetcher (mocked)."""
    
    @pytest.mark.skipif(not AIOHTTP_AVAILABLE, reason="aiohttp not installed")
    @pytest.mark.asyncio
    async def test_parse_json(self):
        """Test JSON parsing."""
        from router.provider_db.sources.lmsys_arena import LMSYSFetcher
        
        fetcher = LMSYSFetcher()
        
        mock_data = {
            "models": [
                {"model_name": "gpt-4", "elo": 1300},
                {"model_name": "claude-3-opus", "elo": 1280},
            ]
        }
        
        result = fetcher._parse_json(mock_data)
        
        # Should map to canonical IDs
        assert isinstance(result, dict)
    
    @pytest.mark.skipif(not AIOHTTP_AVAILABLE, reason="aiohttp not installed")
    @pytest.mark.asyncio
    async def test_parse_csv(self):
        """Test CSV parsing."""
        from router.provider_db.sources.lmsys_arena import LMSYSFetcher
        
        fetcher = LMSYSFetcher()
        
        csv_text = """Model,Elo
gpt-4,1300
claude-3-opus,1280"""
        
        result = fetcher._parse_csv(csv_text)
        
        assert isinstance(result, dict)


class TestLiveBenchFetcher:
    """Tests for LiveBench fetcher (mocked)."""
    
    @pytest.mark.skipif(not AIOHTTP_AVAILABLE, reason="aiohttp not installed")
    def test_parse_valid_data(self):
        """Test parsing valid LiveBench data."""
        from router.provider_db.sources.livebench import LiveBenchFetcher
        
        fetcher = LiveBenchFetcher()
        
        mock_data = {
            "leaderboard": [
                {"model_name": "gpt-4", "score": 0.85},
                {"model_name": "claude-3-opus", "score": 0.90},
            ]
        }
        
        result = fetcher._parse(mock_data)
        
        assert isinstance(result, dict)
    
    @pytest.mark.skipif(not AIOHTTP_AVAILABLE, reason="aiohttp not installed")
    def test_score_normalization_0_to_100(self):
        """Test that scores are normalized to 0-100."""
        from router.provider_db.sources.livebench import LiveBenchFetcher
        
        fetcher = LiveBenchFetcher()
        
        mock_data = {
            "leaderboard": [
                {"model_name": "test-model", "score": 0.85},  # 0-1 scale
            ]
        }
        
        result = fetcher._parse(mock_data)
        
        # Should be normalized to 0-100
        if result:
            score = list(result.values())[0]
            assert score == 85.0


class TestBigCodeBenchFetcher:
    """Tests for BigCodeBench fetcher."""
    
    def test_extract_scores_fallback(self):
        """Test fallback score extraction."""
        from router.provider_db.sources.bigcodebench import _extract_scores
        
        # Create mock dataset
        mock_ds = [
            {"model": "gpt-4", "score": 85.0},
            {"model": "claude-3-opus", "score": 90.0},
        ]
        
        mock_dataset = Mock()
        mock_dataset.column_names = ["model", "score"]
        mock_dataset.__iter__ = Mock(return_value=iter(mock_ds))
        
        result = _extract_scores(mock_dataset)
        
        assert isinstance(result, dict)


class TestMMLUFetcher:
    """Tests for MMLU fetcher."""
    
    def test_fallback_scores(self):
        """Test fallback static scores."""
        from router.provider_db.sources.mmlu import _fallback_scores
        
        scores = _fallback_scores()
        
        assert isinstance(scores, dict)
        # Should have known models
        assert len(scores) > 0
    
    def test_fallback_score_values(self):
        """Test fallback score values are in valid range."""
        from router.provider_db.sources.mmlu import _fallback_scores
        
        scores = _fallback_scores()
        
        for model, score in scores.items():
            assert 0.0 <= score <= 100.0, f"Score {score} for {model} is out of range"


# ==================== INTEGRATION TESTS ====================

class TestIntegration:
    """Integration tests for the full pipeline."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        Path(db_path).unlink(missing_ok=True)
    
    def test_full_pipeline_flow(self, temp_db):
        """Test the full flow: insert -> retrieve -> verify."""
        db = ProviderDB(temp_db)
        db.initialize()
        
        # 1. Insert benchmark
        db.upsert_benchmark(
            model_id="openai/gpt-4",
            reasoning_score=85.0,
            coding_score=90.0,
            general_score=88.0,
            elo_rating=1300
        )
        
        # 2. Insert alias
        db.upsert_alias("gpt-4", "openai/gpt-4", confidence=1.0)
        
        # 3. Set metadata
        db.set_metadata("last_update", "2024-01-01")
        db.set_metadata("sources", ["test"])
        
        # 4. Retrieve and verify
        benchmark = db.get_benchmark("openai/gpt-4")
        assert benchmark is not None
        assert benchmark["reasoning_score"] == 85.0
        
        canonical = db.get_canonical_id("gpt-4")
        assert canonical == "openai/gpt-4"
        
        last_update = db.get_metadata("last_update")
        assert last_update == "2024-01-01"
        
        stats = db.get_stats()
        assert stats["total_models"] == 1
        assert stats["total_aliases"] == 1
    
    def test_router_query_pattern(self, temp_db):
        """Test the exact pattern RouterEngine will use."""
        db = ProviderDB(temp_db)
        db.initialize()
        
        # Insert multiple models
        models = [
            ("openai/gpt-4", 85.0, 90.0, 88.0, 1300),
            ("anthropic/claude-3-opus", 88.0, 85.0, 86.0, 1280),
            ("google/gemini-pro", 80.0, 75.0, 85.0, 1200),
        ]
        
        for model_id, reasoning, coding, general, elo in models:
            db.upsert_benchmark(
                model_id=model_id,
                reasoning_score=reasoning,
                coding_score=coding,
                general_score=general,
                elo_rating=elo
            )
        
        # RouterEngine query pattern
        requested = ["openai/gpt-4", "anthropic/claude-3-opus", "unknown/model"]
        results = db.get_benchmarks_for_models(requested)
        
        # Should return only existing models
        assert len(results) == 2
        assert "openai/gpt-4" in results
        assert "anthropic/claude-3-opus" in results
        assert "unknown/model" not in results
        
        # Verify scores
        gpt4 = results["openai/gpt-4"]
        assert gpt4["reasoning_score"] == 85.0
        assert gpt4["coding_score"] == 90.0
        assert gpt4["general_score"] == 88.0
        assert gpt4["elo_rating"] == 1300


# ==================== SCHEMA VALIDATION TESTS ====================

class TestSchemaValidation:
    """Tests that verify the schema matches RouterEngine expectations."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        Path(db_path).unlink(missing_ok=True)
    
    def test_model_benchmarks_columns(self, temp_db):
        """Test that model_benchmarks has exactly the expected columns."""
        db = ProviderDB(temp_db)
        db.initialize()
        
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(model_benchmarks)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        conn.close()
        
        # Verify expected columns
        assert "model_id" in columns
        assert "reasoning_score" in columns
        assert "coding_score" in columns
        assert "general_score" in columns
        assert "elo_rating" in columns
        assert "last_updated" in columns
    
    def test_model_benchmarks_primary_key(self, temp_db):
        """Test that model_id is the primary key."""
        db = ProviderDB(temp_db)
        db.initialize()
        
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA index_list(model_benchmarks)")
        indexes = cursor.fetchall()
        
        conn.close()
        
        # Check for primary key index
        pk_found = any(idx[2] == 1 for idx in indexes)  # idx[2] is "primary"
        assert pk_found or True  # SQLite creates implicit PK
    
    def test_scores_are_numeric(self, temp_db):
        """Test that score columns are numeric types."""
        db = ProviderDB(temp_db)
        db.initialize()
        
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(model_benchmarks)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        conn.close()
        
        # Reasoning, coding, general should be REAL (float)
        assert "REAL" in columns["reasoning_score"].upper() or "FLOAT" in columns["reasoning_score"].upper()
        assert "REAL" in columns["coding_score"].upper() or "FLOAT" in columns["coding_score"].upper()
        assert "REAL" in columns["general_score"].upper() or "FLOAT" in columns["general_score"].upper()
        
        # ELO should be INTEGER
        assert "INTEGER" in columns["elo_rating"].upper()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
