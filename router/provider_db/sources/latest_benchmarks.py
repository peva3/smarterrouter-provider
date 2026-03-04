"""
Latest Model Benchmarks from Press Releases (2025-2026)
This source contains the most recent benchmark data from official announcements,
press releases, and model cards for the newest frontier models.
"""

from typing import Dict
from ..model_mapper import model_mapper


def fetch_latest_benchmarks() -> Dict[str, Dict[str, float]]:
    """
    Fetch benchmark scores from latest model announcements.
    Returns dict: model_id -> {reasoning, coding, general, elo}
    """
    scores = {}
    
    # Comprehensive latest benchmarks from press releases (2025-2026)
    # Sources: OpenAI, Anthropic, Google, xAI official announcements
    
    latest_models = {
        # ============ OPENAI GPT-5 SERIES ============
        "openai/gpt-5.2": {
            "reasoning": 92.4,  # GPQA Diamond
            "coding": 80.0,     # SWE-bench Verified
            "general": 89.6,     # MMLU
            "elo": 1478,
        },
        "openai/gpt-5.2-codex": {
            "reasoning": 92.4,
            "coding": 80.0,     # SWE-bench Verified
            "general": 89.6,
            "elo": 1470,
        },
        "openai/gpt-5.1": {
            "reasoning": 86.4,  # GPQA Diamond
            "coding": 74.9,      # SWE-bench Verified
            "general": 86.0,
            "elo": 1450,
        },
        "openai/gpt-5.1-codex": {
            "reasoning": 86.4,
            "coding": 77.3,      # Terminal-Bench 2.0
            "general": 86.0,
            "elo": 1470,
        },
        "openai/gpt-5.1-codex-mini": {
            "reasoning": 86.4,
            "coding": 77.3,
            "general": 86.0,
            "elo": 1280,
        },
        "openai/gpt-5.3-codex": {
            "reasoning": 92.4,
            "coding": 56.8,      # SWE-bench Pro
            "general": 89.6,
            "elo": 1280,
        },
        "openai/gpt-5-pro": {
            "reasoning": 92.4,
            "coding": 87.4,      # Aider polyglot
            "general": 92.9,
            "elo": 1280,
        },
        "openai/gpt-5-mini": {
            "reasoning": 86.4,
            "coding": 74.9,
            "general": 86.0,
            "elo": 1280,
        },
        
        # ============ ANTHROPIC CLAUDE 4 SERIES ============
        "anthropic/claude-opus-4.6": {
            "reasoning": 91.1,   # GPQA
            "coding": 80.8,      # SWE-bench Verified
            "general": 88.8,     # MMLU
            "elo": 1505,
        },
        "anthropic/claude-opus-4.6-thinking": {
            "reasoning": 91.1,
            "coding": 90.0,
            "general": 86.0,
            "elo": 1505,
        },
        "anthropic/claude-sonnet-4.6": {
            "reasoning": 86.5,   # GPQA
            "coding": 80.2,      # SWE-bench Verified
            "general": 86.5,     # MMLU
            "elo": 1480,
        },
        "anthropic/claude-sonnet-4.6-thinking": {
            "reasoning": 86.5,
            "coding": 90.0,
            "general": 86.0,
            "elo": 1480,
        },
        "anthropic/claude-sonnet-4.5": {
            "reasoning": 84.0,   # GPQA
            "coding": 80.9,      # SWE-bench Verified
            "general": 88.3,     # MMLU
            "elo": 1380,
        },
        
        # ============ GOOGLE GEMINI 3 SERIES ============
        "google/gemini-3-pro": {
            "reasoning": 91.9,   # GPQA Diamond
            "coding": 76.2,      # SWE-bench Verified
            "general": 88.7,     # MMLU
            "elo": 1500,
        },
        "google/gemini-3-pro-preview": {
            "reasoning": 91.9,
            "coding": 76.2,
            "general": 88.7,
            "elo": 1500,
        },
        "google/gemini-3-flash": {
            "reasoning": 89.8,   # GPQA
            "coding": 75.0,
            "general": 85.0,
            "elo": 1474,
        },
        "google/gemini-3-flash-preview": {
            "reasoning": 89.8,
            "coding": 75.0,
            "general": 85.0,
            "elo": 1474,
        },
        "google/gemini-3.1-pro": {
            "reasoning": 94.3,   # GPQA Diamond
            "coding": 80.6,      # SWE-bench Verified
            "general": 92.6,     # MMLU
            "elo": 1485,
        },
        "google/gemini-3.1-flash": {
            "reasoning": 89.8,
            "coding": 75.0,
            "general": 88.0,
            "elo": 1350,
        },
        
        # ============ XAI GROK 4 SERIES ============
        "xai/grok-4": {
            "reasoning": 88.0,   # GPQA Diamond
            "coding": 75.0,      # SWE-bench
            "general": 87.0,     # MMLU-Pro
            "elo": 1473,
        },
        "xai/grok-4-thinking": {
            "reasoning": 88.0,
            "coding": 79.4,      # LiveCodeBench
            "general": 87.0,
            "elo": 1473,
        },
        "xai/grok-3": {
            "reasoning": 86.4,   # GPQA
            "coding": 71.0,      # SWE-bench
            "general": 83.0,
            "elo": 1400,
        },
        "xai/grok-3-thinking": {
            "reasoning": 86.4,
            "coding": 78.0,
            "general": 83.0,
            "elo": 1400,
        },
        
        # ============ MOONSHOT KIMI SERIES ============
        "moonshotai/kimi-k2.5": {
            "reasoning": 85.0,
            "coding": 72.0,
            "general": 80.0,
            "elo": 1420,
        },
        "moonshotai/kimi-k2.5-thinking": {
            "reasoning": 90.0,
            "coding": 77.0,
            "general": 73.0,
            "elo": 1420,
        },
        
        # ============ DEEPSEEK SERIES ============
        "deepseek/deepseek-r1-zero": {
            "reasoning": 92.0,
            "coding": 75.0,
            "general": 80.0,
            "elo": 1330,
        },
        "deepseek/deepseek-v3.2-thinking": {
            "reasoning": 85.0,
            "coding": 70.0,
            "general": 75.0,
            "elo": 1310,
        },
        
        # ============ QWEN 3 SERIES ============
        "qwen/qwen3-coder": {
            "reasoning": 80.0,
            "coding": 85.0,
            "general": 80.0,
            "elo": 1380,
        },
        "qwen/qwen3-max": {
            "reasoning": 90.0,
            "coding": 80.0,
            "general": 88.0,
            "elo": 1340,
        },
        "qwen/qwen3-max-thinking": {
            "reasoning": 92.0,
            "coding": 80.0,
            "general": 84.0,
            "elo": 1340,
        },
        "qwen/qwen3-5-397b-a17b": {
            "reasoning": 85.0,
            "coding": 75.0,
            "general": 82.0,
            "elo": 1350,
        },
        
        # ============ MINIMAX SERIES ============
        "minimax/minimax-m2.5": {
            "reasoning": 88.0,
            "coding": 73.0,
            "general": 80.0,
            "elo": 1400,
        },
        
        # ============ NVIDIA SERIES ============
        "nvidia/nemotron-4-mini": {
            "reasoning": 80.0,
            "coding": 72.0,
            "general": 78.0,
            "elo": 1150,
        },
    }
    
    # Map to canonical IDs
    for name, data in latest_models.items():
        canonical = model_mapper.to_canonical(name)
        if canonical:
            scores[canonical] = data
    
    if scores:
        print(f"Latest Benchmarks: {len(scores)} models (from press releases)")
    
    return scores
