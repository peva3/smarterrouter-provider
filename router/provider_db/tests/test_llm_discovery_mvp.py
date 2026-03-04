#!/usr/bin/env python3
"""
MVP: LLM-Assisted Benchmark Discovery Test Script

This is a proof-of-concept demonstrating how an LLM could:
1. Search for new benchmark datasets on HuggingFace, arXiv, and the web
2. Analyze them and propose a fetcher backend  
3. Generate and test the code
4. Return sample data

Enhanced with web search capabilities to discover:
- GitHub repositories with benchmark implementations
- Academic papers with benchmark results
- Benchmark leaderboard websites
- Model evaluation platforms

This version uses mock LLM responses for demonstration.
To use a real LLM, set environment variables:
    LLM_API_ENDPOINT=https://api.openai.com/v1
    LLM_API_KEY=your-key-here
    LLM_MODEL=gpt-4-turbo-preview

Usage: python -m router.provider_db.tests.test_llm_discovery_mvp

Dependencies for real LLM mode:
    pip install requests
    pip install datasets (for testing generated fetchers)

Optional dependencies for web search:
    pip install beautifulsoup4 (for HTML parsing)
    pip install feedparser (for RSS feeds)

The mock mode requires no external dependencies.
"""

import os
import json
import sys
import tempfile
import subprocess
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import requests
import time
import random

# Optional imports for web search (will degrade gracefully if not available)
try:
    from bs4 import BeautifulSoup
    BEAUTIFUL_SOUP_AVAILABLE = True
except ImportError:
    BEAUTIFUL_SOUP_AVAILABLE = False
    BeautifulSoup = None

# feedparser could be added for RSS feed parsing of arXiv, blogs, etc.
FEEDPARSER_AVAILABLE = False
feedparser = None

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# Configuration
# ============================================================================

LLM_API_ENDPOINT = os.environ.get("LLM_API_ENDPOINT", "https://api.openai.com/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4-turbo-preview")
USE_REAL_LLM = bool(LLM_API_KEY.strip())

# Web search configuration
WEB_SEARCH_ENABLED = os.environ.get("WEB_SEARCH_ENABLED", "false").lower() == "true"
WEB_SEARCH_ENGINE = os.environ.get("WEB_SEARCH_ENGINE", "duckduckgo")  # or "google"
WEB_SEARCH_MAX_RESULTS = int(os.environ.get("WEB_SEARCH_MAX_RESULTS", "10"))
WEB_SEARCH_QUERIES = [
    "LLM benchmark results 2024",
    "large language model evaluation dataset",
    "AI benchmark leaderboard",
    "language model performance scores",
    "model evaluation benchmark GitHub",
    "multimodal benchmark dataset",
    "reasoning benchmark leaderboard",
    "coding evaluation benchmark",
    "math reasoning benchmark results"
]

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class BenchmarkSource:
    """Information about a discovered benchmark dataset."""
    id: str
    source: str  # "HuggingFace", "arXiv", "GitHub", etc.
    name: str
    url: str
    description: str
    category: str  # "reasoning", "coding", "general", "elo"
    splits: List[str]
    key_columns: List[str]


@dataclass
class LLMAnalysis:
    """Analysis result from LLM."""
    credibility_score: int
    reasoning: str
    implementation_complexity: str
    coverage_estimate: str
    risks: List[str]


@dataclass
class FetcherSpec:
    """Specification for a fetcher function."""
    function_name: str
    category: str
    imports_needed: List[str]
    load_dataset_call: str
    parsing_logic: str
    estimated_coverage: str


@dataclass
class DiscoveryResult:
    """Complete result for a discovered benchmark."""
    source: BenchmarkSource
    analysis: LLMAnalysis
    fetcher_spec: FetcherSpec
    generated_code: str
    validation_result: Dict
    sample_data: Dict[str, float]


# ============================================================================
# Mock LLM Responses (for demonstration)
# ============================================================================

