"""
Pydantic model for provider.db.
Matches RouterEngine expectations exactly.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ModelBenchmark(BaseModel):
    """
    Single row per model in model_benchmarks table.
    RouterEngine queries this via provider_db.get_benchmarks_for_models().
    """
    model_id: str = Field(..., description="OpenRouter canonical ID (e.g., openai/gpt-4-turbo)")
    reasoning_score: float = Field(default=0.0, ge=0.0, le=100.0, description="From LiveBench, 0-100")
    coding_score: float = Field(default=0.0, ge=0.0, le=100.0, description="From BigCodeBench, 0-100")
    general_score: float = Field(default=0.0, ge=0.0, le=100.0, description="From MMLU, 0-100")
    elo_rating: int = Field(default=1000, ge=1000, description="From LMSYS Arena, raw 1000+")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    archived: bool = Field(default=False, description="True if model no longer exists in OpenRouter")


class AliasRecord(BaseModel):
    """Maps alternate model names to canonical IDs."""
    alias: str
    canonical_id: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class Metadata(BaseModel):
    """Database metadata."""
    last_update: datetime = Field(default_factory=datetime.utcnow)
    sources: list[str] = Field(default_factory=list)
    total_models: int = 0
    build_duration_seconds: Optional[float] = None
