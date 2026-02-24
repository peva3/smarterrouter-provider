"""
Heuristic score estimator for models without direct benchmark data.
Uses model name patterns, provider reputation, size, and category to estimate scores.
"""

import re
from typing import Dict


# Comprehensive provider baselines (realistic defaults for 2024-2025)
PROVIDER_BASELINES = {
    # Tier 1: Top providers (real benchmark data available)
    "openai": {"reasoning": 75.0, "coding": 80.0, "general": 85.0, "elo": 1280},
    "anthropic": {"reasoning": 72.0, "coding": 75.0, "general": 82.0, "elo": 1260},
    "google": {"reasoning": 70.0, "coding": 72.0, "general": 80.0, "elo": 1240},
    "deepseek": {"reasoning": 68.0, "coding": 70.0, "general": 75.0, "elo": 1220},
    
    # Tier 2: Strong providers
    "meta": {"reasoning": 60.0, "coding": 58.0, "general": 65.0, "elo": 1150},
    "mistralai": {"reasoning": 62.0, "coding": 60.0, "general": 68.0, "elo": 1180},
    "qwen": {"reasoning": 65.0, "coding": 66.0, "general": 70.0, "elo": 1190},
    "moonshotai": {"reasoning": 66.0, "coding": 64.0, "general": 70.0, "elo": 1200},
    "z-ai": {"reasoning": 70.0, "coding": 72.0, "general": 78.0, "elo": 1250},
    "minimax": {"reasoning": 68.0, "coding": 70.0, "general": 75.0, "elo": 1220},
    "xai": {"reasoning": 67.0, "coding": 65.0, "general": 72.0, "elo": 1210},
    "cohere": {"reasoning": 60.0, "coding": 58.0, "general": 65.0, "elo": 1150},
    "ai21": {"reasoning": 58.0, "coding": 55.0, "general": 62.0, "elo": 1120},
    "01-ai": {"reasoning": 62.0, "coding": 60.0, "general": 66.0, "elo": 1170},
    "baichuan": {"reasoning": 55.0, "coding": 52.0, "general": 58.0, "elo": 1100},
    "microsoft": {"reasoning": 70.0, "coding": 72.0, "general": 78.0, "elo": 1240},
    "nvidia": {"reasoning": 68.0, "coding": 70.0, "general": 75.0, "elo": 1220},
    
    # Tier 3: Specialized/Regional providers
    "upstage": {"reasoning": 65.0, "coding": 63.0, "general": 68.0, "elo": 1180},
    "together": {"reasoning": 60.0, "coding": 58.0, "general": 64.0, "elo": 1140},
    "baidu": {"reasoning": 65.0, "coding": 62.0, "general": 70.0, "elo": 1180},
    "tencent": {"reasoning": 63.0, "coding": 60.0, "general": 66.0, "elo": 1160},
    "bytedance": {"reasoning": 60.0, "coding": 58.0, "general": 62.0, "elo": 1140},
    "alibaba": {"reasoning": 62.0, "coding": 60.0, "general": 65.0, "elo": 1150},
    
    # Tier 4: Emerging/Specialized providers (need heuristics)
    "amazon": {"reasoning": 55.0, "coding": 50.0, "general": 58.0, "elo": 1100},
    "allenai": {"reasoning": 58.0, "coding": 55.0, "general": 62.0, "elo": 1120},
    "arcee-ai": {"reasoning": 50.0, "coding": 55.0, "general": 52.0, "elo": 1080},
    "nousresearch": {"reasoning": 55.0, "coding": 52.0, "general": 58.0, "elo": 1100},
    "perplexity": {"reasoning": 58.0, "coding": 45.0, "general": 62.0, "elo": 1120},
    "sao10k": {"reasoning": 50.0, "coding": 52.0, "general": 52.0, "elo": 1060},
    "liquid": {"reasoning": 52.0, "coding": 48.0, "general": 55.0, "elo": 1070},
    "thedrummer": {"reasoning": 48.0, "coding": 50.0, "general": 50.0, "elo": 1050},
    "aion-labs": {"reasoning": 45.0, "coding": 42.0, "general": 48.0, "elo": 1030},
    "inception": {"reasoning": 45.0, "coding": 48.0, "general": 48.0, "elo": 1040},
    "inflection": {"reasoning": 50.0, "coding": 45.0, "general": 52.0, "elo": 1060},
    "morph": {"reasoning": 48.0, "coding": 45.0, "general": 50.0, "elo": 1050},
    "neversleep": {"reasoning": 45.0, "coding": 42.0, "general": 48.0, "elo": 1030},
    "relace": {"reasoning": 42.0, "coding": 45.0, "general": 45.0, "elo": 1020},
    "stepfun": {"reasoning": 48.0, "coding": 45.0, "general": 50.0, "elo": 1050},
    "deepcogito": {"reasoning": 50.0, "coding": 48.0, "general": 52.0, "elo": 1060},
    "prime-intellect": {"reasoning": 48.0, "coding": 45.0, "general": 50.0, "elo": 1050},
    "gryphe": {"reasoning": 45.0, "coding": 48.0, "general": 48.0, "elo": 1040},
    "essentialai": {"reasoning": 42.0, "coding": 45.0, "general": 45.0, "elo": 1020},
    "raifle": {"reasoning": 45.0, "coding": 48.0, "general": 48.0, "elo": 1040},
    "switchpoint": {"reasoning": 40.0, "coding": 42.0, "general": 42.0, "elo": 1010},
    "tngtech": {"reasoning": 45.0, "coding": 48.0, "general": 48.0, "elo": 1040},
    "undi95": {"reasoning": 45.0, "coding": 48.0, "general": 48.0, "elo": 1040},
    "writer": {"reasoning": 48.0, "coding": 45.0, "general": 50.0, "elo": 1050},
    "alpindale": {"reasoning": 42.0, "coding": 45.0, "general": 45.0, "elo": 1020},
    "anthracite-org": {"reasoning": 45.0, "coding": 48.0, "general": 48.0, "elo": 1040},
    "cognitivecomputations": {"reasoning": 48.0, "coding": 45.0, "general": 50.0, "elo": 1050},
    "eleutherai": {"reasoning": 50.0, "coding": 48.0, "general": 52.0, "elo": 1060},
    "mancer": {"reasoning": 45.0, "coding": 48.0, "general": 48.0, "elo": 1040},
    "opengvlab": {"reasoning": 52.0, "coding": 50.0, "general": 55.0, "elo": 1070},
    "kwaipilot": {"reasoning": 45.0, "coding": 50.0, "general": 48.0, "elo": 1040},
    "nex-agi": {"reasoning": 45.0, "coding": 48.0, "general": 48.0, "elo": 1040},
    "alfredpros": {"reasoning": 42.0, "coding": 48.0, "general": 45.0, "elo": 1020},
    "xiaomi": {"reasoning": 50.0, "coding": 48.0, "general": 52.0, "elo": 1060},
    "meituan": {"reasoning": 45.0, "coding": 48.0, "general": 48.0, "elo": 1040},
    "ibm-granite": {"reasoning": 50.0, "coding": 48.0, "general": 52.0, "elo": 1060},
    "openrouter": {"reasoning": 45.0, "coding": 42.0, "general": 48.0, "elo": 1030},
}


