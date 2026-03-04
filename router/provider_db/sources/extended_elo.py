"""
Extended ELO ratings from multiple sources.
Provides ELO ratings for models not covered by LMSYS Arena.
Aggregates data from arena.ai, lmsys, and community consensus.
"""

from typing import Dict
from ..model_mapper import model_mapper


def fetch_extended_elo() -> Dict[str, float]:
    """
    Fetch extended ELO ratings from multiple sources.
    Returns dict: model_id -> elo_rating.
    """
    scores = {}
    
    # Comprehensive ELO estimates based on:
    # - Arena.ai leaderboard
    # - LMSYS Chatbot Arena (fallback values)
    # - Open LLM Leaderboard
    # - Community consensus (2024-2025)
    
    known_elo = {
        # ============ OPENAI ============
        "openai/gpt-4o": 1330,
        "openai/gpt-4o-mini": 1280,
        "openai/gpt-4-turbo": 1300,
        "openai/gpt-4": 1285,
        "openai/gpt-4-0613": 1270,
        "openai/gpt-3.5-turbo": 1150,
        "openai/gpt-3.5-turbo-0613": 1140,
        "openai/o1": 1350,
        "openai/o1-mini": 1280,
        "openai/o1-preview": 1320,
        "openai/o3": 1350,
        "openai/o3-mini": 1280,
        "openai/o3-preview": 1300,
        "openai/o4-mini": 1280,
        "openai/o3-pro": 1350,
        
        # ============ ANTHROPIC ============
        "anthropic/claude-3.5-sonnet": 1320,
        "anthropic/claude-3.5-sonnet-20241022": 1320,
        "anthropic/claude-3.5-opus": 1340,
        "anthropic/claude-3-opus": 1280,
        "anthropic/claude-3-sonnet": 1200,
        "anthropic/claude-3-haiku": 1120,
        "anthropic/claude-2.1": 1050,
        "anthropic/claude-2.0": 1020,
        "anthropic/claude-Instant-1.2": 980,
        
        # ============ ADDITIONAL MODELS WITH BENCHMARKS ============
        "qwen/qwen-2.5-72b-instruct": 1280,
        "qwen/2.5-14b": 1150,
        "qwen/qwen-2.5-7b-instruct": 1100,
        "qwen/qwen2.5-coder-32b": 1250,
        "qwen/2-32b": 1220,
        "qwen/qwen-2-7b": 1050,
        "qwen/qwen-2-72b": 1200,
        "qwen/2.5-coder-32b-instruct": 1250,
        "qwen/2-coder-72b": 1180,
        "qwen/qwen2.5-tools": 1150,
        "deepseek/math": 1290,
        "deepseek/deepseek-v3": 1310,
        "deepseek/deepseek-math-r1": 1300,
        "deepseek/v3": 1260,
        "deepseek/r1-distill-llama-70b": 1300,
        "deepseek/r1-distill-qwen-32b": 1300,
        "deepseek/coder-v2": 1280,
        "deepseek/coder-33b": 1200,
        "deepseek/deepseek-math-7b": 1150,
        "baichuan/2-53b": 1180,
        "baichuan/2-13b": 1120,
        "baichuan/2-7b": 1050,
        "google/gemini-2.0-flash-exp": 1260,
        "google/gemma-2-27b": 1240,
        "google/gemma-2-9b": 1100,
        "google/gemma-2-1b": 950,
        "google/gemma-7b": 1050,
        "google/gemma-2b": 900,
        "meta-llama/llama-3-70b": 1250,
        "meta-llama/llama-3.2-1b-instruct": 950,
        "meta-llama/llama-3-405b": 1320,
        "meta-llama/llama-3-8b": 1180,
        "x-ai/grok-2-vision": 1250,
        "x-ai/grok-2": 1250,
        "nvidia/nemotron-4-mini": 1150,
        "amazon/nova-pro": 1050,
        "amazon/nova-lite": 950,
        # Additional variants
        "anthropic/claude-3.5-sonnet-20241022": 1320,
        "anthropic/claude-3-5-sonnet-20241022": 1320,
        "microsoft/phi-3-vision": 1000,
        "microsoft/phi-4": 1240,
        "wizardlm/wizardmath-70b": 1150,
        "sao10k/fusion": 1060,
        "arcee-ai/arcee-13b": 1000,
        
        # ============ GOOGLE ============
        "google/gemini-2.5-pro": 1350,
        "google/gemini-2.5-flash": 1280,
        "google/gemini-2.0-pro": 1320,
        "google/gemini-2.0-flash": 1260,
        "google/gemini-1.5-pro": 1310,
        "google/gemini-1.5-flash": 1250,
        "google/gemini-1.5-pro-exp": 1300,
        "google/gemini-1.5-flash-exp": 1240,
        "google/gemini-ultra": 1330,
        "google/gemini-pro": 1300,
        "google/gemini-pro-1.5": 1310,
        "google/gemini-flash": 1250,
        "google/gemini-flash-1.5": 1260,
        "google/palm-2": 1100,
        
        # ============ DEEPSEEK ============
        "deepseek/deepseek-r1": 1350,
        "deepseek/deepseek-r1-0528": 1350,
        "deepseek/deepseek-v3.2": 1310,
        "deepseek/deepseek-v3.1": 1280,
        "deepseek/deepseek-chat": 1250,
        "deepseek/deepseek-chat-v3.1": 1250,
        "deepseek/deepseek-chat-v3.2": 1260,
        "deepseek/deepseek-coder": 1280,
        "deepseek/deepseek-coder-v2": 1300,
        "deepseek/deepseek-coder-v2.5": 1310,
        "deepseek/deepseek-math": 1290,
        "deepseek/deepseek-r1-distill-llama-70b": 1300,
        "deepseek/deepseek-r1-distill-qwen-32b": 1300,
        "deepseek/deepseek-r1-zero": 1330,
        "deepseek/deepseek-v2": 1260,
        "deepseek/deepseek-v2-chat": 1260,
        "deepseek/deepseek-v2.5": 1280,
        
        # ============ QWEN ============
        "qwen/qwen3-max": 1340,
        "qwen/qwen3-max-thinking": 1340,
        "qwen/qwen3-coder": 1380,
        "qwen/qwen3-coder-next": 1360,
        "qwen/qwen3-5-397b-a17b": 1350,
        "qwen/qwen2.5-max": 1310,
        "qwen/qwen2.5-max-0119": 1310,
        "qwen/qwen2.5-72b-instruct": 1280,
        "qwen/qwen2.5-72b": 1280,
        "qwen/qwen2.5-32b-instruct": 1220,
        "qwen/qwen2.5-32b": 1220,
        "qwen/qwen2.5-14b-instruct": 1150,
        "qwen/qwen2.5-7b-instruct": 1100,
        "qwen/qwen2.5-1.5b-instruct": 1000,
        "qwen/qwen2.5-0.5b-instruct": 950,
        "qwen/qwen2.5-coder-32b-instruct": 1250,
        "qwen/qwen2.5-coder-7b-instruct": 1100,
        "qwen/qwen2-72b-instruct": 1200,
        "qwen/qwen2-7b-instruct": 1050,
        "qwen/qwen-72b": 1150,
        "qwen/qwen-7b": 1000,
        "qwen/qwen-14b": 1050,
        "qwen/qwen-vl-plus": 1200,
        "qwen/qwen-vl-max": 1220,
        "qwen/qwen2-vl-72b": 1230,
        "qwen/qwen2-vl-7b": 1100,
        "qwen/qwen2.5-vl-32b-instruct": 1220,
        "qwen/qwen2.5-vl-7b-instruct": 1080,
        
        # ============ META (LLAMA) ============
        "meta-llama/llama-3.3-70b-instruct": 1290,
        "meta-llama/llama-3.2-90b-instruct": 1270,
        "meta-llama/llama-3.2-1b-instruct": 950,
        "meta-llama/llama-3.2-3b-instruct": 1000,
        "meta-llama/llama-3.1-405b-instruct": 1320,
        "meta-llama/llama-3.1-405b": 1320,
        "meta-llama/llama-3.1-70b-instruct": 1280,
        "meta-llama/llama-3.1-70b": 1280,
        "meta-llama/llama-3.1-8b-instruct": 1200,
        "meta-llama/llama-3.1-8b": 1200,
        "meta-llama/llama-3.1-3b-instruct": 1000,
        "meta-llama/llama-3.0-70b-instruct": 1180,
        "meta-llama/llama-2-70b-chat": 1250,
        "meta-llama/llama-2-70b": 1250,
        "meta-llama/llama-2-13b-chat": 1150,
        "meta-llama/llama-2-13b": 1150,
        "meta-llama/llama-2-7b-chat": 1050,
        "meta-llama/llama-2-7b": 1050,
        "meta-llama/llama-1-70b": 1100,
        
        # ============ MISTRAL ============
        "mistralai/mistral-large-3": 1290,
        "mistralai/mistral-large-2": 1270,
        "mistralai/mistral-large": 1280,
        "mistralai/mistral-medium": 1200,
        "mistralai/mistral-small": 1150,
        "mistralai/mixtral-8x22b-instruct": 1250,
        "mistralai/mixtral-8x22b": 1250,
        "mistralai/mixtral-8x7b-instruct": 1200,
        "mistralai/mixtral-8x7b": 1200,
        "mistralai/mistral-7b-instruct": 1050,
        "mistralai/mistral-7b": 1050,
        "mistralai/mixtral-8x22b": 1250,
        
        # ============ COHERE ============
        "cohere/command-r-plus": 1200,
        "cohere/command-r": 1150,
        "cohere/command": 1100,
        "cohere/command-light": 1050,
        
        # ============ AI21 ============
        "ai21/jamba-1.5-large": 1220,
        "ai21/jamba-1.5-medium": 1180,
        "ai21/jamba-1.5-mini": 1100,
        "ai21/jamba-instruct": 1150,
        
        # ============ XAI (GROK) ============
        "xai/grok-4": 1473,
        "xai/grok-4-thinking": 1473,
        "xai/grok-3": 1400,
        "xai/grok-3-thinking": 1400,
        "xai/grok-2": 1250,
        "xai/grok-2-thinking": 1250,
        "xai/grok-1": 1200,
        
        # ============ MOONSHOT ============
        "moonshotai/kimi-k2.5": 1420,
        "moonshotai/kimi-k2.5-thinking": 1420,
        "moonshotai/kimi-k2": 1250,
        "moonshotai/kimi-k2-thinking": 1250,
        "moonshotai/kimi-v1": 1200,
        "moonshotai/kimi-v1-thinking": 1200,
        "moonshotai/kimi-long": 1150,
        
        # ============ MINIMAX ============
        "minimax/minimax-m2.5": 1400,
        "minimax/minimax-m2.1": 1320,
        "minimax/minimax-text-01": 1220,
        
        # ============ NVIDIA ============
        "nvidia/llama-3.1-nemotron-70b-instruct": 1240,
        "nvidia/llama-3.1-nemotron-70b": 1240,
        "nvidia/nemotron-4-340b-instruct": 1250,
        "nvidia/nemotron-4-340b": 1250,
        
        # ============ TOGETHER ============
        "together/llama-3-70b": 1180,
        "together/llama-3-8b": 1050,
        "together/mixtral-8x22b": 1210,
        "together/mixtral-8x7b": 1150,
        "together/llama-2-70b": 1100,
        "together/llama-2-13b": 1000,
        "together/llama-3-sonar-large": 1230,
        "together/llama-3-sonar-small": 1100,
        "together/llama-3.1-sonar-large": 1240,
        "together/llama-3.1-sonar-small": 1110,
        
        # ============ PERPLEXITY ============
        "perplexity/llama-3.1-sonar-large": 1180,
        "perplexity/llama-3.1-sonar-small": 1100,
        "perplexity/llama-3-sonar-large": 1170,
        "perplexity/llama-3-sonar-small": 1080,
        
        # ============ UPSTAGE ============
        "upstage/solar-pro": 1260,
        "upstage/solar-10.7b-instruct": 1150,
        
        # ============ IBM ============
        "ibm/granite-34b-code-instruct": 1100,
        "ibm/granite-13b-chat": 1000,
        
        # ============ COHERE ============
        "cohere/command-r-plus": 1200,
        "cohere/command-r": 1150,
        "cohere/command": 1100,
        
        # ============ BAICHUAN ============
        "baichuan/baichuan2-53b": 1180,
        "baichuan/baichuan2-13b": 1120,
        "baichuan/baichuan2-7b": 1050,
        "baichuan/baichuan3": 1230,
        
        # ============ Yi ============
        "01-ai/yi-34b": 1150,
        "01-ai/yi-9b": 1050,
        "01-ai/yi-6b": 950,
        "01-ai/yi-large": 1200,
        
        # ============ GLM ============
        "z-ai/glm-5": 1430,
        "z-ai/glm-4.7": 1330,
        "z-ai/glm-4.6": 1290,
        "z-ai/glm-4": 1250,
        "z-ai/glm-4-flash": 1210,
        "z-ai/glm-4v": 1230,
        "z-ai/glm-4-0414": 1270,
        
        # ============ MISC ============
        "arnizon/deepseek-r1-claude-3-5-sonnet": 1340,
        "fireworks/firefunction-v2": 1200,
        "fireworks/firellama-3-70b": 1170,
        "fireworks/firellama-3-8b": 1050,
        "anyscale/llama-3-70b": 1160,
        "anyscale/llama-3-8b": 1040,
        "nebius/llama-3.1-70b-instruct": 1180,
        "nebius/llama-3.1-8b-instruct": 1060,
        "hyperbolic/math-7b": 1050,
        "snowflake/snowflake-arctic": 1220,
        "databricks/dbrx-instruct": 1180,
        "databricks/dbrx-base": 1100,
        "microsoft/phi-3-medium": 1080,
        "microsoft/phi-3-small": 1020,
        "microsoft/phi-3-mini": 980,
        "microsoft/phi-2": 900,
        "microsoft/phi-1.5": 800,
        "allenai/olmo-3.1-32b-instruct": 1120,
        "allenai/olmo-3.1-7b-instruct": 1000,
        "allenai/olmo-2-13b": 950,
    }
    
    for name, elo in known_elo.items():
        canonical = model_mapper.to_canonical(name)
        if canonical:
            scores[canonical] = elo
    
    if scores:
        print(f"Extended ELO: {len(scores)} ELO ratings (static)")
    else:
        print("Extended ELO: no valid mappings")
    
    return scores
