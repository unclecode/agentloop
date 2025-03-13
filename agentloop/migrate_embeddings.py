#!/usr/bin/env python
"""
Migration script for adding embeddings to existing messages in the Mem4AI database.
This script adds vector embeddings to all user and assistant messages to enable
semantic search capabilities.

Usage:
    python -m agentloop.migrate_embeddings [--db DB_PATH] [--batch-size BATCH_SIZE] [--resume-from MESSAGE_ID]
"""

import os
import sys
from .mem4ai import migrate_embeddings

def run_migration():
    """Run the embedding migration with command line arguments"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate Mem4AI messages to add embeddings")
    parser.add_argument("--db", default=os.path.expanduser("~/.agentloop/memory.db"), 
                        help="Database path (default: ~/.agentloop/memory.db)")
    parser.add_argument("--batch-size", type=int, default=32, 
                        help="Batch size for processing (default: 32)")
    parser.add_argument("--resume-from", type=int, default=0, 
                        help="Message ID to resume from (in case of interrupted migration)")
    
    args = parser.parse_args()
    
    # Check if the database file exists
    if not os.path.exists(args.db):
        print(f"Error: Database file not found: {args.db}")
        sys.exit(1)
    
    # Run migration
    migrate_embeddings(args.db, args.batch_size, args.resume_from)
    
if __name__ == "__main__":
    run_migration()