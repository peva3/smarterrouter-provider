"""
Model name mapper - converts various model name formats to OpenRouter canonical IDs.
"""

import re
from typing import Optional


class ModelMapper:
    """
    Maps model names from different sources to OpenRouter canonical IDs.
    Handles aliases, patterns, and known mappings.
    """
    
    PROVIDER_PREFIXES = {
        "openai": "openai",
        "anthropic": "anthropic",
        "google": "google",
        "meta-llama": "meta-llama",
        "mistralai": "mistralai",
        "mistral": "mistralai",
        "x": "x",
        "cohere": "cohere",
        "ai21": "ai21",
        "amazon": "amazon",
        "nvidia": "nvidia",
        "fireworks": "fireworks",
        "perplexity": "perplexity",
        "togetherai": "togetherai",
        "anyscale": "anyscale",
        "replicate": "replicate",
        "deepseek": "deepseek",
        "qwen": "qwen",
        "01-ai": "01-ai",
        "baidu": "baidu",
        "alibaba": "alibaba",
        "tencent": "tencent",
        "bytedance": "bytedance",
        "z-ai": "z-ai",
        "baichuan": "baichuan",
        "moonshotai": "moonshotai",
        "minimax": "minimax",
        "xfajk": "xfajk",
        "iflytek": "iFlytek",
        "360": "360",
        "sensenova": "sensenova",
        "bigscience": "bigscience",
        "tiiuae": "tiiuae",
        "allenai": "allenai",
        "nousresearch": "nousresearch",
        "cognitivecomputations": "cognitivecomputations",
        "huggingface": "huggingface",
        "openchat": "openchat",
        "wizardlm": "wizardlm",
        "lmsys": "lmsys",
        "gryphe": "gryphe",
        "microsoft": "microsoft",
        "phind": "phind",
        "upstage": "upstage",
        "sophosympatheia": "sophosympatheia",
        "rokmr": "rokmr",
        "nepsys": "nepsys",
        "blue": "blue",
        "skepsun": "skepsun",
        "ravenous": "ravenous",
        "azure": "azure-openai",
    }
    
    KNOWN_ALIASES = {
        # OpenAI
        "gpt-4": "openai/gpt-4",
        "gpt-4-32k": "openai/gpt-4-32k",
        "gpt-4-turbo": "openai/gpt-4-turbo",
        "gpt-4o": "openai/gpt-4o",
        "gpt-4o-mini": "openai/gpt-4o-mini",
        "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
        "gpt-3.5-turbo-16k": "openai/gpt-3.5-turbo-16k",
        "gpt-4-0125-preview": "openai/gpt-4-0125-preview",
        "gpt-4-turbo-preview": "openai/gpt-4-turbo-preview",
        "o1": "openai/o1",
        "o1-mini": "openai/o1-mini",
        "o3-mini": "openai/o3-mini",
        
        # Anthropic
        "claude-3-opus": "anthropic/claude-3-opus",
        "claude-3-sonnet": "anthropic/claude-3-sonnet",
        "claude-3-haiku": "anthropic/claude-3-haiku",
        "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
        "claude-3.5-sonnet-20241022": "anthropic/claude-3.5-sonnet-20241022",
        "claude-3.5-haiku": "anthropic/claude-3.5-haiku",
        "claude-opus-3-5": "anthropic/claude-3-opus",
        "claude-sonnet-3-5": "anthropic/claude-3.5-sonnet",
        
        # Google
        "gemini-pro": "google/gemini-pro",
        "gemini-pro-1.5": "google/gemini-1.5-pro",
        "gemini-1.5-pro": "google/gemini-1.5-pro",
        "gemini-1.5-flash": "google/gemini-1.5-flash",
        "gemini-1.5-flash-8b": "google/gemini-1.5-flash-8b",
        "gemini-2.0-flash-exp": "google/gemini-2.0-flash-exp",
        
        # Meta Llama
        "llama-2-70b": "meta-llama/llama-2-70b-chat",
        "llama-2-7b": "meta-llama/llama-2-7b-chat",
        "llama-2-13b": "meta-llama/llama-2-13b-chat",
        "llama-3-8b": "meta-llama/llama-3-8b-instruct",
        "llama-3-70b": "meta-llama/llama-3-70b-instruct",
        "llama-3.1-8b": "meta-llama/llama-3.1-8b-instruct",
        "llama-3.1-70b": "meta-llama/llama-3.1-70b-instruct",
        "llama-3.1-405b": "meta-llama/llama-3.1-405b-instruct",
        "llama-3.2-1b": "meta-llama/llama-3.2-1b-instruct",
        "llama-3.2-90b": "meta-llama/llama-3.2-90b-instruct",
        
        # Mistral
        "mistral-7b": "mistralai/mistral-7b-instruct",
        "mistral-8x7b": "mistralai/mixtral-8x7b-instruct",
        "mixtral-8x7b": "mistralai/mixtral-8x7b-instruct",
        "mixtral-8x22b": "mistralai/mixtral-8x22b-instruct",
        "mistral-large": "mistralai/mistral-large",
        "mistral-small": "mistralai/mistral-small",
        
        # Cohere
        "command-r": "cohere/command-r",
        "command-r-plus": "cohere/command-r-plus",
        
        # Qwen
        "qwen-2": "qwen/qwen-2-72b",
        "qwen-2-72b": "qwen/qwen-2-72b",
        "qwen-2-7b": "qwen/qwen-2-7b",
        "qwen-2.5-72b": "qwen/qwen-2.5-72b-instruct",
        "qwen-2.5-7b": "qwen/qwen-2.5-7b-instruct",
        "qwen-2.5-32b": "qwen/qwen-2.5-32b-instruct",
        "qwen-2.5-coder-32b": "qwen/qwen-2.5-coder-32b-instruct",
        "qwen-2.5-vl-72b": "qwen/qwen-2.5-vl-72b-instruct",
        "qwen1.5-72b": "qwen/qwen1.5-72b-chat",
        
        # DeepSeek
        "deepseek-chat": "deepseek/deepseek-chat",
        "deepseek-coder": "deepseek/deepseek-coder",
        "deepseek-r1": "deepseek/deepseek-r1",
        
        # Others
        "mixtral-8x7b-instruct": "mistralai/mixtral-8x7b-instruct",
        "mixtral-8x22b-instruct": "mistralai/mixtral-8x22b-instruct",
        "yi-34b": "01-ai/yi-34b-chat",
        "yi-large": "01-ai/yi-large",
        "wizardlm-2-8x22b": "wizardlm/wizardlm-2-8x22b",
        "wizardlm-2-7b": "wizardlm/wizardlm-2-7b",
        
        # Azure OpenAI
        "gpt-4-azure": "azure-openai/gpt-4",
        "gpt-35-turbo-azure": "azure-openai/gpt-35-turbo",
        
        # LMSYS specific names
        "gpt-4-turbo-2024-04-09": "openai/gpt-4-turbo",
        "gpt-4-2024-05-13": "openai/gpt-4o",
        "claude-3-5-sonnet-20241022": "anthropic/claude-3.5-sonnet-20241022",
        "llama-3-70b-instruct": "meta-llama/llama-3-70b-instruct",
        "llama-3-8b-instruct": "meta-llama/llama-3-8b-instruct",
        
        # MATH benchmark specific names
        "gemini 2.0 flash experimental": "google/gemini-2.0-flash-exp",
        "gemini-2.0-flash-experimental": "google/gemini-2.0-flash-exp",
        "qwen2.5-math-72b-instruct": "qwen/qwen-2.5-72b-instruct",
        "qwen2.5-math-7b-instruct": "qwen/qwen-2.5-7b-instruct",
        "qwen2.5-math-1.5b-instruct": "qwen/qwen-2.5-7b-instruct",  # Approximate
        "qwen2-math-72b-instruct": "qwen/qwen-2-72b",
        "gpt-4-code model": "openai/gpt-4",
        "gpt-4-turbo (macm, w/code, voting)": "openai/gpt-4-turbo",
        "openmath2-llama3.1-70b": "meta-llama/llama-3.1-70b-instruct",
        "openmath2-llama3.1-8b": "meta-llama/llama-3.1-8b-instruct",
        "cr (gpt-4-turbo model, w/ code)": "openai/gpt-4-turbo",
        
        # Chinese model aliases
        "ernie-4": "baidu/ernie-4",
        "ernie-3.5": "baidu/ernie-3.5",
        "ernie-bot": "baidu/ernie-bot",
        "qwen-max": "alibaba/qwen-max",
        "qwen-72b": "alibaba/qwen-72b",
        "qwen2.5-72b": "alibaba/qwen2.5-72b",
        "glm-4": "z-ai/glm-4",
        "glm-5": "z-ai/glm-5",
        "kimi-k2": "moonshotai/kimi-k2",
        "kimi-k2.5": "moonshotai/kimi-k2.5",
        "yi-large": "01-ai/yi-large",
        "yi-34b": "01-ai/yi-34b",
        "baichuan-2-53b": "baichuan/baichuan-2-53b",
        "hunyuan": "tencent/hunyuan",
        "hunyuan-pro": "tencent/hunyuan-pro",
        "douyin-pro": "bytedance/douyin-pro",
        "minimax-text-01": "minimax/minimax-text-01",
    }
    
    def to_canonical(self, name: str) -> Optional[str]:
        """
        Convert a model name to OpenRouter canonical ID.
        Returns None if no mapping is found.
        """
        if not name:
            return None
        
        # Normalize
        normalized = name.strip().lower()
        
        # Check for empty after strip
        if not normalized:
            return None
        
        # Check exact alias
        if normalized in self.KNOWN_ALIASES:
            return self.KNOWN_ALIASES[normalized]
        
        # Check if already a canonical ID (has /)
        if "/" in name:
            return name.strip()
        
        # Try to extract provider and model
        parts = normalized.replace("_", "-").split("-")
        if len(parts) >= 2:
            provider = parts[0]
            model = "-".join(parts[1:])
            
            # Check known providers
            if provider in self.PROVIDER_PREFIXES:
                return f"{self.PROVIDER_PREFIXES[provider]}/{model}"
            
            # Try to match prefix
            for known_prefix, known_provider in self.PROVIDER_PREFIXES.items():
                if normalized.startswith(known_prefix.replace("-", "")):
                    model_part = normalized[len(known_prefix):].lstrip("-")
                    if model_part:
                        return f"{known_provider}/{model_part}"
        
        return None
    
    def get_all_aliases(self) -> dict[str, str]:
        """Return all known aliases."""
        return self.KNOWN_ALIASES.copy()


model_mapper = ModelMapper()