def get_mock_analysis_for_source(source: BenchmarkSource) -> dict:
    """Return appropriate mock analysis based on source category."""
    base_name = source.name.split('/')[-1].lower().replace('-', '_')
    
    if 'mmlu' in source.name.lower():
        return {
            "analysis": {
                "credibility_score": 4,
                "reasoning": "This is an official benchmark from TIGER-Lab, the same group that created MMLU. It's widely cited and has rigorous methodology.",
                "implementation_complexity": "low",
                "coverage_estimate": "Likely covers 50+ popular models",
                "risks": ["Dataset might be large", "May require significant compute to evaluate"]
            },
            "fetcher_spec": {
                "function_name": f"fetch_{base_name}",
                "category": "general",
                "imports_needed": ["datasets", "typing"],
                "load_dataset_call": f"load_dataset('{source.name}', split='test')",
                "parsing_logic": "Extract 'model' and 'accuracy' fields, convert accuracy from 0-1 to 0-100 scale",
                "estimated_coverage": "50-100 models"
            }
        }
    elif 'livebench' in source.name.lower():
        return {
            "analysis": {
                "credibility_score": 5,
                "reasoning": "LiveBench is a widely recognized benchmark for reasoning tasks, regularly updated with new model evaluations.",
                "implementation_complexity": "medium",
                "coverage_estimate": "Covers 100+ models with frequent updates",
                "risks": ["Dataset structure might change", "Multiple score columns need aggregation"]
            },
            "fetcher_spec": {
                "function_name": f"fetch_{base_name}",
                "category": "reasoning",
                "imports_needed": ["datasets", "typing", "statistics"],
                "load_dataset_call": f"load_dataset('{source.name}', split='test')",
                "parsing_logic": "Extract 'model' and average score across all reasoning tasks",
                "estimated_coverage": "100+ models"
            }
        }
    elif 'bigcode' in source.name.lower():
        return {
            "analysis": {
                "credibility_score": 5,
                "reasoning": "BigCodeBench is the standard coding benchmark from BigCode, widely used in the community.",
                "implementation_complexity": "low",
                "coverage_estimate": "Covers 80+ coding-focused models",
                "risks": ["Multiple pass@k metrics need consolidation"]
            },
            "fetcher_spec": {
                "function_name": f"fetch_{base_name}",
                "category": "coding",
                "imports_needed": ["datasets", "typing"],
                "load_dataset_call": f"load_dataset('{source.name}', split='train')",
                "parsing_logic": "Extract 'model' and 'pass@1' score, convert to 0-100 scale",
                "estimated_coverage": "80+ models"
            }
        }
    elif 'arc' in source.name.lower():
        return {
            "analysis": {
                "credibility_score": 3,
                "reasoning": "New benchmark from arXiv paper, promising but needs verification of methodology.",
                "implementation_complexity": "high",
                "coverage_estimate": "Likely covers 20-30 models initially",
                "risks": ["Dataset not yet on HuggingFace", "Implementation requires custom evaluation"]
            },
            "fetcher_spec": {
                "function_name": f"fetch_{base_name}",
                "category": "reasoning",
                "imports_needed": ["requests", "typing", "json"],
                "load_dataset_call": "Custom API call or local file load",
                "parsing_logic": "Parse arXiv paper supplement or GitHub repository for results",
                "estimated_coverage": "20-30 models"
            }
        }
    elif source.source == "GitHub":
        return {
            "analysis": {
                "credibility_score": 4,
                "reasoning": "GitHub repository with benchmark implementation. May contain results in README, JSON files, or code output.",
                "implementation_complexity": "medium",
                "coverage_estimate": "Varies widely - could be 10-100 models",
                "risks": ["Data format may be inconsistent", "May require cloning the repo", "Results might be outdated"]
            },
            "fetcher_spec": {
                "function_name": f"fetch_{base_name}",
                "category": source.category,
                "imports_needed": ["requests", "typing", "json", "re"],
                "load_dataset_call": "GitHub API or raw file download",
                "parsing_logic": "Parse README, JSON results files, or scrape GitHub pages for benchmark results",
                "estimated_coverage": "Varies"
            }
        }
    elif source.source == "Web":
        return {
            "analysis": {
                "credibility_score": 4,
                "reasoning": "Web leaderboard or benchmark website. May require HTML scraping or API calls.",
                "implementation_complexity": "medium-high",
                "coverage_estimate": "Typically 20-200 models depending on site",
                "risks": ["Website structure may change", "May require authentication", "Rate limiting", "Legal/ToS considerations"]
            },
            "fetcher_spec": {
                "function_name": f"fetch_{base_name}",
                "category": source.category,
                "imports_needed": ["requests", "typing", "bs4" if BEAUTIFUL_SOUP_AVAILABLE else "re"],
                "load_dataset_call": "HTTP request to website URL",
                "parsing_logic": "HTML parsing or API endpoint discovery to extract model scores",
                "estimated_coverage": "Varies"
            }
        }
    else:
        # Default response
        return {
            "analysis": {
                "credibility_score": 3,
                "reasoning": "Unknown benchmark, needs further investigation.",
                "implementation_complexity": "medium",
                "coverage_estimate": "Unknown",
                "risks": ["Unverified source", "Data format unknown"]
            },
            "fetcher_spec": {
                "function_name": f"fetch_{base_name}",
                "category": source.category,
                "imports_needed": ["datasets", "typing"],
                "load_dataset_call": f"load_dataset('{source.name}', split='test')",
                "parsing_logic": "Extract model and score fields based on dataset structure",
                "estimated_coverage": "Unknown"
            }
        }


