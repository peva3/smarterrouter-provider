"""
Model name mapper - converts various model name formats to OpenRouter canonical IDs.
"""

import re
from typing import Optional, List, Tuple


class ModelMapper:
    """
    Maps model names from different sources to OpenRouter canonical IDs.
    Handles aliases, patterns, fuzzy matching, and known mappings.
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
    
    # Normalize version patterns for fuzzy matching
    VERSION_ALIASES = {
        # GPT versions
        "gpt-4": ["gpt4", "gpt-4", "gpt4o", "gpt-4o"],
        "gpt-5": ["gpt5", "gpt-5", "gpt5o", "gpt-5o"],
        "gpt-3.5": ["gpt35", "gpt-3.5", "gpt3.5"],
        # Claude versions
        "claude-3.5": ["claude35", "claude-3.5", "claude3.5", "claude-3.5-sonnet", "claude-sonnet-3.5"],
        "claude-3": ["claude3", "claude-3", "claude3opus", "claude3sonnet"],
        "claude-opus-4": ["claude-opus-4", "claude-opus4", "opus-4", "opus4"],
        # Qwen versions
        "qwen2": ["qwen2", "qwen-2", "qwen2.5", "qwen-2.5", "qwen2.5", "qwen-2", "qwen2"],
        "qwen3": ["qwen3", "qwen-3"],
        # Llama versions
        "llama-3": ["llama3", "llama-3", "llama3.1", "llama-3.1", "llama3.2", "llama-3.2"],
        "llama-2": ["llama2", "llama-2"],
        # Mistral versions
        "mistral-large": ["mistral-large", "mistrallarge", "mistral_large"],
        "mistral-small": ["mistral-small", "mistralsmall"],
        "mixtral": ["mixtral", "mixtral-"],
        # DeepSeek versions
        "deepseek-v3": ["deepseek-v3", "deepseekv3", "deepseek-v3.2", "deepseekv3.2"],
        "deepseek-r1": ["deepseek-r1", "deepr1", "deepseekr1"],
        "deepseek-coder": ["deepseek-coder", "deepseekcoder"],
        # Gemini versions
        "gemini-2": ["gemini-2", "gemini2", "gemini-2.0", "gemini2.0"],
        "gemini-1.5": ["gemini-1.5", "gemini1.5", "gemini-1.5-pro", "gemini1.5pro"],
        "gemini-pro": ["geminipro", "gemini-pro"],
        # Phi versions
        "phi-4": ["phi4", "phi-4"],
        "phi-3": ["phi3", "phi-3"],
    }
    
    # Provider name variations
    PROVIDER_ALIASES = {
        "openai": ["openai", "gpt"],
        "anthropic": ["anthropic", "claude"],
        "google": ["google", "gemini", "gemma"],
        "deepseek": ["deepseek", "deepseekai"],
        "qwen": ["qwen", "alibaba"],
        "meta": ["meta", "llama", "facebook"],
        "mistralai": ["mistralai", "mistral"],
        "moonshotai": ["moonshotai", "kimi"],
        "x": ["x", "xai", "grok"],
        "nvidia": ["nvidia", "nemotron"],
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
        
        # SWE-bench Verified naming conventions
        "claude-opus-4.5": "anthropic/claude-opus-4.5",
        "claude-opus-4.6": "anthropic/claude-opus-4.6",
        "claude-sonnet-4.5": "anthropic/claude-sonnet-4.5",
        "claude-sonnet-4": "anthropic/claude-sonnet-4",
        "claude-haiku-4.5": "anthropic/claude-haiku-4.5",
        "gemini-3-pro": "google/gemini-3-pro",
        "gemini-3-flash": "google/gemma-3-flash",
        "gpt-5.2": "openai/gpt-5.2",
        "gpt-5.1": "openai/gpt-5.1",
        "gpt-5-high": "openai/gpt-5-high",
        "gpt-5-medium": "openai/gpt-5-medium",
        "gpt-5-low": "openai/gpt-5-low",
        
        # LiveCodeBench naming conventions  
        "x/4": "xai/grok-4",
        "x/3": "xai/grok-3",
        "x/3-mini": "xai/grok-3-mini",
        "x/2": "xai/grok-2",
        "x/2-mini": "xai/grok-2-mini",
        "google/3-flash": "google/gemini-3-flash",
        "google/3-pro": "google/gemini-3-pro",
        "google/2.5-pro": "google/gemini-2.5-pro",
        "google/2.5-flash": "google/gemini-2.5-flash",
        "google/2.0-pro": "google/gemini-2.0-pro",
        "google/2.0-flash": "google/gemini-2.0-flash",
        "deepseek/v3.2": "deepseek/deepseek-v3.2",
        
        # MMLU-Pro naming
        "gemini-3-pro": "google/gemini-3-pro",
        
        # Generic version patterns
        "claude-opus-4": "anthropic/claude-opus-4",
        "claude-opus-3": "anthropic/claude-opus-3",
        "claude-sonnet-3": "anthropic/claude-sonnet-3",
        "claude-haiku-3": "anthropic/claude-haiku-3",
        
        # OpenRouter-specific model names that need mapping
        "claude-opus-4-5": "anthropic/claude-opus-4.5",
        "claude-opus-4-6": "anthropic/claude-opus-4.6",
        "claude-sonnet-4-5": "anthropic/claude-sonnet-4.5",
        "claude-haiku-4-5": "anthropic/claude-haiku-4.5",
        
        # OpenRouter model name patterns
        "qwen/qwen2.5-tools": "qwen/qwen2.5-tools",
        "qwen/2-coder-72b": "qwen/qwen2.5-coder-72b-instruct",
        "qwen/2-coder-32b": "qwen/qwen2.5-coder-32b-instruct", 
        "qwen/2.5-coder-32b": "qwen/qwen2.5-coder-32b-instruct",
        "qwen/coder-72b": "qwen/qwen2.5-coder-72b-instruct",
        "qwen/coder-32b": "qwen/qwen2.5-coder-32b-instruct",
        "qwen/2-coder-32b": "qwen/qwen2.5-coder-32b-instruct",
        "qwen/2.5-coder-14b": "qwen/qwen2.5-coder-14b-instruct",
        "qwen/2-72b": "qwen/qwen2.5-72b-instruct",
        "qwen/2.5-32b": "qwen/qwen2.5-32b-instruct",
        "qwen/2-32b": "qwen/qwen2.5-32b-instruct",
        "qwen/2-1.5b": "qwen/qwen2.5-1.5b-instruct",
        "qwen/2-0.5b": "qwen/qwen2.5-0.5b-instruct",
        "qwen/2-1.5b-instruct": "qwen/qwen2.5-1.5b-instruct",
        "qwen3-coder-next": "qwen/qwen3-coder-next",
        
        # Google models
        "google/gemini-2.5-pro-preview": "google/gemini-2.5-pro",
        "google/gemini-2.5-pro-preview-05-06": "google/gemini-2.5-pro",
        
        # Meta models
        "meta/llama-3.1-70b-instruct": "meta-llama/llama-3.1-70b-instruct",
        "meta/llama-3.1-8b-instruct": "meta-llama/llama-3.1-8b-instruct",
        "meta/llama-3.1-405b-instruct": "meta-llama/llama-3.1-405b-instruct",
        "meta/llama-3.2-90b": "meta-llama/llama-3.2-90b-instruct",
        
        # DeepSeek
        "deepseek/coder-6.7b": "deepseek/deepseek-coder-v2",
        
        # X models (grok)
        "x/4": "xai/grok-4",
        "x/3": "xai/grok-3",
        "x/3-mini": "xai/grok-3-mini",
        "x/2": "xai/grok-2",
        "x/2-mini": "xai/grok-2-mini",
        "x/2-vision": "xai/grok-2-vision",
        
        # OpenAI o-series
        "openai/o3-pro": "openai/o3-pro",
        
        # Mistral
        "mistralai/mistral-large-3": "mistralai/mistral-large-3",
    }
    
    def _normalize_name(self, name: str) -> str:
        """Normalize model name for comparison."""
        return re.sub(r'[^a-z0-9]', '', name.lower())
    
    def _extract_provider_model(self, name: str) -> Tuple[str, str]:
        """Extract provider and model name from a canonical ID or name."""
        name = name.strip()
        
        if "/" in name:
            parts = name.split("/")
            return parts[0], parts[1]
        
        # Try to detect provider
        name_lower = name.lower()
        
        # Check known prefixes
        for prefix, provider in self.PROVIDER_PREFIXES.items():
            if name_lower.startswith(prefix) or name_lower.replace("-", "").startswith(prefix.replace("-", "")):
                model = name[len(prefix):].lstrip("/-")
                return provider, model
        
        # Try common model patterns
        for known_prefix, aliases in self.PROVIDER_ALIASES.items():
            for alias in aliases:
                if name_lower.replace("-", "").startswith(alias.replace("-", "")):
                    return known_prefix, name[len(alias):].lstrip("/-")
        
        return "", name
    
    def _get_canonical_from_parts(self, provider: str, model: str) -> Optional[str]:
        """Build canonical ID from provider and model parts."""
        if not provider or not model:
            return None
        
        # Check known providers
        if provider in self.PROVIDER_PREFIXES:
            canonical_provider = self.PROVIDER_PREFIXES[provider]
        else:
            # Try to find matching provider
            for known_prefix, canonical in self.PROVIDER_PREFIXES.items():
                if provider.replace("-", "") == known_prefix.replace("-", ""):
                    canonical_provider = canonical
                    break
            else:
                return None
        
        return f"{canonical_provider}/{model}"
    
    def to_canonical(self, name: str, known_models: List[str] = None) -> Optional[str]:
        """
        Convert a model name to OpenRouter canonical ID.
        Uses fuzzy matching when exact match fails.
        
        Args:
            name: The model name to convert
            known_models: Optional list of known canonical IDs to match against
        """
        if not name:
            return None
        
        # Normalize
        normalized = name.strip().lower()
        
        # Check for empty after strip
        if not normalized:
            return None
        
        # Check exact alias first
        if normalized in self.KNOWN_ALIASES:
            return self.KNOWN_ALIASES[normalized]
        
        # Check if already a canonical ID (has /)
        if "/" in name:
            # Verify it looks like a canonical ID
            parts = name.strip().split("/")
            if len(parts) == 2 and parts[0] and parts[1]:
                return name.strip()
        
        # Try fuzzy matching against known models
        if known_models:
            match = self._fuzzy_match(normalized, known_models)
            if match:
                return match
        
        # Try to extract and rebuild
        provider, model = self._extract_provider_model(name)
        if provider and model:
            # Try version normalization
            model = self._normalize_version(model)
            canonical = self._get_canonical_from_parts(provider, model)
            if canonical:
                return canonical
        
        # Last resort: try pattern matching
        return self._pattern_match(normalized)
    
    def _normalize_version(self, model: str) -> str:
        """Normalize version numbers in model name."""
        # Handle common version variations
        model = model.lower()
        
        # Qwen version normalization
        if model.startswith("qwen2"):
            if not ("." in model or "5" in model[:6]):
                model = model.replace("qwen2", "qwen2.5")
        elif model.startswith("qwen"):
            if "2" in model[4:7] and "2.5" not in model:
                model = model.replace("qwen", "qwen2.5", 1)
        
        # GPT version normalization
        if "gpt-5" not in model and "gpt5" not in model:
            if "gpt4" in model:
                model = model.replace("gpt4", "gpt-4")
        
        # Claude version normalization
        if "claude-opus-4" not in model:
            if "opus-4" in model or "opus4" in model:
                model = model.replace("opus4", "opus-4").replace("opus-4", "claude-opus-4")
        
        return model
    
    def _fuzzy_match(self, normalized: str, known_models: List[str]) -> Optional[str]:
        """Fuzzy match against known canonical models."""
        norm_input = self._normalize_name(normalized)
        
        best_match = None
        best_score = 0
        
        for model in known_models:
            norm_model = self._normalize_name(model)
            
            # Exact match after normalization
            if norm_input == norm_model:
                return model
            
            # Partial match (input is subset of model or vice versa)
            if norm_input in norm_model or norm_model in norm_input:
                if len(norm_input) >= 4:  # Only for substantial names
                    score = len(min(norm_input, norm_model, key=len))
                    if score > best_score:
                        best_score = score
                        best_match = model
            else:
                # Check key tokens
                input_tokens = set(norm_input.replace("-", "").replace("_", ""))
                model_tokens = set(norm_model.replace("-", "").replace("_", ""))
                
                # Check if 80%+ of tokens match
                if input_tokens and model_tokens:
                    overlap = len(input_tokens & model_tokens)
                    score = overlap / max(len(input_tokens), len(model_tokens))
                    if score > 0.8 and score > best_score:
                        best_score = score
                        best_match = model
        
        return best_match
    
    def _pattern_match(self, normalized: str) -> Optional[str]:
        """Pattern-based matching for common model formats."""
        
        # Extract provider prefix
        for prefix, canonical_provider in self.PROVIDER_PREFIXES.items():
            prefix_normalized = prefix.replace("-", "")
            if normalized.replace("-", "").startswith(prefix_normalized):
                # Extract model name after prefix
                model_part = normalized[len(prefix):].lstrip("-/")
                if not model_part:
                    return None
                
                # Normalize the model part
                model_part = self._normalize_version(model_part)
                
                # Rebuild
                return f"{canonical_provider}/{model_part}"
        
        # Try to match model patterns without provider
        # E.g., "gpt-4o" -> "openai/gpt-4o"
        for alias, canonical in self.KNOWN_ALIASES.items():
            if normalized == alias or normalized in alias or alias in normalized:
                if len(alias) >= 5:  # Only substantial matches
                    return canonical
        
        return None
    
    def get_all_aliases(self) -> dict[str, str]:
        """Return all known aliases."""
        return self.KNOWN_ALIASES.copy()


model_mapper = ModelMapper()
