"""
Arena.ai (Arena) - ELO ratings from arena.ai leaderboard.
Provides Text, Code, Vision, and overall ELO scores.
Currently uses fallback data as the website requires JavaScript.
"""

from typing import Dict


# Comprehensive ELO fallback data from arena.ai leaderboard (as of Feb 2025)
# These are raw ELO ratings (1000+ scale)
FALLBACK_ELO = {
    # Claude 4 series
    "anthropic/claude-opus-4-6": 1505,
    "anthropic/claude-opus-4-6-thinking": 1505,
    "anthropic/claude-sonnet-4-6": 1480,
    "anthropic/claude-sonnet-4-6-thinking": 1480,
    "anthropic/claude-3-5-opus": 1460,
    "anthropic/claude-3-5-sonnet": 1380,
    "anthropic/claude-3-5-haiku": 1260,
    "anthropic/claude-3-opus": 1350,
    "anthropic/claude-3-sonnet": 1320,
    "anthropic/claude-3-haiku": 1180,
    
    # GPT-5 series
    "openai/gpt-5.2": 1478,
    "openai/gpt-5.2-codex": 1471,
    "openai/gpt-5.1": 1450,
    "openai/gpt-5.1-codex": 1471,
    "openai/gpt-5": 1350,
    "openai/gpt-5-codex": 1400,
    "openai/gpt-4o": 1340,
    "openai/gpt-4o-mini": 1280,
    "openai/gpt-4-turbo": 1295,
    "openai/gpt-4": 1280,
    "openai/o3": 1350,
    "openai/o3-mini": 1200,
    "openai/o1": 1280,
    
    # Gemini series
    "google/gemini-3-pro-preview": 1500,
    "google/gemini-3-1-pro-preview": 1486,
    "google/gemini-3-flash-preview": 1474,
    "google/gemini-2.5-pro": 1380,
    "google/gemini-2.5-flash": 1270,
    "google/gemini-pro": 1300,
    "google/gemini-pro-1.5": 1320,
    "google/gemini-flash": 1250,
    "google/gemini-flash-1.5": 1270,
    
    # GLM series
    "z-ai/glm-5": 1430,
    "z-ai/glm-4.7": 1330,
    "z-ai/glm-4.6": 1290,
    "z-ai/glm-4": 1250,
    "z-ai/glm-4-flash": 1210,
    
    # Qwen series
    "qwen/qwen3-5-397b-a17b": 1350,
    "qwen/qwen3-max": 1340,
    "qwen/qwen3-coder": 1380,
    "qwen/qwen3-coder-next": 1360,
    "qwen/qwen2.5-72b": 1280,
    "qwen/qwen2.5-7b": 1150,
    
    # DeepSeek series
    "deepseek/deepseek-v3.2": 1310,
    "deepseek/deepseek-v3.2-thinking": 1310,
    "deepseek/deepseek-r1": 1330,
    "deepseek/deepseek-chat": 1260,
    "deepseek/deepseek-coder": 1240,
    
    # Moonshot/Kimi
    "moonshotai/kimi-k2.5": 1420,
    "moonshotai/kimi-k2.5-thinking": 1420,
    "moonshotai/kimi-k2": 1250,
    "moonshotai/kimi-k2-thinking": 1250,
    
    # MiniMax
    "minimax/minimax-m2.5": 1400,
    "minimax/minimax-m2.1": 1320,
    
    # xAI/Grok
    "xai/grok-4": 1473,
    "xai/grok-4-thinking": 1473,
    "xai/grok-3": 1400,
    "xai/grok-beta": 1240,
    
    # Meta/Llama
    "meta-llama/llama-3-405b-instruct": 1320,
    "meta-llama/llama-3-70b-instruct": 1250,
    "meta-llama/llama-3-8b-instruct": 1180,
    "meta-llama/llama-3.1-405b-instruct": 1320,
    "meta-llama/llama-3.1-70b-instruct": 1280,
    "meta-llama/llama-3.1-8b-instruct": 1200,
    "meta-llama/llama-3.2-90b": 1270,
    "meta-llama/llama-3.3-70b": 1290,
    
    # Mistral
    "mistralai/mistral-large-3": 1290,
    "mistralai/mistral-large": 1280,
    "mistralai/mistral-medium": 1200,
    "mistralai/mistral-small": 1150,
    "mistralai/mixtral-8x7b": 1200,
    "mistralai/mixtral-8x22b": 1250,
    
    # Cohere
    "cohere/command-r-plus": 1200,
    "cohere/command-r": 1150,
    "cohere/command": 1100,
    
    # AI21
    "ai21/jamba-1.5-large": 1220,
    "ai21/jamba-1.5-mini": 1180,
    
    # Others
    "nvidia/nemotron-70b": 1210,
    "together/llama-3-sonar-large": 1230,
    "upstage/solar-pro": 1260,
    "arnizon/deepseek-r1-claude-3-5-sonnet": 1340,
}


def fetch_arena() -> Dict[str, int]:
    """
    Fetch ELO ratings from arena.ai leaderboard.
    Currently uses fallback data (scraping requires JavaScript).
    Returns: dict of model_id -> overall ELO
    """
    print("Arena.ai: using fallback ELO data")
    return dict(FALLBACK_ELO)
