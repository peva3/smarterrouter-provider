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
    from .health_check import check_database_health, check_sources, print_report
    
    db_path = Path(args.db_path) if args.db_path else get_default_db_path()
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1
    
    db = ProviderDB(db_path)
    health = check_database_health(db)
    sources = check_sources(db)
    
    return print_report(health, sources, verbose=args.verbose)


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


def cmd_discover(args):
    """Auto-discover new models and update benchmarks."""
    from .sources.auto_discover import generate_autodiscover_score, is_likely_new_version
    from .sources.openrouter import OpenRouterFetcher
    
    db_path = Path(args.db_path) if args.db_path else get_default_db_path()
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1
    
    db = ProviderDB(db_path)
    
    print("\n=== Auto-Discover New Models ===\n")
    
    # Get existing models from database
    existing = set(db.get_all_model_ids())
    print(f"Existing models in database: {len(existing)}")
    
    # Fetch latest from OpenRouter
    print("Fetching latest from OpenRouter...")
    or_models = asyncio.run(OpenRouterFetcher().fetch())
    new_models = set(or_models) - existing
    print(f"New models on OpenRouter: {len(new_models)}")
    
    # Find new versions
    new_versions = [m for m in new_models if is_likely_new_version(m)]
    print(f"New version models detected: {len(new_versions)}")
    
    if not new_versions:
        print("\nNo new version models found.")
        return 0
    
    print("\nNew models found:")
    for model in sorted(new_versions)[:20]:
        est = generate_autodiscover_score(model, existing)
        if est:
            print(f"  {model}")
            print(f"    -> R:{est['reasoning']:.1f} C:{est['coding']:.1f} G:{est['general']:.1f} ELO:{est['elo']}")
        else:
            print(f"  {model} (no estimate)")
    
    if args.dry_run:
        print("\n[DRY RUN] No changes made.")
        return 0
    
    print("\nTo add these models, run: python -m router.provider_db build")
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
    health_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output with top models'
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
    
    # Auto-discover command - find and update new models
    discover_parser = subparsers.add_parser('discover', help='Auto-discover new models and update benchmarks')
    discover_parser.add_argument(
        '--db-path',
        type=Path,
        help='Path to database file'
    )
    discover_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )
    discover_parser.set_defaults(func=cmd_discover)
    
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
