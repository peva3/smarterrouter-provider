"""
Provider DB Builder - Orchestrates fetching benchmark data from multiple sources.

This is the main entry point for building provider.db.
Run with: python -m router.provider_db.cli build
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar, Coroutine
from functools import wraps

from .database import ProviderDB
from .models import ModelBenchmark

logger = logging.getLogger(__name__)

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
                        logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. Retrying in {wait_time:.1f}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected error in async_retry")
        return wrapper
    return decorator


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
        logger.info(f"Starting provider.db build at {self.stats['start_time']}")
        
        try:
            # Initialize database
            self.db.initialize()
            
            # Get existing active model IDs before any changes
            existing_active_ids = self.db.get_active_model_ids()
            logger.info(f"Found {len(existing_active_ids)} active models in database")
            
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
            logger.info("Fetching OpenRouter model catalog...")
            try:
                from .sources.openrouter import OpenRouterFetcher
                openrouter_models = set(await OpenRouterFetcher().fetch())
                logger.info(f"OpenRouter has {len(openrouter_models)} total models")
                
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
                                elo_rating=int(estimated["elo_rating"]),
                                last_updated=datetime.now(timezone.utc),
                                archived=False
                            )
                            estimated_count += 1
                        else:
                            # Create ModelBenchmark with all defaults (0 scores, 1000 ELO)
                            aggregated[model_id] = ModelBenchmark(
                                model_id=model_id,
                                reasoning_score=0.0,
                                coding_score=0.0,
                                general_score=0.0,
                                elo_rating=1000,
                                last_updated=datetime.now(timezone.utc),
                                archived=False
                            )
                            added_count += 1
                
                if added_count > 0 or estimated_count > 0:
                    logger.info(f"Added {added_count} OpenRouter models with default scores")
                    logger.info(f"Estimated scores for {estimated_count} OpenRouter models using heuristics")
                    self.stats['models_added_defaults'] = added_count
                    self.stats['models_estimated'] = estimated_count
                    
            except Exception as e:
                logger.warning(f"Failed to fetch OpenRouter models: {e}. Proceeding with only benchmarked models.")
            
            # Write to database
            logger.info(f"Writing {len(aggregated)} models to database...")
            await self._write_to_db(aggregated, force=force)
            
            # Handle archiving: models in DB but not in OpenRouter
            archived_count = 0
            reactivated_count = 0
            if openrouter_models:
                models_to_archive = existing_active_ids - openrouter_models
                for model_id in models_to_archive:
                    self.db.archive_model(model_id)
                    archived_count += 1
                
                # Handle reactivation: archived models that are back in OpenRouter
                archived_in_db = existing_active_ids & (openrouter_models - set(aggregated.keys()))
                for model_id in archived_in_db:
                    self.db.unarchive_model(model_id)
                    reactivated_count += 1
                
                if archived_count > 0:
                    logger.info(f"Archived {archived_count} models no longer in OpenRouter")
                if reactivated_count > 0:
                    logger.info(f"Reactivated {reactivated_count} models back in OpenRouter")
                
                self.stats['models_archived'] = archived_count
                self.stats['models_reactivated'] = reactivated_count
            
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
        
        async def fetch_arena():
            """Fetch from arena.ai (primary ELO source)."""
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
        
        async def fetch_lmsys():
            """Fetch from LMSYS (fallback ELO source)."""
            try:
                from .sources.lmsys_arena import fetch_lmsys_arena
                self.stats['sources_attempted'].append('lmsys')
                result = await fetch_lmsys_arena()
                if result:
                    self.stats['sources_succeeded'].append('lmsys')
                    logger.info(f"LMSYS: fetched {len(result)} ELO ratings")
                return {'elo': result}
            except Exception as e:
                logger.error(f"LMSYS fetch failed: {e}")
                self.stats['sources_failed'].append('lmsys')
                return {'elo': {}}
        
        async def fetch_livebench():
            try:
                from .sources.livebench import fetch_livebench
                self.stats['sources_attempted'].append('livebench')
                result = await fetch_livebench()
                if result:
                    self.stats['sources_succeeded'].append('livebench')
                    logger.info(f"LiveBench: fetched {len(result)} reasoning scores")
                return {'reasoning': result}
            except Exception as e:
                logger.error(f"LiveBench fetch failed: {e}")
                self.stats['sources_failed'].append('livebench')
                return {'reasoning': {}}
        
        async def fetch_bigcodebench():
            try:
                from .sources import bigcodebench
                self.stats['sources_attempted'].append('bigcodebench')
                # This is sync but we run in executor
                result = await asyncio.to_thread(bigcodebench.fetch_bigcodebench)
                if result:
                    self.stats['sources_succeeded'].append('bigcodebench')
                    logger.info(f"BigCodeBench: fetched {len(result)} coding scores")
                return {'coding': result}
            except Exception as e:
                logger.error(f"BigCodeBench fetch failed: {e}")
                self.stats['sources_failed'].append('bigcodebench')
                return {'coding': {}}
        
        async def fetch_mmlu():
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
        
        async def fetch_mmlu_pro():
            try:
                from .sources import mmlu_pro
                self.stats['sources_attempted'].append('mmlu_pro')
                result = await asyncio.to_thread(mmlu_pro.fetch_mmlu_pro)
                if result:
                    self.stats['sources_succeeded'].append('mmlu_pro')
                    logger.info(f"MMLU-Pro: fetched {len(result)} general scores")
                return {'general': result}  # Merge into general
            except Exception as e:
                logger.error(f"MMLU-Pro fetch failed: {e}")
                self.stats['sources_failed'].append('mmlu_pro')
                return {'general': {}}
        
        async def fetch_gsm8k():
            try:
                from .sources import gsm8k
                self.stats['sources_attempted'].append('gsm8k')
                result = await asyncio.to_thread(gsm8k.fetch_gsm8k)
                if result:
                    self.stats['sources_succeeded'].append('gsm8k')
                    logger.info(f"GSM8K: fetched {len(result)} reasoning scores")
                return {'reasoning': result}  # Merge into reasoning
            except Exception as e:
                logger.error(f"GSM8K fetch failed: {e}")
                self.stats['sources_failed'].append('gsm8k')
                return {'reasoning': {}}
        
        async def fetch_humaneval():
            try:
                from .sources import humaneval
                self.stats['sources_attempted'].append('humaneval')
                result = await asyncio.to_thread(humaneval.fetch_humaneval)
                if result:
                    self.stats['sources_succeeded'].append('humaneval')
                    logger.info(f"HumanEval: fetched {len(result)} coding scores")
                return {'coding': result}  # Merge into coding
            except Exception as e:
                logger.error(f"HumanEval fetch failed: {e}")
                self.stats['sources_failed'].append('humaneval')
                return {'coding': {}}
        
        async def fetch_swebench():
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
                
        async def fetch_aider():
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
                
        async def fetch_agieval():
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
                
        async def fetch_mathvista():
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
        
        async def fetch_livecodebench():
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
        
        async def fetch_frontiermath():
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
        
        async def fetch_aime():
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
        
        async def fetch_scicode():
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
        
        async def fetch_megabench():
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
        
        async def fetch_mixeval_x():
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
        
        async def fetch_gpqa():
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
        
        async def fetch_stateval():
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
        
        async def fetch_chinese():
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
        
        async def fetch_tool_use():
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
        
        async def fetch_vision():
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
        
        async def fetch_ailuminate():
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
        
        async def fetch_domain_specific():
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
        
        async def fetch_helm():
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

        async def fetch_arc():
            try:
                from .sources import arc
                self.stats['sources_attempted'].append('arc')
                result = await asyncio.to_thread(arc.fetch_arc)
                if result:
                    self.stats['sources_succeeded'].append('arc')
                    logger.info(f"ARC: fetched {len(result)} reasoning scores")
                return {'reasoning': result}  # Merge into reasoning
            except Exception as e:
                logger.error(f"ARC fetch failed: {e}")
                self.stats['sources_failed'].append('arc')
                return {'reasoning': {}}
        
        async def fetch_bbh():
            try:
                from .sources import bbh
                self.stats['sources_attempted'].append('bbh')
                result = await asyncio.to_thread(bbh.fetch_bbh)
                if result:
                    self.stats['sources_succeeded'].append('bbh')
                    logger.info(f"BBH: fetched {len(result)} reasoning scores")
                return {'reasoning': result}  # Merge into reasoning
            except Exception as e:
                logger.error(f"BBH fetch failed: {e}")
                self.stats['sources_failed'].append('bbh')
                return {'reasoning': {}}
        
        # Run all fetchers in parallel
        results = await asyncio.gather(
            fetch_arena(),
            fetch_lmsys(),
            fetch_livebench(),
            fetch_bigcodebench(),
            fetch_mmlu(),
            fetch_mmlu_pro(),
            fetch_gsm8k(),
            fetch_humaneval(),
            fetch_arc(),
            fetch_bbh(),
            fetch_swebench(),
            fetch_aider(),
            fetch_agieval(),
            fetch_mathvista(),
            fetch_livecodebench(),
            fetch_frontiermath(),
            fetch_aime(),
            fetch_scicode(),
            fetch_megabench(),
            fetch_mixeval_x(),
            fetch_gpqa(),
            fetch_stateval(),
            fetch_chinese(),
            fetch_tool_use(),
            fetch_vision(),
            fetch_ailuminate(),
            fetch_domain_specific(),
            fetch_helm(),
        )
        
        # Merge results
        merged = {}
        for result in results:
            for category, scores in result.items():
                for model_id, score in scores.items():
                    if model_id not in merged:
                        merged[model_id] = {}
                    merged[model_id][category] = score
        
        logger.info(f"Total unique models from all sources: {len(merged)}")
        return merged
    
    def _aggregate_scores(self, scores: dict[str, dict[str, Any]]) -> dict[str, ModelBenchmark]:
        """
        Aggregate scores from multiple sources for each model.
        
        Handles conflicts by averaging if the same model appears in the same category
        from multiple sources (though this is rare in practice since each source
        provides different score types).
        """
        aggregated = {}
        
        for model_id, categories in scores.items():
            reasoning_scores = []
            coding_scores = []
            general_scores = []
            elo_ratings = []
            
            # Collect scores by category
            if 'reasoning' in categories:
                reasoning_scores.append(categories['reasoning'])
            # Note: LiveBench might also have 'coding' or 'general' if API returns more
            
            if 'coding' in categories:
                coding_scores.append(categories['coding'])
            
            if 'general' in categories:
                general_scores.append(categories['general'])
            
            if 'elo' in categories:
                elo_ratings.append(categories['elo'])
            
            # Average if multiple scores for same category (conflict resolution)
            avg_reasoning = sum(reasoning_scores) / len(reasoning_scores) if reasoning_scores else 0.0
            avg_coding = sum(coding_scores) / len(coding_scores) if coding_scores else 0.0
            avg_general = sum(general_scores) / len(general_scores) if general_scores else 1000
            avg_elo = int(sum(elo_ratings) / len(elo_ratings)) if elo_ratings else 1000
            
            # Ensure within valid ranges
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
                archived=False,
            )
        
        return aggregated
    
    async def _write_to_db(self, models: dict[str, ModelBenchmark], force: bool = False) -> None:
        """Write aggregated models to database."""
        
        # Check existing if not forcing
        existing = {}
        if not force:
            existing = self.db.get_benchmarks_for_models(list(models.keys()))
        
        written = 0
        skipped = 0
        
        for model_id, benchmark in models.items():
            # Skip if already exists and not forcing
            if not force and model_id in existing:
                skipped += 1
                continue
            
            self.db.upsert_benchmark(
                model_id=benchmark.model_id,
                reasoning_score=benchmark.reasoning_score,
                coding_score=benchmark.coding_score,
                general_score=benchmark.general_score,
                elo_rating=benchmark.elo_rating,
                archived=benchmark.archived,
            )
            written += 1
        
        logger.info(f"Wrote {written} new models, skipped {skipped} existing (force={force})")
    
    def _generate_aliases(self, models: dict[str, ModelBenchmark]) -> int:
        """
        Generate aliases for models to improve routing accuracy.
        
        Creates aliases including:
        - Base model names (e.g., "gpt-4" for "openai/gpt-4")
        - Vision keyword aliases (for capability detection)
        - Tool keyword aliases (for capability detection)
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
                
                # Create vision-capable alias if applicable
                model_lower = model_name.lower()
                if any(kw in model_lower for kw in VISION_KEYWORDS):
                    vision_alias = f"{model_id}-vision"
                    self.db.upsert_alias(vision_alias, model_id, confidence=0.9)
                    aliases_created += 1
                
                # Create tool-capable alias if applicable
                if any(kw in model_lower for kw in TOOL_KEYWORDS):
                    tool_alias = f"{model_id}-tools"
                    self.db.upsert_alias(tool_alias, model_id, confidence=0.9)
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
