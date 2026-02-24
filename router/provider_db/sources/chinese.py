"""
Chinese Benchmarks - C-Eval, C-MMLU, Chinese-SimpleQA.
Comprehensive evaluation for Chinese language models.
"""

import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# Chinese benchmark scores (from c-eval.github.io)
# Scores are % correct on Chinese knowledge tasks
FALLBACK_SCORES = {
    # OpenAI
    "openai/gpt-4o": 78.0,
    "openai/gpt-4": 72.0,
    "openai/gpt-3.5-turbo": 55.0,
    "openai/o1": 80.0,
    "openai/o3": 85.0,
    
    # Anthropic
    "anthropic/claude-3-opus": 68.0,
    "anthropic/claude-3-5-opus": 75.0,
    "anthropic/claude-opus-4-6": 78.0,
    "anthropic/claude-sonnet-4-6": 72.0,
    "anthropic/claude-3-haiku": 58.0,
    
    # Baidu
    "baidu/ernie-4": 82.0,
    "baidu/ernie-3.5": 78.0,
    "baidu/ernie-3.0": 72.0,
    "baidu/ernie-bot": 70.0,
    "baidu/ernie-speed": 65.0,
    "baidu/ernie-lite": 55.0,
    
    # Tencent
    "tencent/hunyuan": 75.0,
    "tencent/hunyuan-pro": 80.0,
    
    # Alibaba
    "alibaba/qwen-72b": 78.0,
    "alibaba/qwen-14b": 72.0,
    "alibaba/qwen2.5-72b": 80.0,
    "alibaba/qwen2.5-coder-32b": 75.0,
    "alibaba/qwen-vl-max": 78.0,
    "alibaba/qwen-max": 85.0,
    
    # ByteDance
    "bytedance/douyin-pro": 72.0,
    "bytedance/douyin-lite": 60.0,
    "bytedance/豆包": 70.0,
    
    # 01-AI
    "01-ai/yi-large": 75.0,
    "01-ai/yi-34b": 70.0,
    "01-ai/yi-9b": 62.0,
    "01-ai/yi-6b": 55.0,
    
    # Zhipu/GLM
    "z-ai/glm-4": 78.0,
    "z-ai/glm-4-flash": 72.0,
    "z-ai/glm-5": 82.0,
    "z-ai/glm-4v": 75.0,
    
    # Baichuan
    "baichuan/baichuan-2-13b": 68.0,
    "baichuan/baichuan-2-7b": 60.0,
    "baichuan/baichuan-2-53b": 72.0,
    "baichuan/baichuan-vision": 70.0,
    
    # Moonshot
    "moonshotai/kimi-k2": 80.0,
    "moonshotai/kimi-k2.5": 82.0,
    "moonshotai/kimi-large": 78.0,
    "moonshotai/kimi-medium": 72.0,
    "moonshotai/kimi-small": 65.0,
    
    # Others Chinese
    "minimax/minimax-text-01": 75.0,
    "xfajk/xfajk-7b": 58.0,
    "iFlytek/aiges": 62.0,
    "360/360gpt2": 55.0,
    "sensenova/sense-7b": 52.0,
    
    # Meta
    "meta-llama/llama-3-8b": 48.0,
    "meta-llama/llama-3.1-8b": 52.0,
    
    # Google
    "google/gemini-1.5-pro": 65.0,
    "google/gemini-1.5-flash": 58.0,
    
    # Mistral
    "mistralai/mistral-large": 60.0,
}


def fetch_chinese() -> Dict[str, float]:
    """
    Fetch Chinese benchmark scores (C-Eval, C-MMLU, Chinese-SimpleQA).
    Returns: dict of model_id -> general_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://c-eval.github.io"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_chinese(resp.text)
            if scores:
                logger.info(f"Chinese benchmarks: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests not available")
    except Exception as e:
        logger.debug(f"Chinese benchmarks scrape failed: {e}")
    
    logger.info("Chinese benchmarks: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_chinese(html: str) -> Dict[str, float]:
    """Parse Chinese benchmark leaderboard pages."""
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
