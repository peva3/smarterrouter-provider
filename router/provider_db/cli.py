"""
CLI for provider_db.

Usage:
    python -m router.provider_db.cli build
    python -m router.provider_db.cli stats
    python -m router.provider_db.cli health
    python -m router.provider_db.cli inspect <model_id>
    python -m router.provider_db.cli validate
"""

import argparse
import asyncio
import logging
import sys
import json
from pathlib import Path

from .builder import build_provider_db
from .database import ProviderDB
from .utils import MetricsCollector, compute_sha256


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Suppress noisy third-party libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('datasets').setLevel(logging.WARNING)
    logging.getLogger('huggingface_hub').setLevel(logging.WARNING)
    logging.getLogger('fsspec').setLevel(logging.WARNING)
    logging.getLogger('filelock').setLevel(logging.WARNING)


def get_default_db_path() -> Path:
    """Get default database path."""
    # Docker-compatible default: /app/data/provider.db
    # Also supports local development: ./data/provider.db
    data_dir_path = Path.cwd() / "data" / "provider.db"
    root_path = Path.cwd() / "provider.db"
    
    # Prefer data directory path (Docker default)
    return data_dir_path


async def cmd_build(args):
    """Build the provider database."""
    db_path = args.db_path or get_default_db_path()
    force = args.force
    
    print(f"Building provider.db at: {db_path}")
    if force:
        print("  Force mode: rebuilding all models")
    
    stats = await build_provider_db(db_path, force=force)
    
    print("\n=== Build Complete ===")
    print(f"Duration: {stats.get('duration', 0):.1f}s")
    print(f"Total models: {stats.get('total_models', 0)}")
    print(f"Total aliases: {stats.get('total_aliases', 0)}")
    print(f"\nSources succeeded: {stats.get('sources_succeeded', [])}")
    print(f"Sources failed: {stats.get('sources_failed', [])}")
    print(f"\nModels with reasoning: {stats.get('models_with_reasoning', 0)}")
    print(f"Models with coding: {stats.get('models_with_coding', 0)}")
    print(f"Models with general: {stats.get('models_with_general', 0)}")
    print(f"Models with ELO: {stats.get('models_with_elo', 0)}")
    
    return 0


def cmd_stats(args):
    """Show database statistics."""
    db_path = Path(args.db_path) if args.db_path else get_default_db_path()
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1
    
    db = ProviderDB(db_path)
    stats = db.get_stats()
    
    print(f"\n=== Provider DB Stats ===")
    print(f"Database: {db_path}")
    print(f"Total models: {stats['total_models']}")
    print(f"Total aliases: {stats['total_aliases']}")
    
    # Show metadata
    last_build = db.get_metadata('last_build')
    sources = db.get_metadata('sources_succeeded', [])
    print(f"\nLast build: {last_build}")
    print(f"Sources: {sources}")
    
    return 0


def cmd_health(args):
    """Check database health and integrity."""
    db_path = Path(args.db_path) if args.db_path else get_default_db_path()
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1
    
    db = ProviderDB(db_path)
    issues = []
    
    print(f"\n=== Health Check ===")
    print(f"Database: {db_path}")
    
    # Check file size
    size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"Size: {size_mb:.2f} MB")
    
    # Check table exists
    stats = None
    try:
        stats = db.get_stats()
        print(f"✓ Models table: {stats['total_models']} rows")
    except Exception as e:
        issues.append(f"Models table error: {e}")
        print(f"✗ Models table error: {e}")
    
    # Check aliases table
    try:
        alias_count = stats.get('total_aliases', 0) if stats else 0
        print(f"✓ Aliases table: {alias_count} rows")
    except Exception as e:
        issues.append(f"Aliases table error: {e}")
        print(f"✗ Aliases table error: {e}")
    
    # Check for invalid scores
    with db._get_connection() as conn:
        cursor = conn.cursor()
        
        # Check for NULL scores
        null_scores = cursor.execute("""
            SELECT COUNT(*) FROM model_benchmarks 
            WHERE reasoning_score IS NULL OR coding_score IS NULL OR general_score IS NULL
        """).fetchone()[0]
        
        if null_scores > 0:
            issues.append(f"Found {null_scores} rows with NULL scores")
            print(f"✗ NULL scores: {null_scores}")
        else:
            print(f"✓ No NULL scores")
        
        # Check for out-of-range scores
        out_of_range = cursor.execute("""
            SELECT COUNT(*) FROM model_benchmarks 
            WHERE reasoning_score < 0 OR reasoning_score > 100
            OR coding_score < 0 OR coding_score > 100
            OR general_score < 0 OR general_score > 100
        """).fetchone()[0]
        
        if out_of_range > 0:
            issues.append(f"Found {out_of_range} rows with out-of-range scores")
            print(f"✗ Out-of-range scores: {out_of_range}")
        else:
            print(f"✓ All scores in valid range (0-100)")
        
        # Check ELO range
        invalid_elo = cursor.execute("""
            SELECT COUNT(*) FROM model_benchmarks 
            WHERE elo_rating < 0 OR elo_rating > 2000
        """).fetchone()[0]
        
        if invalid_elo > 0:
            issues.append(f"Found {invalid_elo} rows with invalid ELO")
            print(f"✗ Invalid ELO: {invalid_elo}")
        else:
            print(f"✓ All ELO ratings valid")
    
    # Check metadata
    last_build = db.get_metadata('last_build')
    if last_build:
        print(f"✓ Last build: {last_build}")
    else:
        issues.append("No last_build metadata")
        print(f"⚠ No last build timestamp")
    
    # Summary
    print(f"\n=== Summary ===")
    if issues:
        print(f"Issues found: {len(issues)}")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    else:
        print("✓ Database is healthy!")
        return 0