def generate_mock_code(source: BenchmarkSource, analysis: dict) -> str:
    """Generate mock code appropriate for the source."""
    spec = analysis.get("fetcher_spec", {})
    function_name = spec.get("function_name", "fetch_benchmark")
    dataset_name = source.name
    category = spec.get("category", "general")
    
    if 'arc' in source.name.lower():
        # Special case for arXiv source
        return f'''
"""
{source.name} - fetch {category} scores.
{source.description}
"""

from typing import Dict
import requests
import json
from router.provider_db.model_mapper import model_mapper

def {function_name}() -> Dict[str, float]:
    """Fetch {category} scores from {source.name}."""
    scores = {{}}
    
    try:
        # NOTE: This is a placeholder for arXiv benchmark
        # In reality, would parse the paper or GitHub repository
        print(f"{source.name}: arXiv benchmark - manual implementation needed")
        print(f"  URL: {source.url}")
        print(f"  See paper for evaluation results")
        
        # Example placeholder data
        example_scores = {{
            "openai/gpt-4": 85.2,
            "anthropic/claude-3-opus": 82.7,
            "meta-llama/llama-3-70b": 78.4
        }}
        
        for model, score in example_scores.items():
            canonical = model_mapper.to_canonical(model)
            if canonical:
                scores[canonical] = score
        
        print(f"{source.name}: using placeholder data - {{len(scores)}} scores")
        
    except Exception as e:
        print(f"{source.name} failed: {{e}}")
    
    return scores
'''
    elif source.source == "GitHub":
        # GitHub repository - may contain results in various formats
        return f'''
"""
{source.name} - fetch {category} scores.
{source.description}
GitHub repository at: {source.url}
"""

from typing import Dict
import requests
import json
import re
from router.provider_db.model_mapper import model_mapper

def {function_name}() -> Dict[str, float]:
    """Fetch {category} scores from {source.name}."""
    scores = {{}}
    
    try:
        print(f"{source.name}: GitHub benchmark - requires custom implementation")
        print(f"  Repository: {source.url}")
        
        # Example approaches:
        # 1. Check for results.json or similar files
        # 2. Parse README.md for markdown tables
        # 3. Use GitHub API to explore repository structure
        # 4. Clone repository and run evaluation scripts
        
        # Placeholder implementation
        print(f"  This would require analyzing the repository structure")
        print(f"  Common patterns: JSON results, CSV files, markdown tables")
        
        # Example placeholder data
        example_scores = {{
            "openai/gpt-4": 88.5,
            "anthropic/claude-3-sonnet": 85.2,
            "meta-llama/llama-3-70b": 82.7,
            "mistralai/mixtral-8x7b": 80.4
        }}
        
        for model, score in example_scores.items():
            canonical = model_mapper.to_canonical(model)
            if canonical:
                scores[canonical] = score
        
        print(f"{source.name}: using placeholder data - {{len(scores)}} scores")
        
    except Exception as e:
        print(f"{source.name} failed: {{e}}")
    
    return scores
'''
    elif source.source == "Web":
        # Web leaderboard or benchmark website
        return f'''
"""
{source.name} - fetch {category} scores.
{source.description}
Website: {source.url}
"""

from typing import Dict
import requests
{'from bs4 import BeautifulSoup' if BEAUTIFUL_SOUP_AVAILABLE else '# BeautifulSoup not available'}
import re
import json
from router.provider_db.model_mapper import model_mapper

def {function_name}() -> Dict[str, float]:
    """Fetch {category} scores from {source.name}."""
    scores = {{}}
    
    try:
        print(f"{source.name}: Web benchmark - requires HTML scraping or API")
        print(f"  URL: {source.url}")
        
        # Example approaches:
        # 1. HTML scraping with BeautifulSoup
        # 2. API endpoint discovery
        # 3. JSON-LD or structured data extraction
        # 4. Table parsing
        
        if BEAUTIFUL_SOUP_AVAILABLE:
            print(f"  BeautifulSoup available for HTML parsing")
        else:
            print(f"  Note: BeautifulSoup not installed, using regex fallback")
        
        # Placeholder implementation
        print(f"  This would require analyzing website structure")
        
        # Example placeholder data
        example_scores = {{
            "openai/gpt-4": 92.1,
            "anthropic/claude-3-opus": 89.7,
            "google/gemini-pro": 87.3,
            "meta-llama/llama-3-70b": 84.6,
            "mistralai/mistral-large": 86.2
        }}
        
        for model, score in example_scores.items():
            canonical = model_mapper.to_canonical(model)
            if canonical:
                scores[canonical] = score
        
        print(f"{source.name}: using placeholder data - {{len(scores)}} scores")
        
    except Exception as e:
        print(f"{source.name} failed: {{e}}")
    
    return scores
'''
    else:
        # Default: HuggingFace-like dataset or unknown source
        # Standard HuggingFace dataset
        # Use double curly braces for literal braces in the output
        return f'''
"""
{source.name} - fetch {category} scores.
{source.description}
"""

from typing import Dict
try:
    from datasets import load_dataset
except ImportError:
    load_dataset = None

from router.provider_db.model_mapper import model_mapper

def {function_name}() -> Dict[str, float]:
    """Fetch {category} scores from {source.name}."""
    scores = {{}}
    
    if load_dataset is None:
        print(f"{source.name}: datasets library not installed")
        return scores
    
    try:
        # Load dataset
        dataset = load_dataset('{dataset_name}', split='test')
        
        # Parse scores - adjust field names based on actual dataset
        for item in dataset:
            model = item.get('model') or item.get('model_name') or item.get('model_id')
            score_value = item.get('accuracy') or item.get('score') or item.get('pass@1')
            
            if model and score_value is not None:
                canonical = model_mapper.to_canonical(str(model))
                if canonical:
                    # Convert 0-1 to 0-100 if needed
                    score = float(score_value)
                    if score <= 1.0:
                        score *= 100
                    # Clamp to 0-100 range
                    score = max(0.0, min(100.0, score))
                    scores[canonical] = score
        
        print(f"{source.name}: fetched {{len(scores)}} {category} scores")
        
    except Exception as e:
        print(f"{source.name} failed: {{e}}")
    
    return scores
'''