def extract_size_parameters(model_name: str) -> float:
    """Extract parameter count in billions from model name."""
    name_lower = model_name.lower()
    
    # Ultra-large models (>100B)
    if "405b" in name_lower or "400b" in name_lower:
        return 405.0
    if "340b" in name_lower:
        return 340.0
    if "235b" in name_lower:
        return 235.0
    if "300b" in name_lower or "424b" in name_lower:
        return 300.0
    
    # Large models (70B-100B)
    if "110b" in name_lower:
        return 110.0
    if "90b" in name_lower:
        return 90.0
    if "80b" in name_lower:
        return 80.0
    if "70b" in name_lower:
        return 70.0
    
    # Medium-large (30B-70B)
    if "36b" in name_lower:
        return 36.0
    if "34b" in name_lower:
        return 34.0
    if "32b" in name_lower:
        return 32.0
    if "30b" in name_lower:
        return 30.0
    
    # Medium (13B-30B)
    if "24b" in name_lower:
        return 24.0
    if "20b" in name_lower:
        return 20.0
    if "27b" in name_lower:
        return 27.0
    if "13b" in name_lower:
        return 13.0
    if "14b" in name_lower:
        return 14.0
    
    # Small (7B-13B)
    if "12b" in name_lower:
        return 12.0
    if "11b" in name_lower:
        return 11.0
    if "8b" in name_lower:
        return 8.0
    if "7b" in name_lower:
        return 7.0
    if "9b" in name_lower:
        return 9.0
    
    # Tiny (<7B)
    if "6b" in name_lower:
        return 6.0
    if "3b" in name_lower:
        return 3.0
    if "2b" in name_lower:
        return 2.0
    if "1b" in name_lower or "1.2b" in name_lower or "1.6b" in name_lower:
        return 1.5
    if "0.5b" in name_lower or "500m" in name_lower:
        return 0.5
    
    return 7.0  # Default assumption


