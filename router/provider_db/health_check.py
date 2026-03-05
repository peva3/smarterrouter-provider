#!/usr/bin/env python3
"""
Provider DB Health Check Script

Run this script to validate the provider.db database health.
Can be used in CI/CD pipelines or scheduled cron jobs.

Usage:
    python -m router.provider_db.health_check
    python -m router.provider_db.health_check --verbose
    python -m router.provider_db.health_check --db-path /custom/path/provider.db
"""

import argparse
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .database import ProviderDB
from .models import ModelBenchmark


def format_timestamp(iso_string: str) -> str:
    """Format ISO timestamp to human-readable."""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M UTC')
    except:
        return iso_string


def check_database_health(db: ProviderDB) -> dict[str, Any]:
    """Run database health checks."""
    issues = []
    warnings = []
    
    with db._get_connection() as conn:
        cursor = conn.cursor()
        
        # Basic counts
        total_models = cursor.execute("SELECT COUNT(*) FROM model_benchmarks").fetchone()[0]
        total_aliases = cursor.execute("SELECT COUNT(*) FROM aliases").fetchone()[0]
        
        # Score coverage
        reasoning = cursor.execute("SELECT COUNT(*) FROM model_benchmarks WHERE reasoning_score > 0").fetchone()[0]
        coding = cursor.execute("SELECT COUNT(*) FROM model_benchmarks WHERE coding_score > 0").fetchone()[0]
        general = cursor.execute("SELECT COUNT(*) FROM model_benchmarks WHERE general_score > 0").fetchone()[0]
        elo = cursor.execute("SELECT COUNT(*) FROM model_benchmarks WHERE elo_rating > 0").fetchone()[0]
        
        # Data quality checks
        null_scores = cursor.execute("""
            SELECT COUNT(*) FROM model_benchmarks 
            WHERE reasoning_score IS NULL OR coding_score IS NULL 
            OR general_score IS NULL OR elo_rating IS NULL
        """).fetchone()[0]
        
        out_of_range = cursor.execute("""
            SELECT COUNT(*) FROM model_benchmarks 
            WHERE reasoning_score < 0 OR reasoning_score > 100
            OR coding_score < 0 OR coding_score > 100
            OR general_score < 0 OR general_score > 100
        """).fetchone()[0]
        
        bad_elo = cursor.execute("""
            SELECT COUNT(*) FROM model_benchmarks 
            WHERE elo_rating < 0 OR elo_rating > 2000
        """).fetchone()[0]
        
        # Check for models with no scores at all
        no_scores = cursor.execute("""
            SELECT COUNT(*) FROM model_benchmarks 
            WHERE reasoning_score = 0 AND coding_score = 0 
            AND general_score = 0 AND elo_rating <= 1000
        """).fetchone()[0]
        
        # Score ranges
        r_range = cursor.execute("""
            SELECT MIN(reasoning_score), MAX(reasoning_score), AVG(reasoning_score) 
            FROM model_benchmarks WHERE reasoning_score > 0
        """).fetchone()
        
        c_range = cursor.execute("""
            SELECT MIN(coding_score), MAX(coding_score), AVG(coding_score) 
            FROM model_benchmarks WHERE coding_score > 0
        """).fetchone()
        
        g_range = cursor.execute("""
            SELECT MIN(general_score), MAX(general_score), AVG(general_score) 
            FROM model_benchmarks WHERE general_score > 0
        """).fetchone()
        
        e_range = cursor.execute("""
            SELECT MIN(elo_rating), MAX(elo_rating), AVG(elo_rating) 
            FROM model_benchmarks WHERE elo_rating > 0
        """).fetchone()
        
        # Add issues
        if null_scores > 0:
            issues.append(f"Found {null_scores} rows with NULL scores")
        
        if out_of_range > 0:
            issues.append(f"Found {out_of_range} rows with out-of-range scores")
        
        if bad_elo > 0:
            issues.append(f"Found {bad_elo} rows with invalid ELO")
        
        # Add warnings
        if no_scores > 10:
            warnings.append(f"{no_scores} models have no benchmark data (using heuristics)")
        
        if reasoning / total_models < 0.5:
            warnings.append(f"Reasoning coverage low: {100*reasoning/total_models:.1f}%")
        
        if coding / total_models < 0.5:
            warnings.append(f"Coding coverage low: {100*coding/total_models:.1f}%")
        
        if general / total_models < 0.5:
            warnings.append(f"General coverage low: {100*general/total_models:.1f}%")
        
        # Top models
        top_reasoning = cursor.execute("""
            SELECT model_id, reasoning_score FROM model_benchmarks 
            WHERE reasoning_score > 0 ORDER BY reasoning_score DESC LIMIT 5
        """).fetchall()
        
        top_coding = cursor.execute("""
            SELECT model_id, coding_score FROM model_benchmarks 
            WHERE coding_score > 0 ORDER BY coding_score DESC LIMIT 5
        """).fetchall()
        
        top_general = cursor.execute("""
            SELECT model_id, general_score FROM model_benchmarks 
            WHERE general_score > 0 ORDER BY general_score DESC LIMIT 5
        """).fetchall()
        
        top_elo = cursor.execute("""
            SELECT model_id, elo_rating FROM model_benchmarks 
            ORDER BY elo_rating DESC LIMIT 5
        """).fetchall()
    
    return {
        'total_models': total_models,
        'total_aliases': total_aliases,
        'coverage': {
            'reasoning': {'count': reasoning, 'pct': 100*reasoning/total_models},
            'coding': {'count': coding, 'pct': 100*coding/total_models},
            'general': {'count': general, 'pct': 100*general/total_models},
            'elo': {'count': elo, 'pct': 100*elo/total_models},
        },
        'score_ranges': {
            'reasoning': {'min': r_range[0], 'max': r_range[1], 'avg': r_range[2]},
            'coding': {'min': c_range[0], 'max': c_range[1], 'avg': c_range[2]},
            'general': {'min': g_range[0], 'max': g_range[1], 'avg': g_range[2]},
            'elo': {'min': e_range[0], 'max': e_range[1], 'avg': e_range[2]},
        },
        'data_quality': {
            'null_scores': null_scores,
            'out_of_range': out_of_range,
            'bad_elo': bad_elo,
            'no_scores': no_scores,
        },
        'issues': issues,
        'warnings': warnings,
        'top_models': {
            'reasoning': [{'model': m[0], 'score': m[1]} for m in top_reasoning],
            'coding': [{'model': m[0], 'score': m[1]} for m in top_coding],
            'general': [{'model': m[0], 'score': m[1]} for m in top_general],
            'elo': [{'model': m[0], 'score': m[1]} for m in top_elo],
        }
    }