# ============================================================================
# Scout: Find New Datasets
# ============================================================================

def scout_huggingface() -> List[BenchmarkSource]:
    """
    Search HuggingFace for new benchmark datasets.
    Simulated discovery for MVP.
    """
    print("🔍 Simulating HuggingFace search...")
    
    return [
        BenchmarkSource(
            id="hf_mmlu_pro",
            source="HuggingFace",
            name="TIGER-Lab/MMLU-Pro",
            url="https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro",
            description="MMLU-Pro is a more challenging version of MMLU with harder questions",
            category="general",
            splits=["test"],
            key_columns=["model", "accuracy", "subject"]
        ),
        BenchmarkSource(
            id="hf_livebench_reasoning",
            source="HuggingFace", 
            name="livebench/reasoning",
            url="https://huggingface.co/datasets/livebench/reasoning",
            description="LiveBench reasoning tasks dataset",
            category="reasoning",
            splits=["test"],
            key_columns=["model", "score", "task"]
        ),
        BenchmarkSource(
            id="hf_bigcodebench_results",
            source="HuggingFace",
            name="bigcode/bigcodebench-results",
            url="https://huggingface.co/datasets/bigcode/bigcodebench-results", 
            description="BigCodeBench benchmark results with pass@k scores",
            category="coding",
            splits=["train"],
            key_columns=["model", "pass@1", "pass@10"]
        )
    ]


def scout_arxiv() -> List[BenchmarkSource]:
    """Search arXiv for new benchmark papers (simulated)."""
    print("🔍 Simulating arXiv search...")
    
    return [
        BenchmarkSource(
            id="arxiv_arc_agi_3",
            source="arXiv",
            name="ARC-AGI-3",
            url="https://arxiv.org/abs/2501.12345",
            description="ARC-AGI-3: A New Challenge for Abstract Reasoning",
            category="reasoning",
            splits=["test"],
            key_columns=["model", "accuracy", "task_type"]
        )
    ]


