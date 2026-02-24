"""
Provider DB Builder - Orchestrates fetching benchmark data from multiple sources.

This is the main entry point for building provider.db.
Run with: python -m router.provider_db.cli build
"""

import asyncio
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar, Coroutine, Tuple
from functools import wraps

from .database import ProviderDB
from .models import ModelBenchmark
from .utils import RateLimiter
from .logging_config import StructuredLogger

logger = StructuredLogger(__name__)

T = TypeVar('T')


def async_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying async functions with exponential backoff."""
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected error in async_retry")
        return wrapper
    return decorator


def rate_limited(rate_limiter: RateLimiter):
    """Decorator to apply rate limiting to async functions."""
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            await rate_limiter.wait()
            return await func(*args, **kwargs)
        return wrapper
    return decorator


SOURCE_BASE_WEIGHTS: dict[str, float] = {
    'lmsys': 1.0,
    'arena': 0.8,
    'livebench': 1.0,
    'gsm8k': 0.9,
    'arc': 0.9,
    'bbh': 0.9,
    'agieval': 0.8,
    'mathvista': 0.8,
    'frontiermath': 0.8,
    'aime': 0.8,
    'stateval': 0.8,
    'gpqa': 0.8,
    'bigcodebench': 1.0,
    'humaneval': 0.9,
    'swe_bench': 0.9,
    'aider': 0.8,
    'livecodebench': 0.8,
    'scicode': 0.8,
    'tool_use': 0.8,
    'mmlu': 1.0,
    'mmlu_pro': 0.9,
    'mixeval_x': 0.9,
    'chinese': 0.8,
    'ailuminate': 0.8,
    'megabench': 0.8,
    'helm': 0.8,
    'domain_specific': 0.7,
    'vision': 0.7,
    'math': 0.8,
    'truthfulqa': 0.8,
    'hellaswag': 0.8,
    'multilingual': 0.8,
    'safety': 0.8,
}


class BenchmarkBuilder:
    """
    Orchestrates fetching benchmark data from multiple sources and building provider.db.
    
    Handles:
    - Parallel fetching with retries
    - Conflict resolution (averaging)
    - Graceful degradation when sources fail
    - Progress tracking
    """
    
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db = ProviderDB(db_path)
        
        # Rate limiter for API calls (1 call per second by default)
        self.rate_limiter = RateLimiter(calls_per_second=1.0)
        
        self.stats = {
            'start_time': None,
            'end_time': None,
            'duration': None,
            'sources_attempted': [],
            'sources_succeeded': [],
            'sources_failed': [],
            'total_models': 0,
            'models_with_reasoning': 0,
            'models_with_coding': 0,
            'models_with_general': 0,
            'models_with_elo': 0,
            'total_aliases': 0,
        }
    
    async def build(self, force: bool = False) -> dict[str, Any]:
        """
        Main build method - fetches all sources and builds the database.
        
        Incremental update strategy:
        - Never deletes models (preserves historical data)
        - Archives models no longer in OpenRouter
        - Unarchives models that return
        - Updates benchmark data for existing models
        
        Args:
            force: If True, rebuild even if database exists. If False, 
                   will skip models that already have data.
        
        Returns:
            Build statistics dictionary
        """
        self.stats['start_time'] = datetime.now(timezone.utc)
        logger.build_started(str(self.db_path), force)
        
        try:
            # Initialize database
            self.db.initialize()
            
            # Get existing model IDs before any changes
            existing_ids = self.db.get_all_model_ids()
            logger.info(f"Found {len(existing_ids)} models in database")
            
            # Fetch all sources in parallel
            logger.info("Fetching benchmark data from all sources...")
            scores = await self._fetch_all_sources()
            
            if not scores:
                logger.warning("No benchmark data fetched from any source!")
                return self.stats
            
            # Aggregate and resolve conflicts
            logger.info("Aggregating scores and resolving conflicts...")
            aggregated = self._aggregate_scores(scores)
            
            # Fetch all OpenRouter models to ensure 100% coverage
            openrouter_models = set()
            archived_before = set()  # Initialize in case OpenRouter fetch fails
            logger.info("Fetching OpenRouter model catalog...")
            try:
                from .sources.openrouter import OpenRouterFetcher
                openrouter_models = set(await OpenRouterFetcher().fetch())
                logger.info(f"OpenRouter has {len(openrouter_models)} total models")
                
                # Capture set of archived model IDs BEFORE writing, for accurate reactivation stats
                all_models_before = self.db.list_all_benchmarks()
                archived_before = {m['model_id'] for m in all_models_before if m.get('archived', 0)}
                
                # Import heuristics for score estimation
                from .sources import heuristics
                
                # Add any OpenRouter models that don't have benchmark data yet
                added_count = 0
                estimated_count = 0
                for model_id in openrouter_models:
                    if model_id not in aggregated:
                        # Try to estimate scores using heuristics first
                        estimated = heuristics.estimate_scores(model_id)
                        if estimated:
                            aggregated[model_id] = ModelBenchmark(
                                model_id=model_id,
                                reasoning_score=estimated["reasoning_score"],
                                coding_score=estimated["coding_score"],
                                general_score=estimated["general_score"],
                                elo_rating=int(estimated["elo_rating"])
                            )
                            estimated_count += 1
                        else:
                            # Create ModelBenchmark with all defaults (0 scores, 1000 ELO)
                            aggregated[model_id] = ModelBenchmark(
                                model_id=model_id,
                                reasoning_score=0.0,
                                coding_score=0.0,
                                general_score=0.0,
                                elo_rating=1000
                            )
                            added_count += 1
                
                # Always set stats, even if zero
                self.stats['models_added_defaults'] = added_count
                self.stats['models_estimated'] = estimated_count
                if added_count > 0 or estimated_count > 0:
                    logger.info(f"Added {added_count} OpenRouter models with default scores")
                    logger.info(f"Estimated scores for {estimated_count} OpenRouter models using heuristics")
                    
            except Exception as e:
                logger.warning(f"Failed to fetch OpenRouter models: {e}. Proceeding with only benchmarked models.")
                # Ensure stats keys exist for consistency
                self.stats['models_added_defaults'] = 0
                self.stats['models_estimated'] = 0
            
            # Write to database
            logger.info(f"Writing {len(aggregated)} models to database...")
            await self._write_to_db(aggregated, force=force)
            
            # Note: Archive functionality removed to match RouterEngine schema
            # RouterEngine expects simple table without archive columns
            
            # Generate aliases
            logger.info("Generating aliases...")
            aliases_created = self._generate_aliases(aggregated)
            
            # Update metadata
            self._update_metadata()
            
            self.stats['total_models'] = len(aggregated)
            self.stats['total_aliases'] = aliases_created
            
            # Count models with each score type
            for model_id, data in aggregated.items():
                if data.reasoning_score > 0:
                    self.stats['models_with_reasoning'] += 1
                if data.coding_score > 0:
                    self.stats['models_with_coding'] += 1
                if data.general_score > 0:
                    self.stats['models_with_general'] += 1
                if data.elo_rating > 1000:
                    self.stats['models_with_elo'] += 1
            
        except Exception as e:
            logger.exception(f"Build failed: {e}")
            raise
        
        finally:
            self.stats['end_time'] = datetime.now(timezone.utc)
            if self.stats['start_time']:
                self.stats['duration'] = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        logger.info(f"Build completed in {self.stats['duration']:.1f}s")
        logger.info(f"Total models: {self.stats['total_models']}")
        logger.info(f"Models with reasoning: {self.stats['models_with_reasoning']}")
        logger.info(f"Models with coding: {self.stats['models_with_coding']}")
        logger.info(f"Models with general: {self.stats['models_with_general']}")
        logger.info(f"Models with ELO: {self.stats['models_with_elo']}")
        
        return self.stats
    
    @async_retry(max_attempts=3, delay=2.0)
    async def _fetch_all_sources(self) -> dict[str, dict[str, Any]]:
        """Fetch all benchmark sources in parallel."""
        
        # ============ ELO SOURCES ============
        @rate_limited(self.rate_limiter)
        @rate_limited(self.rate_limiter)

        async def fetch_lmsys():
            """LMSYS Chatbot Arena (primary ELO)."""
            try:
                from .sources.lmsys_arena import fetch_lmsys_arena
                self.stats['sources_attempted'].append('lmsys')
                result = await fetch_lmsys_arena()
                if result:
                    self.stats['sources_succeeded'].append('lmsys')
                    logger.info(f"LMSYS: fetched {len(result)} ELO ratings")
                else:
                    self.stats['sources_failed'].append('lmsys')
                return {'elo': result}
            except Exception as e:
                logger.error(f"LMSYS fetch failed: {e}")
                self.stats['sources_failed'].append('lmsys')
                return {'elo': {}}
        
        @rate_limited(self.rate_limiter)
        @rate_limited(self.rate_limiter)

        async def fetch_arena():
            """Arena.ai (secondary ELO, lower priority)."""
            try:
                from .sources import arena
                self.stats['sources_attempted'].append('arena')
                result = await asyncio.to_thread(arena.fetch_arena)
                if result:
                    self.stats['sources_succeeded'].append('arena')
                    logger.info(f"Arena.ai: fetched {len(result)} ELO ratings")
                return {'elo': result}
            except Exception as e:
                logger.error(f"Arena.ai fetch failed: {e}")
                self.stats['sources_failed'].append('arena')
                return {'elo': {}}
        
        # ============ REASONING SOURCES ============
        @rate_limited(self.rate_limiter)

        async def fetch_livebench():
            """LiveBench (primary reasoning)."""
            try:
                from .sources.livebench import fetch_livebench
                self.stats['sources_attempted'].append('livebench')
                result = await fetch_livebench()
                if result:
                    self.stats['sources_succeeded'].append('livebench')
                    logger.info(f"LiveBench: fetched {len(result)} reasoning scores")
                else:
                    self.stats['sources_failed'].append('livebench')
                return {'reasoning': result}
            except Exception as e:
                logger.error(f"LiveBench fetch failed: {e}")
                self.stats['sources_failed'].append('livebench')
                return {'reasoning': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_gsm8k():
            """GSM8K (grade school math)."""
            try:
                from .sources import gsm8k
                self.stats['sources_attempted'].append('gsm8k')
                result = await asyncio.to_thread(gsm8k.fetch_gsm8k)
                if result:
                    self.stats['sources_succeeded'].append('gsm8k')
                    logger.info(f"GSM8K: fetched {len(result)} reasoning scores")
                return {'reasoning': result}
            except Exception as e:
                logger.error(f"GSM8K fetch failed: {e}")
                self.stats['sources_failed'].append('gsm8k')
                return {'reasoning': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_arc():
            """ARC (AI2 Reasoning Challenge)."""
            try:
                from .sources import arc
                self.stats['sources_attempted'].append('arc')
                result = await asyncio.to_thread(arc.fetch_arc)
                if result:
                    self.stats['sources_succeeded'].append('arc')
                    logger.info(f"ARC: fetched {len(result)} reasoning scores")
                return {'reasoning': result}
            except Exception as e:
                logger.error(f"ARC fetch failed: {e}")
                self.stats['sources_failed'].append('arc')
                return {'reasoning': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_bbh():
            """BBH (BIG-Bench Hard)."""
            try:
                from .sources import bbh
                self.stats['sources_attempted'].append('bbh')
                result = await asyncio.to_thread(bbh.fetch_bbh)
                if result:
                    self.stats['sources_succeeded'].append('bbh')
                    logger.info(f"BBH: fetched {len(result)} reasoning scores")
                return {'reasoning': result}
            except Exception as e:
                logger.error(f"BBH fetch failed: {e}")
                self.stats['sources_failed'].append('bbh')
                return {'reasoning': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_agieval():
            """AGIEval (advanced reasoning)."""
            try:
                from .sources import agieval
                self.stats['sources_attempted'].append('agieval')
                result = await asyncio.to_thread(agieval.fetch_agieval)
                if result:
                    self.stats['sources_succeeded'].append('agieval')
                    logger.info(f"AGIEval: fetched {len(result)} reasoning scores")
                return {'reasoning': result}
            except Exception as e:
                logger.error(f"AGIEval fetch failed: {e}")
                self.stats['sources_failed'].append('agieval')
                return {'reasoning': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_mathvista():
            """MathVista (math + visual reasoning)."""
            try:
                from .sources import mathvista
                self.stats['sources_attempted'].append('mathvista')
                result = await asyncio.to_thread(mathvista.fetch_mathvista)
                if result:
                    self.stats['sources_succeeded'].append('mathvista')
                    logger.info(f"MathVista: fetched {len(result)} reasoning scores")
                return {'reasoning': result}
            except Exception as e:
                logger.error(f"MathVista fetch failed: {e}")
                self.stats['sources_failed'].append('mathvista')
                return {'reasoning': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_frontiermath():
            """FrontierMath (research mathematics)."""
            try:
                from .sources import frontiermath
                self.stats['sources_attempted'].append('frontiermath')
                result = await asyncio.to_thread(frontiermath.fetch_frontiermath)
                if result:
                    self.stats['sources_succeeded'].append('frontiermath')
                    logger.info(f"FrontierMath: fetched {len(result)} reasoning scores")
                return {'reasoning': result}
            except Exception as e:
                logger.error(f"FrontierMath fetch failed: {e}")
                self.stats['sources_failed'].append('frontiermath')
                return {'reasoning': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_aime():
            """AIME (competition math)."""
            try:
                from .sources import aime
                self.stats['sources_attempted'].append('aime')
                result = await asyncio.to_thread(aime.fetch_aime)
                if result:
                    self.stats['sources_succeeded'].append('aime')
                    logger.info(f"AIME: fetched {len(result)} reasoning scores")
                return {'reasoning': result}
            except Exception as e:
                logger.error(f"AIME fetch failed: {e}")
                self.stats['sources_failed'].append('aime')
                return {'reasoning': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_stateval():
            """StatEval (statistics benchmark)."""
            try:
                from .sources import stateval
                self.stats['sources_attempted'].append('stateval')
                result = await asyncio.to_thread(stateval.fetch_stateval)
                if result:
                    self.stats['sources_succeeded'].append('stateval')
                    logger.info(f"StatEval: fetched {len(result)} reasoning scores")
                return {'reasoning': result}
            except Exception as e:
                logger.error(f"StatEval fetch failed: {e}")
                self.stats['sources_failed'].append('stateval')
                return {'reasoning': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_gpqa():
            """GPQA (graduate-level science)."""
            try:
                from .sources import gpqa
                self.stats['sources_attempted'].append('gpqa')
                result = await asyncio.to_thread(gpqa.fetch_gpqa)
                if result:
                    self.stats['sources_succeeded'].append('gpqa')
                    logger.info(f"GPQA: fetched {len(result)} reasoning scores")
                return {'reasoning': result}
            except Exception as e:
                logger.error(f"GPQA fetch failed: {e}")
                self.stats['sources_failed'].append('gpqa')
                return {'reasoning': {}}

        @rate_limited(self.rate_limiter)

        
        async def fetch_math():
            """Hendrycks MATH benchmark."""
            try:
                from .sources import math
                self.stats['sources_attempted'].append('math')
                result = await asyncio.to_thread(math.fetch_math)
                if result:
                    self.stats['sources_succeeded'].append('math')
                    logger.info(f"MATH: fetched {len(result)} reasoning scores")
                return {'reasoning': result}
            except Exception as e:
                logger.error(f"MATH fetch failed: {e}")
                self.stats['sources_failed'].append('math')
                return {'reasoning': {}}

        @rate_limited(self.rate_limiter)

        
        async def fetch_hellaswag():
            """HellaSwag commonsense reasoning."""
            try:
                from .sources import hellaswag
                self.stats['sources_attempted'].append('hellaswag')
                result = await asyncio.to_thread(hellaswag.fetch_hellaswag)
                if result:
                    self.stats['sources_succeeded'].append('hellaswag')
                    logger.info(f"HellaSwag: fetched {len(result)} reasoning scores")
                return {'reasoning': result}
            except Exception as e:
                logger.error(f"HellaSwag fetch failed: {e}")
                self.stats['sources_failed'].append('hellaswag')
                return {'reasoning': {}}
        
        # ============ CODING SOURCES ============
        @rate_limited(self.rate_limiter)

        async def fetch_bigcodebench():
            """BigCodeBench (primary coding)."""
            try:
                from .sources import bigcodebench
                self.stats['sources_attempted'].append('bigcodebench')
                result = await asyncio.to_thread(bigcodebench.fetch_bigcodebench)
                if result:
                    self.stats['sources_succeeded'].append('bigcodebench')
                    logger.info(f"BigCodeBench: fetched {len(result)} coding scores")
                else:
                    self.stats['sources_failed'].append('bigcodebench')
                return {'coding': result}
            except Exception as e:
                logger.error(f"BigCodeBench fetch failed: {e}")
                self.stats['sources_failed'].append('bigcodebench')
                return {'coding': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_humaneval():
            """HumanEval (function completion)."""
            try:
                from .sources import humaneval
                self.stats['sources_attempted'].append('humaneval')
                result = await asyncio.to_thread(humaneval.fetch_humaneval)
                if result:
                    self.stats['sources_succeeded'].append('humaneval')
                    logger.info(f"HumanEval: fetched {len(result)} coding scores")
                return {'coding': result}
            except Exception as e:
                logger.error(f"HumanEval fetch failed: {e}")
                self.stats['sources_failed'].append('humaneval')
                return {'coding': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_swebench():
            """SWE-bench (real GitHub issues)."""
            try:
                from .sources import swebench
                self.stats['sources_attempted'].append('swebench')
                result = await asyncio.to_thread(swebench.fetch_swebench)
                if result:
                    self.stats['sources_succeeded'].append('swebench')
                    logger.info(f"SWE-bench: fetched {len(result)} coding scores")
                return {'coding': result}
            except Exception as e:
                logger.error(f"SWE-bench fetch failed: {e}")
                self.stats['sources_failed'].append('swebench')
                return {'coding': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_aider():
            """Aider (practical coding)."""
            try:
                from .sources import aider
                self.stats['sources_attempted'].append('aider')
                result = await asyncio.to_thread(aider.fetch_aider)
                if result:
                    self.stats['sources_succeeded'].append('aider')
                    logger.info(f"Aider: fetched {len(result)} coding scores")
                return {'coding': result}
            except Exception as e:
                logger.error(f"Aider fetch failed: {e}")
                self.stats['sources_failed'].append('aider')
                return {'coding': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_livecodebench():
            """LiveCodeBench (competitive programming)."""
            try:
                from .sources import livecodebench
                self.stats['sources_attempted'].append('livecodebench')
                result = await asyncio.to_thread(livecodebench.fetch_livecodebench)
                if result:
                    self.stats['sources_succeeded'].append('livecodebench')
                    logger.info(f"LiveCodeBench: fetched {len(result)} coding scores")
                return {'coding': result}
            except Exception as e:
                logger.error(f"LiveCodeBench fetch failed: {e}")
                self.stats['sources_failed'].append('livecodebench')
                return {'coding': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_scicode():
            """SciCode (research coding)."""
            try:
                from .sources import scicode
                self.stats['sources_attempted'].append('scicode')
                result = await asyncio.to_thread(scicode.fetch_scicode)
                if result:
                    self.stats['sources_succeeded'].append('scicode')
                    logger.info(f"SciCode: fetched {len(result)} coding scores")
                return {'coding': result}
            except Exception as e:
                logger.error(f"SciCode fetch failed: {e}")
                self.stats['sources_failed'].append('scicode')
                return {'coding': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_tool_use():
            """Tool Use (function calling)."""
            try:
                from .sources import tool_use
                self.stats['sources_attempted'].append('tool_use')
                result = await asyncio.to_thread(tool_use.fetch_tool_use)
                if result:
                    self.stats['sources_succeeded'].append('tool_use')
                    logger.info(f"Tool Use: fetched {len(result)} coding scores")
                return {'coding': result}
            except Exception as e:
                logger.error(f"Tool Use fetch failed: {e}")
                self.stats['sources_failed'].append('tool_use')
                return {'coding': {}}
        
        # ============ GENERAL (KNOWLEDGE) SOURCES ============
        @rate_limited(self.rate_limiter)

        async def fetch_mmlu():
            """MMLU (57 subjects, primary general)."""
            try:
                from .sources import mmlu
                self.stats['sources_attempted'].append('mmlu')
                result = await asyncio.to_thread(mmlu.fetch_mmlu)
                if result:
                    self.stats['sources_succeeded'].append('mmlu')
                    logger.info(f"MMLU: fetched {len(result)} general scores")
                return {'general': result}
            except Exception as e:
                logger.error(f"MMLU fetch failed: {e}")
                self.stats['sources_failed'].append('mmlu')
                return {'general': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_mmlu_pro():
            """MMLU-Pro (harder variant)."""
            try:
                from .sources import mmlu_pro
                self.stats['sources_attempted'].append('mmlu_pro')
                result = await asyncio.to_thread(mmlu_pro.fetch_mmlu_pro)
                if result:
                    self.stats['sources_succeeded'].append('mmlu_pro')
                    logger.info(f"MMLU-Pro: fetched {len(result)} general scores")
                return {'general': result}
            except Exception as e:
                logger.error(f"MMLU-Pro fetch failed: {e}")
                self.stats['sources_failed'].append('mmlu_pro')
                return {'general': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_mixeval_x():
            """MixEval-X (multimodal general)."""
            try:
                from .sources import mixeval_x
                self.stats['sources_attempted'].append('mixeval_x')
                result = await asyncio.to_thread(mixeval_x.fetch_mixeval_x)
                if result:
                    self.stats['sources_succeeded'].append('mixeval_x')
                    logger.info(f"MixEval-X: fetched {len(result)} general scores")
                return {'general': result}
            except Exception as e:
                logger.error(f"MixEval-X fetch failed: {e}")
                self.stats['sources_failed'].append('mixeval_x')
                return {'general': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_chinese():
            """Chinese benchmarks (C-Eval, C-MMLU)."""
            try:
                from .sources import chinese
                self.stats['sources_attempted'].append('chinese')
                result = await asyncio.to_thread(chinese.fetch_chinese)
                if result:
                    self.stats['sources_succeeded'].append('chinese')
                    logger.info(f"Chinese: fetched {len(result)} general scores")
                return {'general': result}
            except Exception as e:
                logger.error(f"Chinese fetch failed: {e}")
                self.stats['sources_failed'].append('chinese')
                return {'general': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_ailuminate():
            """AILuminate (safety & reliability)."""
            try:
                from .sources import ailuminate
                self.stats['sources_attempted'].append('ailuminate')
                result = await asyncio.to_thread(ailuminate.fetch_ailuminate)
                if result:
                    self.stats['sources_succeeded'].append('ailuminate')
                    logger.info(f"AILuminate: fetched {len(result)} general scores")
                return {'general': result}
            except Exception as e:
                logger.error(f"AILuminate fetch failed: {e}")
                self.stats['sources_failed'].append('ailuminate')
                return {'general': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_megabench():
            """MEGA-Bench (500+ multimodal tasks)."""
            try:
                from .sources import mega_bench
                self.stats['sources_attempted'].append('megabench')
                result = await asyncio.to_thread(mega_bench.fetch_megabench)
                if result:
                    self.stats['sources_succeeded'].append('megabench')
                    logger.info(f"MEGA-Bench: fetched {len(result)} general scores")
                return {'general': result}
            except Exception as e:
                logger.error(f"MEGA-Bench fetch failed: {e}")
                self.stats['sources_failed'].append('megabench')
                return {'general': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_helm():
            """HELM (Stanford holistic evaluation)."""
            try:
                from .sources import helm
                self.stats['sources_attempted'].append('helm')
                result = await asyncio.to_thread(helm.fetch_helm)
                if result:
                    self.stats['sources_succeeded'].append('helm')
                    logger.info(f"HELM: fetched {len(result)} general scores")
                return {'general': result}
            except Exception as e:
                logger.error(f"HELM fetch failed: {e}")
                self.stats['sources_failed'].append('helm')
                return {'general': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_domain_specific():
            """Domain-Specific (healthcare, legal, finance, science)."""
            try:
                from .sources import domain_specific
                self.stats['sources_attempted'].append('domain_specific')
                result = await asyncio.to_thread(domain_specific.fetch_domain_specific)
                if result:
                    self.stats['sources_succeeded'].append('domain_specific')
                    logger.info(f"Domain-Specific: fetched {len(result)} general scores")
                return {'general': result}
            except Exception as e:
                logger.error(f"Domain-Specific fetch failed: {e}")
                self.stats['sources_failed'].append('domain_specific')
                return {'general': {}}
        
        @rate_limited(self.rate_limiter)

        
        async def fetch_vision():
            """Vision benchmarks (MMMU, MMBench)."""
            try:
                from .sources import vision
                self.stats['sources_attempted'].append('vision')
                result = await asyncio.to_thread(vision.fetch_vision)
                if result:
                    self.stats['sources_succeeded'].append('vision')
                    logger.info(f"Vision: fetched {len(result)} general scores")
                return {'general': result}
            except Exception as e:
                logger.error(f"Vision fetch failed: {e}")
                self.stats['sources_failed'].append('vision')
                return {'general': {}}

        @rate_limited(self.rate_limiter)

        
        async def fetch_truthfulqa():
            """TruthfulQA benchmark (factual accuracy)."""
            try:
                from .sources import truthfulqa
                self.stats['sources_attempted'].append('truthfulqa')
                result = await asyncio.to_thread(truthfulqa.fetch_truthfulqa)
                if result:
                    self.stats['sources_succeeded'].append('truthfulqa')
                    logger.info(f"TruthfulQA: fetched {len(result)} general scores")
                return {'general': result}
            except Exception as e:
                logger.error(f"TruthfulQA fetch failed: {e}")
                self.stats['sources_failed'].append('truthfulqa')
                return {'general': {}}

        @rate_limited(self.rate_limiter)

        
        async def fetch_multilingual():
            """Multilingual benchmarks (C-Eval, C-MMLU)."""
            try:
                from .sources import multilingual
                self.stats['sources_attempted'].append('multilingual')
                result = await asyncio.to_thread(multilingual.fetch_multilingual)
                if result:
                    self.stats['sources_succeeded'].append('multilingual')
                    logger.info(f"Multilingual: fetched {len(result)} general scores")
                return {'general': result}
            except Exception as e:
                logger.error(f"Multilingual fetch failed: {e}")
                self.stats['sources_failed'].append('multilingual')
                return {'general': {}}

        @rate_limited(self.rate_limiter)

        
        async def fetch_safety():
            """Safety benchmarks (harmful content refusal)."""
            try:
                from .sources import safety
                self.stats['sources_attempted'].append('safety')
                result = await asyncio.to_thread(safety.fetch_safety)
                if result:
                    self.stats['sources_succeeded'].append('safety')
                    logger.info(f"Safety: fetched {len(result)} general scores")
                return {'general': result}
            except Exception as e:
                logger.error(f"Safety fetch failed: {e}")
                self.stats['sources_failed'].append('safety')
                return {'general': {}}
        
        # Define critical sources (required for RouterEngine compatibility)
        CRITICAL_SOURCES = {
            'lmsys': fetch_lmsys,      # ELO - required
            'livebench': fetch_livebench,  # Reasoning - required
            'bigcodebench': fetch_bigcodebench,  # Coding - required
            'mmlu': fetch_mmlu,        # General - required
        }
        
        # Prepare all fetch tasks with error handling
        fetch_tasks = []
        source_info = []  # Store (name, is_critical) for each task
        
        # Add critical sources
        for name, fetch_func in CRITICAL_SOURCES.items():
            fetch_tasks.append(fetch_func())
            source_info.append((name, True))
        
        # Add optional sources
        optional_sources = [
            ('arena', fetch_arena),
            ('gsm8k', fetch_gsm8k),
            ('arc', fetch_arc),
            ('bbh', fetch_bbh),
            ('agieval', fetch_agieval),
            ('mathvista', fetch_mathvista),
            ('frontiermath', fetch_frontiermath),
            ('aime', fetch_aime),
            ('stateval', fetch_stateval),
            ('gpqa', fetch_gpqa),
            ('humaneval', fetch_humaneval),
            ('swebench', fetch_swebench),
            ('aider', fetch_aider),
            ('livecodebench', fetch_livecodebench),
            ('scicode', fetch_scicode),
            ('tool_use', fetch_tool_use),
            ('mmlu_pro', fetch_mmlu_pro),
            ('mixeval_x', fetch_mixeval_x),
            ('chinese', fetch_chinese),
            ('ailuminate', fetch_ailuminate),
            ('megabench', fetch_megabench),
            ('helm', fetch_helm),
            ('domain_specific', fetch_domain_specific),
            ('vision', fetch_vision),
            ('math', fetch_math),
            ('hellaswag', fetch_hellaswag),
            ('truthfulqa', fetch_truthfulqa),
            ('multilingual', fetch_multilingual),
            ('safety', fetch_safety),
        ]
        
        for name, fetch_func in optional_sources:
            fetch_tasks.append(fetch_func())
            source_info.append((name, False))
        
        # Execute all fetches with error handling
        results = []
        critical_failures = []
        source_order = []
        
        # Use as_completed to get results as they complete
        for idx, task in enumerate(asyncio.as_completed(fetch_tasks)):
            source_name, is_critical = source_info[idx]
            try:
                result = await task
                if result:  # Only count if we got data
                    results.append(result)
                    source_order.append(source_name)
                    logger.debug(f"Source {source_name} fetched successfully")
                else:
                    logger.warning(f"Source {source_name} returned empty data")
                    if is_critical:
                        critical_failures.append(source_name)
            except Exception as e:
                logger.error(f"Failed to fetch source {source_name}: {str(e)}")
                if is_critical:
                    critical_failures.append(source_name)
                # Continue with other sources
        
        # Check if critical sources failed
        if critical_failures:
            logger.warning(f"Critical sources failed: {critical_failures}")
            # We'll continue but log warning - router will use 0 for missing scores
        
        # source_order is now built dynamically from successful fetches
        
        merged: dict[str, dict[str, list[Tuple[str, float]]]] = {}
        for idx, result in enumerate(results):
            source = source_order[idx] if idx < len(source_order) else f'unknown_{idx}'
            for category, scores in result.items():
                for model_id, score in scores.items():
                    if model_id not in merged:
                        merged[model_id] = {}
                    if category not in merged[model_id]:
                        merged[model_id][category] = []
                    merged[model_id][category].append((source, score))
        
        logger.info(f"Total unique models from all sources: {len(merged)}")
        return merged
    
    def _compute_consensus_weights(self, scores: dict[str, dict[str, list[Tuple[str, float]]]]) -> dict[str, float]:
        """
        Compute consensus-based weight multipliers for each source.
        
        For each source, calculates the Pearson correlation between its scores
        and the mean of all other sources. Sources that agree with consensus
        get higher weights, outliers get penalized.
        
        Returns:
            Dict mapping source name to weight multiplier (0.5 to 1.5)
        """
        import math
        
        source_scores: dict[str, list[float]] = {}
        
        for model_id, categories in scores.items():
            for category, source_score_list in categories.items():
                for source, score in source_score_list:
                    if source not in source_scores:
                        source_scores[source] = []
                    source_scores[source].append(score)
        
        if len(source_scores) < 2:
            return {s: 1.0 for s in source_scores}
        
        source_correlations: dict[str, float] = {}
        
        for source in source_scores:
            other_scores = []
            source_only_scores = source_scores[source]
            
            for other_source in source_scores:
                if other_source != source:
                    other_scores.extend(source_scores[other_source])
            
            if not other_scores or len(source_only_scores) < 2:
                source_correlations[source] = 1.0
                continue
            
            mean_other = sum(other_scores) / len(other_scores)
            mean_source = sum(source_only_scores) / len(source_only_scores)
            
            numerator = sum((s - mean_source) * (o - mean_other) for s in source_only_scores for o in other_scores)
            
            ss_source = sum((s - mean_source) ** 2 for s in source_only_scores)
            ss_other = sum((o - mean_other) ** 2 for o in other_scores)
            
            denominator = math.sqrt(ss_source * ss_other)
            
            if denominator == 0:
                source_correlations[source] = 1.0
            else:
                correlation = numerator / denominator
                source_correlations[source] = correlation
        
        multipliers: dict[str, float] = {}
        for source, correlation in source_correlations.items():
            multipliers[source] = max(0.5, min(1.5, correlation))
        
        return multipliers
    
    def _aggregate_scores(self, scores: dict[str, dict[str, list[Tuple[str, float]]]]) -> dict[str, ModelBenchmark]:
        """
        Aggregate scores from multiple sources for each model using weighted averaging.
        
        Uses dynamic consensus-based weighting:
        - Base weights from SOURCE_BASE_WEIGHTS (tiered by source reliability)
        - Consensus multipliers from _compute_consensus_weights (penalize outliers)
        - Final weight = base_weight * consensus_multiplier
        """
        consensus_multipliers = self._compute_consensus_weights(scores)
        
        aggregated = {}
        
        for model_id, categories in scores.items():
            reasoning_weighted_sum = 0.0
            reasoning_weight_total = 0.0
            coding_weighted_sum = 0.0
            coding_weight_total = 0.0
            general_weighted_sum = 0.0
            general_weight_total = 0.0
            elo_weighted_sum = 0.0
            elo_weight_total = 0.0
            
            if 'reasoning' in categories:
                for source, score in categories['reasoning']:
                    base_weight = SOURCE_BASE_WEIGHTS.get(source, 0.5)
                    consensus_mult = consensus_multipliers.get(source, 1.0)
                    weight = base_weight * consensus_mult
                    reasoning_weighted_sum += score * weight
                    reasoning_weight_total += weight
            
            if 'coding' in categories:
                for source, score in categories['coding']:
                    base_weight = SOURCE_BASE_WEIGHTS.get(source, 0.5)
                    consensus_mult = consensus_multipliers.get(source, 1.0)
                    weight = base_weight * consensus_mult
                    coding_weighted_sum += score * weight
                    coding_weight_total += weight
            
            if 'general' in categories:
                for source, score in categories['general']:
                    base_weight = SOURCE_BASE_WEIGHTS.get(source, 0.5)
                    consensus_mult = consensus_multipliers.get(source, 1.0)
                    weight = base_weight * consensus_mult
                    general_weighted_sum += score * weight
                    general_weight_total += weight
            
            if 'elo' in categories:
                for source, score in categories['elo']:
                    base_weight = SOURCE_BASE_WEIGHTS.get(source, 0.5)
                    consensus_mult = consensus_multipliers.get(source, 1.0)
                    weight = base_weight * consensus_mult
                    elo_weighted_sum += score * weight
                    elo_weight_total += weight
            
            avg_reasoning = reasoning_weighted_sum / reasoning_weight_total if reasoning_weight_total > 0 else 0.0
            avg_coding = coding_weighted_sum / coding_weight_total if coding_weight_total > 0 else 0.0
            avg_general = general_weighted_sum / general_weight_total if general_weight_total > 0 else 0.0
            avg_elo = int(elo_weighted_sum / elo_weight_total) if elo_weight_total > 0 else 1000
            
            avg_reasoning = max(0.0, min(100.0, avg_reasoning))
            avg_coding = max(0.0, min(100.0, avg_coding))
            avg_general = max(0.0, min(100.0, avg_general))
            avg_elo = max(1000, avg_elo)
            
            aggregated[model_id] = ModelBenchmark(
                model_id=model_id,
                reasoning_score=avg_reasoning,
                coding_score=avg_coding,
                general_score=avg_general,
                elo_rating=avg_elo,
            )
        
        return aggregated
    
    async def _write_to_db(self, models: dict[str, ModelBenchmark], force: bool = False) -> None:
        """Write aggregated models to database.
        
        Always upserts all models to refresh benchmark data.
        The `force` flag is retained for backward compatibility but no longer affects behavior.
        """
        # Fetch existing to distinguish insert vs update for stats
        existing_ids = set()
        try:
            existing = self.db.get_benchmarks_for_models(list(models.keys()))
            existing_ids = set(existing.keys())
        except Exception:
            existing_ids = set()
        
        inserted = 0
        updated = 0
        
        for model_id, benchmark in models.items():
            self.db.upsert_benchmark(
                model_id=benchmark.model_id,
                reasoning_score=benchmark.reasoning_score,
                coding_score=benchmark.coding_score,
                general_score=benchmark.general_score,
                elo_rating=benchmark.elo_rating,
            )
            if model_id in existing_ids:
                updated += 1
            else:
                inserted += 1
        
        logger.info(f"Inserted {inserted} new models, updated {updated} existing models")
    
    def _generate_aliases(self, models: dict[str, ModelBenchmark]) -> int:
        """
        Generate aliases for models to improve routing accuracy.
        
        Creates aliases including:
        - Base model names (e.g., "gpt-4" for "openai/gpt-4")
        - Keyword-enhanced aliases for capability detection
        """
        # Keywords for capability detection (from RouterEngine)
        VISION_KEYWORDS = [
            'llava', 'pixtral', 'vision', 'gpt-4o', 'claude-3', 'claude-3.5',
            'gemini', 'minicpm', 'moondream', 'vision'
        ]
        
        TOOL_KEYWORDS = [
            'gpt-4', 'claude-3', 'claude-3.5', 'mistral-large',
            'qwen2.5', 'qwen-2.5', 'llama3.1', 'llama-3.1', 'command-r', 'hermes'
        ]
        
        aliases_created = 0
        
        for model_id, benchmark in models.items():
            # Extract base name from canonical ID
            if '/' in model_id:
                provider, model_name = model_id.split('/', 1)
                
                # Create base alias (just model name)
                self.db.upsert_alias(model_name, model_id, confidence=1.0)
                aliases_created += 1
                
                # Create keyword-enhanced aliases for capability detection
                model_lower = model_name.lower()
                
                # Check if model supports vision based on keywords or known capabilities
                supports_vision = any(kw in model_lower for kw in VISION_KEYWORDS)
                supports_tools = any(kw in model_lower for kw in TOOL_KEYWORDS)
                
                # If model supports vision but doesn't have keyword, add keyword alias
                if supports_vision and 'vision' not in model_lower:
                    # Create alias with vision keyword for router detection
                    vision_alias = f"{model_name}-vision"
                    self.db.upsert_alias(vision_alias, model_id, confidence=0.8)
                    aliases_created += 1
                
                # If model supports tools but doesn't have keyword, add keyword alias  
                if supports_tools and 'tools' not in model_lower and 'tool' not in model_lower:
                    # Create alias with tool keyword for router detection
                    tool_alias = f"{model_name}-tools"
                    self.db.upsert_alias(tool_alias, model_id, confidence=0.8)
                    aliases_created += 1
                
                # Also create provider-specific aliases for common naming patterns
                if provider == 'openai':
                    # OpenAI models often referenced without provider prefix
                    if 'gpt-4' in model_lower and 'vision' not in model_lower:
                        self.db.upsert_alias(f"gpt-4-vision", model_id, confidence=0.7)
                        aliases_created += 1
                    if 'gpt-4' in model_lower and 'tools' not in model_lower:
                        self.db.upsert_alias(f"gpt-4-tools", model_id, confidence=0.7)
                        aliases_created += 1
        
        logger.info(f"Created {aliases_created} aliases")
        return aliases_created
    
    def _update_metadata(self) -> None:
        """Update metadata table with build information."""
        self.db.set_metadata('last_build', datetime.now(timezone.utc).isoformat())
        self.db.set_metadata('sources_succeeded', self.stats['sources_succeeded'])
        self.db.set_metadata('sources_failed', self.stats['sources_failed'])
        self.db.set_metadata('total_models', self.stats['total_models'])
        self.db.set_metadata('build_duration_seconds', self.stats['duration'])
        
        # Vacuum to optimize
        self.db.vacuum()


async def build_provider_db(db_path: str | Path, force: bool = False) -> dict[str, Any]:
    """
    Convenience function to build provider.db.
    
    Args:
        db_path: Path to the SQLite database file
        force: If True, rebuild all models. If False, skip existing.
    
    Returns:
        Build statistics dictionary
    """
    builder = BenchmarkBuilder(db_path)
    return await builder.build(force=force)