def get_size_modifier(model_name: str) -> float:
    """
    Returns a multiplier based on model size in parameters.
    Uses a logarithmic scale since larger models have diminishing returns.
    """
    params = extract_size_parameters(model_name)
    
    # Logarithmic scaling: 7B = 1.0, 70B = 1.2, 405B = 1.35
    if params >= 100:
        return 1.35
    elif params >= 70:
        return 1.25
    elif params >= 30:
        return 1.15
    elif params >= 13:
        return 1.05
    elif params >= 7:
        return 0.95
    elif params >= 3:
        return 0.85
    else:
        return 0.75


def get_variant_modifier(model_name: str) -> dict:
    """
    Adjust scores based on model variant (reasoning, coding, vision, etc.)
    """
    name_lower = model_name.lower()
    
    modifiers = {"reasoning": 1.0, "coding": 1.0, "general": 1.0, "elo": 1.0}
    
    # Reasoning-focused models (strong boost)
    if any(x in name_lower for x in ["r1", "reasoning", "think", "cot", "o1", "o2", "o3", "o4", "grok-3", "grok3"]):
        modifiers["reasoning"] *= 1.35
        modifiers["coding"] *= 1.15
        modifiers["general"] *= 1.1
    
    # Thinking variants (newer reasoning approach)
    if "think" in name_lower or "thinking" in name_lower:
        modifiers["reasoning"] *= 1.25
        modifiers["coding"] *= 1.1
    
    # Coding-focused models
    if any(x in name_lower for x in ["coder", "codex", "code", "programmer", "codefast", "code-fast"]):
        modifiers["coding"] *= 1.5
        modifiers["reasoning"] *= 1.05
    
    # Vision/Multimodal models
    if any(x in name_lower for x in ["vision", "vl", "pixtral", "llava", "moondream", "minicpm"]):
        modifiers["general"] *= 1.15
        modifiers["reasoning"] *= 1.05
    
    # Search/Research models (good at general, weak at coding)
    if any(x in name_lower for x in ["search", "research", "sonar", "deep-research", "deepresearch"]):
        modifiers["general"] *= 1.2
        modifiers["coding"] *= 0.7
        modifiers["reasoning"] *= 1.1
    
    # Security/Safety models (specialized, lower general scores)
    if any(x in name_lower for x in ["guard", "safety", "security", "protect"]):
        modifiers["reasoning"] *= 0.8
        modifiers["coding"] *= 0.8
        modifiers["general"] *= 0.7
    
    # Free tier models (typically weaker)
    if ":free" in model_name or "free" in name_lower:
        modifiers["reasoning"] *= 0.85
        modifiers["coding"] *= 0.85
        modifiers["general"] *= 0.85
    
    # Mini/Lite variants (reduced capability)
    if any(x in name_lower for x in ["mini", "lite", "small", "tiny", "nano", "micro"]):
        modifiers["reasoning"] *= 0.85
        modifiers["coding"] *= 0.85
        modifiers["general"] *= 0.85
    
    # Flash variants (optimized for speed)
    if "flash" in name_lower:
        modifiers["reasoning"] *= 0.9
        modifiers["coding"] *= 0.9
        modifiers["general"] *= 0.9
    
    # Premier/Pro variants (stronger)
    if any(x in name_lower for x in ["premier", "pro", "ultra", "max"]):
        modifiers["reasoning"] *= 1.15
        modifiers["coding"] *= 1.15
        modifiers["general"] *= 1.15
    
    # Instruction-tuned
    if any(x in name_lower for x in ["instruct", "chat", "dialogue"]):
        modifiers["general"] *= 1.1
    
    # Preview variants
    if "preview" in name_lower or "beta" in name_lower:
        modifiers["reasoning"] *= 0.95
        modifiers["coding"] *= 0.95
        modifiers["general"] *= 0.95
    
    return modifiers