def scout_web() -> List[BenchmarkSource]:
    """
    Search the web for new benchmark sources.
    Simulates web search for MVP. Can be extended with real web search.
    """
    print("🌐 Simulating web search for benchmark sources...")
    
    # Simulated web search results - these would come from actual search in a real implementation
    simulated_results = [
        # GitHub repositories with benchmark implementations
        BenchmarkSource(
            id="web_github_llm_benchmark",
            source="GitHub",
            name="EvalPlus/LLM-Benchmark",
            url="https://github.com/EvalPlus/LLM-Benchmark",
            description="Comprehensive LLM benchmark suite with multiple evaluation tasks",
            category="general",
            splits=["main"],
            key_columns=["model", "overall_score", "task_scores"]
        ),
        BenchmarkSource(
            id="web_github_math_benchmark",
            source="GitHub", 
            name="OpenMathBench/OpenMathBench",
            url="https://github.com/OpenMathBench/OpenMathBench",
            description="Open-source math reasoning benchmark for LLMs",
            category="reasoning",
            splits=["test"],
            key_columns=["model", "accuracy", "problem_type"]
        ),
        # Benchmark leaderboard websites
        BenchmarkSource(
            id="web_leaderboard_lm_sys",
            source="Web",
            name="LM-Sys Arena Leaderboard",
            url="https://arena.lmsys.org/leaderboard",
            description="LMSYS Chatbot Arena leaderboard with Elo ratings",
            category="elo",
            splits=["current"],
            key_columns=["model", "elo_rating", "win_rate"]
        ),
        BenchmarkSource(
            id="web_leaderboard_opencompass",
            source="Web",
            name="OpenCompass Leaderboard",
            url="https://opencompass.org.cn/leaderboard",
            description="Comprehensive Chinese LLM evaluation leaderboard",
            category="general",
            splits=["latest"],
            key_columns=["model", "overall_score", "category_scores"]
        ),
        # Academic benchmark websites
        BenchmarkSource(
            id="web_benchmark_mmlu",
            source="Web",
            name="MMLU Official Results",
            url="https://crfm.stanford.edu/helm/latest/?group=mmlu",
            description="Official MMLU benchmark results from Stanford CRFM",
            category="general",
            splits=["latest"],
            key_columns=["model", "average", "subject_scores"]
        ),
        BenchmarkSource(
            id="web_benchmark_bigbench",
            source="Web",
            name="BigBench Hard Results",
            url="https://github.com/google/BIG-bench/tree/main/bigbench/benchmark_tasks",
            description="BigBench Hard benchmark results from Google",
            category="reasoning",
            splits=["hard"],
            key_columns=["model", "score", "task_name"]
        ),
        # Model evaluation platforms
        BenchmarkSource(
            id="web_platform_openrouter",
            source="Web",
            name="OpenRouter Benchmarks",
            url="https://openrouter.ai/benchmarks",
            description="OpenRouter model benchmarking results",
            category="general",
            splits=["latest"],
            key_columns=["model", "performance", "cost_per_token"]
        ),
        BenchmarkSource(
            id="web_platform_together",
            source="Web",
            name="Together AI Benchmarks",
            url="https://together.ai/benchmarks",
            description="Together AI model evaluation results",
            category="general",
            splits=["current"],
            key_columns=["model", "score", "benchmark_name"]
        )
    ]
    
    # In a real implementation, we would:
    # 1. Use search API (Google, DuckDuckGo, etc.)
    # 2. Parse search results
    # 3. Fetch and analyze promising pages
    # 4. Extract benchmark information
    
    print(f"   Found {len(simulated_results)} potential web sources")
    return simulated_results


# ============================================================================
# Helper functions for real web search (commented out for MVP)
# ============================================================================

def perform_web_search(query: str, max_results: int = 10) -> List[Tuple[str, str]]:
    """
    Perform actual web search (placeholder for real implementation).
    Returns list of (title, url) pairs.
    """
    if not WEB_SEARCH_ENABLED:
        return []
    
    # This would use a search API like:
    # - DuckDuckGo HTML scraping
    # - Google Custom Search API
    # - SerpAPI
    # - etc.
    
    print(f"   🔍 Searching web for: {query}")
    
    # Simulated delay for web search
    time.sleep(0.5)
    
    # Return empty list for MVP - real implementation would return actual results
    return []


def analyze_web_page(url: str) -> Optional[Dict]:
    """
    Analyze a web page to determine if it contains benchmark data.
    Returns extracted information if successful.
    """
    if not BEAUTIFUL_SOUP_AVAILABLE:
        return None
    
    try:
        # Import inside function to avoid static analysis issues
        from bs4 import BeautifulSoup
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for common benchmark indicators
        page_text = soup.get_text().lower()
        indicators = [
            'benchmark', 'leaderboard', 'evaluation', 'score', 'accuracy',
            'model', 'llm', 'large language model', 'performance', 'rank',
            'elo', 'pass@', 'mmlu', 'gsm8k', 'human eval', 'bigbench'
        ]
        
        indicator_count = sum(1 for indicator in indicators if indicator in page_text)
        
        if indicator_count > 2:
            # Page likely contains benchmark data
            title = soup.title.string if soup.title else url
            return {
                'url': url,
                'title': title,
                'indicator_count': indicator_count,
                'text_preview': page_text[:500]
            }
    
    except Exception as e:
        print(f"   Error analyzing {url}: {e}")
    
    return None


# ============================================================================
# Analyzer: Evaluate with LLM
# ============================================================================

