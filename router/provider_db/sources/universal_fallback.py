"""
Universal fallback scores for ALL models.
This ensures 100% coverage by providing reasonable estimates for any model.
Uses provider patterns, model size, and version information.
"""

from typing import Dict
import re
from ..model_mapper import model_mapper


# Provider baseline ELO scores
PROVIDER_ELO = {
    "openai": 1200,
    "anthropic": 1200,
    "google": 1180,
    "meta": 1100,
    "mistralai": 1150,
    "qwen": 1100,
    "deepseek": 1180,
    "xai": 1150,
    "moonshotai": 1150,
    "minimax": 1150,
    "cohere": 1080,
    "ai21": 1080,
    "baichuan": 1050,
    "01-ai": 1050,
    "z-ai": 1100,  # Zhipu/GLM
    "amazon": 1050,
    "nvidia": 1100,
    "microsoft": 1000,
    "stabilityai": 1000,
    "tiiuae": 1000,
    "bigcode": 1000,
    "wizardlm": 1050,
    "NousResearch": 1000,
    "together": 1050,
    "perplexity": 1080,
    "upstage": 1050,
    "fireworks": 1050,
    "anyscale": 1030,
    "nebius": 1050,
    "snowflake": 1080,
    "databricks": 1050,
    "ibm": 1000,
    "arc53": 950,
    "aeon": 950,
    "jondurbin": 900,
    "togethercomputer": 1000,
    "lmsys": 1000,
    "stanford": 1000,
    "allenai": 1000,
    "eleutherai": 950,
}


def _extract_provider(model_id: str) -> str:
    """Extract provider from model ID."""
    parts = model_id.split("/")
    if len(parts) >= 2:
        return parts[0].lower()
    # Try to match from model name itself
    model_name = parts[0].lower() if parts else ""
    for provider in PROVIDER_ELO:
        if provider in model_name:
            return provider
    return "unknown"


def _extract_size(model_id: str) -> int:
    """Extract model size in billions from model ID."""
    model_name = model_id.lower()
    
    # Try to find size patterns like "70b", "8b", "7b", etc.
    patterns = [
        r'(\d+)b(?:\s|$|_)',  # 70b, 8b, 7b
        r'(\d+)b(?:\s|$|_)',  # 405b
        r'(\d+)b',  # Any b suffix
    ]
    
    for pattern in patterns:
        match = re.search(pattern, model_name)
        if match:
            size = int(match.group(1))
            if size > 100:  # Probably MB, convert
                size = size // 1000
            return size
    
    # Check for specific known sizes
    if "gpt-4" in model_name:
        return 100  # Assume GPT-4 is ~100B
    if "gpt-3.5" in model_name:
        return 20   # ~20B
    if "claude-3" in model_name:
        return 100  # Claude 3 family
    if "claude-2" in model_name:
        return 80
    if "llama-3.1" in model_name and "405" in model_name:
        return 405
    if "llama-3" in model_name and "70" in model_name:
        return 70
    if "llama-3" in model_name and "8" in model_name:
        return 8
    if "llama-2" in model_name and "70" in model_name:
        return 70
    if "llama-2" in model_name and "13" in model_name:
        return 13
    if "llama-2" in model_name and "7" in model_name:
        return 7
    
    return 7  # Default assumption


def _extract_version(model_id: str) -> int:
    """Extract version number from model ID."""
    model_name = model_id.lower()
    
    # Try to find version patterns
    patterns = [
        r'(\d+)\.',  # 3.0, 2.0, etc.
        r'-v(\d+)',  # -v1, -v2
        r'_v(\d+)',  # _v1
    ]
    
    for pattern in patterns:
        match = re.search(pattern, model_name)
        if match:
            return int(match.group(1))
    
    # Check for specific version indicators
    if "4o" in model_name or "gpt-4o" in model_name:
        return 4
    if "turbo" in model_name:
        return 3
    if "mini" in model_name or "small" in model_name:
        return 2
    
    return 1  # Default version


def fetch_universal_fallback() -> Dict[str, float]:
    """
    Fetch universal fallback ELO for ANY model.
    This ensures 100% coverage by estimating ELO for all models.
    """
    scores = {}
    
    # This would typically be called with the full list of models
    # But we'll use a pattern-based approach
    
    # For now, return empty - this is handled differently
    return scores


def estimate_elo_for_model(model_id: str) -> int:
    """
    Estimate ELO for a single model based on provider, size, and version.
    """
    provider = _extract_provider(model_id)
    size = _extract_size(model_id)
    version = _extract_version(model_id)
    
    # Base ELO from provider
    base_elo = PROVIDER_ELO.get(provider, 1000)
    
    # Size adjustment (larger models = better)
    # Use logarithmic scaling - each doubling adds ~50 ELO
    if size > 0:
        size_bonus = int(50 * (size ** 0.3))  # Diminishing returns
    else:
        size_bonus = 0
    
    # Version adjustment
    version_bonus = (version - 1) * 20
    
    # Calculate final ELO
    estimated_elo = base_elo + size_bonus + version_bonus
    
    # Clamp to reasonable range
    estimated_elo = max(900, min(1500, estimated_elo))
    
    return estimated_elo
