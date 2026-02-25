"""
HTML Report Generator for Provider DB

Generates a beautiful, interactive HTML page showing all models and their scores.
Run directly: python -m router.provider_db.html_export
Or integrate into build process.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ModelData:
    """Model data from database."""
    model_id: str
    reasoning_score: float
    coding_score: float
    general_score: float
    elo_rating: int
    aliases: List[str]


@dataclass 
class ReportStats:
    """Summary statistics for the report."""
    total_models: int
    models_with_reasoning: int
    models_with_coding: int
    models_with_general: int
    models_with_elo: int
    avg_reasoning: float
    avg_coding: float
    avg_general: float
    avg_elo: float
    top_reasoning: List[tuple]
    top_coding: List[tuple]
    top_general: List[tuple]
    top_elo: List[tuple]


def get_db_path() -> Path:
    """Get the database path."""
    return Path(__file__).parent.parent.parent / "provider.db"


def get_output_path() -> Path:
    """Get the output HTML path."""
    return Path(__file__).parent.parent.parent / "models.html"


def load_models(db_path: Path) -> List[ModelData]:
    """Load all models from the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all models with aliases
    cursor.execute("""
        SELECT 
            m.model_id,
            m.reasoning_score,
            m.coding_score,
            m.general_score,
            m.elo_rating,
            GROUP_CONCAT(a.alias, '|||') as aliases
        FROM model_benchmarks m
        LEFT JOIN aliases a ON m.model_id = a.canonical_id
        GROUP BY m.model_id
        ORDER BY m.elo_rating DESC
    """)
    
    models = []
    for row in cursor.fetchall():
        aliases = []
        if row[5]:
            aliases = row[5].split('|||')
        
        models.append(ModelData(
            model_id=row[0],
            reasoning_score=row[1] or 0.0,
            coding_score=row[2] or 0.0,
            general_score=row[3] or 0.0,
            elo_rating=row[4] or 0,
            aliases=aliases
        ))
    
    conn.close()
    return models


