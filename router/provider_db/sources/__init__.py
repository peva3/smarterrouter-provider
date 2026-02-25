"""
Benchmark data sources for provider.db.
"""

__all__ = [
    'LMSYSFetcher',
    'fetch_lmsys_arena',
    'LiveBenchFetcher', 
    'fetch_livebench',
    'fetch_bigcodebench',
    'fetch_evalplus',
    'fetch_latest_benchmarks',
    'fetch_mmlu',
    'OpenRouterFetcher',
    'fetch_openrouter_models',
    'fetch_arena',
    'fetch_lmarena',
    'fetch_eqbench',
    'fetch_swebench',
    'fetch_aider',
    'fetch_agieval',
    'fetch_mathvista',
    'fetch_livecodebench',
    'fetch_frontiermath',
    'fetch_aime',
    'fetch_scicode',
    'fetch_megabench',
    'fetch_mixeval_x',
    'fetch_gpqa',
    'fetch_stateval',
    'fetch_chinese',
    'fetch_tool_use',
    'fetch_vision',
    'fetch_ailuminate',
    'fetch_domain_specific',
    'fetch_helm',
    'fetch_multilingual',
    'fetch_chinese_reasoning',
    'fetch_chinese_coding',
    'fetch_chinese_elo',
    'fetch_extended_elo',
    'estimate_scores',
    'fetch_heuristics',
]


def __getattr__(name):
    """Lazy import to avoid requiring dependencies at import time."""
    if name == 'LMSYSFetcher' or name == 'fetch_lmsys_arena':
        from .lmsys_arena import LMSYSFetcher, fetch_lmsys_arena
        return LMSYSFetcher if name == 'LMSYSFetcher' else fetch_lmsys_arena
    elif name == 'LiveBenchFetcher' or name == 'fetch_livebench':
        from .livebench import LiveBenchFetcher, fetch_livebench
        return LiveBenchFetcher if name == 'LiveBenchFetcher' else fetch_livebench
    elif name == 'fetch_bigcodebench':
        from .bigcodebench import fetch_bigcodebench
        return fetch_bigcodebench
    elif name == 'fetch_evalplus':
        from .evalplus import fetch_evalplus
        return fetch_evalplus
    elif name == 'fetch_latest_benchmarks':
        from .latest_benchmarks import fetch_latest_benchmarks
        return fetch_latest_benchmarks
    elif name == 'fetch_mmlu':
        from .mmlu import fetch_mmlu
        return fetch_mmlu
    elif name == 'OpenRouterFetcher' or name == 'fetch_openrouter_models':
        from .openrouter import OpenRouterFetcher, fetch_openrouter_models
        return OpenRouterFetcher if name == 'OpenRouterFetcher' else fetch_openrouter_models
    elif name == 'fetch_arena':
        from .arena import fetch_arena
        return fetch_arena
    elif name == 'fetch_lmarena':
        from .lmarena import fetch_lmarena
        return fetch_lmarena
    elif name == 'fetch_eqbench':
        from .eqbench import fetch_eqbench
        return fetch_eqbench
    elif name == 'fetch_swebench':
        from .swebench import fetch_swebench
        return fetch_swebench
    elif name == 'fetch_aider':
        from .aider import fetch_aider
        return fetch_aider
    elif name == 'fetch_agieval':
        from .agieval import fetch_agieval
        return fetch_agieval
    elif name == 'fetch_mathvista':
        from .mathvista import fetch_mathvista
        return fetch_mathvista
    elif name == 'fetch_livecodebench':
        from .livecodebench import fetch_livecodebench
        return fetch_livecodebench
    elif name == 'fetch_frontiermath':
        from .frontiermath import fetch_frontiermath
        return fetch_frontiermath
    elif name == 'fetch_aime':
        from .aime import fetch_aime
        return fetch_aime
    elif name == 'fetch_scicode':
        from .scicode import fetch_scicode
        return fetch_scicode
    elif name == 'fetch_megabench':
        from .mega_bench import fetch_megabench
        return fetch_megabench
    elif name == 'fetch_mixeval_x':
        from .mixeval_x import fetch_mixeval_x
        return fetch_mixeval_x
    elif name == 'fetch_gpqa':
        from .gpqa import fetch_gpqa
        return fetch_gpqa
    elif name == 'fetch_stateval':
        from .stateval import fetch_stateval
        return fetch_stateval
    elif name == 'fetch_chinese':
        from .chinese import fetch_chinese
        return fetch_chinese
    elif name == 'fetch_multilingual':
        from .multilingual import fetch_multilingual
        return fetch_multilingual
    elif name == 'fetch_chinese_reasoning':
        from .chinese_reasoning import fetch_chinese_reasoning
        return fetch_chinese_reasoning
    elif name == 'fetch_chinese_coding':
        from .chinese_coding import fetch_chinese_coding
        return fetch_chinese_coding
    elif name == 'fetch_chinese_elo':
        from .chinese_elo import fetch_chinese_elo
        return fetch_chinese_elo
    elif name == 'fetch_extended_elo':
        from .extended_elo import fetch_extended_elo
        return fetch_extended_elo
    elif name == 'fetch_tool_use':
        from .tool_use import fetch_tool_use
        return fetch_tool_use
    elif name == 'fetch_vision':
        from .vision import fetch_vision
        return fetch_vision
    elif name == 'fetch_ailuminate':
        from .ailuminate import fetch_ailuminate
        return fetch_ailuminate
    elif name == 'fetch_domain_specific':
        from .domain_specific import fetch_domain_specific
        return fetch_domain_specific
    elif name == 'fetch_helm':
        from .helm import fetch_helm
        return fetch_helm
    elif name == 'estimate_scores':
        from .heuristics import estimate_scores
        return estimate_scores
    elif name == 'fetch_heuristics':
        from .heuristics import fetch_heuristics
        return fetch_heuristics
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
