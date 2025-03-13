# Embedding Migration Instructions

This document explains how to migrate existing messages in the Mem4AI database to add vector embeddings for improved search capabilities.

## What This Migration Does

The migration script:

1. Scans the database for user and assistant messages without embeddings
2. Generates embeddings for these messages using OpenAI's embedding model
3. Stores these embeddings in the database for future semantic search

## Prerequisites

- Python 3.8+
- OpenAI Python package (`pip install openai`)
- An OpenAI API key set as an environment variable (`OPENAI_API_KEY`)

## Running the Migration

### Option 1: Run as a module

```bash
# Basic usage (uses default database location at ~/.agentloop/memory.db)
python -m agentloop.migrate_embeddings

# Specify a custom database path
python -m agentloop.migrate_embeddings --db /path/to/your/database.db

# Increase batch size for faster processing (default: 32)
python -m agentloop.migrate_embeddings --batch-size 64

# Resume from a specific message ID (useful if previous run was interrupted)
python -m agentloop.migrate_embeddings --resume-from 1234
```

### Option 2: Import and run programmatically

```python
from agentloop.mem4ai import migrate_embeddings

# Basic usage
migrate_embeddings()

# With custom parameters
migrate_embeddings(
    db_path="/path/to/your/database.db",
    batch_size=64,
    resume_from=1234
)
```

## Troubleshooting

### Migration Interrupted

If the migration is interrupted (due to API errors, rate limits, etc.), the script will output the last processed message ID. You can resume from that point by using the `--resume-from` parameter.

### Rate Limits

If you encounter rate limits from the OpenAI API, try:
- Reducing the batch size (e.g., `--batch-size 10`)
- Waiting a while before resuming
- Using an API key with higher rate limits

### Database Errors

If you encounter database errors:
- Ensure the database path is correct
- Check that the database has the correct schema with the embedding fields
- Verify you have write permissions to the database file

## After Migration

Once migration is complete, the hybrid search functionality will automatically use both BM25 text search and vector similarity for more relevant results.

No further configuration is needed - the system will use the embeddings automatically.