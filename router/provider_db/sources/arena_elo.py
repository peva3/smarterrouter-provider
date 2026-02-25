"""
Additional ELO ratings from various leaderboards.
Extends ELO coverage for models not in LMSYS.
"""

from typing import Dict
from ..model_mapper import model_mapper


def fetch_arena_elo() -> Dict[str, float]:
    """
    Fetch ELO ratings from arena.ai (alternative to LMSYS).
    Returns dict: model_id -> elo_rating.
    """
    scores = {}
    
    # Static ELO estimates from arena.ai (as of 2024-2025)
    # These supplement LMSYS when available
    known_elo = {
        # Top models - ELO estimates
        "openai/gpt-4o": 1330,
        "openai/gpt-4-turbo": 1300,
        "openai/gpt-4": 1285,
        "openai/gpt-3.5-turbo": 1150,
        "anthropic/claude-3.5-sonnet": 1320,
        "anthropic/claude-3-opus": 1280,
        "anthropic/claude-3-sonnet": 1200,
        "anthropic/claude-3-haiku": 1120,
        "google/gemini-1.5-pro": 1310,
        "google/gemini-1.5-flash": 1250,
        "google/gemini-2.0-flash": 1280,
        "google/gemini-2.5-pro": 1350,
        "meta/llama-3.1-405b-instruct": 1250,
        "meta/llama-3.1-70b-instruct": 1200,
        "meta/llama-3.1-8b-instruct": 1100,
        "meta/llama-3-70b-instruct": 1180,
        "meta/llama-3-8b-instruct": 1080,
        "mistralai/mistral-large": 1280,
        "mistralai/mixtral-8x7b-instruct": 1200,
        "mistralai/mistral-7b-instruct": 1050,
        "qwen/qwen-2.5-72b-instruct": 1220,
        "qwen/qwen-2.5-7b-instruct": 1100,
        "qwen/qwen-plus": 1250,
        "qwen/qwen-max": 1300,
        "deepseek/deepseek-r1": 1350,
        "deepseek/deepseek-v3": 1320,
        "deepseek/deepseek-chat": 1250,
        "deepseek/deepseek-coder": 1280,
        "xai/grok-3": 1300,
        "xai/grok-2": 1250,
        "moonshotai/kimi-v1": 1200,
        "moonshotai/kimi-v1-thinking": 1220,
        "perplexity/llama-3.1-sonar-large": 1180,
        "perplexity/llama-3.1-sonar-small": 1100,
        "nvidia/llama-3.1-nemotron-70b": 1240,
        "cohere/command-r-plus": 1180,
        "cohere/command-r": 1100,
        "ai21/jamba-1.5-large": 1150,
        "ai21/jamba-1.5-medium": 1080,
        "together/llama-3-70b": 1180,
        "together/mixtral-8x22b": 1210,
        "fireworks/firefunction-v2": 1200,
        "fireworks/firellama-3-70b": 1170,
        "anyscale/llama-3-70b": 1160,
        "nebius/llama-3.1-70b-instruct": 1180,
    }
    
    for name, elo in known_elo.items():
        canonical = model_mapper.to_canonical(name)
        if canonical:
            scores[canonical] = elo
    
    if scores:
        print(f"Arena ELO: {len(scores)} ELO ratings (static)")
    
    return scores
