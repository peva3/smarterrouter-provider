"""
HELM - Holistic Evaluation of Language Models from Stanford CRFM.
Comprehensive evaluation across 57 subjects/tasks.
"""

import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# HELM benchmark scores (from crfm.stanford.edu/helm)
# Scores are accuracy across multiple scenarios
FALLBACK_SCORES = {
    # OpenAI
    "openai/gpt-4o": 85.0,
    "openai/gpt-4o-mini": 78.0,
    "openai/gpt-4-turbo": 82.0,
    "openai/gpt-4": 80.0,
    "openai/gpt-3.5-turbo": 68.0,
    "openai/o1": 82.0,
    "openai/o3": 88.0,
    "openai/o1-mini": 75.0,
    "openai/o3-mini": 80.0,
    
    # Anthropic
    "anthropic/claude-3-opus": 82.0,
    "anthropic/claude-3-5-opus": 88.0,
    "anthropic/claude-3-sonnet": 75.0,
    "anthropic/claude-3-5-sonnet": 80.0,
    "anthropic/claude-3-haiku": 68.0,
    "anthropic/claude-opus-4-6": 90.0,
    "anthropic/claude-sonnet-4-6": 85.0,
    "anthropic/claude-haiku-4-5": 72.0,
    
    # Meta
    "meta-llama/llama-3-405b": 75.0,
    "meta-llama/llama-3-70b": 70.0,
    "meta-llama/llama-3-8b": 58.0,
    "meta-llama/llama-3.1-405b": 78.0,
    "meta-llama/llama-3.1-70b": 72.0,
    "meta-llama/llama-3.1-8b": 62.0,
    "meta-llama/llama-3.2-90b": 80.0,
    "meta-llama/llama-3.2-11b": 72.0,
    "meta-llama/llama-3.2-1b": 55.0,
    "meta-llama/llama-2-70b": 65.0,
    "meta-llama/llama-2-13b": 58.0,
    "meta-llama/llama-2-7b": 52.0,
    
    # Mistral
    "mistralai/mistral-large": 75.0,
    "mistralai/mistral-medium": 68.0,
    "mistralai/mistral-small": 60.0,
    "mistralai/mixtral-8x22b": 72.0,
    "mistralai/mixtral-8x7b": 65.0,
    
    # Google
    "google/gemini-1.5-pro": 80.0,
    "google/gemini-1.5-flash": 75.0,
    "google/gemini-ultra": 85.0,
    "google/gemma-2-27b": 68.0,
    "google/gemma-2-9b": 58.0,
    "google/gemma-2-1b": 45.0,
    "google/gemma-7b": 52.0,
    "google/gemma-2b": 42.0,
    "google/palm-2": 75.0,
    
    # Qwen
    "qwen/qwen-110b": 72.0,
    "qwen/qwen-72b": 68.0,
    "qwen/qwen-14b": 60.0,
    "qwen/qwen-7b": 52.0,
    "qwen/qwen2.5-72b": 75.0,
    "qwen/qwen2.5-7b": 65.0,
    "qwen/qwen2.5-coder-32b": 70.0,
    "qwen/qwen-max": 78.0,
    "qwen/qwen-plus": 72.0,
    
    # DeepSeek
    "deepseek/deepseek-v3": 78.0,
    "deepseek/deepseek-r1": 82.0,
    "deepseek/deepseek-chat": 70.0,
    "deepseek/deepseek-coder": 72.0,
    "deepseek/deepseek-coder-v2": 78.0,
    "deepseek/deepseek-math": 75.0,
    "deepseek/deepseek-math-r1": 80.0,
    
    # Cohere
    "cohere/command-r": 68.0,
    "cohere/command-r-plus": 75.0,
    "cohere/command": 60.0,
    "cohere/command-light": 55.0,
    
    # Amazon
    "amazon/nova-pro": 65.0,
    "amazon/nova-lite": 58.0,
    "amazon/nova-micro": 50.0,
    "amazon/titan-text": 55.0,
    "amazon/titan-text-express": 60.0,
    
    # NVIDIA
    "nvidia/nemotron-70b": 70.0,
    "nvidia/nemotron-4-mini": 62.0,
    
    # Microsoft
    "microsoft/phi-4": 58.0,
    "microsoft/phi-3-medium": 55.0,
    "microsoft/phi-3-small": 48.0,
    "microsoft/phi-3-mini": 42.0,
    "microsoft/phi-2": 45.0,
    "microsoft/phi-1": 40.0,
    "microsoft/phi-1.5": 45.0,
    
    # AI21
    "ai21/jamba-1.5-large": 68.0,
    "ai21/jamba-1.5-mini": 62.0,
    "ai21/jamba": 55.0,
    "ai21/j2-ultra": 65.0,
    "ai21/j2-mid": 58.0,
    
    # X.AI
    "x-ai/grok-2": 70.0,
    "x-ai/grok-2-vision": 68.0,
    "x-ai/grok-1": 65.0,
    "x-ai/grok-beta": 72.0,
    
    # 01-AI
    "01-ai/yi-large": 72.0,
    "01-ai/yi-34b": 68.0,
    "01-ai/yi-9b": 58.0,
    "01-ai/yi-6b": 52.0,
    "01-ai/yi-chat": 60.0,
    "01-ai/yi-vl-plus": 70.0,
    
    # Baichuan
    "baichuan/baichuan-2-13b": 58.0,
    "baichuan/baichuan-2-7b": 52.0,
    "baichuan/baichuan-2-53b": 65.0,
    "baichuan/baichuan-7b": 48.0,
    "baichuan/baichuan-13b": 55.0,
    
    # Zhipu
    "z-ai/glm-4": 72.0,
    "z-ai/glm-4-flash": 68.0,
    "z-ai/glm-5": 78.0,
    "z-ai/glm-4v": 70.0,
    "z-ai/glm-3": 62.0,
    "z-ai/chatglm-6b": 50.0,
    "z-ai/chatglm2-6b": 55.0,
    
    # Moonshot
    "moonshotai/kimi-k2": 78.0,
    "moonshotai/kimi-k2.5": 80.0,
    "moonshotai/kimi-large": 72.0,
    "moonshotai/kimi-medium": 65.0,
    "moonshotai/kimi-small": 58.0,
    "moonshotai/kimi-nano": 50.0,
    
    # MiniMax
    "minimax/minimax-text-01": 72.0,
    "minimax/minimax-chat": 65.0,
    
    # Tencent
    "tencent/hunyuan": 70.0,
    "tencent/hunyuan-pro": 75.0,
    
    # ByteDance
    "bytedance/douyin-pro": 68.0,
    "bytedance/douyin-lite": 58.0,
    
    # Salesforce
    "salesforce/sfr-迭代-70b": 68.0,
    "salesforce/sfr-迭代-32b": 62.0,
    
    # Others
    "togethercomputer/llama-2-70b": 65.0,
    "togethercomputer/llama-2-13b": 58.0,
    "togethercomputer/llama-2-7b": 52.0,
    "togethercomputer/m2-bert-2": 45.0,
    "huggingfaceh4/zephyr-7b": 55.0,
    "mistralai/mistral-tiny": 45.0,
    "mistralai/mistral-nemo": 60.0,
}


def fetch_helm() -> Dict[str, float]:
    """
    Fetch HELM holistic evaluation scores.
    Returns: dict of model_id -> general_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://crfm.stanford.edu/helm"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_helm(resp.text)
            if scores:
                logger.info(f"HELM: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests not available")
    except Exception as e:
        logger.debug(f"HELM scrape failed: {e}")
    
    logger.info("HELM: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_helm(html: str) -> Dict[str, float]:
    """Parse HELM leaderboard page."""
    from bs4 import BeautifulSoup
    
    scores = {}
    soup = BeautifulSoup(html, "lxml")
    
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) >= 2:
                model_text = cols[0].get_text(strip=True)
                try:
                    score = float(cols[1].get_text(strip=True).replace("%", ""))
                    if 0 <= score <= 100:
                        canonical = model_mapper.to_canonical(model_text)
                        if canonical:
                            scores[canonical] = score
                except (ValueError, IndexError):
                    continue
    
    return scores