def cmd_validate(args):
    """Validate database meets SmarterRouter requirements."""
    db_path = Path(args.db_path) if args.db_path else get_default_db_path()
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1
    
    db = ProviderDB(db_path)
    requirements = []
    checks_passed = 0
    
    print(f"\n=== SmarterRouter Validation ===")
    
    with db._get_connection() as conn:
        cursor = conn.cursor()
        
        # Check required columns
        cursor.execute("PRAGMA table_info(model_benchmarks)")
        columns = {row[1] for row in cursor.fetchall()}
        
        required_cols = {'model_id', 'reasoning_score', 'coding_score', 'general_score', 'elo_rating'}
        missing_cols = required_cols - columns
        
        if missing_cols:
            requirements.append(f"Missing columns: {missing_cols}")
            print(f"✗ Missing columns: {missing_cols}")
        else:
            print(f"✓ All required columns present")
            checks_passed += 1
        
        # Check model count
        model_count = cursor.execute("SELECT COUNT(*) FROM model_benchmarks").fetchone()[0]
        print(f"✓ Models: {model_count}")
        checks_passed += 1
        
        # Check score ranges
        invalid = cursor.execute("""
            SELECT COUNT(*) FROM model_benchmarks 
            WHERE (reasoning_score < 0 OR reasoning_score > 100 OR reasoning_score IS NULL)
            AND (coding_score < 0 OR coding_score > 100 OR coding_score IS NULL)
            AND (general_score < 0 OR general_score > 100 OR general_score IS NULL)
            AND elo_rating < 1000
        """).fetchone()[0]
        
        if invalid > 0:
            requirements.append(f"{invalid} models have no valid scores")
            print(f"⚠ {invalid} models have no valid scores (may use heuristics)")
        else:
            print(f"✓ All models have at least one valid score")
            checks_passed += 1
        
        # Check primary key
        cursor.execute("SELECT model_id FROM model_benchmarks GROUP BY model_id HAVING COUNT(*) > 1")
        dupes = cursor.fetchall()
        if dupes:
            requirements.append(f"Duplicate model IDs found: {dupes}")
            print(f"✗ Duplicate model IDs: {len(dupes)}")
        else:
            print(f"✓ No duplicate model IDs")
            checks_passed += 1
    
    # Final result
    print(f"\n=== Result ===")
    if requirements:
        print(f"Validation issues: {len(requirements)}")
        for req in requirements:
            print(f"  - {req}")
        return 1
    else:
        print(f"✓ All {checks_passed} checks passed - Database is SmarterRouter compatible!")
        return 0


def cmd_inspect(args):
    """Inspect a specific model."""
    db_path = Path(args.db_path) if args.db_path else get_default_db_path()
    model_id = args.model_id
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1
    
    db = ProviderDB(db_path)
    benchmark = db.get_benchmark(model_id)
    
    if not benchmark:
        print(f"Model not found: {model_id}")
        return 1
    
    print(f"\n=== Model: {model_id} ===")
    print(f"Reasoning score: {benchmark.get('reasoning_score', 'N/A')}")
    print(f"Coding score: {benchmark.get('coding_score', 'N/A')}")
    print(f"General score: {benchmark.get('general_score', 'N/A')}")
    print(f"ELO rating: {benchmark.get('elo_rating', 'N/A')}")
    
    # Check aliases
    canonical = db.get_canonical_id(model_id)
    if canonical:
        print(f"Canonical ID: {canonical}")
    
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Provider DB CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Build provider database')
    build_parser.add_argument(
        '-o', '--db-path',
        type=Path,
        help='Path to database file'
    )
    build_parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Force rebuild all models (ignore existing)'
    )
    build_parser.set_defaults(func=cmd_build)
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')
    stats_parser.add_argument(
        '--db-path',
        type=Path,
        help='Path to database file'
    )
    stats_parser.set_defaults(func=cmd_stats)
    
    # Health check command
    health_parser = subparsers.add_parser('health', help='Check database health')
    health_parser.add_argument(
        '--db-path',
        type=Path,
        help='Path to database file'
    )
    health_parser.set_defaults(func=cmd_health)
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate for SmarterRouter')
    validate_parser.add_argument(
        '--db-path',
        type=Path,
        help='Path to database file'
    )
    validate_parser.set_defaults(func=cmd_validate)
    
    # Inspect command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect a model')
    inspect_parser.add_argument(
        '--db-path',
        type=Path,
        help='Path to database file'
    )
    inspect_parser.add_argument(
        'model_id',
        help='Model ID to inspect'
    )
    inspect_parser.set_defaults(func=cmd_inspect)
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'build':
            return asyncio.run(cmd_build(args))
        else:
            return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except Exception as e:
        logging.exception(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