def get_category_modifier(model_name: str) -> dict:
    """
    Apply category-specific adjustments based on detected model type.
    """
    name_lower = model_name.lower()
    
    modifiers = {"reasoning": 1.0, "coding": 1.0, "general": 1.0, "elo": 1.0}
    
    # Search engines (high general, low coding)
    if "search" in name_lower or "sonar" in name_lower or "perplexity" in name_lower:
        modifiers["coding"] *= 0.65
        modifiers["general"] *= 1.15
    
    # Research models
    if "research" in name_lower or "olmo" in name_lower or "allenai" in name_lower:
        modifiers["reasoning"] *= 1.1
        modifiers["general"] *= 1.05
    
    # Code execution/agents
    if "agent" in name_lower or "tool" in name_lower or "function" in name_lower:
        modifiers["coding"] *= 1.2
    
    # Long context models
    if "long" in name_lower or "context" in name_lower or "192k" in name_lower or "128k" in name_lower:
        modifiers["general"] *= 1.05
    
    return modifiers


def estimate_scores(model_id: str) -> Dict[str, float | int] | None:
    """
    Estimate benchmark scores for a model based on its name and provider.
    
    Uses multiple heuristics:
    1. Provider reputation baseline
    2. Model size (parameter count)
    3. Variant type (reasoning, coding, vision, etc.)
    4. Category detection (search, research, etc.)
    
    Args:
        model_id: OpenRouter model ID (e.g., "openai/gpt-4o")
        
    Returns:
        Dict with reasoning_score, coding_score, general_score, elo_rating
        Or None if cannot estimate
    """
    # Extract provider from model_id
    if "/" not in model_id:
        return None
    
    provider = model_id.split("/")[0].lower()
    model_name = model_id.split("/")[-1].lower()
    
    # Get provider baseline
    if provider not in PROVIDER_BASELINES:
        # Try to match with partial provider name
        for known_provider in PROVIDER_BASELINES:
            if known_provider in provider or provider in known_provider:
                provider = known_provider
                break
        else:
            # Default for unknown providers
            provider = "openrouter"
    
    baseline = PROVIDER_BASELINES.get(provider, PROVIDER_BASELINES["openrouter"]).copy()
    
    # Apply size modifier
    size_mod = get_size_modifier(model_id)
    for key in baseline:
        if key != "elo":
            baseline[key] *= size_mod
    
    # Apply variant modifiers
    variant_mods = get_variant_modifier(model_id)
    for key in baseline:
        if key != "elo":
            baseline[key] *= variant_mods[key]
    
    # Apply category modifiers
    category_mods = get_category_modifier(model_id)
    for key in baseline:
        if key != "elo":
            baseline[key] *= category_mods[key]
    
    # Ensure within valid bounds
    baseline["reasoning_score"] = max(0.0, min(100.0, baseline["reasoning"]))
    baseline["coding_score"] = max(0.0, min(100.0, baseline["coding"]))
    baseline["general_score"] = max(0.0, min(100.0, baseline["general"]))
    baseline["elo_rating"] = max(1000, min(1400, int(baseline["elo"])))
    
    return {
        "reasoning_score": baseline["reasoning_score"],
        "coding_score": baseline["coding_score"],
        "general_score": baseline["general_score"],
        "elo_rating": baseline["elo_rating"],
    }


def fetch_heuristics() -> Dict[str, Dict[str, float]]:
    """
    This is not a real fetcher - it's used by builder to estimate scores.
    Returns empty dict because builder will call estimate_scores directly.
    """
    return {}