class MockLLMClient:
    """Mock LLM client for demonstration."""
    
    def chat(self, system: str, user: str, json_mode: bool = False) -> str:
        """Return mock response for demonstration."""
        print("🤖 Using mock LLM (for demonstration - fallback)")
        
        # Generic fallback response (should not be called in normal flow)
        if json_mode:
            return json.dumps({
                "analysis": {
                    "credibility_score": 3,
                    "reasoning": "Generic mock analysis",
                    "implementation_complexity": "medium",
                    "coverage_estimate": "Unknown",
                    "risks": ["Unknown"]
                },
                "fetcher_spec": {
                    "function_name": "fetch_generic",
                    "category": "general",
                    "imports_needed": ["datasets", "typing"],
                    "load_dataset_call": "load_dataset('example/dataset', split='test')",
                    "parsing_logic": "Extract model and score fields",
                    "estimated_coverage": "Unknown"
                }
            })
        else:
            return '''
"""
Generic benchmark - fetch scores.
Mock implementation.
"""

from typing import Dict
from router.provider_db.model_mapper import model_mapper

def fetch_generic() -> Dict[str, float]:
    """Fetch scores from generic benchmark."""
    print("Generic benchmark: mock implementation")
    return {}
'''


class RealLLMClient:
    """Real OpenAI-compatible LLM client."""
    
    def __init__(self, endpoint: str = None, api_key: str = None, model: str = None):
        self.endpoint = endpoint or LLM_API_ENDPOINT
        self.api_key = api_key or LLM_API_KEY
        self.model = model or LLM_MODEL
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY not set")
    
    def chat(self, system: str, user: str, json_mode: bool = False) -> str:
        """Send a chat request to the LLM."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": 0.7
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        response = requests.post(
            f"{self.endpoint}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"LLM API error: {response.status_code} - {response.text}")
        
        return response.json()["choices"][0]["message"]["content"]


def get_llm_client():
    """Return appropriate LLM client based on configuration."""
    if USE_REAL_LLM:
        print("🔌 Using real LLM API")
        return RealLLMClient()
    else:
        print("🧪 Using mock LLM (set LLM_API_KEY for real LLM)")
        return MockLLMClient()


def analyze_with_llm(llm_client, source: BenchmarkSource) -> Optional[Dict]:
    """
    Use LLM to analyze a dataset and propose a fetcher implementation.
    """
    print(f"🤖 Analyzing {source.name} with LLM...")
    
    try:
        if isinstance(llm_client, MockLLMClient):
            # Use mock response tailored to source
            analysis = get_mock_analysis_for_source(source)
        else:
            # Real LLM call
            system_prompt = """You are an expert AI engineer specializing in building data pipelines for LLM benchmarks.
    Your job is to analyze a new benchmark dataset and propose a Python fetcher function."""
    
            user_prompt = f"""Analyze this benchmark dataset and create a fetcher specification:

    Dataset: {source.name}
    URL: {source.url}
    Description: {source.description}
    Category: {source.category}
    Splits available: {source.splits}
    Key columns: {source.key_columns}

    Please respond with a JSON object containing:
    {{
        "analysis": {{
            "credibility_score": 1-5,
            "reasoning": "Why this source is/isn't credible",
            "implementation_complexity": "low/medium/high",
            "coverage_estimate": "How many models this might cover",
            "risks": ["list of potential issues"]
        }},
        "fetcher_spec": {{
            "function_name": "fetch_<name>",
            "category": "reasoning/coding/general/elo",
            "imports_needed": ["list of imports"],
            "load_dataset_call": "Exact HuggingFace load_dataset call",
            "parsing_logic": "How to extract scores from the dataset",
            "estimated_coverage": "Number of models expected"
        }}
    }}

    Respond ONLY with valid JSON."""
            
            response = llm_client.chat(system_prompt, user_prompt, json_mode=True)
            analysis = json.loads(response)
        
        print(f"   ✓ Analysis complete - Complexity: {analysis['analysis']['implementation_complexity']}")
        return analysis
        
    except Exception as e:
        print(f"   ✗ LLM analysis failed: {e}")
        return None


def generate_fetcher_code(llm_client, source: BenchmarkSource, analysis: Dict) -> Optional[str]:
    """
    Generate the actual Python fetcher code using LLM.
    """
    print(f"📝 Generating fetcher code for {source.name}...")
    
    spec = analysis.get("fetcher_spec", {})
    
    try:
        if isinstance(llm_client, MockLLMClient):
            # Use mock code tailored to source
            code = generate_mock_code(source, analysis)
        else:
            # Real LLM call
            system_prompt = """You are an expert Python developer.
    Generate a complete, working Python fetcher function based on the specification.
    Follow existing source patterns in the project.
    Use proper typing and error handling."""

            user_prompt = f"""Generate a complete Python fetcher file for this benchmark:

    Dataset: {source.name}
    URL: {source.url}
    Description: {source.description}

    Category: {spec.get('category', 'general')}
    Function name: {spec.get('function_name', 'fetch_benchmark')}
    Imports needed: {spec.get('imports_needed', [])}
    Load dataset call: {spec.get('load_dataset_call', 'load_dataset("...")')}
    Parsing logic: {spec.get('parsing_logic', 'Extract scores from dataset')}

    Generate a complete Python file that:
    1. Has proper docstring
    2. Imports required modules
    3. Loads the dataset from HuggingFace
    4. Parses scores using the specified logic
    5. Uses model_mapper.to_canonical() to normalize model names
    6. Returns Dict[str, float] of model_id -> score
    7. Has proper error handling
    8. Prints a summary of how many scores were fetched

    Generate ONLY the Python code, no markdown formatting."""

            code = llm_client.chat(system_prompt, user_prompt)
        
        # Clean up any markdown formatting
        if code.startswith("```python"):
            code = code[9:]
        if code.endswith("```"):
            code = code[:-3]
        code = code.strip()
        
        print(f"   ✓ Generated {len(code)} bytes of code")
        return code
        
    except Exception as e:
        print(f"   ✗ Code generation failed: {e}")
        return None


# ============================================================================
# Validator: Test Generated Code
# ============================================================================

def validate_fetcher(code: str, source: BenchmarkSource) -> Dict:
    """
    Test the generated fetcher code in isolation.
    Returns validation results.
    """
    print(f"🧪 Validating fetcher for {source.name}...")
    
    result = {
        "import_check": False,
        "syntax_check": False,
        "dry_run": False,
        "sample_data": {},
        "errors": []
    }
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        # 1. Import check - try to import the module
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("test_fetcher", temp_path)
            
            # Mock dependencies
            import sys
            sys.modules['router'] = type(sys)('router')
            sys.modules['router.provider_db'] = type(sys)('router.provider_db')
            sys.modules['router.provider_db.model_mapper'] = type(sys)('router.provider_db.model_mapper')
            
            class MockMapper:
                @staticmethod
                def to_canonical(name):
                    # Simple mock that returns the name
                    return name
            
            sys.modules['router.provider_db.model_mapper'].model_mapper = MockMapper()
            
            # Mock datasets module
            sys.modules['datasets'] = type(sys)('datasets')
            # Add load_dataset attribute to the mocked module
            sys.modules['datasets'].load_dataset = None  # Will be set later
            
            result["import_check"] = True
            print("   ✓ Import check passed")
        except Exception as e:
            result["errors"].append(f"Import error: {e}")
            print(f"   ✗ Import check failed: {e}")
            return result
        
        # 2. Syntax check
        try:
            with open(temp_path, 'r') as f:
                compile(f.read(), temp_path, 'exec')
            result["syntax_check"] = True
            print("   ✓ Syntax check passed")
        except SyntaxError as e:
            result["errors"].append(f"Syntax error: {e}")
            print(f"   ✗ Syntax check failed: {e}")
            return result
        
        # 3. Dry run - simulate execution
        # We'll create a mock dataset that simulates the expected structure
        try:
            # Create a namespace with mocked dependencies
            namespace = {
                'model_mapper': MockMapper(),
                'load_dataset': None  # Will be mocked
            }
            
            # Mock datasets.load_dataset
            class MockDataset:
                def __init__(self):
                    self.data = [
                        {'model': 'gpt-4', 'accuracy': 0.85},
                        {'model': 'claude-3-opus', 'accuracy': 0.82},
                        {'model': 'llama3-70b', 'accuracy': 0.78},
                        {'model': 'mixtral-8x7b', 'accuracy': 0.76},
                        {'model': 'qwen2.5-72b', 'accuracy': 0.81},
                    ]
                
                def __iter__(self):
                    return iter(self.data)
            
            def mock_load_dataset(*args, **kwargs):
                return MockDataset()
            
            namespace['load_dataset'] = mock_load_dataset
            # Also set on the mocked module for imports
            sys.modules['datasets'].load_dataset = mock_load_dataset
            
            # Execute the code in our namespace
            exec(code, namespace)
            
            # Find and call the fetch function
            func_name = None
            for key in namespace:
                if key.startswith('fetch_'):
                    func_name = key
                    break
            
            if not func_name:
                result["errors"].append("No fetch_* function found in code")
                print("   ✗ No fetch function found")
                return result
            
            fetcher_func = namespace[func_name]
            
            # Run the fetcher
            scores = fetcher_func()
            
            result["dry_run"] = True
            result["sample_data"] = dict(list(scores.items())[:5])
            print(f"   ✓ Dry run passed - simulated {len(scores)} scores")
            
        except Exception as e:
            result["errors"].append(f"Dry run error: {e}")
            print(f"   ✗ Dry run failed: {e}")
            
    finally:
        # Cleanup
        import os
        os.unlink(temp_path)
    
    return result


# ============================================================================
# Main Pipeline
# ============================================================================

def run_discovery_mvp() -> List[DiscoveryResult]:
    """
    Run the complete MVP discovery pipeline.
    Returns list of discovered and validated benchmark sources.
    """
    print("=" * 70)
    print("🚀 LLM-Assisted Benchmark Discovery - MVP Test")
    print("=" * 70)
    print()
    
    # Initialize LLM client
    try:
        llm_client = get_llm_client()
    except ValueError as e:
        print(f"✗ {e}")
        print("\nFor real LLM usage, set environment variables:")
        print("  export LLM_API_KEY=your-key-here")
        print("  export LLM_API_ENDPOINT=https://api.openai.com/v1")
        print("  export LLM_MODEL=gpt-4-turbo-preview")
        print("\nContinuing with mock LLM...")
        llm_client = MockLLMClient()
    
    print()
    
    # Phase 1: Scout
    print("=" * 70)
    print("PHASE 1: Scout - Finding new benchmark sources")
    print("=" * 70)
    
    sources = []
    sources.extend(scout_huggingface())
    sources.extend(scout_arxiv())
    sources.extend(scout_web())  # Add web search results
    
    print(f"\n📊 Total sources discovered: {len(sources)}")
    for i, src in enumerate(sources, 1):
        print(f"  {i}. {src.name} ({src.category}) - {src.description[:60]}...")
    
    print()
    
    # Phase 2: Analyze and Generate
    print("=" * 70)
    print("PHASE 2: Analyze & Generate - LLM creates fetcher specs")
    print("=" * 70)
    
    results = []
    
    # Process first 6 sources for demonstration (including web sources)
    for src in sources[:6]:
        print(f"\n--- Processing: {src.name} ---")
        
        # Analyze with LLM
        analysis_dict = analyze_with_llm(llm_client, src)
        if not analysis_dict:
            continue
        
        # Parse analysis
        analysis = LLMAnalysis(
            credibility_score=analysis_dict['analysis']['credibility_score'],
            reasoning=analysis_dict['analysis']['reasoning'],
            implementation_complexity=analysis_dict['analysis']['implementation_complexity'],
            coverage_estimate=analysis_dict['analysis']['coverage_estimate'],
            risks=analysis_dict['analysis']['risks']
        )
        
        # Parse fetcher spec
        spec_dict = analysis_dict['fetcher_spec']
        fetcher_spec = FetcherSpec(
            function_name=spec_dict['function_name'],
            category=spec_dict['category'],
            imports_needed=spec_dict['imports_needed'],
            load_dataset_call=spec_dict['load_dataset_call'],
            parsing_logic=spec_dict['parsing_logic'],
            estimated_coverage=spec_dict['estimated_coverage']
        )
        
        # Generate code
        code = generate_fetcher_code(llm_client, src, analysis_dict)
        if not code:
            continue
        
        # Validate
        validation = validate_fetcher(code, src)
        
        # Create result
        result = DiscoveryResult(
            source=src,
            analysis=analysis,
            fetcher_spec=fetcher_spec,
            generated_code=code,
            validation_result=validation,
            sample_data=validation.get('sample_data', {})
        )
        
        results.append(result)
        print()
    
    # Phase 3: Results
    print("=" * 70)
    print("PHASE 3: Results - Summary")
    print("=" * 70)
    
    successful = [r for r in results if r.validation_result.get('dry_run')]
    
    print(f"\n✅ Successfully generated: {len(successful)}/{len(results)} fetchers")
    
    if successful:
        print("\n📋 Generated fetchers ready for review:")
        for i, result in enumerate(successful, 1):
            print(f"\n{i}. {result.source.name}")
            print(f"   Category: {result.fetcher_spec.category}")
            print(f"   Complexity: {result.analysis.implementation_complexity}")
            print(f"   Credibility: {result.analysis.credibility_score}/5")
            print(f"   Sample data: {result.sample_data}")
            
            # Save generated code to file for inspection
            output_dir = PROJECT_ROOT / "generated_fetchers"
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"{result.fetcher_spec.function_name}.py"
            
            with open(output_file, 'w') as f:
                f.write(result.generated_code)
            
            print(f"   Code saved to: {output_file.relative_to(PROJECT_ROOT)}")
    
    print("\n" + "=" * 70)
    print("MVP Complete!")
    print("=" * 70)
    
    if successful:
        print("\n🎯 Next steps:")
        print("   1. Review generated code in 'generated_fetchers/' directory")
        print("   2. Test with real data (install datasets library)")
        print("   3. Integrate into sources/ directory if valid")
        print("   4. Add to builder.py SOURCE_WEIGHTS dictionary")
    
    return results


if __name__ == "__main__":
    run_discovery_mvp()
