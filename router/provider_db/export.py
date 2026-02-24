"""
Export utility to merge provider.db data into SmarterRouter's router.db.
Handles the schema mismatch by mapping model_id -> ollama_name.
"""

import sqlite3
import argparse
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def export_to_router_db(provider_db_path: Path, router_db_path: Path, dry_run: bool = False):
    """
    Export benchmark data from provider.db to router.db.
    
    Args:
        provider_db_path: Path to source provider.db
        router_db_path: Path to destination router.db
        dry_run: If True, don't write changes
    """
    if not provider_db_path.exists():
        logger.error(f"Provider database not found at {provider_db_path}")
        return False
        
    if not router_db_path.exists():
        logger.error(f"Router database not found at {router_db_path}")
        return False
    
    logger.info(f"Reading from {provider_db_path}")
    logger.info(f"Writing to {router_db_path}")
    
    # Initialize connections to None for finally block
    src_conn = None
    dst_conn = None
    
    # Connect to both databases
    try:
        # Open provider DB
        src_conn = sqlite3.connect(str(provider_db_path))
        src_conn.row_factory = sqlite3.Row
        src_cursor = src_conn.cursor()
        
        # Open router DB
        dst_conn = sqlite3.connect(str(router_db_path))
        dst_cursor = dst_conn.cursor()
        
        # Check if destination table exists
        dst_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='benchmarks'")
        if not dst_cursor.fetchone():
            logger.error("Destination 'benchmarks' table not found in router.db. Is this a valid SmarterRouter database?")
            return False
            
        # Get source data
        src_cursor.execute("""
            SELECT model_id, reasoning_score, coding_score, general_score, elo_rating
            FROM model_benchmarks
        """)
        rows = src_cursor.fetchall()
        
        logger.info(f"Found {len(rows)} active models to export")
        
        updated_count = 0
        inserted_count = 0
        
        for row in rows:
            # Map model_id -> ollama_name
            ollama_name = row['model_id']
            
            if dry_run:
                continue
                
            # Check if exists
            dst_cursor.execute("SELECT 1 FROM benchmarks WHERE ollama_name = ?", (ollama_name,))
            exists = dst_cursor.fetchone()
            
            if exists:
                # Update
                dst_cursor.execute("""
                    UPDATE benchmarks 
                    SET reasoning_score = ?, coding_score = ?, general_score = ?, elo_rating = ?, last_updated = ?
                    WHERE ollama_name = ?
                """, (
                    row['reasoning_score'], 
                    row['coding_score'], 
                    row['general_score'], 
                    row['elo_rating'], 
                    datetime.now().isoformat(),
                    ollama_name
                ))
                updated_count += 1
            else:
                # Insert
                dst_cursor.execute("""
                    INSERT INTO benchmarks (ollama_name, reasoning_score, coding_score, general_score, elo_rating, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    ollama_name,
                    row['reasoning_score'],
                    row['coding_score'],
                    row['general_score'],
                    row['elo_rating'],
                    datetime.now().isoformat()
                ))
                inserted_count += 1
                
        if not dry_run:
            dst_conn.commit()
            logger.info(f"Export complete: {inserted_count} inserted, {updated_count} updated")
        else:
            logger.info(f"Dry run complete: would insert {inserted_count}, update {updated_count}")
            
    except Exception as e:
        logger.error(f"Error during export: {e}")
        return False
    finally:
        if src_conn is not None:
            src_conn.close()
        if dst_conn is not None:
            dst_conn.close()
        
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge provider.db into SmarterRouter's router.db")
    parser.add_argument("--provider-db", "-p", type=str, required=True, help="Path to provider.db")
    parser.add_argument("--router-db", "-r", type=str, required=True, help="Path to router.db")
    parser.add_argument("--dry-run", action="store_true", help="Don't write changes")
    
    args = parser.parse_args()
    
    success = export_to_router_db(Path(args.provider_db), Path(args.router_db), args.dry_run)
    sys.exit(0 if success else 1)
