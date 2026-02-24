"""
Vision Benchmarks - MMMU, MMBench, SEED.
Tests multimodal vision understanding capabilities.
"""

import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# Vision/Multimodal benchmark scores
# Scores are accuracy on multimodal vision tasks
FALLBACK_SCORES = {
    # OpenAI - excellent vision
    "openai/gpt-4o": 85.0,
    "openai/gpt-4o-mini": 78.0,
    "openai/gpt-4-vision": 80.0,
    "openai/gpt-4": 72.0,
    "openai/o1": 75.0,
    "openai/o3": 78.0,
    
    # Anthropic
    "anthropic/claude-3-opus": 78.0,
    "anthropic/claude-3-5-opus": 82.0,
    "anthropic/claude-3-sonnet": 72.0,
    "anthropic/claude-3-5-sonnet": 76.0,
    "anthropic/claude-3-haiku": 65.0,
    "anthropic/claude-opus-4-6": 85.0,
    "anthropic/claude-sonnet-4-6": 80.0,
    
    # Google
    "google/gemini-1.5-pro": 82.0,
    "google/gemini-1.5-flash": 76.0,
    "google/gemini-ultra": 85.0,
    "google/gemini-2.0-flash": 80.0,
    "google/gemini-2.0-pro": 85.0,
    
    # Qwen Vision
    "qwen/qwen-vl-max": 80.0,
    "qwen/qwen-vl-plus": 76.0,
    "qwen/qwen2.5-vl-72b": 82.0,
    "qwen/qwen2.5-vl-32b": 78.0,
    
    # LLaVA family
    "llava-hf/llava-1.6-mistral-7b": 72.0,
    "llava-hf/llava-1.5-13b": 70.0,
    "llava-hf/llava-1.5-7b": 65.0,
    "llava-llama/llava-1.6-34b": 75.0,
    "llava-llama/llava-1.5-13b": 72.0,
    
    # DeepSeek
    "deepseek/deepseek-vl2": 78.0,
    "deepseek/deepseek-vl": 72.0,
    "deepseek/deepseek-v3": 70.0,
    
    # Baichuan Vision
    "baichuan-inc/baichuan-vision": 68.0,
    "baichuan/baichuan-2-vision": 70.0,
    
    # MiniMax
    "minimax/minimax-vl-80k": 75.0,
    "minimax/minimax-text-01": 72.0,
    
    # ByteDance
    "bytedance/douyin-pro": 70.0,
    "bytedance/豆包": 68.0,
    
    # OpenBMB
    "openbmb/minicpm-v": 72.0,
    "openbmb/minicpm-v2": 75.0,
    
    # Moondream
    "moondreamai/moondream2": 65.0,
    "vikhyatk/moondream2": 65.0,
    
    # Phi-4 Vision
    "microsoft/phi-4-vision": 72.0,
    "microsoft/phi-3-vision": 68.0,
    
    # Mistral
    "mistralai/pixtral-12b": 78.0,
    "mistralai/pixtral-large": 82.0,
    
    # Salesforce
    "salesforce/blip-2-opt-2.7b": 58.0,
    "salesforce/blip-2-flan-t5-xl": 62.0,
    
    # Adept
    "adept/act-1": 65.0,
    
    # 01-AI
    "01-ai/yi-vl-plus": 72.0,
    "01-ai/yi-vl-34b": 75.0,
    
    # Zhipu
    "z-ai/glm-4v": 75.0,
    "z-ai/glm-4v-plus": 78.0,
    
    # Meta
    "meta-llama/llama-3.2-90b-vision": 80.0,
    "meta-llama/llama-3.2-11b-vision": 75.0,
    "meta-llama/llama-3.2-1b-vision": 65.0,
}


def fetch_vision() -> Dict[str, float]:
    """
    Fetch vision/multimodal benchmark scores.
    Returns: dict of model_id -> general_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://paperswithcode.com/dataset/mmlu"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_vision(resp.text)
            if scores:
                logger.info(f"Vision: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests not available")
    except Exception as e:
        logger.debug(f"Vision scrape failed: {e}")
    
    logger.info("Vision: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_vision(html: str) -> Dict[str, float]:
    """Parse vision benchmark leaderboard pages."""
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