def check_sources(db: ProviderDB) -> dict[str, Any]:
    """Check source metadata."""
    last_build = db.get_metadata('last_build')
    sources_succeeded = db.get_metadata('sources_succeeded', [])
    sources_failed = db.get_metadata('sources_failed', [])
    
    return {
        'last_build': last_build,
        'sources_succeeded': sources_succeeded,
        'sources_failed': sources_failed,
        'total_sources': len(sources_succeeded) + len(sources_failed),
    }


def print_report(health: dict, sources: dict, verbose: bool = False) -> int:
    """Print health check report."""
    print("=" * 60)
    print("Provider DB Health Check")
    print("=" * 60)
    
    # Database stats
    print(f"\n📊 Database Statistics:")
    print(f"   Total models: {health['total_models']:,}")
    print(f"   Total aliases: {health['total_aliases']:,}")
    
    # Coverage
    print(f"\n📈 Score Coverage:")
    cov = health['coverage']
    print(f"   Reasoning: {cov['reasoning']['count']:,} ({cov['reasoning']['pct']:.1f}%)")
    print(f"   Coding:    {cov['coding']['count']:,} ({cov['coding']['pct']:.1f}%)")
    print(f"   General:   {cov['general']['count']:,} ({cov['general']['pct']:.1f}%)")
    print(f"   ELO:       {cov['elo']['count']:,} ({cov['elo']['pct']:.1f}%)")
    
    # Score ranges
    print(f"\n📏 Score Ranges:")
    ranges = health['score_ranges']
    print(f"   Reasoning: {ranges['reasoning']['min']:.1f} - {ranges['reasoning']['max']:.1f} (avg: {ranges['reasoning']['avg']:.1f})")
    print(f"   Coding:    {ranges['coding']['min']:.1f} - {ranges['coding']['max']:.1f} (avg: {ranges['coding']['avg']:.1f})")
    print(f"   General:   {ranges['general']['min']:.1f} - {ranges['general']['max']:.1f} (avg: {ranges['general']['avg']:.1f})")
    print(f"   ELO:       {ranges['elo']['min']} - {ranges['elo']['max']} (avg: {ranges['elo']['avg']:.0f})")
    
    # Sources
    print(f"\n🔗 Sources:")
    print(f"   Last build: {format_timestamp(sources['last_build'])}")
    print(f"   Sources succeeded: {len(sources['sources_succeeded'])}")
    if verbose and sources['sources_failed']:
        print(f"   Sources failed: {sources['sources_failed']}")
    
    # Data quality
    print(f"\n✅ Data Quality:")
    dq = health['data_quality']
    print(f"   NULL scores: {dq['null_scores']}")
    print(f"   Out of range: {dq['out_of_range']}")
    print(f"   Bad ELO: {dq['bad_elo']}")
    print(f"   No scores: {dq['no_scores']}")
    
    # Top models
    if verbose:
        print(f"\n🏆 Top Models:")
        for category, models in health['top_models'].items():
            print(f"   {category.capitalize()}:")
            for m in models[:3]:
                print(f"      {m['model'][:50]}: {m['score']:.1f}")
    
    # Issues and warnings
    print(f"\n" + "=" * 60)
    if health['issues']:
        print(f"❌ Issues ({len(health['issues'])}):")
        for issue in health['issues']:
            print(f"   - {issue}")
    
    if health['warnings']:
        print(f"⚠️  Warnings ({len(health['warnings'])}):")
        for warning in health['warnings']:
            print(f"   - {warning}")
    
    if not health['issues'] and not health['warnings']:
        print(f"✅ Database is healthy!")
    
    print("=" * 60)
    
    # Return exit code
    return 1 if health['issues'] else 0


def main():
    parser = argparse.ArgumentParser(description="Provider DB Health Check")
    parser.add_argument("--db-path", type=Path, help="Path to provider.db")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--exit-code", action="store_true", help="Exit with non-zero if issues found")
    args = parser.parse_args()
    
    # Get database path
    if args.db_path:
        db_path = args.db_path
    else:
        # Default locations
        db_path = Path("data/provider.db")
        if not db_path.exists():
            db_path = Path("provider.db")
        if not db_path.exists():
            db_path = Path("/app/data/provider.db")
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1
    
    # Run checks
    db = ProviderDB(db_path)
    health = check_database_health(db)
    sources = check_sources(db)
    
    # Output
    if args.json:
        output = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'db_path': str(db_path),
            'health': health,
            'sources': sources,
        }
        print(json.dumps(output, indent=2))
    else:
        exit_code = print_report(health, sources, verbose=args.verbose)
        if args.exit_code:
            return exit_code
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
