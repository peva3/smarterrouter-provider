"""
Provider DB - External model benchmark database for SmarterRouter.

This module provides tools to build provider.db - a SQLite database
containing benchmark scores for external LLM models.
"""

from .database import ProviderDB
from .models import ModelBenchmark, AliasRecord, Metadata
from .builder import BenchmarkBuilder, build_provider_db

__all__ = [
    'ProviderDB',
    'ModelBenchmark',
    'AliasRecord', 
    'Metadata',
    'BenchmarkBuilder',
    'build_provider_db',
]