def load_metadata(db_path: Path) -> Dict:
    """Load metadata from database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT key, value FROM metadata")
    metadata = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    return metadata


def calculate_stats(models: List[ModelData]) -> ReportStats:
    """Calculate summary statistics."""
    with_scores = [m for m in models if m.reasoning_score > 0 or m.coding_score > 0 or m.general_score > 0]
    
    reasoning_scores = [m.reasoning_score for m in with_scores if m.reasoning_score > 0]
    coding_scores = [m.coding_score for m in with_scores if m.coding_score > 0]
    general_scores = [m.general_score for m in with_scores if m.general_score > 0]
    elo_scores = [m.elo_rating for m in with_scores if m.elo_rating > 0]
    
    # Top models per category
    top_reasoning = sorted(
        [(m.model_id, m.reasoning_score) for m in models if m.reasoning_score > 0],
        key=lambda x: -x[1]
    )[:10]
    
    top_coding = sorted(
        [(m.model_id, m.coding_score) for m in models if m.coding_score > 0],
        key=lambda x: -x[1]
    )[:10]
    
    top_general = sorted(
        [(m.model_id, m.general_score) for m in models if m.general_score > 0],
        key=lambda x: -x[1]
    )[:10]
    
    top_elo = sorted(
        [(m.model_id, m.elo_rating) for m in models if m.elo_rating > 0],
        key=lambda x: -x[1]
    )[:10]
    
    return ReportStats(
        total_models=len(models),
        models_with_reasoning=len(reasoning_scores),
        models_with_coding=len(coding_scores),
        models_with_general=len(general_scores),
        models_with_elo=len(elo_scores),
        avg_reasoning=sum(reasoning_scores)/len(reasoning_scores) if reasoning_scores else 0,
        avg_coding=sum(coding_scores)/len(coding_scores) if coding_scores else 0,
        avg_general=sum(general_scores)/len(general_scores) if general_scores else 0,
        avg_elo=sum(elo_scores)/len(elo_scores) if elo_scores else 0,
        top_reasoning=top_reasoning,
        top_coding=top_coding,
        top_general=top_general,
        top_elo=top_elo,
    )


def score_color(score: float, max_score: float = 100) -> str:
    """Get color for score based on value."""
    ratio = score / max_score
    if ratio >= 0.8:
        return "#22c55e"  # Green
    elif ratio >= 0.6:
        return "#84cc16"  # Lime
    elif ratio >= 0.4:
        return "#eab308"  # Yellow
    elif ratio >= 0.2:
        return "#f97316"  # Orange
    else:
        return "#ef4444"  # Red


def generate_html(models: List[ModelData], stats: ReportStats, metadata: Dict) -> str:
    """Generate the complete HTML report."""
    
    # Convert metadata
    last_build = metadata.get('last_build', 'Unknown')
    try:
        dt = datetime.fromisoformat(last_build.replace('Z', '+00:00'))
        last_build = dt.strftime('%B %d, %Y at %H:%M UTC')
    except:
        pass
    
    sources_succeeded = []
    try:
        sources_succeeded = json.loads(metadata.get('sources_succeeded', '[]'))
    except:
        sources_succeeded = metadata.get('sources_succeeded', '').strip('[]').split(',')
    
    # Build models JSON for JavaScript
    models_json = []
    for m in models:
        models_json.append({
            'id': m.model_id,
            'reasoning': m.reasoning_score,
            'coding': m.coding_score,
            'general': m.general_score,
            'elo': m.elo_rating,
            'aliases': m.aliases
        })
    
    models_json_str = json.dumps(models_json, indent=2)
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Provider DB - Model Leaderboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        :root {{
            --bg-primary: #0a0a0b;
            --bg-secondary: #111113;
            --bg-tertiary: #18181b;
            --bg-card: #1c1c1f;
            --border: #27272a;
            --border-light: #3f3f46;
            --text-primary: #fafafa;
            --text-secondary: #a1a1aa;
            --text-muted: #71717a;
            --accent: #6366f1;
            --accent-hover: #818cf8;
            --accent-muted: #4f46e5;
            --success: #22c55e;
            --warning: #eab308;
            --danger: #ef4444;
            --score-high: #22c55e;
            --score-mid: #84cc16;
            --score-low: #eab308;
            --score-vlow: #f97316;
        }}
        
        * {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        
        body {{
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        /* Header */
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
        }}
        
        .logo-section {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        
        .logo {{
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, var(--accent) 0%, var(--accent-muted) 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 1.25rem;
        }}
        
        h1 {{
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.025em;
        }}
        
        .subtitle {{
            color: var(--text-secondary);
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }}
        
        .meta-badge {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-size: 0.875rem;
            color: var(--text-secondary);
        }}
        
        .meta-badge svg {{
            width: 16px;
            height: 16px;
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            transition: all 0.2s ease;
        }}
        
        .stat-card:hover {{
            border-color: var(--border-light);
            transform: translateY(-2px);
        }}
        
        .stat-label {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: -0.025em;
        }}
        
        .stat-value.accent {{ color: var(--accent); }}
        .stat-value.success {{ color: var(--success); }}
        
        .stat-detail {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }}
        
        /* Top Performers */
        .top-section {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .top-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
        }}
        
        .top-card h3 {{
            font-size: 0.875rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .top-card h3::before {{
            content: '';
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent);
        }}
        
        .top-list {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}
        
        .top-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem;
            background: var(--bg-tertiary);
            border-radius: 6px;
            font-size: 0.8rem;
        }}
        
        .top-item .name {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
            color: var(--text-secondary);
            max-width: 140px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .top-item .score {{
            font-weight: 600;
            padding: 0.125rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
        }}
        
        /* Search & Filters */
        .controls {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }}
        
        .search-box {{
            flex: 1;
            min-width: 280px;
            position: relative;
        }}
        
        .search-box input {{
            width: 100%;
            padding: 0.75rem 1rem 0.75rem 2.75rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 0.875rem;
            outline: none;
            transition: all 0.2s ease;
        }}
        
        .search-box input:focus {{
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
        }}
        
        .search-box input::placeholder {{
            color: var(--text-muted);
        }}
        
        .search-box svg {{
            position: absolute;
            left: 0.875rem;
            top: 50%;
            transform: translateY(-50%);
            width: 18px;
            height: 18px;
            color: var(--text-muted);
        }}
        
        .filter-group {{
            display: flex;
            gap: 0.5rem;
        }}
        
        .filter-btn {{
            padding: 0.75rem 1rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-secondary);
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .filter-btn:hover {{
            border-color: var(--border-light);
            color: var(--text-primary);
        }}
        
        .filter-btn.active {{
            background: var(--accent);
            border-color: var(--accent);
            color: white;
        }}
        
        /* Table */
        .table-container {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        thead {{
            background: var(--bg-tertiary);
        }}
        
        th {{
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            user-select: none;
            transition: color 0.2s ease;
        }}
        
        th:hover {{
            color: var(--text-primary);
        }}
        
        th svg {{
            width: 12px;
            height: 12px;
            margin-left: 0.25rem;
            opacity: 0.5;
            vertical-align: middle;
        }}
        
        td {{
            padding: 1rem;
            border-bottom: 1px solid var(--border);
            font-size: 0.875rem;
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        tr:hover td {{
            background: var(--bg-tertiary);
        }}
        
        .model-name {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: var(--text-primary);
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            display: block;
        }}
        
        .model-name:hover {{
            color: var(--accent);
        }}
        
        .score-cell {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .score-bar {{
            width: 60px;
            height: 6px;
            background: var(--bg-primary);
            border-radius: 3px;
            overflow: hidden;
        }}
        
        .score-bar-fill {{
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s ease;
        }}
        
        .elo-cell {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 500;
        }}
        
        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 500;
        }}
        
        .badge.reasoning {{
            background: rgba(34, 197, 94, 0.15);
            color: #22c55e;
        }}
        
        .badge.coding {{
            background: rgba(99, 102, 241, 0.15);
            color: #6366f1;
        }}
        
        .badge.general {{
            background: rgba(234, 179, 8, 0.15);
            color: #eab308;
        }}
        
        .badge.elo {{
            background: rgba(236, 72, 153, 0.15);
            color: #ec4899;
        }}
        
        /* Footer */
        footer {{
            margin-top: 2rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: var(--text-muted);
            font-size: 0.8rem;
        }}
        
        .sources-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            max-width: 70%;
        }}
        
        .source-tag {{
            padding: 0.25rem 0.5rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 4px;
            font-size: 0.7rem;
            color: var(--text-secondary);
        }}
        
        /* Responsive */
        @media (max-width: 1200px) {{
            .stats-grid, .top-section {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            
            .stats-grid, .top-section {{
                grid-template-columns: 1fr;
            }}
            
            header {{
                flex-direction: column;
                gap: 1rem;
                align-items: flex-start;
            }}
            
            .controls {{
                flex-direction: column;
            }}
            
            .search-box {{ min-width: 100%; }}
            
            .table-container {{
                overflow-x: auto;
            }}
            
            table {{ min-width: 800px; }}
            
            footer {{
                flex-direction: column;
                gap: 1rem;
            }}
            
            .sources-list {{ max-width: 100%; }}
        }}
        
        /* Animations */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .stat-card, .top-card {{
            animation: fadeIn 0.4s ease forwards;
        }}
        
        .stat-card:nth-child(1) {{ animation-delay: 0.05s; }}
        .stat-card:nth-child(2) {{ animation-delay: 0.1s; }}
        .stat-card:nth-child(3) {{ animation-delay: 0.15s; }}
        .stat-card:nth-child(4) {{ animation-delay: 0.2s; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-section">
                <div class="logo">P</div>
                <div>
                    <h1>Provider DB</h1>
                    <div class="subtitle">Model Performance Leaderboard & Benchmark Scores</div>
                </div>
            </div>
            <div class="meta-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12,6 12,12 16,14"/>
                </svg>
                <span>Last updated: {last_build}</span>
            </div>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Models</div>
                <div class="stat-value accent">{stats.total_models}</div>
                <div class="stat-detail">{stats.models_with_elo} with ELO ratings</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Reasoning</div>
                <div class="stat-value success">{stats.models_with_reasoning}</div>
                <div class="stat-detail">Avg: {{stats.avg_reasoning:.1f}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Coding</div>
                <div class="stat-value">{stats.models_with_coding}</div>
                <div class="stat-detail">Avg: {{stats.avg_coding:.1f}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">General</div>
                <div class="stat-value">{stats.models_with_general}</div>
                <div class="stat-detail">Avg: {{stats.avg_general:.1f}}</div>
            </div>
        </div>
        
        <div class="top-section">
            <div class="top-card">
                <h3>Top Reasoning</h3>
                <div class="top-list">
                    {''.join([f'<div class="top-item"><span class="name">{name}</span><span class="score" style="background:{score_color(score,100)}22;color:{score_color(score,100)}">{score:.1f}</span></div>' for name, score in stats.top_reasoning[:5]])}
                </div>
            </div>
            <div class="top-card">
                <h3>Top Coding</h3>
                <div class="top-list">
                    {''.join([f'<div class="top-item"><span class="name">{name}</span><span class="score" style="background:{score_color(score,100)}22;color:{score_color(score,100)}">{score:.1f}</span></div>' for name, score in stats.top_coding[:5]])}
                </div>
            </div>
            <div class="top-card">
                <h3>Top General</h3>
                <div class="top-list">
                    {''.join([f'<div class="top-item"><span class="name">{name}</span><span class="score" style="background:{score_color(score,100)}22;color:{score_color(score,100)}">{score:.1f}</span></div>' for name, score in stats.top_general[:5]])}
                </div>
            </div>
            <div class="top-card">
                <h3>Top ELO</h3>
                <div class="top-list">
                    {''.join([f'<div class="top-item"><span class="name">{name[:25]}{"..." if len(name) > 25 else ""}</span><span class="score" style="background:#ec489922;color:#ec4899">{score}</span></div>' for name, score in stats.top_elo[:5]])}
                </div>
            </div>
        </div>
        
        <div class="controls">
            <div class="search-box">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="m21 21-4.35-4.35"/>
                </svg>
                <input type="text" id="searchInput" placeholder="Search models by name...">
            </div>
            <div class="filter-group">
                <button class="filter-btn active" data-filter="all">All</button>
                <button class="filter-btn" data-filter="reasoning">Has Reasoning</button>
                <button class="filter-btn" data-filter="coding">Has Coding</button>
                <button class="filter-btn" data-filter="general">Has General</button>
            </div>
        </div>
        
        <div class="controls" style="margin-bottom: 0.5rem; justify-content: space-between;">
            <span id="resultCount" style="color: var(--text-secondary); font-size: 0.875rem;"></span>
            <button id="loadMore" class="filter-btn" style="display: none;">Load more</button>
        </div>
        
        <div class="table-container" id="tableContainer" style="overflow-y: auto; max-height: 600px;">
            <table>
                <thead>
                    <tr>
                        <th data-sort="id">Model ID <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m7 15 5 5 5-5m7-5-5 5-5"/></svg></th>
                        <th data-sort="reasoning">Reasoning <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m7 15 5 5 5-5m7-5-5 5-5"/></svg></th>
                        <th data-sort="coding">Coding <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m7 15 5 5 5-5m7-5-5 5-5"/></svg></th>
                        <th data-sort="general">General <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m7 15 5 5 5-5m7-5-5 5-5"/></svg></th>
                        <th data-sort="elo">ELO <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m7 15 5 5 5-5m7-5-5 5-5"/></svg></th>
                    </tr>
                </thead>
                <tbody id="tableBody">
                    <!-- Populated by JavaScript -->
                </tbody>
            </table>
        </div>
        
        <footer>
            <div class="sources-list">
                <span style="color: var(--text-muted); margin-right: 0.5rem;">Sources:</span>
                {''.join([f'<span class="source-tag">{s.strip()}</span>' for s in sources_succeeded[:20]])}
            </div>
            <div>
                Generated by Provider DB Builder
            </div>
        </footer>
    </div>
    
    <script>
        const modelsData = {models_json_str};
        let currentSort = {{ column: 'elo', ascending: false }};
        let currentFilter = 'all';
        let searchQuery = '';
        
        // Pagination config
        const PAGE_SIZE = 50;
        let displayedCount = PAGE_SIZE;
        let filteredData = [];
        
        // Debounce utility
        function debounce(fn, delay) {{
            let timeout;
            return (...args) => {{
                clearTimeout(timeout);
                timeout = setTimeout(() => fn(...args), delay);
            }};
        }}
        
        function scoreColor(score, maxScore = 100) {{
            const ratio = score / maxScore;
            if (ratio >= 0.8) return '#22c55e';
            if (ratio >= 0.6) return '#84cc16';
            if (ratio >= 0.4) return '#eab308';
            if (ratio >= 0.2) return '#f97316';
            return '#ef4444';
        }}
        
        function filterAndSort() {{
            filtered = modelsData.filter(m => {{
                if (searchQuery && !m.id.toLowerCase().includes(searchQuery.toLowerCase())) {{
                    return false;
                }}
                if (currentFilter === 'reasoning' && m.reasoning === 0) return false;
                if (currentFilter === 'coding' && m.coding === 0) return false;
                if (currentFilter === 'general' && m.general === 0) return false;
                return true;
            }});
            
            filtered.sort((a, b) => {{
                let aVal = a[currentSort.column];
                let bVal = b[currentSort.column];
                if (currentSort.column === 'id') {{
                    aVal = aVal.toLowerCase();
                    bVal = bVal.toLowerCase();
                }}
                if (aVal < bVal) return currentSort.ascending ? -1 : 1;
                if (aVal > bVal) return currentSort.ascending ? 1 : -1;
                return 0;
            }});
            
            filteredData = filtered;
            displayedCount = PAGE_SIZE;
            renderTable();
            updateCounts();
            updateLoadMore();
        }}
        
        function updateCounts() {{
            document.getElementById('resultCount').textContent = filteredData.length + ' models';
        }}
        
        function updateLoadMore() {{
            const loadMore = document.getElementById('loadMore');
            if (displayedCount >= filteredData.length) {{
                loadMore.style.display = 'none';
            }} else {{
                loadMore.style.display = 'block';
                loadMore.textContent = 'Load more (' + (filteredData.length - displayedCount) + ' remaining)';
            }}
        }}
        
        function renderTable() {{
            const tbody = document.getElementById('tableBody');
            const toRender = filteredData.slice(0, displayedCount);
            
            tbody.innerHTML = toRender.map(m => `
                <tr>
                    <td>
                        <span class="model-name" title="${{m.id}}">${{m.id}}</span>
                    </td>
                    <td>
                        ${{m.reasoning > 0 ? `
                            <div class="score-cell">
                                <span>${{m.reasoning.toFixed(1)}}</span>
                                <div class="score-bar">
                                    <div class="score-bar-fill" style="width:${{m.reasoning}}%;background:${{scoreColor(m.reasoning)}}"></div>
                                </div>
                            </div>
                        ` : '<span style="color:var(--text-muted)">—</span>'}}
                    </td>
                    <td>
                        ${{m.coding > 0 ? `
                            <div class="score-cell">
                                <span>${{m.coding.toFixed(1)}}</span>
                                <div class="score-bar">
                                    <div class="score-bar-fill" style="width:${{m.coding}}%;background:${{scoreColor(m.coding)}}"></div>
                                </div>
                            </div>
                        ` : '<span style="color:var(--text-muted)">—</span>'}}
                    </td>
                    <td>
                        ${{m.general > 0 ? `
                            <div class="score-cell">
                                <span>${{m.general.toFixed(1)}}</span>
                                <div class="score-bar">
                                    <div class="score-bar-fill" style="width:${{m.general}}%;background:${{scoreColor(m.general)}}"></div>
                                </div>
                            </div>
                        ` : '<span style="color:var(--text-muted)">—</span>'}}
                    </td>
                    <td>
                        ${{m.elo > 0 ? `<span class="elo-cell" style="color:#ec4899">${{m.elo}}</span>` : '<span style="color:var(--text-muted)">—</span>'}}
                    </td>
                </tr>
            `).join('');
        }}
        
        function loadMore() {{
            displayedCount += PAGE_SIZE;
            renderTable();
            updateLoadMore();
        }}
        
        const debouncedFilter = debounce(filterAndSort, 150);
        
        // Infinite scroll
        let scrollTimeout;
        document.getElementById('tableContainer').addEventListener('scroll', () => {{
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {{
                const el = document.getElementById('tableContainer');
                if (el.scrollTop + el.clientHeight >= el.scrollHeight - 100) {{
                    loadMore();
                }}
            }}, 100);
        }});
        
        // Search - debounced
        document.getElementById('searchInput').addEventListener('input', (e) => {{
            searchQuery = e.target.value;
            debouncedFilter();
        }});
        
        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentFilter = btn.dataset.filter;
                filterAndSort();
            }});
        }});
        
        // Sort headers
        document.querySelectorAll('th[data-sort]').forEach(th => {{
            th.addEventListener('click', () => {{
                const column = th.dataset.sort;
                if (currentSort.column === column) {{
                    currentSort.ascending = !currentSort.ascending;
                }} else {{
                    currentSort.column = column;
                    currentSort.ascending = column === 'id';
                }}
                document.getElementById('tableContainer').scrollTop = 0;
                filterAndSort();
            }});
        }});
        
        // Load more button
        document.getElementById('loadMore').addEventListener('click', loadMore);
        
        // Initial render
        filterAndSort();
    </script>
</body>
</html>'''
    
    return html


def generate_report(db_path: Path = None, output_path: Path = None) -> Path:
    """Generate the HTML report."""
    if db_path is None:
        db_path = get_db_path()
    if output_path is None:
        output_path = get_output_path()
    
    print(f"Loading models from {db_path}...")
    models = load_models(db_path)
    metadata = load_metadata(db_path)
    stats = calculate_stats(models)
    
    print(f"Generating HTML report for {len(models)} models...")
    html = generate_html(models, stats, metadata)
    
    output_path.write_text(html)
    print(f"Report saved to {output_path}")
    
    return output_path


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate HTML report from provider.db")
    parser.add_argument("--db", type=Path, help="Path to provider.db")
    parser.add_argument("--output", type=Path, help="Output path for HTML file")
    args = parser.parse_args()
    
    generate_report(args.db, args.output)


if __name__ == "__main__":
    main()
